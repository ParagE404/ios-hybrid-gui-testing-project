"""Run one scenario under one configuration and record everything.

Origin: original, 

Configurations share one codebase (proposal):
    scripted  fixed Appium locators from the scenario file
    a11y      structured resolver + router, VLM disabled
    hybrid    structured resolver + router, VLM fallback when the router is uncertain

Two policies are explicit because they change results (decision D-007, proposed):
    a11y_on_uncertain  "best_effort": act on the top candidate anyway if it is valid
                       "fail": stop the step
    hybrid_on_reject   what hybrid does when every VLM proposal is rejected
                       "best_effort" (same as a11y) or "fail"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from . import matchers
from .backend import Backend
from .model import Action, Intent, Snapshot
from .resolver import ResolverConfig, resolve
from .router import RouterConfig, route
from .scenario import Scenario, Step
from .telemetry import Telemetry
from .validator import ValidatorConfig, validate
from .vlm import VLMAdapter


@dataclass
class RunConfig:
    name: str
    use_resolver: bool
    use_vlm: bool
    a11y_on_uncertain: str = "best_effort"
    hybrid_on_reject: str = "best_effort"
    max_vlm_attempts: int = 2
    resolver: ResolverConfig = field(default_factory=ResolverConfig)
    router: RouterConfig = field(default_factory=RouterConfig)
    validator: ValidatorConfig = field(default_factory=ValidatorConfig)


CONFIGS = {
    "scripted": RunConfig("scripted", use_resolver=False, use_vlm=False),
    "a11y": RunConfig("a11y", use_resolver=True, use_vlm=False),
    "hybrid": RunConfig("hybrid", use_resolver=True, use_vlm=True),
}


_INFRA_NAMES = {"InvalidSessionIdException", "NoSuchDriverException", "MaxRetryError", "NewConnectionError",
                "ConnectionRefusedError", "ConnectionError", "ProtocolError", "RemoteDisconnected"}
_INFRA_TEXT = ("session is either terminated", "not started", "connection refused", "instruments crashed",
               "xcodebuild failed", "could not proxy command")


class InfrastructureError(RuntimeError):
    """The automation stack failed (Appium/WDA/simulator), not the engine's decision.

    Pre-registered rule (PLAN Week 5, D-014): such runs are retried up to twice by the
    batch runner; if they still fail they are excluded from analysis and reported.
    """


def is_infrastructure_error(exc: BaseException) -> bool:
    if isinstance(exc, InfrastructureError):
        return True
    for cls in type(exc).__mro__:
        if cls.__name__ in _INFRA_NAMES:
            return True
    msg = str(exc).lower()
    return any(t in msg for t in _INFRA_TEXT)


def _err(exc: BaseException) -> dict:
    return {"type": type(exc).__name__, "message": str(exc).splitlines()[0][:300] if str(exc) else ""}


@dataclass
class StepResult:
    index: int
    executed: bool
    route: str
    reason: str
    oracle_ok: Optional[bool]
    expect_ok: Optional[bool]
    latency_ms: dict

    @property
    def success(self) -> bool:
        return self.executed and self.oracle_ok is not False and self.expect_ok is not False


@dataclass
class ScenarioResult:
    scenario_id: str
    config: str
    condition: str
    repetition: int
    steps: list[StepResult]
    postconditions_ok: bool
    completed: bool
    total_ms: float
    infrastructure_error: bool = False


def _action_from_candidate(intent: Intent, cand) -> Action:
    cx, cy = cand.element.tap_point
    if intent.action == "type_text":
        return Action(kind="type_text", x=cx, y=cy, text=intent.value, element_idx=cand.element.idx)
    return Action(kind="tap", x=cx, y=cy, element_idx=cand.element.idx)


def _targetless(intent: Intent) -> Action:
    if intent.action == "swipe":
        return Action(kind="swipe", direction=intent.value)
    if intent.action == "navigate_back":
        return Action(kind="navigate_back")
    return Action(kind="wait", seconds=min(float(intent.value or 1), 5.0))


def _execute(backend: Backend, a: Action) -> None:
    if a.kind == "tap":
        backend.tap(a.x, a.y)
    elif a.kind == "type_text":
        backend.type_text(a.x, a.y, a.text)
    elif a.kind == "swipe":
        backend.swipe(a.direction)
    elif a.kind == "navigate_back":
        backend.back()
    elif a.kind == "wait":
        backend.wait(a.seconds)
    else:
        raise ValueError(f"cannot execute {a.kind}")


def _oracle(step: Step, snap: Snapshot, a: Optional[Action], condition: str = "baseline") -> Optional[bool]:
    """Did the action hit the element the scenario author intended? None = no oracle."""
    oracle = step.oracle_for(condition)
    if not oracle:
        return None
    if a is None or a.element_idx is None:
        return False
    el = snap.elements[a.element_idx]
    # Accept the hit element itself, an ancestor (e.g. the Cell around a label),
    # or a descendant (e.g. the label inside the Cell that was tapped).
    related = [el] + [snap.elements[i] for i in el.ancestors] + \
              [e for e in snap.elements if el.is_ancestor_of(e)]
    return any(matchers.matches(e, snap, oracle) for e in related)


def run_step(i: int, step: Step, backend: Backend, cfg: RunConfig, vlm: Optional[VLMAdapter],
             tel: Telemetry, condition: str = "baseline") -> StepResult:
    lat: dict = {}
    t_step = time.perf_counter()
    snap = backend.snapshot()
    lat["snapshot_ms"] = snap.retrieval_ms
    intent = step.intent
    action: Optional[Action] = None
    route_name, reason = "scripted", "n/a"
    log: dict = {"step_index": i, "step": step.text, "action_type": intent.action,
                 "snapshot_chars": snap.source_chars, "snapshot_sha1": snap.source_sha1}

    if not cfg.use_resolver:
        if intent.action in ("tap", "type_text"):
            ok = backend.scripted(step.scripted, intent.action, intent.value)
            reason = "ok" if ok else "locator_not_found"
            executed = ok
        else:
            _execute(backend, _targetless(intent))
            executed, reason = True, "not_applicable"
        lat["total_ms"] = (time.perf_counter() - t_step) * 1000
        after = backend.snapshot()
        expect_ok = matchers.check(after, step.expect_after)[0] if step.expect_after else None
        tel.emit("step", **log, route=route_name, reason=reason, executed=executed,
                 oracle_ok=None, expect_ok=expect_ok, latency=lat)
        return StepResult(i, executed, route_name, reason, None, expect_ok, lat)

    res = resolve(snap, intent, cfg.resolver)
    lat["resolution_ms"] = res.resolution_ms
    dec = route(res, cfg.router)
    route_name, reason = dec.route, dec.reason
    log["candidates"] = [c.to_log() for c in res.candidates]
    log["collapsed"] = res.collapsed
    log["decision"] = dec.to_log()

    if intent.action in ("swipe", "navigate_back", "wait"):
        action = _targetless(intent)
    elif dec.route == "structured":
        action = _action_from_candidate(intent, dec.chosen)
    else:
        top_valid = res.top is not None and res.top.score > 0
        if cfg.use_vlm and vlm is not None:
            cand_idxs = {c.element.idx for c in res.candidates}
            attempts = []
            for attempt in range(cfg.max_vlm_attempts):
                try:
                    shot = backend.screenshot_png()
                except Exception as e:  # screenshots come from the automation stack
                    raise InfrastructureError(f"screenshot failed: {e}") from e
                try:
                    vr = vlm.propose(shot, intent, dec.reason, [c.to_log() for c in res.candidates],
                                     (snap.width, snap.height), attempt=attempt)
                except Exception as e:  # a model failure counts against the hybrid route
                    attempts.append({"attempt": attempt, "vlm_error": _err(e)})
                    continue
                lat.setdefault("vlm_ms", []).append(vr.latency_ms)
                a = validate(vr.parsed, intent, snap, cand_idxs, cfg.validator)
                attempts.append({"attempt": attempt, "vlm": vr.to_log(), "validated": a.to_log()})
                if a.kind != "reject":
                    action, route_name = a, "vlm"
                    break
            log["vlm_attempts"] = attempts
            if action is None:
                route_name = "vlm_rejected"
                if cfg.hybrid_on_reject == "best_effort" and top_valid:
                    action, route_name = _action_from_candidate(intent, res.top), "vlm_rejected_best_effort"
        elif cfg.a11y_on_uncertain == "best_effort" and top_valid:
            action, route_name = _action_from_candidate(intent, res.top), "best_effort"

    oracle_ok = _oracle(step, snap, action, condition) if intent.action in ("tap", "type_text") else None
    executed = False
    if action is not None:
        t = time.perf_counter()
        try:
            _execute(backend, action)
            executed = True
        except Exception as e:
            if is_infrastructure_error(e):
                raise
            # The action itself failed (e.g. typing after tapping a non-input). Record a failed step.
            log["execution_error"] = _err(e)
            reason = "execution_error"
        lat["execute_ms"] = (time.perf_counter() - t) * 1000
    lat["total_ms"] = (time.perf_counter() - t_step) * 1000
    expect_ok = None
    if step.expect_after and executed:
        expect_ok = matchers.check(backend.snapshot(), step.expect_after)[0]
    tel.emit("step", **log, route=route_name, reason=reason, executed=executed,
             action=action.to_log() if action else None, oracle_ok=oracle_ok, expect_ok=expect_ok, latency=lat)
    return StepResult(i, executed, route_name, reason, oracle_ok, expect_ok, lat)


def run_scenario(scn: Scenario, backend: Backend, cfg: RunConfig, condition: str, repetition: int,
                 vlm: Optional[VLMAdapter] = None, tel: Optional[Telemetry] = None) -> ScenarioResult:
    tel = (tel or Telemetry(None)).bind(scenario=scn.id, app=scn.app, config=cfg.name,
                                       condition=condition, repetition=repetition)
    args = list(scn.initial_state.get("launch_args", []))
    if condition == "perturbed" and scn.perturbation:
        args += scn.perturbation.launch_args
    t0 = time.perf_counter()
    results: list[StepResult] = []
    try:
        backend.reset(args)
        tel.emit("scenario_start", launch_args=args, category=scn.category,
                 perturbation_kind=scn.perturbation.kind if scn.perturbation else None)
        for i, step in enumerate(scn.steps):
            r = run_step(i, step, backend, cfg, vlm, tel, condition)
            results.append(r)
            if not r.executed:
                break
        final = backend.snapshot()
    except Exception as e:
        if not is_infrastructure_error(e):
            raise  # an engine bug: fail loudly rather than record misleading data
        total = (time.perf_counter() - t0) * 1000
        tel.emit("scenario_end", completed=False, postconditions_ok=False, infrastructure_error=True,
                 error=_err(e), steps_run=len(results), total_ms=total)
        return ScenarioResult(scn.id, cfg.name, condition, repetition, results, False, False, total,
                              infrastructure_error=True)
    checks = [matchers.check(final, c) for c in scn.postconditions]
    post_ok = all(ok for ok, _ in checks)
    all_steps = len(results) == len(scn.steps) and all(r.success for r in results)
    completed = all_steps and post_ok
    total = (time.perf_counter() - t0) * 1000
    tel.emit("scenario_end", completed=completed, postconditions_ok=post_ok, infrastructure_error=False,
             postconditions=[m for _, m in checks], steps_run=len(results), total_ms=total)
    return ScenarioResult(scn.id, cfg.name, condition, repetition, results, post_ok, completed, total)

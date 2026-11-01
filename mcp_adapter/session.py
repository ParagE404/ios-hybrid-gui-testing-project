
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from engine import matchers
from engine.backend import Backend
from engine.intent import parse_step
from engine.model import Snapshot
from engine.resolver import resolve
from engine.router import route
from engine.runner import CONFIGS, StepResult, _err, is_infrastructure_error, run_step
from engine.scenario import Scenario, Step, load_dir
from engine.telemetry import Telemetry

ACTIONS = ("tap", "type_text", "swipe", "navigate_back", "wait")
DIRECTIONS = ("up", "down", "left", "right")
MAX_TEXT = 200
MAX_WAIT_S = 5.0
MAX_ELEMENTS = 300


class ToolError(ValueError):
    """A request outside the adapter's bounds. Returned to the caller as an error, never executed."""


def _step_payload(r: StepResult, rec: dict) -> dict:
    keep = ("step_index", "step", "action_type", "route", "reason", "decision", "candidates", "action",
            "oracle_ok", "expect_ok", "executed", "vlm_attempts", "execution_error", "latency",
            "snapshot_sha1", "snapshot_chars")
    out = {k: rec.get(k) for k in keep if k in rec}
    out["success"] = r.success
    return out


class EngineSession:
    def __init__(self, backend_for: Callable[[str], Backend], tel: Telemetry,
                 scenarios_dir: str | Path = "benchmark/scenarios", apps: Optional[dict] = None,
                 vlm_factory: Optional[Callable[[], object]] = None):
        self.backend_for = backend_for
        self.tel = tel
        self.scenarios = {s.id: s for s in load_dir(scenarios_dir)} if scenarios_dir else {}
        self.apps = apps or {}
        self.vlm_factory = vlm_factory
        self._vlm = None
        self.app: Optional[str] = None
        self._run: Optional[dict] = None
        self._last_snap: Optional[Snapshot] = None

    # ------------------------------------------------------------------ helpers
    def _vlm_for(self, config: str):
        if not CONFIGS[config].use_vlm:
            return None
        if self._vlm is None:
            if self.vlm_factory is None:
                raise ToolError("hybrid needs a VLM; start the server with --vlm")
            self._vlm = self.vlm_factory()
        return self._vlm

    def _backend(self) -> Backend:
        if self.app is None:
            raise ToolError("no app selected: call select_app or start_scenario first")
        return self.backend_for(self.app)

    def _config(self, config: str):
        if config not in CONFIGS:
            raise ToolError(f"config must be one of {sorted(CONFIGS)}")
        if config == "scripted":
            raise ToolError("the scripted baseline needs locators from a scenario file; use start_scenario")
        return CONFIGS[config]

    # ------------------------------------------------------------------ discovery
    def list_scenarios(self) -> list[dict]:
        return [{"id": s.id, "app": s.app, "title": s.title, "category": s.category,
                 "steps": [st.text for st in s.steps]} for s in self.scenarios.values() if not s.pilot]

    def select_app(self, app: str, launch_args: Optional[list[str]] = None) -> dict:
        if self.apps and app not in self.apps:
            raise ToolError(f"unknown app {app!r}; allowed: {sorted(self.apps)}")
        args = list(launch_args or [])
        if any(not a.startswith("-") and (i == 0 or args[i - 1] != "-perturb") for i, a in enumerate(args)):
            raise ToolError("launch_args may contain only flags and '-perturb <name>' pairs")
        self.app = app
        self._backend().reset(args)
        return {"app": app, "launch_args": args}

    # ------------------------------------------------------------------ benchmark path (mirrors run_scenario)
    def start_scenario(self, scenario_id: str, condition: str = "baseline", config: str = "a11y",
                       repetition: int = 1) -> dict:
        if scenario_id not in self.scenarios:
            raise ToolError(f"unknown scenario {scenario_id!r}")
        if condition not in ("baseline", "perturbed"):
            raise ToolError("condition must be baseline or perturbed")
        if config not in CONFIGS:
            raise ToolError(f"config must be one of {sorted(CONFIGS)}")
        scn: Scenario = self.scenarios[scenario_id]
        cfg = CONFIGS[config]
        tel = self.tel.bind(scenario=scn.id, app=scn.app, config=cfg.name, condition=condition,
                            repetition=repetition)
        args = list(scn.initial_state.get("launch_args", []))
        if condition == "perturbed" and scn.perturbation:
            args += scn.perturbation.launch_args
        self.app = scn.app
        t0 = time.perf_counter()
        self._run = {"scn": scn, "cfg": cfg, "tel": tel, "condition": condition, "t0": t0,
                     "results": [], "stopped": False, "vlm": self._vlm_for(config)}
        try:
            self._backend().reset(args)
        except Exception as e:
            return self._infra(e)
        tel.emit("scenario_start", launch_args=args, category=scn.category,
                 perturbation_kind=scn.perturbation.kind if scn.perturbation else None)
        return {"scenario": scn.id, "steps": len(scn.steps), "launch_args": args}

    def run_step(self, index: int) -> dict:
        run = self._require_run()
        scn: Scenario = run["scn"]
        if index != len(run["results"]):
            raise ToolError(f"steps run in order; next step is {len(run['results'])}")
        if run["stopped"]:
            raise ToolError("the previous step was not executed; call finish_scenario")
        if not 0 <= index < len(scn.steps):
            raise ToolError("step index out of range")
        try:
            r = run_step(index, scn.steps[index], self._backend(), run["cfg"], run["vlm"], run["tel"],
                         run["condition"])
        except Exception as e:
            if not is_infrastructure_error(e):
                raise
            return self._infra(e)
        run["results"].append(r)
        run["stopped"] = not r.executed
        return _step_payload(r, run["tel"].records[-1])

    def finish_scenario(self) -> dict:
        run = self._require_run()
        scn: Scenario = run["scn"]
        results: list[StepResult] = run["results"]
        try:
            final = self._backend().snapshot()
        except Exception as e:
            if not is_infrastructure_error(e):
                raise
            return self._infra(e)
        checks = [matchers.check(final, c) for c in scn.postconditions]
        post_ok = all(ok for ok, _ in checks)
        all_steps = len(results) == len(scn.steps) and all(r.success for r in results)
        completed = all_steps and post_ok
        total = (time.perf_counter() - run["t0"]) * 1000
        run["tel"].emit("scenario_end", completed=completed, postconditions_ok=post_ok,
                        infrastructure_error=False, postconditions=[m for _, m in checks],
                        steps_run=len(results), total_ms=total)
        self._run = None
        return {"completed": completed, "postconditions_ok": post_ok,
                "postconditions": [m for _, m in checks], "steps_run": len(results), "total_ms": total}

    def _require_run(self) -> dict:
        if self._run is None:
            raise ToolError("no scenario in progress: call start_scenario first")
        return self._run

    def _infra(self, e: BaseException) -> dict:
        run = self._run
        total = (time.perf_counter() - run["t0"]) * 1000 if run else 0.0
        if run:
            run["tel"].emit("scenario_end", completed=False, postconditions_ok=False, infrastructure_error=True,
                            error=_err(e), steps_run=len(run["results"]), total_ms=total)
        self._run = None
        return {"infrastructure_error": True, "error": _err(e), "total_ms": total}

    # ------------------------------------------------------------------ interactive path (agent use)
    def snapshot(self, max_elements: int = 150, interactive_only: bool = True) -> dict:
        from engine.validator import INTERACTIVE
        max_elements = max(1, min(int(max_elements), MAX_ELEMENTS))
        snap = self._backend().snapshot()
        self._last_snap = snap
        els = [e for e in snap.elements if e.visible and (not interactive_only or e.type in INTERACTIVE)]
        return {"app": self.app, "width": snap.width, "height": snap.height, "elements_total": len(snap.elements),
                "sha1": snap.source_sha1, "truncated": len(els) > max_elements,
                "elements": [e.summary() for e in els[:max_elements]]}

    def resolve(self, step: str, config: str = "a11y") -> dict:
        """Read-only: what would the structured resolver and router do for this step now?"""
        cfg = self._config(config)
        intent = self._intent(step)
        snap = self._backend().snapshot()
        self._last_snap = snap
        res = resolve(snap, intent, cfg.resolver)
        dec = route(res, cfg.router)
        return {"intent": {"action": intent.action, "target": intent.target, "value": intent.value},
                "decision": dec.to_log(), "candidates": [c.to_log() for c in res.candidates],
                "resolution_ms": res.resolution_ms}

    def act(self, step: str, config: str = "a11y") -> dict:
        """Resolve and execute one free-text step with the engine's own step logic (no oracle)."""
        cfg = self._config(config)
        st = Step(text=step, intent=self._intent(step))
        tel = self.tel.bind(app=self.app, config=cfg.name, condition="interactive")
        r = run_step(0, st, self._backend(), cfg, self._vlm_for(config), tel, "baseline")
        return _step_payload(r, tel.records[-1])

    def execute_action(self, kind: str, x: Optional[float] = None, y: Optional[float] = None,
                       text: Optional[str] = None, direction: Optional[str] = None,
                       seconds: Optional[float] = None) -> dict:
        """One bounded low-level action, checked like a VLM proposal before it runs."""
        if kind not in ACTIONS:
            raise ToolError(f"kind must be one of {ACTIONS}")
        b = self._backend()
        if kind in ("tap", "type_text"):
            snap = self._last_snap or b.snapshot()
            if x is None or y is None or not (0 <= x <= snap.width and 0 <= y <= snap.height):
                raise ToolError(f"x, y must lie on the screen (0..{snap.width}, 0..{snap.height})")
            if kind == "type_text":
                if not text or len(text) > MAX_TEXT:
                    raise ToolError(f"text is required and at most {MAX_TEXT} characters")
                b.type_text(x, y, text)
            else:
                b.tap(x, y)
        elif kind == "swipe":
            if direction not in DIRECTIONS:
                raise ToolError(f"direction must be one of {DIRECTIONS}")
            b.swipe(direction)
        elif kind == "navigate_back":
            b.back()
        else:
            s = float(seconds if seconds is not None else 1.0)
            if not 0 < s <= MAX_WAIT_S:
                raise ToolError(f"seconds must be in (0, {MAX_WAIT_S}]")
            b.wait(s)
        self._last_snap = None
        return {"ok": True, "kind": kind}

    def telemetry(self, last: int = 20) -> list[dict]:
        last = max(1, min(int(last), 200))
        return self.tel.records[-last:]

    @staticmethod
    def _intent(step: str):
        if not step or len(step) > 300:
            raise ToolError("step text is required and at most 300 characters")
        try:
            return parse_step(step)
        except ValueError as e:
            raise ToolError(str(e)) from e

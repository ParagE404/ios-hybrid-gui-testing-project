"""Formal experiment batch runner: scenarios x conditions x configurations x repetitions.

Origin: original, 

Pre-registered run protocol (D-014, written 18 Oct 2026 before any formal run):
  * Order: repetition blocks (all of rep 1, then rep 2, then rep 3). Within a block the
    scenario order is shuffled, and for each scenario the 6 condition x configuration
    pairs are shuffled. One fixed seed, stored in the manifest.
  * Every run starts from a fresh app launch with -resetData (runner.reset).
  * Infrastructure failures (Appium/WDA/simulator, see runner.is_infrastructure_error)
    are retried up to 2 more times after reconnecting; runs that still fail are excluded
    from analysis and reported with their count.
  * Engine errors (an exception inside the engine itself) are NOT retried: they are
    recorded as a failed run for that configuration (engine_error=true) and reported,
    because they are failures of the artefact under test.
  * Resume: a (scenario, condition, config, repetition) with a recorded scenario_end
    that is not an infrastructure failure is never re-run.
"""

from __future__ import annotations

import itertools
import json
import platform
import random
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

from .runner import CONFIGS, ScenarioResult, is_infrastructure_error, run_scenario
from .scenario import Scenario
from .telemetry import Telemetry

Key = tuple[str, str, str, int]   # scenario, condition, config, repetition


def plan_runs(scenarios: list[Scenario], conditions: list[str], configs: list[str],
              repetitions: int, seed: int) -> list[Key]:
    rng = random.Random(seed)
    plan: list[Key] = []
    for rep in range(1, repetitions + 1):
        order = sorted(scenarios, key=lambda s: s.id)
        rng.shuffle(order)
        for scn in order:
            pairs = list(itertools.product(conditions, configs))
            rng.shuffle(pairs)
            plan += [(scn.id, cond, cfg, rep) for cond, cfg in pairs]
    return plan


def finished_keys(log_paths: list[Path]) -> set[Key]:
    done: set[Key] = set()
    for p in log_paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("event") == "scenario_end" and not r.get("infrastructure_error"):
                done.add((r["scenario"], r["condition"], r["config"], int(r["repetition"])))
    return done


def run_batch(scenarios: list[Scenario], plan: list[Key], backend_for: Callable[[str], object],
              reconnect: Callable[[], None], tel: Telemetry, vlm_factory: Optional[Callable[[], object]] = None,
              max_infra_retries: int = 2, log_paths: Optional[list[Path]] = None,
              progress: Callable[[str], None] = print) -> dict:
    by_id = {s.id: s for s in scenarios}
    done = finished_keys(log_paths or ([tel.path] if tel.path else []))
    todo = [k for k in plan if k not in done]
    vlm = None
    summary = {"planned": len(plan), "already_done": len(plan) - len(todo), "completed": 0, "failed": 0,
               "infrastructure_excluded": 0, "engine_errors": 0, "infra_retries": 0}
    t_start = time.perf_counter()
    for n, (sid, cond, cfg_name, rep) in enumerate(todo, 1):
        scn = by_id[sid]
        if cfg_name == "hybrid" and vlm is None and vlm_factory is not None:
            vlm = vlm_factory()
        cfg = CONFIGS[cfg_name]
        result: Optional[ScenarioResult] = None
        for attempt in range(max_infra_retries + 1):
            run_tel = tel.bind(attempt=attempt, plan_index=plan.index((sid, cond, cfg_name, rep)))
            try:
                result = run_scenario(scn, backend_for(scn.app), cfg, cond, rep, vlm=vlm, tel=run_tel)
            except Exception as e:
                if is_infrastructure_error(e):   # e.g. failure while connecting
                    result = None
                else:
                    run_tel.bind(scenario=sid, app=scn.app, config=cfg_name, condition=cond, repetition=rep).emit(
                        "scenario_end", completed=False, postconditions_ok=False, infrastructure_error=False,
                        engine_error=True, error={"type": type(e).__name__, "message": str(e)[:300]})
                    summary["engine_errors"] += 1
                    result = "engine_error"
                    break
            if result is not None and not result.infrastructure_error:
                break
            summary["infra_retries"] += 1
            try:
                reconnect()
            except Exception as e:  # keep going; the next attempt will fail and be recorded
                progress(f"reconnect failed: {e}")
        if result == "engine_error":
            outcome = "ENGINE ERROR"
        elif result is None or result.infrastructure_error:
            summary["infrastructure_excluded"] += 1
            outcome = "INFRA (excluded)"
        elif result.completed:
            summary["completed"] += 1
            outcome = "COMPLETED"
        else:
            summary["failed"] += 1
            outcome = "FAILED"
        elapsed = time.perf_counter() - t_start
        eta = elapsed / n * (len(todo) - n)
        progress(f"[{n}/{len(todo)}] {sid} {cond:9s} {cfg_name:8s} rep{rep}: {outcome}  "
                 f"(elapsed {elapsed / 60:.0f} min, eta {eta / 60:.0f} min)")
    summary["minutes"] = round((time.perf_counter() - t_start) / 60, 1)
    return summary


def write_manifest(path: Path, *, batch_id: str, seed: int, plan: list[Key], scenarios: list[Scenario],
                   extra: dict) -> None:
    from .runner import CONFIGS as C
    man = {
        "batch_id": batch_id, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seed": seed,
        "host": platform.platform(), "python": platform.python_version(),
        "configs": {k: {"use_resolver": v.use_resolver, "use_vlm": v.use_vlm,
                        "a11y_on_uncertain": v.a11y_on_uncertain, "hybrid_on_reject": v.hybrid_on_reject,
                        "max_vlm_attempts": v.max_vlm_attempts, "router": asdict(v.router),
                        "resolver": asdict(v.resolver)} for k, v in C.items()},
        "scenarios": {s.id: str(s.path) for s in scenarios},
        "plan": [list(k) for k in plan], **extra,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(man, indent=1, default=str))


def new_batch_id() -> str:
    return time.strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:4]

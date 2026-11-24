# Origin: AI-scaffolded and rewritten by the author.
"""Fixed fake-backend cases whose telemetry pins the frozen runner's behaviour (D-029).

`python tests/golden/runner_cases.py OUT.json` writes the telemetry of every case with timing fields
removed. Run it against the engine extracted from tag experiment-freeze-1 to create
frozen_runner_telemetry.json; tests/test_v2.py re-runs the cases on the current engine and requires
identical output for the v1 configurations.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMING = {"ts", "latency", "latency_ms", "total_ms", "resolution_ms", "snapshot_ms", "execute_ms", "vlm_ms"}


def _strip(x):
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k not in TIMING}
    if isinstance(x, list):
        return [_strip(v) for v in x]
    return x


def run_cases(configs=("scripted", "a11y", "hybrid"), overrides=None) -> list:
    from engine.backend import FakeBackend
    from engine.runner import CONFIGS, run_scenario
    from engine.scenario import load_scenario
    from engine.telemetry import Telemetry
    from engine.vlm import FakeVLM
    sys.path.insert(0, str(ROOT))
    from tests import fixtures as F

    scn = load_scenario(ROOT / "benchmark" / "examples" / "tb-example-add-item.yaml")
    homes = {"home": F.HOME, "renamed": F.HOME_RENAMED, "weak": F.HOME_WEAK, "delete": F.HOME_DELETE}
    vlms = {"none": dict(), "icon": dict(point=(372 / 402, 77 / 874)), "junk": dict(raw="click the plus"),
            "retry": dict(by_attempt={0: (0.74, 0.01), 1: (372 / 402, 77 / 874)})}
    out = []
    import tempfile
    for cfg in configs:
        rc = (overrides or {}).get(cfg, CONFIGS[cfg])
        for hname, home in homes.items():
            for vname, vkw in vlms.items():
                if cfg != "hybrid" and vname != "none":
                    continue
                for cond in ("baseline", "perturbed"):
                    fb = FakeBackend(
                        screens={"home": home, "add": F.ADD, "typed": F.ADD_TYPED, "done": F.HOME_EGGS},
                        start="home",
                        transitions={("home", "Add item"): "add", ("home", "addItemButton"): "add",
                                     ("home", "button_3"): "add", ("home", "addButton_v2"): "add",
                                     ("add", "type:Eggs"): "typed", ("typed", "Save"): "done"})
                    with tempfile.TemporaryDirectory() as d:
                        log = Path(d) / "t.jsonl"
                        run_scenario(scn, fb, rc, cond, 1, vlm=FakeVLM(**vkw), tel=Telemetry(log, run_id="g"))
                        recs = [_strip(json.loads(x)) for x in log.read_text().splitlines()]
                    out.append({"case": [cfg, hname, vname, cond], "records": recs, "actions": fb.actions})
    return out


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else str(ROOT))
    import engine
    print("engine used:", engine.__file__)
    Path(sys.argv[1]).write_text(json.dumps(run_cases(), indent=0, sort_keys=True))
    print("cases written:", sys.argv[1])

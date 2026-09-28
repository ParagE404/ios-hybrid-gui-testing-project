"""Batch runner tests on the fake backend. Origin: original, """
import json
from pathlib import Path

from engine.backend import FakeBackend
from engine.batch import finished_keys, plan_runs, run_batch
from engine.scenario import load_scenario
from engine.telemetry import Telemetry
from engine.vlm import FakeVLM

from . import fixtures as F

SCN = load_scenario(Path(__file__).parent.parent / "benchmark" / "examples" / "tb-example-add-item.yaml")


def fake():
    return FakeBackend(
        screens={"home": F.HOME, "add": F.ADD, "typed": F.ADD_TYPED, "done": F.HOME_EGGS}, start="home",
        transitions={("home", "Add item"): "add", ("home", "addItemButton"): "add",
                     ("add", "type:Eggs"): "typed", ("typed", "Save"): "done"})


def test_plan_is_complete_and_deterministic():
    p1 = plan_runs([SCN], ["baseline", "perturbed"], ["scripted", "a11y", "hybrid"], 3, seed=7)
    p2 = plan_runs([SCN], ["baseline", "perturbed"], ["scripted", "a11y", "hybrid"], 3, seed=7)
    assert p1 == p2 and len(p1) == 18 and len(set(p1)) == 18
    assert [k[3] for k in p1] == sorted(k[3] for k in p1)          # repetition blocks in order


class SessionDied(Exception):
    pass


SessionDied.__name__ = "InvalidSessionIdException"


def test_infra_failure_retried_then_resume_skips(tmp_path):
    log = tmp_path / "b.jsonl"
    plan = plan_runs([SCN], ["baseline"], ["scripted", "a11y", "hybrid"], 1, seed=1)
    calls = {"n": 0}
    be = fake()
    orig = be.snapshot

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise SessionDied("A session is either terminated or not started")
        return orig()
    be.snapshot = flaky
    s = run_batch([SCN], plan, lambda app: be, lambda: None, Telemetry(log, run_id="t"),
                  vlm_factory=lambda: FakeVLM(), progress=lambda m: None)
    assert s["infra_retries"] == 1 and s["completed"] == 3 and s["infrastructure_excluded"] == 0
    ends = [json.loads(l) for l in log.read_text().splitlines() if '"scenario_end"' in l]
    assert sum(e["infrastructure_error"] for e in ends) == 1
    assert len(finished_keys([log])) == 3
    s2 = run_batch([SCN], plan, lambda app: fake(), lambda: None, Telemetry(log, run_id="t2"),
                   progress=lambda m: None)
    assert s2["already_done"] == 3 and s2["completed"] == 0


def test_action_error_is_a_failed_step_not_a_crash(tmp_path):
    be = fake()

    def boom(x, y, text):
        raise ValueError("active element is not a text field")
    be.type_text = boom
    plan = [(SCN.id, "baseline", "a11y", 1)]
    s = run_batch([SCN], plan, lambda app: be, lambda: None, Telemetry(tmp_path / "c.jsonl", run_id="t"),
                  progress=lambda m: None)
    assert s["failed"] == 1 and s["engine_errors"] == 0
    steps = [json.loads(l) for l in (tmp_path / "c.jsonl").read_text().splitlines() if '"step"' in l]
    assert steps[1]["reason"] == "execution_error" and steps[1]["executed"] is False

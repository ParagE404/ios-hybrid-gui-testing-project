"""Integration tests: full scenario runs on the fake backend for all three configurations.

Origin: original, 
"""

import json
from pathlib import Path

import pytest

from engine.backend import FakeBackend
from engine.runner import CONFIGS, run_scenario
from engine.scenario import load_scenario
from engine.telemetry import Telemetry
from engine.vlm import FakeVLM

from . import fixtures as F

SCENARIO = Path(__file__).parent.parent / "benchmark" / "examples" / "tb-example-add-item.yaml"


def backend(home_xml):
    return FakeBackend(
        screens={"home": home_xml, "add": F.ADD, "typed": F.ADD_TYPED, "done": F.HOME_EGGS},
        start="home",
        transitions={("home", "Add item"): "add", ("home", "addItemButton"): "add",
                     ("home", "button_3"): "add", ("home", "addButton_v2"): "add",
                     ("add", "type:Eggs"): "typed", ("typed", "Save"): "done"},
    )


@pytest.fixture
def scn():
    return load_scenario(SCENARIO)


def test_scenario_loads(scn):
    assert scn.id == "tb-example-add-item" and len(scn.steps) == 3
    assert scn.perturbation.kind == "identifier_rename"


@pytest.mark.parametrize("config", ["scripted", "a11y", "hybrid"])
def test_baseline_completes_in_every_config(scn, config):
    r = run_scenario(scn, backend(F.HOME), CONFIGS[config], "baseline", 1, vlm=FakeVLM())
    assert r.completed, r


def test_identifier_rename_breaks_scripted_but_not_a11y(scn):
    scripted = run_scenario(scn, backend(F.HOME_RENAMED), CONFIGS["scripted"], "perturbed", 1)
    a11y = run_scenario(scn, backend(F.HOME_RENAMED), CONFIGS["a11y"], "perturbed", 1)
    assert not scripted.completed and scripted.steps[0].reason == "locator_not_found"
    assert a11y.completed


def test_weak_metadata_needs_vlm(scn, tmp_path):
    log = tmp_path / "run.jsonl"
    a11y = run_scenario(scn, backend(F.HOME_WEAK), CONFIGS["a11y"], "perturbed", 1)
    vlm = FakeVLM(point=(372 / 402, 77 / 874))       # model points at the icon-only button
    hybrid = run_scenario(scn, backend(F.HOME_WEAK), CONFIGS["hybrid"], "perturbed", 1,
                          vlm=vlm, tel=Telemetry(log, run_id="t1"))
    assert not a11y.completed
    assert hybrid.completed and hybrid.steps[0].route == "vlm"
    assert vlm.calls and vlm.calls[0]["reason"] in ("no_match", "low_score")
    lines = [json.loads(x) for x in log.read_text().splitlines()]
    assert lines[0]["event"] == "scenario_start" and lines[-1]["event"] == "scenario_end"
    step0 = lines[1]
    assert step0["route"] == "vlm" and step0["vlm_attempts"][0]["validated"]["kind"] == "tap"
    assert all(k in step0 for k in ("scenario", "config", "condition", "repetition", "run_id"))


def test_malformed_vlm_output_is_rejected_and_logged(scn):
    vlm = FakeVLM(raw="I think you should click the plus")
    r = run_scenario(scn, backend(F.HOME_WEAK), CONFIGS["hybrid"], "perturbed", 1, vlm=vlm)
    assert not r.completed and r.steps[0].route == "vlm_rejected"
    assert len(vlm.calls) == CONFIGS["hybrid"].max_vlm_attempts


def test_vlm_retry_uses_full_step_text(scn):
    # attempt 0 points at nothing interactive (status bar), attempt 1 at the icon-only button
    vlm = FakeVLM(by_attempt={0: (0.74, 0.01), 1: (372 / 402, 77 / 874)})
    r = run_scenario(scn, backend(F.HOME_WEAK), CONFIGS["hybrid"], "perturbed", 1, vlm=vlm)
    assert r.completed and r.steps[0].route == "vlm"
    assert vlm.calls[0]["query"] != vlm.calls[1]["query"]
    assert vlm.calls[1]["query"] == "Tap the 'Add item' button"

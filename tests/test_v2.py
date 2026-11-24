# Origin: AI-scaffolded and rewritten by the author.
"""Engine v2 options (D-029): scroll_to_find and relax_candidate_set, both off by default."""
import json
import sys
from pathlib import Path

import pytest

from engine.backend import FakeBackend
from engine.intent import parse_step
from engine.normalise import parse_page_source
from engine.runner import CONFIGS, RunConfig, run_scenario
from engine.scenario import Perturbation, Scenario, Step
from engine.telemetry import Telemetry
from engine.validator import ValidatorConfig, validate
from engine.vlm import FakeVLM

from . import fixtures as F

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "golden"))
import runner_cases  # noqa: E402


def scenario(*steps, post):
    return Scenario(id="v2-test", app="testbed", title="t",
                    steps=[Step(text=t, intent=parse_step(t), scripted={"strategy": "accessibility_id", "value": "x"},
                                oracle=o) for t, o in steps],
                    postconditions=post, perturbation=Perturbation("weak_metadata", ""))


# ------------------------------------------------------------------ defaults and frozen behaviour

def test_options_default_off():
    assert RunConfig("x", True, False).scroll_to_find is False
    assert ValidatorConfig().relax_candidate_set is False
    for name in ("scripted", "a11y", "hybrid"):
        assert CONFIGS[name].scroll_to_find is False
        assert CONFIGS[name].validator.relax_candidate_set is False
    for name in ("a11y-v2", "hybrid-v2"):
        assert CONFIGS[name].scroll_to_find and CONFIGS[name].validator.relax_candidate_set
    assert CONFIGS["hybrid-v2"].use_vlm and not CONFIGS["a11y-v2"].use_vlm


def test_v1_telemetry_identical_to_frozen_runner():
    """The golden file was produced by the engine extracted from tag experiment-freeze-1."""
    golden = json.loads((ROOT / "tests" / "golden" / "frozen_runner_telemetry.json").read_text())
    now = json.loads(json.dumps(runner_cases.run_cases(), sort_keys=True))
    assert len(golden) == len(now) == 48
    assert now == golden


# ------------------------------------------------------------------ scroll_to_find

TOP = F.page(F.e("Table", F.cell("Milk", 140), F.cell("Bread", 184), rect=(0, 120, 402, 600)))
BOTTOM = F.page(F.e("Table", F.cell("Eggs", 140), F.cell("About", 184), rect=(0, 120, 402, 600)))
ABOUT = F.page(F.e("StaticText", name="About page", label="About page", rect=(20, 140, 200, 20)))


def scroll_backend(swipes_needed=1):
    screens = {"top": TOP, "mid": TOP, "bottom": BOTTOM, "about": ABOUT}
    tr = {("bottom", "About"): "about"}
    tr[("top", "swipe:up")] = "bottom" if swipes_needed == 1 else "mid"
    tr[("mid", "swipe:up")] = "bottom"
    return FakeBackend(screens=screens, start="top", transitions=tr)


SCROLL_SCN = scenario(("Tap the 'About' row", {"label": "About"}),
                      post=[{"check": "exists", "element": {"label": "About page"}}])


def test_scroll_to_find_reaches_target_below_the_fold(tmp_path):
    log = tmp_path / "t.jsonl"
    v1 = run_scenario(SCROLL_SCN, scroll_backend(), CONFIGS["a11y"], "baseline", 1)
    fb = scroll_backend(swipes_needed=2)
    v2 = run_scenario(SCROLL_SCN, fb, CONFIGS["a11y-v2"], "baseline", 1, tel=Telemetry(log, run_id="t"))
    assert not v1.completed and v1.steps[0].reason == "no_match"
    assert v2.completed and v2.steps[0].route == "structured" and v2.steps[0].oracle_ok
    assert [a for a in fb.actions if "swipe" in a] == [{"swipe": "up"}, {"swipe": "up"}]
    step = [json.loads(x) for x in log.read_text().splitlines() if '"step"' in x][0]
    assert [s["reason"] for s in step["scroll_to_find"]] == ["no_match", "ok"]
    assert "scroll_ms" in step["latency"]


def test_scroll_to_find_stops_after_max_scrolls():
    fb = FakeBackend(screens={"top": TOP}, start="top", transitions={})
    r = run_scenario(SCROLL_SCN, fb, CONFIGS["a11y-v2"], "baseline", 1)
    assert not r.completed and r.steps[0].reason == "no_match"
    assert sum("swipe" in a for a in fb.actions) == CONFIGS["a11y-v2"].max_scrolls == 3


def test_scroll_to_find_not_used_when_a_candidate_exists():
    fb = scroll_backend()
    scn = scenario(("Tap the 'Milk' row", {"label": "Milk"}), post=[{"check": "exists", "element": {"label": "Milk"}}])
    r = run_scenario(scn, fb, CONFIGS["a11y-v2"], "baseline", 1)
    assert r.completed and not any("swipe" in a for a in fb.actions)


# ------------------------------------------------------------------ relax_candidate_set

# A sheet: the list's 'Add item' button is hidden behind it; the sheet's confirm is an unlabelled icon.
SHEET = F.page(
    F.e("Button", name="addItemButton", label="Add item", visible=False, rect=(350, 55, 44, 44)),
    F.e("NavigationBar",
        F.e("Button", name="button_21", rect=(330, 110, 60, 44)),
        name="New Item", rect=(0, 100, 402, 54)))
DONE = F.page(F.e("StaticText", name="Tea", label="Tea", rect=(20, 140, 200, 20)))
ICON = (360 / 402, 132 / 874)
RELAX_SCN = scenario(("Tap the 'Add' button", {"name": "button_21"}),
                     post=[{"check": "exists", "element": {"label": "Tea"}}])


def sheet_backend():
    return FakeBackend(screens={"sheet": SHEET, "done": DONE}, start="sheet",
                       transitions={("sheet", "button_21"): "done"})


def test_only_candidate_hidden_v1_rejects_v2_accepts(tmp_path):
    v1 = run_scenario(RELAX_SCN, sheet_backend(), CONFIGS["hybrid"], "baseline", 1, vlm=FakeVLM(point=ICON))
    assert not v1.completed and v1.steps[0].reason == "incompatible_state"
    log = tmp_path / "t.jsonl"
    v2 = run_scenario(RELAX_SCN, sheet_backend(), CONFIGS["hybrid-v2"], "baseline", 1, vlm=FakeVLM(point=ICON),
                      tel=Telemetry(log, run_id="t"))
    assert v2.completed and v2.steps[0].route == "vlm" and v2.steps[0].oracle_ok
    step = [json.loads(x) for x in log.read_text().splitlines() if '"step"' in x][0]
    assert step["candidate_set_relaxed"] is True
    rejected = [json.loads(x) for x in log.read_text().splitlines()]  # v1 rejects for the stated reason
    r1 = run_scenario(RELAX_SCN, sheet_backend(), CONFIGS["hybrid"], "baseline", 1, vlm=FakeVLM(point=ICON),
                      tel=Telemetry(tmp_path / "v1.jsonl", run_id="t"))
    s1 = [json.loads(x) for x in (tmp_path / "v1.jsonl").read_text().splitlines() if '"step"' in x][0]
    assert {a["validated"]["reason"] for a in s1["vlm_attempts"]} == {"outside_candidate_set"}
    assert "candidate_set_relaxed" not in s1 and not r1.completed and rejected


def test_a11y_v2_cannot_use_relaxation():
    r = run_scenario(RELAX_SCN, sheet_backend(), CONFIGS["a11y-v2"], "baseline", 1)
    assert not r.completed


def test_validator_relaxes_only_when_every_candidate_is_invalid():
    snap = parse_page_source(SHEET)
    hidden = next(e.idx for e in snap.elements if e.label == "Add item")
    intent = parse_step("Tap the 'Add' button")
    raw = {"action": "tap", "x": 360, "y": 132}
    on = ValidatorConfig(relax_candidate_set=True)
    assert validate(raw, intent, snap, {hidden}, on, all_candidates_invalid=False).reason == "outside_candidate_set"
    assert validate(raw, intent, snap, {hidden}, ValidatorConfig(), all_candidates_invalid=True).reason \
        == "outside_candidate_set"
    assert validate(raw, intent, snap, {hidden}, on, all_candidates_invalid=True).kind == "tap"


def test_relaxation_not_applied_when_a_candidate_scores():
    # the hidden button becomes visible: it now scores > 0, so the check stays on
    snap_xml = SHEET.replace('visible="false"', 'visible="true"')
    fb = FakeBackend(screens={"sheet": snap_xml, "done": DONE}, start="sheet",
                     transitions={("sheet", "button_21"): "done"})
    cfg = CONFIGS["hybrid-v2"]
    r = run_scenario(RELAX_SCN, fb, cfg, "baseline", 1, vlm=FakeVLM(point=ICON))
    assert r.steps[0].route != "vlm"


@pytest.mark.parametrize("name", ["a11y-v2", "hybrid-v2"])
def test_v2_configs_match_v1_on_cases_without_no_match_or_invalid_sets(name):
    """On the frozen golden cases the fixes never trigger, so v2 routes and outcomes equal v1."""
    v1 = name.replace("-v2", "")
    a = runner_cases.run_cases(configs=(v1,))
    b = runner_cases.run_cases(configs=(v1,), overrides={v1: CONFIGS[name]})
    strip = lambda cases: [[{k: v for k, v in r.items() if k not in ("config", "scroll_to_find", "candidate_set_relaxed")}
                            for r in c["records"]] for c in cases]
    triggered = [i for i, c in enumerate(b) if any("scroll_to_find" in r or "candidate_set_relaxed" in r
                                                    for r in c["records"])]
    same = [i for i in range(len(a)) if i not in triggered]
    assert [strip(a)[i] for i in same] == [strip(b)[i] for i in same]

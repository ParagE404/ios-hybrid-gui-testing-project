# Origin: AI-scaffolded and rewritten by the author.
"""Tests for analysis/sensitivity.py (workstream B, D-027)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import sensitivity as s  # noqa: E402

from engine.intent import parse_step  # noqa: E402
from engine.normalise import parse_page_source  # noqa: E402
from engine.resolver import ResolverConfig, resolve  # noqa: E402
from engine.router import RouterConfig, route  # noqa: E402
from engine.scenario import load_scenario  # noqa: E402

PS = ROOT / "benchmark" / "pagesource"


def _row(scn, cond, i, top, second, ok, rep=1, route="structured"):
    return {"scenario": scn, "app": "testbed", "condition": cond, "repetition": rep, "step_index": i,
            "step": "", "n_cands": 2, "top_score": top, "second_score": second, "top": ("Button", "X", None),
            "cands": ((("Button", "X", None), top),), "logged_route": route, "logged_reason": "ok",
            "oracle_ok": ok}


@pytest.mark.parametrize("screen,step", [
    ("list", "Tap the 'Add item' button"),
    ("list", "Tap 'Delete' in the 'Eggs' row"),
    ("settings", "Tap the 'Show completed' switch"),
    ("detail", "Tap the 'Mark as done' button"),
])
def test_accepted_matches_engine_router(screen, step):
    snap = parse_page_source((PS / "baseline" / f"{screen}.xml").read_text(encoding="utf-8"))
    res = resolve(snap, parse_step(step))
    top = res.top.score if res.top else None
    sec = res.second.score if res.second else None
    for tau in (0.5, 0.66, 0.8, 0.95, 1.0):
        for delta in (0.0, 0.09, 0.2, 0.5):
            expect = route(res, RouterConfig(threshold=tau, margin=delta)).route == "structured"
            assert s.accepted(top, sec, tau, delta) == expect


def test_accepted_edge_cases():
    assert not s.accepted(None, None, 0.5, 0.0)          # no_match
    assert not s.accepted(0.0, None, 0.0, 0.0)           # incompatible state / type gate
    assert s.accepted(0.7, None, 0.66, 0.09)             # no runner-up: margin not checked
    assert not s.accepted(0.7, 0.65, 0.66, 0.09)
    assert s.accepted(0.66, 0.57, 0.66, 0.09)            # boundaries are inclusive (>=)


def test_threshold_grid_counts():
    u = pd.DataFrame([_row("a", "baseline", 0, 0.95, 0.10, True), _row("a", "baseline", 1, 0.70, 0.65, True),
                      _row("b", "baseline", 0, 0.60, None, False)])
    u["reps"] = 3
    g = s.threshold_grid(u).set_index(["tau", "delta"])
    fz = g.loc[(0.66, 0.09)]
    assert fz.accepted_steps == 1 and fz.precision == 1.0 and fz.route_changes == 0
    low = g.loc[(0.5, 0.0)]
    assert low.accepted_steps == 3 and low.wrong_accepted == 1 and low.route_changes == 2
    assert low.route_changes_runs == 6
    assert len(g) == len(s.TAUS) * len(s.DELTAS)


def test_threshold_grid_is_deterministic():
    rng = np.random.default_rng(1)
    rows = [_row("a", "baseline", i, float(t), float(t - m), bool(o))
            for i, (t, m, o) in enumerate(zip(rng.random(20), rng.random(20) * 0.3, rng.random(20) > 0.2))]
    u = pd.DataFrame(rows); u["reps"] = 1
    pd.testing.assert_frame_equal(s.threshold_grid(u), s.threshold_grid(u))


def test_unique_steps_flags_disagreeing_repetitions():
    st = pd.DataFrame([_row("a", "baseline", 0, 0.9, 0.1, True, rep=1), _row("a", "baseline", 0, 0.9, 0.1, True, rep=2),
                       _row("b", "baseline", 0, 0.9, 0.1, True, rep=1), _row("b", "baseline", 0, 0.9, 0.1, False, rep=2)])
    u, bad = s.unique_steps(st)
    assert len(u) == 2 and list(u.reps) == [2, 2]
    assert bad == [("b", "baseline", 0)]


def test_simplex_grid():
    pts = s.simplex(0.05)
    assert len(pts) == 231
    assert all(abs(sum(p) - 1) < 1e-9 and min(p) >= 0 for p in pts)
    assert (0.6, 0.25, 0.15) in pts                       # the frozen weights lie on the grid


def test_variants_leave_frozen_default_untouched():
    names = [n for _, n, _ in s.variants()]
    assert names[0] == "frozen" and len(names) == len(set(names))
    assert s.variants()[0][2] == ResolverConfig()
    assert ResolverConfig().field_weights["label"] == 1.0  # replace() must not mutate the default


def test_screen_file_paths():
    tb = load_scenario(ROOT / "benchmark" / "scenarios" / "tb-05.yaml")
    su = load_scenario(ROOT / "benchmark" / "scenarios" / "su-03.yaml")
    assert s.screen_file(PS, tb, "baseline", "list") == PS / "baseline" / "list.xml"
    assert s.screen_file(PS, tb, "perturbed", "list") == PS / "tb05_duplicate_delete" / "list.xml"
    assert s.screen_file(PS, su, "perturbed", "new_syncup") == \
        PS / "syncups" / "su03_notes_section_inserted" / "new_syncup.xml"
    assert s.screen_file(PS, su, "baseline", "list").exists()


def test_b1_reproduces_logged_routes_on_formal_log():
    u, _ = s.unique_steps(s.load_a11y_steps(ROOT / "experiments" / "raw" / "formal.jsonl"))
    rec = [s.accepted(s._n(t), s._n(x), s.FROZEN_TAU, s.FROZEN_DELTA) for t, x in zip(u.top_score, u.second_score)]
    assert len(u) == 150
    assert rec == list(u.logged_route == "structured")

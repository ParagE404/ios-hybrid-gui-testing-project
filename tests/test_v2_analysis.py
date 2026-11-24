# Origin: AI-scaffolded and rewritten by the author.
"""Tests for analysis/v2.py on synthetic logs (D-029)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import v2  # noqa: E402


def run(scn, cfg, cond, completed, rep=1, scroll=None, relax=False, steps=1):
    base = {"run_id": "r", "scenario": scn, "config": cfg, "condition": cond, "repetition": rep, "attempt": 0}
    st = []
    for i in range(steps):
        s = dict(base, event="step", step_index=i, executed=True, expect_ok=None, oracle_ok=completed,
                 route="structured", latency={"total_ms": 10.0})
        if scroll and i == steps - 1:
            s["scroll_to_find"] = [{"swipe": k + 1, "reason": "no_match"} for k in range(scroll)]
            s["latency"]["scroll_ms"] = 1500.0 * scroll
        if relax:
            s["candidate_set_relaxed"] = True
        st.append(s)
    end = dict(base, event="scenario_end", completed=completed, postconditions_ok=completed, total_ms=100.0,
               infrastructure_error=False, postconditions=[])
    return [dict(base, event="scenario_start")] + st + [end]


def write(tmp, name, recs):
    p = tmp / name
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    return p


def heldout_dir(tmp):
    d = tmp / "heldout"; d.mkdir()
    exp = {c: {"baseline": "complete", "perturbed": "complete"} for c in v2.ORDER}
    exp["a11y-v1"] = {"baseline": "fail at step 1", "perturbed": "fail at step 1"}
    (d / "h-01.yaml").write_text(json.dumps({"id": "h-01", "heldout": {"class": "below_fold", "expected": exp}}))
    return d


def test_heldout_cells_predictions_and_gains(tmp_path):
    recs = []
    for rep in (1, 2, 3):
        recs += run("h-01", "a11y", "baseline", False, rep)
        recs += run("h-01", "a11y-v2", "baseline", True, rep, scroll=2)
        recs += run("h-01", "hybrid", "baseline", True, rep)
        recs += run("h-01", "hybrid-v2", "baseline", rep != 3, rep, relax=True)   # disagreeing reps
    log = write(tmp_path, "h.jsonl", recs)
    preds = v2.load_predictions(heldout_dir(tmp_path))
    df = v2.run_table(v2.F.load_runs(log))
    assert set(df.config) == {"a11y-v1", "a11y-v2", "hybrid-v1", "hybrid-v2"}
    cells = v2.cell_table(df, preds).set_index("config")
    assert bool(cells.loc["a11y-v1", "prediction_met"])          # predicted fail, failed
    assert bool(cells.loc["a11y-v2", "prediction_met"])          # predicted complete, completed
    assert cells.loc["a11y-v2", "scroll_fired"] == 3
    assert not bool(cells.loc["hybrid-v2", "reps_agree"]) and not bool(cells.loc["hybrid-v2", "prediction_met"])
    assert cells.loc["hybrid-v2", "relax_fired"] == 3
    gl = v2.gained_lost(df)
    assert {(r.pair, r.change) for r in gl.itertuples()} == {("a11y-v1 -> a11y-v2", "gained"),
                                                             ("hybrid-v1 -> hybrid-v2", "lost")}
    assert df[df.config == "a11y-v2"].scroll_ms.iloc[0] == 3000.0


def test_regression_table_flags_motivating_scenarios(tmp_path):
    ref = run("su-07", "hybrid", "perturbed", False) + run("tb-01", "a11y", "baseline", True)
    reg = run("su-07", "hybrid-v2", "perturbed", True) + run("tb-01", "a11y-v2", "baseline", False)
    a = v2.run_table(v2.F.load_runs(write(tmp_path, "ref.jsonl", ref)))
    b = v2.run_table(v2.F.load_runs(write(tmp_path, "reg.jsonl", reg)))
    t = v2.regression_table(b, a).set_index("scenario")
    assert t.loc["su-07", "change"] == "gained" and bool(t.loc["su-07", "motivating"])
    assert t.loc["tb-01", "change"] == "lost" and not bool(t.loc["tb-01", "motivating"])


def test_main_writes_outputs(tmp_path):
    recs = run("h-01", "a11y", "baseline", False) + run("h-01", "a11y-v2", "baseline", True, scroll=1)
    log = write(tmp_path, "h.jsonl", recs)
    v2.main([str(log), "--heldout", str(heldout_dir(tmp_path)), "--out", str(tmp_path / "out")])
    md = (tmp_path / "out" / "v2.md").read_text()
    assert "cells matching the committed prediction: 2 of 2" in md
    assert (tmp_path / "out" / "fig_v2_heldout.png").exists()

"""Tests for analysis/faults.py (workstream A, D-028), on synthetic logs only."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import faults as F  # noqa: E402


def step(i, executed=True, expect=None, oracle=True, route="structured", idx=5, label="Save"):
    return {"event": "step", "step_index": i, "executed": executed, "expect_ok": expect, "oracle_ok": oracle,
            "route": route, "action": {"kind": "tap", "element_idx": idx} if executed else None,
            "candidates": [{"idx": idx, "label": label, "score": 0.9}]}


def run(scn, cfg, cond, steps, post_ok=True, post_msgs=("exists {'label_contains': 'Coffee'}: 1 found",),
        rep=1, run_id="r", attempt=0, completed=None, infra=False, engine_error=False):
    base = {"run_id": run_id, "scenario": scn, "config": cfg, "condition": cond, "repetition": rep,
            "attempt": attempt}
    lines = [dict(base, event="scenario_start")] + [dict(base, **s) for s in steps]
    end = dict(base, event="scenario_end", postconditions_ok=post_ok, postconditions=list(post_msgs),
               infrastructure_error=infra, steps_run=len(steps),
               completed=post_ok and all(s["executed"] for s in steps) if completed is None else completed)
    if engine_error:
        end["engine_error"] = True
    return lines + [end]


def write(tmp, name, records):
    p = tmp / name
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return p


FAULT = {"class": "lure", "base_scenario": "tb-01", "fault_step": 3,
         "expected": {c: {"baseline": "detection at postcondition", "perturbed": "fragility (masked) at step 0"}
                      for c in ("scripted", "a11y", "hybrid")}}


def test_failed_postconditions_parsing():
    msgs = ["exists {'label': 'A'}: 0 found", "exists {'label': 'B'}: 2 found", "absent {'label': 'C'}: 1 found",
            "absent {'label': 'D'}: 0 found", "above {'a': 1} vs {'b': 2}: False", "above {'a': 1} vs {'b': 2}: True",
            "above {'a': 1} vs {'b': 2}: missing (0, 1)", "count {'x': 1}: expected 2, found 2",
            "count {'x': 1}: expected 2, found 3"]
    assert F.failed_postconditions(msgs) == [0, 2, 4, 6, 8]


def test_verdict_is_oracle_free():
    r = {"end": {"postconditions_ok": True}, "steps": [step(0), step(1, oracle=False)]}
    assert F.verdict(r) == ("pass",)                      # substitute tapped, checks hold -> passes
    r = {"end": {"postconditions_ok": True}, "steps": [step(0), step(1, expect=False), step(2, executed=False)]}
    assert F.verdict(r) == ("step", 1, "expect")
    r = {"end": {"postconditions_ok": True}, "steps": [step(0), step(1, executed=False)]}
    assert F.verdict(r) == ("step", 1, "not_executed")
    assert F.verdict({"end": {"postconditions_ok": False}, "steps": [step(0)]}) == ("post",)
    assert F.verdict({"end": {"engine_error": True}, "steps": []}) == ("engine_error",)


def test_classify_rules():
    ref_pass, ref_s0 = {("pass",)}, {("step", 0, "not_executed")}
    assert F.classify(("pass",), ref_pass, 3) == ("false_pass", "")
    assert F.classify(("step", 0, "not_executed"), ref_s0, 3) == ("fragility", "step 0 (not_executed)")
    assert F.classify(("post",), ref_pass, 3) == ("detection", "postcondition")
    assert F.classify(("step", 3, "not_executed"), ref_pass, 3) == ("detection", "fault step")
    assert F.classify(("step", 3, "expect"), ref_pass, 3) == ("detection", "fault step")
    assert F.classify(("step", 4, "not_executed"), ref_pass, 3) == ("detection", "later step")
    assert F.classify(("step", 1, "not_executed"), ref_pass, 3) == ("other", "step 1 (not_executed)")
    # same step as the reference but a different kind is not masked
    assert F.classify(("step", 0, "expect"), ref_s0, 0) == ("detection", "fault step")


def test_end_to_end_on_synthetic_logs(tmp_path):
    formal = (run("tb-01", "a11y", "baseline", [step(i) for i in range(4)]) +
              run("tb-01", "scripted", "perturbed", [step(0, executed=False)], post_ok=False))
    fault = (run("f-09", "a11y", "baseline", [step(0), step(1), step(2), step(3, oracle=False, label="Save draft")],
                 post_ok=False, post_msgs=["exists {'label_contains': 'Coffee'}: 0 found"]) +
             run("f-09", "scripted", "perturbed", [step(0, executed=False)], post_ok=False) +
             # an infrastructure attempt followed by a successful retry: only the retry counts
             run("f-09", "a11y", "perturbed", [step(0)], infra=True, attempt=0) +
             run("f-09", "a11y", "perturbed", [step(i) for i in range(4)], attempt=1))
    fr = F.load_runs(write(tmp_path, "formal.jsonl", formal))
    fa = F.load_runs(write(tmp_path, "faults.jsonl", fault))
    assert len(fa) == 3
    df = F.classify_runs(fa, fr, {"f-09": FAULT}).set_index(["config", "condition"])
    assert df.loc[("a11y", "baseline"), "class"] == "detection"
    assert df.loc[("a11y", "baseline"), "where"] == "postcondition"
    assert df.loc[("a11y", "baseline"), "substitutes"] == "s3 structured 'Save draft'"
    assert df.loc[("a11y", "baseline"), "failed_postconditions"] == "0"
    assert bool(df.loc[("a11y", "baseline"), "prediction_met"])
    assert df.loc[("scripted", "perturbed"), "class"] == "fragility"
    assert bool(df.loc[("scripted", "perturbed"), "prediction_met"])
    # no formal reference for a11y perturbed in this synthetic set, and it passes: a false pass
    assert df.loc[("a11y", "perturbed"), "class"] == "false_pass"
    assert not bool(df.loc[("a11y", "perturbed"), "prediction_met"])


def test_summary_and_scenario_tables(tmp_path):
    rows = []
    for scn, cls in (("f-01", "detection"), ("f-02", "false_pass"), ("f-03", "detection")):
        for rep in (1, 2, 3):
            rows.append({"scenario": scn, "fault_class": "behavioural", "config": "a11y", "condition": "baseline",
                         "repetition": rep, "class": cls, "where": "", "predicted": "detection",
                         "prediction_met": cls == "detection", "runner_completed": cls == "false_pass",
                         "substitute_steps": 0, "substitutes": ""})
    import pandas as pd
    df = pd.DataFrame(rows)
    t = F.summary_table(df, ["config", "condition"]).iloc[0]
    assert t.runs == 9 and t.false_pass == 3 and t.detection == 6
    assert abs(t.false_pass_rate - 1 / 3) < 1e-9 and t.false_pass_ci_low <= 1 / 3 <= t.false_pass_ci_high
    s = F.scenario_table(df)
    assert list(s["class"]) == ["detection", "false_pass", "detection"]
    df.loc[0, "class"] = "fragility"
    assert F.scenario_table(df)["class"].iloc[0] == "mixed:detection+fragility"


def test_fault_files_are_well_formed():
    faults = F.load_faults(ROOT / "benchmark" / "faults")
    assert sorted(faults) == [f"f-{i:02d}" for i in range(1, 13)]
    assert sum(f["class"] == "behavioural" for f in faults.values()) == 8
    assert sum(f["class"] == "lure" for f in faults.values()) == 4
    for f in faults.values():
        for cfg in ("scripted", "a11y", "hybrid"):
            for cond in ("baseline", "perturbed"):
                assert f["expected"][cfg][cond].split()[0] in ("detection", "fragility", "false")

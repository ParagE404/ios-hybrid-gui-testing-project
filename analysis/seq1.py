"""SEQ1 analysis: does MCP invocation preserve structured outcomes, and what latency does it add?

Inputs: engine telemetry (experiments/raw/seq1.jsonl, field 'mode' = direct | mcp), the per-call
timing log (experiments/raw/seq1_timing.jsonl) and, optionally, the formal log for a third
reference (the a11y runs of the same scenarios in the main experiment).

Outputs (analysis/out/):
  seq1_equivalence.csv  one row per (scenario, condition, repetition, step): the structured outcome
                        under each mode and whether they are identical
  seq1_overhead.csv     per-step orchestration overhead (client round trip minus the engine's own
                        step time) and response size, by mode
  seq1.md               summary: identical steps and runs, overhead median/p90/p95, paired
                        scenario wall-time difference with a Wilcoxon signed-rank test

Structured outcome of a step = (route, reason, chosen element's type/label/identifier, top score
and margin to 4 dp, action kind, oracle verdict, executed). Element indices are not compared:
they can shift between page-source snapshots without any change in the decision.

Usage:
    python analysis/seq1.py experiments/raw/seq1.jsonl experiments/raw/seq1_timing.jsonl
        [--formal experiments/raw/formal.jsonl] [--out analysis/out]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["scenario", "condition", "repetition"]


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def outcome(rec: dict) -> tuple:
    dec = rec.get("decision") or {}
    chosen = dec.get("chosen_idx")
    el = next((c for c in rec.get("candidates") or [] if c.get("idx") == chosen), None)
    top = (rec.get("candidates") or [{}])[0] if rec.get("candidates") else {}
    r4 = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 4)
    return (rec.get("route"), rec.get("reason"),
            (el or {}).get("type"), (el or {}).get("label"), (el or {}).get("identifier"),
            r4(top.get("score")), r4(dec.get("margin")),
            (rec.get("action") or {}).get("kind"), rec.get("oracle_ok"), rec.get("executed"))


def steps_by_mode(recs: list[dict], mode_of=lambda r: r.get("mode")) -> dict:
    """Last attempt wins, as in the formal analysis (an infrastructure retry replaces the run)."""
    out: dict = {}
    for r in recs:
        if r.get("event") == "step":
            out[(mode_of(r), r["scenario"], r["condition"], r["repetition"], r["step_index"])] = outcome(r)
    return out


def ends_by_mode(recs: list[dict], mode_of=lambda r: r.get("mode")) -> dict:
    out = {}
    for r in recs:
        if r.get("event") == "scenario_end" and not r.get("infrastructure_error"):
            out[(mode_of(r), r["scenario"], r["condition"], r["repetition"])] = bool(r["completed"])
    return out


def equivalence(engine: list[dict], formal: list[dict] | None) -> tuple[pd.DataFrame, dict]:
    st = steps_by_mode(engine)
    en = ends_by_mode(engine)
    scen = {k[1] for k in st}
    if formal:
        fa = [r for r in formal if r.get("config") == "a11y" and r.get("scenario") in scen]
        st.update(steps_by_mode(fa, lambda r: "formal"))
        en.update(ends_by_mode(fa, lambda r: "formal"))
    keys = sorted({k[1:] for k in st if k[0] in ("direct", "mcp")})
    rows = []
    for k in keys:
        d, m, f = st.get(("direct",) + k), st.get(("mcp",) + k), st.get(("formal",) + k)
        rows.append({"scenario": k[0], "condition": k[1], "repetition": k[2], "step": k[3],
                     "direct": d, "mcp": m, "formal": f, "mcp_eq_direct": d is not None and d == m,
                     "mcp_eq_formal": (m == f) if f is not None else None})
    df = pd.DataFrame(rows)
    run_keys = sorted({k[1:] for k in en if k[0] in ("direct", "mcp")})
    runs = [{"key": k, "direct": en.get(("direct",) + k), "mcp": en.get(("mcp",) + k),
             "formal": en.get(("formal",) + k)} for k in run_keys]
    paired = [r for r in runs if r["direct"] is not None and r["mcp"] is not None]
    # a run is equivalent when completion matches and every one of its steps matches
    step_ok = df.groupby(KEY)["mcp_eq_direct"].all().to_dict() if len(df) else {}
    summ = {
        "steps_compared": int(len(df)),
        "steps_identical_mcp_vs_direct": int(df["mcp_eq_direct"].sum()) if len(df) else 0,
        "steps_with_formal_reference": int(df["mcp_eq_formal"].notna().sum()) if len(df) else 0,
        "steps_identical_mcp_vs_formal": int((df["mcp_eq_formal"] == True).sum()) if len(df) else 0,  # noqa: E712
        "runs_paired": len(paired),
        "runs_same_completion": sum(r["direct"] == r["mcp"] for r in paired),
        "runs_fully_identical": sum(r["direct"] == r["mcp"] and step_ok.get(r["key"], False) for r in paired),
        "completed_direct": sum(bool(r["direct"]) for r in paired),
        "completed_mcp": sum(bool(r["mcp"]) for r in paired),
    }
    return df, summ


def overhead(timing: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    t = pd.DataFrame(timing)
    ends = t[t["call"] == "run_end"]
    bad = ends[ends["infrastructure_error"] == True]  # noqa: E712
    # keep only calls from the final (successful) attempt of each run: drop calls at or before a failed attempt
    steps = t[t["call"] == "run_step"].copy()
    if len(bad):
        last_bad = bad.groupby(["mode"] + KEY)["ts"].max()
        steps = steps.join(last_bad.rename("bad_ts"), on=["mode"] + KEY)
        steps = steps[steps["bad_ts"].isna() | (steps["ts"] > steps["bad_ts"])].drop(columns="bad_ts")
    steps["overhead_ms"] = steps["client_ms"] - steps["server_ms"]

    def q(s, p):
        return float(np.percentile(s, p)) if len(s) else float("nan")
    rows = []
    for mode, g in steps.groupby("mode"):
        rows.append({"mode": mode, "steps": len(g),
                     "overhead_median_ms": q(g.overhead_ms, 50), "overhead_p90_ms": q(g.overhead_ms, 90),
                     "overhead_p95_ms": q(g.overhead_ms, 95), "overhead_max_ms": float(g.overhead_ms.max()),
                     "step_client_median_ms": q(g.client_ms, 50), "step_engine_median_ms": q(g.server_ms, 50),
                     "response_chars_median": q(g.response_chars, 50)})
    table = pd.DataFrame(rows)

    good = ends[ends["infrastructure_error"] != True]  # noqa: E712
    wall = good.pivot_table(index=KEY, columns="mode", values="wall_ms", aggfunc="last").dropna()
    res = {"paired_runs": int(len(wall))}
    if len(wall) and {"direct", "mcp"} <= set(wall.columns):
        d = (wall["mcp"] - wall["direct"]) / 1000
        res.update({"wall_diff_median_s": float(d.median()), "wall_diff_mean_s": float(d.mean()),
                    "wall_direct_median_s": float(wall["direct"].median() / 1000),
                    "wall_mcp_median_s": float(wall["mcp"].median() / 1000)})
        if (d != 0).sum() >= 1:
            from scipy.stats import wilcoxon
            res["wilcoxon_p"] = float(wilcoxon(wall["mcp"], wall["direct"]).pvalue)
    return steps, table, res


def _md(df: pd.DataFrame) -> str:
    if df.empty:
        return "(none)"
    cols = list(df.columns)
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("engine_log")
    ap.add_argument("timing_log")
    ap.add_argument("--formal")
    ap.add_argument("--out", default="analysis/out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    eq, es = equivalence(_read(a.engine_log), _read(a.formal) if a.formal else None)
    steps, table, wall = overhead(_read(a.timing_log))
    eq.to_csv(out / "seq1_equivalence.csv", index=False)
    steps.to_csv(out / "seq1_overhead.csv", index=False)
    mism = eq[~eq["mcp_eq_direct"]] if len(eq) else eq
    lines = ["# SEQ1: direct vs MCP invocation (generated by analysis/seq1.py)", "",
             "## Structured outcomes", "", "```", json.dumps(es, indent=1), "```", "",
             "Steps where MCP differs from direct:", "", _md(mism[KEY + ["step", "direct", "mcp"]]) if len(mism) else "none", "",
             "## Orchestration overhead per step (client round trip minus engine step time)", "", _md(table), "",
             "## Scenario wall time, paired by scenario x condition x repetition (MCP minus direct)", "",
             "```", json.dumps(wall, indent=1), "```", ""]
    (out / "seq1.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
# SEQ1 protocol notes
# Results summary

"""Scenario-level tables and sensitivity checks for Chapter 4 (supplements analyse.py).

Why it exists:
  * In the formal data every scenario x config x condition cell is 0/3 or 3/3, so the three
    repetitions are not independent observations. Run-level McNemar (analyse.py, already a
    sensitivity analysis only) counts each scenario three times. This script repeats the
    test with one observation per scenario.
  * Two benchmark-construction defects were found in the formal data (D-025): tb-04's scripted
    locator does not match the live Settings tab, and su-06's second postcondition checks a
    row label that its own perturbation removes. The sensitivity table drops both scenarios.
  * scenario_outcomes.csv lists, per scenario, the pre-registered expected outcome next to
    what happened, with the first failing step, for the prediction-versus-outcome discussion.

Usage:
    python analysis/scenario_level.py experiments/raw/formal.jsonl [--out analysis/out]
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import pandas as pd
import yaml
from scipy.stats import binomtest

CONFIGS = ["scripted", "a11y", "hybrid"]
CONDITIONS = ["baseline", "perturbed"]
DEFECTIVE = ["tb-04", "su-06"]


def load(log: Path):
    runs, steps = [], []
    for line in log.read_text().splitlines():
        r = json.loads(line)
        if r["event"] == "scenario_end":
            runs.append(r)
        elif r["event"] == "step":
            steps.append(r)
    runs = pd.DataFrame(runs)
    runs = runs[~runs["infrastructure_error"].fillna(False).astype(bool)]
    # keep the last attempt of each run key (infrastructure retries)
    runs = runs.sort_values("attempt").groupby(["scenario", "condition", "config", "repetition"]).tail(1)
    return runs, steps


def scenario_matrix(runs: pd.DataFrame) -> pd.DataFrame:
    """Completions out of 3 per scenario x condition x config."""
    return runs.pivot_table(index="scenario", columns=["condition", "config"], values="completed",
                            aggfunc="sum").astype(int)


def determinism(m: pd.DataFrame) -> dict:
    vals = m.values.ravel()
    return {"cells": int(vals.size), "all_or_nothing_cells": int(((vals == 0) | (vals == 3)).sum())}


def scenario_mcnemar(m: pd.DataFrame, scenarios=None) -> pd.DataFrame:
    """Exact McNemar with one observation per scenario (completed in all 3 repetitions or not)."""
    out = []
    sub = m if scenarios is None else m.loc[scenarios]
    for cond in CONDITIONS:
        for a, b in [("hybrid", "a11y"), ("hybrid", "scripted"), ("a11y", "scripted")]:
            sa, sb = sub[(cond, a)] == 3, sub[(cond, b)] == 3
            nb, nc = int((sa & ~sb).sum()), int((~sa & sb).sum())
            p = 1.0 if nb + nc == 0 else float(binomtest(nb, nb + nc, 0.5).pvalue)
            out.append({"condition": cond, "comparison": f"{a} - {b}", "scenarios": len(sub),
                        "rate_a": round(sa.mean(), 3), "rate_b": round(sb.mean(), 3),
                        "diff_pp": round(100 * (sa.mean() - sb.mean()), 1),
                        "a_only": nb, "b_only": nc, "exact_p": round(p, 5)})
    return pd.DataFrame(out)


def first_failure(steps: list[dict], scenario: str, condition: str, config: str) -> str:
    rel = [s for s in steps if s["scenario"] == scenario and s["condition"] == condition
           and s["config"] == config and s["repetition"] == 1]
    rel.sort(key=lambda s: (s["attempt"], s["step_index"]))
    for s in rel:
        if s.get("oracle_ok") is False or s.get("executed") is False:
            rej = [a["validated"].get("reason") for a in s.get("vlm_attempts", [])
                   if a.get("validated", {}).get("kind") == "reject"]
            extra = f" vlm_rejects={rej}" if rej else ""
            return f"step {s['step_index']} ({s['step']}): {s['route']}/{s['reason']}{extra}"
    return ""


def outcomes(m: pd.DataFrame, runs: pd.DataFrame, steps: list[dict], scen_dir: Path) -> pd.DataFrame:
    meta = {}
    for f in sorted(scen_dir.glob("*.yaml")):
        d = yaml.safe_load(f.read_text())
        if not d.get("pilot"):
            meta[d["id"]] = d
    rows = []
    for sc in m.index:
        d = meta.get(sc, {})
        row = {"scenario": sc, "app": d.get("app"), "category": d.get("category"),
               "perturbation": (d.get("perturbation") or {}).get("kind")}
        for cond in CONDITIONS:
            for cfg in CONFIGS:
                row[f"{cond}_{cfg}"] = int(m.loc[sc, (cond, cfg)])
        for cfg in CONFIGS:
            fail = first_failure(steps, sc, "perturbed", cfg)
            if not fail and m.loc[sc, ("perturbed", cfg)] < 3:
                end = runs[(runs.scenario == sc) & (runs.condition == "perturbed") & (runs.config == cfg)]
                fail = "postcondition: " + "; ".join(end.iloc[0]["postconditions"] or [])
            row[f"perturbed_{cfg}_first_failure"] = fail
        row["baseline_scripted_first_failure"] = first_failure(steps, sc, "baseline", "scripted")
        row["expected_outcome"] = " ".join(str(d.get("expected_outcome", "")).split())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--scenarios", default="benchmark/scenarios")
    ap.add_argument("--out", default="analysis/out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    runs, steps = load(Path(a.log))
    m = scenario_matrix(runs)
    det = determinism(m)
    primary = scenario_mcnemar(m)
    keep = [s for s in m.index if s not in DEFECTIVE]
    sens = scenario_mcnemar(m, keep)
    oc = outcomes(m, runs, steps, Path(a.scenarios))
    primary.to_csv(out / "scenario_mcnemar.csv", index=False)
    sens.to_csv(out / "sensitivity_excl_defects.csv", index=False)
    oc.to_csv(out / "scenario_outcomes.csv", index=False)
    lines = ["# Scenario-level results (generated by analysis/scenario_level.py)", "",
             f"Determinism: {det['all_or_nothing_cells']} of {det['cells']} scenario x condition x config "
             "cells are 0/3 or 3/3.", "",
             "## Exact McNemar, one observation per scenario (all 24)", "", primary.to_markdown(index=False), "",
             f"## Sensitivity: excluding benchmark defects {DEFECTIVE}", "", sens.to_markdown(index=False), ""]
    (out / "scenario_level.md").write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"wrote scenario_mcnemar.csv, sensitivity_excl_defects.csv, scenario_outcomes.csv to {out}")


if __name__ == "__main__":
    main()

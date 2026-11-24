# Origin: AI-generated and reviewed by the author.
"""Seeded-fault study analysis (workstream A, D-028).

Classifies every fault run with the rule pre-registered in D-028:
  * verdict is ORACLE-FREE: a run passes if every step executed, no expect_after failed and all
    postconditions held (the step oracle is benchmark instrumentation, not part of a real test);
  * false pass         : the fault run passes;
  * fragility (masked) : it fails at the same first failure point and kind as the matching
                         fault-free formal tb run (same configuration and condition);
  * detection          : any other failure, split into at the fault step / at a later step /
                         at a postcondition;
  * other              : a failure before the fault step that the formal run did not have.
Substitute actions are executed targeted steps whose oracle is false (a11y and hybrid only).

Usage:
    python analysis/faults.py experiments/raw/faults.jsonl --reference experiments/raw/formal.jsonl \
        [--faults benchmark/faults] [--out analysis/out]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CONFIGS = ["scripted", "a11y", "hybrid"]
CONDITIONS = ["baseline", "perturbed"]
CLASSES = ["false_pass", "detection", "fragility", "other", "engine_error"]
SEED = 20261018
N_BOOT = 10_000


# ----------------------------------------------------------------------------- loading

def load_runs(path: str | Path) -> list[dict]:
    """Final non-infrastructure attempt of every run, with its step records."""
    steps, ends, starts = defaultdict(list), {}, {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        key = (r.get("run_id"), r.get("scenario"), r.get("condition"), r.get("config"),
               r.get("repetition"), r.get("attempt", 0))
        ev = r.get("event")
        if ev == "step":
            steps[key].append(r)
        elif ev == "scenario_end":
            ends[key] = r
        elif ev == "scenario_start":
            starts[key] = r
    best: dict = {}
    for key, e in ends.items():
        if e.get("infrastructure_error"):
            continue
        rk = key[1:5]
        if rk not in best or (key[5] or 0) >= (best[rk][0][5] or 0):
            best[rk] = (key, e)
    out = []
    for rk, (key, e) in sorted(best.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        out.append({"scenario": rk[0], "condition": rk[1], "config": rk[2], "repetition": rk[3],
                    "end": e, "steps": sorted(steps[key], key=lambda s: s["step_index"])})
    return out




def failed_postconditions(messages: list[str]) -> list[int]:
    """Indices of failing postconditions, recovered from matchers.check messages."""
    bad = []
    for i, m in enumerate(messages or []):
        kind = m.split(" ", 1)[0]
        if ": " not in m or kind not in ("exists", "absent", "count", "above"):
            continue
        tail = m.rsplit(": ", 1)[1]          # the status follows the LAST ": " (specs contain colons)
        n = re.match(r"(\d+) found", tail)
        if kind == "exists" and n and int(n.group(1)) == 0:
            bad.append(i)
        elif kind == "absent" and n and int(n.group(1)) > 0:
            bad.append(i)
        elif kind == "count" and "expected" in tail:
            exp, found = re.findall(r"\d+", tail)[:2]
            if exp != found:
                bad.append(i)
        elif kind == "above" and (tail.strip() == "False" or tail.startswith("missing")):
            bad.append(i)
    return bad


def verdict(run: dict) -> tuple:
    """Oracle-free first failure: ('pass',), ('step', i, 'not_executed'|'expect'), ('post',), ('engine_error',)."""
    e = run["end"]
    if e.get("engine_error"):
        return ("engine_error",)
    for s in run["steps"]:
        if not s.get("executed"):
            return ("step", s["step_index"], "not_executed")
        if s.get("expect_ok") is False:
            return ("step", s["step_index"], "expect")
    if not e.get("postconditions_ok"):
        return ("post",)
    return ("pass",)


def substitutes(run: dict) -> list[dict]:
    out = []
    for s in run["steps"]:
        if s.get("executed") and s.get("oracle_ok") is False:
            a = s.get("action") or {}
            label = next((c.get("label") for c in s.get("candidates") or [] if c.get("idx") == a.get("element_idx")), None)
            out.append({"step": s["step_index"], "route": s.get("route"), "label": label})
    return out


# ----------------------------------------------------------------------------- classification

def reference_verdicts(formal_runs: list[dict]) -> dict:
    ref = defaultdict(set)
    for r in formal_runs:
        ref[(r["scenario"], r["config"], r["condition"])].add(verdict(r))
    return ref


def classify(v: tuple, ref: set, fault_step: int) -> tuple[str, str]:
    """(class, where) for one fault run given its verdict and the formal reference verdicts."""
    if v[0] == "engine_error":
        return "engine_error", ""
    if v[0] == "pass":
        return "false_pass", ""
    if v in ref:
        return "fragility", _where(v)
    if v[0] == "step" and v[1] < fault_step:
        return "other", _where(v)
    if v[0] == "post":
        return "detection", "postcondition"
    return "detection", "fault step" if v[1] == fault_step else "later step"


def _where(v: tuple) -> str:
    return "postcondition" if v[0] == "post" else f"step {v[1]} ({v[2]})"


def load_faults(directory: str | Path) -> dict:
    out = {}
    for p in sorted(Path(directory).glob("*.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        out[d["id"]] = d["fault"]
    return out


def classify_runs(fault_runs: list[dict], formal_runs: list[dict], faults: dict) -> pd.DataFrame:
    ref = reference_verdicts(formal_runs)
    rows = []
    for r in fault_runs:
        f = faults[r["scenario"]]
        rv = ref.get((f["base_scenario"], r["config"], r["condition"]), set())
        v = verdict(r)
        cls, where = classify(v, rv, int(f["fault_step"]))
        subs = substitutes(r)
        predicted = f["expected"][r["config"]][r["condition"]]
        pred_cls = "false_pass" if predicted.startswith("false pass") else predicted.split()[0].strip(" (:")
        e = r["end"]
        rows.append({
            "scenario": r["scenario"], "fault_class": f["class"], "base": f["base_scenario"],
            "config": r["config"], "condition": r["condition"], "repetition": r["repetition"],
            "verdict": "/".join(map(str, v)), "reference": "|".join(sorted("/".join(map(str, x)) for x in rv)),
            "class": cls, "where": where, "predicted": pred_cls, "prediction_met": cls == pred_cls,
            "runner_completed": bool(e.get("completed")),
            "substitute_steps": len(subs),
            "substitutes": "; ".join(f"s{x['step']} {x['route']} '{x['label']}'" for x in subs),
            "failed_postconditions": ",".join(map(str, failed_postconditions(e.get("postconditions")))),
            "steps_run": e.get("steps_run"),
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- tables

def _boot(rates: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    if len(rates) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    b = rates[rng.integers(0, len(rates), size=(n_boot, len(rates)))].mean(axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def summary_table(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        row["runs"] = len(g)
        for c in CLASSES:
            row[c] = int((g["class"] == c).sum())
        row["substitute_runs"] = int((g.substitute_steps > 0).sum())
        row["runner_completed"] = int(g.runner_completed.sum())
        for c in ("false_pass", "detection"):
            rates = g.assign(x=g["class"] == c).groupby("scenario")["x"].mean().to_numpy(dtype=float)
            row[f"{c}_rate"] = float(rates.mean()) if len(rates) else np.nan
            row[f"{c}_ci_low"], row[f"{c}_ci_high"] = _boot(rates)
        rows.append(row)
    return pd.DataFrame(rows)


def scenario_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scn, cfg, cond), g in df.groupby(["scenario", "config", "condition"]):
        classes = sorted(set(g["class"]))
        rows.append({"scenario": scn, "fault_class": g.fault_class.iloc[0], "config": cfg, "condition": cond,
                     "class": classes[0] if len(classes) == 1 else "mixed:" + "+".join(classes),
                     "where": "|".join(sorted(set(g["where"]))), "predicted": g.predicted.iloc[0],
                     "prediction_met": bool(g.prediction_met.all()),
                     "substitutes": "|".join(sorted(set(x for x in g.substitutes if x)))})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- figure and report

def figure(tab: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "#fcfcfb", "pdf.fonttype": 42})
    colours = {"false_pass": "#b91c1c", "detection": "#1d4ed8", "fragility": "#a8a29e", "other": "#57534e",
               "engine_error": "#111111"}
    names = {"false_pass": "false pass", "detection": "detection", "fragility": "fragility (masked)",
             "other": "other failure", "engine_error": "engine error"}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True, constrained_layout=True)
    for ax, cls in zip(axes, ["behavioural", "lure"]):
        t = tab[tab.fault_class == cls].set_index(["config", "condition"])
        labels, bottoms = [], None
        xs = []
        for cfg in CONFIGS:
            for cond in CONDITIONS:
                xs.append((cfg, cond)); labels.append(f"{cfg}\n{cond}")
        x = np.arange(len(xs))
        bottom = np.zeros(len(xs))
        for c in CLASSES:
            vals = np.array([t.loc[k, c] / t.loc[k, "runs"] if k in t.index else 0 for k in xs], dtype=float)
            if vals.sum() == 0:
                continue
            ax.bar(x, vals, 0.7, bottom=bottom, color=colours[c], label=names[c], zorder=2)
            bottom += vals
        ax.set_xticks(x, labels, fontsize=8)
        ax.set_title(f"{cls} faults", fontsize=10)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.yaxis.grid(True, color="#e6e5e1"); ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("share of runs", fontsize=9)
    h, l = axes[0].get_legend_handles_labels()
    h2, l2 = axes[1].get_legend_handles_labels()
    seen = dict(zip(l + l2, h + h2))
    fig.legend(seen.values(), seen.keys(), loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=5, frameon=False,
               fontsize=8)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_faults.{ext}", dpi=200, bbox_inches="tight",
                    metadata={"CreationDate": None} if ext == "pdf" else None)
    plt.close(fig)


def _md(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df is None or df.empty:
        return "_(none)_\n"
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else format(v, floatfmt))
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    return "\n".join([head, "|" + "---|" * len(d.columns),
                      *["| " + " | ".join(map(str, r)) + " |" for r in d.itertuples(index=False)]]) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--reference", default="experiments/raw/formal.jsonl")
    ap.add_argument("--faults", default="benchmark/faults")
    ap.add_argument("--out", default="analysis/out")
    ap.add_argument("--prefix", default="faults", help="output name prefix (never overwrite other outputs)")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    faults = load_faults(a.faults)
    fault_runs = [r for r in load_runs(a.log) if r["scenario"] in faults]
    formal = [r for r in load_runs(a.reference) if str(r["scenario"]).startswith("tb-")]
    df = classify_runs(fault_runs, formal, faults)
    by_cfg = summary_table(df, ["config", "condition"])
    by_cls = summary_table(df, ["fault_class", "config", "condition"])
    scn = scenario_table(df)
    planned = len(faults) * len(CONFIGS) * len(CONDITIONS)
    df.to_csv(out / f"{a.prefix}_runs.csv", index=False)
    by_cfg.to_csv(out / f"{a.prefix}_by_config.csv", index=False)
    by_cls.to_csv(out / f"{a.prefix}_by_class.csv", index=False)
    scn.to_csv(out / f"{a.prefix}_scenarios.csv", index=False)
    figure(by_cls, out)

    fp = df[df["class"] == "false_pass"][["scenario", "fault_class", "config", "condition", "repetition",
                                           "substitutes", "verdict"]]
    other = df[df["class"].isin(["other", "engine_error"])][["scenario", "config", "condition", "repetition",
                                                             "verdict", "reference"]]
    misses = scn[~scn.prediction_met][["scenario", "config", "condition", "class", "where", "predicted"]]
    md = [
        f"# Seeded-fault study (generated)\n\nLog: {a.log}; reference: {a.reference}. Rule: D-028.\n\n",
        f"- runs analysed: {len(df)} (planned {planned * 3}); scenario x config x condition cells: {len(scn)} "
        f"(planned {planned})\n",
        f"- false passes: {int((df['class'] == 'false_pass').sum())}; detections: "
        f"{int((df['class'] == 'detection').sum())}; fragility (masked): {int((df['class'] == 'fragility').sum())}; "
        f"other: {int((df['class'] == 'other').sum())}; engine errors: {int((df['class'] == 'engine_error').sum())}\n",
        f"- runs with a substitute action (executed step, oracle false): {int((df.substitute_steps > 0).sum())}\n",
        f"- repetitions disagreeing within a cell: {int(scn['class'].str.startswith('mixed').sum())}\n",
        f"- cells matching the pre-registered prediction: {int(scn.prediction_met.sum())} of {len(scn)}\n\n",
        "## By configuration and condition (rates are scenario means; 95% scenario-cluster bootstrap)\n\n",
        _md(by_cfg), "\n## By fault class\n\n", _md(by_cls),
        "\n## Scenario level\n\n", _md(scn),
        "\n## False passes (each needs a one-line cause in the write-up)\n\n", _md(fp),
        "\n## Other failures and engine errors\n\n", _md(other),
        "\n## Cells that missed the prediction\n\n", _md(misses),
    ]
    (out / f"{a.prefix}.md").write_text("".join(md), encoding="utf-8")
    print("".join(md[:2]))


if __name__ == "__main__":
    main()

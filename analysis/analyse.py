"""Analysis of formal runs: tables and figures for Chapter 4.

Implements the analysis promised in the proposal ("Experiment and analysis"):
  * primary outcome: end-to-end scenario completion per configuration x condition
  * paired percentage-point differences between configurations with cluster-bootstrap
    95% CIs that resample SCENARIOS (runs of one scenario are not independent)
  * exact McNemar tests on paired run outcomes (sensitivity analysis only)
  * secondary: step success, recovery, routes, fallback frequency, VLM acceptance and
    rejection reasons, latency (median, p90, p95) with paired Wilcoxon tests at
    scenario level, model input/output size, failure categories
Statistical inference is exploratory; effect sizes and failure analysis come first
(Arcuri and Briand, 2011).

Usage:
    python analysis/analyse.py experiments/raw/formal.jsonl [--out analysis/out] [--include-pilot]

Bias rule D-018: do not run on formal data until all scenarios are written.
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

CONFIGS = ["scripted", "a11y", "hybrid"]
CONDITIONS = ["baseline", "perturbed"]
CATEGORY_NAMES = {1: "1 Identifier change", 2: "2 Hierarchy change", 3: "3 Duplicate/generic label",
                  4: "4 Weak metadata"}
SEED = 20261018
N_BOOT = 10_000


# ----------------------------------------------------------------------------- loading

def load(paths: list[str], include_pilot: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (runs, steps, notes). One row per final, non-infrastructure attempt."""
    starts, ends, steps = {}, [], []
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if not include_pilot and str(r.get("scenario", "")).startswith("p-"):
                continue
            key = (r.get("run_id"), r.get("scenario"), r.get("condition"), r.get("config"),
                   r.get("repetition"), r.get("attempt", 0))
            ev = r.get("event")
            if ev == "scenario_start":
                starts[key] = r
            elif ev == "scenario_end":
                ends.append((key, r))
            elif ev == "step":
                steps.append((key, r))

    rows, infra, engine = {}, 0, 0
    for key, r in ends:
        if r.get("infrastructure_error"):
            infra += 1
            continue
        engine += bool(r.get("engine_error"))
        run_key = key[1:5]
        prev = rows.get(run_key)
        if prev is None or (key[5] or 0) >= (prev["attempt"] or 0):
            st = starts.get(key, {})
            rows[run_key] = {
                "run_id": key[0], "scenario": key[1], "condition": key[2], "config": key[3],
                "repetition": key[4], "attempt": key[5], "app": r.get("app"),
                "category": st.get("category"), "perturbation_kind": st.get("perturbation_kind"),
                "completed": bool(r.get("completed")), "postconditions_ok": bool(r.get("postconditions_ok")),
                "engine_error": bool(r.get("engine_error")), "steps_run": r.get("steps_run"),
                "total_ms": r.get("total_ms"),
            }
    runs = pd.DataFrame(rows.values())
    kept = {(r["run_id"], r["scenario"], r["condition"], r["config"], r["repetition"], r["attempt"])
            for r in rows.values()}

    srows = []
    for key, r in steps:
        if key not in kept:
            continue
        lat = r.get("latency") or {}
        cands = r.get("candidates") or []
        attempts = r.get("vlm_attempts") or []
        vlm_calls = [a for a in attempts if "vlm" in a]
        srows.append({
            "scenario": key[1], "condition": key[2], "config": key[3], "repetition": key[4],
            "step_index": r.get("step_index"), "action_type": r.get("action_type"),
            "route": r.get("route"), "reason": r.get("reason"), "executed": bool(r.get("executed")),
            "oracle_ok": r.get("oracle_ok"), "expect_ok": r.get("expect_ok"),
            "top_score": cands[0]["score"] if cands else None,
            "margin": (r.get("decision") or {}).get("margin"),
            "snapshot_ms": lat.get("snapshot_ms"), "resolution_ms": lat.get("resolution_ms"),
            "execute_ms": lat.get("execute_ms"), "step_total_ms": lat.get("total_ms"),
            "vlm_calls": len(vlm_calls), "vlm_errors": len(attempts) - len(vlm_calls),
            "vlm_ms": float(sum(lat.get("vlm_ms") or [])),
            "vlm_accepted": any(a.get("validated", {}).get("kind") not in (None, "reject") for a in vlm_calls),
            "vlm_reject_reasons": "|".join(a["validated"].get("reason", "") for a in vlm_calls
                                           if a.get("validated", {}).get("kind") == "reject"),
            "vlm_input_chars": sum(a["vlm"].get("input_chars", 0) for a in vlm_calls),
            "vlm_image_bytes": sum(a["vlm"].get("image_bytes", 0) for a in vlm_calls),
            "vlm_output_chars": sum(a["vlm"].get("output_chars", 0) for a in vlm_calls),
            "snapshot_chars": r.get("snapshot_chars"),
            "execution_error": (r.get("execution_error") or {}).get("type"),
        })
    stp = pd.DataFrame(srows)
    if not stp.empty:
        stp["targeted"] = stp["action_type"].isin(["tap", "type_text"])
        stp["success"] = stp["executed"] & (stp["oracle_ok"] != False) & (stp["expect_ok"] != False)  # noqa: E712
    notes = {"infrastructure_excluded_attempts": infra, "engine_error_runs": engine,
             "runs": len(runs), "steps": len(stp)}
    return runs, stp, notes


# ----------------------------------------------------------------------------- statistics

def completion_table(runs: pd.DataFrame) -> pd.DataFrame:
    g = runs.groupby(["config", "condition"])["completed"]
    t = pd.DataFrame({"runs": g.size(), "completed": g.sum()}).reset_index()
    t["rate"] = t["completed"] / t["runs"]
    lo, hi = [], []
    for _, row in t.iterrows():
        sub = runs[(runs.config == row.config) & (runs.condition == row.condition)]
        ci = cluster_bootstrap_rate(sub)
        lo.append(ci[0]); hi.append(ci[1])
    t["ci_low"], t["ci_high"] = lo, hi
    return t


def _scenario_rates(runs: pd.DataFrame) -> pd.Series:
    return runs.groupby("scenario")["completed"].mean()


def cluster_bootstrap_rate(runs: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    rates = _scenario_rates(runs).to_numpy()
    if len(rates) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(rates), size=(n_boot, len(rates)))
    boots = rates[idx].mean(axis=1)
    return (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))


def paired_differences(runs: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Scenario-level paired differences in completion rate (percentage points), A minus B."""
    out = []
    rng = np.random.default_rng(seed)
    for cond in CONDITIONS:
        sub = runs[runs.condition == cond]
        piv = sub.groupby(["scenario", "config"])["completed"].mean().unstack("config")
        for a, b in [("hybrid", "a11y"), ("hybrid", "scripted"), ("a11y", "scripted")]:
            if a not in piv or b not in piv:
                continue
            d = (piv[a] - piv[b]).dropna().to_numpy()
            if len(d) == 0:
                continue
            idx = rng.integers(0, len(d), size=(n_boot, len(d)))
            boots = d[idx].mean(axis=1)
            mc = mcnemar_exact(sub, a, b)
            out.append({"condition": cond, "comparison": f"{a} - {b}", "scenarios": len(d),
                        "diff_pp": 100 * d.mean(),
                        "ci_low_pp": 100 * float(np.percentile(boots, 2.5)),
                        "ci_high_pp": 100 * float(np.percentile(boots, 97.5)),
                        "mcnemar_b": mc["b"], "mcnemar_c": mc["c"], "mcnemar_p": mc["p"]})
    return pd.DataFrame(out)


def mcnemar_exact(runs: pd.DataFrame, a: str, b: str) -> dict:
    """Exact McNemar on runs paired by (scenario, repetition). b: a succeeds, b fails; c: reverse."""
    from scipy.stats import binomtest
    piv = runs.pivot_table(index=["scenario", "repetition"], columns="config", values="completed",
                           aggfunc="first")
    if a not in piv or b not in piv:
        return {"b": None, "c": None, "p": None}
    pair = piv[[a, b]].dropna().astype(bool)
    nb = int((pair[a] & ~pair[b]).sum())
    nc = int((~pair[a] & pair[b]).sum())
    p = 1.0 if nb + nc == 0 else float(binomtest(nb, nb + nc, 0.5).pvalue)
    return {"b": nb, "c": nc, "p": p}


def category_table(runs: pd.DataFrame) -> pd.DataFrame:
    sub = runs[runs.condition == "perturbed"].copy()
    sub["category_name"] = sub["category"].map(CATEGORY_NAMES)
    g = sub.groupby(["category_name", "config"])["completed"]
    t = pd.DataFrame({"runs": g.size(), "completed": g.sum()}).reset_index()
    t["rate"] = t["completed"] / t["runs"]
    return t


def recovery_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Two recovery views per configuration.
    retention: perturbed completion among (scenario, rep) pairs the SAME config completed at baseline.
    recovery_after_scripted_break: perturbed completion among (scenario, rep) where scripted failed perturbed."""
    piv = runs.pivot_table(index=["scenario", "repetition"], columns=["config", "condition"],
                           values="completed", aggfunc="first")
    out = []
    for cfg in CONFIGS:
        if (cfg, "baseline") not in piv or (cfg, "perturbed") not in piv:
            continue
        base_ok = piv[(cfg, "baseline")] == True  # noqa: E712
        ret = piv.loc[base_ok, (cfg, "perturbed")].dropna()
        row = {"config": cfg, "retention_n": len(ret), "retention_rate": float(ret.mean()) if len(ret) else np.nan}
        if ("scripted", "perturbed") in piv:
            broke = piv[("scripted", "perturbed")] == False  # noqa: E712
            rec = piv.loc[broke, (cfg, "perturbed")].dropna()
            row.update({"after_scripted_break_n": len(rec),
                        "after_scripted_break_rate": float(rec.mean()) if len(rec) else np.nan})
        out.append(row)
    return pd.DataFrame(out)


def step_table(steps: pd.DataFrame) -> pd.DataFrame:
    t = steps[steps.targeted].groupby(["config", "condition"]).agg(
        target_steps=("success", "size"), step_success=("success", "mean"),
        structured=("route", lambda r: (r == "structured").mean()),
        vlm_route=("route", lambda r: (r == "vlm").mean()),
        fallback_needed=("route", lambda r: (~r.isin(["structured", "scripted"])).mean()),
    ).reset_index()
    return t


def route_reason_table(steps: pd.DataFrame) -> pd.DataFrame:
    s = steps[steps.targeted & steps.config.isin(["a11y", "hybrid"])]
    return s.groupby(["config", "condition", "route", "reason"]).size().rename("steps").reset_index()


def vlm_table(steps: pd.DataFrame) -> pd.DataFrame:
    s = steps[steps.vlm_calls > 0]
    if s.empty:
        return pd.DataFrame()
    return s.groupby("condition").agg(
        steps_with_vlm=("vlm_calls", "size"), vlm_calls=("vlm_calls", "sum"),
        accepted=("vlm_accepted", "sum"),
        accepted_and_correct=("oracle_ok", lambda o: int(((o == True) & s.loc[o.index, "vlm_accepted"]).sum())),  # noqa: E712
        median_call_ms=("vlm_ms", lambda m: float((m / s.loc[m.index, "vlm_calls"]).median())),
        mean_image_kb=("vlm_image_bytes", lambda b: float((b / s.loc[b.index, "vlm_calls"]).mean() / 1024)),
        mean_input_chars=("vlm_input_chars", lambda c: float((c / s.loc[c.index, "vlm_calls"]).mean())),
        mean_output_chars=("vlm_output_chars", lambda c: float((c / s.loc[c.index, "vlm_calls"]).mean())),
    ).reset_index()


def vlm_reject_reasons(steps: pd.DataFrame) -> pd.DataFrame:
    rs = steps.loc[steps.vlm_reject_reasons.fillna("") != "", "vlm_reject_reasons"].str.split("|").explode()
    return rs.value_counts().rename_axis("reason").rename("rejections").reset_index()


def _q(x: pd.Series, q: float) -> float:
    x = x.dropna()
    return float(np.percentile(x, q)) if len(x) else np.nan


def latency_table(runs: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (cfg, cond), s in steps.groupby(["config", "condition"]):
        r = runs[(runs.config == cfg) & (runs.condition == cond)]
        out.append({"config": cfg, "condition": cond,
                    "step_median_ms": _q(s.step_total_ms, 50), "step_p90_ms": _q(s.step_total_ms, 90),
                    "step_p95_ms": _q(s.step_total_ms, 95),
                    "snapshot_median_ms": _q(s.snapshot_ms, 50), "resolution_median_ms": _q(s.resolution_ms, 50),
                    "vlm_total_s": float(s.vlm_ms.sum() / 1000),
                    "scenario_median_s": _q(r.total_ms, 50) / 1000, "scenario_p90_s": _q(r.total_ms, 90) / 1000,
                    "scenario_p95_s": _q(r.total_ms, 95) / 1000})
    return pd.DataFrame(out)


def latency_tests(runs: pd.DataFrame) -> pd.DataFrame:
    """Paired Wilcoxon signed-rank on per-scenario median run time (exploratory)."""
    from scipy.stats import wilcoxon
    out = []
    for cond in CONDITIONS:
        piv = runs[runs.condition == cond].groupby(["scenario", "config"])["total_ms"].median().unstack("config")
        for a, b in [("hybrid", "a11y"), ("hybrid", "scripted"), ("a11y", "scripted")]:
            if a not in piv or b not in piv:
                continue
            d = (piv[a] - piv[b]).dropna()
            if len(d) < 2 or (d == 0).all():
                p = np.nan
            else:
                p = float(wilcoxon(d, zero_method="wilcox").pvalue)
            out.append({"condition": cond, "comparison": f"{a} - {b}", "scenarios": len(d),
                        "median_diff_s": float(d.median() / 1000) if len(d) else np.nan, "wilcoxon_p": p})
    return pd.DataFrame(out)


def failure_table(runs: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    """Classify each failed run by its first failing step (or the postconditions)."""
    out = []
    failed = runs[~runs.completed]
    for _, r in failed.iterrows():
        s = steps[(steps.scenario == r.scenario) & (steps.condition == r.condition) &
                  (steps.config == r.config) & (steps.repetition == r.repetition)].sort_values("step_index")
        bad = s[~s.success]
        if r.engine_error:
            cat = "engine_error"
        elif bad.empty:
            cat = "postcondition_failed"
        else:
            f = bad.iloc[0]
            if not f.executed:
                cat = {"locator_not_found": "scripted_locator_not_found",
                       "execution_error": "execution_error"}.get(f.reason, f"not_executed:{f.route}:{f.reason}")
            elif f.oracle_ok is not None and not pd.isna(f.oracle_ok) and not bool(f.oracle_ok):
                cat = f"wrong_target:{f.route}"
            else:
                cat = "expect_after_failed"
        out.append({"config": r.config, "condition": r.condition, "category": r.category, "failure": cat})
    df = pd.DataFrame(out)
    if df.empty:
        return df
    return df.groupby(["config", "condition", "failure"]).size().rename("runs").reset_index()


# ----------------------------------------------------------------------------- figures

PALETTE = {"scripted": "#2a78d6", "a11y": "#eb6834", "hybrid": "#1baf7a"}   # validated, light, slots 1-3
LABELS = {"scripted": "Scripted", "a11y": "Accessibility-only", "hybrid": "Hybrid"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _bars(ax, groups: list[str], values: dict, errs: dict | None, ylabel: str):
    n = len(CONFIGS)
    width = 0.8 / n
    x = np.arange(len(groups))
    for i, cfg in enumerate(CONFIGS):
        vals = np.array([values.get((cfg, g), np.nan) for g in groups], dtype=float)
        pos = x - 0.4 + width * (i + 0.5)
        ax.bar(pos, vals, width * 0.92, color=PALETTE[cfg], label=LABELS[cfg], zorder=2)
        if errs:
            lo = np.array([errs.get((cfg, g), (np.nan, np.nan))[0] for g in groups])
            hi = np.array([errs.get((cfg, g), (np.nan, np.nan))[1] for g in groups])
            ax.errorbar(pos, vals, yerr=[vals - lo, hi - vals], fmt="none", ecolor=INK2, elinewidth=1,
                        capsize=2, zorder=3)
        for px, v in zip(pos, vals):       # direct labels: relief for the low-contrast slot
            if not np.isnan(v):
                ax.text(px, v + 0.02, f"{v:.0%}", ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.set_xticks(x, groups)
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))


def figures(runs: pd.DataFrame, steps: pd.DataFrame, comp: pd.DataFrame, cat: pd.DataFrame, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": SURFACE})

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    _style(ax)
    vals = {(r.config, r.condition.capitalize()): r.rate for r in comp.itertuples()}
    errs = {(r.config, r.condition.capitalize()): (r.ci_low, r.ci_high) for r in comp.itertuples()}
    _bars(ax, [c.capitalize() for c in CONDITIONS], vals, errs, "Scenarios completed")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_completion.{ext}", dpi=200)
    plt.close(fig)

    if not cat.empty:
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        _style(ax)
        groups = sorted(cat.category_name.unique())
        vals = {(r.config, r.category_name): r.rate for r in cat.itertuples()}
        _bars(ax, groups, vals, None, "Perturbed scenarios completed")
        ax.set_xticks(range(len(groups)), [g.replace(" ", "\n", 1) for g in groups])
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(out / f"fig_category.{ext}", dpi=200)
        plt.close(fig)

    s = steps[steps.targeted & steps.step_total_ms.notna()]
    if not s.empty:
        fig, ax = plt.subplots(figsize=(6.4, 3.4))
        _style(ax)
        data = [s[(s.config == c) & (s.condition == k)].step_total_ms / 1000 for c in CONFIGS for k in CONDITIONS]
        pos = [i * 2.5 + j for i in range(len(CONFIGS)) for j in range(len(CONDITIONS))]
        bp = ax.boxplot(data, positions=pos, widths=0.7, patch_artist=True, showfliers=True,
                        medianprops={"color": INK, "linewidth": 1.2},
                        flierprops={"markersize": 3, "markeredgecolor": INK2},
                        whiskerprops={"color": INK2}, capprops={"color": INK2})
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(PALETTE[CONFIGS[i // len(CONDITIONS)]])
            patch.set_edgecolor(SURFACE)
        short = {"scripted": "Scripted", "a11y": "A11y-only", "hybrid": "Hybrid"}
        ax.set_xticks(pos, [f"{short[c]}\n{k}" for c in CONFIGS for k in CONDITIONS], fontsize=7.5)
        ax.set_yscale("log")
        ax.set_ylabel("Time per targeted step (s, log scale)", color=INK2, fontsize=9)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(out / f"fig_step_latency.{ext}", dpi=200)
        plt.close(fig)


# ----------------------------------------------------------------------------- report

def _md(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df is None or df.empty:
        return "_(no data)_\n"
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else format(v, floatfmt))
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "|" + "---|" * len(d.columns)
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in d.itertuples(index=False)]
    return "\n".join([head, sep, *rows]) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", default="analysis/out")
    ap.add_argument("--include-pilot", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    runs, steps, notes = load(a.logs, a.include_pilot)
    comp = completion_table(runs)
    diffs = paired_differences(runs)
    cat = category_table(runs)
    rec = recovery_table(runs)
    stp = step_table(steps)
    rr = route_reason_table(steps)
    vlm = vlm_table(steps)
    vrr = vlm_reject_reasons(steps)
    lat = latency_table(runs, steps)
    lt = latency_tests(runs)
    fail = failure_table(runs, steps)

    tables = {"completion": comp, "paired_differences": diffs, "category": cat, "recovery": rec,
              "steps": stp, "routes_reasons": rr, "vlm": vlm, "vlm_reject_reasons": vrr,
              "latency": lat, "latency_tests": lt, "failures": fail}
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    runs.to_csv(out / "runs.csv", index=False)
    steps.to_csv(out / "steps_long.csv", index=False)
    figures(runs, steps, comp, cat, out)

    md = [f"# Results summary (generated)\n\nLogs: {', '.join(a.logs)}  \nNotes: {notes}\n"]
    for name, df in tables.items():
        md.append(f"\n## {name}\n\n{_md(df)}")
    (out / "results.md").write_text("".join(md), encoding="utf-8")
    print(f"{notes}\nwrote {len(tables)} tables, figures and results.md to {out}")


if __name__ == "__main__":
    main()

"""Engine v2 evaluation (workstream C, D-029): held-out scenarios first, formal regression second.

Held-out (primary, exploratory): completion per configuration x condition (runner completion, as in the
formal experiment), comparison with the prediction committed in each scenario file, scenarios gained and
lost by v2 against v1, how often each fix fired, and the latency added by scrolling.

Regression (secondary): the 24 formal scenarios run with a11y-v2 and hybrid-v2, compared run by run with
the frozen a11y and hybrid results in the formal log. SU-03 and SU-07 motivated the fixes, so any gain
there is not held-out evidence.

Usage:
    python analysis/v2.py experiments/raw/heldout.jsonl [--regression experiments/raw/v2_regression.jsonl]
        [--reference experiments/raw/formal.jsonl] [--heldout benchmark/heldout] [--out analysis/out]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import faults as F  # noqa: E402  (shared log loader)

V1 = {"a11y": "a11y-v1", "hybrid": "hybrid-v1", "a11y-v2": "a11y-v2", "hybrid-v2": "hybrid-v2"}
ORDER = ["a11y-v1", "hybrid-v1", "a11y-v2", "hybrid-v2"]
MOTIVATING = {"su-03", "su-05", "su-07"}


def run_table(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for r in runs:
        steps = r["steps"]
        scroll = [s for s in steps if "scroll_to_find" in s]
        rows.append({
            "scenario": r["scenario"], "condition": r["condition"], "config": V1.get(r["config"], r["config"]),
            "repetition": r["repetition"], "completed": bool(r["end"].get("completed")),
            "engine_error": bool(r["end"].get("engine_error")),
            "first_failure": "/".join(map(str, F.verdict(r))),
            "routes": "|".join(str(s.get("route")) for s in steps),
            "scroll_fired": len(scroll) > 0,
            "scroll_swipes": sum(len(s["scroll_to_find"]) for s in scroll),
            "scroll_ms": sum((s.get("latency") or {}).get("scroll_ms", 0.0) for s in steps),
            "relax_fired": any(s.get("candidate_set_relaxed") for s in steps),
            "total_ms": r["end"].get("total_ms"),
        })
    return pd.DataFrame(rows)


def load_predictions(directory: str | Path) -> dict:
    out = {}
    for p in sorted(Path(directory).glob("*.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        h = d["heldout"]
        for cfg, conds in h["expected"].items():
            for cond, text in conds.items():
                out[(d["id"], cfg, cond)] = {"class": h["class"],
                                             "predicted_complete": text.strip().lower().startswith("complete"),
                                             "prediction": text}
    return out


def cell_table(df: pd.DataFrame, preds: dict | None = None) -> pd.DataFrame:
    rows = []
    for (scn, cfg, cond), g in df.groupby(["scenario", "config", "condition"]):
        row = {"scenario": scn, "config": cfg, "condition": cond, "runs": len(g),
               "completed": int(g.completed.sum()), "reps_agree": g.completed.nunique() == 1,
               "first_failure": "|".join(sorted(set(g.first_failure))),
               "scroll_fired": int(g.scroll_fired.sum()), "relax_fired": int(g.relax_fired.sum())}
        if preds is not None:
            p = preds.get((scn, cfg, cond), {})
            row["class"] = p.get("class")
            row["predicted_complete"] = p.get("predicted_complete")
            row["prediction_met"] = (p.get("predicted_complete") is not None and
                                     bool(g.completed.all()) == p["predicted_complete"] and row["reps_agree"])
        rows.append(row)
    return pd.DataFrame(rows)


def completion_by(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    t = df.groupby(by).agg(runs=("completed", "size"), completed=("completed", "sum")).reset_index()
    t["rate"] = t.completed / t.runs
    return t


def gained_lost(df: pd.DataFrame) -> pd.DataFrame:
    """Scenario x condition cells whose all-reps completion differs between v1 and v2 of the same route."""
    rows = []
    cells = df.groupby(["scenario", "condition", "config"]).completed.all().unstack("config")
    for v1, v2 in (("a11y-v1", "a11y-v2"), ("hybrid-v1", "hybrid-v2")):
        if v1 not in cells or v2 not in cells:
            continue
        for (scn, cond), r in cells[[v1, v2]].dropna().iterrows():
            if bool(r[v1]) != bool(r[v2]):
                rows.append({"pair": f"{v1} -> {v2}", "scenario": scn, "condition": cond,
                             "change": "gained" if r[v2] else "lost"})
    return pd.DataFrame(rows, columns=["pair", "scenario", "condition", "change"])


def regression_table(reg: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Per formal scenario x condition: frozen v1 completion vs v2 completion (all repetitions)."""
    rows = []
    for v1, v2 in (("a11y-v1", "a11y-v2"), ("hybrid-v1", "hybrid-v2")):
        a = ref[ref.config == v1].groupby(["scenario", "condition"]).completed.agg(["sum", "size"])
        b = reg[reg.config == v2].groupby(["scenario", "condition"]).completed.agg(["sum", "size"])
        for key in sorted(set(a.index) | set(b.index)):
            ra = a.loc[key] if key in a.index else None
            rb = b.loc[key] if key in b.index else None
            rows.append({"pair": f"{v1} -> {v2}", "scenario": key[0], "condition": key[1],
                         "v1_completed": None if ra is None else f"{int(ra['sum'])}/{int(ra['size'])}",
                         "v2_completed": None if rb is None else f"{int(rb['sum'])}/{int(rb['size'])}",
                         "change": ("" if ra is None or rb is None or (ra["sum"] / ra["size"]) == (rb["sum"] / rb["size"])
                                    else ("gained" if rb["sum"] / rb["size"] > ra["sum"] / ra["size"] else "lost")),
                         "motivating": key[0] in MOTIVATING})
    return pd.DataFrame(rows)


def figure(comp: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "#fcfcfb", "pdf.fonttype": 42})
    colours = {"a11y-v1": "#a8a29e", "a11y-v2": "#57534e", "hybrid-v1": "#93c5fd", "hybrid-v2": "#1d4ed8"}
    classes = [c for c in ["below_fold", "hidden_candidate", "control"] if c in set(comp["class"])]
    fig, ax = plt.subplots(figsize=(7.5, 3.4), constrained_layout=True)
    x = np.arange(len(classes))
    w = 0.8 / len(ORDER)
    for i, cfg in enumerate(ORDER):
        vals = [comp[(comp["class"] == c) & (comp.config == cfg)].rate.sum() for c in classes]
        pos = x - 0.4 + w * (i + 0.5)
        ax.bar(pos, vals, w * 0.92, color=colours[cfg], label=cfg, zorder=2)
        for px, v in zip(pos, vals):
            ax.text(px, v + 0.02, f"{v:.0%}", ha="center", fontsize=7.5)
    ax.set_xticks(x, [c.replace("_", " ") for c in classes])
    ax.set_ylim(0, 1.15)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("held-out completion", fontsize=9)
    ax.yaxis.grid(True, color="#e6e5e1"); ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_v2_heldout.{ext}", dpi=200, metadata={"CreationDate": None} if ext == "pdf" else None)
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
    ap.add_argument("heldout_log")
    ap.add_argument("--heldout", default="benchmark/heldout")
    ap.add_argument("--regression")
    ap.add_argument("--reference", default="experiments/raw/formal.jsonl")
    ap.add_argument("--out", default="analysis/out")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    preds = load_predictions(a.heldout)
    h = run_table(F.load_runs(a.heldout_log))
    h["class"] = [preds.get((s, c, d), {}).get("class") for s, c, d in zip(h.scenario, h.config, h.condition)]
    cells = cell_table(h, preds)
    comp = completion_by(h, ["class", "config"])
    comp_cond = completion_by(h, ["config", "condition"])
    gl = gained_lost(h)
    scroll = h[h.scroll_fired]
    h.to_csv(out / "v2_heldout_runs.csv", index=False)
    cells.to_csv(out / "v2_heldout_cells.csv", index=False)
    comp.to_csv(out / "v2_heldout_completion.csv", index=False)
    figure(comp, out)

    md = [f"# Engine v2 evaluation (generated, exploratory)\n\nHeld-out log: {a.heldout_log}. Rule: D-029.\n\n",
          "## Held-out scenarios (primary)\n\n",
          f"- runs: {len(h)}; engine errors: {int(h.engine_error.sum())}; cells: {len(cells)}; "
          f"cells whose repetitions disagree: {int((~cells.reps_agree).sum())}\n",
          f"- cells matching the committed prediction: {int(cells.prediction_met.sum())} of {len(cells)}\n",
          f"- runs where scroll_to_find fired: {int(h.scroll_fired.sum())}; where relax_candidate_set fired: "
          f"{int(h.relax_fired.sum())}\n",
          f"- added scrolling latency when it fired: median {scroll.scroll_ms.median() / 1000 if len(scroll) else 0:.1f} s, "
          f"max {scroll.scroll_ms.max() / 1000 if len(scroll) else 0:.1f} s over {len(scroll)} runs\n\n",
          "Completion by scenario class and configuration:\n\n", _md(comp),
          "\nCompletion by configuration and condition:\n\n", _md(comp_cond),
          "\nScenario cells gained or lost by v2 (all repetitions):\n\n", _md(gl),
          "\nCells (prediction from the scenario file, committed before v2 code):\n\n", _md(cells)]

    if a.regression:
        reg = run_table(F.load_runs(a.regression))
        ref = run_table([r for r in F.load_runs(a.reference) if r["config"] in ("a11y", "hybrid")])
        rt = regression_table(reg, ref)
        rt.to_csv(out / "v2_regression.csv", index=False)
        rc = completion_by(pd.concat([ref, reg]), ["config", "condition"])
        md += ["\n## Formal scenarios with v2 (secondary: regression check)\n\n",
               f"Regression log: {a.regression}; v1 reference: {a.reference}. SU-03, SU-05 and SU-07 motivated "
               "the fixes, so gains there are not held-out evidence.\n\n",
               f"- v2 runs: {len(reg)}; engine errors: {int(reg.engine_error.sum())}; scroll_to_find fired in "
               f"{int(reg.scroll_fired.sum())} runs, relax_candidate_set in {int(reg.relax_fired.sum())}\n",
               f"- cells lost by v2: {int((rt.change == 'lost').sum())}; gained: {int((rt.change == 'gained').sum())} "
               f"(of which on motivating scenarios: {int(((rt.change == 'gained') & rt.motivating).sum())})\n\n",
               _md(rc), "\nChanged cells:\n\n", _md(rt[rt.change != ""])]
    (out / "v2.md").write_text("".join(md), encoding="utf-8")
    print("".join(md[:6]))


if __name__ == "__main__":
    main()

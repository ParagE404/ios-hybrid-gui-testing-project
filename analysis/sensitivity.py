"""Sensitivity of the frozen router thresholds and resolver weights (workstream B, D-027).

Post-hoc analysis made after the formal experiment. It reads the formal log and the saved
page sources only; the engine is imported, never changed, and no live run is involved.

B1  Router thresholds, exact from the logs. In the a11y configuration the engine acts on
    the top candidate whatever the route (D-007, best_effort), so a step's logged
    oracle_ok says whether the top candidate was right. For every a11y targeted step the
    accept/fallback decision is recomputed for tau in 0.50..0.95 and delta in 0.00..0.30.

B2  Resolver weights, replayed offline on the saved page sources named by each step's
    `screen:` field. The replay is first validated against the log with the default
    ResolverConfig; steps whose replay disagrees (saved screen differs from the live one)
    are excluded and listed. Then component weights (simplex grid, step 0.05), attribute
    weights (one at a time, +/-0.2) and three ablations are applied.

Usage:
    python analysis/sensitivity.py experiments/raw/formal.jsonl [--out analysis/out]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from engine import matchers  # noqa: E402
from engine.normalise import parse_page_source  # noqa: E402
from engine.resolver import ResolverConfig, resolve  # noqa: E402
from engine.router import RouterConfig, route  # noqa: E402
from engine.scenario import load_scenario  # noqa: E402

FROZEN_TAU, FROZEN_DELTA = RouterConfig().threshold, RouterConfig().margin
TAUS = np.round(np.arange(0.50, 0.95 + 1e-9, 0.01), 2)
DELTAS = np.round(np.arange(0.00, 0.30 + 1e-9, 0.01), 2)
SCORE_TOL = 5e-4        # logged scores are rounded to 4 dp
STEP_KEY = ["scenario", "condition", "step_index"]


# ----------------------------------------------------------------------------- loading

def load_a11y_steps(path: str | Path) -> pd.DataFrame:
    """One row per logged a11y targeted step (tap / type_text), all repetitions."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("event") != "step" or r.get("config") != "a11y":
            continue
        if r.get("action_type") not in ("tap", "type_text"):
            continue
        if str(r.get("scenario", "")).startswith("p-"):
            continue
        c = r.get("candidates") or []
        rows.append({
            "scenario": r["scenario"], "app": r.get("app"), "condition": r["condition"],
            "repetition": r["repetition"], "step_index": r["step_index"], "step": r.get("step"),
            "n_cands": len(c), "top_score": c[0]["score"] if c else None,
            "second_score": c[1]["score"] if len(c) > 1 else None,
            "top": _ident(c[0]) if c else None,
            "cands": tuple((_ident(x), x["score"]) for x in c),
            "logged_route": (r.get("decision") or {}).get("route"),
            "logged_reason": (r.get("decision") or {}).get("reason"),
            "oracle_ok": bool(r.get("oracle_ok")),
        })
    return pd.DataFrame(rows)


def _ident(c: dict) -> tuple:
    return (c.get("type"), c.get("label"), c.get("identifier"))


def unique_steps(steps: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Collapse repetitions. Returns (one row per step, list of steps whose reps disagree)."""
    cols = ["cands", "logged_route", "oracle_ok"]
    bad = [k for k, g in steps.groupby(STEP_KEY) if len(g[cols].astype(str).drop_duplicates()) > 1]
    u = steps.sort_values(STEP_KEY + ["repetition"]).drop_duplicates(STEP_KEY).reset_index(drop=True)
    u["reps"] = steps.groupby(STEP_KEY).size().reindex(pd.MultiIndex.from_frame(u[STEP_KEY])).to_numpy()
    return u, bad


# ----------------------------------------------------------------------------- B1

def accepted(top: float | None, second: float | None, tau: float, delta: float) -> bool:
    """Router acceptance (engine/router.py) from top and runner-up scores."""
    if top is None or top == 0.0 or top < tau:
        return False
    if second is not None and top - second < delta:
        return False
    return True


def threshold_grid(u: pd.DataFrame) -> pd.DataFrame:
    top = u["top_score"].to_numpy(dtype=float, na_value=np.nan)
    sec = u["second_score"].to_numpy(dtype=float, na_value=np.nan)
    ok = u["oracle_ok"].to_numpy(dtype=bool)
    w = u["reps"].to_numpy(dtype=int)
    frozen = np.array([accepted(_n(t), _n(s), FROZEN_TAU, FROZEN_DELTA) for t, s in zip(top, sec)])
    out = []
    for tau in TAUS:
        for delta in DELTAS:
            acc = np.array([accepted(_n(t), _n(s), tau, delta) for t, s in zip(top, sec)])
            n_acc = int(acc.sum())
            out.append({
                "tau": float(tau), "delta": float(delta),
                "accepted_steps": n_acc, "coverage": n_acc / len(u),
                "precision": float(ok[acc].mean()) if n_acc else np.nan,
                "wrong_accepted": int((acc & ~ok).sum()),
                "route_changes": int((acc != frozen).sum()),
                "route_changes_runs": int(((acc != frozen) * w).sum()),
            })
    return pd.DataFrame(out)


def _n(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


def stable_region(grid: pd.DataFrame) -> dict:
    """Extent of the zero-change region, and the nearest change along each axis from the frozen point."""
    z = grid[grid.route_changes == 0]
    on_tau = grid[(grid.delta == FROZEN_DELTA)].sort_values("tau")
    on_delta = grid[(grid.tau == FROZEN_TAU)].sort_values("delta")

    def interval(line, col, frozen):
        vals = line[col].to_numpy(); ch = line.route_changes.to_numpy()
        i = int(np.argmin(np.abs(vals - frozen)))
        lo = i
        while lo > 0 and ch[lo - 1] == 0:
            lo -= 1
        hi = i
        while hi < len(vals) - 1 and ch[hi + 1] == 0:
            hi += 1
        return float(vals[lo]), float(vals[hi])

    return {"cells": len(grid), "zero_change_cells": len(z),
            "tau_interval_at_frozen_delta": interval(on_tau, "tau", FROZEN_TAU),
            "delta_interval_at_frozen_tau": interval(on_delta, "delta", FROZEN_DELTA),
            "zero_change_tau_range": (float(z.tau.min()), float(z.tau.max())) if len(z) else None,
            "zero_change_delta_range": (float(z.delta.min()), float(z.delta.max())) if len(z) else None}


# ----------------------------------------------------------------------------- B2 replay

def screen_file(pagesource: Path, scn, condition: str, screen: str) -> Path:
    folder = "baseline"
    if condition == "perturbed" and scn.perturbation and scn.perturbation.launch_args:
        folder = scn.perturbation.launch_args[-1]
    base = pagesource if scn.app == "testbed" else pagesource / scn.app
    return base / folder / f"{screen}.xml"


def _oracle_hit(snap, el, oracle) -> bool:
    related = [el] + [snap.elements[i] for i in el.ancestors] + [e for e in snap.elements if el.is_ancestor_of(e)]
    return any(matchers.matches(e, snap, oracle) for e in related)


class Replay:
    """Saved screens and scenario steps for the logged a11y steps (parsed once)."""

    def __init__(self, u: pd.DataFrame, scenario_dir: Path, pagesource: Path):
        self.items, self.missing = [], []
        scns = {p.stem: load_scenario(p) for p in sorted(Path(scenario_dir).glob("*.yaml"))}
        cache: dict[Path, object] = {}
        for row in u.itertuples(index=False):
            scn = scns[row.scenario]
            step = scn.steps[row.step_index]
            if not step.screen:
                self.missing.append((row.scenario, row.condition, row.step_index, "no screen"))
                continue
            f = screen_file(pagesource, scn, row.condition, step.screen)
            if not f.exists():
                self.missing.append((row.scenario, row.condition, row.step_index, f"missing {f.name}"))
                continue
            if f not in cache:
                cache[f] = parse_page_source(f.read_text(encoding="utf-8"))
            self.items.append({"row": row, "step": step, "snap": cache[f], "file": f,
                               "oracle": step.oracle_for(row.condition)})

    def evaluate(self, cfg: ResolverConfig) -> list[dict]:
        out = []
        for it in self.items:
            res = resolve(it["snap"], it["step"].intent, cfg)
            dec = route(res)
            top = res.top
            acts = top is not None and top.score > 0          # a11y best_effort acts on a valid top
            correct = bool(acts and it["oracle"] and _oracle_hit(it["snap"], top.element, it["oracle"]))
            out.append({"key": (it["row"].scenario, it["row"].condition, it["row"].step_index),
                        "top": None if top is None else (top.element.type, top.element.label, top.element.identifier),
                        "top_score": None if top is None else round(top.score, 4),
                        "cands": tuple(((c.element.type, c.element.label, c.element.identifier), round(c.score, 4))
                                       for c in res.candidates),
                        "route": dec.route, "reason": dec.reason, "correct": correct})
        return out


def validate_replay(rep: Replay, base: list[dict]) -> pd.DataFrame:
    rows = []
    for it, b in zip(rep.items, base):
        r = it["row"]
        ls, bs = _n(r.top_score), b["top_score"]
        same_top = b["top"] == r.top and ((ls is None and bs is None) or
                                          (ls is not None and bs is not None and abs(bs - ls) <= SCORE_TOL))
        same_list = len(b["cands"]) == len(r.cands) and all(
            x[0] == y[0] and abs(x[1] - y[1]) <= SCORE_TOL for x, y in zip(b["cands"], r.cands))
        same_route = b["route"] == r.logged_route and b["reason"] == r.logged_reason
        same_oracle = b["correct"] == r.oracle_ok
        rows.append({"scenario": r.scenario, "condition": r.condition, "step_index": r.step_index,
                     "screen": it["file"].relative_to(ROOT / "benchmark" / "pagesource").as_posix()
                     if it["file"].is_relative_to(ROOT / "benchmark" / "pagesource") else str(it["file"]),
                     "same_top": same_top, "same_candidates": same_list, "same_route": same_route,
                     "same_oracle": same_oracle,
                     "agree": same_top and same_route and same_oracle,
                     "logged_top": r.top, "replayed_top": b["top"],
                     "logged_score": r.top_score, "replayed_score": b["top_score"]})
    return pd.DataFrame(rows)


def simplex(step: float = 0.05) -> list[tuple[float, float, float]]:
    n = int(round(1 / step))
    return [(round(i * step, 2), round(j * step, 2), round((n - i - j) * step, 2))
            for i in range(n + 1) for j in range(n + 1 - i)]


def variants() -> list[tuple[str, str, ResolverConfig]]:
    d = ResolverConfig()
    v = [("frozen", "frozen", d)]
    for wt, wy, wc in simplex():
        if wt + wy == 0:            # score undefined for steps without a context phrase
            continue
        v.append(("simplex", f"text={wt:.2f} type={wy:.2f} context={wc:.2f}",
                  replace(d, w_text=wt, w_type=wy, w_context=wc)))
    for f in ("label", "identifier", "placeholder", "value"):
        for s in (-0.2, 0.2):
            fw = dict(d.field_weights); fw[f] = round(fw[f] + s, 2)
            v.append(("attribute", f"{f} {fw[f]:.2f} ({s:+.1f})", replace(d, field_weights=fw)))
    v.append(("ablation", "text only (type 0, context 0)", replace(d, w_type=0.0, w_context=0.0)))
    v.append(("ablation", "no context (context 0)", replace(d, w_context=0.0)))
    v.append(("ablation", "no type (type 0)", replace(d, w_type=0.0)))
    return v


def weight_sweep(rep: Replay, keep: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per variant: correct top candidates, route changes and scenario-pair changes vs frozen."""
    idx = [i for i, it in enumerate(rep.items)
           if (it["row"].scenario, it["row"].condition, it["row"].step_index) in keep]
    base = rep.evaluate(ResolverConfig())
    pairs = sorted({(rep.items[i]["row"].scenario, rep.items[i]["row"].condition) for i in idx})

    def pair_status(ev):
        st = {p: True for p in pairs}
        for i in idx:
            r = rep.items[i]["row"]
            st[(r.scenario, r.condition)] &= ev[i]["correct"]
        return st

    base_pairs = pair_status(base)
    rows, flips = [], []
    for kind, name, cfg in variants():
        ev = rep.evaluate(cfg)
        ps = pair_status(ev)
        changed_pairs = [p for p in pairs if ps[p] != base_pairs[p]]
        changed_steps = [i for i in idx if ev[i]["correct"] != base[i]["correct"]]
        rows.append({"kind": kind, "variant": name, "w_text": cfg.w_text, "w_type": cfg.w_type,
                     "w_context": cfg.w_context, "steps": len(idx),
                     "top_correct": sum(ev[i]["correct"] for i in idx),
                     "steps_gained": sum(ev[i]["correct"] and not base[i]["correct"] for i in changed_steps),
                     "steps_lost": sum(base[i]["correct"] and not ev[i]["correct"] for i in changed_steps),
                     "route_changes": sum(ev[i]["route"] != base[i]["route"] for i in idx),
                     "accepted": sum(ev[i]["route"] == "structured" for i in idx),
                     "scenario_pairs_changed": len(changed_pairs)})
        if kind != "simplex":
            for i in changed_steps:
                r = rep.items[i]["row"]
                flips.append({"variant": name, "scenario": r.scenario, "condition": r.condition,
                              "step_index": r.step_index, "frozen_correct": base[i]["correct"],
                              "variant_correct": ev[i]["correct"], "variant_top": ev[i]["top"]})
    return pd.DataFrame(rows), pd.DataFrame(flips)


def nearest_change(sx: pd.DataFrame) -> dict:
    d = ResolverConfig()
    s = sx.copy()
    s["dist"] = np.sqrt((s.w_text - d.w_text) ** 2 + (s.w_type - d.w_type) ** 2 + (s.w_context - d.w_context) ** 2)
    ch = s[(s.steps_gained + s.steps_lost) > 0]
    same = s[(s.steps_gained + s.steps_lost) == 0]
    interior = s[(s.w_text > 0) & (s.w_type > 0) & (s.w_context > 0)]
    return {"grid_points": len(s), "unchanged_points": len(same),
            "interior_points": len(interior),
            "interior_unchanged": int(((interior.steps_gained + interior.steps_lost) == 0).sum()),
            "max_gained": int(s.steps_gained.max()), "max_lost": int(s.steps_lost.max()),
            "nearest_change_distance": float(ch.dist.min()) if len(ch) else None,
            "nearest_change": ch.sort_values(["dist", "variant"]).iloc[0]["variant"] if len(ch) else None}


# ----------------------------------------------------------------------------- figures and report

def figures(grid: pd.DataFrame, sx: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "#fcfcfb",
                         "svg.hashsalt": "sensitivity", "pdf.fonttype": 42})
    ink2 = "#52514e"

    # B1 heatmaps: route changes, and precision on accepted steps
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), constrained_layout=True)
    for ax, col, title, cmap in (
            (axes[0], "route_changes", "Steps whose route differs from frozen", "Greys"),
            (axes[1], "precision", "Precision on accepted steps", "Blues")):
        m = grid.pivot(index="delta", columns="tau", values=col).to_numpy(dtype=float)
        im = ax.imshow(m, origin="lower", aspect="auto", cmap=cmap,
                       extent=[TAUS[0] - 0.005, TAUS[-1] + 0.005, DELTAS[0] - 0.005, DELTAS[-1] + 0.005])
        z = grid.pivot(index="delta", columns="tau", values="route_changes").to_numpy() == 0
        ax.contour(TAUS, DELTAS, z.astype(float), levels=[0.5], colors="#c2410c", linewidths=1.2)
        ax.plot(FROZEN_TAU, FROZEN_DELTA, marker="o", ms=6, mfc="white", mec="#c2410c", mew=1.5)
        ax.set_xlabel("threshold tau", color=ink2, fontsize=9)
        ax.set_ylabel("margin delta", color=ink2, fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.tick_params(colors=ink2, labelsize=8)
        fig.colorbar(im, ax=ax, shrink=0.85).ax.tick_params(labelsize=8)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_sensitivity_thresholds.{ext}", dpi=200, metadata={"CreationDate": None}
                    if ext == "pdf" else None)
    plt.close(fig)

    # B2 simplex: change in correct top candidates per weight triple
    s = sx[sx.kind == "simplex"]
    delta = (s.steps_gained - s.steps_lost).to_numpy()
    fig, ax = plt.subplots(figsize=(5.2, 4.2), constrained_layout=True)
    vmax = max(1, int(np.abs(delta).max()))
    sc = ax.scatter(s.w_text, s.w_type, c=delta, cmap="RdBu", vmin=-vmax, vmax=vmax, s=46,
                    edgecolors=np.where((s.steps_gained + s.steps_lost) > 0, "#0b0b0b", "#d0cfca"), linewidths=0.6)
    d = ResolverConfig()
    ax.plot(d.w_text, d.w_type, marker="*", ms=14, mfc="none", mec="#c2410c", mew=1.6)
    ax.set_xlabel("text weight (context = 1 - text - type)", color=ink2, fontsize=9)
    ax.set_ylabel("type weight", color=ink2, fontsize=9)
    ax.set_title("Correct top candidates vs frozen weights", fontsize=10)
    ax.tick_params(colors=ink2, labelsize=8)
    fig.colorbar(sc, ax=ax, shrink=0.85, label="steps gained minus lost").ax.tick_params(labelsize=8)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_sensitivity_weights.{ext}", dpi=200, metadata={"CreationDate": None}
                    if ext == "pdf" else None)
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
    ap.add_argument("--out", default="analysis/out")
    ap.add_argument("--scenarios", default=str(ROOT / "benchmark" / "scenarios"))
    ap.add_argument("--pagesource", default=str(ROOT / "benchmark" / "pagesource"))
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    steps = load_a11y_steps(a.log)
    u, rep_disagree = unique_steps(steps)

    # B1 ----------------------------------------------------------------
    frozen_recomputed = [accepted(_n(t), _n(s), FROZEN_TAU, FROZEN_DELTA)
                         for t, s in zip(u.top_score, u.second_score)]
    b1_agree = int(sum(f == (r == "structured") for f, r in zip(frozen_recomputed, u.logged_route)))
    grid = threshold_grid(u)
    region = stable_region(grid)
    fz = grid[(grid.tau == FROZEN_TAU) & (grid.delta == FROZEN_DELTA)].iloc[0]
    grid.to_csv(out / "sensitivity_thresholds.csv", index=False)
    near = u.assign(gap_tau=u.top_score - FROZEN_TAU,
                    gap_delta=(u.top_score - u.second_score).where(u.second_score.notna()) - FROZEN_DELTA)
    near = near[[c for c in STEP_KEY + ["top_score", "second_score", "gap_tau", "gap_delta", "logged_route",
                                         "oracle_ok"]]]
    near = near[(near.top_score > 0)].assign(
        nearest=lambda d: np.fmin(d.gap_tau.abs(), d.gap_delta.abs().fillna(np.inf))).sort_values("nearest").head(8)

    # B2 ----------------------------------------------------------------
    rep = Replay(u, Path(a.scenarios), Path(a.pagesource))
    base = rep.evaluate(ResolverConfig())
    val = validate_replay(rep, base)
    val.to_csv(out / "sensitivity_replay.csv", index=False)
    keep = {(r.scenario, r.condition, r.step_index) for r in val[val.agree].itertuples()}
    sweep, flips = weight_sweep(rep, keep)
    sweep.to_csv(out / "sensitivity_weights.csv", index=False)
    flips.to_csv(out / "sensitivity_weight_flips.csv", index=False)
    nc = nearest_change(sweep[sweep.kind == "simplex"])
    figures(grid, sweep, out)

    # report --------------------------------------------------------------
    excluded = val[~val.agree][["scenario", "condition", "step_index", "screen", "same_top", "same_route",
                                "same_oracle", "logged_top", "replayed_top"]]
    table = sweep[sweep.kind != "simplex"][["kind", "variant", "top_correct", "steps_gained", "steps_lost",
                                            "route_changes", "scenario_pairs_changed"]]
    md = [
        "# Sensitivity of frozen thresholds and resolver weights (generated)\n\n",
        f"Log: {a.log}. Post-hoc analysis after the formal experiment (D-027); engine unchanged.\n\n",
        "## Data\n\n",
        f"- a11y targeted step records: {len(steps)}; unique steps (scenario, condition, step): {len(u)}\n",
        f"- steps whose repetitions disagree: {len(rep_disagree)} {rep_disagree if rep_disagree else ''}\n",
        f"- top candidate correct (logged oracle_ok): {int(u.oracle_ok.sum())} of {len(u)}\n\n",
        "## B1 Router thresholds (exact, from logs)\n\n",
        f"- Recomputed route at frozen (tau {FROZEN_TAU}, delta {FROZEN_DELTA}) agrees with the logged route "
        f"for {b1_agree} of {len(u)} unique steps.\n",
        f"- Frozen cell: coverage {fz.coverage:.3f} ({int(fz.accepted_steps)} accepted), precision "
        f"{fz.precision:.3f}, wrong accepted {int(fz.wrong_accepted)}.\n",
        f"- Grid {len(TAUS)} x {len(DELTAS)} = {region['cells']} cells; cells where no step changes route: "
        f"{region['zero_change_cells']}.\n",
        f"- Holding delta at {FROZEN_DELTA}, tau can move over {region['tau_interval_at_frozen_delta']} "
        f"with no route change; holding tau at {FROZEN_TAU}, delta over {region['delta_interval_at_frozen_tau']}.\n",
        "- Wrong top candidate accepted at the frozen cell: "
        f"{u[np.array(frozen_recomputed) & ~u.oracle_ok.to_numpy()][STEP_KEY + ['top_score', 'top']].to_dict('records')}.\n",
        "- In the a11y configuration the route does not change the action (best_effort acts on the top "
        "candidate either way, D-007), so a route change here matters only for hybrid, where it decides "
        "whether the VLM is called.\n",
        f"- Over the whole grid: route changes up to {int(grid.route_changes.max())} steps; coverage "
        f"{grid.coverage.min():.3f} to {grid.coverage.max():.3f}.\n",
        f"- Over the whole grid: min precision on accepted steps {grid.precision.min():.3f}, "
        f"max wrong accepted {int(grid.wrong_accepted.max())}.\n\n",
        "Steps nearest the frozen boundary (gap = score minus threshold, or margin minus delta):\n\n",
        _md(near), "\n",
        "## B2 Resolver weights (replay on saved page sources)\n\n",
        f"- Replayable steps (screen saved): {len(rep.items)} of {len(u)}; no screen / missing file: "
        f"{len(rep.missing)} {rep.missing if rep.missing else ''}\n",
        f"- Replay agrees with log (same top candidate and score, same route and reason, same oracle "
        f"result): {int(val.agree.sum())} of {len(val)} ({val.agree.mean():.1%}); identical full candidate "
        f"list: {int(val.same_candidates.sum())}.\n",
        f"- Steps used for the weight sweep: {len(keep)}.\n\n",
        "Excluded steps (saved screen differs from the live one):\n\n", _md(excluded), "\n",
        f"Component-weight simplex (step 0.05, {nc['grid_points']} points, (0,0,1) skipped): "
        f"{nc['unchanged_points']} points give exactly the frozen set of correct top candidates; nearest point "
        f"that changes any step: {nc['nearest_change']} (Euclidean distance {nc['nearest_change_distance']:.3f}). "
        f"Interior points (every weight >= 0.05): {nc['interior_points']}, of which {nc['interior_unchanged']} "
        f"are unchanged{'; all changes lie on the edges where a weight is 0' if nc['interior_unchanged'] == nc['interior_points'] else ''}. Most steps gained "
        f"by any point: {nc['max_gained']}; most lost: {nc['max_lost']}.\n\n",
        "Attribute weights and ablations:\n\n", _md(table), "\n",
        "Steps that change under attribute or ablation variants:\n\n", _md(flips), "\n",
        "Caveats: the replay covers only steps the a11y run logged (a run stops at its first failed step), "
        "on one saved screen per step; scenario_pairs_changed counts (scenario, condition) pairs whose "
        "all-steps-correct status flips, which approximates but is not the same as scenario completion. "
        "The type and state gates are hard rules, not weights, and stay on in every variant.\n",
    ]
    (out / "sensitivity.md").write_text("".join(md), encoding="utf-8")
    print("".join(md))


if __name__ == "__main__":
    main()

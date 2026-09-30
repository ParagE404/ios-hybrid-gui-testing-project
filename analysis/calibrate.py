"""Calibrate the router threshold (tau) and margin (delta) on PILOT runs only (D-005).

Input: JSONL telemetry from pilot scenarios (ids starting "p-") run in the a11y
configuration, baseline and perturbed. In a11y the engine always acts on the top
candidate when it is valid (D-007 best_effort), so each step's oracle_ok tells us
whether the top candidate was right. That gives labelled (top score, margin, correct)
points.

Pre-registered selection rule (written 18 Oct 2026, before any pilot data existed):
  1. Search tau in [0.60, 0.95] and delta in [0.05, 0.30], step 0.01 (floors stop
     degenerate thresholds).
  2. A step is "accepted" when top >= tau and (top - second) >= delta.
  3. Keep only (tau, delta) with precision 1.0 on accepted steps (the structured
     route never takes a wrong action on the pilot set). If none exists, use the
     highest precision available and report it.
  4. Among those, keep the ones with maximum coverage (share of steps accepted).
  5. Choose the median tau of that tied set, then the median delta among points
     with that tau (centre of the tied region, not its edge, to avoid overfitting).
Output: experiments/calibration.json with the chosen values and the full grid summary.
These values are then frozen into RouterConfig and recorded in D-005.

Usage: python analysis/calibrate.py experiments/raw/pilot.jsonl [more.jsonl ...]
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def load_points(paths: list[str]) -> list[dict]:
    pts = []
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("event") != "step" or r.get("config") != "a11y":
                continue
            if not str(r.get("scenario", "")).startswith("p-"):
                continue
            if r.get("action_type") not in ("tap", "type_text") or r.get("oracle_ok") is None:
                continue
            c = r.get("candidates") or []
            top = c[0]["score"] if c else 0.0
            second = c[1]["score"] if len(c) > 1 else 0.0
            pts.append({"scenario": r["scenario"], "condition": r.get("condition"), "step": r.get("step_index"),
                        "top": top, "margin": top - second, "correct": bool(r["oracle_ok"])})
    return pts


def _grid(lo: float, hi: float) -> list[float]:
    n = int(round((hi - lo) / 0.01))
    return [round(lo + i * 0.01, 2) for i in range(n + 1)]


def calibrate(pts: list[dict], taus=None, deltas=None) -> dict:
    taus = taus or _grid(0.60, 0.95)
    deltas = deltas or _grid(0.05, 0.30)
    if not pts:
        raise ValueError("no pilot points")
    cells = []
    for t in taus:
        for d in deltas:
            acc = [p for p in pts if p["top"] >= t and p["margin"] >= d]
            prec = (sum(p["correct"] for p in acc) / len(acc)) if acc else 1.0
            cells.append({"tau": t, "delta": d, "accepted": len(acc), "coverage": len(acc) / len(pts),
                          "precision": prec})
    best_prec = max(c["precision"] for c in cells)
    feas = [c for c in cells if c["precision"] == best_prec]
    max_cov = max(c["coverage"] for c in feas)
    tied = [c for c in feas if c["coverage"] == max_cov]
    tau = statistics.median_low(sorted({c["tau"] for c in tied}))
    delta = statistics.median_low(sorted({c["delta"] for c in tied if c["tau"] == tau}))
    chosen = next(c for c in tied if c["tau"] == tau and c["delta"] == delta)
    wrong_tops = [p for p in pts if not p["correct"]]
    return {
        "rule": "max coverage s.t. max precision; median of tied region (see module docstring)",
        "n_points": len(pts), "n_wrong_top": len(wrong_tops),
        "precision_achieved": best_prec, "coverage": round(max_cov, 4),
        "tau": tau, "delta": delta, "chosen_cell": chosen,
        "tied_tau_range": [min(c["tau"] for c in tied), max(c["tau"] for c in tied)],
        "tied_delta_range_at_tau": [min(c["delta"] for c in tied if c["tau"] == tau),
                                    max(c["delta"] for c in tied if c["tau"] == tau)],
        "wrong_top_points": wrong_tops,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pts = load_points(sys.argv[1:])
    out = calibrate(pts)
    Path("experiments").mkdir(exist_ok=True)
    Path("experiments/calibration.json").write_text(json.dumps({**out, "points": pts}, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "wrong_top_points"}, indent=1))
    print(f"wrong top candidates on pilot: {out['n_wrong_top']}")


if __name__ == "__main__":
    main()

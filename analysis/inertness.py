"""Inertness check for the seeded-fault build (D-028): fault-free tb runs on the rebuilt app vs the formal runs.

A run matches when its runner completion, oracle-free first failure point (analysis/faults.verdict) and the
per-step (route, oracle_ok) sequence equal those of a formal run of the same scenario, config and condition.

Usage: python analysis/inertness.py experiments/raw/fault_inertness.jsonl [--reference ...] [--out analysis/out]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import faults as F  # noqa: E402


def signature(r: dict) -> tuple:
    return (bool(r["end"].get("completed")), F.verdict(r),
            tuple((s["step_index"], s.get("route"), s.get("oracle_ok")) for s in r["steps"]))


def compare(new: list[dict], formal: list[dict]) -> tuple[int, list]:
    ref = defaultdict(set)
    for r in formal:
        ref[(r["scenario"], r["config"], r["condition"])].add(signature(r))
    bad = [((r["scenario"], r["config"], r["condition"]), signature(r)) for r in new
           if signature(r) not in ref[(r["scenario"], r["config"], r["condition"])]]
    return len(new) - len(bad), bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--reference", default="experiments/raw/formal.jsonl")
    ap.add_argument("--out", default="analysis/out")
    a = ap.parse_args(argv)
    new = F.load_runs(a.log)
    formal = [r for r in F.load_runs(a.reference) if r["scenario"].startswith("tb-")]
    ok, bad = compare(new, formal)
    done = sum(bool(r["end"].get("completed")) for r in new)
    md = (f"# Fault-build inertness check (generated, D-028)\n\nLog: {a.log}; reference: {a.reference}.\n\n"
          f"- runs: {len(new)} (tb-01..08 x 2 conditions x 3 configurations x 1 repetition)\n"
          f"- runner-completed: {done}; failed: {len(new) - done}\n"
          f"- runs matching a formal run on completion, oracle-free first failure and per-step route and "
          f"oracle: {ok} of {len(new)}\n"
          + "".join(f"- MISMATCH {k}: {s}\n" for k, s in bad))
    Path(a.out, "fault_inertness.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()

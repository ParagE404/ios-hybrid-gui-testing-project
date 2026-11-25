"""Print the steps of one run from a telemetry log as a readable table (video demo aid).

Origin: original,  Not part of the engine
or the analysis: it only reads a JSONL log and prints it.

Usage:
    python spikes/demo_show.py experiments/raw/demo.jsonl              # most recent run in the log
    python spikes/demo_show.py LOG --scenario tb-07 --config hybrid --condition perturbed
"""

from __future__ import annotations

import argparse
import json
import textwrap


def runs(path):
    """Group step records under their scenario_start, in log order."""
    out, cur = [], None
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("event") == "scenario_start":
            cur = {"start": r, "steps": [], "end": None}
            out.append(cur)
        elif cur is not None and r.get("event") == "step":
            cur["steps"].append(r)
        elif cur is not None and r.get("event") == "scenario_end":
            cur["end"] = r
            cur = None
    return out


def top(rec):
    c = (rec.get("candidates") or [None])[0]
    if not c:
        return "none"
    name = c.get("label") or c.get("identifier") or c.get("type")
    return f"{c.get('type')} '{name}' {c.get('score', 0):.2f}"


def vlm(rec):
    parts = []
    for a in rec.get("vlm_attempts") or []:
        v, val = a.get("vlm") or {}, a.get("validated") or {}
        verdict = val.get("kind") if val.get("kind") != "reject" else f"reject ({val.get('reason')})"
        parts.append(f"'{v.get('query', '')}' -> {v.get('raw_text', '?')} -> {verdict}")
    return "; ".join(parts) or "-"


def show(run):
    s, e = run["start"], run["end"] or {}
    print()
    print(f"  {s['scenario']}  |  {s['config']}  |  {s['condition']}  |  repetition {s.get('repetition')}")
    print("  " + "-" * 96)
    for r in run["steps"]:
        margin = (r.get("decision") or {}).get("margin")
        print(f"  Step {r['step_index'] + 1}: {r['step']}")
        print(f"     route      {r.get('route')}  ({r.get('reason')})")
        if r.get("candidates") is not None:
            m = f"   margin {margin:.2f}" if isinstance(margin, (int, float)) else ""
            print(f"     best match {top(r)}{m}")
        if r.get("vlm_attempts"):
            for line in textwrap.wrap(vlm(r), 84):
                print(f"     model      {line}")
        oracle = r.get("oracle_ok")
        print(f"     executed   {'yes' if r.get('executed') else 'no'}"
              + ("" if oracle is None else f"   right target {'yes' if oracle else 'no'}"))
    print("  " + "-" * 96)
    total = e.get("total_ms")
    status = "COMPLETED" if e.get("completed") else "FAILED"
    print(f"  {status}" + (f" in {total / 1000:.1f} s" if total else ""))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--scenario")
    ap.add_argument("--config")
    ap.add_argument("--condition")
    a = ap.parse_args()
    rs = [r for r in runs(a.log)
          if (not a.scenario or r["start"]["scenario"] == a.scenario)
          and (not a.config or r["start"]["config"] == a.config)
          and (not a.condition or r["start"]["condition"] == a.condition)]
    if not rs:
        raise SystemExit("no matching run in the log")
    show(rs[-1])


if __name__ == "__main__":
    main()
# Asset update

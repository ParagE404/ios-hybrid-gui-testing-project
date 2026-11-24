# Origin: AI-generated and reviewed by the author.
"""Live narrator for the video demo: follows a telemetry log and explains each decision as it lands.

 AI-assisted (Claude), reviewed by Parag Dharadhar. A demo aid only: it reads the
JSONL log the engine already writes (and the scenario YAML for the scripted locators); it changes
nothing in the engine, the benchmark or the formal data.

Run it in a second terminal pane BEFORE starting a scenario:
    python spikes/demo_watch.py experiments/raw/demo.jsonl
Replay a past run instead (for testing, or as a fallback on camera):
    python spikes/demo_watch.py experiments/raw/formal.jsonl --replay --scenario tb-07 --config hybrid --condition perturbed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

TAU, DELTA = 0.66, 0.09          # frozen router thresholds (D-005), shown for explanation only
NAMES = {"scripted": "Scripted", "a11y": "Accessibility-only", "hybrid": "Hybrid"}
B, DIM, RED, GRN, YEL, CYN, RST = "\033[1m", "\033[2m", "\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[0m"
PACE = 0.12
SCREEN_W, SCREEN_H = 402, 874     # iPhone 17 simulator, points


def say(text="", pause=PACE):
    print(text, flush=True)
    time.sleep(pause)


def bar(score, width=12):
    n = max(0, min(width, round(score * width)))
    return "█" * n + "░" * (width - n)


def scenario_yaml(sid, root):
    try:
        import yaml
        return yaml.safe_load((Path(root) / f"{sid}.yaml").read_text())
    except Exception:
        return {}


def banner(rec, scn):
    os.system("clear")
    say(f"{B}{NAMES.get(rec['config'], rec['config'])}{RST}  {DIM}·  {rec['scenario']}  ·  {rec['condition']}{RST}", 0)
    say(f"{DIM}{scn.get('title', '')}{RST}", 0)
    if rec["condition"] == "perturbed" and scn.get("perturbation"):
        say(f"{YEL}Changed in the app: {scn['perturbation'].get('description', '')}{RST}", 0)
    say("─" * 60, 0.4)


def locator_words(loc):
    if not loc:
        return "?"
    if loc.get("strategy") == "accessibility_id":
        return f"identifier '{loc['value']}'"
    return f"{loc.get('strategy')} {loc.get('value')}"


def step(rec, scn):
    i = rec["step_index"]
    say()
    say(f"{B}Step {i + 1}{RST}  {rec['step']}", 0.3)
    route, reason = rec.get("route"), rec.get("reason")
    if route == "scripted":
        steps = scn.get("steps") or []
        loc = steps[i].get("scripted") if i < len(steps) else None
        say(f"  Looking for {locator_words(loc)}")
        if rec.get("executed"):
            say(f"  {GRN}✓ found it, tapped{RST}")
        elif reason == "not_applicable":
            say(f"  {DIM}(no target){RST}")
        else:
            say(f"  {RED}✗ not found: the test has nothing to tap{RST}")
        return
    cands = rec.get("candidates") or []
    if rec.get("action_type") in ("tap", "type_text"):
        if cands:
            say(f"  {DIM}Candidates on screen{RST}")
            for c in cands[:3]:
                name = c.get("label") or c.get("identifier") or c.get("type")
                say(f"   {bar(c.get('score', 0))} {c.get('score', 0):.2f}  {c.get('type')} '{name[:28]}'")
        else:
            target = rec["step"].split("'")[1] if "'" in rec["step"] else "the target"
            say(f"  {RED}No label, id or text on screen matches '{target}'{RST}", 0.3)
    dec = rec.get("decision") or {}
    if reason == "ok" and route == "structured":
        top = cands[0]["score"] if cands else 0
        m = dec.get("margin") or 0
        say(f"  Router: score {top:.2f} ≥ {TAU}  and  lead {m:.2f} ≥ {DELTA}  {GRN}→ confident{RST}")
    elif reason not in (None, "not_applicable"):
        say(f"  Router: {YEL}unsure ({reason.replace('_', ' ')}){RST}", 0.3)
    for a in rec.get("vlm_attempts") or []:
        v, val = a.get("vlm") or {}, a.get("validated") or {}
        say(f"  {CYN}Asking ShowUI-2B: “{v.get('query', '')}”{RST}", 0.5)
        p = v.get("parsed") or {}
        if "x" in p:
            px, py = round(p["x"] * SCREEN_W), round(p["y"] * SCREEN_H)
            say(f"  {CYN}Model points at ({px}, {py}) on the screen{RST}")
        if val.get("kind") == "reject":
            say(f"  Validator: {RED}✗ rejected ({val.get('reason', '').replace('_', ' ')}){RST}")
        else:
            say(f"  Validator: {GRN}✓ snapped to a real button, safe to {val.get('kind')}{RST}")
    if rec.get("action_type") in ("tap", "type_text"):
        if rec.get("executed"):
            ok = rec.get("oracle_ok")
            mark = f"{GRN}✓ hit the right control{RST}" if ok else f"{RED}✗ hit the wrong control{RST}"
            say(f"  Tapped  {mark}")
        else:
            say(f"  {RED}✗ nothing safe to tap: the test stops here{RST}")


def end(rec):
    say("─" * 60, 0.2)
    t = rec.get("total_ms", 0) / 1000
    if rec.get("completed"):
        say(f"{B}{GRN}✓ COMPLETED{RST}  {DIM}{t:.1f} s{RST}", 0)
    else:
        say(f"{B}{RED}✗ FAILED{RST}  {DIM}{t:.1f} s{RST}", 0)


def handle(rec, scenarios_dir, state):
    ev = rec.get("event")
    if ev == "scenario_start":
        state["scn"] = scenario_yaml(rec["scenario"], scenarios_dir)
        banner(rec, state["scn"])
    elif ev == "step":
        step(rec, state.get("scn") or {})
    elif ev == "scenario_end":
        end(rec)


def follow(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).touch()
    with open(path, encoding="utf-8") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue
            if line.strip():
                yield json.loads(line)


def replay(path, a):
    recs = [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
    key = lambda r: (r.get("run_id"), r.get("scenario"), r.get("config"), r.get("condition"), r.get("repetition"), r.get("attempt"))
    match = [r for r in recs if (not a.scenario or r.get("scenario") == a.scenario)
             and (not a.config or r.get("config") == a.config)
             and (not a.condition or r.get("condition") == a.condition)]
    starts = [r for r in match if r.get("event") == "scenario_start"]
    if not starts:
        raise SystemExit("no matching run")
    k = key(starts[-1])
    return [r for r in match if key(r) == k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--scenarios", default="benchmark/scenarios")
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--scenario")
    ap.add_argument("--config")
    ap.add_argument("--condition")
    a = ap.parse_args()
    state = {}
    try:
        if a.replay:
            for r in replay(a.log, a):
                handle(r, a.scenarios, state)
        else:
            print(f"{DIM}Watching {a.log} ... start a scenario in the other pane{RST}", flush=True)
            for r in follow(a.log):
                handle(r, a.scenarios, state)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

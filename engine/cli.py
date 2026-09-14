"""Command line: run scenarios against a real simulator through Appium.

Origin: original, 
Not yet verified on a simulator (needs Xcode). Example:

    appium &      # in another terminal
    python -m engine.cli run benchmark/examples/tb-example-add-item.yaml \
        --config a11y --condition baseline --device "iPhone 16" \
        --bundle com.parag.Testbed --log experiments/raw/dev.jsonl

    python -m engine.cli resolve spikes/out/page_source.xml "Tap the 'General' cell"
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from .intent import parse_step
from .normalise import parse_page_source
from .resolver import resolve
from .router import route


def cmd_resolve(a):
    src = Path(a.page_source)
    if not src.exists():
        raise SystemExit(f"{src} not found. Run spikes/appium_smoke.py first (needs Xcode + a booted simulator).")
    snap = parse_page_source(src.read_text(encoding="utf-8"))
    res = resolve(snap, parse_step(a.step))
    dec = route(res)
    print(json.dumps({"decision": dec.to_log(), "resolution_ms": round(res.resolution_ms, 2),
                      "elements": len(snap.elements),
                      "candidates": [c.to_log() for c in res.candidates]}, indent=2))


def cmd_run(a):
    from appium import webdriver
    from appium.options.ios import XCUITestOptions

    from .backend import AppiumBackend
    from .runner import run_scenario
    from .scenario import load_scenario
    from .telemetry import Telemetry

    opts = XCUITestOptions()
    opts.device_name = a.device
    if a.platform_version:
        opts.platform_version = a.platform_version
    opts.bundle_id = a.bundle
    opts.new_command_timeout = 300
    driver = webdriver.Remote(a.server, options=opts)
    vlm = None
    if a.config == "hybrid":
        from .vlm.showui import ShowUIAdapter
        vlm = ShowUIAdapter()
    tel = Telemetry(a.log, run_id=a.run_id or uuid.uuid4().hex[:8])
    try:
        backend = AppiumBackend(driver, a.bundle)
        for path in a.scenarios:
            scn = load_scenario(path)
            for rep in range(1, a.repetitions + 1):
                from .runner import CONFIGS
                r = run_scenario(scn, backend, CONFIGS[a.config], a.condition, rep, vlm=vlm, tel=tel)
                print(f"{scn.id} {a.config} {a.condition} rep{rep}: "
                      f"{'COMPLETED' if r.completed else 'FAILED'} "
                      f"routes={[s.route for s in r.steps]} {r.total_ms / 1000:.1f}s")
    finally:
        driver.quit()


def cmd_check(a):
    from .scenario import load_scenario
    from .staticcheck import check_scenario
    paths = sorted(Path(a.scenarios).glob("*.yaml")) if Path(a.scenarios).is_dir() else [Path(a.scenarios)]
    cols = ["scenario", "condition", "step", "screen", "scripted_matches", "oracle_matches",
            "route", "reason", "chosen", "score", "margin", "oracle_ok", "target_labels", "note"]
    print("\t".join(cols))
    for p in paths:
        for row in check_scenario(load_scenario(p), Path(a.pagesource), a.show_perturbed_routes):
            print("\t".join("" if row.get(c) is None else str(row.get(c)) for c in cols))


def cmd_batch(a):
    import yaml
    from .batch import new_batch_id, plan_runs, run_batch, write_manifest
    from .scenario import load_dir
    from .telemetry import Telemetry

    scenarios = [s for s in load_dir(a.scenarios) if a.allow_pilot or not s.pilot]
    plan = plan_runs(scenarios, a.conditions.split(","), a.configs.split(","), a.repetitions, a.seed)
    if a.limit:
        plan = plan[: a.limit]
    print(f"{len(scenarios)} scenarios, {len(plan)} runs planned (seed {a.seed})")
    if a.dry_run:
        for k in plan:
            print(*k)
        return
    apps = yaml.safe_load(Path(a.apps).read_text())
    batch_id = a.batch_id or new_batch_id()
    log = Path(a.log)
    write_manifest(log.with_suffix(".manifest.json"), batch_id=batch_id, seed=a.seed, plan=plan,
                   scenarios=scenarios, extra={"device": a.device, "apps": apps, "log": str(log)})

    from appium import webdriver
    from appium.options.ios import XCUITestOptions
    from .backend import AppiumBackend

    state = {"driver": None, "backends": {}}

    def connect():
        if state["driver"] is not None:
            try:
                state["driver"].quit()
            except Exception:
                pass
        first = next(iter(apps.values()))["bundle"]
        opts = XCUITestOptions()
        opts.device_name = a.device
        if a.platform_version:
            opts.platform_version = a.platform_version
        opts.bundle_id = first
        opts.new_command_timeout = 600
        state["driver"] = webdriver.Remote(a.server, options=opts)
        state["backends"] = {}

    def backend_for(app):
        if app not in state["backends"]:
            state["backends"][app] = AppiumBackend(state["driver"], apps[app]["bundle"])
        return state["backends"][app]

    def vlm_factory():
        from .vlm.showui import ShowUIAdapter
        print("loading ShowUI-2B ...")
        return ShowUIAdapter()

    connect()
    try:
        summary = run_batch(scenarios, plan, backend_for, connect, Telemetry(log, run_id=batch_id),
                            vlm_factory=vlm_factory)
    finally:
        if state["driver"] is not None:
            state["driver"].quit()
    print(json.dumps(summary, indent=1))


def main():
    p = argparse.ArgumentParser(prog="engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("resolve", help="Resolve one step against a saved page source (no simulator)")
    r.add_argument("page_source")
    r.add_argument("step")
    r.set_defaults(func=cmd_resolve)

    c = sub.add_parser("check", help="Static check of scenarios against saved page sources")
    c.add_argument("scenarios", help="scenario YAML or directory")
    c.add_argument("--pagesource", default="benchmark/pagesource")
    c.add_argument("--show-perturbed-routes", action="store_true",
                   help="also show resolver routes on perturbed screens (avoid before the freeze, D-013)")
    c.set_defaults(func=cmd_check)

    b = sub.add_parser("batch", help="Run the formal experiment (randomised, resumable, D-014)")
    b.add_argument("scenarios", help="directory of scenario YAMLs")
    b.add_argument("--conditions", default="baseline,perturbed")
    b.add_argument("--configs", default="scripted,a11y,hybrid")
    b.add_argument("--repetitions", type=int, default=3)
    b.add_argument("--seed", type=int, default=20261018)
    b.add_argument("--limit", type=int, help="only the first N planned runs (smoke test)")
    b.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    b.add_argument("--allow-pilot", action="store_true", help="include pilot scenarios (calibration only)")
    b.add_argument("--apps", default="benchmark/apps.yaml")
    b.add_argument("--device", required=False, default="iPhone 17")
    b.add_argument("--platform-version", default="27.0", help="iOS runtime; must match the booted simulator")
    b.add_argument("--server", default="http://127.0.0.1:4723")
    b.add_argument("--log", default="experiments/raw/formal.jsonl")
    b.add_argument("--batch-id")
    b.set_defaults(func=cmd_batch)

    run = sub.add_parser("run", help="Run scenarios on a simulator")
    run.add_argument("scenarios", nargs="+")
    run.add_argument("--config", choices=["a11y", "hybrid", "scripted"], required=True)
    run.add_argument("--condition", choices=["baseline", "perturbed"], default="baseline")
    run.add_argument("--repetitions", type=int, default=1)
    run.add_argument("--device", required=True)
    run.add_argument("--platform-version", default="27.0", help="iOS runtime; must match the booted simulator")
    run.add_argument("--bundle", required=True)
    run.add_argument("--server", default="http://127.0.0.1:4723")
    run.add_argument("--log", default="experiments/raw/dev.jsonl")
    run.add_argument("--run-id")
    run.set_defaults(func=cmd_run)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()

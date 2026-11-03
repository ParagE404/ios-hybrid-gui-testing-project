
from __future__ import annotations

import argparse
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError as MCPToolError

from engine.telemetry import Telemetry

from .session import EngineSession, ToolError


def _guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ToolError as e:
        # Out-of-bounds requests come back as tool errors; nothing was executed.
        raise MCPToolError(f"rejected: {e}") from e


def build_server(session: EngineSession, on_shutdown=None) -> MCPServer:
    @asynccontextmanager
    async def lifespan(_server):
        try:
            yield {}
        finally:
            if on_shutdown:
                on_shutdown()

    mcp = MCPServer("ios-hybrid-testing", lifespan=lifespan, instructions=(
        "Intent-driven native iOS GUI testing on an iOS Simulator through Appium/XCUITest. "
        "Steps use controlled English with the target in quotes, e.g. \"Tap the 'Save' button\" or "
        "\"Type 'Milk' into the 'Item name' field\". Use resolve to inspect a step without acting."))

    @mcp.tool()
    def list_scenarios() -> list[dict]:
        """List the formal benchmark scenarios (id, app, title, category, step texts)."""
        return session.list_scenarios()

    @mcp.tool()
    def start_scenario(scenario_id: str, condition: str = "baseline", config: str = "a11y",
                       repetition: int = 1) -> dict:
        """Reset the scenario's app (with its perturbation if condition='perturbed') and begin a run.
        config: scripted | a11y | hybrid."""
        return _guard(session.start_scenario, scenario_id, condition, config, repetition)

    @mcp.tool()
    def run_step(index: int) -> dict:
        """Run step `index` of the current scenario with the engine; returns route, reason,
        decision, candidates, action, oracle verdict and latencies. Steps run in order."""
        return _guard(session.run_step, index)

    @mcp.tool()
    def finish_scenario() -> dict:
        """Check the scenario's postconditions and end the run; returns completed and timings."""
        return _guard(session.finish_scenario)

    @mcp.tool()
    def select_app(app: str, launch_args: Optional[list[str]] = None) -> dict:
        """Relaunch an app from benchmark/apps.yaml, optionally with flags such as
        ['-resetData'] or ['-perturb', '<flag>']."""
        return _guard(session.select_app, app, launch_args)

    @mcp.tool()
    def snapshot(max_elements: int = 150, interactive_only: bool = True) -> dict:
        """Summarise the current screen: visible (interactive) elements with type, label, identifier, frame."""
        return _guard(session.snapshot, max_elements, interactive_only)

    @mcp.tool()
    def resolve(step: str, config: str = "a11y") -> dict:
        """Read-only. Rank candidate elements for a step and return the router's decision
        (structured or fallback, with a reason code). Nothing is executed."""
        return _guard(session.resolve, step, config)

    @mcp.tool()
    def act(step: str, config: str = "a11y") -> dict:
        """Resolve and execute one step with the engine's own logic (a11y, or hybrid with VLM fallback)."""
        return _guard(session.act, step, config)

    @mcp.tool()
    def execute_action(kind: str, x: Optional[float] = None, y: Optional[float] = None,
                       text: Optional[str] = None, direction: Optional[str] = None,
                       seconds: Optional[float] = None) -> dict:
        """One bounded action: tap(x,y) | type_text(x,y,text<=200) | swipe(direction) |
        navigate_back | wait(seconds<=5). Coordinates must lie on the current screen."""
        return _guard(session.execute_action, kind, x, y, text, direction, seconds)

    @mcp.tool()
    def telemetry(last: int = 20) -> list[dict]:
        """The most recent telemetry records (JSONL events) from this server process."""
        return _guard(session.telemetry, last)

    return mcp


def appium_session(apps_path: str, scenarios: str, log: Optional[str], device: str, platform_version: str,
                   server_url: str, run_id: str, mode: str, vlm: bool):
    """EngineSession on a real simulator: one Appium driver, one backend per app (as in cmd_batch)."""
    import yaml
    from appium import webdriver
    from appium.options.ios import XCUITestOptions

    from engine.backend import AppiumBackend

    apps = yaml.safe_load(Path(apps_path).read_text())
    state = {"driver": None, "backends": {}}

    def driver():
        if state["driver"] is None:
            opts = XCUITestOptions()
            opts.device_name = device
            if platform_version:
                opts.platform_version = platform_version
            opts.bundle_id = next(iter(apps.values()))["bundle"]
            opts.new_command_timeout = 600
            state["driver"] = webdriver.Remote(server_url, options=opts)
        return state["driver"]

    def backend_for(app):
        if app not in state["backends"]:
            state["backends"][app] = AppiumBackend(driver(), apps[app]["bundle"])
        return state["backends"][app]

    def shutdown():
        if state["driver"] is not None:
            try:
                state["driver"].quit()
            except Exception:
                pass
            state["driver"], state["backends"] = None, {}

    def vlm_factory():
        from engine.vlm.showui import ShowUIAdapter
        print("loading ShowUI-2B ...", file=sys.stderr)
        return ShowUIAdapter()

    tel = Telemetry(log, run_id=run_id, mode=mode)
    sess = EngineSession(backend_for, tel, scenarios, apps, vlm_factory if vlm else None)
    return sess, shutdown


def add_appium_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--apps", default="benchmark/apps.yaml")
    p.add_argument("--scenarios", default="benchmark/scenarios")
    p.add_argument("--device", default="iPhone 17")
    p.add_argument("--platform-version", default="27.0")
    p.add_argument("--server", default="http://127.0.0.1:4723")


def main(argv=None):
    p = argparse.ArgumentParser(prog="mcp_adapter.server")
    add_appium_args(p)
    p.add_argument("--log", help="telemetry JSONL (default: keep in memory only)")
    p.add_argument("--run-id", default="mcp")
    p.add_argument("--mode", default="mcp", help="value of the 'mode' field in telemetry")
    p.add_argument("--vlm", action="store_true", help="allow config=hybrid (loads ShowUI-2B on first use)")
    p.add_argument("--selftest", action="store_true",
                   help="no simulator: serve the example scenario on the test suite's fake backend")
    a = p.parse_args(argv)
    if a.selftest:
        from tests.test_runner import backend
        from tests import fixtures as F
        fb = backend(F.HOME)
        sess = EngineSession(lambda app: fb, Telemetry(a.log, run_id=a.run_id, mode=a.mode),
                             "benchmark/examples", {"testbed": {}})
        build_server(sess).run("stdio")
        return
    sess, shutdown = appium_session(a.apps, a.scenarios, a.log, a.device, a.platform_version, a.server,
                                    a.run_id, a.mode, a.vlm)
    build_server(sess, on_shutdown=shutdown).run("stdio")


if __name__ == "__main__":
    main()

"""Tests for the MCP adapter (D-026). Origin: original, 

1. EngineSession reproduces engine.runner.run_scenario exactly (same telemetry, minus timings).
2. The same calls through a real MCP client (in-memory transport) give the same results.
3. Out-of-bounds tool requests are rejected and nothing is executed.
"""

import json
from pathlib import Path

import anyio
import pytest

from engine.runner import CONFIGS, run_scenario
from engine.scenario import load_scenario
from engine.telemetry import Telemetry
from engine.vlm import FakeVLM
from mcp_adapter.server import build_server
from mcp_adapter.session import EngineSession, ToolError

from . import fixtures as F
from .test_runner import backend

EXAMPLES = Path(__file__).parent.parent / "benchmark" / "examples"
SID = "tb-example-add-item"
TIMING = {"ts", "latency", "total_ms"}


def strip(recs):
    out = []
    for r in recs:
        r = {k: v for k, v in r.items() if k not in TIMING}
        for a in r.get("vlm_attempts", []) or []:
            a.get("vlm", {}).pop("latency_ms", None)
        out.append(r)
    return out


def session(home_xml, vlm=None):
    fb = backend(home_xml)
    tel = Telemetry(None, run_id="t")
    return EngineSession(lambda app: fb, tel, EXAMPLES, {"testbed": {}},
                         (lambda: vlm) if vlm else None), fb


def drive(sess, condition, config):
    sess.start_scenario(SID, condition, config, 1)
    n = len(sess.scenarios[SID].steps)
    for i in range(n):
        r = sess.run_step(i)
        if not r["executed"]:
            break
    return sess.finish_scenario()


@pytest.mark.parametrize("home,condition,config", [
    (F.HOME, "baseline", "a11y"), (F.HOME, "baseline", "scripted"),
    (F.HOME_RENAMED, "perturbed", "scripted"), (F.HOME_WEAK, "perturbed", "a11y"),
    (F.HOME_WEAK, "perturbed", "hybrid")])
def test_session_matches_run_scenario(home, condition, config):
    point = (372 / 402, 77 / 874)
    scn = load_scenario(EXAMPLES / f"{SID}.yaml")
    ref_tel = Telemetry(None, run_id="t")
    ref = run_scenario(scn, backend(home), CONFIGS[config], condition, 1, vlm=FakeVLM(point=point), tel=ref_tel)
    sess, _ = session(home, FakeVLM(point=point))
    out = drive(sess, condition, config)
    assert out["completed"] == ref.completed
    assert strip(sess.tel.records) == strip(ref_tel.records)


def test_mcp_client_gives_same_results():
    from mcp.client.client import Client

    sess, _ = session(F.HOME_WEAK)
    direct_sess, _ = session(F.HOME_WEAK)
    direct = drive(direct_sess, "perturbed", "a11y")

    async def run():
        async with Client(build_server(sess)) as c:
            names = {t.name for t in (await c.list_tools()).tools}
            assert {"start_scenario", "run_step", "finish_scenario", "resolve", "execute_action"} <= names
            await c.call_tool("start_scenario", {"scenario_id": SID, "condition": "perturbed", "config": "a11y"})
            steps = []
            for i in range(3):
                r = json.loads((await c.call_tool("run_step", {"index": i})).content[0].text)
                steps.append(r)
                if not r["executed"]:
                    break
            fin = json.loads((await c.call_tool("finish_scenario", {})).content[0].text)
            bad = await c.call_tool("execute_action", {"kind": "tap", "x": 9999, "y": 5})
            return steps, fin, bad

    steps, fin, bad = anyio.run(run)
    assert fin["completed"] == direct["completed"]
    assert strip(sess.tel.records) == strip(direct_sess.tel.records)
    assert steps[0]["route"] in ("best_effort", "fallback", "structured")
    assert bad.is_error and "rejected" in bad.content[0].text


def test_bounds_are_enforced():
    sess, fb = session(F.HOME)
    sess.select_app("testbed", ["-resetData", "-perturb", "x"])
    for call in [lambda: sess.execute_action("rm -rf"),
                 lambda: sess.execute_action("tap", 500, 10),
                 lambda: sess.execute_action("type_text", 10, 10, "x" * 201),
                 lambda: sess.execute_action("swipe", direction="diagonal"),
                 lambda: sess.execute_action("wait", seconds=60),
                 lambda: sess.select_app("Safari"),
                 lambda: sess.select_app("testbed", ["/etc/passwd"]),
                 lambda: sess.resolve("Tap the 'Add item' button", config="scripted"),
                 lambda: sess.run_step(0)]:
        n = len(fb.actions)
        with pytest.raises(ToolError):
            call()
        assert len(fb.actions) == n          # nothing executed
    assert sess.execute_action("wait", seconds=1)["ok"]


def test_resolve_is_read_only_and_act_executes():
    sess, fb = session(F.HOME)
    sess.select_app("testbed")
    n = len(fb.actions)
    r = sess.resolve("Tap the 'Add item' button")
    assert r["decision"]["route"] == "structured" and len(fb.actions) == n
    a = sess.act("Tap the 'Add item' button")
    assert a["executed"] and fb.current == "add"


def test_steps_must_run_in_order():
    sess, _ = session(F.HOME)
    sess.start_scenario(SID, "baseline", "a11y")
    with pytest.raises(ToolError):
        sess.run_step(1)


def test_stdio_subprocess_round_trip(tmp_path):
    """The real transport: server as a subprocess over stdio (catches anything printed to stdout)."""
    import sys
    from mcp import StdioServerParameters
    from mcp.client.client import Client

    root = Path(__file__).parent.parent
    log = tmp_path / "mcp.jsonl"
    params = StdioServerParameters(command=sys.executable, cwd=str(root),
                                   args=["-m", "mcp_adapter.server", "--selftest", "--log", str(log)])

    async def run():
        async with Client(params, read_timeout_seconds=60) as c:
            await c.call_tool("start_scenario", {"scenario_id": SID})
            for i in range(3):
                r = json.loads((await c.call_tool("run_step", {"index": i})).content[0].text)
                assert r["executed"] and r["route"] == "structured"
            return json.loads((await c.call_tool("finish_scenario", {})).content[0].text)

    assert anyio.run(run)["completed"]
    recs = [json.loads(x) for x in log.read_text().splitlines()]
    assert recs[0]["event"] == "scenario_start" and recs[-1]["event"] == "scenario_end"
    assert all(r["mode"] == "mcp" for r in recs)


def test_seq1_pipeline_on_fake_backend(tmp_path):
    """Both SEQ1 modes through the shared driver, then the SEQ1 analysis on the resulting logs."""
    import time as _t
    from mcp.client.client import Client

    from analysis import seq1 as A
    from mcp_adapter.seq1 import Recorder, _drive_async

    log, timing = tmp_path / "seq1.jsonl", tmp_path / "timing.jsonl"
    rec = Recorder(timing, "b")

    def mk(mode, home):
        fb = backend(home)
        return EngineSession(lambda app: fb, Telemetry(log, run_id="b", mode=mode), EXAMPLES, {"testbed": {}})

    async def go():
        for cond, home in (("baseline", F.HOME), ("perturbed", F.HOME_WEAK)):
            d = mk("direct", home)
            fns = {"start_scenario": lambda k: d.start_scenario(**k), "run_step": lambda k: d.run_step(**k),
                   "finish_scenario": lambda k: d.finish_scenario()}

            async def dcall(name, args):
                t = _t.perf_counter()
                o = fns[name](args)
                return o, (_t.perf_counter() - t) * 1000, len(json.dumps(o, default=str))
            await _drive_async(dcall, rec, "direct", SID, cond, 1, 3)
            async with Client(build_server(mk("mcp", home))) as c:
                async def mcall(name, args):
                    t = _t.perf_counter()
                    r = await c.call_tool(name, args)
                    return json.loads(r.content[0].text), (_t.perf_counter() - t) * 1000, len(r.content[0].text)
                await _drive_async(mcall, rec, "mcp", SID, cond, 1, 3)

    anyio.run(go)
    A.main([str(log), str(timing), "--out", str(tmp_path / "out")])
    eq = pd_read(tmp_path / "out" / "seq1_equivalence.csv")
    assert len(eq) > 0 and eq["mcp_eq_direct"].all()
    md = (tmp_path / "out" / "seq1.md").read_text()
    assert '"runs_fully_identical": 2' in md and "overhead_median_ms" in md


def pd_read(p):
    import pandas as pd
    return pd.read_csv(p)

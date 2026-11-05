
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

SUBSET = ["tb-03", "tb-07", "su-03", "su-07", "nn-03", "nn-07"]
SEED = 20261019


def plan(reps: int, seed: int, conditions: list[str], subset: list[str]) -> list[tuple[str, list]]:
    rng = random.Random(seed)
    blocks = []
    for rep in range(1, reps + 1):
        order = ["direct", "mcp"] if rep % 2 else ["mcp", "direct"]
        for mode in order:
            runs = [(s, c, rep) for s in subset for c in conditions]
            rng.shuffle(runs)
            blocks.append((mode, runs))
    return blocks


def done_keys(timing: Path) -> set:
    if not timing.exists():
        return set()
    keys = set()
    for line in timing.read_text().splitlines():
        r = json.loads(line)
        if r.get("call") == "run_end" and not r.get("infrastructure_error"):
            keys.add((r["mode"], r["scenario"], r["condition"], r["repetition"]))
    return keys


class Recorder:
    def __init__(self, path: Path, batch: str):
        self.path, self.batch = path, batch
        path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, **rec):
        with self.path.open("a") as f:
            f.write(json.dumps({"ts": time.time(), "batch": self.batch, **rec}) + "\n")


def _retrying(drive_one):
    """First try plus two infrastructure retries per run, as in the formal protocol (D-014)."""
    async def go(runs):
        for s, c, r in runs:
            for _ in range(3):
                if await drive_one(s, c, r):
                    break
    return go


def run_direct(a, runs, rec, n_steps):
    import anyio

    from .server import appium_session
    sess, shutdown = appium_session(a.apps, a.scenarios, a.log, a.device, a.platform_version, a.server,
                                    a.batch, "direct", False)
    fns = {"start_scenario": lambda k: sess.start_scenario(**k), "run_step": lambda k: sess.run_step(**k),
           "finish_scenario": lambda k: sess.finish_scenario()}

    async def acall(name, args):
        t = time.perf_counter()
        out = fns[name](args)
        ms = (time.perf_counter() - t) * 1000
        return out, ms, len(json.dumps(out, default=str))

    try:
        anyio.run(_retrying(lambda s, c, r: _drive_async(acall, rec, "direct", s, c, r, n_steps[s])), runs)
    finally:
        shutdown()


def run_mcp(a, runs, rec, n_steps):
    import anyio
    from mcp import StdioServerParameters
    from mcp.client.client import Client

    params = StdioServerParameters(command=sys.executable, cwd=str(Path.cwd()), args=[
        "-m", "mcp_adapter.server", "--log", a.log, "--run-id", a.batch, "--mode", "mcp",
        "--apps", a.apps, "--scenarios", a.scenarios, "--device", a.device,
        "--platform-version", a.platform_version, "--server", a.server])

    async def main():
        async with Client(params, read_timeout_seconds=300) as client:
            async def acall(name, args):
                t = time.perf_counter()
                res = await client.call_tool(name, args)
                ms = (time.perf_counter() - t) * 1000
                text = res.content[0].text if res.content else "{}"
                if res.is_error:
                    raise RuntimeError(f"{name} failed: {text}")
                return json.loads(text), ms, len(text)
            await _retrying(lambda s, c, r: _drive_async(acall, rec, "mcp", s, c, r, n_steps[s]))(runs)

    anyio.run(main)


async def _drive_async(acall, rec, mode, scenario, condition, rep, n_steps):
    """One run through start/run_step/finish. Both modes use this function; only `acall` differs:
    in-process EngineSession calls (direct) or MCP tool calls over stdio (mcp)."""
    key = dict(mode=mode, scenario=scenario, condition=condition, repetition=rep)
    t0 = time.perf_counter()
    p, ms, ch = await acall("start_scenario", {"scenario_id": scenario, "condition": condition,
                                               "config": "a11y", "repetition": rep})
    rec(call="start_scenario", client_ms=ms, response_chars=ch, **key)
    if p.get("infrastructure_error"):
        rec(call="run_end", completed=False, infrastructure_error=True, error=p.get("error"),
            wall_ms=(time.perf_counter() - t0) * 1000, **key)
        return False
    for i in range(n_steps):
        p, ms, ch = await acall("run_step", {"index": i})
        if p.get("infrastructure_error"):
            rec(call="run_end", completed=False, infrastructure_error=True, error=p.get("error"),
                wall_ms=(time.perf_counter() - t0) * 1000, **key)
            return False
        server_ms = (p.get("latency") or {}).get("total_ms")
        rec(call="run_step", index=i, client_ms=ms, server_ms=server_ms, response_chars=ch,
            route=p.get("route"), reason=p.get("reason"), executed=p.get("executed"), **key)
        if not p.get("executed"):
            break
    p, ms, ch = await acall("finish_scenario", {})
    rec(call="finish_scenario", client_ms=ms, response_chars=ch, **key)
    infra = bool(p.get("infrastructure_error"))
    rec(call="run_end", completed=bool(p.get("completed")), infrastructure_error=infra,
        server_total_ms=p.get("total_ms"), wall_ms=(time.perf_counter() - t0) * 1000, **key)
    return not infra


def main(argv=None):
    from engine.scenario import load_scenario

    from .server import add_appium_args
    p = argparse.ArgumentParser(prog="mcp_adapter.seq1")
    add_appium_args(p)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--conditions", default="baseline,perturbed")
    p.add_argument("--log", default="experiments/raw/seq1.jsonl")
    p.add_argument("--timing", default="experiments/raw/seq1_timing.jsonl")
    p.add_argument("--batch", default=time.strftime("seq1-%Y%m%d-%H%M"))
    p.add_argument("--limit", type=int, help="only the first N runs of each block (smoke test)")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    n_steps = {s: len(load_scenario(Path(a.scenarios) / f"{s}.yaml").steps) for s in SUBSET}
    blocks = plan(a.reps, a.seed, a.conditions.split(","), SUBSET)
    done = done_keys(Path(a.timing))
    rec = Recorder(Path(a.timing), a.batch)
    total = sum(len(r) for _, r in blocks)
    print(f"SEQ1: {len(blocks)} blocks, {total} runs, {len(done)} already done (seed {a.seed})", file=sys.stderr)
    for mode, runs in blocks:
        todo = [(s, c, r) for s, c, r in runs if (mode, s, c, r) not in done]
        if a.limit:
            todo = todo[: a.limit]
        print(f"block {mode}: {len(todo)} runs", file=sys.stderr)
        if a.dry_run or not todo:
            for k in todo:
                print(mode, *k)
            continue
        (run_direct if mode == "direct" else run_mcp)(a, todo, rec, n_steps)
    if not a.dry_run:
        print(json.dumps(summary(Path(a.timing)), indent=1))


def summary(timing: Path) -> dict:
    ends = [json.loads(x) for x in timing.read_text().splitlines()]
    ends = [r for r in ends if r.get("call") == "run_end"]
    out = {}
    for m in ("direct", "mcp"):
        rs = [r for r in ends if r["mode"] == m and not r.get("infrastructure_error")]
        out[m] = {"runs": len(rs), "completed": sum(r["completed"] for r in rs),
                  "infrastructure_attempts": sum(1 for r in ends if r["mode"] == m and r.get("infrastructure_error"))}
    return out


if __name__ == "__main__":
    main()

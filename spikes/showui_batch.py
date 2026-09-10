"""Spike 2b: score ShowUI-2B grounding on a labelled screen (evidence for decision D-002).

Origin: original,  Uses
engine.vlm.showui.ShowUIAdapter, which is adapted from the ShowUI-2B model card.

For every labelled row in spikes/out/screenshot_truth.json it asks the model to locate
"<label> cell", checks whether the predicted point falls inside that row, and reports
hit rate and latency (median, p90). Results go to spikes/out/showui_batch.json.

Usage:
    python spikes/make_test_screen.py        # synthetic screen + ground truth
    python spikes/showui_batch.py
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.intent import parse_step                 # noqa: E402
from engine.vlm.showui import ShowUIAdapter          # noqa: E402

OUT = Path(__file__).parent / "out"


def main():
    truth = json.loads((OUT / "screenshot_truth.json").read_text())
    png = (OUT / "screenshot.png").read_bytes()
    t = time.perf_counter()
    vlm = ShowUIAdapter()
    load_s = time.perf_counter() - t
    print(f"model load {load_s:.1f}s on {vlm.device}")

    rows, lat = [], []
    for label, (_, _, box) in truth.items():
        intent = parse_step(f"Tap the '{label}' cell")
        r = vlm.propose(png, intent, "spike", [], (402, 874))
        p = r.parsed
        hit = bool(p) and box[0] <= p["x"] <= box[2] and box[1] <= p["y"] <= box[3]
        lat.append(r.latency_ms)
        rows.append({"label": label, "raw": r.raw_text, "hit": hit, "latency_ms": round(r.latency_ms)})
        print(f"{'HIT ' if hit else 'MISS'} {label:22s} {r.raw_text:18s} {r.latency_ms:6.0f} ms")

    lat_sorted = sorted(lat)
    summary = {
        "device": vlm.device, "model_load_s": round(load_s, 1), "n": len(rows),
        "hits": sum(r["hit"] for r in rows),
        "parseable": sum(1 for r in rows if r["raw"] and "[" in r["raw"]),
        "latency_ms_median": round(statistics.median(lat)),
        "latency_ms_p90": round(lat_sorted[int(0.9 * (len(lat_sorted) - 1))]),
        "first_call_ms": round(lat[0]),
        "rows": rows,
    }
    (OUT / "showui_batch.json").write_text(json.dumps(summary, indent=1))
    print(f"\nhits {summary['hits']}/{summary['n']}, parseable {summary['parseable']}/{summary['n']}, "
          f"median {summary['latency_ms_median']} ms, p90 {summary['latency_ms_p90']} ms "
          f"(first call {summary['first_call_ms']} ms includes warm-up)")


if __name__ == "__main__":
    main()

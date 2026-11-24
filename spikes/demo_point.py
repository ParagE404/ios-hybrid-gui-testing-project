# Origin: AI-generated and reviewed by the author.
"""Show where ShowUI pointed: a simulator screenshot with the model's point drawn on it (video demo aid).

 AI-assisted (Claude), reviewed by Parag Dharadhar. Reads the last VLM proposal from a
telemetry log, takes a fresh screenshot of the booted simulator, and draws the point. The screenshot is
taken after the run, so the star already shows as filled; say so if you narrate over it.

Usage (macOS, simulator booted):
    python spikes/demo_point.py experiments/raw/demo.jsonl [--out experiments/raw/demo_point.png]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def last_point(log):
    point = None
    for line in open(log, encoding="utf-8"):
        r = json.loads(line)
        for a in r.get("vlm_attempts") or []:
            p = (a.get("vlm") or {}).get("parsed") or {}
            if "x" in p and (a.get("validated") or {}).get("kind") != "reject":
                point = (p["x"], p["y"], (a.get("vlm") or {}).get("query", ""))
    if point is None:
        raise SystemExit("no accepted model point in the log")
    return point


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--out", default="experiments/raw/demo_point.png")
    a = ap.parse_args()
    x, y, query = last_point(a.log)
    shot = Path(a.out).with_name("demo_screen.png")
    subprocess.run(["xcrun", "simctl", "io", "booted", "screenshot", str(shot)], check=True)
    img = Image.open(shot).convert("RGB")
    w, h = img.size
    cx, cy, r = x * w, y * h, w * 0.06
    d = ImageDraw.Draw(img)
    for k, colour in ((10, (255, 255, 255)), (6, (220, 38, 38))):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=k)
        d.line([cx - 1.8 * r, cy, cx - 1.1 * r, cy], fill=colour, width=k)
        d.line([cx + 1.1 * r, cy, cx + 1.8 * r, cy], fill=colour, width=k)
        d.line([cx, cy - 1.8 * r, cx, cy - 1.1 * r], fill=colour, width=k)
        d.line([cx, cy + 1.1 * r, cx, cy + 1.8 * r], fill=colour, width=k)
    img.save(a.out)
    print(f"ShowUI was asked for “{query}” and pointed at ({x:.2f}, {y:.2f}); saved {a.out}")
    subprocess.run(["open", a.out])


if __name__ == "__main__":
    main()

"""Figures for the worked example in Chapter 4 (scenario tb-07, 'Favourite' star).

Origin: original, AI-assisted (drafted with Claude Code; see docs/ai-use-log.md).

Reads only saved captures and one logged step; it runs nothing on the simulator.
  fig_perturbation_tb07   baseline vs perturbed detail screen, with the star's metadata
  fig_worked_step_tb07    the hybrid step: model point, snapped element, executed tap

The captures in benchmark/pagesource/ were taken on the 'Milk' item during the screen
tour; the formal step ran on 'Batteries'. The star sits in the same toolbar frame on both.

Usage:
    python analysis/worked_example.py experiments/raw/formal.jsonl --out analysis/out
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "benchmark/pagesource/baseline/detail"
PERT = ROOT / "benchmark/pagesource/tb07_star_unlabelled/detail"
SCALE = 3                      # screenshot pixels per point (1206 x 2622 px = 402 x 874 pt)
CROP_PT = (150, 40, 402, 130)  # toolbar region, in points: x0, y0, x1, y1
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
SCRIPTED, A11Y, HYBRID = "#2a78d6", "#eb6834", "#1baf7a"


def star(xml_path: Path, name: str) -> dict:
    """Return the attributes of the star button from a saved page source."""
    text = xml_path.read_text(encoding="utf-8")
    tag = re.search(r'<XCUIElementTypeButton[^>]*name="%s"[^>]*>' % re.escape(name), text).group(0)
    return dict(re.findall(r'(\w+)="([^"]*)"', tag))


def logged_step(log: Path) -> dict:
    """First hybrid, perturbed tb-07 step that went to the model."""
    for line in open(log, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if (r.get("event") == "step" and r["scenario"] == "tb-07" and r["config"] == "hybrid"
                and r["condition"] == "perturbed" and r.get("vlm_attempts")):
            return r
    raise SystemExit("no tb-07 hybrid fallback step in the log")


def crop(png: Path) -> Image.Image:
    x0, y0, x1, y1 = (v * SCALE for v in CROP_PT)
    return Image.open(png.with_suffix(".png")).convert("RGB").crop((x0, y0, x1, y1))


def show(ax, img):
    x0, y0, x1, y1 = CROP_PT
    ax.imshow(img, extent=(x0, x1, y1, y0))   # axes in points, origin top-left
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#e6e5e1")


def frame(ax, el, colour):
    ax.add_patch(Rectangle((float(el["x"]), float(el["y"])), float(el["width"]), float(el["height"]),
                           fill=False, edgecolor=colour, linewidth=1.8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--out", default="analysis/out")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": SURFACE})

    before, after = star(BASE.with_suffix(".xml"), "favouriteButton"), star(PERT.with_suffix(".xml"), "button_7")

    # Figure 1: same pixels, different metadata.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.3))
    for ax, png, el, title, colour in ((axes[0], BASE, before, "Baseline", SCRIPTED),
                                       (axes[1], PERT, after, "Perturbed (tb07_star_unlabelled)", A11Y)):
        show(ax, crop(png)); frame(ax, el, colour)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_xlabel(f'label: {el.get("label", "(none)")}\nidentifier: {el["name"]}',
                      fontsize=8.5, color=INK2, loc="left", family="DejaVu Sans Mono")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_perturbation_tb07.{ext}", dpi=200)
    plt.close(fig)

    # Figure 2: what the hybrid did on the perturbed screen.
    r = logged_step(Path(args.log))
    att = r["vlm_attempts"][0]
    px, py = att["vlm"]["parsed"]["x"] * 402, att["vlm"]["parsed"]["y"] * 874
    tx, ty = r["action"]["x"], r["action"]["y"]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    show(ax, crop(PERT)); frame(ax, after, HYBRID)
    ax.plot(px, py, marker="x", color=A11Y, markersize=9, markeredgewidth=2, linestyle="none",
            label=f'Model point {att["vlm"]["raw_text"]} = ({px:.0f}, {py:.0f}) pt')
    ax.plot(tx, ty, marker="o", color=HYBRID, markersize=6, linestyle="none",
            label=f"Executed tap ({tx:.1f}, {ty:.1f}) pt, centre of snapped element")
    ax.plot([], [], color=HYBRID, linewidth=1.8, label=f'Snapped element: Button "{after["name"]}"')
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.0, -0.05))
    ax.set_title(f'Step: {r["step"]}   router: {r["decision"]["reason"]}   query: "{att["vlm"]["query"]}"',
                 fontsize=8.5, color=INK, loc="left")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"fig_worked_step_tb07.{ext}", dpi=200)
    plt.close(fig)
    print("wrote", out / "fig_perturbation_tb07.png", out / "fig_worked_step_tb07.png")


if __name__ == "__main__":
    main()

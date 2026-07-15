"""Render a synthetic iOS-style Settings screen for the ShowUI spike (no simulator needed).

Origin: original, 
Writes spikes/out/screenshot.png at iPhone 16 Pro pixel size (1206x2622, 3x scale) and
spikes/out/screenshot_truth.json with the true centre of each row (relative 0..1), so
the spike's predictions can be scored, not just eyeballed.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, S = 1206, 2622, 3
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

def font(size, bold=False):
    for p in (["/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc"] +
              [f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"]):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()

img = Image.new("RGB", (W, H), (242, 242, 247))
d = ImageDraw.Draw(img)
d.text((60 * S // 3 * 1, 40), "9:41", font=font(17 * S, True), fill="black")
d.text((16 * S, 100 * S), "Settings", font=font(34 * S, True), fill="black")
d.rounded_rectangle((16 * S, 150 * S, W - 16 * S, 186 * S), radius=10 * S, fill=(227, 227, 233))
d.text((44 * S, 158 * S), "Search", font=font(17 * S), fill=(142, 142, 147))

groups = [
    [("Airplane Mode", (255, 149, 0)), ("Wi-Fi", (0, 122, 255)), ("Bluetooth", (0, 122, 255)),
     ("Cellular", (52, 199, 89))],
    [("General", (142, 142, 147)), ("Accessibility", (0, 122, 255)), ("Camera", (142, 142, 147)),
     ("Display & Brightness", (0, 122, 255)), ("Wallpaper", (90, 200, 250))],
    [("Notifications", (255, 59, 48)), ("Sounds & Haptics", (255, 45, 85)), ("Focus", (88, 86, 214)),
     ("Screen Time", (88, 86, 214))],
]
truth = {}
y = 206 * S
row_h = 44 * S
for g in groups:
    top = y
    d.rounded_rectangle((16 * S, top, W - 16 * S, top + row_h * len(g)), radius=10 * S, fill="white")
    for i, (label, colour) in enumerate(g):
        ry = top + i * row_h
        d.rounded_rectangle((32 * S, ry + 8 * S, 60 * S, ry + 36 * S), radius=7 * S, fill=colour)
        d.text((76 * S, ry + 11 * S), label, font=font(17 * S), fill="black")
        d.text((W - 36 * S, ry + 10 * S), ">", font=font(17 * S, True), fill=(196, 196, 199))
        if i < len(g) - 1:
            d.line((76 * S, ry + row_h, W - 16 * S, ry + row_h), fill=(220, 220, 224), width=2)
        truth[label] = [round((W / 2) / W, 4), round((ry + row_h / 2) / H, 4),
                        [16 * S / W, ry / H, (W - 16 * S) / W, (ry + row_h) / H]]
    y = top + row_h * len(g) + 35 * S

img.save(OUT / "screenshot.png")
(OUT / "screenshot_truth.json").write_text(json.dumps(truth, indent=1))
print(f"saved {OUT/'screenshot.png'} ({W}x{H}) with {len(truth)} labelled rows")

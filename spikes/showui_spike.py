"""Spike 2: can ShowUI-2B ground a UI element on this Mac, and how fast?

Gives one screenshot and one text query to ShowUI and prints the predicted relative
click point [x, y] (0 to 1) plus latency. Feeds decision D-002 (run the VLM locally
or use an approved API as the documented fallback).

Usage:
    python spikes/showui_spike.py --image spikes/out/screenshot.png --query "General"
"""

import argparse
import ast
import time

import torch
from PIL import Image, ImageDraw
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

MODEL_ID = "showlab/ShowUI-2B"
PROCESSOR_ID = "Qwen/Qwen2-VL-2B-Instruct"
MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1344 * 28 * 28
SYSTEM = (
    "Based on the screenshot of the page, I give a text description and you give its "
    "corresponding location. The coordinate represents a clickable location [x, y] for an "
    "element, which is a relative coordinate on the screenshot, scaled from 0 to 1."
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--runs", type=int, default=3)
    args = p.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float16 if device == "mps" else torch.float32
    print(f"device={device} dtype={dtype}")

    t = time.perf_counter()
    model = Qwen2VLForConditionalGeneration.from_pretrained(MODEL_ID, torch_dtype=dtype).to(device)
    processor = AutoProcessor.from_pretrained(PROCESSOR_ID, min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS)
    print(f"model load: {time.perf_counter() - t:.1f}s")

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": SYSTEM},
            {"type": "image", "image": args.image, "min_pixels": MIN_PIXELS, "max_pixels": MAX_PIXELS},
            {"type": "text", "text": args.query},
        ],
    }]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs,
                       padding=True, return_tensors="pt").to(device)

    out_text = ""
    for i in range(args.runs):
        t = time.perf_counter()
        ids = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        trimmed = ids[:, inputs.input_ids.shape[1]:]
        out_text = processor.batch_decode(trimmed, skip_special_tokens=True)[0]
        print(f"run {i + 1}: {(time.perf_counter() - t) * 1000:.0f} ms -> {out_text}")

    try:
        x, y = ast.literal_eval(out_text)
        img = Image.open(args.image).convert("RGB")
        px, py = x * img.width, y * img.height
        d = ImageDraw.Draw(img)
        d.ellipse([px - 18, py - 18, px + 18, py + 18], outline="red", width=6)
        img.save("spikes/out/showui_prediction.png")
        print(f"pixel point: ({px:.0f}, {py:.0f}) saved spikes/out/showui_prediction.png")
    except (ValueError, SyntaxError):
        print("output was not a coordinate; record this as a malformed-output case")


if __name__ == "__main__":
    main()

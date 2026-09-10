"""ShowUI-2B grounding adapter.

ShowUI-2B in grounding mode takes a screenshot and a text description and returns a
relative click point [x, y] in 0..1. The candidate list is not put in the prompt (the
model was not trained on that format); instead the validator enforces the bounded
candidate set after the fact by snapping the point to an element (decision D-008,
proposed).
"""

from __future__ import annotations

import io
import time
from typing import Optional

from ..model import Intent
from . import VLMResult, parse_point, proposal_from_point, query_for_attempt

MODEL_ID = "showlab/ShowUI-2B"
PROCESSOR_ID = "Qwen/Qwen2-VL-2B-Instruct"
MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1344 * 28 * 28
SYSTEM = (
    "Based on the screenshot of the page, I give a text description and you give its "
    "corresponding location. The coordinate represents a clickable location [x, y] for an "
    "element, which is a relative coordinate on the screenshot, scaled from 0 to 1."
)


class ShowUIAdapter:
    name = "showui-2b"

    def __init__(self, revision: Optional[str] = None, max_pixels: int = MAX_PIXELS):
        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if self.device == "mps" else torch.float32
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_ID, revision=revision, torch_dtype=dtype).to(self.device)
        self.model.eval()
        self.max_pixels = max_pixels
        self.processor = AutoProcessor.from_pretrained(PROCESSOR_ID, min_pixels=MIN_PIXELS, max_pixels=max_pixels)

    def propose(self, screenshot_png: bytes, intent: Intent, reason: str,
                candidates: list[dict], screen: tuple[int, int], attempt: int = 0) -> VLMResult:
        import torch
        from PIL import Image
        from qwen_vl_utils import process_vision_info

        query = query_for_attempt(intent, attempt)
        image = Image.open(io.BytesIO(screenshot_png)).convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "text", "text": SYSTEM},
            {"type": "image", "image": image, "min_pixels": MIN_PIXELS, "max_pixels": self.max_pixels},
            {"type": "text", "text": query},
        ]}]
        t = time.perf_counter()
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(text=[text], images=image_inputs, videos=video_inputs,
                                padding=True, return_tensors="pt").to(self.device)
        with torch.no_grad():
            ids = self.model.generate(**inputs, max_new_tokens=32, do_sample=False)
        out = self.processor.batch_decode(ids[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
        latency = (time.perf_counter() - t) * 1000
        return VLMResult(out, proposal_from_point(intent, parse_point(out)), latency,
                         len(SYSTEM) + len(query), len(screenshot_png), len(out), query=query)

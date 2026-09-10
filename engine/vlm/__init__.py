"""VLM adapters. Origin: original, """

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional, Protocol

from ..model import Intent


@dataclass
class VLMResult:
    raw_text: str
    parsed: Optional[dict]          # proposal for the validator, or None if unparseable
    latency_ms: float
    input_chars: int
    image_bytes: int
    output_chars: int
    query: str = ""

    def to_log(self) -> dict:
        return {"query": self.query, "raw_text": self.raw_text, "parsed": self.parsed, "latency_ms": round(self.latency_ms, 1),
                "input_chars": self.input_chars, "image_bytes": self.image_bytes,
                "output_chars": self.output_chars}


class VLMAdapter(Protocol):
    name: str

    def propose(self, screenshot_png: bytes, intent: Intent, reason: str,
                candidates: list[dict], screen: tuple[int, int], attempt: int = 0) -> VLMResult: ...


_POINT = re.compile(r"\[\s*([0-9]*\.?[0-9]+)\s*,\s*([0-9]*\.?[0-9]+)\s*\]")


def parse_point(text: str) -> Optional[tuple[float, float]]:
    m = _POINT.search(text or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def grounding_query(intent: Intent) -> str:
    """Describe the target the way a person would, for a grounding model."""
    parts = [intent.target or ""]
    if intent.type_hint:
        parts.append({"field": "text field", "cell": "row"}.get(intent.type_hint, intent.type_hint))
    q = " ".join(p for p in parts if p).strip()
    if intent.context:
        q += f" in the {intent.context} section"
    return q


def query_for_attempt(intent: Intent, attempt: int) -> str:
    """D-016: decoding is greedy, so repeating an identical query returns an identical answer.
    Attempt 0 uses the short grounding description; any retry uses the full step wording."""
    return grounding_query(intent) if attempt == 0 else intent.text


def proposal_from_point(intent: Intent, point: Optional[tuple[float, float]]) -> Optional[dict]:
    """Grounding models return a location; the action type comes from the step itself."""
    if point is None:
        return None
    p = {"action": intent.action, "x": point[0], "y": point[1], "relative": True}
    if intent.action == "type_text":
        p["text"] = intent.value
    return p


class FakeVLM:
    """Deterministic stand-in for tests: returns a fixed relative point or raw text."""

    name = "fake"

    def __init__(self, point: Optional[tuple[float, float]] = None, raw: Optional[str] = None,
                 by_attempt: Optional[dict] = None):
        self.point, self.raw, self.by_attempt = point, raw, by_attempt or {}
        self.calls: list[dict] = []

    def propose(self, screenshot_png, intent, reason, candidates, screen, attempt: int = 0) -> VLMResult:
        t = time.perf_counter()
        q = query_for_attempt(intent, attempt)
        self.calls.append({"intent": intent.text, "reason": reason, "n_candidates": len(candidates),
                           "attempt": attempt, "query": q})
        point = self.by_attempt.get(attempt, self.point)
        raw = self.raw if self.raw is not None else (f"[{point[0]}, {point[1]}]" if point else "")
        parsed = proposal_from_point(intent, parse_point(raw))
        return VLMResult(raw, parsed, (time.perf_counter() - t) * 1000, len(q), len(screenshot_png or b""),
                         len(raw), query=q)

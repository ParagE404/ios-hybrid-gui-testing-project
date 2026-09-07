"""Validate model-proposed actions before anything touches the app.

Origin: original, 

Only six actions exist: tap, type_text, swipe, navigate_back, wait, reject.
Anything else, anything malformed, out of screen bounds, outside the bounded
candidate set (when required) or inconsistent with the step's intent is rejected
with a reason, and the rejection is logged (proposal, "VLM, comparators and MCP").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .model import Action, Element, Intent, Snapshot
from .resolver import TAPPABLE_STRONG, TEXT_INPUT

# Elements a tap can meaningfully activate. Static content (StaticText, Image, Other) is
# only acceptable through an interactive ancestor (e.g. the label inside a Button).
INTERACTIVE = TAPPABLE_STRONG | TEXT_INPUT | {"Slider", "Stepper", "PickerWheel", "Tab", "SearchField"}

ALLOWED = {"tap", "type_text", "swipe", "navigate_back", "wait", "reject"}
DIRECTIONS = {"up", "down", "left", "right"}
MAX_TEXT = 200
MAX_WAIT_S = 5.0


@dataclass
class ValidatorConfig:
    require_candidate: bool = True   # snapped element must be in the bounded candidate list
    snap_to_element: bool = True     # map a point to the smallest compatible element under it


def _reject(reason: str) -> Action:
    return Action(kind="reject", reason=reason)


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _element_at(snap: Snapshot, x: float, y: float, intent: Intent) -> tuple[Optional[Element], str]:
    """Smallest enabled, visible INTERACTIVE element under the point (D-015).

    Returns (element, "") or (None, reason). A point on static text with no interactive
    ancestor under it (e.g. an alert's title) is rejected as not_interactive.
    """
    hits = sorted((e for e in snap.elements if e.contains(x, y) and e.visible and e.enabled and e.area > 0),
                  key=lambda e: e.area)
    if not hits:
        return None, "no_element_at_point"
    wanted = TEXT_INPUT if intent.action == "type_text" else INTERACTIVE
    for e in hits:
        if e.type in wanted:
            return e, ""
    return None, ("not_text_input" if intent.action == "type_text" else "not_interactive")


def validate(raw: Any, intent: Intent, snap: Snapshot,
             candidate_idxs: Optional[set[int]] = None,
             cfg: Optional[ValidatorConfig] = None) -> Action:
    cfg = cfg or ValidatorConfig()
    if not isinstance(raw, dict):
        return _reject("malformed_output")
    kind = raw.get("action")
    if kind not in ALLOWED:
        return _reject("unsupported_action")
    if kind == "reject":
        return _reject(str(raw.get("reason") or "model_rejected"))

    expected = intent.action
    if kind != expected:
        return _reject("intent_mismatch")

    if kind == "navigate_back":
        return Action(kind="navigate_back")

    if kind == "swipe":
        d = str(raw.get("direction", "")).lower()
        return Action(kind="swipe", direction=d) if d in DIRECTIONS else _reject("bad_direction")

    if kind == "wait":
        s = _num(raw.get("seconds"))
        if s is None or not (0 < s <= MAX_WAIT_S):
            return _reject("bad_wait")
        return Action(kind="wait", seconds=s)

    # tap / type_text need a point
    x, y = _num(raw.get("x")), _num(raw.get("y"))
    if x is None or y is None:
        return _reject("missing_point")
    if raw.get("relative"):
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return _reject("out_of_bounds")
        x, y = x * snap.width, y * snap.height
    if not (0 <= x <= snap.width and 0 <= y <= snap.height):
        return _reject("out_of_bounds")

    el_idx = None
    if cfg.snap_to_element:
        el, why = _element_at(snap, x, y, intent)
        if el is None:
            return _reject(why)
        # An empty candidate set (no_match) leaves the model free to choose.
        if candidate_idxs and cfg.require_candidate:
            ok = el.idx in candidate_idxs or any(a in candidate_idxs for a in el.ancestors) \
                 or any(snap.elements[c].is_ancestor_of(el) or el.is_ancestor_of(snap.elements[c])
                        for c in candidate_idxs)
            if not ok:
                return _reject("outside_candidate_set")
        if kind == "type_text" and el.type not in TEXT_INPUT:
            return _reject("not_text_input")
        el_idx = el.idx

        # Snap to the element's activation point (e.g. a Switch's trailing control).
        x, y = el.tap_point

    if kind == "type_text":
        text = raw.get("text", intent.value)
        if not isinstance(text, str) or not text or len(text) > MAX_TEXT:
            return _reject("bad_text")
        return Action(kind="type_text", x=x, y=y, text=text, element_idx=el_idx)

    return Action(kind="tap", x=x, y=y, element_idx=el_idx)
# Validator update
# Snapping fix

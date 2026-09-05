"""Structured (accessibility-only) resolver: rank candidate elements for an Intent.

Origin: original,  The idea of
combining several weighted attributes into one similarity score follows
similarity-based element localisation (Nass et al., 2023).

Score components (each 0..1):
    text     best weighted similarity over label, identifier, value, placeholder
    type     compatibility of element type with the action and the type hint
    context  whether the element sits inside / below an anchor matching the context phrase
Hard gates (component recorded, score forced to 0, reason available to the router):
    state    element must be enabled and visible with a non-zero size
    type     an incompatible type (e.g. typing into a Button) scores 0

All weights live in ResolverConfig so they can be calibrated on pilot scenarios and
then frozen (decision D-005).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from .model import Candidate, Element, Intent, Resolution, Snapshot

# ---------------------------------------------------------------- text similarity

_NOISE = {"button", "btn", "field", "textfield", "tf", "cell", "row", "label", "lbl", "view",
          "txt", "text", "icon", "image", "img", "switch", "toggle", "tab", "link", "the", "a", "an"}


def tokens(s: Optional[str]) -> list[str]:
    if not s:
        return []
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)          # camelCase -> camel Case
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)         # URLField -> URL Field
    s = re.sub(r"[_\-./:]+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return [t for t in s.lower().split() if t]


def norm_key(s: Optional[str]) -> str:
    return " ".join(t for t in tokens(s) if t not in _NOISE)


def similarity(target: str, text: Optional[str]) -> float:
    """0..1 similarity between the step's target phrase and one element attribute."""
    if not text:
        return 0.0
    a, b = norm_key(target), norm_key(text)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    inter = len(ta & tb)
    if inter:
        recall, precision = inter / len(ta), inter / len(tb)
        f1 = 2 * recall * precision / (recall + precision)
    else:
        f1 = 0.0
    seq = SequenceMatcher(None, a, b).ratio()
    return 0.6 * f1 + 0.4 * seq


# ---------------------------------------------------------------- type compatibility

TEXT_INPUT = {"TextField", "SecureTextField", "SearchField", "TextView"}
TAPPABLE_STRONG = {"Button", "Cell", "Link", "Switch", "Toggle", "MenuItem", "Key", "Icon", "SegmentedControl"}
TAPPABLE_WEAK = {"StaticText", "Image", "Other", "NavigationBar"} | TEXT_INPUT
CONTAINERS = {"Application", "Window", "Table", "CollectionView", "ScrollView", "TabBar",
              "Toolbar", "Alert", "Sheet", "Keyboard", "StatusBar"}

HINT_TYPES = {
    "button": {"Button", "Link"},
    "cell": {"Cell"},
    "tab": {"Button"},
    "switch": {"Switch", "Toggle"},
    "field": TEXT_INPUT,
    "link": {"Link", "Button"},
    "icon": {"Icon", "Image", "Button"},
}


def type_score(el: Element, intent: Intent) -> float:
    if el.type in CONTAINERS:
        return 0.0
    if intent.action == "type_text":
        return 1.0 if el.type in TEXT_INPUT else 0.0
    hinted = HINT_TYPES.get(intent.type_hint or "", set())
    if hinted and el.type in hinted:
        return 1.0
    if el.type in TAPPABLE_STRONG:
        return 0.8 if hinted else 1.0
    if el.type in TAPPABLE_WEAK:
        return 0.5
    return 0.3


def state_ok(el: Element) -> bool:
    return el.enabled and el.visible and el.width > 0 and el.height > 0


# ---------------------------------------------------------------- config

@dataclass
class ResolverConfig:
    w_text: float = 0.6
    w_type: float = 0.25
    w_context: float = 0.15
    field_weights: dict = field(default_factory=lambda: {
        "label": 1.0, "identifier": 0.9, "placeholder": 0.85, "value": 0.6,
    })
    min_text: float = 0.35          # below this an element is not a candidate at all
    collapse_eps: float = 0.05      # nested candidates within this text score are merged
    max_candidates: int = 10        # bound on the list kept (and shown to the VLM)
    segment_weight: float = 0.95    # combined labels "Milk, Qty 1": score of a matching segment


# ---------------------------------------------------------------- resolver

def label_similarity(target: str, text: Optional[str], segment_weight: float) -> tuple[float, str]:
    """Similarity that also handles combined labels such as "Milk, Qty 1".

    SwiftUI and UIKit often merge child texts into one accessibility label joined by
    ", ". The first segment usually carries the element's name, so a segment match is
    scored slightly below an exact whole-label match.
    """
    whole = similarity(target, text)
    best, key = whole, norm_key(text)
    if text and ", " in text:
        for seg in text.split(", "):
            s = segment_weight * similarity(target, seg)
            if s > best:
                best, key = s, norm_key(seg)
    return best, key


def _text_score(el: Element, target: str, cfg: ResolverConfig) -> tuple[float, Optional[str], str]:
    best, best_field, best_key = 0.0, None, ""
    for fname, value in (("label", el.label), ("identifier", el.identifier),
                         ("placeholder", el.placeholder), ("value", el.value)):
        if not value:
            continue
        sim, key = label_similarity(target, value, cfg.segment_weight) if fname == "label" \
            else (similarity(target, value), norm_key(value))
        s = cfg.field_weights[fname] * sim
        if s > best:
            best, best_field, best_key = s, fname, key
    return best, best_field, best_key


def _context_score(el: Element, snap: Snapshot, context: str) -> float:
    anchors = [a for a in snap.elements
               if a.idx != el.idx and max(label_similarity(context, a.label, 0.95)[0],
                                          similarity(context, a.name)) >= 0.8]
    if not anchors:
        return 0.0
    def row(e: Element) -> Optional[int]:
        if e.type == "Cell":
            return e.idx
        return next((i for i in reversed(e.ancestors) if snap.elements[i].type == "Cell"), None)

    best = 0.0
    el_row = row(el)
    for a in anchors:
        if a.is_ancestor_of(el):
            return 1.0
        a_row = row(a)
        if a_row is not None:
            # Anchor is a row (or text inside one): only the same row counts.
            if a_row == el_row:
                return 1.0
            continue
        # Section header pattern: anchor sits above the element, same column.
        dy = el.y - (a.y + a.height)
        if dy >= -2:
            horizontal_overlap = min(el.x + el.width, a.x + a.width) - max(el.x, a.x) > 0
            if horizontal_overlap and snap.height:
                best = max(best, max(0.0, 1.0 - dy / (0.5 * snap.height)))
    return best


_CONTENT_TYPES = {"StaticText", "Image", "Icon", "Other"}


def _collapse_nested(cands: list[Candidate], eps: float) -> tuple[list[Candidate], list[dict]]:
    """Merge nested candidates that are really one control.

    Two cases (both seen in real XCUITest page source):
      1. Content inside a control: a StaticText or Image nested in a Button, Cell, Switch
         or text field is that control's content, so the content node is dropped whatever
         its text score (e.g. StaticText "Milk" inside Button "Milk, Qty 1").
      2. Two nested nodes with near-identical text scores: keep the more actionable
         type, or the ancestor when types tie.
    """
    removed: set[int] = set()
    log: list[dict] = []
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            if a.element.idx in removed or b.element.idx in removed:
                continue
            ea, eb = a.element, b.element
            if ea.is_ancestor_of(eb):
                anc, desc = a, b
            elif eb.is_ancestor_of(ea):
                anc, desc = b, a
            else:
                continue
            control = anc.element.type in TAPPABLE_STRONG or anc.element.type in TEXT_INPUT
            if control and desc.element.type in _CONTENT_TYPES:
                drop, keep, why = desc, anc, "content_of_control"
            elif abs(a.components["text"] - b.components["text"]) <= eps + 1e-9:
                ta, tb = a.components["type"], b.components["type"]
                if ta != tb:
                    drop = b if ta > tb else a
                else:
                    drop = desc
                keep = a if drop is b else b
                why = "same_text"
            else:
                continue
            removed.add(drop.element.idx)
            log.append({"dropped": drop.element.idx, "kept": keep.element.idx, "why": why})
    return [c for c in cands if c.element.idx not in removed], log


def resolve(snap: Snapshot, intent: Intent, cfg: Optional[ResolverConfig] = None) -> Resolution:
    cfg = cfg or ResolverConfig()
    t0 = time.perf_counter()
    if not intent.target:
        return Resolution(intent=intent, candidates=[], resolution_ms=0.0)

    cands: list[Candidate] = []
    for el in snap.elements:
        text, fname, key = _text_score(el, intent.target, cfg)
        if text < cfg.min_text:
            continue
        ty = type_score(el, intent)
        st = state_ok(el)
        comps = {"text": text, "type": ty, "state": 1.0 if st else 0.0}
        weights = cfg.w_text + cfg.w_type
        total = cfg.w_text * text + cfg.w_type * ty
        if intent.context:
            ctx = _context_score(el, snap, intent.context)
            comps["context"] = ctx
            total += cfg.w_context * ctx
            weights += cfg.w_context
        score = total / weights
        if ty == 0.0 or not st:
            score = 0.0
        cands.append(Candidate(element=el, score=score, components=comps, matched_field=fname, text_key=key))

    cands.sort(key=lambda c: (c.score, c.components["text"]), reverse=True)
    cands, collapsed = _collapse_nested(cands, cfg.collapse_eps)
    cands = cands[: cfg.max_candidates]
    return Resolution(intent=intent, candidates=cands, collapsed=collapsed,
                      resolution_ms=(time.perf_counter() - t0) * 1000)

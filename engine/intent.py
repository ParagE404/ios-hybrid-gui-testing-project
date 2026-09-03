"""Parse constrained natural-language test steps into Intents.

Origin: original, 

Design (decision D-006, proposed): steps use a controlled English with quoted targets,
for example:
    Tap the 'Add item' button
    Tap 'Wi-Fi' in the 'Network' section
    Type 'Milk' into the 'Item name' field
    Toggle the 'Dark mode' switch
    Swipe up / Scroll down
    Go back
    Wait 2 seconds
Quoting keeps the parsing step deterministic so that the experiment measures element
resolution, not language understanding. Unquoted targets are still accepted
(quoted=False) and logged, as a threat to validity rather than a silent failure.
"""

from __future__ import annotations

import re

from .model import Intent

_Q = r"['\"‘’“”]"                 # straight and curly quotes
_QUOTED = re.compile(rf"{_Q}(.+?){_Q}")

TYPE_WORDS = {
    "button": "button", "btn": "button",
    "cell": "cell", "row": "cell", "item": "cell",
    "tab": "tab",
    "switch": "switch", "toggle": "switch",
    "field": "field", "text field": "field", "textfield": "field", "search field": "field",
    "search bar": "field", "box": "field",
    "link": "link",
    "icon": "icon", "image": "icon",
}

_TAP = re.compile(r"^(tap|press|click|select|open|choose|toggle|turn on|turn off|switch on|switch off)\b", re.I)
_TYPE = re.compile(r"^(type|enter|input|fill in|write)\b", re.I)
_SWIPE = re.compile(r"^(swipe|scroll)\s+(up|down|left|right)\b", re.I)
_BACK = re.compile(r"^(go back|navigate back|back)\b", re.I)
_WAIT = re.compile(r"^wait(?:\s+(?:for\s+)?(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds?)?)?\b", re.I)
_CONTEXT = re.compile(rf"\b(?:in|under|within|inside|on)\s+(?:the\s+)?{_Q}(.+?){_Q}", re.I)


def _type_hint(text: str, after: int) -> str | None:
    tail = text[after:].lower()
    # Take the first type word that appears right after the target.
    m = re.match(r"\s*(text field|search field|search bar|[a-z]+)", tail)
    if m and m.group(1) in TYPE_WORDS:
        return TYPE_WORDS[m.group(1)]
    return None


def _strip_type_words(s: str) -> str:
    words = [w for w in re.split(r"\s+", s) if w.lower() not in TYPE_WORDS and w.lower() not in ("the", "a", "an")]
    return " ".join(words).strip()


def parse_step(text: str) -> Intent:
    raw = text.strip()
    t = raw.rstrip(".")

    if _BACK.match(t):
        return Intent(text=raw, action="navigate_back", target=None)

    m = _SWIPE.match(t)
    if m:
        return Intent(text=raw, action="swipe", value=m.group(2).lower())

    m = _WAIT.match(t)
    if m:
        return Intent(text=raw, action="wait", value=m.group(1) or "1")

    context = None
    cm = _CONTEXT.search(t)

    if _TYPE.match(t):
        quotes = list(_QUOTED.finditer(t))
        if len(quotes) >= 2:
            value, target_m = quotes[0].group(1), quotes[1]
            if cm and cm.start() < target_m.start():
                cm = None  # "into the" not a context phrase
            hint = _type_hint(t, target_m.end()) or "field"
            return Intent(text=raw, action="type_text", target=target_m.group(1), value=value,
                          type_hint=hint, context=None)
        if len(quotes) == 1:
            rest = t[quotes[0].end():]
            rm = re.search(r"\b(?:into|in)\s+(?:the\s+)?(.+)$", rest, re.I)
            target = _strip_type_words(rm.group(1)) if rm else None
            return Intent(text=raw, action="type_text", target=target or None, value=quotes[0].group(1),
                          type_hint="field", quoted=False)
        raise ValueError(f"Cannot parse type step (needs a quoted value): {raw!r}")

    if _TAP.match(t):
        verb = _TAP.match(t).group(1).lower()
        quotes = list(_QUOTED.finditer(t))
        if quotes:
            target_m = quotes[0]
            if cm and cm.start() < target_m.start():
                cm = None
            if cm:
                context = cm.group(1)
            hint = _type_hint(t, target_m.end())
            if verb.startswith(("toggle", "turn", "switch")) and hint is None:
                hint = "switch"
            return Intent(text=raw, action="tap", target=target_m.group(1), type_hint=hint, context=context)
        rest = t[len(verb):]
        target = _strip_type_words(rest)
        hint = None
        for w in re.split(r"\s+", rest.lower()):
            if w in TYPE_WORDS:
                hint = TYPE_WORDS[w]
        if not target:
            raise ValueError(f"Cannot parse tap step (no target): {raw!r}")
        return Intent(text=raw, action="tap", target=target, type_hint=hint, quoted=False)

    raise ValueError(f"Unsupported step: {raw!r}")
# Parser update

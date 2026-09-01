"""Normalise XCUITest page source (XML) into a flat list of Elements.

Origin: original, 

Appium's XCUITest driver returns XML where each node is an XCUIElementType* tag with
attributes such as type, name, label, value, enabled, visible, accessible, x, y,
width, height (Appium Project, 2026a). This module keeps document order, depth,
parent and ancestor chain so the resolver can reason about nesting.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from typing import Optional

from .model import Element, Snapshot

_PREFIX = "XCUIElementType"


def _bool(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("true", "1", "yes")


def _int(v: Optional[str]) -> int:
    try:
        return int(float(v)) if v is not None else 0
    except ValueError:
        return 0


def _text(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _type(node: ET.Element) -> str:
    t = node.get("type") or node.tag
    return t[len(_PREFIX):] if t.startswith(_PREFIX) else t


def parse_page_source(xml: str, retrieval_ms: Optional[float] = None) -> Snapshot:
    root = ET.fromstring(xml)
    # Appium wraps the tree in <AppiumAUT>; start from its children.
    starts = list(root) if root.tag == "AppiumAUT" else [root]

    elements: list[Element] = []

    def visit(node: ET.Element, depth: int, parent: Optional[int], ancestors: tuple[int, ...]) -> None:
        idx = len(elements)
        el = Element(
            idx=idx,
            type=_type(node),
            name=_text(node.get("name")),
            label=_text(node.get("label")),
            value=_text(node.get("value")),
            placeholder=_text(node.get("placeholderValue")),
            enabled=_bool(node.get("enabled"), True),
            visible=_bool(node.get("visible"), True),
            accessible=_bool(node.get("accessible"), False),
            x=_int(node.get("x")), y=_int(node.get("y")),
            width=_int(node.get("width")), height=_int(node.get("height")),
            depth=depth, parent=parent, ancestors=ancestors,
        )
        elements.append(el)
        for child in node:
            visit(child, depth + 1, idx, ancestors + (idx,))

    for s in starts:
        visit(s, 0, None, ())

    app = next((e for e in elements if e.type == "Application"), elements[0] if elements else None)
    width = app.width if app else 0
    height = app.height if app else 0
    return Snapshot(
        elements=elements,
        width=width,
        height=height,
        source_sha1=hashlib.sha1(xml.encode("utf-8")).hexdigest(),
        source_chars=len(xml),
        retrieval_ms=retrieval_ms,
    )

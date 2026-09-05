"""Element matchers used by step oracles and scenario postconditions.

Origin: original, 

A matcher is a small dict, for example:
    {type: Button, label: "Add item"}
    {type: Cell, label_contains: "Milk"}
    {type: Switch, label: "Dark mode", value: "1"}
    {type: Button, label: "Delete", within_label: "Milk"}   # ancestor has this label
    {identifier: "itemNameField"}
    {type: Button, label_contains: Delete, in_row: Eggs}    # same table row (Cell) as text "Eggs"
Keys are ANDed. Postcondition checks: exists, absent, count (n), above (other). Matchers are evaluated on normalised snapshots, so oracles do not
depend on the engine's own resolver (which would be circular).
"""

from __future__ import annotations

from .model import Element, Snapshot

KEYS = {"type", "label", "label_contains", "identifier", "name", "value", "within_label", "in_row", "visible", "enabled"}


def _eq(a, b) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def matches(el: Element, snap: Snapshot, spec: dict) -> bool:
    unknown = set(spec) - KEYS
    if unknown:
        raise ValueError(f"Unknown matcher keys: {sorted(unknown)}")
    if "type" in spec and el.type != spec["type"]:
        return False
    if "label" in spec and not _eq(el.label, spec["label"]):
        return False
    if "label_contains" in spec and spec["label_contains"].lower() not in (el.label or "").lower():
        return False
    if "identifier" in spec and el.identifier != spec["identifier"]:
        return False
    if "name" in spec and el.name != spec["name"]:
        return False
    if "value" in spec and not _eq(el.value, str(spec["value"])):
        return False
    if "visible" in spec and el.visible != bool(spec["visible"]):
        return False
    if "enabled" in spec and el.enabled != bool(spec["enabled"]):
        return False
    if "in_row" in spec:
        row = next((a for a in reversed(el.ancestors) if snap.elements[a].type == "Cell"), None)
        if row is None:
            return False
        needle = str(spec["in_row"]).lower()
        if not any(row in e.ancestors and needle in (e.label or "").lower()
                   for e in snap.elements if e.idx != el.idx):
            return False
    if "within_label" in spec:
        if not any(_eq(snap.elements[a].label, spec["within_label"]) for a in el.ancestors):
            return False
    return True


def find(snap: Snapshot, spec: dict) -> list[Element]:
    return [e for e in snap.elements if matches(e, snap, spec)]


def check(snap: Snapshot, cond: dict) -> tuple[bool, str]:
    """Evaluate one postcondition. Returns (passed, explanation)."""
    kind = cond.get("check", "exists")
    spec = cond.get("element", {})
    found = find(snap, spec)
    if kind == "exists":
        return bool(found), f"exists {spec}: {len(found)} found"
    if kind == "absent":
        return not found, f"absent {spec}: {len(found)} found"
    if kind == "count":
        n = int(cond["n"])
        return len(found) == n, f"count {spec}: expected {n}, found {len(found)}"
    if kind == "above":
        other = find(snap, cond["other"])
        if not found or not other:
            return False, f"above {spec} vs {cond['other']}: missing ({len(found)}, {len(other)})"
        ok = min(e.y for e in found) < min(e.y for e in other)
        return ok, f"above {spec} vs {cond['other']}: {ok}"
    raise ValueError(f"Unknown postcondition check: {kind}")

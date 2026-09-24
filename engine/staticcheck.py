"""Static benchmark check: evaluate scenario steps against saved page sources.

Origin: original, 

Purpose: verify the BENCHMARK (scripted locators resolve, oracles match, step text
parses) before any live run. It is approximate: each step is checked against a saved
screen (`screen:` in the YAML), which may differ in state from the live screen.

Bias control (D-013): by default, resolver routes are reported for the BASELINE
condition only. For perturbed screens only the scripted locator and the oracle are
checked, so the resolver is never tuned by looking at how it does on formal perturbed
cases. Thresholds are calibrated on pilot scenarios only (D-005).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from . import matchers
from .model import Snapshot
from .normalise import parse_page_source
from .resolver import resolve
from .router import route
from .scenario import Scenario

_XP_ATTR = re.compile(r'^//XCUIElementType(\w+)\[@(name|label)="(.+)"\]$')
_XP_INDEX = re.compile(r'^\(//XCUIElementType(\w+)\)\[(\d+)\]$')
_PRED = re.compile(r"^(label|name)\s*==\s*'(.+)'$")


def scripted_matches(snap: Snapshot, loc: dict) -> Optional[int]:
    """Number of elements the scripted locator would match, or None if not evaluable statically."""
    strat, v = loc["strategy"], loc["value"]
    els = [e for e in snap.elements if e.visible]
    if strat == "accessibility_id":
        return sum(1 for e in els if e.name == v)
    if strat == "xpath":
        m = _XP_ATTR.match(v)
        if m:
            t, attr, val = m.groups()
            return sum(1 for e in els if e.type == t and getattr(e, attr) == val)
        m = _XP_INDEX.match(v)
        if m:
            t, n = m.group(1), int(m.group(2))
            return 1 if len([e for e in els if e.type == t]) >= n else 0
        return None
    if strat == "predicate":
        m = _PRED.match(v)
        if m:
            attr, val = m.groups()
            return sum(1 for e in els if getattr(e, attr) == val)
    return None


def _oracle_hits(snap: Snapshot, oracle: Optional[dict]) -> Optional[int]:
    return None if not oracle else len(matchers.find(snap, oracle))


def check_scenario(scn: Scenario, pagesource: Path, show_perturbed_routes: bool = False) -> list[dict]:
    rows = []
    conditions = [("baseline", "baseline")]
    if scn.perturbation:
        flag = scn.perturbation.launch_args[-1] if scn.perturbation.launch_args else None
        conditions.append(("perturbed", flag))
    for cond, folder in conditions:
        for i, step in enumerate(scn.steps):
            screen = getattr(step, "screen", None)
            row = {"scenario": scn.id, "condition": cond, "step": i, "text": step.text, "screen": screen}
            if not screen:
                row["note"] = "no screen"
                rows.append(row)
                continue
            f = pagesource / folder / f"{screen}.xml"
            if not f.exists():
                row["note"] = f"missing {f.relative_to(pagesource)}"
                rows.append(row)
                continue
            snap = parse_page_source(f.read_text(encoding="utf-8"))
            if step.scripted:
                row["scripted_matches"] = scripted_matches(snap, step.scripted)
            oracle = step.oracle_for(cond)
            row["oracle_matches"] = _oracle_hits(snap, oracle)
            if oracle:
                # Metadata the target actually exposes (itself and its descendants). For category 4
                # this must be empty or generic, or the perturbation leaks its meaning (pilot finding).
                tgt = matchers.find(snap, oracle)
                labels = {e.label for t in tgt for e in [t] + [d for d in snap.elements if t.is_ancestor_of(d)]
                          if e.label}
                row["target_labels"] = "|".join(sorted(labels))
            if cond == "baseline" or show_perturbed_routes:
                if step.intent.action in ("tap", "type_text"):
                    res = resolve(snap, step.intent)
                    dec = route(res)
                    row["route"], row["reason"] = dec.route, dec.reason
                    if dec.chosen:
                        el = dec.chosen.element
                        row["chosen"] = f"{el.type}:{el.label or el.name}"
                        row["score"] = round(dec.chosen.score, 3)
                        row["margin"] = None if dec.margin is None else round(dec.margin, 3)
                        if oracle:
                            related = [el] + [snap.elements[a] for a in el.ancestors] + \
                                      [e for e in snap.elements if el.is_ancestor_of(e)]
                            row["oracle_ok"] = any(matchers.matches(e, snap, oracle) for e in related)
            rows.append(row)
    return rows

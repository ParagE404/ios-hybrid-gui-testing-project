"""Scenario format: load and validate benchmark YAML files.

Origin: original, 

Example (benchmark/scenarios/tb-01.yaml):

    id: tb-01
    app: testbed
    title: Add an item to the shopping list
    pilot: false
    initial_state: {launch_args: ["-resetData"]}
    steps:
      - step: "Tap the 'Add item' button"
        scripted: {strategy: accessibility_id, value: addItemButton}
        oracle: {type: Button, label: "Add item"}
      - step: "Type 'Milk' into the 'Item name' field"
        scripted: {strategy: accessibility_id, value: itemNameField}
        oracle: {type: TextField}
      - step: "Tap the 'Save' button"
        scripted: {strategy: accessibility_id, value: saveButton}
        expect_after: {check: exists, element: {type: Cell, label_contains: Milk}}
    postconditions:
      - {check: exists, element: {type: Cell, label_contains: Milk}}
    perturbation:
      kind: identifier_rename
      description: addItemButton renamed to addButton_v2
      launch_args: ["-perturb", "identifier_rename"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .intent import parse_step
from .model import Intent

PERTURBATION_KINDS = {
    "identifier_rename", "identifier_removal",
    "hierarchy_insertion", "hierarchy_restructure",
    "duplicate_label", "generic_label",
    "weak_metadata",
}
LOCATOR_STRATEGIES = {"accessibility_id", "xpath", "predicate", "class_chain"}


@dataclass
class Step:
    text: str
    intent: Intent
    scripted: Optional[dict] = None
    oracle: Optional[dict] = None
    expect_after: Optional[dict] = None
    screen: Optional[str] = None        # saved page-source name for static checks (engine.staticcheck)
    oracle_perturbed: Optional[dict] = None   # oracle for the perturbed condition, when the target's metadata changes

    def oracle_for(self, condition: str) -> Optional[dict]:
        if condition == "perturbed" and self.oracle_perturbed:
            return self.oracle_perturbed
        return self.oracle


@dataclass
class Perturbation:
    kind: str
    description: str
    launch_args: list[str] = field(default_factory=list)
    patch: Optional[str] = None


@dataclass
class Scenario:
    id: str
    app: str
    title: str
    steps: list[Step]
    postconditions: list[dict]
    perturbation: Optional[Perturbation]
    initial_state: dict = field(default_factory=dict)
    pilot: bool = False
    category: Optional[int] = None          # perturbation category 1..4 (benchmark-design.md)
    expected_outcome: str = ""              # written BEFORE formal runs (bias control)
    path: Optional[Path] = None


def _err(path, msg):
    raise ValueError(f"{path}: {msg}")


def load_scenario(path: str | Path) -> Scenario:
    path = Path(path)
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    for k in ("id", "app", "title", "steps", "postconditions"):
        if k not in d:
            _err(path, f"missing '{k}'")
    if not d["postconditions"]:
        _err(path, "at least one postcondition is required")

    steps = []
    for i, s in enumerate(d["steps"]):
        if "step" not in s:
            _err(path, f"step {i}: missing 'step' text")
        try:
            intent = parse_step(s["step"])
        except ValueError as e:
            _err(path, f"step {i}: {e}")
        sc = s.get("scripted")
        if intent.action in ("tap", "type_text"):
            if not sc:
                _err(path, f"step {i}: tap/type steps need a 'scripted' locator for the baseline")
            if sc.get("strategy") not in LOCATOR_STRATEGIES:
                _err(path, f"step {i}: bad scripted strategy {sc.get('strategy')!r}")
        steps.append(Step(text=s["step"], intent=intent, scripted=sc,
                          oracle=s.get("oracle"), expect_after=s.get("expect_after"),
                          screen=s.get("screen"), oracle_perturbed=s.get("oracle_perturbed")))

    pert = None
    if d.get("perturbation"):
        p = d["perturbation"]
        if p.get("kind") not in PERTURBATION_KINDS:
            _err(path, f"unknown perturbation kind {p.get('kind')!r}")
        pert = Perturbation(kind=p["kind"], description=p.get("description", ""),
                            launch_args=p.get("launch_args", []), patch=p.get("patch"))
    elif not d.get("pilot", False):
        _err(path, "formal scenarios need a matched perturbation")

    return Scenario(id=d["id"], app=d["app"], title=d["title"], steps=steps,
                    postconditions=d["postconditions"], perturbation=pert,
                    initial_state=d.get("initial_state", {}), pilot=bool(d.get("pilot", False)),
                    category=d.get("category"), expected_outcome=d.get("expected_outcome", ""),
                    path=path)


def load_dir(directory: str | Path) -> list[Scenario]:
    return [load_scenario(p) for p in sorted(Path(directory).glob("*.yaml"))]

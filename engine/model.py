"""Core data types shared by the engine.

Origin: original,  See docs/ai-use-log.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Element:
    """One node from XCUITest page source, normalised.

    Note on identifiers: XCUITest page source has no separate identifier attribute.
    `name` holds the accessibilityIdentifier when the developer set one, otherwise it
    falls back to the label. `identifier` below is therefore only populated when
    name differs from label, which is the best evidence of a developer-set id.
    """

    idx: int
    type: str                      # "Button", "Cell", ... ("XCUIElementType" prefix removed)
    name: Optional[str]
    label: Optional[str]
    value: Optional[str]
    placeholder: Optional[str]
    enabled: bool
    visible: bool
    accessible: bool
    x: int
    y: int
    width: int
    height: int
    depth: int
    parent: Optional[int]
    ancestors: tuple[int, ...] = ()

    @property
    def identifier(self) -> Optional[str]:
        if self.name and self.name != self.label:
            return self.name
        return None

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def tap_point(self) -> tuple[float, float]:
        """Where to tap to activate the element.

        iOS renders a Switch's control at the trailing edge of its row; tapping the
        row centre (the label) does not toggle it. Every route (scripted, structured,
        VLM-snapped) uses this same rule so execution never differs between configs.
        """
        if self.type in ("Switch", "Toggle") and self.width > 120:
            return (self.x + self.width - 32, self.y + self.height / 2)
        return self.center

    @property
    def area(self) -> int:
        return max(self.width, 0) * max(self.height, 0)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def is_ancestor_of(self, other: "Element") -> bool:
        return self.idx in other.ancestors

    def summary(self) -> dict:
        return {
            "idx": self.idx, "type": self.type, "label": self.label,
            "identifier": self.identifier, "value": self.value,
            "enabled": self.enabled, "visible": self.visible,
            "rect": [self.x, self.y, self.width, self.height],
        }


@dataclass
class Snapshot:
    elements: list[Element]
    width: int
    height: int
    source_sha1: str
    source_chars: int
    retrieval_ms: Optional[float] = None

    def by_idx(self, idx: int) -> Element:
        return self.elements[idx]


@dataclass(frozen=True)
class Intent:
    """A parsed natural-language test step."""

    text: str                      # original step text, sent unchanged to the VLM
    action: str                    # tap | type_text | swipe | navigate_back | wait
    target: Optional[str] = None
    value: Optional[str] = None    # text to type, or swipe direction, or wait seconds
    type_hint: Optional[str] = None
    context: Optional[str] = None  # "in the 'Account' section"
    quoted: bool = True            # whether the target was explicitly quoted


@dataclass
class Candidate:
    element: Element
    score: float
    components: dict = field(default_factory=dict)
    matched_field: Optional[str] = None
    text_key: str = ""             # normalised text that matched, for duplicate detection

    def to_log(self) -> dict:
        return {
            "idx": self.element.idx, "type": self.element.type, "label": self.element.label,
            "identifier": self.element.identifier, "score": round(self.score, 4),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "matched_field": self.matched_field,
        }


@dataclass
class Resolution:
    intent: Intent
    candidates: list[Candidate]    # ranked, best first
    collapsed: list[dict] = field(default_factory=list)
    resolution_ms: float = 0.0

    @property
    def top(self) -> Optional[Candidate]:
        return self.candidates[0] if self.candidates else None

    @property
    def second(self) -> Optional[Candidate]:
        return self.candidates[1] if len(self.candidates) > 1 else None


@dataclass
class RouteDecision:
    route: str                     # "structured" | "fallback"
    reason: str                    # see engine.router.REASONS
    chosen: Optional[Candidate]
    margin: Optional[float]

    def to_log(self) -> dict:
        return {
            "route": self.route, "reason": self.reason,
            "chosen_idx": self.chosen.element.idx if self.chosen else None,
            "margin": None if self.margin is None else round(self.margin, 4),
        }


@dataclass(frozen=True)
class Action:
    """A validated, executable action. Coordinates are in screen points."""

    kind: str                      # tap | type_text | swipe | navigate_back | wait | reject
    x: Optional[float] = None
    y: Optional[float] = None
    text: Optional[str] = None
    direction: Optional[str] = None
    seconds: Optional[float] = None
    element_idx: Optional[int] = None
    reason: Optional[str] = None   # for reject

    def to_log(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

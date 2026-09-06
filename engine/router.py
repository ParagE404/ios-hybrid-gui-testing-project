"""Confidence router: accept the structured result or route to VLM fallback.

Origin: original, 

A deterministic action is accepted only when the best candidate clears a calibrated
threshold AND is separated from the runner-up by a margin (proposal, "System design
and routing"). Otherwise a reason code explains why fallback was needed; these codes
are the basis of the failure analysis in Chapter 4.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Resolution, RouteDecision

OK = "ok"
NO_MATCH = "no_match"
LOW_SCORE = "low_score"
LOW_MARGIN = "low_margin"
DUPLICATE_LABEL = "duplicate_label"
INCOMPATIBLE_STATE = "incompatible_state"
UNRESOLVED_NESTING = "unresolved_nesting"
NOT_APPLICABLE = "not_applicable"     # actions with no target (swipe, back, wait)

REASONS = (OK, NO_MATCH, LOW_SCORE, LOW_MARGIN, DUPLICATE_LABEL, INCOMPATIBLE_STATE,
           UNRESOLVED_NESTING, NOT_APPLICABLE)


@dataclass
class RouterConfig:
    # Frozen 18 Oct 2026 from pilot round 2 (analysis/calibrate.py, experiments/calibration.json), D-005.
    threshold: float = 0.66
    margin: float = 0.09


def route(res: Resolution, cfg: RouterConfig | None = None) -> RouteDecision:
    cfg = cfg or RouterConfig()
    intent = res.intent
    if intent.action in ("swipe", "navigate_back", "wait"):
        return RouteDecision("structured", NOT_APPLICABLE, None, None)

    top, second = res.top, res.second
    if top is None:
        return RouteDecision("fallback", NO_MATCH, None, None)

    # Best text match exists but is disabled, hidden or the wrong type.
    if top.score == 0.0:
        reason = INCOMPATIBLE_STATE if top.components.get("state") == 0.0 else LOW_SCORE
        return RouteDecision("fallback", reason, top, None)

    margin = top.score - second.score if second else top.score
    if top.score < cfg.threshold:
        return RouteDecision("fallback", LOW_SCORE, top, margin)

    if second is not None and margin < cfg.margin:
        if top.text_key and top.text_key == second.text_key:
            return RouteDecision("fallback", DUPLICATE_LABEL, top, margin)
        ta, tb = top.element, second.element
        if ta.is_ancestor_of(tb) or tb.is_ancestor_of(ta):
            return RouteDecision("fallback", UNRESOLVED_NESTING, top, margin)
        return RouteDecision("fallback", LOW_MARGIN, top, margin)

    return RouteDecision("structured", OK, top, margin)
# Router update

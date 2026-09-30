# Design decision and component attribution register
Promised in the proposal's risk register. Each decision gives the options, the evidence, and the rationale. These feed Chapters 3, 6 and 7 and the BCS requirement for "rationale for design/implementation decisions".

## Decisions

### D-001 Native execution through Appium XCUITest, not Playwright (accepted, proposal)
- **Date:** 2026-06-26
- **Options:** Playwright MCP with iPhone emulation; Appium XCUITest; XCUITest directly in Swift.
- **Rationale:** Playwright emulates browser viewport, user agent and touch, not native UIKit/SwiftUI. Appium exposes XCTest-derived attributes to Python and has an MCP ecosystem.
- **Source:** proposal, Critical Context.

### D-002 VLM hosting: local ShowUI-2B on M4 Pro vs approved API (decided: local)
- **Date:** 2026-09-05
- **Evidence (spikes/showui_batch.py):** synthetic 1206x2622 Settings screen, 13 labelled rows, MPS, float16. model load 6.1 s; 12/13 hits; latency median 3,215 ms.
- **Live evidence (pilot round 1):** 6 calls, 3.2 to 3.9 s each; 1 accepted and correct (p-05 picker).
- **Decision rule:** Local if median latency under about 10 s and outputs parseable. Both met, so the VLM runs locally.
- **Runtime implication:** about 3.2 s per fallback call, so the 432-run experiment fits overnight.

### D-006 Step language: controlled English with quoted targets (confirmed)
- **Date:** 2026-09-05
- **Proposed:** controlled English with quoted targets parsed by rules.
- **Rationale:** Parsing stays deterministic, so results measure element resolution rather than language understanding.

### D-007 Router uncertainty behavior (confirmed)
- **Date:** 2026-09-05
- **Proposed:** "best_effort" for both \`a11y_on_uncertain\` and \`hybrid_on_reject\`.
- **Rationale:** This gives the accessibility-only baseline its strongest fair form, so any hybrid gain is not inflated.

### D-008 VLM Constraints (confirmed)
- **Date:** 2026-09-05
- **Mechanism:** validator snaps the predicted point to the smallest compatible element and rejects it if that element is outside the resolver's candidate set.

### D-009 Execution primitive shared by all routes (confirmed)
- **Date:** 2026-09-05
- **Logic:** All routes tap at screen coordinates through \`mobile: tap\`; scripted finds by locator and clicks. Same backend for all three configurations.

### D-010 Step oracle (confirmed)
- **Date:** 2026-09-05
- **Logic:** Correctness is judged by an author-written matcher (\`oracle\`) on the pre-action snapshot, independent of the resolver.

### D-011 Scripted baseline locator policy (proposed 12 Sep 2026)
- **Initial Rule (12 Sep 2026):** (1) developer identifier; (2) XPath on unique name; (3) positional XPath.
- **Rationale:** mechanical application prevents author bias.

### D-012 Activation point for switches (proposed)
- **Date:** 2026-09-05
- **Logic:** All routes use \`Element.tap_point\` (trailing edge minus 32 pt for switches wider than 120 pt).

### D-013 Separating development from evaluation (adopted)
- **Date:** 2026-09-05
- **Logic:** Engine fixes made from BASELINE testbed screens before the freeze are development.
- **Static check result (10 Sep 2026):** baseline steps resolve through structured route; perturbed scripted locators break exactly at designed steps.

### D-014 Formal run protocol (pre-registered)
- **Date:** 2026-09-10
- **Implementation:** \`engine/batch.py\`. Repetition blocks with shuffled scenario order. Fresh app launch with \`-resetData\` before every run.

### D-015 Validator snaps only to interactive elements (pilot finding)
- **Date:** 2026-09-15
- **Finding:** Pilot p-02 showed ShowUI pointing at an alert title.
- **Decision:** point must fall inside an enabled, visible interactive element.

### D-016 VLM retry query (pilot finding)
- **Date:** 2026-09-15
- **Finding:** Identical calls returned the same point.
- **Decision:** Attempt 1 uses short grounding description; retry uses full step wording.

### D-017 Category 4 icons must carry no symbol semantics (pilot finding)
- **Date:** 2026-09-15
- **Finding:** SF Symbol labels ("Edit") leaked into accessibility metadata.
- **Decision:** \`UnlabelledSymbol\` redraws the symbol into a plain bitmap.

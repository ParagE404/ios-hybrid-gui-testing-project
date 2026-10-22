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

### D-003 External apps (confirmed)
- **Date:** 2026-10-11
- **Selection:** Testbed "Errands" (SwiftUI, own), SyncUps by Point-Free (SwiftUI, MIT), NetNewsWire by Ranchero Software (mostly UIKit, MIT).
- **Rationale:** one controlled app for internal validity, two independent real apps for external validity, both SwiftUI and UIKit.
- **Pinned commits:**
  - SyncUps: @ 170bc1ad... Bundle id co.pointfree.SyncUps.
  - NetNewsWire: @ bb5ab3dc... Bundle id uk.ac.city.parag.NetNewsWire.iOS-DEBUG.
- **Gates (5 Oct 2026):** Determinism verified via two -resetData launches giving byte-identical page source except for processId.

### D-004 Perturbation design (confirmed)
- **Date:** 2026-10-11
- **Balanced:** 3 apps x 4 categories x 2 scenarios = 24. Categories: 1 identifier rename/removal, 2 hierarchy insertion/restructure, 3 duplicate/generic labels, 4 visually clear but weak metadata.
- **Mechanism:** testbed uses launch arguments (\`-perturb <flag>\`); external apps use one git patch per perturbed scenario.
- **Bias control:** each scenario file carries an \`expected_outcome\` written before any formal run.

### D-005 Router threshold and margin 
- **Calibration set:** 6 pilot scenarios (benchmark/pilot/p-01..06), testbed only.
- **Rule (written 15 Sep 2026):** grid tau 0.60 to 0.95 and delta 0.05 to 0.30; maximize precision (target 1.0), then coverage.
- **Disclosure (15 Sep 2026):** baseline development runs of the FORMAL testbed scenarios reported accepted margins as low as 0.118. The rule is NOT changed in response to avoid tuning.
- **Pilot round 1 (15 Sep 2026):** rule output tau = 0.66, delta = 0.09. Precision 1.0, coverage 0.933.
- **Frozen values (pilot round ):** tau = 0.66, delta = 0.09, freeze tag \`experiment-freeze-1\`. Evidence: f22bc95f.

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

### D-011 Scripted baseline locator policy (proposed 12 Sep; amended 28 Oct 2026)
- **Initial Rule (12 Sep 2026):** (1) developer identifier; (2) XPath on unique name; (3) positional XPath.
- **Amended (D-023, 28 Oct 2026):** a unique non-empty label is tried before a positional XPath.
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

### D-018 Blind until benchmark is complete (adopted)
- **Date:** 2026-09-30
- **Rule:** Results are NOT broken down by configuration until all external scenarios are written and committed.

### D-019 External-app scenarios and instrumentation (proposed)
- **Date:** 2026-10-11
- **Implementation:** 16 scenarios written from captured baseline page source.
- **Instrumentation:** identifiers added to key buttons to allow category 1 (rename/remove) to function. Evidence: a94b46bd.

### D-020 Generic labels and XCUITest (finding)
- **Date:** 2026-10-15
- **Finding:** Initial captures showed that while labels were generic, iOS kept visible titles in the snapshot as \`accessible=false\` StaticText.
- **Decision:** Keep perturbations but revise predictions (a11y now predicted to succeed).

### D-021 Scenario corrections after external capture
- **Date:** 2026-10-15
- **Logic:** Oracles made unique; su-07 target changed from Indigo to Seafoam (Indigo was scrolled off-screen).

### D-022 Settle wait for theme menu
- **Date:** 2026-10-18
- **Finding:** SwiftUI theme menu loads items while scrolling.
- **Fix:** Add "Wait 2 seconds" step.
- **Status:** Verification failed; positional indices remained unstable.

### D-023 Label rung added to locator policy
- **Date:** 2026-10-22
- **Finding:** Page source read during animation can settle on a tree with missing items.
- **Decision:** D-011 gains a rung: (1) id $\rightarrow$ (2) unique name $\rightarrow$ (3) unique non-empty label $\rightarrow$ (4) positional.

# Design decision and component attribution register
Promised in the proposal's risk register. Each decision gives the options, the evidence, and the rationale. These feed Chapters 3, 6 and 7 and the BCS requirement for "rationale for design/implementation decisions".

## Decisions

### D-001 Native execution through Appium XCUITest, not Playwright (accepted, proposal)
- **Date:** 2026-06-26
- **Options:** Playwright MCP with iPhone emulation; Appium XCUITest; XCUITest directly in Swift.
- **Rationale:** Playwright emulates browser viewport, user agent and touch, not native UIKit/SwiftUI. Appium exposes XCTest-derived attributes to Python and has an MCP ecosystem.
- **Source:** proposal, Critical Context.

### D-006 Step language: controlled English with quoted targets (confirmed)
- **Date:** 2026-09-05
- **Proposed:** controlled English with quoted targets parsed by rules.
- **Rationale:** Parsing stays deterministic, so results measure element resolution rather than language understanding.

### D-010 Step oracle (confirmed)
- **Date:** 2026-09-05
- **Logic:** Correctness is judged by an author-written matcher (\`oracle\`) on the pre-action snapshot, independent of the resolver.

### D-012 Activation point for switches (proposed)
- **Date:** 2026-09-05
- **Logic:** All routes use \`Element.tap_point\` (trailing edge minus 32 pt for switches wider than 120 pt).

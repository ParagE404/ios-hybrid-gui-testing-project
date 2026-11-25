# Design decision and component attribution register
Promised in the proposal's risk register. Each decision gives the options, the evidence, and the rationale. These feed Chapters 3, 6 and 7 and the BCS requirement for "rationale for design/implementation decisions".

## Decisions

### D-001 Native execution through Appium XCUITest, not Playwright (accepted, proposal)
- **Options:** Playwright MCP with iPhone emulation; Appium XCUITest; XCUITest directly in Swift.
- **Rationale:** Playwright emulates browser viewport, user agent and touch, not native UIKit/SwiftUI. Appium exposes XCTest-derived attributes to Python and has an MCP ecosystem.
- **Source:** proposal, Critical Context.

### D-002 VLM hosting: local ShowUI-2B on M4 Pro vs approved API (decided: local)
- **Evidence (spikes/showui_batch.py):** synthetic 1206x2622 Settings screen, 13 labelled rows, MPS, float16. model load 6.1 s; 12/13 hits; latency median 3,215 ms.
- **Live evidence (pilot round 1):** 6 calls, 3.2 to 3.9 s each; 1 accepted and correct (p-05 picker).
- **Decision rule:** Local if median latency under about 10 s and outputs parseable. Both met, so the VLM runs locally.
- **Runtime implication:** about 3.2 s per fallback call, so the 432-run experiment fits overnight.

### D-003 External apps (confirmed)
- **Selection:** Testbed "Errands" (SwiftUI, own), SyncUps by Point-Free (SwiftUI, MIT), NetNewsWire by Ranchero Software (mostly UIKit, MIT).
- **Rationale:** one controlled app for internal validity, two independent real apps for external validity, both SwiftUI and UIKit.
- **Pinned commits:**
  - SyncUps: @ ... Bundle id co.pointfree.SyncUps.
  - NetNewsWire: @ ... Bundle id uk.ac.city.parag.NetNewsWire.iOS-DEBUG.
- **Determinism check:** Determinism verified via two -resetData launches giving byte-identical page source except for processId.

### D-004 Perturbation design (confirmed)
- **Balanced:** 3 apps x 4 categories x 2 scenarios = 24. Categories: 1 identifier rename/removal, 2 hierarchy insertion/restructure, 3 duplicate/generic labels, 4 visually clear but weak metadata.
- **Mechanism:** testbed uses launch arguments (\`-perturb <flag>\`); external apps use one git patch per perturbed scenario.
- **Bias control:** each scenario file carries an \`expected_outcome\` written before any formal run.

### D-005 Router threshold and margin 
- **Calibration set:** 6 pilot scenarios (benchmark/pilot/p-01..06), testbed only.
- **Calibration rule:** grid tau 0.60 to 0.95 and delta 0.05 to 0.30; maximize precision (target 1.0), then coverage.
- **Disclosure:** baseline development runs of the FORMAL testbed scenarios reported accepted margins as low as 0.118. The rule is NOT changed in response to avoid tuning.
- **Pilot round 1:** rule output tau = 0.66, delta = 0.09. Precision 1.0, coverage 0.933.
- **Frozen values:** tau = 0.66, delta = 0.09.
- **Timeline evidence:** The logs date pilot round 2 to 18 September and the formal testbed batch to 30 September. AI-use log Entry 9 records a freeze milestone on 19 September. Its scope is unverified. Commit `066debf` records the calibration on 2 October. The available `experiment-freeze-1` tag is dated 7 November and points to a commit outside `main`.

### D-006 Step language: controlled English with quoted targets (confirmed)
- **Proposed:** controlled English with quoted targets parsed by rules.
- **Rationale:** Parsing stays deterministic, so results measure element resolution rather than language understanding.

### D-007 Router uncertainty behavior (confirmed)
- **Proposed:** "best_effort" for both \`a11y_on_uncertain\` and \`hybrid_on_reject\`.
- **Rationale:** This gives the accessibility-only baseline its strongest fair form, so any hybrid gain is not inflated.

### D-008 VLM Constraints (confirmed)
- **Mechanism:** validator snaps the predicted point to the smallest compatible element and rejects it if that element is outside the resolver's candidate set.

### D-009 Execution primitive shared by all routes (confirmed)
- **Logic:** All routes tap at screen coordinates through \`mobile: tap\`; scripted finds by locator and clicks. Same backend for all three configurations.

### D-010 Step oracle (confirmed)
- **Logic:** Correctness is judged by an author-written matcher (\`oracle\`) on the pre-action snapshot, independent of the resolver.

### D-011 Scripted baseline locator policy (initial proposal, later amended)
- **Initial rule:** (1) developer identifier; (2) XPath on unique name; (3) positional XPath.
- **Amendment (D-023):** a unique non-empty label is tried before a positional XPath.
- **Rationale:** mechanical application prevents author bias.

### D-012 Activation point for switches (proposed)
- **Logic:** All routes use \`Element.tap_point\` (trailing edge minus 32 pt for switches wider than 120 pt).

### D-013 Separating development from evaluation (adopted)
- **Logic:** Engine fixes using baseline testbed screens were development work. The 24 September refinements recorded in AI-use log Entry 5 preceded the 30 September formal testbed batch and followed the 19 September milestone recorded in Entry 9.
- **Static check result:** baseline steps resolve through structured route; perturbed scripted locators break exactly at designed steps.

### D-014 Formal run protocol (pre-registered)
- **Implementation:** \`engine/batch.py\`. Repetition blocks with shuffled scenario order. Fresh app launch with \`-resetData\` before every run.

### D-015 Validator snaps only to interactive elements (pilot finding)
- **Finding:** Pilot p-02 showed ShowUI pointing at an alert title.
- **Decision:** point must fall inside an enabled, visible interactive element.

### D-016 VLM retry query (pilot finding)
- **Finding:** Identical calls returned the same point.
- **Decision:** Attempt 1 uses short grounding description; retry uses full step wording.

### D-017 Category 4 icons must carry no symbol semantics (pilot finding)
- **Finding:** SF Symbol labels ("Edit") leaked into accessibility metadata.
- **Decision:** \`UnlabelledSymbol\` redraws the symbol into a plain bitmap.

### D-018 Blind until benchmark is complete (adopted)
- **Rule:** Results are NOT broken down by configuration until all external scenarios are written and committed.

### D-019 External-app scenarios and instrumentation (proposed)
- **Implementation:** 16 scenarios written from captured baseline page source.
- **Instrumentation:** identifiers added to key buttons to allow category 1 (rename/remove) to function. .

### D-020 Generic labels and XCUITest (finding)
- **Finding:** Initial captures showed that while labels were generic, iOS kept visible titles in the snapshot as \`accessible=false\` StaticText.
- **Decision:** Keep perturbations but revise predictions (a11y now predicted to succeed).

### D-021 Scenario corrections after external capture
- **Logic:** Oracles made unique; su-07 target changed from Indigo to Seafoam (Indigo was scrolled off-screen).

### D-022 Settle wait for theme menu
- **Finding:** SwiftUI theme menu loads items while scrolling.
- **Fix:** Add "Wait 2 seconds" step.
- **Status:** Verification failed; positional indices remained unstable.

### D-023 Label rung added to locator policy
- **Finding:** Page source read during animation can settle on a tree with missing items.
- **Decision:** D-011 gains a rung: (1) id $\rightarrow$ (2) unique name $\rightarrow$ (3) unique non-empty label $\rightarrow$ (4) positional.

### D-024 Blind lifted; formal analysis run
- **Action:** Commit `662ac36` on 28 October records the blind lift and primary analysis of all 432 formal runs. Commit `8256dfe` on 26 October adds the analysis pipeline and tests, and AI-use log Entry 15 records an analysis session that day. The date the configuration breakdown was first viewed is unverified.

### D-025 Reporting formal results
- **Observation:** Repetitions never disagreed.
- **Decision:** Report scenario-cluster bootstrap CI as primary; use exact McNemar on one observation per scenario.

### D-026 MCP adapter and the SEQ1 protocol
- **Design:** \`mcp_adapter/\` wraps the frozen engine as an MCP server over stdio.
- **SEQ1 protocol:** 72 runs, ABBAAB block order, comparing direct vs MCP.
- **Final Register Update:** .

### D-027 Sensitivity of the frozen thresholds and resolver weights (post-hoc extension)
- **Context:** I tested how sensitive the results were to the routing thresholds and resolver weights. These settings were chosen by hand or calibrated on six testbed pilot scenarios. I kept the engine configuration fixed and used `formal.jsonl` as read-only input.
- **My role and AI assistance:** I chose which settings to vary and required checks against the original log before using the replay. Claude Code helped with the script, replay, tests and reproducibility checks. I interpreted the results and decided to retain the frozen settings.
- **Method:** \`analysis/sensitivity.py\`. B1: accept/fallback recomputed from logged top and runner-up scores for every unique a11y targeted step (150), tau 0.50 to 0.95 and delta 0.00 to 0.30, step 0.01. B2: resolver replayed on the saved page source named by each step's \`screen:\`; the replay must reproduce the logged top candidate, score, route and oracle result before a step is used. Then a 0.05 simplex over (text, type, context) weights, attribute weights one at a time by +/-0.2, and three ablations.
- **Validation:** B1 recomputation at (0.66, 0.09) reproduces 150/150 logged routes. Replay agrees on 141/150 steps; the 9 excluded steps (nn-01/04/07 add-folder, su-07 theme menu, tb-01 Save, tb-04 perturbed) are listed in \`analysis/out/sensitivity.md\`. Repetitions of tb-04 step 0 disagree on the Settings button's identifier (None vs gearshape) but not on route or oracle.
- **Result (B1):** route at the frozen point unchanged for tau in [0.50, 0.70] at delta 0.09, and delta in [0.00, 0.11] at tau 0.66 (252 of 1,426 cells change no route). Nearest edges: tb-08 baseline step 1 (margin 0.118) and tb-06 perturbed step 0 (score 0.705). Precision on accepted steps is 0.992 or higher everywhere; the only wrong accepted step is nn-06 perturbed step 1 (score 0.853, no runner-up). In the a11y configuration the route does not change the action (D-007), so these edges matter only for when hybrid calls the VLM.
- **Result (B2):** all 171 interior simplex points (every weight at least 0.05) give exactly the frozen set of correct top candidates; changes appear only where the type or context weight is 0. No point gains a step. Attribute weights +/-0.2 change no correct top candidate. Ablations lose steps: text only 11, no type 8, no context 3 (all tb-05 duplicate Delete).
- **Decision:** I interpreted this as a plateau for the weights and for precision, while noting routing near an edge in delta (+0.03) and tau (+0.05). I kept the frozen values unchanged.

### D-028 Seeded-fault study: design, taxonomy and measures (post-hoc extension, pre-registered)
- **Context:** I tested whether tolerating cosmetic changes could also hide real regressions. I defined the 12 seeded-fault scenarios and predictions before running them.
- **My role and AI assistance:** I defined the experimental controls, oracle-free verdict and fault classification. Claude Code helped with scenario files, Swift fault hooks, analysis scripts, checks and batch execution. I compared the results with the pre-run predictions and classified the failures.
- **Faults:** testbed only. New \`apps/testbed/Errands/Fault.swift\`, enum \`Fault\`, read from \`-fault <flag>\`, separate from \`Perturb\` and inert unless passed. 8 behavioural faults, one per tb-01..08 (f-01 Save not persisted; f-02 Urgent flag dropped; f-03 Mark as done marks the next item; f-04 Show completed ignored; f-05 Delete removes the row below; f-06 By date leaves name order; f-07 favourite not stored; f-08 chip applies the previous category). 4 lure faults, intended control removed while a similar one remains (f-09 Save -> Save draft; f-10 Mark as done -> Mark all as done; f-11 Show completed -> Show completed first; f-12 no Delete in the Eggs row).
- **Scenarios:** \`benchmark/faults/f-01..12.yaml\`; steps, locators, oracles, postconditions and perturbation copied unchanged from the base tb file (checked by script). Conditions become fault only (baseline) and fault + cosmetic perturbation (perturbed). Each file states fault_step, what can observe the fault, and a prediction per configuration and condition.
- **Primary verdict (oracle-free):** a run passes if every step executed, no expect_after failed and all postconditions held. The step oracle is benchmark instrumentation a real test does not have, so it is NOT part of the verdict; it is used only to tell whether a substitute control was acted on. The runner's own \`completed\` (which includes the oracle) is reported as well.
- **Classification of each fault run:** (1) false pass: oracle-free verdict passes; (2) fragility (masked): the run fails at the same first failure point and kind as the matching fault-free formal tb run (same config and condition), so it would have failed without the fault; (3) detection: any other failure, reported as at the fault step, at a later step, or at a postcondition. A detection whose first failure precedes fault_step is reported separately as "other" (the fault should not change earlier behaviour).
- **Measures:** false-pass, detection and fragility counts per configuration x condition and per fault class, at run and scenario level, with the same scenario-cluster bootstrap as the main analysis; substitute actions = executed steps with oracle_ok false. Each false pass gets a one-line cause (weak postcondition, substitute control, or model choice).
- **Runs:** 12 x 2 conditions x 3 configurations x 3 repetitions = 216, \`python -m engine.cli batch benchmark/faults --log experiments/raw/faults.jsonl --seed 20261117\`. Before the batch: a 48-run inertness check (tb-01..08 x 2 x 3, one repetition) on the rebuilt app, logged to \`experiments/raw/fault_inertness.jsonl\`; outcomes must equal the formal results.
- **Prediction (all files):** no false passes. Lure faults f-09..f-11 are predicted to make a11y and hybrid act on the substitute on the structured route and to be caught only by postconditions. All twelve faults are observable by the copied postconditions or expect_after checks, so this study tests whether tolerance hides faults that the test's own checks can see; it does not measure postcondition adequacy.
- **Amendment before the fault batch:** the static check showed f-11's copied step-1 oracle (\`label_contains: Show completed\`) also matches the lure 'Show completed first', so substitute taps would not be counted. The f-11 oracle is tightened to exact labels (\`Show completed\`; perturbed \`Show completed, Includes finished errands\` via \`oracle_perturbed\`). Verified on saved screens: matches the real switch in both conditions, nothing on the lure screens. The verdict does not use the oracle, so no prediction changes. Inertness check: 48/48 runs match the formal runs (\`analysis/out/fault_inertness.md\`).
- **Result:** 216/216 runs logged, no infrastructure exclusions or engine errors; repetitions never disagreed; 72/72 cells match the prediction (\`analysis/out/faults.md\`). False passes: 0. Detections: scripted 33/72, a11y 66/72, hybrid 72/72; the rest are fragility (masked): scripted fails where the fault-free run already failed (33 of its 36 perturbed runs), a11y at the tb-07/tb-08 perturbed steps. Every a11y and hybrid lure run acted on a substitute (48/48): 'Save draft', 'Mark all as done' and 'Show completed first' on the structured route, then caught only by a postcondition; f-12 deleted another row and was caught at the fault step by expect_after. Scripted detected lures at the fault step only where it reached them (9/36). In f-08 hybrid, after the step-0 check had already failed, the VLM tapped two elements for a row that was not on screen (runs continue after an expect_after failure); the detection is unaffected.

### D-029 Engine v2 on held-out scenarios: scenario design (pre-registered, before any v2 code)
- **Context:** I investigated whether the two changes proposed after SU-03, SU-05 and SU-07 would help on new scenarios. I specified those scenarios before implementing v2 and used the formal set only for the regression check.
- **My role and AI assistance:** I set the held-out evaluation design, success criteria and limits, and kept the original predictions unchanged when static checks exposed a weakness in the planned scroll trigger. I used Claude Code to assist with testbed flags, v2 implementation, golden and inertness checks, experiment execution and analysis. I interpreted both improvements and remaining failure cases rather than treating successful execution as evidence that the fixes worked.
- **Fixes (to be implemented behind options that default to off):** \`scroll_to_find\` (on no_match, swipe and re-snapshot, at most three times) and \`relax_candidate_set\` (the validator skips the candidate-set check when every candidate scores 0 or is incompatible).
- **Held-out scenarios:** \`benchmark/heldout/h-01..08.yaml\`, none built on SU-03/05/07 screens or controls. h-01..h-03: targets below the fold of NetNewsWire Settings in the unmodified app (absent from the page source until scrolled; checked live before the held-out runs). h-04..h-06: the only text match is a control hidden behind a sheet while the real control is visible and unlabelled; this does not occur naturally in the benchmark apps outside the excluded SU cases, so three new metadata-only testbed flags are proposed (h04_add_confirm_icon, h05_name_field_unlabelled, h06_edit_confirm_icon), passed in initial_state. h-07, h-08: controls where neither fix should matter. Each scenario's perturbation block reuses an existing cosmetic flag, so both conditions apply.
- **Configurations and runs:** a11y-v1, hybrid-v1 (the frozen engine), a11y-v2, hybrid-v2; 8 x 2 conditions x 4 configurations x 3 repetitions = 192 runs into \`experiments/raw/heldout.jsonl\`. Outcome: runner completion, as in the formal experiment. The scripted configuration is not run.
- **Predictions:** v1 fails h-01..h-06; a11y-v2 completes h-01..h-03 and still fails h-04..h-06 (it has no VLM); hybrid-v2 completes h-01..h-03 and completes h-04..h-06 only if ShowUI grounds the unlabelled control (uncertain); all four complete h-07 and h-08.
- **Known limits before running:** the three below-fold scenarios share one screen (NetNewsWire Settings). The three hidden-candidate scenarios rely on new testbed flags covered in the component attribution table. Results will be labelled exploratory.
- **Pre-run finding (after the static check, before any held-out run; predictions NOT edited):** testbed rebuilt with the three flags; 48/48 inertness runs match the formal runs (\`analysis/out/heldout_inertness.md\`). Static check of h-01..h-08 on captured screens: all locators and oracles match one element; h-04..h-06 route incompatible_state with the hidden 'Add item' / 'Mark as done' as the only candidate, as designed. But on the unscrolled Settings screen the h-01..h-03 targets do not give no_match: partial text matches route low_score ('Add NetNewsWire News Feed' for h-01 and h-03, 'Add Account' for h-02). As specified, scroll_to_find triggers only on no_match, so it is now expected NOT to fire on h-01..h-03, and v2 is expected to fail them like v1, against the committed prediction. I did not widen the trigger after seeing the held-out screens, because that would tune v2 on the evaluation set. I kept the pre-registered batch and reported its outcome against the original prediction.
- **Held-out result (exploratory):** 192/192 runs, no engine errors or exclusions; repetitions never disagreed; 50/64 cells match the committed prediction (\`analysis/out/v2.md\`). Controls h-07, h-08: all four configurations complete (no regression). Below the fold h-01..h-03: 0/18 for every configuration; scroll_to_find never fired, because the targets route low_score on partial matches ('Add NetNewsWire News Feed', 'Add Account') and every configuration acts on the wrong control; the 12 v2 cells miss their prediction, as the pre-run note expected. Hidden candidate h-04..h-06: v1 and a11y-v2 0/18; hybrid-v2 12/18 (h-05 and h-06 complete in both conditions). relax_candidate_set fired in all 18 hybrid-v2 runs; in h-04 ShowUI grounded 'Add' to the quantity stepper's Increment (+) button, which v1 would have rejected as outside the candidate set and v2 accepted, so the relaxation also removed a safeguard; the run still failed at its postcondition. Overall hybrid-v2 completes 24/48 held-out runs against 12/48 for hybrid-v1.
- **Regression result on the formal set (secondary):** 24 formal scenarios x 2 conditions x a11y-v2 and hybrid-v2 x 3 repetitions = 288 runs (seed 20261120) into `experiments/raw/v2_regression.jsonl`, compared with the a11y and hybrid runs of `experiments/raw/formal.jsonl` (`analysis/out/v2_regression.md`, `v2_regression.csv`). No engine errors. No scenario-condition cell changed completion in either direction: a11y-v2 completes 72/72 baseline and 42/72 perturbed, hybrid-v2 72/72 and 54/72, the same as v1. scroll_to_find fired in 30 perturbed runs (nn-07, nn-08, su-08, tb-07, tb-08), where the target's metadata had been removed, so scrolling could not find it; it added a median 6.7 s per run (max 12.9 s) and changed no outcome. relax_candidate_set fired in the 9 hybrid-v2 perturbed runs of SU-03, SU-05 and SU-07, the scenarios that motivated it, and all 9 still failed (SU-03 and SU-05 at step 3, SU-07 at its postcondition). So on the formal set v2 causes no regression but also does not fix the cases it was designed from, and scrolling only adds latency.

## Component attribution

| Module group | Scope | Origin | Commit evidence or source |
|---|---|---|---|
| Engine inputs and parsing | Data model, page-source normalisation, intent parser, and scenario loader | Written by the author with AI help | [3a3e0a5](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/3a3e0a5e0845a7dc4fa9ec826796fc5efcdc5d8a), [dc26629](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/dc266293fde6a5c8f21c3ace705e691151a64afd) |
| Accessibility resolver | Element resolution and matchers | Written by the author with AI help | [4c74883](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/4c74883004786d91e87185160d2599bd6ef65fc6) |
| Routing, validation, and telemetry | Confidence router, action validator, telemetry, and threshold calibration | Written by the author with AI help | [efeaacc](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/efeaacc040d0afce13b3e7156f61d89ffd2b4d91), [8ff7452](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/8ff7452c1712889430b523d827f1dc716d5e7fd0) |
| App execution and batch runner | Appium backend, scenario runner, CLI, batch scheduling, and static checks | AI-scaffolded and rewritten by the author | [758f4ac](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/758f4ac236aaefd8e3258e991a9d96d888472586), [142ed36](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/142ed3679266760af8406ae00cc234245d3215ce), [44d7fab](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/44d7fabb840b46f248a1238b161926399882566c), [8e5e175](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/8e5e175ec1b94e5e4db4731084f84e59af96ce49) |
| Vision-model fallback | Project-side ShowUI-2B adapter and grounding batch script | Written by the author with AI help | [caa965e](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/caa965e8e2c4d53d712d8eb963d9ed1f1e070545) |
| Errands testbed design | Specified the baseline workflows and eight cosmetic perturbations. | Author-defined | D-004, [a12e373](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/a12e37367c2cc9f875d2ad8be695b224292fe6a0) |
| Errands SwiftUI implementation | App screens, state store, build setup and perturbation switches. | AI-generated and reviewed by the author | [ad05939](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/ad05939d644ccaab59fa3ea0dfdc841440f6945b) |
| External app instrumentation | Project patches and Swift instrumentation helpers for SyncUps and NetNewsWire | AI-scaffolded and rewritten by the author | [02b4ab1](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/02b4ab1e67c404dbbbe3a3f2c8cd47f300855b70), [34d6dce](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/34d6dce658daa634947e16170e9c9bc5bb157d57) |
| Pilot and formal scenario design | Defined the test steps, step oracles and postconditions, and set the formal outcome predictions. | Author-defined | D-004, D-010, [a12e373](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/a12e37367c2cc9f875d2ad8be695b224292fe6a0), [8e5e175](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/8e5e175ec1b94e5e4db4731084f84e59af96ce49) |
| Pilot and formal scenario YAML | YAML implementation of the pilot and formal scenarios for the three apps. | AI-generated and reviewed by the author | [8243d5a](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/8243d5a238a597518e600e7284692fb55313e5a2), [a12e373](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/a12e37367c2cc9f875d2ad8be695b224292fe6a0), [e4a2709](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/e4a2709a92503a1dee145da0ec11033ab8b19a40), [4638c69](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/4638c69b778bf7facec12bb39b2aeaefbfeb8955) |
| MCP adapter and SEQ1 | Session facade, MCP server, direct-versus-MCP runner, and SEQ1 analysis | Written by the author with AI help | [b4a20c4](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/b4a20c435d5cde2cb3955d1b4c9902b60231c686), [65e64a6](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/65e64a6911aec559aed3c181903b5f2b031bc859), [420999d](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/420999da9bd5b98c59a4d09d807d68331f5470d5), [88c99ae](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/88c99ae9bedbcfa0c5f818ce7b65e0db76ca9b95) |
| Formal analysis and reporting | Main statistical analysis, scenario-level tables, and worked-example figures | Written by the author with AI help | [8256dfe](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/8256dfe0053e5b2eb82a0ee09f346f3546af158d), [74f2b2d](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/74f2b2d4f01a931255af292cc243d99c8f25fdc3), [6be278b](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/6be278b725ed275523c725892aaf52b526508bf0) |
| Sensitivity extension | Threshold and resolver-weight replay | Written by the author with AI help | [eb2b139](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/eb2b1390c89fd86c07e12cec8a697392885f52c5) |
| Seeded-fault study design | Specified the 12 faults and pre-run predictions, the oracle-free pass criteria and the failure classification. | Author-defined with AI assistance | D-028, [08e4531](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/08e45317d1904908725d4871893ffe725cbe4fc9), [bf1b73e](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/bf1b73ee7f0669a9a3c6f5ced45d0eae13cf519f) |
| Seeded-fault implementation | Scenario YAML, Swift fault hooks, and fault and inertness analysis scripts. | AI-generated and reviewed by the author | [08e4531](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/08e45317d1904908725d4871893ffe725cbe4fc9), [af3775c](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/af3775cb41a9add47d2dd91287a7ae3fa506c788), [90b6a56](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/90b6a561055630e556d38a385b94db95cd908a5e) |
| Held-out evaluation and engine v2 | Held-out scenarios, testbed flags, engine v2 options, and v2 analysis | AI-scaffolded and rewritten by the author | [6066686](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/6066686675c4e7c2fb88335b49f2dee1137d8a06), [a4d0f83](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/a4d0f8324f884fbd868a2a485dc50012349be3c1), [21c4bdd](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/21c4bdd8e81ff721a9d4153ddd67273c72c6e26f), [c64c328](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/c64c328347c09da28761400e21011fd88ea5cd38) |
| Tests and golden fixtures | Core unit tests, batch and adapter tests, and frozen-engine regression fixtures | AI-scaffolded and rewritten by the author | [efeaacc](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/efeaacc040d0afce13b3e7156f61d89ffd2b4d91), [44d7fab](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/44d7fabb840b46f248a1238b161926399882566c), [65e64a6](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/65e64a6911aec559aed3c181903b5f2b031bc859), [21c4bdd](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/21c4bdd8e81ff721a9d4153ddd67273c72c6e26f) |
| Feasibility, capture, and demo tools | Appium smoke scripts, synthetic screens, page-source capture, and demo viewer | AI-generated and reviewed by the author | [e07e9e8](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/e07e9e8f53589420dce9e279114f118604cb4087), [84de645](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/84de645c94b15a00221c3cfdf0a8c70914cc57c3), [77f9f81](https://github.com/ParagE404/ios-hybrid-gui-testing-project/commit/77f9f819046753696de89b63ee50d0dfb8de9a6b) |
| Appium tooling | Appium 3.8.0 and Appium XCUITest driver 12.18.2 (Apache-2.0) | Third-party | [Appium](https://github.com/appium/appium), [XCUITest driver](https://github.com/appium/appium-xcuitest-driver) |
| MCP Python SDK | Python SDK 2.3.0 (MIT) | Third-party | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) |
| ShowUI-2B | Model weights at the recorded revision (MIT per the model card) | Third-party | [Pinned model](https://huggingface.co/showlab/ShowUI-2B/tree/cabec4fcc48d15ffd3efe0b33ea9bc7d41509d60) |
| SyncUps and NetNewsWire | Unmodified upstream apps used as patch bases (MIT) | Third-party | [SyncUps revision](https://github.com/pointfreeco/syncups/commit/170bc1ad7b0ec1e64606d7c45c54456a0f26b04c), [NetNewsWire revision](https://github.com/Ranchero-Software/NetNewsWire/commit/bb5ab3dc91f9da00fa8eaedf89a04c5e7970ad5c) |

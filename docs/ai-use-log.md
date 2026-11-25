# Generative AI use log

| # | Date | Tool | Task | Key prompt (summarised) | Output used? | How I verified it | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | 2026-07-05 | Claude Code | Set up development environment: Python 3.12, Appium, and VLM model weight downloads | Read setup-week1.md. Implement steps 2-4... record versions in docs/versions.md | Accepted with modification: I manually handled Node version to avoid PATH conflicts | Verified via version commands and `pytest` | docs/versions.md |
| 2 | 2026-07-15 | Claude | Developed synthetic screen generator and ShowUI grounding/latency scripts | Help me write a script to generate a synthetic labelled iOS screen and a batch script to score latency | Accepted: I ran and tested the scripts on the Mac | Verified via result metrics in D-002 | spikes/out/showui_batch.json |
| 3 | 2026-09-07 | Claude | Designed the engine core; used AI to assist with boilerplate scaffolding for the parser, router, and matchers | Help me scaffold the engine core components (normaliser, intent parser, etc.) | Modified: I reviewed and refined the design choices (D-006 to D-010) | Verified by running tests on synthetic page sources | tests/ |
| 4 | 2026-09-16 | Claude | Implemented Errands SwiftUI testbed; used AI to assist with perturbation flags and scenario YAMLs | Assist in writing the SwiftUI testbed and 8 perturbation scenarios with expected outcomes | Modified: I manually verified locators on the real simulator | Verified that 46 tests pass and scenarios load correctly | apps/testbed/, benchmark/scenarios/ |
| 5 | 2026-09-24 | Claude | Refined engine based on real page source; implemented nested-content collapse and in_row matchers | Analyze this page source; help me fix the nested-content collapse and tighten the oracles | Accepted: I integrated these fixes into the core engine (D-013) | Verified via static checks on baseline screen sets | docs/decision-register.md D-013 |
| 6 | 2026-09-20 | Claude Code | Automated the capture of baseline and perturbed page sources via Appium | Run the smoke script and capture page source/screenshots for all 8 perturbation flags | Accepted: I reviewed the captured screenshots | Verified that each flag correctly altered the ID/label | benchmark/pagesource/ |
| 7 | 2026-09-26 | Claude Code | Ran live development baselines; used AI to help diagnose and fix a keyboard focus bug in the backend | Run tb-01 baseline. If it fails, help me diagnose the issue in engine/backend.py | Modified: I verified the fix in a standalone session | I logged a `pytest` check. The saved development log starts on 18 October | tests/ |
| 8 | 2026-09-28 | Claude | Developed the pilot set and batch runner with retry/resume logic | Help me implement a batch runner with randomized order and resume capabilities (D-014) | Accepted: I reviewed the logic for infrastructure failures | Verified via dry-run of 144 formal runs | engine/batch.py, benchmark/pilot/ |
| 9 | 2026-09-18, 2026-09-19, 2026-09-30 | Claude Code | Ran pilot round 2 (18 Sep), logged a freeze milestone (19 Sep), and ran the formal testbed batch (30 Sep) | Run pilot round 2, apply RouterConfig freeze, and execute the 144-run formal batch | Accepted: I used the calibrated thresholds for the formal batch | Pilot and formal logs verify the run dates. All 144 testbed runs completed without engine errors. The scope of the 19 September milestone is unverified | experiments/raw/pilot2.manifest.json, experiments/raw/formal.jsonl |
| 10 | 2026-10-26 | Claude | Developed the analysis pipeline for bootstrap CIs and McNemar tests | Help me write an analysis script for completion rates, latency, and failure categories | Modified: I tested the pipeline on pilot data first to avoid bias | Verified via smoke tests on fake-backend logs | analysis/analyse.py |
| 11 | 2026-10-10 | Claude Code | Integrated external apps (SyncUps, NetNewsWire); used AI to assist with instrumentation patches | Help me clone and patch SyncUps/NetNewsWire for -resetData and Perturb reader | Modified: I manually fixed build compatibility issues in Swift | Verified that both apps reset to a byte-identical state |  |
| 12 | 2026-10-14 | Claude Code | Implemented external perturbations (16 flags); used AI to help map UIKit/SwiftUI labels | Implement 16 flags per external-perturbations.md and capture baseline screens | Modified: I manually adjusted UIMenu behavior for UIKit | Verified via page source grep checks | apps/external/*.patch |
| 13 | 2026-10-20 | Claude Code | Debugged menu animation timing; used AI to help analyze page source snapshots | Verify the wait fix for su-07; run 8 dev runs to check stability | Rejected: I found that mid-animation snapshots caused failures | Verified by comparing page source lengths | experiments/raw/dev_external.jsonl |
| 14 | 2026-10-24 | Claude Code | Implemented label-based locators (D-023) and executed formal batch 2 | Verify label locators for su-02/07, then execute the remaining 288 external runs | Accepted: I verified the label matches exactly 1 element | Under the D-023 stop condition, the external batch could start only after all 12 development runs passed every step oracle. All 12 passed. |  |
| 15 | 2026-10-26 | Claude | Used AI to help with analysis and draft the scenario-level sensitivity analysis | Run analysis on all 432 runs; help me write the prediction-vs-outcome table | Modified: I manually verified VLM points against screenshots | The primary analysis and blind lift were recorded on 28 Oct (D-024). The date I first viewed the formal breakdown is unverified | analysis/scenario_level.py, analysis/out/results.md |
| 16 | 2026-11-15 | Claude Code | Reproduced final analysis results on the Mac and committed the data | Install analysis extras and regenerate all CSVs and figures to ensure reproducibility | Accepted: I verified the file hashes matched | Verified via `diff -r` between temp and final output | analysis/out/ |
| 17 | 2026-11-03 | Claude | Designed MCP adapter and SEQ1 runner; used AI to help scaffold the MCP server tools | Help me design an MCP adapter facade and a SEQ1 runner for ABBAAB blocks | Modified: I updated the SDK API calls to match MCP 2.3.0 | Verified via stdio self-test mode | mcp_adapter/, tests/test_mcp_adapter.py |
| 18 | 2026-11-07 | Claude Code | Executed 72-run SEQ1 batch and performed comparative analysis | Run the full SEQ1 batch; analyze differences between direct and MCP routes | Accepted: I verified that 117/117 steps were identical | Verified via seq1.md summary | experiments/raw/seq1*.jsonl |
| 19 | 2026-11-17 | Claude Code | I checked how the results changed with different routing thresholds and resolver weights. Claude Code helped with the replay and repeatability checks. | Vary the thresholds and weights, and compare the replay with the formal logs. | I used the results to retain the frozen settings in D-027. | All 80 tests passed, including 12 new tests. Recomputed routes matched 150 of 150 logged routes. Resolver replay matched 141 of 150 steps. Two runs produced identical files. | analysis/sensitivity.py, analysis/out/sensitivity.md, D-027 |
| 20 | 2026-11-17 | Claude Code | I planned the seeded-fault study. Claude Code helped draft scenarios and predictions, implement Swift fault hooks, rebuild the app and prepare the analysis. | Prepare the fault scenarios, implementation and checks. Stop before the 216-run batch. | I used the checks to prepare the study. Entry 21 records the formal fault runs. | Predictions were committed before the fault code (08e4531). Of 63 screens, 60 matched the formal build exactly and the other three differed only in tab identifiers or menu positions by 1–2 points. All 48 inertness runs matched the formal runs. All 86 tests passed. | benchmark/faults/, apps/testbed/Errands/Fault.swift, analysis/faults.py, analysis/out/fault_inertness.md |
| 21 | 2026-11-17 | Claude Code | I approved the f-11 oracle change and ran the 216-run seeded-fault batch with Claude Code. | Tighten the f-11 oracle and run the seeded-fault batch. | I compared the results with the predictions and recorded the fault classifications in D-028. | The f-11 oracle was checked against saved screens before the batch. The analysis passed synthetic-log tests. Two regenerations matched byte for byte, and all 72 result cells were checked against their predictions. | experiments/raw/faults.jsonl, analysis/out/faults.md, fig_faults.png |
| 22 | 2026-11-17 | Claude Code | I assessed two engine v2 changes on held-out scenarios. Claude Code helped implement the changes, check the testbed and analyse the 192-run batch. | Implement the two changes behind flags that are off by default. Check frozen behaviour and analyse the held-out runs. | I used the results to identify where the changes helped and where they failed (D-029). | All 48 inertness runs and 48 frozen-engine telemetry cases matched. I recorded the static-check finding before the batch. The analysis passed synthetic-log tests and two runs produced identical outputs. | engine/runner.py, engine/validator.py, tests/test_v2.py, tests/golden/, analysis/v2.py, analysis/out/v2.md |
| 23 | 2026-11-17 | Claude Code | I assessed engine v2 on the formal benchmark and checked the supporting literature with Claude Code. | Run the v2 regression and check the cited findings against the original sources. | I recorded the regression result in D-029 and marked which literature sources had been checked. | The 288-run regression had its own output files. The held-out tables regenerated byte for byte and all 100 tests passed. I traced reading-list figures to checked sources and marked unchecked sources as unconfirmed. | experiments/raw/v2_regression.jsonl, analysis/out/v2_regression.md, docs/literature-extension.md, D-029 |

## Verbatim prompt excerpts

These excerpts are copied from saved Claude Code messages on 17 November 2026. The log entries above summarise the tasks and prompts.

**Predictions before runs**

> Write and commit every new scenario's expected_outcome before its first run. Never edit a prediction afterwards.

**Fault batch stop condition**

> after the predictions are committed and the 48-run inertness check passes, before the 216-run batch

**Oracle correction**

> Tighten f-11, then run

**Reporting the results**

> Report results whichever way they fall. If the fault study shows false passes, or v2 does not help on held-out scenarios, that is a finding to write up, not something to tune away.

**Regression approval**

> Yes, run regression

**Literature verification**

> Give me the verified list and cite only what I confirm I have read.

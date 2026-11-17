# Claude Code guide

Accessibility-first hybrid iOS GUI testing is Parag Dharadhar's MSc Software Engineering project (INM468, City St George's, University of London). Work within this checkout and use `main` as the reference for submission evidence. Use [README.md](README.md) for setup and reproduction, the [decision register](docs/decision-register.md) for rationale and attribution, and the [version record](docs/versions.md) for the evaluated toolchain.

## Project map

| Path | What lives there |
| --- | --- |
| `engine/` | CLI, Appium XCUITest backend, page-source normalisation, controlled-English intent parsing, resolver, router, action validation, scenario runner and JSONL telemetry |
| `mcp_adapter/` | Bounded stdio MCP tools that wrap the engine and support the SEQ1 direct-versus-MCP comparison |
| `apps/testbed/`, `apps/external/` | SwiftUI Errands testbed, plus pinned SyncUps and NetNewsWire patches and instrumentation |
| `benchmark/` | Formal scenarios, separate pilot and extension scenarios, and captured XML and screenshots |
| `experiments/raw/`, `analysis/` | Recorded run logs and manifests, analysis scripts, and reference outputs under `analysis/out/` |
| `tests/`, `spikes/` | Offline tests and golden fixtures, plus exploratory scripts |

## Runtime behaviour to preserve

- `scripted` uses fixed Appium locators. `a11y` ranks controls from XCUITest page source and uses a positive-score structured candidate as best effort on uncertain matches.
- `hybrid` uses the same structured path and calls local ShowUI-2B on uncertain matches. Validate proposed model actions and keep the two-attempt budget. If the model produces no valid action within that budget, the runner may use a positive-score structured candidate.
- The formal router values are threshold **0.66** and margin **0.09** (D-005). Keep scroll-to-find and the relaxed visual candidate-set rule opt-in through the v2 configurations. Preserve v1 route and reason codes, action bounds and telemetry behaviour. Use the golden comparison in `tests/test_v2.py` to check v1 compatibility.
- Keep oracles and postconditions independent of locator selection. An executed tap alone does not establish completion. Keep MCP app selection allowlisted, actions bounded and `resolve` read-only.

## Working with Claude

1. **Inspect.** Read the affected entry point, its callers and the relevant tests or decision records. Check `git status --short` before editing and preserve work already in the tree. For a log or capture, start with the schema or a small slice.
2. **Define the check.** Identify an observable pass condition before editing. For a bug, reproduce it with the smallest available test, saved screen or log. For a multi-file change with design trade-offs, outline the approach, the affected behaviour and how you will verify it. Parag owns research and design decisions.
3. **Implement.** Reuse the existing entry points and keep the diff focused. Diagnose failures before changing expectations. In particular, preserve independent scenario oracles, historical fixtures and the distinction between recorded measurements and derived outputs.
4. **Verify.** Start with the affected tests or offline command. Run the full suite when changing shared engine, telemetry or analysis behaviour. Use simulator evidence for claims about live iOS behaviour. Read the final diff and report the checks you ran, their results and any gaps.
5. **Hand off.** For work spanning sessions, retain a short summary of the goal, key decisions, files changed, verification and open issues. Keep this file focused on durable instructions and link to project documents for detailed procedures. Leave edits for review unless Parag asks for a commit or push.

## Commands and verification

Run from the repository root. The report environment uses Python 3.12. Reuse the existing `.venv` if present.

```sh
# First-time offline setup
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,analysis,mcp]'

# Full suite and focused examples
python -m pytest -q
python -m pytest -q tests/test_unit.py tests/test_runner.py tests/test_v2.py
python -m pytest -q tests/test_mcp_adapter.py

# Inspect a scenario, a resolution and a planned batch run offline
python -m engine.cli check benchmark/scenarios/tb-07.yaml
python -m engine.cli resolve benchmark/pagesource/baseline/list.xml "Tap the 'Batteries' item"
python -m engine.cli batch benchmark/scenarios --dry-run --limit 1
```

- For analysis changes, rerun the relevant command in the [report reproduction guide](README.md#regenerate-report-results) with output directed to a temporary directory. Check the relevant tables, counts or figures against `analysis/out/`.
- For live checks, follow [Live runs](README.md#live-runs) and [pinned versions](docs/versions.md). Appium and a booted iOS Simulator are required. `apps/testbed/build.sh` builds and installs Errands. Use a scratch `--log` path for new checks. The live `batch` command defaults to `experiments/raw/formal.jsonl`.

## Experiment evidence

- The primary benchmark has 24 scenarios across Errands, SyncUps and NetNewsWire, two conditions and three repetitions per configuration (432 runs). Pilot runs are for calibration and are excluded from the formal results. Keep the formal logs, manifests, scenarios, frozen defaults and reference fixtures as evidence.
- When reproducing or extending the protocol, keep predictions and outcome criteria fixed before the evaluated runs. Keep configuration results blinded until the external scenarios are committed (D-018). Under D-023, all 12 development runs had to pass every step oracle before the formal external-app batch could start.
- Keep SEQ1 and extensions D-027 to D-029 identifiable as separate analyses. Use the recorded protocol and scenario-level unit when reproducing the formal inference (D-025). Use pilot or development data for tuning and reserve held-out scenarios for evaluation.
- Verify dates, run counts and versions against the raw logs, manifests and decision register. State any uncertainty about the freeze timeline and cite the evidence. Treat `20261018` as the batch seed.

## Authorship and reporting

- Parag owns benchmark design, predictions and interpretation. When updating the project records, describe what he decided, what AI contributed, what he accepted or changed and how he verified it. Quote prompts only when the original wording is available. Label paraphrases as summaries. See the [AI-use log](docs/ai-use-log.md).
- Keep source origin headers accurate and aligned with the [component attribution table](docs/decision-register.md#component-attribution). Preserve the upstream MIT notices in both external app patches and the attribution for reused ShowUI code.
- Follow the approved no-participants ethics scope. Use UK English and Harvard referencing in the report, and avoid em dashes. Keep the Word report and Turnitin source appendix outside Git.

Workflow references: [Claude Code best practices](https://code.claude.com/docs/en/best-practices), [Claude Code project instructions](https://code.claude.com/docs/en/memory), and [Anthropic's context engineering guidance](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents).

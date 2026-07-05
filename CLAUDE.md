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

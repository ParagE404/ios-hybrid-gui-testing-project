# Accessibility-first hybrid iOS GUI testing

MSc Software Engineering project (INM468), City St George's, University of London. Parag Dharadhar, 2026.

A Python test engine that runs plain-English test steps on native iOS apps. It finds each control from the XCUITest accessibility tree and calls a local vision model (ShowUI-2B) only when that match is uncertain. It is evaluated on 24 scenarios across three apps (432 runs), with an optional MCP interface.

## Layout

- `engine/` test engine
- `mcp_adapter/` MCP server
- `apps/` SwiftUI testbed and patches for SyncUps and NetNewsWire
- `benchmark/` scenarios and saved page sources
- `experiments/raw/` run logs
- `analysis/` analysis scripts and outputs
- `tests/` automated tests
- `docs/` decision register, AI-use log, pinned versions

## Quick start (no simulator needed)

```
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[appium,vlm,dev,analysis,mcp]'
pytest -q
python analysis/analyse.py experiments/raw/formal.jsonl --out /tmp/an
```

## Live runs

Needs macOS, Xcode 27.1, an iPhone 17 simulator on iOS 27.0 and Appium 3.8 (versions in `docs/versions.md`). Build the testbed with `apps/testbed/build.sh`, start `appium`, then:

```
python -m engine.cli run benchmark/scenarios/tb-07.yaml --config hybrid --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands
```

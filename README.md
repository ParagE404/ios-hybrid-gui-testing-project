# Accessibility-first hybrid iOS GUI testing

MSc Software Engineering project (INM468), City St George's, University of London. Parag Dharadhar, 2026.

A Python test engine that runs plain-English test steps on native iOS apps. The formal benchmark covers 24 scenarios across Errands, SyncUps and NetNewsWire, with baseline and perturbed conditions and three repetitions per configuration (432 runs). The project also compares direct and MCP invocation and evaluates sensitivity, seeded faults and two engine changes.

## Configurations

| CLI name | How it finds and acts on a control |
|---|---|
| `scripted` | Uses the fixed Appium locator stored with each targeted step. A failed lookup stops the step. |
| `a11y` (accessibility-only) | Ranks controls from the XCUITest page source using accessibility metadata. It takes the structured route when the best match clears the score and margin thresholds. On an uncertain match, it uses the top candidate if its score is positive. |
| `hybrid` | Uses the same scoring and routing as `a11y`. On an uncertain match, it asks local ShowUI-2B to locate the control on a screenshot and validates the proposed action. If neither of the two allowed model attempts produces a valid action, it uses the top structured candidate if its score is positive. |

The formal runs use a score threshold of 0.66 and a margin of 0.09. The v2 study compares the frozen `a11y` and `hybrid` behaviour with `a11y-v2` and `hybrid-v2`. The v2 options retry a missing match after scrolling and relax the visual candidate-set check when all ranked candidates are invalid. SEQ1 uses the accessibility-only engine through two interfaces, direct calls and MCP.

## Layout

- `engine/` test engine
- `mcp_adapter/` MCP server
- `apps/` SwiftUI testbed and patches for SyncUps and NetNewsWire
- `benchmark/` scenarios and saved page sources
- `experiments/raw/` run logs
- `analysis/` analysis scripts and outputs
- `tests/` automated tests
- `docs/` decision register, AI-use log, pinned versions
- `.mcp.json` MCP client configuration for the local engine server
- `.vscode/launch.json` debugger launch for the TB-07 demonstration
- `scripts.sh` command notes from recording the demo. Use [Live runs](#live-runs) for a fresh run.

## Quick start

Run the offline tests and analysis from the repository root with Python 3.12. The report commands use committed logs, saved screen captures and scenario definitions. They run without a simulator or model weights.

```sh
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev,analysis,mcp]'
pytest -q
```

## Regenerate report results

Run this block in the activated environment. It writes CSV, Markdown, PNG and PDF files to a fresh directory and prints its path. The [committed outputs](analysis/out/) provide a reference for comparison.

```sh
report_out=$(mktemp -d /tmp/ios-gui-report.XXXXXX)
report_raw=experiments/raw

python analysis/analyse.py "$report_raw/formal.jsonl" --out "$report_out"
python analysis/scenario_level.py "$report_raw/formal.jsonl" --out "$report_out"
python analysis/worked_example.py "$report_raw/formal.jsonl" --out "$report_out"
python analysis/seq1.py "$report_raw/seq1.jsonl" "$report_raw/seq1_timing.jsonl" \
  --formal "$report_raw/formal.jsonl" --out "$report_out"

python analysis/sensitivity.py "$report_raw/formal.jsonl" --out "$report_out"
python analysis/faults.py "$report_raw/faults.jsonl" \
  --reference "$report_raw/formal.jsonl" --out "$report_out"
python analysis/inertness.py "$report_raw/fault_inertness.jsonl" \
  --reference "$report_raw/formal.jsonl" --out "$report_out"
python analysis/v2.py "$report_raw/heldout.jsonl" --out "$report_out"
python analysis/inertness.py "$report_raw/heldout_inertness.jsonl" \
  --reference "$report_raw/formal.jsonl" --name heldout_inertness.md --out "$report_out"
python analysis/v2.py "$report_raw/heldout.jsonl" --regression "$report_raw/v2_regression.jsonl" \
  --reference "$report_raw/formal.jsonl" --md v2_regression.md --out "$report_out"

printf 'Report outputs: %s\n' "$report_out"
```

### Report tables and figures

The command names below refer to the invocations above. Both PNG and PDF versions are generated for each plotted figure.

| Report item | Command and output |
|---|---|
| Table 4.1 · Completion by configuration and condition | `analyse.py` → `completion.csv`. The denominators are 72 runs per configuration and condition. |
| Figure 4.1 · Completion with scenario-cluster confidence intervals | `analyse.py` → `fig_completion.png` / `.pdf` |
| Table 4.2 · Paired effects and exact McNemar tests | `analyse.py` → `paired_differences.csv` for effects and bootstrap intervals. `scenario_level.py` → `scenario_mcnemar.csv` for the one-pair-per-scenario test. [Summarise the perturbed rows](#report-specific-summaries). |
| Figure 4.2 · Completion by perturbation category | `analyse.py` → `fig_category.png` / `.pdf` |
| Table 4.3 · Perturbed completion by app | `scenario_level.py` → `scenario_outcomes.csv`. [Count scenarios with three successful repetitions](#report-specific-summaries) by app and configuration. |
| Figure 4.3 · TB-07 perturbation | `worked_example.py` → `fig_perturbation_tb07.png` / `.pdf`, using the saved baseline and perturbed detail-screen captures |
| Figure 4.4 · TB-07 model point, snapped control and tap | `worked_example.py` → `fig_worked_step_tb07.png` / `.pdf`, using the same captures and the logged hybrid step |
| Table 4.4 · Visual fallback steps and other failures | `analyse.py` → `steps_long.csv` for calls, routes and outcomes. `scenario_level.py` → `scenario_outcomes.csv` for first failures. The report groups cases and explains the causes using [raw telemetry](experiments/raw/formal.jsonl) and [saved screens](benchmark/pagesource/). |
| Figure 4.5 · Targeted step latency | `analyse.py` → `fig_step_latency.png` / `.pdf` |
| Table 4.5 and Appendix F.3 · Direct versus MCP (SEQ1) | `seq1.py` → `seq1.md`, `seq1_equivalence.csv` and `seq1_overhead.csv` |
| Table 4.6 · Seeded faults by configuration | `faults.py` → `faults_by_config.csv`. [Sum the two conditions](#report-specific-summaries) for each configuration. |
| Figure 4.6 · Seeded-fault outcomes | `faults.py` → `fig_faults.png` / `.pdf`, plotted from `faults_by_class.csv` |
| Figure 4.7 · Held-out completion by class and configuration | `v2.py` with the held-out log → `fig_v2_heldout.png` / `.pdf` and `v2_heldout_completion.csv` |
| Appendix F.1 · Run-level results | `analyse.py` → `results.md` and its CSV tables |
| Appendix F.2 and §4.6 · Scenario-level results and defect exclusion | `scenario_level.py` → `scenario_level.md`, `scenario_mcnemar.csv` and `sensitivity_excl_defects.csv` |
| Appendix F.4 and Appendix I.3 · Threshold and resolver-weight sensitivity (D-027) | `sensitivity.py` → `sensitivity.md`, `sensitivity_*.csv`, `fig_sensitivity_thresholds.*` and `fig_sensitivity_weights.*` |
| Appendix F.4 · Seeded-fault analysis (D-028) | `faults.py` → `faults.md` and `faults_*.csv`. `inertness.py` with the fault-check log → `fault_inertness.md`. |
| Appendix F.4 · Held-out and regression checks (D-029) | `v2.py` → `v2.md` and `v2_heldout_*.csv`. The invocation with `--regression` also writes `v2_regression.md` and `v2_regression.csv`. `inertness.py` with the held-out check log → `heldout_inertness.md`. |

### Report-specific summaries

After running the analysis block, this command writes the numeric rows for Tables 4.2, 4.3 and 4.6. Word supplies the display labels, rounding and formatting.

```sh
python - "$report_out" <<'PY'
from pathlib import Path
import sys

import pandas as pd

out = Path(sys.argv[1])
effects = pd.read_csv(out / "paired_differences.csv").query("condition == 'perturbed'")
tests = pd.read_csv(out / "scenario_mcnemar.csv").query("condition == 'perturbed'")
effects[["comparison", "diff_pp", "ci_low_pp", "ci_high_pp"]].merge(
    tests[["comparison", "a_only", "b_only", "exact_p"]],
    on="comparison", validate="one_to_one",
).to_csv(out / "table_4_2.csv", index=False)

configs = ["scripted", "a11y", "hybrid"]
counts = pd.read_csv(out / "scenario_outcomes.csv")
completed = counts[[f"perturbed_{c}" for c in configs]].eq(3)
completed.columns = configs
by_app = completed.groupby(counts["app"]).sum().loc[["testbed", "syncups", "netnewswire"]]
by_app.loc["external_apps"] = by_app.loc[["syncups", "netnewswire"]].sum()
by_app.loc["all"] = completed.sum()
by_app.to_csv(out / "table_4_3.csv")

faults = pd.read_csv(out / "faults_by_config.csv")
faults.groupby("config")[["false_pass", "detection", "fragility"]].sum().loc[configs].to_csv(
    out / "table_4_6.csv"
)
PY
```

### Report tables and diagram assembled in Word

| Report item | Source material and checks |
|---|---|
| Tables 1.1 and 1.2 · Objectives and effort | The report’s approved objectives and planned-versus-actual effort record |
| Table 2.1 · Literature synthesis | [Literature log](docs/literature.md), [extension reading list](docs/literature-extension.md) and the report’s references |
| Tables 3.1, 3.2 and 3.3 · Lifecycle, requirements and timeline | [Decision register](docs/decision-register.md), [benchmark design](docs/benchmark-design.md), run logs, `pytest -q` and `git log main` |
| Figure 3.1 · Engine architecture | Diagram of the [runner](engine/runner.py), [resolver](engine/resolver.py), [router](engine/router.py), [validator](engine/validator.py) and [Appium backend](engine/backend.py) |
| Table 5.1 and Appendix B · AI use | [AI-use log](docs/ai-use-log.md) |
| Table 7.1 · Objectives against their tests | Table 1.1, `pytest -q`, and the formal, SEQ1 and extension results above |
| Appendix C.2 · Component attribution | [Decision register](docs/decision-register.md), including links to commits and upstream sources |
| Table D.1 · Pinned versions | [Environment and version checks](docs/versions.md) |
| Table E.1 · Formal scenario catalogue | [Formal scenario YAML](benchmark/scenarios/). IDs, app, category and perturbation are specified per scenario. |
| Appendix G.1 · Submitted files | The report’s submission inventory and the repository tree |
| Tables H.1 and H.2 · Search strands and self-healing tools | [Literature log](docs/literature.md), [extension reading list](docs/literature-extension.md) and the source citations in Appendix H |
| Tables I.1 and I.2 · Seeded-fault and held-out scenarios | [Seeded-fault YAML](benchmark/faults/) and [held-out YAML](benchmark/heldout/). The `fault` and `heldout` blocks record the case definitions. |

## Live runs

Needs macOS, Xcode 27.1, XcodeGen, an iPhone 17 simulator on iOS 27.0 and Appium 3.8. See the [pinned versions](docs/versions.md) for the driver and model revisions. Boot the simulator and run `appium` in another terminal. The build script installs Errands on the booted simulator.

```sh
python -m pip install -e '.[appium,vlm]'
apps/testbed/build.sh
python -m engine.cli run benchmark/scenarios/tb-07.yaml --config hybrid --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands
```

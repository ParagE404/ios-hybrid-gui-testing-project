import sys
from pathlib import Path

from engine.batch import plan_runs, run_batch
from engine.telemetry import Telemetry
from engine.vlm import FakeVLM

from .test_batch import SCN, fake

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))
import analyse  # noqa: E402


def test_pipeline_end_to_end(tmp_path):
    log = tmp_path / "f.jsonl"
    plan = plan_runs([SCN], ["baseline", "perturbed"], ["scripted", "a11y", "hybrid"], 2, seed=3)
    run_batch([SCN], plan, lambda app: fake(), lambda: None, Telemetry(log, run_id="t"),
              vlm_factory=lambda: FakeVLM(), progress=lambda m: None)
    runs, steps, notes = analyse.load([str(log)])
    assert notes["runs"] == 12 and len(runs) == 12
    comp = analyse.completion_table(runs)
    assert set(comp.config) == {"scripted", "a11y", "hybrid"} and (comp.rate == 1.0).all()
    diffs = analyse.paired_differences(runs, n_boot=200)
    assert (diffs.diff_pp == 0).all() and (diffs.mcnemar_p == 1.0).all()
    assert analyse.failure_table(runs, steps).empty
    lat = analyse.latency_table(runs, steps)
    assert len(lat) == 6
    analyse.figures(runs, steps, comp, analyse.category_table(runs), tmp_path)
    assert (tmp_path / "fig_completion.png").exists()

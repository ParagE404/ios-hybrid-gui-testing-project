"""Tests for the pilot calibration rule. Origin: original, """
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))
from calibrate import calibrate  # noqa: E402


def P(top, margin, correct):
    return {"top": top, "margin": margin, "correct": correct}


def test_threshold_sits_between_wrong_and_right():
    pts = [P(0.95, 0.5, True), P(0.90, 0.3, True), P(0.85, 0.2, True), P(0.70, 0.02, False), P(0.72, 0.25, False)]
    out = calibrate(pts)
    assert out["precision_achieved"] == 1.0
    assert out["coverage"] == 0.6                 # all three correct points accepted
    assert 0.73 <= out["tau"] <= 0.85             # inside the gap, not at its edge
    assert out["tied_tau_range"] == [0.73, 0.85]


def test_floors_respected_when_everything_is_correct():
    out = calibrate([P(0.99, 0.9, True), P(0.97, 0.8, True)])
    assert out["tau"] >= 0.60 and out["delta"] >= 0.05 and out["coverage"] == 1.0


def test_reports_best_precision_when_perfect_is_impossible():
    out = calibrate([P(0.99, 0.9, False), P(0.98, 0.9, True)])
    assert out["precision_achieved"] < 1.0 or out["coverage"] == 0

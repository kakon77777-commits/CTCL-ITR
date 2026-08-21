from copy import deepcopy

import pytest

from ctcl_itr.horizon_calibration import (
    HorizonCalibrationError,
    calibrate_subject,
)


def _mins(distinct=2, total=10, per_depth=2):
    return {
        "min_distinct_depths": distinct,
        "min_total_trials": total,
        "min_trials_per_depth": per_depth,
    }


def test_aggregates_duplicate_depths_and_preserves_evidence_refs():
    points = [
        {"depth": 4, "trials": 5, "successes": 5, "evidence_refs": ["a"]},
        {"depth": 4, "trials": 5, "successes": 4, "evidence_refs": ["b", "a"]},
        {"depth": 8, "trials": 10, "successes": 5, "evidence_refs": ["c"]},
    ]
    profile = calibrate_subject(
        points,
        target_reliability=0.75,
        confidence_level=0.90,
        minimums=_mins(),
    )
    assert [p["depth"] for p in profile["points"]] == [4.0, 8.0]
    assert profile["points"][0]["trials"] == 10
    assert profile["points"][0]["successes"] == 9
    assert profile["points"][0]["evidence_refs"] == ["a", "b"]
    assert profile["evidence_refs"] == ["a", "b", "c"]


def test_wilson_interval_is_reported_for_each_empirical_point():
    points = [
        {"depth": 4, "trials": 20, "successes": 20, "evidence_refs": []},
        {"depth": 8, "trials": 20, "successes": 10, "evidence_refs": []},
    ]
    profile = calibrate_subject(points, 0.75, 0.90, _mins(total=40))
    first = profile["points"][0]
    assert first["empirical_success_rate"] == 1.0
    assert 0.8 < first["wilson_lower"] < 1.0
    assert first["wilson_upper"] == pytest.approx(1.0)


def test_weighted_pava_enforces_nonincreasing_reliability():
    points = [
        {"depth": 1, "trials": 20, "successes": 18, "evidence_refs": []},  # .90
        {"depth": 2, "trials": 20, "successes": 16, "evidence_refs": []},  # .80
        {"depth": 3, "trials": 20, "successes": 17, "evidence_refs": []},  # .85 violation
        {"depth": 4, "trials": 20, "successes": 8, "evidence_refs": []},   # .40
    ]
    profile = calibrate_subject(points, 0.70, 0.90, _mins(distinct=4, total=80))
    fitted = [p["fitted_success_rate"] for p in profile["points"]]
    assert fitted == pytest.approx([0.90, 0.825, 0.825, 0.40])
    assert fitted == sorted(fitted, reverse=True)


def test_exact_target_crossing_returns_observed_depth():
    points = [
        {"depth": 4, "trials": 20, "successes": 20, "evidence_refs": []},
        {"depth": 8, "trials": 20, "successes": 19, "evidence_refs": []},
        {"depth": 12, "trials": 20, "successes": 18, "evidence_refs": []},
        {"depth": 16, "trials": 20, "successes": 10, "evidence_refs": []},
    ]
    profile = calibrate_subject(points, 0.90, 0.90, _mins(distinct=4, total=80))
    assert profile["support_status"] == "supported"
    assert profile["horizon_depth"] == pytest.approx(12.0)
    assert profile["crossing_bracket"]["lower_depth"] == 12.0


def test_interpolated_target_crossing_is_linear_in_depth_probability_plane():
    points = [
        {"depth": 2, "trials": 20, "successes": 20, "evidence_refs": []},
        {"depth": 8, "trials": 20, "successes": 19, "evidence_refs": []},
        {"depth": 10, "trials": 20, "successes": 17, "evidence_refs": []},
        {"depth": 14, "trials": 20, "successes": 8, "evidence_refs": []},
    ]
    profile = calibrate_subject(points, 0.90, 0.90, _mins(distinct=4, total=80))
    assert profile["support_status"] == "supported"
    assert profile["horizon_depth"] == pytest.approx(9.0)
    assert profile["crossing_bracket"] == pytest.approx({
        "lower_depth": 8.0,
        "upper_depth": 10.0,
        "lower_probability": 0.95,
        "upper_probability": 0.85,
    })


def test_refuses_unbracketed_high_and_low_targets_instead_of_extrapolating():
    above = [
        {"depth": 1, "trials": 10, "successes": 10, "evidence_refs": []},
        {"depth": 2, "trials": 10, "successes": 10, "evidence_refs": []},
    ]
    high = calibrate_subject(above, 0.90, 0.90, _mins(total=20))
    assert high["horizon_depth"] is None
    assert high["support_status"] == "target_not_bracketed_high"

    below = [
        {"depth": 1, "trials": 10, "successes": 5, "evidence_refs": []},
        {"depth": 2, "trials": 10, "successes": 4, "evidence_refs": []},
    ]
    low = calibrate_subject(below, 0.90, 0.90, _mins(total=20))
    assert low["horizon_depth"] is None
    assert low["support_status"] == "target_not_bracketed_low"


def test_insufficient_evidence_minimums_are_explicit():
    points = [
        {"depth": 1, "trials": 4, "successes": 4, "evidence_refs": []},
        {"depth": 2, "trials": 4, "successes": 2, "evidence_refs": []},
    ]
    profile = calibrate_subject(points, 0.75, 0.90, _mins(distinct=3, total=20, per_depth=5))
    assert profile["horizon_depth"] is None
    assert profile["support_status"] == "insufficient_evidence"
    assert set(profile["support_reasons"]) == {
        "insufficient_distinct_depths",
        "insufficient_total_trials",
        "insufficient_trials_per_depth",
    }


@pytest.mark.parametrize(
    "point",
    [
        {"depth": 1, "trials": 0, "successes": 0, "evidence_refs": []},
        {"depth": 1, "trials": 5, "successes": 6, "evidence_refs": []},
        {"depth": -1, "trials": 5, "successes": 4, "evidence_refs": []},
        {"depth": float("inf"), "trials": 5, "successes": 4, "evidence_refs": []},
    ],
)
def test_invalid_trial_points_are_rejected(point):
    with pytest.raises(HorizonCalibrationError):
        calibrate_subject([point], 0.9, 0.9, _mins(distinct=1, total=1, per_depth=1))


def test_calibration_does_not_mutate_inputs():
    points = [
        {"depth": 4, "trials": 10, "successes": 10, "evidence_refs": ["a"]},
        {"depth": 8, "trials": 10, "successes": 5, "evidence_refs": ["b"]},
    ]
    original = deepcopy(points)
    calibrate_subject(points, 0.75, 0.90, _mins(total=20))
    assert points == original

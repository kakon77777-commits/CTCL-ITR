"""Evidence-backed Horizon calibration for CTCL-ITR v0.2.7."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite, sqrt
from statistics import NormalDist
from typing import Any


class HorizonCalibrationError(ValueError):
    """Raised when Horizon calibration evidence or contracts are invalid."""


DEFAULT_MINIMUMS = {
    "min_distinct_depths": 4,
    "min_total_trials": 40,
    "min_trials_per_depth": 5,
}

METHOD_ID = "monotone_binomial_pava_v1"


def _number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise HorizonCalibrationError(f"{label} must be numeric") from exc
    if not isfinite(result):
        raise HorizonCalibrationError(f"{label} must be finite")
    return result


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise HorizonCalibrationError(f"{label} must be a positive integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise HorizonCalibrationError(f"{label} must be a positive integer") from exc
    if result != value or result <= 0:
        raise HorizonCalibrationError(f"{label} must be a positive integer")
    return result


def _validate_probability(value: Any, label: str, *, inclusive_zero: bool = False) -> float:
    result = _number(value, label)
    lower_ok = result >= 0.0 if inclusive_zero else result > 0.0
    if not lower_ok or result > 1.0:
        interval = "[0, 1]" if inclusive_zero else "(0, 1]"
        raise HorizonCalibrationError(f"{label} must be in {interval}")
    return result


def _validate_minimums(minimums: dict[str, Any] | None) -> dict[str, int]:
    source = deepcopy(DEFAULT_MINIMUMS if minimums is None else minimums)
    required = ("min_distinct_depths", "min_total_trials", "min_trials_per_depth")
    missing = [key for key in required if key not in source]
    if missing:
        raise HorizonCalibrationError(f"missing evidence minimums: {', '.join(missing)}")
    return {key: _positive_int(source[key], key) for key in required}


def _aggregate_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(points, list) or not points:
        raise HorizonCalibrationError("evidence points must be a non-empty array")
    grouped: dict[float, dict[str, Any]] = {}
    for index, raw in enumerate(points):
        if not isinstance(raw, dict):
            raise HorizonCalibrationError(f"evidence point {index} must be an object")
        depth = _number(raw.get("depth"), f"points[{index}].depth")
        if depth < 0:
            raise HorizonCalibrationError("depth must be nonnegative")
        trials = _positive_int(raw.get("trials"), f"points[{index}].trials")
        successes_value = raw.get("successes")
        if isinstance(successes_value, bool):
            raise HorizonCalibrationError("successes must be an integer")
        try:
            successes = int(successes_value)
        except (TypeError, ValueError) as exc:
            raise HorizonCalibrationError("successes must be an integer") from exc
        if successes != successes_value or successes < 0 or successes > trials:
            raise HorizonCalibrationError("successes must satisfy 0 <= successes <= trials")
        refs = raw.get("evidence_refs", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise HorizonCalibrationError("evidence_refs must contain non-empty strings")
        bucket = grouped.setdefault(depth, {"depth": depth, "trials": 0, "successes": 0, "evidence_refs": set()})
        bucket["trials"] += trials
        bucket["successes"] += successes
        bucket["evidence_refs"].update(refs)
    return [
        {
            "depth": depth,
            "trials": grouped[depth]["trials"],
            "successes": grouped[depth]["successes"],
            "evidence_refs": sorted(grouped[depth]["evidence_refs"]),
        }
        for depth in sorted(grouped)
    ]


def _wilson_interval(successes: int, trials: int, confidence_level: float) -> tuple[float, float]:
    # Two-sided Wilson score interval using the standard-normal quantile.
    alpha = 1.0 - confidence_level
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    p = successes / trials
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denom
    half = z * sqrt((p * (1.0 - p) / trials) + z2 / (4.0 * trials * trials)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _pava_nonincreasing(points: list[dict[str, Any]]) -> list[float]:
    # Blocks store inclusive indices and aggregate binomial sufficient statistics.
    blocks: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        block = {
            "start": index,
            "end": index,
            "trials": point["trials"],
            "successes": point["successes"],
        }
        blocks.append(block)
        # Non-increasing expected: previous mean must be >= next mean.
        while len(blocks) >= 2:
            left, right = blocks[-2], blocks[-1]
            left_mean = left["successes"] / left["trials"]
            right_mean = right["successes"] / right["trials"]
            if left_mean >= right_mean:
                break
            merged = {
                "start": left["start"],
                "end": right["end"],
                "trials": left["trials"] + right["trials"],
                "successes": left["successes"] + right["successes"],
            }
            blocks[-2:] = [merged]

    fitted = [0.0] * len(points)
    for block in blocks:
        mean = block["successes"] / block["trials"]
        for index in range(block["start"], block["end"] + 1):
            fitted[index] = mean
    return fitted


def _crossing(points: list[dict[str, Any]], target: float) -> tuple[str, float | None, dict[str, float] | None]:
    rates = [point["fitted_success_rate"] for point in points]
    if all(rate >= target for rate in rates):
        # Equal-at-target at an observed depth is supported only if a deeper point falls below.
        if rates[-1] == target:
            return "target_not_bracketed_high", None, None
        return "target_not_bracketed_high", None, None
    if all(rate < target for rate in rates):
        return "target_not_bracketed_low", None, None

    last_supported = None
    for index, rate in enumerate(rates):
        if rate >= target:
            last_supported = index
        else:
            break
    if last_supported is None:
        return "target_not_bracketed_low", None, None
    if last_supported >= len(points) - 1:
        return "target_not_bracketed_high", None, None

    left = points[last_supported]
    right = points[last_supported + 1]
    p_left = left["fitted_success_rate"]
    p_right = right["fitted_success_rate"]
    d_left = left["depth"]
    d_right = right["depth"]

    if p_left == target:
        horizon = d_left
    elif p_left == p_right:
        # A flat block cannot cross a target strictly between values.
        raise HorizonCalibrationError("invalid flat crossing in fitted reliability curve")
    else:
        fraction = (p_left - target) / (p_left - p_right)
        horizon = d_left + fraction * (d_right - d_left)

    return (
        "supported",
        horizon,
        {
            "lower_depth": d_left,
            "upper_depth": d_right,
            "lower_probability": p_left,
            "upper_probability": p_right,
        },
    )


def calibrate_subject(
    points: list[dict[str, Any]],
    target_reliability: float,
    confidence_level: float = 0.90,
    minimums: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calibrate one subject's interaction-depth reliability horizon.

    The reference method is empirical and monotone. It does not extrapolate
    beyond the observed depth range.
    """

    raw_points = deepcopy(points)
    target = _validate_probability(target_reliability, "target_reliability")
    confidence = _validate_probability(confidence_level, "confidence_level")
    mins = _validate_minimums(minimums)
    aggregated = _aggregate_points(raw_points)

    fitted_rates = _pava_nonincreasing(aggregated)
    enriched: list[dict[str, Any]] = []
    evidence_refs: set[str] = set()
    for point, fitted in zip(aggregated, fitted_rates):
        empirical = point["successes"] / point["trials"]
        lower, upper = _wilson_interval(point["successes"], point["trials"], confidence)
        evidence_refs.update(point["evidence_refs"])
        enriched.append(
            {
                **point,
                "empirical_success_rate": empirical,
                "wilson_lower": lower,
                "wilson_upper": upper,
                "fitted_success_rate": fitted,
            }
        )

    total_trials = sum(point["trials"] for point in aggregated)
    support_reasons: list[str] = []
    if len(aggregated) < mins["min_distinct_depths"]:
        support_reasons.append("insufficient_distinct_depths")
    if total_trials < mins["min_total_trials"]:
        support_reasons.append("insufficient_total_trials")
    if any(point["trials"] < mins["min_trials_per_depth"] for point in aggregated):
        support_reasons.append("insufficient_trials_per_depth")

    if support_reasons:
        status, horizon, bracket = "insufficient_evidence", None, None
    else:
        status, horizon, bracket = _crossing(enriched, target)
        if status != "supported":
            support_reasons.append(status)

    return {
        "method": METHOD_ID,
        "target_reliability": target,
        "evidence_confidence_p": confidence,
        "minimums": mins,
        "distinct_depths": len(aggregated),
        "total_trials": total_trials,
        "total_successes": sum(point["successes"] for point in aggregated),
        "support_status": status,
        "support_reasons": support_reasons,
        "horizon_depth": horizon,
        "crossing_bracket": bracket,
        "points": enriched,
        "evidence_refs": sorted(evidence_refs),
        "non_authoritative": True,
    }


def calibrate_horizon_suite(suite: dict[str, Any]) -> dict[str, Any]:
    """Calibrate autonomy/governance evidence under one shared contract."""

    if not isinstance(suite, dict):
        raise HorizonCalibrationError("calibration suite must be an object")
    source = deepcopy(suite)
    if source.get("schema_version") != "0.2.7":
        raise HorizonCalibrationError("calibration suite must use schema_version 0.2.7")
    calibration_id = source.get("calibration_id")
    calibrated_at = source.get("calibrated_at")
    if not isinstance(calibration_id, str) or not calibration_id:
        raise HorizonCalibrationError("calibration_id is required")
    if not isinstance(calibrated_at, str) or not calibrated_at:
        raise HorizonCalibrationError("calibrated_at is required")

    contract = source.get("measurement_contract")
    if not isinstance(contract, dict):
        raise HorizonCalibrationError("measurement_contract is required")
    if contract.get("unit") != "interaction_depth":
        raise HorizonCalibrationError("calibration unit must be interaction_depth")
    target = _validate_probability(contract.get("reliability_p"), "reliability_p")
    scope_id = contract.get("scope_id")
    if not isinstance(scope_id, str) or not scope_id:
        raise HorizonCalibrationError("measurement_contract scope_id is required")
    if contract.get("assessment_method") != METHOD_ID:
        raise HorizonCalibrationError(f"assessment_method must be {METHOD_ID}")

    confidence = _validate_probability(source.get("evidence_confidence_p"), "evidence_confidence_p")
    minimums = _validate_minimums(source.get("minimums"))
    subjects = source.get("subjects")
    if not isinstance(subjects, dict):
        raise HorizonCalibrationError("subjects is required")
    if set(subjects) != {"autonomy", "governance"}:
        raise HorizonCalibrationError("subjects must contain exactly autonomy and governance")

    profiles = {
        name: calibrate_subject(
            subjects[name],
            target_reliability=target,
            confidence_level=confidence,
            minimums=minimums,
        )
        for name in ("autonomy", "governance")
    }

    derived_assessment = None
    if all(profiles[name]["support_status"] == "supported" for name in profiles):
        evidence_refs = sorted(
            set(profiles["autonomy"]["evidence_refs"]) | set(profiles["governance"]["evidence_refs"])
        )
        derived_assessment = {
            "schema_version": "0.2.6",
            "assessment_id": f"horizon:{calibration_id}",
            "assessed_at": calibrated_at,
            "measurement_contract": deepcopy(contract),
            "autonomy_horizon_depth": profiles["autonomy"]["horizon_depth"],
            "governance_horizon_depth": profiles["governance"]["horizon_depth"],
            "evidence_refs": evidence_refs,
        }

    return {
        "schema_version": "0.2.7",
        "calibration_id": calibration_id,
        "calibrated_at": calibrated_at,
        "measurement_contract": deepcopy(contract),
        "evidence_confidence_p": confidence,
        "minimums": minimums,
        "subjects": profiles,
        "derived_assessment": derived_assessment,
        "non_authoritative": True,
    }


def _main(argv=None) -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Calibrate CTCL-ITR autonomy/governance horizons from repeated evidence.")
    parser.add_argument("--suite", required=True, help="Path to HorizonCalibrationSuite JSON")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    report = calibrate_horizon_suite(suite)
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    _main()

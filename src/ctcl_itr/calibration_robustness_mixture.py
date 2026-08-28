"""Mixture and support helpers for CTCL-ITR calibration robustness."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
from typing import Any

from .calibration_robustness_common import CalibrationRobustnessError

def _normalize_weights(raw: Any, family_ids: list[str], label: str) -> dict[str, float]:
    if not isinstance(raw, dict) or not raw:
        raise CalibrationRobustnessError(f"{label} must be a non-empty object")
    if set(raw) != set(family_ids):
        raise CalibrationRobustnessError(f"{label} must contain exactly the compared task families")
    parsed: dict[str, float] = {}
    for family_id in sorted(family_ids):
        value = raw[family_id]
        try:
            weight = float(value)
        except (TypeError, ValueError) as exc:
            raise CalibrationRobustnessError(f"{label}.{family_id} must be numeric") from exc
        if not isfinite(weight) or weight <= 0.0:
            raise CalibrationRobustnessError(f"{label}.{family_id} must be positive and finite")
        parsed[family_id] = weight
    total = sum(parsed.values())
    return {family_id: parsed[family_id] / total for family_id in sorted(parsed)}

def _observed_weights(snapshot: dict[str, Any], subject: str, family_ids: list[str]) -> dict[str, float]:
    masses = {
        family_id: float(snapshot["families"][family_id]["trial_mass"][subject])
        for family_id in family_ids
    }
    total = sum(masses.values())
    if total <= 0.0:
        raise CalibrationRobustnessError("observed trial mass must be positive")
    return {family_id: masses[family_id] / total for family_id in sorted(masses)}

def _subject_profile(snapshot: dict[str, Any], family_id: str, subject: str) -> dict[str, Any]:
    return snapshot["families"][family_id]["profile"]["subjects"][subject]

def _interpolate_probability(profile: dict[str, Any], depth: float) -> float:
    points = profile["points"]
    if not points:
        raise CalibrationRobustnessError("family profile has no points")
    low = float(points[0]["depth"])
    high = float(points[-1]["depth"])
    if depth < low or depth > high:
        raise CalibrationRobustnessError("mixture interpolation would extrapolate outside observed support")
    for point in points:
        if float(point["depth"]) == depth:
            return float(point["fitted_success_rate"])
    for left, right in zip(points, points[1:]):
        d0 = float(left["depth"])
        d1 = float(right["depth"])
        if d0 < depth < d1:
            p0 = float(left["fitted_success_rate"])
            p1 = float(right["fitted_success_rate"])
            if d1 == d0:
                return p0
            fraction = (depth - d0) / (d1 - d0)
            return p0 + fraction * (p1 - p0)
    raise CalibrationRobustnessError("could not interpolate family probability")

def _mixture_horizon(
    snapshot: dict[str, Any],
    subject: str,
    weights: dict[str, float],
) -> dict[str, Any]:
    target = float(snapshot["measurement_contract"]["reliability_p"])
    positive_families = [family_id for family_id, weight in weights.items() if weight > 0.0]
    unsupported = [
        family_id
        for family_id in positive_families
        if _subject_profile(snapshot, family_id, subject)["support_status"] != "supported"
    ]
    if unsupported:
        return {
            "support_status": "unsupported",
            "support_reasons": [f"family_unsupported:{family_id}" for family_id in unsupported],
            "horizon_depth": None,
            "common_support": None,
            "crossing_bracket": None,
            "curve": [],
            "weights": deepcopy(weights),
        }

    lows = []
    highs = []
    for family_id in positive_families:
        points = _subject_profile(snapshot, family_id, subject)["points"]
        lows.append(float(points[0]["depth"]))
        highs.append(float(points[-1]["depth"]))
    common_low = max(lows)
    common_high = min(highs)
    if common_low >= common_high:
        return {
            "support_status": "unsupported",
            "support_reasons": ["no_common_depth_support"],
            "horizon_depth": None,
            "common_support": [common_low, common_high],
            "crossing_bracket": None,
            "curve": [],
            "weights": deepcopy(weights),
        }

    candidate_depths = {common_low, common_high}
    for family_id in positive_families:
        for point in _subject_profile(snapshot, family_id, subject)["points"]:
            depth = float(point["depth"])
            if common_low <= depth <= common_high:
                candidate_depths.add(depth)
    depths = sorted(candidate_depths)
    curve = []
    for depth in depths:
        probability = sum(
            weights[family_id]
            * _interpolate_probability(_subject_profile(snapshot, family_id, subject), depth)
            for family_id in positive_families
        )
        curve.append({"depth": depth, "success_probability": probability})

    probabilities = [point["success_probability"] for point in curve]
    if all(probability >= target for probability in probabilities):
        return {
            "support_status": "unsupported",
            "support_reasons": ["target_not_bracketed_high"],
            "horizon_depth": None,
            "common_support": [common_low, common_high],
            "crossing_bracket": None,
            "curve": curve,
            "weights": deepcopy(weights),
        }
    if all(probability < target for probability in probabilities):
        return {
            "support_status": "unsupported",
            "support_reasons": ["target_not_bracketed_low"],
            "horizon_depth": None,
            "common_support": [common_low, common_high],
            "crossing_bracket": None,
            "curve": curve,
            "weights": deepcopy(weights),
        }

    left_index = None
    for index, probability in enumerate(probabilities[:-1]):
        if probability >= target and probabilities[index + 1] < target:
            left_index = index
            break
    if left_index is None:
        return {
            "support_status": "unsupported",
            "support_reasons": ["target_not_bracketed_in_common_support"],
            "horizon_depth": None,
            "common_support": [common_low, common_high],
            "crossing_bracket": None,
            "curve": curve,
            "weights": deepcopy(weights),
        }

    left = curve[left_index]
    right = curve[left_index + 1]
    p0 = left["success_probability"]
    p1 = right["success_probability"]
    d0 = left["depth"]
    d1 = right["depth"]
    if p0 == target:
        horizon = d0
    elif p0 == p1:
        return {
            "support_status": "unsupported",
            "support_reasons": ["flat_target_crossing"],
            "horizon_depth": None,
            "common_support": [common_low, common_high],
            "crossing_bracket": None,
            "curve": curve,
            "weights": deepcopy(weights),
        }
    else:
        fraction = (p0 - target) / (p0 - p1)
        horizon = d0 + fraction * (d1 - d0)

    return {
        "support_status": "supported",
        "support_reasons": [],
        "horizon_depth": horizon,
        "common_support": [common_low, common_high],
        "crossing_bracket": {
            "lower_depth": d0,
            "upper_depth": d1,
            "lower_probability": p0,
            "upper_probability": p1,
        },
        "curve": curve,
        "weights": deepcopy(weights),
    }

def _sign(value: float, tolerance: float = 1e-12) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0

def _range_or_none(values: list[float]) -> list[float] | None:
    if not values:
        return None
    return [min(values), max(values)]

def _context_diagnostics(base: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    backend_changed = base["backend_id"] != current["backend_id"]
    benchmark_version_changed = base["benchmark_version"] != current["benchmark_version"]
    agent_config_changed = base["agent_config_id"] != current["agent_config_id"]
    family_set_changed = set(base["families"]) != set(current["families"])
    changed_axes = sum((backend_changed, benchmark_version_changed, agent_config_changed, family_set_changed))
    if backend_changed and changed_axes == 1:
        comparison_kind = "cross_backend"
    elif changed_axes == 0:
        comparison_kind = "longitudinal_same_configuration"
    else:
        comparison_kind = "mixed_configuration_change"
    return {
        "backend_changed": backend_changed,
        "benchmark_version_changed": benchmark_version_changed,
        "agent_config_changed": agent_config_changed,
        "family_set_changed": family_set_changed,
        "comparison_kind": comparison_kind,
    }

def _parse_datetime_value(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise CalibrationRobustnessError(f"{label} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise CalibrationRobustnessError(f"{label} must include a timezone offset")
    return parsed


"""Shared validation/grid helpers for CTCL-ITR v0.2.10 mixture sensitivity."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Iterator

from .calibration_robustness import build_calibration_snapshot
from .calibration_robustness_common import _parse_time, _required_string

METHOD_ID = "simplex_grid_reference_mixture_v1"


class CalibrationMixtureSensitivityError(ValueError):
    """Raised when v0.2.10 mixture-sensitivity contracts are invalid."""


def _number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise CalibrationMixtureSensitivityError(f"{label} must be numeric") from exc
    if not isfinite(result):
        raise CalibrationMixtureSensitivityError(f"{label} must be finite")
    return result


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise CalibrationMixtureSensitivityError(f"{label} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CalibrationMixtureSensitivityError(f"{label} must be a positive integer") from exc
    if parsed != value or parsed <= 0:
        raise CalibrationMixtureSensitivityError(f"{label} must be a positive integer")
    return parsed


def _as_grid_units(value: Any, label: str, total_units: int | None = None) -> tuple[float, int]:
    numeric = _number(value, label)
    if numeric <= 0.0 or numeric >= 1.0:
        raise CalibrationMixtureSensitivityError(f"{label} must be in (0, 1)")
    if total_units is None:
        inverse = 1.0 / numeric
        units = round(inverse)
        if units < 2 or abs(inverse - units) > 1e-9:
            raise CalibrationMixtureSensitivityError(
                f"{label} must partition one into an integer number of grid units"
            )
        return numeric, units
    units_float = numeric * total_units
    units = round(units_float)
    if units <= 0 or abs(units_float - units) > 1e-9:
        raise CalibrationMixtureSensitivityError(
            f"{label} must be an integer multiple of grid_step"
        )
    return numeric, units


def _validate_spec(raw: dict[str, Any], family_count: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationMixtureSensitivityError("sensitivity spec must be an object")
    spec = deepcopy(raw)
    if spec.get("schema_version") != "0.2.10":
        raise CalibrationMixtureSensitivityError("sensitivity spec must use schema_version 0.2.10")
    _required_string(spec.get("sensitivity_id"), "sensitivity_id")
    spec["generated_at"] = _parse_time(spec.get("generated_at"), "generated_at")
    if spec.get("method") != METHOD_ID:
        raise CalibrationMixtureSensitivityError(f"method must be {METHOD_ID}")
    step, total_units = _as_grid_units(spec.get("grid_step"), "grid_step")
    minimum, minimum_units = _as_grid_units(
        spec.get("minimum_family_weight"), "minimum_family_weight", total_units
    )
    max_points = _positive_int(spec.get("max_grid_points"), "max_grid_points")
    if minimum_units * family_count > total_units:
        raise CalibrationMixtureSensitivityError(
            "minimum_family_weight leaves no feasible simplex grid"
        )
    spec["grid_step"] = step
    spec["minimum_family_weight"] = minimum
    spec["max_grid_points"] = max_points
    spec["_total_units"] = total_units
    spec["_minimum_units"] = minimum_units
    return spec


def _integer_compositions(total: int, parts: int, minimum: int) -> Iterator[tuple[int, ...]]:
    if parts == 1:
        if total >= minimum:
            yield (total,)
        return
    remaining_minimum = minimum * (parts - 1)
    maximum_first = total - remaining_minimum
    for first in range(minimum, maximum_first + 1):
        for tail in _integer_compositions(total - first, parts - 1, minimum):
            yield (first, *tail)


def _simplex_grid(families: list[str], spec: dict[str, Any]) -> list[dict[str, float]]:
    grid: list[dict[str, float]] = []
    total_units = spec["_total_units"]
    minimum_units = spec["_minimum_units"]
    for units in _integer_compositions(total_units, len(families), minimum_units):
        grid.append(
            {
                family: unit / total_units
                for family, unit in zip(families, units)
            }
        )
        if len(grid) > spec["max_grid_points"]:
            raise CalibrationMixtureSensitivityError(
                "simplex grid exceeds max_grid_points"
            )
    if not grid:
        raise CalibrationMixtureSensitivityError("simplex grid is empty")
    return grid


def _sign_shares(values: list[float], tolerance: float = 1e-12) -> dict[str, float] | None:
    if not values:
        return None
    counts = {"positive": 0, "negative": 0, "zero": 0}
    for value in values:
        if value > tolerance:
            counts["positive"] += 1
        elif value < -tolerance:
            counts["negative"] += 1
        else:
            counts["zero"] += 1
    n = len(values)
    return {key: counts[key] / n for key in ("positive", "negative", "zero")}


def _sensitivity_range(scan: list[dict[str, Any]]) -> dict[str, Any] | None:
    supported = [entry for entry in scan if entry["support_status"] == "supported"]
    if not supported:
        return None
    minimum = min(supported, key=lambda entry: entry["composition_adjusted_delta"])
    maximum = max(supported, key=lambda entry: entry["composition_adjusted_delta"])
    return {
        "minimum": minimum["composition_adjusted_delta"],
        "maximum": maximum["composition_adjusted_delta"],
        "span": maximum["composition_adjusted_delta"] - minimum["composition_adjusted_delta"],
        "argmin_weights": deepcopy(minimum["reference_family_weights"]),
        "argmax_weights": deepcopy(maximum["reference_family_weights"]),
    }



def _weights_match(left: dict[str, Any], right: dict[str, Any], tolerance: float = 1e-12) -> bool:
    if set(left) != set(right):
        return False
    return all(abs(float(left[key]) - float(right[key])) <= tolerance for key in left)


def _validate_uncertainty_report(
    report: dict[str, Any],
    *,
    base_snapshot_id: str,
    current_snapshot_id: str,
    comparison_id: str,
    measurement_contract: dict[str, Any],
    reference_family_weights: dict[str, float],
) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("schema_version") != "0.2.9":
        raise CalibrationMixtureSensitivityError("uncertainty report must use schema_version 0.2.9")
    for field, expected in (
        ("base_snapshot_id", base_snapshot_id),
        ("current_snapshot_id", current_snapshot_id),
        ("comparison_id", comparison_id),
    ):
        if report.get(field) != expected:
            raise CalibrationMixtureSensitivityError(f"uncertainty report {field} mismatch")
    if report.get("measurement_contract") != measurement_contract:
        raise CalibrationMixtureSensitivityError("uncertainty report measurement_contract mismatch")
    weights = report.get("point_estimate_context", {}).get("reference_family_weights")
    if not isinstance(weights, dict) or not _weights_match(weights, reference_family_weights):
        raise CalibrationMixtureSensitivityError("uncertainty report reference_family_weights mismatch")
    return report


def _uncertainty_axis(
    uncertainty: dict[str, Any] | None,
    subject: str,
    sensitivity_span: float | None,
) -> dict[str, Any]:
    sampling_summary = None
    sampling_width = None
    if uncertainty is not None:
        source = uncertainty.get("subjects", {}).get(subject, {}).get("bands", {}).get("composition_adjusted_delta")
        if not isinstance(source, dict):
            raise CalibrationMixtureSensitivityError(
                f"uncertainty report missing {subject} composition_adjusted_delta band"
            )
        sampling_summary = deepcopy(source)
        band = source.get("band")
        if source.get("support_status") == "supported" and isinstance(band, dict):
            sampling_width = float(band["upper"]) - float(band["lower"] )

    if sampling_width is not None and sensitivity_span is not None:
        if sampling_width > 0:
            ratio = sensitivity_span / sampling_width
        else:
            ratio = None
        tolerance = 1e-12
        if abs(sampling_width - sensitivity_span) <= tolerance:
            larger = "equal"
        elif sampling_width > sensitivity_span:
            larger = "sampling"
        else:
            larger = "mixture_choice"
    else:
        ratio = None
        larger = "unavailable"

    return {
        "sampling_uncertainty_at_reference": sampling_summary,
        "sampling_band_width_at_reference": sampling_width,
        "reference_mixture_sensitivity_span": sensitivity_span,
        "mixture_to_sampling_width_ratio": ratio,
        "larger_reported_axis": larger,
        "axes_are_additive": False,
    }


def _ensure_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationMixtureSensitivityError("snapshot must be an object")
    if isinstance(raw.get("families"), dict):
        return deepcopy(raw)
    if isinstance(raw.get("family_suites"), dict):
        return build_calibration_snapshot(raw)
    raise CalibrationMixtureSensitivityError("snapshot must contain families or family_suites")


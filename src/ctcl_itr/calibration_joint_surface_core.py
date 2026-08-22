"""Joint outcome-resampling x reference-mixture surface for CTCL-ITR v0.2.11."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from .calibration_robustness import build_calibration_snapshot, compare_calibration_snapshots
from .calibration_uncertainty import (
    METHOD_ID as RESAMPLING_METHOD_ID,
    CalibrationUncertaintyError,
    _band,
    _resample_snapshot_spec,
    _sign_shares,
    _validate_spec as _validate_uncertainty_spec,
)
from .calibration_mixture_sensitivity_common import (
    METHOD_ID as MIXTURE_METHOD_ID,
    CalibrationMixtureSensitivityError,
    _simplex_grid,
    _validate_spec as _validate_mixture_spec,
)

METHOD_ID = "joint_empirical_binomial_simplex_surface_v1"


class CalibrationJointSurfaceError(ValueError):
    """Raised when v0.2.11 joint-surface contracts or evidence are invalid."""


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationJointSurfaceError(f"{label} is required")
    return value


def _validate_surface_spec(raw: dict[str, Any], family_count: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationJointSurfaceError("surface spec must be an object")
    spec = deepcopy(raw)
    if spec.get("schema_version") != "0.2.11":
        raise CalibrationJointSurfaceError("surface spec must use schema_version 0.2.11")
    _required_string(spec.get("surface_id"), "surface_id")
    _required_string(spec.get("generated_at"), "generated_at")
    if spec.get("method") != METHOD_ID:
        raise CalibrationJointSurfaceError(f"method must be {METHOD_ID}")

    resampling = spec.get("resampling")
    if not isinstance(resampling, dict):
        raise CalibrationJointSurfaceError("resampling must be an object")
    uncertainty_shim = {
        "schema_version": "0.2.9",
        "uncertainty_id": spec["surface_id"],
        "generated_at": spec["generated_at"],
        "method": resampling.get("method"),
        "seed": resampling.get("seed"),
        "replicates": resampling.get("replicates"),
        "interval_p": resampling.get("interval_p"),
        "minimum_supported_fraction": resampling.get("minimum_supported_fraction"),
    }
    try:
        validated_resampling = _validate_uncertainty_spec(uncertainty_shim)
    except CalibrationUncertaintyError as exc:
        raise CalibrationJointSurfaceError(str(exc)) from exc
    if validated_resampling["method"] != RESAMPLING_METHOD_ID:
        raise CalibrationJointSurfaceError(f"resampling.method must be {RESAMPLING_METHOD_ID}")

    mixture = spec.get("mixture_grid")
    if not isinstance(mixture, dict):
        raise CalibrationJointSurfaceError("mixture_grid must be an object")
    mixture_shim = {
        "schema_version": "0.2.10",
        "sensitivity_id": spec["surface_id"],
        "generated_at": spec["generated_at"],
        "method": mixture.get("method"),
        "grid_step": mixture.get("grid_step"),
        "minimum_family_weight": mixture.get("minimum_family_weight"),
        "max_grid_points": mixture.get("max_grid_points"),
    }
    try:
        validated_mixture = _validate_mixture_spec(mixture_shim, family_count)
    except CalibrationMixtureSensitivityError as exc:
        raise CalibrationJointSurfaceError(str(exc)) from exc
    if validated_mixture["method"] != MIXTURE_METHOD_ID:
        raise CalibrationJointSurfaceError(f"mixture_grid.method must be {MIXTURE_METHOD_ID}")

    return {
        **spec,
        "resampling": {
            "method": validated_resampling["method"],
            "seed": validated_resampling["seed"],
            "replicates": validated_resampling["replicates"],
            "interval_p": validated_resampling["interval_p"],
            "minimum_supported_fraction": validated_resampling["minimum_supported_fraction"],
        },
        "mixture_grid": {
            "method": validated_mixture["method"],
            "grid_step": validated_mixture["grid_step"],
            "minimum_family_weight": validated_mixture["minimum_family_weight"],
            "max_grid_points": validated_mixture["max_grid_points"],
        },
        "_mixture_validated": validated_mixture,
    }


def _band_sign_class(band_payload: dict[str, Any], tolerance: float = 1e-12) -> str:
    if band_payload.get("support_status") != "supported" or not isinstance(band_payload.get("band"), dict):
        return "unsupported"
    band = band_payload["band"]
    lower = float(band["lower"])
    upper = float(band["upper"])
    if lower > tolerance:
        return "positive_band"
    if upper < -tolerance:
        return "negative_band"
    if abs(lower) <= tolerance and abs(upper) <= tolerance:
        return "zero_band"
    return "crosses_zero"


def _summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts = {
        "positive_band": 0,
        "negative_band": 0,
        "crosses_zero": 0,
        "zero_band": 0,
        "unsupported": 0,
    }
    point_supported = 0
    resampling_supported = 0
    support_fractions: list[float] = []
    widths: list[float] = []
    reasons: dict[str, int] = {}
    classes_seen: set[str] = set()

    for cell in cells:
        if cell["point_estimate"]["support_status"] == "supported":
            point_supported += 1
        resampling = cell["resampling"]
        support_fraction = float(resampling["supported_fraction"])
        support_fractions.append(support_fraction)
        cls = resampling["band_sign_class"]
        class_counts[cls] += 1
        if cls != "unsupported":
            classes_seen.add(cls)
        if resampling["support_status"] == "supported":
            resampling_supported += 1
            band = resampling["band"]
            widths.append(float(band["upper"]) - float(band["lower"]))
        for reason, count in resampling["unsupported_reason_counts"].items():
            reasons[reason] = reasons.get(reason, 0) + int(count)

    return {
        "total_cells": len(cells),
        "point_supported_cells": point_supported,
        "resampling_supported_cells": resampling_supported,
        "resampling_supported_fraction": resampling_supported / len(cells) if cells else 0.0,
        "band_sign_class_counts": class_counts,
        "sign_sensitive_to_mixture": len(classes_seen) > 1,
        "support_fraction_range": {
            "minimum": min(support_fractions) if support_fractions else None,
            "maximum": max(support_fractions) if support_fractions else None,
        },
        "band_width_range": {
            "minimum": min(widths) if widths else None,
            "maximum": max(widths) if widths else None,
        },
        "unsupported_reason_counts": dict(sorted(reasons.items())),
    }


def analyze_joint_uncertainty_surface(
    base_snapshot_spec: dict[str, Any],
    current_snapshot_spec: dict[str, Any],
    comparison_spec: dict[str, Any],
    surface_spec: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate outcome-sampling uncertainty over a reference-mixture grid."""

    base_source = deepcopy(base_snapshot_spec)
    current_source = deepcopy(current_snapshot_spec)
    comparison = deepcopy(comparison_spec)

    if not isinstance(base_source, dict) or not isinstance(base_source.get("family_suites"), dict):
        raise CalibrationJointSurfaceError("base snapshot must contain raw family_suites evidence")
    if not isinstance(current_source, dict) or not isinstance(current_source.get("family_suites"), dict):
        raise CalibrationJointSurfaceError("current snapshot must contain raw family_suites evidence")

    families = sorted(set(base_source["family_suites"]) | set(current_source["family_suites"]))
    if len(families) < 2:
        raise CalibrationJointSurfaceError("at least two task families are required")
    spec = _validate_surface_spec(surface_spec, len(families))
    grid = _simplex_grid(families, spec["_mixture_validated"])

    base_point = build_calibration_snapshot(base_source)
    current_point = build_calibration_snapshot(current_source)
    reference_point = compare_calibration_snapshots(base_point, current_point, comparison)

    cells: dict[str, list[dict[str, Any]]] = {"autonomy": [], "governance": []}
    values: dict[str, list[list[float]]] = {
        "autonomy": [[] for _ in grid],
        "governance": [[] for _ in grid],
    }
    reason_counts: dict[str, list[dict[str, int]]] = {
        "autonomy": [{} for _ in grid],
        "governance": [{} for _ in grid],
    }

    for index, weights in enumerate(grid):
        scanned = deepcopy(comparison)
        scanned["comparison_id"] = f"{comparison['comparison_id']}:joint:{index:04d}"
        scanned["reference_family_weights"] = deepcopy(weights)
        result = compare_calibration_snapshots(base_point, current_point, scanned)
        for subject in ("autonomy", "governance"):
            payload = result["subjects"][subject]
            cells[subject].append(
                {
                    "reference_family_weights": deepcopy(weights),
                    "point_estimate": {
                        "support_status": payload["support_status"],
                        "support_reasons": deepcopy(payload.get("support_reasons", [])),
                        "composition_adjusted_delta": payload.get("composition_adjusted_delta"),
                        "reference_base_horizon": payload["reference_mix"]["base"].get("horizon_depth"),
                        "reference_current_horizon": payload["reference_mix"]["current"].get("horizon_depth"),
                    },
                    "resampling": None,
                }
            )

    resampling = spec["resampling"]
    for replicate in range(resampling["replicates"]):
        try:
            base_resampled_spec = _resample_snapshot_spec(
                base_source,
                seed=resampling["seed"],
                replicate=replicate,
                snapshot_label="base",
            )
            current_resampled_spec = _resample_snapshot_spec(
                current_source,
                seed=resampling["seed"],
                replicate=replicate,
                snapshot_label="current",
            )
            base_resampled = build_calibration_snapshot(base_resampled_spec)
            current_resampled = build_calibration_snapshot(current_resampled_spec)
        except (CalibrationUncertaintyError, ValueError) as exc:
            raise CalibrationJointSurfaceError(str(exc)) from exc

        for index, weights in enumerate(grid):
            scanned = deepcopy(comparison)
            scanned["comparison_id"] = f"{comparison['comparison_id']}:joint:{index:04d}"
            scanned["reference_family_weights"] = deepcopy(weights)
            result = compare_calibration_snapshots(base_resampled, current_resampled, scanned)
            for subject in ("autonomy", "governance"):
                payload = result["subjects"][subject]
                value = payload.get("composition_adjusted_delta")
                if value is not None:
                    numeric = float(value)
                    if not isfinite(numeric):
                        raise CalibrationJointSurfaceError("composition_adjusted_delta must be finite")
                    values[subject][index].append(numeric)
                if payload["support_status"] != "supported":
                    for reason in payload.get("support_reasons", []):
                        bucket = reason_counts[subject][index]
                        bucket[reason] = bucket.get(reason, 0) + 1

    for subject in ("autonomy", "governance"):
        for index, cell in enumerate(cells[subject]):
            band_payload = _band(
                values[subject][index],
                total_replicates=resampling["replicates"],
                interval_p=resampling["interval_p"],
                minimum_supported_fraction=resampling["minimum_supported_fraction"],
            )
            cell["resampling"] = {
                **band_payload,
                "sign_shares": _sign_shares(values[subject][index]),
                "band_sign_class": _band_sign_class(band_payload),
                "unsupported_reason_counts": dict(sorted(reason_counts[subject][index].items())),
            }

    subjects = {
        subject: {
            "cells": cells[subject],
            "surface_summary": _summary(cells[subject]),
        }
        for subject in ("autonomy", "governance")
    }

    return {
        "schema_version": "0.2.11",
        "surface_id": spec["surface_id"],
        "generated_at": spec["generated_at"],
        "method": METHOD_ID,
        "base_snapshot_id": base_point["snapshot_id"],
        "current_snapshot_id": current_point["snapshot_id"],
        "comparison_id": comparison["comparison_id"],
        "measurement_contract": deepcopy(reference_point["measurement_contract"]),
        "families": families,
        "point_reference_family_weights": deepcopy(reference_point["reference_family_weights"]),
        "resampling": deepcopy(resampling),
        "mixture_grid": {
            "method": spec["mixture_grid"]["method"],
            "grid_step": spec["mixture_grid"]["grid_step"],
            "minimum_family_weight": spec["mixture_grid"]["minimum_family_weight"],
            "max_grid_points": spec["mixture_grid"]["max_grid_points"],
            "total_points": len(grid),
        },
        "conditioning": {
            "outcome_counts_resampled": True,
            "trial_counts_fixed": True,
            "observed_family_weights_fixed": True,
            "reference_mixture_varied": True,
            "mixture_weights_resampled": False,
            "same_resampled_outcomes_reused_across_mixture_cells": True,
            "surface_cells_are_independent": False,
        },
        "subjects": subjects,
        "interpretation_boundary": "joint_sampling_x_reference_mixture_surface",
        "non_authoritative": True,
    }

"""Reference-mixture sensitivity analysis for CTCL-ITR v0.2.10."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .calibration_robustness import compare_calibration_snapshots
from .calibration_mixture_sensitivity_common import (
    CalibrationMixtureSensitivityError,
    METHOD_ID,
    _ensure_snapshot,
    _simplex_grid,
    _sensitivity_range,
    _sign_shares,
    _uncertainty_axis,
    _validate_spec,
    _validate_uncertainty_report,
)

def analyze_reference_mixture_sensitivity(
    base_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    comparison_spec: dict[str, Any],
    sensitivity_spec: dict[str, Any],
    uncertainty_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Scan supported reference mixtures without changing v0.2.8 semantics."""

    base = _ensure_snapshot(base_snapshot)
    current = _ensure_snapshot(current_snapshot)
    comparison = deepcopy(comparison_spec)
    sensitivity = deepcopy(sensitivity_spec)
    uncertainty = deepcopy(uncertainty_report) if uncertainty_report is not None else None

    if base.get("schema_version") != "0.2.8" or current.get("schema_version") != "0.2.8":
        raise CalibrationMixtureSensitivityError("snapshots must use schema_version 0.2.8")
    families = sorted(set(base.get("families", {})) | set(current.get("families", {})))
    if len(families) < 2:
        raise CalibrationMixtureSensitivityError("at least two task families are required")
    spec = _validate_spec(sensitivity, len(families))
    grid = _simplex_grid(families, spec)

    # This validates the original comparison identity/contract before scanning.
    reference_point = compare_calibration_snapshots(base, current, comparison)
    if uncertainty is not None:
        uncertainty = _validate_uncertainty_report(
            uncertainty,
            base_snapshot_id=base["snapshot_id"],
            current_snapshot_id=current["snapshot_id"],
            comparison_id=comparison["comparison_id"],
            measurement_contract=reference_point["measurement_contract"],
            reference_family_weights=reference_point["reference_family_weights"],
        )

    per_subject_scan = {subject: [] for subject in ("autonomy", "governance")}
    for index, weights in enumerate(grid):
        scanned_spec = deepcopy(comparison)
        scanned_spec["comparison_id"] = f"{comparison['comparison_id']}:mixture:{index:04d}"
        scanned_spec["reference_family_weights"] = deepcopy(weights)
        result = compare_calibration_snapshots(base, current, scanned_spec)
        for subject in ("autonomy", "governance"):
            payload = result["subjects"][subject]
            per_subject_scan[subject].append(
                {
                    "reference_family_weights": deepcopy(weights),
                    "support_status": payload["support_status"],
                    "support_reasons": deepcopy(payload.get("support_reasons", [])),
                    "composition_adjusted_delta": payload.get("composition_adjusted_delta"),
                    "reference_base_horizon": payload["reference_mix"]["base"].get("horizon_depth"),
                    "reference_current_horizon": payload["reference_mix"]["current"].get("horizon_depth"),
                }
            )

    subjects: dict[str, Any] = {}
    for subject in ("autonomy", "governance"):
        scan = per_subject_scan[subject]
        supported = [entry for entry in scan if entry["support_status"] == "supported"]
        values = [float(entry["composition_adjusted_delta"]) for entry in supported]
        reasons: dict[str, int] = {}
        for entry in scan:
            if entry["support_status"] != "supported":
                for reason in entry["support_reasons"]:
                    reasons[reason] = reasons.get(reason, 0) + 1
        range_payload = _sensitivity_range(scan)
        reference_delta = reference_point["subjects"][subject].get("composition_adjusted_delta")
        if range_payload and reference_delta is not None and range_payload["span"] > 0:
            position = (reference_delta - range_payload["minimum"]) / range_payload["span"]
        else:
            position = None
        subjects[subject] = {
            "reference_point_estimate": reference_delta,
            "mixture_scan": scan,
            "supported_grid_points": len(supported),
            "total_grid_points": len(scan),
            "supported_grid_fraction": len(supported) / len(scan),
            "sensitivity_range": range_payload,
            "reference_position_in_supported_range": position,
            "sign_shares": _sign_shares(values),
            "unsupported_reason_counts": dict(sorted(reasons.items())),
            "uncertainty_axes": _uncertainty_axis(
                uncertainty,
                subject,
                range_payload["span"] if range_payload is not None else None,
            ),
        }

    return {
        "schema_version": "0.2.10",
        "sensitivity_id": spec["sensitivity_id"],
        "generated_at": spec["generated_at"],
        "method": METHOD_ID,
        "base_snapshot_id": base["snapshot_id"],
        "current_snapshot_id": current["snapshot_id"],
        "comparison_id": comparison["comparison_id"],
        "measurement_contract": deepcopy(reference_point["measurement_contract"]),
        "families": families,
        "reference_family_weights": deepcopy(reference_point["reference_family_weights"]),
        "grid": {
            "grid_step": spec["grid_step"],
            "minimum_family_weight": spec["minimum_family_weight"],
            "max_grid_points": spec["max_grid_points"],
            "total_points": len(grid),
        },
        "conditioning": {
            "task_family_curves_fixed": True,
            "outcome_counts_fixed": True,
            "observed_family_weights_fixed": True,
            "reference_mixture_varied": True,
        },
        "subjects": subjects,
        "uncertainty_decomposition": "separate_axes_not_additive",
        "interpretation_boundary": "reference_mixture_sensitivity_only",
        "non_authoritative": True,
    }



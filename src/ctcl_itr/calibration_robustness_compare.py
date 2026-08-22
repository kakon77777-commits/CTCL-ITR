"""Snapshot comparison and drift decomposition for CTCL-ITR v0.2.8."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .calibration_robustness_common import (
    CalibrationRobustnessError,
    _parse_time,
    _required_string,
)
from .calibration_robustness_mixture import (
    _context_diagnostics,
    _mixture_horizon,
    _normalize_weights,
    _observed_weights,
    _parse_datetime_value,
    _range_or_none,
    _sign,
    _subject_profile,
)


def compare_calibration_snapshots(
    base_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    comparison_spec: dict[str, Any],
) -> dict[str, Any]:
    """Compare two calibrated task-family snapshots without causal attribution."""

    base = deepcopy(base_snapshot)
    current = deepcopy(current_snapshot)
    spec = deepcopy(comparison_spec)
    if base.get("schema_version") != "0.2.8" or current.get("schema_version") != "0.2.8":
        raise CalibrationRobustnessError("snapshots must use schema_version 0.2.8")
    if spec.get("schema_version") != "0.2.8":
        raise CalibrationRobustnessError("comparison spec must use schema_version 0.2.8")
    comparison_id = _required_string(spec.get("comparison_id"), "comparison_id")
    generated_at = _parse_time(spec.get("generated_at"), "generated_at")
    if base.get("measurement_contract") != current.get("measurement_contract"):
        raise CalibrationRobustnessError("snapshot measurement contracts must match")
    if base.get("benchmark_id") != current.get("benchmark_id"):
        raise CalibrationRobustnessError("benchmark_id must match for robustness comparison")

    base_families = sorted(base["families"])
    current_families = sorted(current["families"])
    family_union = sorted(set(base_families) | set(current_families))
    context = _context_diagnostics(base, current)

    reference_weights = _normalize_weights(
        spec.get("reference_family_weights"), family_union, "reference_family_weights"
    )

    base_time = _parse_datetime_value(base["observed_at"], "base observed_at")
    current_time = _parse_datetime_value(current["observed_at"], "current observed_at")
    elapsed_seconds = (current_time - base_time).total_seconds()
    if elapsed_seconds < 0:
        raise CalibrationRobustnessError("current snapshot must not precede base snapshot")

    subjects: dict[str, Any] = {}
    for subject in ("autonomy", "governance"):
        family_deltas: dict[str, Any] = {}
        supported_deltas: list[float] = []
        base_family_horizons: list[float] = []
        current_family_horizons: list[float] = []
        for family_id in family_union:
            base_profile = _subject_profile(base, family_id, subject) if family_id in base["families"] else None
            current_profile = (
                _subject_profile(current, family_id, subject) if family_id in current["families"] else None
            )
            base_horizon = (
                float(base_profile["horizon_depth"])
                if base_profile and base_profile["support_status"] == "supported"
                else None
            )
            current_horizon = (
                float(current_profile["horizon_depth"])
                if current_profile and current_profile["support_status"] == "supported"
                else None
            )
            delta = current_horizon - base_horizon if base_horizon is not None and current_horizon is not None else None
            if base_horizon is not None:
                base_family_horizons.append(base_horizon)
            if current_horizon is not None:
                current_family_horizons.append(current_horizon)
            if delta is not None:
                supported_deltas.append(delta)
            family_deltas[family_id] = {
                "base_horizon_depth": base_horizon,
                "current_horizon_depth": current_horizon,
                "delta": delta,
                "base_support_status": base_profile["support_status"] if base_profile else "missing_family",
                "current_support_status": current_profile["support_status"] if current_profile else "missing_family",
            }

        support_reasons: list[str] = []
        if context["family_set_changed"]:
            base_observed_weights = None
            current_observed_weights = None
            observed_base = observed_current = reference_base = reference_current = {
                "support_status": "unsupported",
                "support_reasons": ["family_set_changed"],
                "horizon_depth": None,
            }
            support_reasons.append("family_set_changed")
            composition_tv = None
        else:
            base_observed_weights = _observed_weights(base, subject, family_union)
            current_observed_weights = _observed_weights(current, subject, family_union)
            composition_tv = round(
                0.5 * sum(
                    abs(current_observed_weights[f] - base_observed_weights[f]) for f in family_union
                ),
                15,
            )
            observed_base = _mixture_horizon(base, subject, base_observed_weights)
            observed_current = _mixture_horizon(current, subject, current_observed_weights)
            reference_base = _mixture_horizon(base, subject, reference_weights)
            reference_current = _mixture_horizon(current, subject, reference_weights)
            for prefix, mix in (
                ("base_observed", observed_base),
                ("current_observed", observed_current),
                ("base_reference", reference_base),
                ("current_reference", reference_current),
            ):
                if mix["support_status"] != "supported":
                    support_reasons.extend(mix["support_reasons"])
                    support_reasons.extend(f"{prefix}:{reason}" for reason in mix["support_reasons"])

        observed_delta = (
            observed_current["horizon_depth"] - observed_base["horizon_depth"]
            if observed_base.get("support_status") == "supported"
            and observed_current.get("support_status") == "supported"
            else None
        )
        adjusted_delta = (
            reference_current["horizon_depth"] - reference_base["horizon_depth"]
            if reference_base.get("support_status") == "supported"
            and reference_current.get("support_status") == "supported"
            else None
        )
        residual = observed_delta - adjusted_delta if observed_delta is not None and adjusted_delta is not None else None

        if adjusted_delta is None or not supported_deltas:
            direction_agreement = None
        else:
            expected_sign = _sign(adjusted_delta)
            direction_agreement = sum(_sign(delta) == expected_sign for delta in supported_deltas) / len(
                supported_deltas
            )

        per_day = (
            adjusted_delta / (elapsed_seconds / 86400.0)
            if adjusted_delta is not None and elapsed_seconds > 0
            else None
        )
        subjects[subject] = {
            "support_status": "supported" if not support_reasons else "unsupported",
            "support_reasons": sorted(set(support_reasons)),
            "observed_family_weights": {"base": base_observed_weights, "current": current_observed_weights},
            "reference_family_weights": deepcopy(reference_weights),
            "composition_total_variation": composition_tv,
            "observed_mix": {"base": observed_base, "current": observed_current},
            "reference_mix": {"base": reference_base, "current": reference_current},
            "observed_mix_delta": observed_delta,
            "composition_adjusted_delta": adjusted_delta,
            "composition_residual": residual,
            "composition_adjusted_delta_per_day": per_day,
            "family_horizon_deltas": family_deltas,
            "supported_family_fraction": len(supported_deltas) / len(family_union) if family_union else 0.0,
            "family_direction_agreement": direction_agreement,
            "base_family_horizon_range": _range_or_none(base_family_horizons),
            "current_family_horizon_range": _range_or_none(current_family_horizons),
            "max_abs_family_delta": max((abs(delta) for delta in supported_deltas), default=None),
        }

    return {
        "schema_version": "0.2.8",
        "comparison_id": comparison_id,
        "generated_at": generated_at,
        "base_snapshot_id": base["snapshot_id"],
        "current_snapshot_id": current["snapshot_id"],
        "measurement_contract": deepcopy(base["measurement_contract"]),
        "reference_family_weights": reference_weights,
        "elapsed_seconds": elapsed_seconds,
        "context_diagnostics": context,
        "subjects": subjects,
        "attribution_boundary": "composition_standardization_only",
        "non_authoritative": True,
    }

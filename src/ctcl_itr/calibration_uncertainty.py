"""Deterministic resampling uncertainty for CTCL-ITR v0.2.9."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from math import ceil, floor, isfinite
from typing import Any

from .calibration_robustness import build_calibration_snapshot, compare_calibration_snapshots

METHOD_ID = "stratified_empirical_binomial_sha256_v1"


class CalibrationUncertaintyError(ValueError):
    """Raised when v0.2.9 uncertainty contracts or evidence are invalid."""


def _number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise CalibrationUncertaintyError(f"{label} must be numeric") from exc
    if not isfinite(result):
        raise CalibrationUncertaintyError(f"{label} must be finite")
    return result


def _probability(value: Any, label: str, *, allow_zero: bool = False) -> float:
    result = _number(value, label)
    if allow_zero:
        ok = 0.0 <= result <= 1.0
    else:
        ok = 0.0 < result <= 1.0
    if not ok:
        interval = "[0, 1]" if allow_zero else "(0, 1]"
        raise CalibrationUncertaintyError(f"{label} must be in {interval}")
    return result


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise CalibrationUncertaintyError(f"{label} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CalibrationUncertaintyError(f"{label} must be a positive integer") from exc
    if parsed != value or parsed <= 0:
        raise CalibrationUncertaintyError(f"{label} must be a positive integer")
    return parsed


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationUncertaintyError(f"{label} is required")
    return value


def _validate_spec(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationUncertaintyError("uncertainty spec must be an object")
    spec = deepcopy(raw)
    if spec.get("schema_version") != "0.2.9":
        raise CalibrationUncertaintyError("uncertainty spec must use schema_version 0.2.9")
    _required_string(spec.get("uncertainty_id"), "uncertainty_id")
    _required_string(spec.get("generated_at"), "generated_at")
    if spec.get("method") != METHOD_ID:
        raise CalibrationUncertaintyError(f"method must be {METHOD_ID}")
    _required_string(spec.get("seed"), "seed")
    spec["replicates"] = _positive_int(spec.get("replicates"), "replicates")
    spec["interval_p"] = _probability(spec.get("interval_p"), "interval_p")
    spec["minimum_supported_fraction"] = _probability(
        spec.get("minimum_supported_fraction"), "minimum_supported_fraction"
    )
    return spec


def _uniform01(seed: str, *labels: Any) -> float:
    material = "\x1f".join([seed, *(str(label) for label in labels)]).encode("utf-8")
    value = int.from_bytes(sha256(material).digest()[:8], "big")
    return value / 2**64


def _resample_successes(
    *, seed: str, p_hat: float, trials: int, labels: tuple[Any, ...]
) -> int:
    if p_hat <= 0.0:
        return 0
    if p_hat >= 1.0:
        return trials
    return sum(_uniform01(seed, *labels, attempt) < p_hat for attempt in range(trials))


def _resample_snapshot_spec(
    snapshot_spec: dict[str, Any], *, seed: str, replicate: int, snapshot_label: str
) -> dict[str, Any]:
    out = deepcopy(snapshot_spec)
    if out.get("schema_version") != "0.2.8":
        raise CalibrationUncertaintyError("snapshot specs must use schema_version 0.2.8")
    families = out.get("family_suites")
    if not isinstance(families, dict) or not families:
        raise CalibrationUncertaintyError("snapshot spec family_suites must be non-empty")
    for family_id in sorted(families):
        suite = families[family_id]
        for subject in ("autonomy", "governance"):
            points = suite.get("subjects", {}).get(subject)
            if not isinstance(points, list) or not points:
                raise CalibrationUncertaintyError(f"missing {family_id}.{subject} evidence")
            for point_index, point in enumerate(points):
                trials = _positive_int(point.get("trials"), "trials")
                successes = point.get("successes")
                if isinstance(successes, bool) or not isinstance(successes, int) or not 0 <= successes <= trials:
                    raise CalibrationUncertaintyError("successes must satisfy 0 <= successes <= trials")
                p_hat = successes / trials
                point["successes"] = _resample_successes(
                    seed=seed,
                    p_hat=p_hat,
                    trials=trials,
                    labels=(
                        snapshot_label,
                        replicate,
                        family_id,
                        subject,
                        point.get("depth"),
                        point_index,
                    ),
                )
    return out


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise CalibrationUncertaintyError("cannot compute quantile of empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = q * (len(sorted_values) - 1)
    lo = floor(position)
    hi = ceil(position)
    if lo == hi:
        return sorted_values[lo]
    fraction = position - lo
    return sorted_values[lo] + fraction * (sorted_values[hi] - sorted_values[lo])


def _band(
    values: list[float], *, total_replicates: int, interval_p: float, minimum_supported_fraction: float
) -> dict[str, Any]:
    supported_count = len(values)
    supported_fraction = supported_count / total_replicates if total_replicates else 0.0
    base = {
        "supported_replicates": supported_count,
        "total_replicates": total_replicates,
        "supported_fraction": supported_fraction,
    }
    if supported_fraction < minimum_supported_fraction or not values:
        return {
            **base,
            "support_status": "insufficient_resampling_support",
            "band": None,
            "mean": None,
        }
    ordered = sorted(float(v) for v in values)
    tail = (1.0 - interval_p) / 2.0
    return {
        **base,
        "support_status": "supported",
        "band": {
            "lower": _quantile(ordered, tail),
            "median": _quantile(ordered, 0.5),
            "upper": _quantile(ordered, 1.0 - tail),
        },
        "mean": sum(ordered) / len(ordered),
    }


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


def _append_if_number(bucket: list[float], value: Any) -> None:
    if value is not None:
        bucket.append(float(value))


def bootstrap_calibration_uncertainty(
    base_snapshot_spec: dict[str, Any],
    current_snapshot_spec: dict[str, Any],
    comparison_spec: dict[str, Any],
    uncertainty_spec: dict[str, Any],
) -> dict[str, Any]:
    """Resample observed success counts and summarize Horizon/drift stability.

    Task-family weights remain fixed to the original v0.2.8 comparison semantics.
    Reported percentile bands are descriptive resampling bands, not posterior
    probabilities or guaranteed-coverage confidence intervals.
    """

    base_source = deepcopy(base_snapshot_spec)
    current_source = deepcopy(current_snapshot_spec)
    comparison_source = deepcopy(comparison_spec)
    spec = _validate_spec(uncertainty_spec)

    base_point = build_calibration_snapshot(base_source)
    current_point = build_calibration_snapshot(current_source)
    point = compare_calibration_snapshots(base_point, current_point, comparison_source)

    storage: dict[str, dict[str, list[float]]] = {}
    reason_counts: dict[str, dict[str, int]] = {}
    for subject in ("autonomy", "governance"):
        storage[subject] = {
            "observed_base_horizon": [],
            "observed_current_horizon": [],
            "observed_mix_delta": [],
            "reference_base_horizon": [],
            "reference_current_horizon": [],
            "composition_adjusted_delta": [],
            "composition_residual": [],
        }
        for family_id in sorted(base_source["family_suites"]):
            storage[subject][f"family_delta:{family_id}"] = []
        reason_counts[subject] = {}

    for replicate in range(spec["replicates"]):
        base_resampled = _resample_snapshot_spec(
            base_source, seed=spec["seed"], replicate=replicate, snapshot_label="base"
        )
        current_resampled = _resample_snapshot_spec(
            current_source, seed=spec["seed"], replicate=replicate, snapshot_label="current"
        )
        base_snapshot = build_calibration_snapshot(base_resampled)
        current_snapshot = build_calibration_snapshot(current_resampled)
        result = compare_calibration_snapshots(base_snapshot, current_snapshot, comparison_source)

        for subject in ("autonomy", "governance"):
            payload = result["subjects"][subject]
            if payload["support_status"] != "supported":
                for reason in payload.get("support_reasons", []):
                    reason_counts[subject][reason] = reason_counts[subject].get(reason, 0) + 1
            _append_if_number(storage[subject]["observed_base_horizon"], payload["observed_mix"]["base"].get("horizon_depth"))
            _append_if_number(storage[subject]["observed_current_horizon"], payload["observed_mix"]["current"].get("horizon_depth"))
            _append_if_number(storage[subject]["observed_mix_delta"], payload.get("observed_mix_delta"))
            _append_if_number(storage[subject]["reference_base_horizon"], payload["reference_mix"]["base"].get("horizon_depth"))
            _append_if_number(storage[subject]["reference_current_horizon"], payload["reference_mix"]["current"].get("horizon_depth"))
            _append_if_number(storage[subject]["composition_adjusted_delta"], payload.get("composition_adjusted_delta"))
            _append_if_number(storage[subject]["composition_residual"], payload.get("composition_residual"))
            for family_id, family in payload["family_horizon_deltas"].items():
                _append_if_number(storage[subject][f"family_delta:{family_id}"], family.get("delta"))

    subjects: dict[str, Any] = {}
    for subject in ("autonomy", "governance"):
        point_subject = point["subjects"][subject]
        bands = {
            key: _band(
                values,
                total_replicates=spec["replicates"],
                interval_p=spec["interval_p"],
                minimum_supported_fraction=spec["minimum_supported_fraction"],
            )
            for key, values in storage[subject].items()
            if not key.startswith("family_delta:")
        }
        family_bands = {
            key.split(":", 1)[1]: _band(
                values,
                total_replicates=spec["replicates"],
                interval_p=spec["interval_p"],
                minimum_supported_fraction=spec["minimum_supported_fraction"],
            )
            for key, values in storage[subject].items()
            if key.startswith("family_delta:")
        }
        subjects[subject] = {
            "point_estimate": {
                "observed_mix_delta": point_subject.get("observed_mix_delta"),
                "composition_adjusted_delta": point_subject.get("composition_adjusted_delta"),
                "composition_residual": point_subject.get("composition_residual"),
                "composition_total_variation": point_subject.get("composition_total_variation"),
            },
            "bands": bands,
            "family_delta_bands": family_bands,
            "sign_shares": {
                "observed_mix_delta": _sign_shares(storage[subject]["observed_mix_delta"]),
                "composition_adjusted_delta": _sign_shares(storage[subject]["composition_adjusted_delta"]),
            },
            "unsupported_reason_counts": dict(sorted(reason_counts[subject].items())),
        }

    return {
        "schema_version": "0.2.9",
        "uncertainty_id": spec["uncertainty_id"],
        "generated_at": spec["generated_at"],
        "method": METHOD_ID,
        "seed": spec["seed"],
        "replicates": spec["replicates"],
        "interval_p": spec["interval_p"],
        "minimum_supported_fraction": spec["minimum_supported_fraction"],
        "base_snapshot_id": base_point["snapshot_id"],
        "current_snapshot_id": current_point["snapshot_id"],
        "comparison_id": point["comparison_id"],
        "measurement_contract": deepcopy(point["measurement_contract"]),
        "conditioning": {
            "composition_resampled": False,
            "observed_family_weights_fixed": True,
            "reference_family_weights_fixed": True,
            "trial_counts_fixed": True,
            "success_counts_resampled": True,
        },
        "point_estimate_context": {
            "reference_family_weights": deepcopy(point["reference_family_weights"]),
            "context_diagnostics": deepcopy(point["context_diagnostics"]),
            "attribution_boundary": point["attribution_boundary"],
        },
        "subjects": subjects,
        "interpretation_boundary": "conditional_outcome_sampling_uncertainty_only",
        "non_authoritative": True,
    }


def _main(argv=None) -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Bootstrap CTCL-ITR Horizon/drift uncertainty from v0.2.8 snapshot evidence.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--uncertainty", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    def load(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    report = bootstrap_calibration_uncertainty(
        load(args.base), load(args.current), load(args.comparison), load(args.uncertainty)
    )
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    _main()

"""Common validation helpers for CTCL-ITR v0.2.13 geometry drift."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

METHOD_ID = "surface_geometry_drift_v1"
GEOMETRY_METHOD = "simplex_supported_surface_geometry_v1"
BOUNDARY_MATCH_METHOD = "greedy_l1_nearest_v1"
SIGN_CLASSES = ("positive_band", "negative_band", "crosses_zero", "zero_band")


class CalibrationGeometryDriftError(ValueError):
    """Raised when geometry-drift inputs are incompatible or invalid."""


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationGeometryDriftError(f"{label} is required")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationGeometryDriftError(f"{label} must be a finite number")
    result = float(value)
    if not isfinite(result):
        raise CalibrationGeometryDriftError(f"{label} must be a finite number")
    return result


def _validate_spec(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationGeometryDriftError("drift spec must be an object")
    spec = deepcopy(raw)
    if spec.get("schema_version") != "0.2.13":
        raise CalibrationGeometryDriftError("drift spec must use schema_version 0.2.13")
    _required_string(spec.get("drift_id"), "drift_id")
    _required_string(spec.get("generated_at"), "generated_at")
    if spec.get("method") != METHOD_ID:
        raise CalibrationGeometryDriftError(f"method must be {METHOD_ID}")
    if spec.get("boundary_match_method", BOUNDARY_MATCH_METHOD) != BOUNDARY_MATCH_METHOD:
        raise CalibrationGeometryDriftError(f"boundary_match_method must be {BOUNDARY_MATCH_METHOD}")
    spec["boundary_match_method"] = BOUNDARY_MATCH_METHOD
    return spec


def _validate_geometry(raw: dict[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationGeometryDriftError(f"{label} geometry must be an object")
    geometry = deepcopy(raw)
    if geometry.get("schema_version") != "0.2.12":
        raise CalibrationGeometryDriftError(f"{label} geometry must use schema_version 0.2.12")
    if geometry.get("method") != GEOMETRY_METHOD:
        raise CalibrationGeometryDriftError(f"{label} geometry method must be {GEOMETRY_METHOD}")
    _required_string(geometry.get("geometry_id"), f"{label}.geometry_id")
    families = geometry.get("families")
    if not isinstance(families, list) or len(families) < 2 or len(set(families)) != len(families):
        raise CalibrationGeometryDriftError(f"{label}.families must contain at least two unique names")
    if any(not isinstance(x, str) or not x for x in families):
        raise CalibrationGeometryDriftError(f"{label}.families must contain non-empty strings")
    if not isinstance(geometry.get("measurement_contract"), dict):
        raise CalibrationGeometryDriftError(f"{label}.measurement_contract must be an object")
    if not isinstance(geometry.get("grid"), dict):
        raise CalibrationGeometryDriftError(f"{label}.grid must be an object")
    _finite(geometry["grid"].get("grid_step"), f"{label}.grid.grid_step")
    if not isinstance(geometry.get("boundary_interpolation"), dict):
        raise CalibrationGeometryDriftError(f"{label}.boundary_interpolation must be an object")
    subjects = geometry.get("subjects")
    if not isinstance(subjects, dict) or set(subjects) != {"autonomy", "governance"}:
        raise CalibrationGeometryDriftError(f"{label}.subjects must contain autonomy and governance")
    for subject in ("autonomy", "governance"):
        payload = subjects[subject]
        if not isinstance(payload, dict):
            raise CalibrationGeometryDriftError(f"{label}.{subject} must be an object")
        graph = payload.get("supported_graph")
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise CalibrationGeometryDriftError(f"{label}.{subject}.supported_graph.nodes must be an array")
        seen: set[str] = set()
        for node in graph["nodes"]:
            if not isinstance(node, dict):
                raise CalibrationGeometryDriftError(f"{label}.{subject}.supported_graph node must be an object")
            key = _required_string(node.get("cell_key"), f"{label}.{subject}.node.cell_key")
            if key in seen:
                raise CalibrationGeometryDriftError(f"duplicate supported node {key}")
            seen.add(key)
            weights = node.get("reference_family_weights")
            if not isinstance(weights, dict) or set(weights) != set(families):
                raise CalibrationGeometryDriftError(f"{label}.{subject}.{key} family weights must match families")
            for family in families:
                _finite(weights[family], f"{label}.{subject}.{key}.{family}")
            if node.get("band_sign_class") not in SIGN_CLASSES:
                raise CalibrationGeometryDriftError(f"{label}.{subject}.{key} band_sign_class is invalid")
        if not isinstance(graph.get("connected_components"), list):
            raise CalibrationGeometryDriftError(f"{label}.{subject}.connected_components must be an array")
        if not isinstance(payload.get("boundaries"), dict):
            raise CalibrationGeometryDriftError(f"{label}.{subject}.boundaries must be an object")
        if not isinstance(payload.get("local_gradients"), list):
            raise CalibrationGeometryDriftError(f"{label}.{subject}.local_gradients must be an array")
    return geometry


def _ensure_compatible(base: dict[str, Any], current: dict[str, Any]) -> None:
    if base["measurement_contract"] != current["measurement_contract"]:
        raise CalibrationGeometryDriftError("measurement_contract mismatch")
    if base["families"] != current["families"]:
        raise CalibrationGeometryDriftError("families mismatch")
    if base["grid"] != current["grid"]:
        raise CalibrationGeometryDriftError("grid mismatch")
    if base["boundary_interpolation"] != current["boundary_interpolation"]:
        raise CalibrationGeometryDriftError("boundary_interpolation mismatch")


def _node_map(subject_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["cell_key"]: node for node in subject_payload["supported_graph"]["nodes"]}

"""Validation and time helpers for CTCL-ITR v0.2.14 geometry trajectories."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from .calibration_geometry_drift_common import (
    CalibrationGeometryDriftError,
    _ensure_compatible,
    _validate_geometry,
)

METHOD_ID = "surface_geometry_trajectory_v1"
TIME_UNIT = "day"
SECONDS_PER_DAY = 86400.0


class CalibrationGeometryTrajectoryError(ValueError):
    """Raised when a geometry trajectory contract is invalid."""


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationGeometryTrajectoryError(f"{label} is required")
    return value


def _parse_time(value: Any, label: str) -> datetime:
    text = _required_string(value, label)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalibrationGeometryTrajectoryError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise CalibrationGeometryTrajectoryError(f"{label} must include timezone")
    return dt


def _validate_spec(raw: dict[str, Any]) -> tuple[dict[str, Any], list[datetime]]:
    if not isinstance(raw, dict):
        raise CalibrationGeometryTrajectoryError("trajectory spec must be an object")
    spec = deepcopy(raw)
    if spec.get("schema_version") != "0.2.14":
        raise CalibrationGeometryTrajectoryError("trajectory spec must use schema_version 0.2.14")
    _required_string(spec.get("trajectory_id"), "trajectory_id")
    _required_string(spec.get("generated_at"), "generated_at")
    if spec.get("method") != METHOD_ID:
        raise CalibrationGeometryTrajectoryError(f"method must be {METHOD_ID}")
    if spec.get("time_unit", TIME_UNIT) != TIME_UNIT:
        raise CalibrationGeometryTrajectoryError(f"time_unit must be {TIME_UNIT}")
    spec["time_unit"] = TIME_UNIT
    observations = spec.get("observations")
    if not isinstance(observations, list) or len(observations) < 3:
        raise CalibrationGeometryTrajectoryError("trajectory requires at least 3 observations")
    seen_obs: set[str] = set()
    seen_geometry: set[str] = set()
    times: list[datetime] = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise CalibrationGeometryTrajectoryError("each observation must be an object")
        oid = _required_string(observation.get("observation_id"), f"observations[{index}].observation_id")
        gid = _required_string(observation.get("geometry_id"), f"observations[{index}].geometry_id")
        if oid in seen_obs:
            raise CalibrationGeometryTrajectoryError(f"duplicate observation_id {oid}")
        if gid in seen_geometry:
            raise CalibrationGeometryTrajectoryError(f"duplicate geometry_id {gid}")
        seen_obs.add(oid); seen_geometry.add(gid)
        times.append(_parse_time(observation.get("observed_at"), f"observations[{index}].observed_at"))
    if any(times[i + 1] <= times[i] for i in range(len(times) - 1)):
        raise CalibrationGeometryTrajectoryError("observation timestamps must be strictly increasing")
    return spec, times


def _validate_geometries(raw: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) != len(spec["observations"]):
        raise CalibrationGeometryTrajectoryError("geometry list length must match observations")
    geometries = []
    for index, item in enumerate(raw):
        try:
            geometry = _validate_geometry(item, f"geometry[{index}]")
        except CalibrationGeometryDriftError as exc:
            raise CalibrationGeometryTrajectoryError(str(exc)) from exc
        expected = spec["observations"][index]["geometry_id"]
        if geometry["geometry_id"] != expected:
            raise CalibrationGeometryTrajectoryError(
                f"geometry[{index}].geometry_id must match observation geometry_id {expected}"
            )
        geometries.append(geometry)
    for geometry in geometries[1:]:
        try:
            _ensure_compatible(geometries[0], geometry)
        except CalibrationGeometryDriftError as exc:
            raise CalibrationGeometryTrajectoryError(f"incompatible geometry contracts: {exc}") from exc
    return geometries


def _elapsed_days(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / SECONDS_PER_DAY


def _direction(value: float, tolerance: float = 1e-12) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def _direction_reversal_count(values: list[float], tolerance: float = 1e-12) -> int:
    signs = [_direction(v, tolerance) for v in values]
    signs = [x for x in signs if x]
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)

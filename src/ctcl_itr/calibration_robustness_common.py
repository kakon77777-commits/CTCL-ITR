"""Shared validation helpers for CTCL-ITR calibration robustness."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
from typing import Any

class CalibrationRobustnessError(ValueError):
    """Raised when robustness snapshot/comparison contracts are invalid."""

def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationRobustnessError(f"{label} is required")
    return value

def _parse_time(value: Any, label: str) -> str:
    text = _required_string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalibrationRobustnessError(f"{label} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise CalibrationRobustnessError(f"{label} must include a timezone offset")
    return text

def _validate_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise CalibrationRobustnessError("measurement_contract is required")
    required = {"unit", "reliability_p", "scope_id", "assessment_method"}
    if set(contract) != required:
        raise CalibrationRobustnessError("measurement_contract fields are invalid")
    if contract.get("unit") != "interaction_depth":
        raise CalibrationRobustnessError("measurement_contract unit must be interaction_depth")
    reliability = contract.get("reliability_p")
    try:
        probability = float(reliability)
    except (TypeError, ValueError) as exc:
        raise CalibrationRobustnessError("measurement_contract reliability_p must be numeric") from exc
    if not isfinite(probability) or not (0.0 < probability <= 1.0):
        raise CalibrationRobustnessError("measurement_contract reliability_p must be in (0, 1]")
    _required_string(contract.get("scope_id"), "measurement_contract scope_id")
    _required_string(contract.get("assessment_method"), "measurement_contract assessment_method")
    return deepcopy(contract)


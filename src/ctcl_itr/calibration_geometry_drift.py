"""Geometry drift and boundary motion for CTCL-ITR v0.2.13."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .calibration_geometry_drift_common import (
    BOUNDARY_MATCH_METHOD,
    METHOD_ID,
    CalibrationGeometryDriftError,
    _ensure_compatible,
    _validate_geometry,
    _validate_spec,
)
from .calibration_geometry_drift_motion import _subject_motion

def compare_surface_geometry(
    base_geometry: dict[str, Any],
    current_geometry: dict[str, Any],
    drift_spec: dict[str, Any],
) -> dict[str, Any]:
    """Compare two compatible v0.2.12 geometry reports without altering them."""

    spec = _validate_spec(drift_spec)
    base = _validate_geometry(base_geometry, "base")
    current = _validate_geometry(current_geometry, "current")
    _ensure_compatible(base, current)
    families = list(base["families"])

    subjects = {
        subject: _subject_motion(base["subjects"][subject], current["subjects"][subject], families)
        for subject in ("autonomy", "governance")
    }

    return {
        "schema_version": "0.2.13",
        "drift_id": spec["drift_id"],
        "generated_at": spec["generated_at"],
        "method": METHOD_ID,
        "boundary_match_method": BOUNDARY_MATCH_METHOD,
        "base_geometry": {
            "geometry_id": base["geometry_id"],
            "source_surface": deepcopy(base.get("source_surface")),
        },
        "current_geometry": {
            "geometry_id": current["geometry_id"],
            "source_surface": deepcopy(current.get("source_surface")),
        },
        "measurement_contract": deepcopy(base["measurement_contract"]),
        "families": families,
        "grid": deepcopy(base["grid"]),
        "boundary_interpolation": deepcopy(base["boundary_interpolation"]),
        "conditioning": {
            "compatible_geometry_contract_required": True,
            "support_gain_loss_separate_from_sign_migration": True,
            "unsupported_region_interpolated": False,
            "boundary_matching_is_descriptive_not_identity": True,
            "gradient_drift_matched_supported_edges_only": True,
        },
        "subjects": subjects,
        "interpretation_boundary": [
            "Geometry Drift != Causal Mechanism",
            "Boundary Motion != Capability Velocity",
            "Support Expansion != Universal Capability Expansion",
            "Component Split/Merge != Physical Phase Transition",
            "Nearest Boundary Match != Persistent Boundary Identity",
            "Gradient Drift != Global Derivative Drift",
            "Geometry Drift Report != Authority",
        ],
        "non_authoritative": True,
    }


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare CTCL-ITR v0.2.12 surface geometry snapshots.")
    parser.add_argument("--base-geometry", required=True)
    parser.add_argument("--current-geometry", required=True)
    parser.add_argument("--drift", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    report = compare_surface_geometry(_load(args.base_geometry), _load(args.current_geometry), _load(args.drift))
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

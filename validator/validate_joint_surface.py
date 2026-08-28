#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        ("schemas/calibration-joint-surface-spec.schema.json", "examples/calibration_joint_surface_spec.json"),
        ("schemas/calibration-joint-surface-report.schema.json", "examples/calibration_joint_surface_report.json"),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)

    stored = load("examples/calibration_joint_surface_report.json")
    regenerated = analyze_joint_uncertainty_surface(
        load("examples/calibration_snapshot_base.json"),
        load("examples/calibration_snapshot_current.json"),
        load("examples/calibration_comparison_spec.json"),
        load("examples/calibration_joint_surface_spec.json"),
    )
    assert regenerated == stored
    assert stored["conditioning"]["same_resampled_outcomes_reused_across_mixture_cells"] is True
    assert stored["conditioning"]["surface_cells_are_independent"] is False
    assert stored["non_authoritative"] is True

    autonomy = stored["subjects"]["autonomy"]["surface_summary"]
    governance = stored["subjects"]["governance"]["surface_summary"]
    assert autonomy["resampling_supported_cells"] == 6
    assert governance["resampling_supported_cells"] == 6
    assert autonomy["sign_sensitive_to_mixture"] is True
    assert governance["sign_sensitive_to_mixture"] is True

    print("ITR/ATL v0.2.11 joint calibration surface: PASS")
    print(f"grid_points={stored['mixture_grid']['total_points']}")
    print(f"replicates={stored['resampling']['replicates']}")
    print(f"autonomy_resampling_supported_cells={autonomy['resampling_supported_cells']}")
    print(f"autonomy_positive_band_cells={autonomy['band_sign_class_counts']['positive_band']}")
    print(f"autonomy_crosses_zero_cells={autonomy['band_sign_class_counts']['crosses_zero']}")
    print(f"governance_resampling_supported_cells={governance['resampling_supported_cells']}")
    print(f"governance_positive_band_cells={governance['band_sign_class_counts']['positive_band']}")
    print(f"governance_crosses_zero_cells={governance['band_sign_class_counts']['crosses_zero']}")
    print("surface_cells_are_independent=False")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()

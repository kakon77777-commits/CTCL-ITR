#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.calibration_surface_geometry import analyze_surface_geometry
from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        (
            "schemas/calibration-surface-geometry-spec.schema.json",
            "examples/calibration_surface_geometry_spec.json",
        ),
        (
            "schemas/calibration-surface-geometry-report.schema.json",
            "examples/calibration_surface_geometry_report.json",
        ),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).validate(instance)

    stored = load("examples/calibration_surface_geometry_report.json")
    source_surface = analyze_joint_uncertainty_surface(
        load("examples/calibration_snapshot_base.json"),
        load("examples/calibration_snapshot_current.json"),
        load("examples/calibration_comparison_spec.json"),
        load("examples/calibration_joint_surface_spec.json"),
    )
    regenerated = analyze_surface_geometry(
        source_surface,
        load("examples/calibration_surface_geometry_spec.json"),
    )
    assert regenerated == stored
    assert stored["conditioning"]["unsupported_cells_interpolated"] is False
    assert stored["conditioning"]["local_gradients_supported_edges_only"] is True
    assert stored["non_authoritative"] is True

    auto = stored["subjects"]["autonomy"]
    gov = stored["subjects"]["governance"]
    assert auto["geometry_summary"]["supported_component_count"] == 1
    assert gov["geometry_summary"]["supported_component_count"] == 1
    assert auto["geometry_summary"]["positive_stability_boundary_count"] == 1
    assert gov["geometry_summary"]["positive_stability_boundary_count"] == 1
    assert len(auto["local_gradients"]) == 5
    assert len(gov["local_gradients"]) == 5

    print("ITR/ATL v0.2.12 surface geometry: PASS")
    print(f"autonomy_supported_components={auto['geometry_summary']['supported_component_count']}")
    print(f"autonomy_positive_stability_boundaries={auto['geometry_summary']['positive_stability_boundary_count']}")
    print(f"autonomy_local_gradient_edges={len(auto['local_gradients'])}")
    print(f"governance_supported_components={gov['geometry_summary']['supported_component_count']}")
    print(f"governance_positive_stability_boundaries={gov['geometry_summary']['positive_stability_boundary_count']}")
    print(f"governance_local_gradient_edges={len(gov['local_gradients'])}")
    print("unsupported_cells_interpolated=False")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()

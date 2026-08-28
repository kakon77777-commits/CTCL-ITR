import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ctcl_itr.calibration_geometry_drift import compare_surface_geometry
from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface
from ctcl_itr.calibration_surface_geometry import analyze_surface_geometry

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def load(name, *, root=EXAMPLES):
    return json.loads((root / name).read_text(encoding="utf-8"))


def build_later_geometry():
    surface = analyze_joint_uncertainty_surface(
        load("calibration_snapshot_base.json"),
        load("calibration_snapshot_later.json"),
        load("calibration_comparison_spec_later.json"),
        load("calibration_joint_surface_spec_later.json"),
    )
    return analyze_surface_geometry(surface, load("calibration_surface_geometry_spec_later.json"))


def test_geometry_drift_schemas_are_valid_draft_2020_12():
    for name in (
        "calibration-geometry-drift-spec.schema.json",
        "calibration-geometry-drift-report.schema.json",
    ):
        schema = load(name, root=SCHEMAS)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(schema)


def test_canonical_later_geometry_and_drift_artifacts_validate():
    geometry_schema = load("calibration-surface-geometry-report.schema.json", root=SCHEMAS)
    drift_spec_schema = load("calibration-geometry-drift-spec.schema.json", root=SCHEMAS)
    drift_report_schema = load("calibration-geometry-drift-report.schema.json", root=SCHEMAS)

    Draft202012Validator(geometry_schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        load("calibration_surface_geometry_report_later.json")
    )
    Draft202012Validator(drift_spec_schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        load("calibration_geometry_drift_spec.json")
    )
    Draft202012Validator(drift_report_schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        load("calibration_geometry_drift_report.json")
    )


def test_canonical_later_geometry_is_exact_regeneration():
    assert build_later_geometry() == load("calibration_surface_geometry_report_later.json")


def test_canonical_geometry_drift_report_is_exact_regeneration():
    fresh = compare_surface_geometry(
        load("calibration_surface_geometry_report.json"),
        build_later_geometry(),
        load("calibration_geometry_drift_spec.json"),
    )
    assert fresh == load("calibration_geometry_drift_report.json")


def test_canonical_geometry_drift_reference_summary():
    report = load("calibration_geometry_drift_report.json")
    auto = report["subjects"]["autonomy"]
    gov = report["subjects"]["governance"]

    for subject in (auto, gov):
        domain = subject["supported_domain_motion"]
        assert domain["base_supported_cell_count"] == 6
        assert domain["current_supported_cell_count"] == 8
        assert domain["gained_supported_cell_count"] == 2
        assert domain["lost_supported_cell_count"] == 0
        assert domain["jaccard_overlap"] == 0.75
        assert subject["component_motion"]["split_count"] == 0
        assert subject["component_motion"]["merge_count"] == 0
        assert subject["support_frontier_motion"]["matched_supported_endpoint_count"] == 1
        assert subject["support_frontier_motion"]["matched_supported_endpoints"][0][
            "signed_family_displacement"
        ]["code"] > 0
        assert subject["local_gradient_drift"]["matched_edge_count"] == 5
        assert subject["local_gradient_drift"]["appeared_edge_count"] == 2
        assert subject["local_gradient_drift"]["disappeared_edge_count"] == 0

    assert auto["stability_boundary_motion"]["positive"]["matches"][0]["current_weights"]["code"] == 0.37677630955816144
    assert gov["stability_boundary_motion"]["positive"]["matches"][0]["current_weights"]["code"] == 0.35854728749637416
    assert auto["stability_boundary_motion"]["positive"]["matches"][0]["signed_family_displacement"]["code"] < 0
    assert gov["stability_boundary_motion"]["positive"]["matches"][0]["signed_family_displacement"]["code"] < 0
    assert report["non_authoritative"] is True

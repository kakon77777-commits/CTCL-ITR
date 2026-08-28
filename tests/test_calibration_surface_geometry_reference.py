import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ctcl_itr.calibration_surface_geometry import analyze_surface_geometry
from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_surface_geometry_schemas_are_valid_draft_2020_12():
    for name in (
        "calibration-surface-geometry-spec.schema.json",
        "calibration-surface-geometry-report.schema.json",
    ):
        schema = load(SCHEMAS / name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(schema)


def test_canonical_geometry_spec_and_report_validate():
    spec_schema = load(SCHEMAS / "calibration-surface-geometry-spec.schema.json")
    report_schema = load(SCHEMAS / "calibration-surface-geometry-report.schema.json")
    spec = load(EXAMPLES / "calibration_surface_geometry_spec.json")
    report = load(EXAMPLES / "calibration_surface_geometry_report.json")

    Draft202012Validator(spec_schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(spec)
    Draft202012Validator(report_schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(report)


def build_reference_surface():
    return analyze_joint_uncertainty_surface(
        load(EXAMPLES / "calibration_snapshot_base.json"),
        load(EXAMPLES / "calibration_snapshot_current.json"),
        load(EXAMPLES / "calibration_comparison_spec.json"),
        load(EXAMPLES / "calibration_joint_surface_spec.json"),
    )


def test_canonical_geometry_report_is_exact_regeneration():
    spec = load(EXAMPLES / "calibration_surface_geometry_spec.json")
    stored = load(EXAMPLES / "calibration_surface_geometry_report.json")
    fresh = analyze_surface_geometry(build_reference_surface(), spec)

    assert fresh == stored


def test_canonical_geometry_reference_summary():
    report = load(EXAMPLES / "calibration_surface_geometry_report.json")
    auto = report["subjects"]["autonomy"]
    gov = report["subjects"]["governance"]

    for subject in (auto, gov):
        summary = subject["geometry_summary"]
        assert summary["supported_component_count"] == 1
        assert summary["largest_supported_component_size"] == 6
        assert summary["support_boundary_edge_count"] == 1
        assert summary["sign_class_boundary_edge_count"] == 1
        assert summary["positive_stability_boundary_count"] == 1
        assert summary["negative_stability_boundary_count"] == 0
        assert summary["local_gradient_edge_count"] == 5

    assert auto["boundaries"]["positive_stability_zero_crossings"][0][
        "estimated_reference_family_weights"
    ]["code"] == 0.5528922561345437
    assert gov["boundaries"]["positive_stability_zero_crossings"][0][
        "estimated_reference_family_weights"
    ]["code"] == 0.5
    assert report["non_authoritative"] is True

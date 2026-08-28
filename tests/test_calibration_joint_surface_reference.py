import json
from pathlib import Path

import jsonschema

from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SCHEMAS = ROOT / "schemas"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_joint_surface_reference_artifacts_validate_against_draft_2020_12():
    spec_schema = load(SCHEMAS / "calibration-joint-surface-spec.schema.json")
    report_schema = load(SCHEMAS / "calibration-joint-surface-report.schema.json")
    jsonschema.Draft202012Validator.check_schema(spec_schema)
    jsonschema.Draft202012Validator.check_schema(report_schema)
    jsonschema.Draft202012Validator(spec_schema).validate(
        load(EXAMPLES / "calibration_joint_surface_spec.json")
    )
    jsonschema.Draft202012Validator(report_schema).validate(
        load(EXAMPLES / "calibration_joint_surface_report.json")
    )


def test_reference_joint_surface_report_is_exactly_regenerated():
    generated = analyze_joint_uncertainty_surface(
        load(EXAMPLES / "calibration_snapshot_base.json"),
        load(EXAMPLES / "calibration_snapshot_current.json"),
        load(EXAMPLES / "calibration_comparison_spec.json"),
        load(EXAMPLES / "calibration_joint_surface_spec.json"),
    )
    stored = load(EXAMPLES / "calibration_joint_surface_report.json")
    assert generated == stored


def test_reference_joint_surface_exposes_support_and_sign_regions():
    report = load(EXAMPLES / "calibration_joint_surface_report.json")
    assert report["resampling"]["replicates"] == 256
    assert report["mixture_grid"]["total_points"] == 9
    assert report["conditioning"]["surface_cells_are_independent"] is False
    for subject in ("autonomy", "governance"):
        summary = report["subjects"][subject]["surface_summary"]
        assert summary["resampling_supported_cells"] < summary["total_cells"]
        assert summary["band_sign_class_counts"]["unsupported"] > 0
        assert summary["sign_sensitive_to_mixture"] is True
        assert summary["band_width_range"]["maximum"] >= summary["band_width_range"]["minimum"]
    assert report["non_authoritative"] is True

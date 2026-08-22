import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ctcl_itr.calibration_mixture_sensitivity import analyze_reference_mixture_sensitivity

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_reference_spec_and_report_validate_against_draft_2020_12():
    spec_schema = load("schemas/calibration-mixture-sensitivity-spec.schema.json")
    report_schema = load("schemas/calibration-mixture-sensitivity-report.schema.json")
    Draft202012Validator.check_schema(spec_schema)
    Draft202012Validator.check_schema(report_schema)
    Draft202012Validator(spec_schema).validate(load("examples/calibration_mixture_sensitivity_spec.json"))
    Draft202012Validator(report_schema).validate(load("examples/calibration_mixture_sensitivity_report.json"))


def test_reference_report_is_exactly_regenerated():
    regenerated = analyze_reference_mixture_sensitivity(
        load("examples/calibration_snapshot_base.json"),
        load("examples/calibration_snapshot_current.json"),
        load("examples/calibration_comparison_spec.json"),
        load("examples/calibration_mixture_sensitivity_spec.json"),
        load("examples/calibration_uncertainty_report.json"),
    )
    assert regenerated == load("examples/calibration_mixture_sensitivity_report.json")
    assert regenerated["subjects"]["autonomy"]["supported_grid_points"] == 6
    assert regenerated["subjects"]["governance"]["supported_grid_points"] == 6
    assert regenerated["subjects"]["autonomy"]["uncertainty_axes"]["larger_reported_axis"] == "sampling"
    assert regenerated["subjects"]["governance"]["uncertainty_axes"]["larger_reported_axis"] == "sampling"

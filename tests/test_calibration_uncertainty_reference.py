import json
from pathlib import Path

import jsonschema

from ctcl_itr.calibration_uncertainty import bootstrap_calibration_uncertainty

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SCHEMAS = ROOT / "schemas"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_uncertainty_reference_artifacts_validate_against_draft_2020_12():
    spec_schema = load(SCHEMAS / "calibration-uncertainty-spec.schema.json")
    report_schema = load(SCHEMAS / "calibration-uncertainty-report.schema.json")
    jsonschema.Draft202012Validator.check_schema(spec_schema)
    jsonschema.Draft202012Validator.check_schema(report_schema)
    jsonschema.Draft202012Validator(spec_schema).validate(load(EXAMPLES / "calibration_uncertainty_spec.json"))
    jsonschema.Draft202012Validator(report_schema).validate(load(EXAMPLES / "calibration_uncertainty_report.json"))


def test_reference_uncertainty_report_is_exactly_regenerated():
    generated = bootstrap_calibration_uncertainty(
        load(EXAMPLES / "calibration_snapshot_base.json"),
        load(EXAMPLES / "calibration_snapshot_current.json"),
        load(EXAMPLES / "calibration_comparison_spec.json"),
        load(EXAMPLES / "calibration_uncertainty_spec.json"),
    )
    stored = load(EXAMPLES / "calibration_uncertainty_report.json")
    assert generated == stored


def test_reference_uncertainty_report_preserves_point_estimate_and_exposes_bands():
    report = load(EXAMPLES / "calibration_uncertainty_report.json")
    assert report["replicates"] == 256
    assert report["method"] == "stratified_empirical_binomial_sha256_v1"
    assert report["conditioning"]["composition_resampled"] is False
    autonomy = report["subjects"]["autonomy"]
    assert autonomy["point_estimate"]["observed_mix_delta"] < 0
    assert autonomy["point_estimate"]["composition_adjusted_delta"] > 0
    adjusted = autonomy["bands"]["composition_adjusted_delta"]
    assert adjusted["support_status"] == "supported"
    assert adjusted["band"]["lower"] <= adjusted["band"]["median"] <= adjusted["band"]["upper"]
    shares = autonomy["sign_shares"]["composition_adjusted_delta"]
    assert abs(sum(shares.values()) - 1.0) < 1e-12
    assert report["non_authoritative"] is True

import json
from pathlib import Path

import jsonschema

from ctcl_itr.calibration_robustness import build_calibration_snapshot, compare_calibration_snapshots

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_reference_artifacts_validate_against_v028_schemas():
    pairs = [
        ("calibration_snapshot_base.json", "calibration-snapshot.schema.json"),
        ("calibration_snapshot_current.json", "calibration-snapshot.schema.json"),
        ("calibration_comparison_spec.json", "calibration-comparison-spec.schema.json"),
        ("calibration_robustness_report.json", "calibration-robustness-report.schema.json"),
    ]
    for example_name, schema_name in pairs:
        schema = load_json(SCHEMAS / schema_name)
        instance = load_json(EXAMPLES / example_name)
        jsonschema.Draft202012Validator(schema).validate(instance)


def test_reference_report_is_exactly_regenerated_from_snapshot_specs():
    base_spec = load_json(EXAMPLES / "calibration_snapshot_base.json")
    current_spec = load_json(EXAMPLES / "calibration_snapshot_current.json")
    comparison_spec = load_json(EXAMPLES / "calibration_comparison_spec.json")
    expected = load_json(EXAMPLES / "calibration_robustness_report.json")

    actual = compare_calibration_snapshots(
        build_calibration_snapshot(base_spec),
        build_calibration_snapshot(current_spec),
        comparison_spec,
    )
    assert actual == expected


def test_reference_exposes_composition_illusion_in_both_subjects():
    report = load_json(EXAMPLES / "calibration_robustness_report.json")
    assert report["context_diagnostics"]["comparison_kind"] == "cross_backend"
    for subject in ("autonomy", "governance"):
        metrics = report["subjects"][subject]
        assert metrics["composition_total_variation"] == 0.6
        assert metrics["observed_mix_delta"] < 0
        assert metrics["composition_adjusted_delta"] > 0
        assert metrics["family_horizon_deltas"]["code"]["delta"] > 0
        assert metrics["family_horizon_deltas"]["research"]["delta"] > 0

import json
from pathlib import Path

import jsonschema

from ctcl_itr.horizon_calibration import calibrate_horizon_suite

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_reference_suite_and_profile_validate_under_draft_202012():
    pairs = [
        ("schemas/horizon-calibration-suite.schema.json", "examples/horizon_calibration_suite.json"),
        ("schemas/horizon-evidence-profile.schema.json", "examples/horizon_calibration_profile.json"),
    ]
    for schema_rel, example_rel in pairs:
        schema = _load(schema_rel)
        instance = _load(example_rel)
        jsonschema.Draft202012Validator(schema).validate(instance)


def test_reference_profile_is_exact_fresh_regeneration():
    suite = _load("examples/horizon_calibration_suite.json")
    stored = _load("examples/horizon_calibration_profile.json")
    regenerated = calibrate_horizon_suite(suite)
    assert regenerated == stored
    assert stored["subjects"]["autonomy"]["horizon_depth"] == 12.0
    assert stored["subjects"]["governance"]["horizon_depth"] == 9.0
    assert stored["derived_assessment"]["autonomy_horizon_depth"] == 12.0
    assert stored["derived_assessment"]["governance_horizon_depth"] == 9.0

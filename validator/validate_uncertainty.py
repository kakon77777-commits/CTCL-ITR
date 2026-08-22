#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.calibration_uncertainty import bootstrap_calibration_uncertainty


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        ("schemas/calibration-uncertainty-spec.schema.json", "examples/calibration_uncertainty_spec.json"),
        ("schemas/calibration-uncertainty-report.schema.json", "examples/calibration_uncertainty_report.json"),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)

    stored = load("examples/calibration_uncertainty_report.json")
    regenerated = bootstrap_calibration_uncertainty(
        load("examples/calibration_snapshot_base.json"),
        load("examples/calibration_snapshot_current.json"),
        load("examples/calibration_comparison_spec.json"),
        load("examples/calibration_uncertainty_spec.json"),
    )
    assert regenerated == stored
    assert stored["conditioning"]["composition_resampled"] is False
    assert stored["non_authoritative"] is True

    autonomy = stored["subjects"]["autonomy"]
    governance = stored["subjects"]["governance"]
    assert autonomy["point_estimate"]["observed_mix_delta"] < 0
    assert autonomy["point_estimate"]["composition_adjusted_delta"] > 0
    assert governance["point_estimate"]["observed_mix_delta"] < 0
    assert governance["point_estimate"]["composition_adjusted_delta"] > 0

    print("ITR/ATL v0.2.9 calibration uncertainty & drift bands: PASS")
    print(f"replicates={stored['replicates']}")
    print(f"interval_p={stored['interval_p']}")
    print(f"autonomy_adjusted_support={autonomy['bands']['composition_adjusted_delta']['supported_fraction']}")
    print(f"autonomy_adjusted_positive_share={autonomy['sign_shares']['composition_adjusted_delta']['positive']}")
    print(f"governance_adjusted_support={governance['bands']['composition_adjusted_delta']['supported_fraction']}")
    print(f"governance_adjusted_positive_share={governance['sign_shares']['composition_adjusted_delta']['positive']}")
    print("composition_resampled=False")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.calibration_robustness import build_calibration_snapshot, compare_calibration_snapshots


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        ("schemas/calibration-snapshot.schema.json", "examples/calibration_snapshot_base.json"),
        ("schemas/calibration-snapshot.schema.json", "examples/calibration_snapshot_current.json"),
        ("schemas/calibration-comparison-spec.schema.json", "examples/calibration_comparison_spec.json"),
        ("schemas/calibration-robustness-report.schema.json", "examples/calibration_robustness_report.json"),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)

    base_spec = load("examples/calibration_snapshot_base.json")
    current_spec = load("examples/calibration_snapshot_current.json")
    comparison_spec = load("examples/calibration_comparison_spec.json")
    stored = load("examples/calibration_robustness_report.json")
    regenerated = compare_calibration_snapshots(
        build_calibration_snapshot(base_spec),
        build_calibration_snapshot(current_spec),
        comparison_spec,
    )
    assert regenerated == stored

    autonomy = stored["subjects"]["autonomy"]
    governance = stored["subjects"]["governance"]
    assert autonomy["observed_mix_delta"] < 0 < autonomy["composition_adjusted_delta"]
    assert governance["observed_mix_delta"] < 0 < governance["composition_adjusted_delta"]
    assert autonomy["composition_total_variation"] == 0.6
    assert governance["composition_total_variation"] == 0.6
    assert stored["context_diagnostics"]["comparison_kind"] == "cross_backend"
    assert stored["non_authoritative"] is True

    print("ITR/ATL v0.2.8 calibration robustness & drift: PASS")
    print(f"autonomy_observed_delta={autonomy['observed_mix_delta']}")
    print(f"autonomy_adjusted_delta={autonomy['composition_adjusted_delta']}")
    print(f"governance_observed_delta={governance['observed_mix_delta']}")
    print(f"governance_adjusted_delta={governance['composition_adjusted_delta']}")
    print(f"composition_tv={autonomy['composition_total_variation']}")
    print(f"comparison_kind={stored['context_diagnostics']['comparison_kind']}")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()

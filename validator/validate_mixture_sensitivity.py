#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.calibration_mixture_sensitivity import analyze_reference_mixture_sensitivity


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        ("schemas/calibration-mixture-sensitivity-spec.schema.json", "examples/calibration_mixture_sensitivity_spec.json"),
        ("schemas/calibration-mixture-sensitivity-report.schema.json", "examples/calibration_mixture_sensitivity_report.json"),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)

    stored = load("examples/calibration_mixture_sensitivity_report.json")
    regenerated = analyze_reference_mixture_sensitivity(
        load("examples/calibration_snapshot_base.json"),
        load("examples/calibration_snapshot_current.json"),
        load("examples/calibration_comparison_spec.json"),
        load("examples/calibration_mixture_sensitivity_spec.json"),
        load("examples/calibration_uncertainty_report.json"),
    )
    assert regenerated == stored
    assert stored["uncertainty_decomposition"] == "separate_axes_not_additive"
    assert stored["non_authoritative"] is True

    autonomy = stored["subjects"]["autonomy"]
    governance = stored["subjects"]["governance"]
    assert autonomy["supported_grid_points"] == 6
    assert governance["supported_grid_points"] == 6
    assert autonomy["sign_shares"]["positive"] == 1.0
    assert governance["sign_shares"]["positive"] == 1.0
    assert autonomy["uncertainty_axes"]["larger_reported_axis"] == "sampling"
    assert governance["uncertainty_axes"]["larger_reported_axis"] == "sampling"
    assert autonomy["uncertainty_axes"]["axes_are_additive"] is False

    print("ITR/ATL v0.2.10 reference-mixture sensitivity: PASS")
    print(f"grid_points={stored['grid']['total_points']}")
    print(f"autonomy_supported_grid_fraction={autonomy['supported_grid_fraction']}")
    print(f"autonomy_mixture_span={autonomy['sensitivity_range']['span']}")
    print(f"autonomy_sampling_band_width={autonomy['uncertainty_axes']['sampling_band_width_at_reference']}")
    print(f"governance_supported_grid_fraction={governance['supported_grid_fraction']}")
    print(f"governance_mixture_span={governance['sensitivity_range']['span']}")
    print(f"governance_sampling_band_width={governance['uncertainty_axes']['sampling_band_width_at_reference']}")
    print("axes_are_additive=False")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()

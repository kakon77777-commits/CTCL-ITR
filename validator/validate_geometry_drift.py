#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.calibration_geometry_drift import compare_surface_geometry
from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface
from ctcl_itr.calibration_surface_geometry import analyze_surface_geometry


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs=[("schemas/calibration-geometry-drift-spec.schema.json","examples/calibration_geometry_drift_spec.json"),("schemas/calibration-geometry-drift-report.schema.json","examples/calibration_geometry_drift_report.json"),("schemas/calibration-surface-geometry-report.schema.json","examples/calibration_surface_geometry_report_later.json")]
    for schema_path,example_path in pairs:
        schema=load(schema_path); instance=load(example_path); jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema,format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER).validate(instance)
    later_surface=analyze_joint_uncertainty_surface(load("examples/calibration_snapshot_base.json"),load("examples/calibration_snapshot_later.json"),load("examples/calibration_comparison_spec_later.json"),load("examples/calibration_joint_surface_spec_later.json"))
    later_geometry=analyze_surface_geometry(later_surface,load("examples/calibration_surface_geometry_spec_later.json"))
    assert later_geometry==load("examples/calibration_surface_geometry_report_later.json")
    stored=load("examples/calibration_geometry_drift_report.json")
    regenerated=compare_surface_geometry(load("examples/calibration_surface_geometry_report.json"),later_geometry,load("examples/calibration_geometry_drift_spec.json"))
    assert regenerated==stored
    assert stored["conditioning"]["unsupported_region_interpolated"] is False
    assert stored["conditioning"]["boundary_matching_is_descriptive_not_identity"] is True
    assert stored["non_authoritative"] is True
    auto=stored["subjects"]["autonomy"]; gov=stored["subjects"]["governance"]
    for subject in (auto,gov):
        assert subject["supported_domain_motion"]["gained_supported_cell_count"]==2
        assert subject["supported_domain_motion"]["lost_supported_cell_count"]==0
        assert subject["component_motion"]["split_count"]==0
        assert subject["component_motion"]["merge_count"]==0
        assert subject["local_gradient_drift"]["matched_edge_count"]==5
        assert subject["local_gradient_drift"]["appeared_edge_count"]==2
    auto_disp=auto["stability_boundary_motion"]["positive"]["matches"][0]["signed_family_displacement"]["code"]
    gov_disp=gov["stability_boundary_motion"]["positive"]["matches"][0]["signed_family_displacement"]["code"]
    assert auto_disp<0 and gov_disp<0
    print("ITR/ATL v0.2.13 geometry drift: PASS")
    print(f"autonomy_supported_gain={auto['supported_domain_motion']['gained_supported_cell_count']}")
    print(f"autonomy_positive_boundary_code_displacement={auto_disp}")
    print(f"autonomy_gradient_appeared={auto['local_gradient_drift']['appeared_edge_count']}")
    print(f"governance_supported_gain={gov['supported_domain_motion']['gained_supported_cell_count']}")
    print(f"governance_positive_boundary_code_displacement={gov_disp}")
    print(f"governance_gradient_appeared={gov['local_gradient_drift']['appeared_edge_count']}")
    print("non_authoritative=True")


if __name__=="__main__": main()

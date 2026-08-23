#!/usr/bin/env python3
from pathlib import Path
import json, sys
import jsonschema

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ctcl_itr.calibration_geometry_trajectory import analyze_geometry_trajectory
from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface
from ctcl_itr.calibration_surface_geometry import analyze_surface_geometry

def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))

def build_regressed_geometry():
    surface=analyze_joint_uncertainty_surface(
        load('examples/calibration_snapshot_base.json'),
        load('examples/calibration_snapshot_regressed.json'),
        load('examples/calibration_comparison_spec_regressed.json'),
        load('examples/calibration_joint_surface_spec_regressed.json'))
    return analyze_surface_geometry(surface,load('examples/calibration_surface_geometry_spec_regressed.json'))

def main():
    for sp in ['schemas/calibration-geometry-trajectory-spec.schema.json','schemas/calibration-geometry-trajectory-report.schema.json']:
        jsonschema.Draft202012Validator.check_schema(load(sp))
    g2=build_regressed_geometry()
    assert g2==load('examples/calibration_surface_geometry_report_regressed.json')
    geometry_schema=load('schemas/calibration-surface-geometry-report.schema.json')
    jsonschema.Draft202012Validator(geometry_schema,format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER).validate(g2)
    spec=load('examples/calibration_geometry_trajectory_spec.json')
    jsonschema.Draft202012Validator(load('schemas/calibration-geometry-trajectory-spec.schema.json'),format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER).validate(spec)
    fresh=analyze_geometry_trajectory([
        load('examples/calibration_surface_geometry_report.json'),
        load('examples/calibration_surface_geometry_report_later.json'),
        g2],spec)
    jsonschema.Draft202012Validator(load('schemas/calibration-geometry-trajectory-report.schema.json'),format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER).validate(fresh)
    assert fresh['non_authoritative'] is True
    auto=fresh['subjects']['autonomy']; gov=fresh['subjects']['governance']
    assert auto['supported_domain_trajectory']['direction_reversal_count']==1
    assert gov['supported_domain_trajectory']['direction_reversal_count']==1
    assert auto['stability_boundary_trajectories']['positive']['lineages'][0]['velocity_direction_reversal_count_by_family']['code']==1
    assert gov['stability_boundary_trajectories']['positive']['lineages'][0]['velocity_direction_reversal_count_by_family']['code']==1
    print('ITR/ATL v0.2.14 geometry trajectory: PASS')
    print(f"autonomy_support_reversals={auto['supported_domain_trajectory']['direction_reversal_count']}")
    print(f"autonomy_boundary_code_velocity_reversals={auto['stability_boundary_trajectories']['positive']['lineages'][0]['velocity_direction_reversal_count_by_family']['code']}")
    print(f"governance_support_reversals={gov['supported_domain_trajectory']['direction_reversal_count']}")
    print(f"governance_boundary_code_velocity_reversals={gov['stability_boundary_trajectories']['positive']['lineages'][0]['velocity_direction_reversal_count_by_family']['code']}")
    print('non_authoritative=True')
if __name__=='__main__': main()

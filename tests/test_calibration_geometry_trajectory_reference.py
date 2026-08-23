import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ctcl_itr.calibration_geometry_trajectory import analyze_geometry_trajectory
from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface
from ctcl_itr.calibration_surface_geometry import analyze_surface_geometry

ROOT=Path(__file__).resolve().parents[1]
EXAMPLES=ROOT/'examples'; SCHEMAS=ROOT/'schemas'

def load(name,root=EXAMPLES): return json.loads((root/name).read_text(encoding='utf-8'))

def build_regressed_geometry():
    surface=analyze_joint_uncertainty_surface(
        load('calibration_snapshot_base.json'),
        load('calibration_snapshot_regressed.json'),
        load('calibration_comparison_spec_regressed.json'),
        load('calibration_joint_surface_spec_regressed.json'),
    )
    return analyze_surface_geometry(surface,load('calibration_surface_geometry_spec_regressed.json'))

def build_trajectory():
    return analyze_geometry_trajectory([
        load('calibration_surface_geometry_report.json'),
        load('calibration_surface_geometry_report_later.json'),
        build_regressed_geometry(),
    ],load('calibration_geometry_trajectory_spec.json'))

def test_geometry_trajectory_schemas_are_valid_draft_2020_12():
    for name in ('calibration-geometry-trajectory-spec.schema.json','calibration-geometry-trajectory-report.schema.json'):
        schema=load(name,SCHEMAS)
        assert schema['$schema']=='https://json-schema.org/draft/2020-12/schema'
        Draft202012Validator.check_schema(schema)

def test_canonical_regressed_geometry_and_generated_trajectory_validate():
    geometry_schema=load('calibration-surface-geometry-report.schema.json',SCHEMAS)
    Draft202012Validator(geometry_schema,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(load('calibration_surface_geometry_report_regressed.json'))
    trajectory_spec_schema=load('calibration-geometry-trajectory-spec.schema.json',SCHEMAS)
    Draft202012Validator(trajectory_spec_schema,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(load('calibration_geometry_trajectory_spec.json'))
    trajectory_schema=load('calibration-geometry-trajectory-report.schema.json',SCHEMAS)
    Draft202012Validator(trajectory_schema,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(build_trajectory())

def test_canonical_regressed_geometry_is_exact_regeneration():
    assert build_regressed_geometry()==load('calibration_surface_geometry_report_regressed.json')

def test_generated_trajectory_reference_summary():
    report=build_trajectory()
    for subject in ('autonomy','governance'):
        q=report['subjects'][subject]
        support=q['supported_domain_trajectory']
        assert support['supported_cell_counts']==[6,8,6]
        assert support['step_directions']==['expansion','contraction']
        assert support['direction_reversal_count']==1
        assert q['component_trajectories']['spans_all_observations_count']==1
        assert q['sign_region_persistence']['support_excursion_cell_count']==2
        positive=q['stability_boundary_trajectories']['positive']
        assert positive['lineage_count']==1
        lineage=positive['lineages'][0]
        assert lineage['velocity_direction_reversal_count_by_family']['code']==1
        assert abs(lineage['net_signed_displacement']['code']) < 1e-12
        assert len(lineage['accelerations'])==1
        assert q['local_gradient_trajectories']['presence_excursion_count']==2
    assert report['non_authoritative'] is True

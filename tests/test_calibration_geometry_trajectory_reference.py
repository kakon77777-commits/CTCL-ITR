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

def test_geometry_trajectory_schemas_are_valid_draft_2020_12():
    for name in ('calibration-geometry-trajectory-spec.schema.json','calibration-geometry-trajectory-report.schema.json'):
        schema=load(name,SCHEMAS)
        assert schema['$schema']=='https://json-schema.org/draft/2020-12/schema'
        Draft202012Validator.check_schema(schema)

def test_canonical_regressed_geometry_and_trajectory_validate():
    pairs=[
        ('calibration-surface-geometry-report.schema.json','calibration_surface_geometry_report_regressed.json'),
        ('calibration-geometry-trajectory-spec.schema.json','calibration_geometry_trajectory_spec.json'),
        ('calibration-geometry-trajectory-report.schema.json','calibration_geometry_trajectory_report.json'),
    ]
    for schema_name,example_name in pairs:
        schema=load(schema_name,SCHEMAS); instance=load(example_name)
        Draft202012Validator(schema,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(instance)

def test_canonical_regressed_geometry_is_exact_regeneration():
    assert build_regressed_geometry()==load('calibration_surface_geometry_report_regressed.json')

def test_canonical_trajectory_is_exact_regeneration():
    fresh=analyze_geometry_trajectory([
        load('calibration_surface_geometry_report.json'),
        load('calibration_surface_geometry_report_later.json'),
        build_regressed_geometry(),
    ],load('calibration_geometry_trajectory_spec.json'))
    assert fresh==load('calibration_geometry_trajectory_report.json')

def test_canonical_trajectory_reference_summary():
    report=load('calibration_geometry_trajectory_report.json')
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

import json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXAMPLES=ROOT/'examples'

def run(*args):
    return subprocess.run(args,cwd=ROOT,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})

def test_module_cli_emits_canonical_trajectory_report():
    cp=run(sys.executable,'-m','ctcl_itr.calibration_geometry_trajectory',
        '--trajectory',str(EXAMPLES/'calibration_geometry_trajectory_spec.json'),
        '--geometry',str(EXAMPLES/'calibration_surface_geometry_report.json'),
        '--geometry',str(EXAMPLES/'calibration_surface_geometry_report_later.json'),
        '--geometry',str(EXAMPLES/'calibration_surface_geometry_report_regressed.json'))
    assert cp.returncode==0,cp.stderr
    assert json.loads(cp.stdout)==json.loads((EXAMPLES/'calibration_geometry_trajectory_report.json').read_text(encoding='utf-8'))
    assert 'RuntimeWarning' not in cp.stderr

def test_geometry_trajectory_validator_passes():
    validator=ROOT/'validator'/'validate_geometry_trajectory.py'
    assert validator.exists()
    cp=run(sys.executable,str(validator))
    assert cp.returncode==0,cp.stderr
    assert 'v0.2.14 geometry trajectory: PASS' in cp.stdout
    assert 'autonomy_support_reversals=1' in cp.stdout
    assert 'governance_boundary_code_velocity_reversals=1' in cp.stdout

def test_package_metadata_is_v0215_and_exposes_entry_point():
    text=(ROOT/'pyproject.toml').read_text(encoding='utf-8')
    assert 'version = "0.2.15"' in text
    assert 'ctcl-itr-geometry-trajectory = "ctcl_itr.calibration_geometry_trajectory:_main"' in text
    init_text=(ROOT/'src'/'ctcl_itr'/'__init__.py').read_text(encoding='utf-8')
    assert '__version__ = "0.2.15"' in init_text

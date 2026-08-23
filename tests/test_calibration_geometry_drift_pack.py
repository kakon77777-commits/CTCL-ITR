import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run(*args):
    return subprocess.run(args,cwd=ROOT,capture_output=True,text=True,env={**os.environ,"PYTHONPATH":str(ROOT / "src")})


def test_module_cli_emits_canonical_drift_report():
    cp = run(sys.executable,"-m","ctcl_itr.calibration_geometry_drift","--base-geometry",str(EXAMPLES / "calibration_surface_geometry_report.json"),"--current-geometry",str(EXAMPLES / "calibration_surface_geometry_report_later.json"),"--drift",str(EXAMPLES / "calibration_geometry_drift_spec.json"))
    assert cp.returncode == 0, cp.stderr
    assert json.loads(cp.stdout) == json.loads((EXAMPLES / "calibration_geometry_drift_report.json").read_text(encoding="utf-8"))
    assert "RuntimeWarning" not in cp.stderr


def test_geometry_drift_validator_passes():
    validator = ROOT / "validator" / "validate_geometry_drift.py"
    assert validator.exists()
    cp = run(sys.executable,str(validator))
    assert cp.returncode == 0, cp.stderr
    assert "v0.2.13 geometry drift: PASS" in cp.stdout
    assert "autonomy_supported_gain=2" in cp.stdout
    assert "governance_positive_boundary_code_displacement=" in cp.stdout


def test_package_metadata_is_v0213_and_exposes_entry_point():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.2.13"' in text
    assert 'ctcl-itr-geometry-drift = "ctcl_itr.calibration_geometry_drift:_main"' in text
    init_text = (ROOT / "src" / "ctcl_itr" / "__init__.py").read_text(encoding="utf-8")
    assert '__version__ = "0.2.13"' in init_text

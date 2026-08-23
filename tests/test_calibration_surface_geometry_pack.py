import json
import os
import subprocess
import sys
from pathlib import Path

from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run(*args):
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )


def build_reference_surface():
    def load(name):
        return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    return analyze_joint_uncertainty_surface(
        load("calibration_snapshot_base.json"),
        load("calibration_snapshot_current.json"),
        load("calibration_comparison_spec.json"),
        load("calibration_joint_surface_spec.json"),
    )


def test_module_cli_emits_reference_equivalent_geometry_report(tmp_path):
    surface_path = tmp_path / "surface.json"
    surface_path.write_text(json.dumps(build_reference_surface(), ensure_ascii=False), encoding="utf-8")
    cp = run(
        sys.executable,
        "-m",
        "ctcl_itr.calibration_surface_geometry",
        "--surface",
        str(surface_path),
        "--geometry",
        str(EXAMPLES / "calibration_surface_geometry_spec.json"),
    )
    assert cp.returncode == 0, cp.stderr
    assert json.loads(cp.stdout) == json.loads(
        (EXAMPLES / "calibration_surface_geometry_report.json").read_text(encoding="utf-8")
    )
    assert "RuntimeWarning" not in cp.stderr


def test_surface_geometry_validator_passes():
    validator = ROOT / "validator" / "validate_surface_geometry.py"
    assert validator.exists()
    cp = run(sys.executable, str(validator))
    assert cp.returncode == 0, cp.stderr
    assert "v0.2.12 surface geometry: PASS" in cp.stdout
    assert "autonomy_supported_components=1" in cp.stdout
    assert "governance_positive_stability_boundaries=1" in cp.stdout


def test_package_metadata_is_v0212_and_exposes_entry_point():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.2.12"' in text
    assert 'ctcl-itr-surface-geometry = "ctcl_itr.calibration_surface_geometry:_main"' in text

    init_text = (ROOT / "src" / "ctcl_itr" / "__init__.py").read_text(encoding="utf-8")
    assert '__version__ = "0.2.12"' in init_text

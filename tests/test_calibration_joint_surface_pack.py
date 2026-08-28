import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run(*args):
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )


def test_module_cli_emits_reference_equivalent_report():
    cp = run(
        sys.executable,
        "-m",
        "ctcl_itr.calibration_joint_surface",
        "--base",
        str(EXAMPLES / "calibration_snapshot_base.json"),
        "--current",
        str(EXAMPLES / "calibration_snapshot_current.json"),
        "--comparison",
        str(EXAMPLES / "calibration_comparison_spec.json"),
        "--surface",
        str(EXAMPLES / "calibration_joint_surface_spec.json"),
    )
    assert cp.returncode == 0, cp.stderr
    assert json.loads(cp.stdout) == json.loads(
        (EXAMPLES / "calibration_joint_surface_report.json").read_text(encoding="utf-8")
    )
    assert "RuntimeWarning" not in cp.stderr


def test_joint_surface_validator_passes():
    validator = ROOT / "validator" / "validate_joint_surface.py"
    assert validator.exists()
    cp = run(sys.executable, str(validator))
    assert cp.returncode == 0, cp.stderr
    assert "v0.2.11 joint calibration surface: PASS" in cp.stdout
    assert "autonomy_resampling_supported_cells=6" in cp.stdout
    assert "governance_resampling_supported_cells=6" in cp.stdout


def test_package_metadata_preserves_v0211_console_entry_point():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = tuple(int(part) for part in metadata["project"]["version"].split("."))
    assert version >= (0, 2, 11)
    assert metadata["project"]["scripts"]["ctcl-itr-joint-surface"] == "ctcl_itr.calibration_joint_surface:_main"

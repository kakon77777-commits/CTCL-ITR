import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_uncertainty_module_cli_emits_exact_reference_report():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctcl_itr.calibration_uncertainty",
            "--base", "examples/calibration_snapshot_base.json",
            "--current", "examples/calibration_snapshot_current.json",
            "--comparison", "examples/calibration_comparison_spec.json",
            "--uncertainty", "examples/calibration_uncertainty_spec.json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    stored = json.loads((ROOT / "examples/calibration_uncertainty_report.json").read_text(encoding="utf-8"))
    assert payload == stored


def test_uncertainty_validator_passes():
    completed = subprocess.run(
        [sys.executable, "validator/validate_uncertainty.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ITR/ATL v0.2.9 calibration uncertainty & drift bands: PASS" in completed.stdout
    assert "autonomy_adjusted_positive_share=" in completed.stdout
    assert "governance_adjusted_positive_share=" in completed.stdout


def test_package_metadata_preserves_v029_console_entry_point():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = tuple(int(part) for part in metadata["project"]["version"].split("."))
    assert version >= (0, 2, 9)
    assert metadata["project"]["scripts"]["ctcl-itr-calibration-uncertainty"] == "ctcl_itr.calibration_uncertainty:_main"

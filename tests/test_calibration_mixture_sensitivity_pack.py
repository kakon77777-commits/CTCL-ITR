import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_mixture_sensitivity_module_cli_emits_exact_reference_report():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctcl_itr.calibration_mixture_sensitivity",
            "--base", "examples/calibration_snapshot_base.json",
            "--current", "examples/calibration_snapshot_current.json",
            "--comparison", "examples/calibration_comparison_spec.json",
            "--sensitivity", "examples/calibration_mixture_sensitivity_spec.json",
            "--uncertainty-report", "examples/calibration_uncertainty_report.json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    stored = json.loads((ROOT / "examples/calibration_mixture_sensitivity_report.json").read_text(encoding="utf-8"))
    assert payload == stored


def test_mixture_sensitivity_validator_passes():
    completed = subprocess.run(
        [sys.executable, "validator/validate_mixture_sensitivity.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ITR/ATL v0.2.10 reference-mixture sensitivity: PASS" in completed.stdout
    assert "autonomy_mixture_span=" in completed.stdout
    assert "governance_mixture_span=" in completed.stdout
    assert "axes_are_additive=False" in completed.stdout


def test_package_metadata_preserves_v0210_console_entry_point():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = tuple(int(part) for part in metadata["project"]["version"].split("."))
    assert version >= (0, 2, 10)
    assert metadata["project"]["scripts"]["ctcl-itr-mixture-sensitivity"] == "ctcl_itr.calibration_mixture_sensitivity:_main"

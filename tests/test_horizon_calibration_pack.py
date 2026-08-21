import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_horizon_calibration_module_cli_emits_exact_reference_profile():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctcl_itr.horizon_calibration",
            "--suite",
            "examples/horizon_calibration_suite.json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    stored = json.loads((ROOT / "examples/horizon_calibration_profile.json").read_text(encoding="utf-8"))
    assert payload == stored
    assert payload["derived_assessment"]["autonomy_horizon_depth"] == 12.0
    assert payload["derived_assessment"]["governance_horizon_depth"] == 9.0


def test_horizon_calibration_validator_passes():
    completed = subprocess.run(
        [sys.executable, "validator/validate_calibration.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ITR/ATL v0.2.7 horizon calibration & evidence profiles: PASS" in completed.stdout
    assert "autonomy_horizon=12.0" in completed.stdout
    assert "governance_horizon=9.0" in completed.stdout
    assert "autonomy_support=supported" in completed.stdout
    assert "governance_support=supported" in completed.stdout

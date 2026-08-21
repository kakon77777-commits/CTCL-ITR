import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_governance_signals_module_cli_emits_exact_reference_report():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run([sys.executable,"-m","ctcl_itr.governance_signals","--metrics","examples/governance_metrics_report.json","--horizon","examples/governance_horizon_assessment.json","--policy","examples/governance_escalation_policy.json"],cwd=ROOT,env=env,capture_output=True,text=True)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    stored = json.loads((ROOT / "examples/governance_signal_report.json").read_text(encoding="utf-8"))
    assert payload == stored
    assert payload["non_authoritative"] is True


def test_governance_signal_pack_validator_passes():
    completed = subprocess.run([sys.executable,"validator/validate_signals.py"],cwd=ROOT,capture_output=True,text=True)
    assert completed.returncode == 0, completed.stderr
    assert "ITR/ATL v0.2.6 governance horizon & escalation signals: PASS" in completed.stdout
    assert "autonomy_governance_gap=3.0" in completed.stdout
    assert "signal_breaches=6" in completed.stdout
    assert "overall_level=critical" in completed.stdout

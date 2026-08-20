import json
import os
import subprocess
import sys
from pathlib import Path


def test_governance_demo_cli_emits_approval_receipt_grant_and_eligibility():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    cp = subprocess.run([sys.executable, "-m", "ctcl_itr.governance", "demo"], cwd=root, env=env, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    assert "RuntimeWarning" not in cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["approval_request"]["status"] == "pending"
    assert payload["decision_receipt"]["decision"] == "approve"
    assert payload["authority_grant"]["state"] == "active"
    assert payload["resume_eligibility"]["eligible"] is True
    assert payload["resume_eligibility"]["remaining_uses"] == 1

from pathlib import Path
import os
import subprocess
import sys


def test_reference_pack_validator_includes_v021_observability_exports():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        [sys.executable, "validator/validate_pack.py"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ITR/ATL v0.2.1 observability pack: PASS" in completed.stdout
    assert "multi_agent_events=12" in completed.stdout
    assert "cloudevents_roundtrip=12" in completed.stdout
    assert "otel_spans=12" in completed.stdout
    assert "join_links=3" in completed.stdout

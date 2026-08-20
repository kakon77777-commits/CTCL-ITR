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


def test_reference_pack_validator_includes_v022_ledger_integrity():
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
    assert "ITR/ATL v0.2.2 ledger integrity pack: PASS" in completed.stdout
    assert "integrity_records=12" in completed.stdout
    assert "anchor_checked=True" in completed.stdout
    assert "tamper_detection=record_digest_mismatch" in completed.stdout
    assert "truncation_detection=anchor_event_count_mismatch" in completed.stdout


def test_reference_pack_validator_includes_v023_governance_core():
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
    assert "ITR/ATL v0.2.3 governance core pack: PASS" in completed.stdout
    assert "governance_events=5" in completed.stdout
    assert "governance_resume_eligible=True" in completed.stdout
    assert "governance_scope_block=scope_mismatch" in completed.stdout


def test_reference_pack_validator_includes_v024_durable_governance_store():
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
    assert "ITR/ATL v0.2.4 durable governance store: PASS" in completed.stdout
    assert "durable_restart_recovered=True" in completed.stdout
    assert "durable_atomic_resolve=True" in completed.stdout
    assert "durable_authority_uses=2" in completed.stdout

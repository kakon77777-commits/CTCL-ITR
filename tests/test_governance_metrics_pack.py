from pathlib import Path
import os, subprocess, sys

def test_v025_metrics_validator():
    root=Path(__file__).resolve().parents[1]; env=os.environ.copy(); env["PYTHONPATH"]=str(root/"src")
    c=subprocess.run([sys.executable,"validator/validate_metrics.py"],cwd=root,env=env,capture_output=True,text=True)
    assert c.returncode==0,c.stderr
    assert "governance_hid=0.4444444444444444" in c.stdout
    assert "governance_eod=0.3157894736842105" in c.stdout
    assert "governance_oversight_debt=28.0" in c.stdout
    assert "governance_escalation_p95_ms=2400000" in c.stdout

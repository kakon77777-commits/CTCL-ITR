from pathlib import Path
import json, jsonschema, os, subprocess, sys
from ctcl_itr.governance_metrics import analyze_governance

ROOT=Path(__file__).resolve().parents[1]

def test_reference_report_is_canonical():
    s=json.loads((ROOT/"examples/governance_metrics_scenario.json").read_text())
    stored=json.loads((ROOT/"examples/governance_metrics_report.json").read_text())
    schema=json.loads((ROOT/"schemas/governance-metrics-report.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema); jsonschema.Draft202012Validator(schema).validate(stored)
    regen=analyze_governance(approval_requests=s["approval_requests"],decision_receipts=s["decision_receipts"],authority_grants=s["authority_grants"],events=s["events"],at=s["observed_at"],intervention_deadlines=s["intervention_deadlines"],policy=s["policy"])
    assert regen==stored and stored["oversight_debt"]["total_weight"]==28

def test_scenario_cli():
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT/"src")
    c=subprocess.run([sys.executable,"-m","ctcl_itr.governance_metrics","--scenario","examples/governance_metrics_scenario.json"],cwd=ROOT,env=env,capture_output=True,text=True)
    assert c.returncode==0,c.stderr
    p=json.loads(c.stdout); assert p["schema_version"]=="0.2.5" and p["effective_oversight_density"]["value"]==6/19

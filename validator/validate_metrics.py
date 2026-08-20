#!/usr/bin/env python3
from pathlib import Path
import json, sys
import jsonschema
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from ctcl_itr.governance_metrics import analyze_governance

def main():
    s=json.loads((ROOT/"examples/governance_metrics_scenario.json").read_text())
    stored=json.loads((ROOT/"examples/governance_metrics_report.json").read_text())
    schema=json.loads((ROOT/"schemas/governance-metrics-report.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema); jsonschema.Draft202012Validator(schema).validate(stored)
    regen=analyze_governance(approval_requests=s["approval_requests"],decision_receipts=s["decision_receipts"],authority_grants=s["authority_grants"],events=s["events"],at=s["observed_at"],intervention_deadlines=s["intervention_deadlines"],policy=s["policy"])
    assert regen==stored
    hid=stored["human_intervention_density"]["value"]; eod=stored["effective_oversight_density"]["value"]; debt=stored["oversight_debt"]["total_weight"]; p95=stored["escalation_latency"]["p95_ms"]
    assert hid==4/9 and eod==6/19 and debt==28 and p95==2400000
    print("ITR/ATL v0.2.5 governance observability metrics: PASS")
    print(f"governance_hid={hid}"); print(f"governance_eod={eod}"); print(f"governance_oversight_debt={debt}"); print(f"governance_escalation_p95_ms={p95}")
if __name__=="__main__": main()

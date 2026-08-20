#!/usr/bin/env python3
from pathlib import Path
import json, sys
try:
    import jsonschema
except Exception as exc:
    print("ERROR: jsonschema package is required:", exc); raise SystemExit(2)
BASE=Path(__file__).resolve().parents[1]; SCHEMAS=BASE/"schemas"; EXAMPLES=BASE/"examples"; SRC=BASE/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from ctcl_itr.interop.cloudevents import from_cloudevent,to_cloudevent
from ctcl_itr.interop.opentelemetry import project_events
from ctcl_itr.integrity import read_jsonl_record_bytes,seal_records,verify_records
from ctcl_itr.governance import evaluate_resume_eligibility
from ctcl_itr.topology import analyze_events

def load(name): return json.loads((SCHEMAS/name).read_text(encoding="utf-8"))
def validate_file(path,schema_name):
    obj=json.loads(Path(path).read_text(encoding="utf-8")); jsonschema.Draft202012Validator(load(schema_name)).validate(obj); return obj
def validate_event_file(path,validator):
    out=[]
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip(): obj=json.loads(line); validator.validate(obj); out.append(obj)
    return out
def load_jsonl(path): return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def main():
    for schema_name in ["intent.schema.json","run.schema.json","checkpoint.schema.json","commit-receipt.schema.json","run-summary.schema.json","temporal-event.schema.json","integrity-record.schema.json","ledger-anchor.schema.json","approval-request.schema.json","decision-receipt.schema.json","authority-grant.schema.json"]:
        jsonschema.Draft202012Validator.check_schema(load(schema_name))
    event_validator=jsonschema.Draft202012Validator(load("temporal-event.schema.json"))
    legacy=validate_event_file(EXAMPLES/"demo_run.events.jsonl",event_validator)
    multi=validate_event_file(EXAMPLES/"multi_agent_branch_join.events.jsonl",event_validator)
    machine=analyze_events(multi,weight_contract="machine_runtime_ms")
    ce=load_jsonl(EXAMPLES/"multi_agent_branch_join.cloudevents.jsonl"); assert [from_cloudevent(x) for x in ce]==multi
    spans=json.loads((EXAMPLES/"multi_agent_branch_join.otel_spans.json").read_text()); join={s["event_id"]:s for s in spans}["evt_008"]; assert len(join["links"])==3
    raw=read_jsonl_record_bytes(EXAMPLES/"multi_agent_branch_join.events.jsonl"); chain,anchor=seal_records(raw); assert verify_records(raw,chain,anchor)["valid"] is True
    approval=validate_file(EXAMPLES/"governance_approval_request.json","approval-request.schema.json"); decision=validate_file(EXAMPLES/"governance_decision_receipt.json","decision-receipt.schema.json"); grant=validate_file(EXAMPLES/"governance_authority_grant.json","authority-grant.schema.json")
    governance_events=validate_event_file(EXAMPLES/"governance_checkpoint.events.jsonl",event_validator); assert [e["event_type"] for e in governance_events]==["human.checkpoint.requested","run.suspended","human.checkpoint.resolved","authority.checked","run.resumed"]
    resume=evaluate_resume_eligibility(approval,decision,grant,action="publish",target=approval["target"],at="2026-08-20T08:11:00+00:00"); block=evaluate_resume_eligibility(approval,decision,grant,action="delete",target=approval["target"],at="2026-08-20T08:11:00+00:00"); assert resume["eligible"] is True and block["reasons"]==["scope_mismatch"]
    print("ITR/ATL v0.2.3 governance core pack: PASS"); print("ITR/ATL v0.2.2 ledger integrity pack: PASS"); print("ITR/ATL v0.2.1 observability pack: PASS"); print(f"legacy_events={len(legacy)}"); print(f"multi_agent_events={len(multi)}"); print(f"cloudevents_roundtrip={len(ce)}"); print(f"otel_spans={len(spans)}"); print(f"join_links={len(join['links'])}"); print(f"integrity_records={len(chain)}"); print(f"governance_events={len(governance_events)}"); print(f"governance_resume_eligible={resume['eligible']}"); print(f"governance_scope_block={block['reasons'][0]}"); print(f"machine_work={machine['work']}"); print(f"machine_depth={machine['depth']}"); print(f"poset_width={machine['poset_width']}")
if __name__=="__main__": main()

#!/usr/bin/env python3
from pathlib import Path
import json
import sys

try:
    import jsonschema
except Exception as exc:
    print("ERROR: jsonschema package is required:", exc)
    raise SystemExit(2)

BASE = Path(__file__).resolve().parents[1]
SCHEMAS = BASE / "schemas"
EXAMPLES = BASE / "examples"
SRC = BASE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctcl_itr.interop.cloudevents import from_cloudevent, to_cloudevent
from ctcl_itr.interop.opentelemetry import project_events
from ctcl_itr.integrity import read_jsonl_record_bytes, seal_records, verify_records
from ctcl_itr.topology import analyze_events


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def validate_file(instance_path, schema_name):
    schema = load(schema_name)
    instance = json.loads(Path(instance_path).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(instance)
    return instance


def validate_event_file(path, validator):
    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            validator.validate(obj)
            events.append(obj)
    return events


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    validate_file(EXAMPLES / "demo_intent.json", "intent.schema.json")
    validate_file(EXAMPLES / "demo_run.json", "run.schema.json")
    validate_file(EXAMPLES / "demo_checkpoint.json", "checkpoint.schema.json")
    validate_file(EXAMPLES / "demo_commit_receipt.json", "commit-receipt.schema.json")
    validate_file(EXAMPLES / "demo_run.summary.json", "run-summary.schema.json")

    for schema_name in [
        "intent.schema.json",
        "run.schema.json",
        "checkpoint.schema.json",
        "commit-receipt.schema.json",
        "run-summary.schema.json",
        "temporal-event.schema.json",
        "integrity-record.schema.json",
        "ledger-anchor.schema.json",
    ]:
        jsonschema.Draft202012Validator.check_schema(load(schema_name))

    event_schema = load("temporal-event.schema.json")
    validator = jsonschema.Draft202012Validator(event_schema)

    events = validate_event_file(EXAMPLES / "demo_run.events.jsonl", validator)
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids)), "duplicate event_id"
    seq = [e["ledger_seq"] for e in events]
    assert seq == list(range(1, len(events) + 1)), "ledger_seq must be contiguous in demo"
    seen = set()
    for e in events:
        for parent in e["causal_parent_ids"]:
            assert parent in seen, f"causal parent {parent} must precede event {e['event_id']} in demo"
        seen.add(e["event_id"])
    types = [e["event_type"] for e in events]
    assert "validation.completed" in types
    assert "human.checkpoint.resolved" in types
    assert types.index("human.checkpoint.resolved") < types.index("commit.executed")
    assert types.index("validation.completed") < types.index("run.succeeded")

    multi_path = EXAMPLES / "multi_agent_branch_join.events.jsonl"
    multi_events = validate_event_file(multi_path, validator)
    machine = analyze_events(multi_events, weight_contract="machine_runtime_ms")
    unit = analyze_events(multi_events, weight_contract="unit")
    assert machine["work"] == 1850.0
    assert machine["depth"] == 1100.0
    assert machine["poset_width"] == 3
    assert machine["branch_nodes"] == ["evt_004"]
    assert machine["join_nodes"] == ["evt_008"]
    assert unit["poset_width"] == 3

    expected_cloudevents = [to_cloudevent(event) for event in multi_events]
    stored_cloudevents = load_jsonl(EXAMPLES / "multi_agent_branch_join.cloudevents.jsonl")
    assert stored_cloudevents == expected_cloudevents, "CloudEvents reference export is stale"
    roundtrip = [from_cloudevent(envelope) for envelope in stored_cloudevents]
    assert roundtrip == multi_events, "CloudEvents round-trip must preserve ATL events"

    expected_spans = project_events(multi_events)
    stored_spans = json.loads((EXAMPLES / "multi_agent_branch_join.otel_spans.json").read_text(encoding="utf-8"))
    assert stored_spans == expected_spans, "OpenTelemetry reference export is stale"
    spans_by_event = {span["event_id"]: span for span in stored_spans}
    join = spans_by_event["evt_008"]
    assert join["parent_span_id"] is None
    assert {link["event_id"] for link in join["links"]} == {"evt_005", "evt_006", "evt_007"}

    raw_records = read_jsonl_record_bytes(multi_path)
    expected_integrity, expected_anchor = seal_records(raw_records)
    stored_integrity = load_jsonl(EXAMPLES / "multi_agent_branch_join.integrity.jsonl")
    stored_anchor = json.loads((EXAMPLES / "multi_agent_branch_join.anchor.json").read_text(encoding="utf-8"))
    assert stored_integrity == expected_integrity, "integrity reference export is stale"
    assert stored_anchor == expected_anchor, "ledger anchor reference export is stale"

    integrity_schema = load("integrity-record.schema.json")
    integrity_validator = jsonschema.Draft202012Validator(integrity_schema)
    for item in stored_integrity:
        integrity_validator.validate(item)
    jsonschema.Draft202012Validator(load("ledger-anchor.schema.json")).validate(stored_anchor)

    integrity_report = verify_records(raw_records, stored_integrity, stored_anchor)
    assert integrity_report["valid"] is True
    assert integrity_report["anchor_checked"] is True

    tampered_records = list(raw_records)
    tampered_records[0] = tampered_records[0].replace(b'"status":"ok"', b'"status":"OK"', 1)
    tamper_report = verify_records(tampered_records, stored_integrity, stored_anchor)
    assert tamper_report["valid"] is False
    assert tamper_report["failure"]["code"] == "record_digest_mismatch"

    truncation_report = verify_records(raw_records[:-1], stored_integrity[:-1], stored_anchor)
    assert truncation_report["valid"] is False
    assert truncation_report["failure"]["code"] == "anchor_event_count_mismatch"

    print("ITR/ATL v0.2.2 ledger integrity pack: PASS")
    print("ITR/ATL v0.2.1 observability pack: PASS")
    print(f"legacy_events={len(events)}")
    print(f"multi_agent_events={len(multi_events)}")
    print(f"cloudevents_roundtrip={len(roundtrip)}")
    print(f"otel_spans={len(stored_spans)}")
    print(f"join_links={len(join['links'])}")
    print(f"integrity_records={len(stored_integrity)}")
    print(f"anchor_checked={integrity_report['anchor_checked']}")
    print(f"tamper_detection={tamper_report['failure']['code']}")
    print(f"truncation_detection={truncation_report['failure']['code']}")
    print(f"machine_work={machine['work']}")
    print(f"machine_depth={machine['depth']}")
    print(f"poset_width={machine['poset_width']}")


if __name__ == "__main__":
    main()

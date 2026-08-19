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

from ctcl_itr.topology import analyze_events, load_events


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

    print("ITR/ATL v0.2 topology pack: PASS")
    print(f"legacy_events={len(events)}")
    print(f"multi_agent_events={len(multi_events)}")
    print(f"machine_work={machine['work']}")
    print(f"machine_depth={machine['depth']}")
    print(f"poset_width={machine['poset_width']}")


if __name__ == "__main__":
    main()

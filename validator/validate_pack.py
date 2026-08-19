#!/usr/bin/env python3
from pathlib import Path
import json

try:
    import jsonschema
except Exception as exc:
    print("ERROR: jsonschema package is required:", exc)
    raise SystemExit(2)

BASE = Path(__file__).resolve().parents[1]
SCHEMAS = BASE / "schemas"
EXAMPLES = BASE / "examples"


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def validate_file(instance_path, schema_name):
    schema = load(schema_name)
    instance = json.loads(Path(instance_path).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(instance)
    return instance


def main():
    validate_file(EXAMPLES / "demo_intent.json", "intent.schema.json")
    validate_file(EXAMPLES / "demo_run.json", "run.schema.json")
    validate_file(EXAMPLES / "demo_checkpoint.json", "checkpoint.schema.json")
    validate_file(EXAMPLES / "demo_commit_receipt.json", "commit-receipt.schema.json")
    validate_file(EXAMPLES / "demo_run.summary.json", "run-summary.schema.json")

    event_schema = load("temporal-event.schema.json")
    validator = jsonschema.Draft202012Validator(event_schema)
    events = []
    for line in (EXAMPLES / "demo_run.events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            validator.validate(obj)
            events.append(obj)

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
    assert types.index("commit.confirmed") < types.index("run.succeeded")

    print("ITR/ATL v0.1 example pack: PASS")
    print(f"events={len(events)}")


if __name__ == "__main__":
    main()

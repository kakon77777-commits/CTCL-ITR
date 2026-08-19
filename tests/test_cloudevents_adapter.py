import copy
import json
from pathlib import Path

import pytest

from ctcl_itr.interop.cloudevents import CloudEventError, from_cloudevent, to_cloudevent


def _first_event():
    root = Path(__file__).resolve().parents[1]
    line = (root / "examples" / "multi_agent_branch_join.events.jsonl").read_text(encoding="utf-8").splitlines()[0]
    return json.loads(line)


def test_to_cloudevent_has_required_context_and_preserves_atl_event():
    event = _first_event()
    envelope = to_cloudevent(event)
    assert envelope["specversion"] == "1.0"
    assert envelope["id"] == event["event_id"]
    assert envelope["source"] == event["source"]
    assert envelope["type"] == f"org.evemiss.itr.{event['event_type']}"
    assert envelope["subject"] == event["subject"]
    assert envelope["time"] == event["occurred_at"]
    assert envelope["datacontenttype"] == "application/json"
    assert envelope["data"] == event


def test_cloudevent_round_trip_is_lossless():
    event = _first_event()
    assert from_cloudevent(to_cloudevent(event)) == event


def test_from_cloudevent_rejects_identity_mismatch():
    event = _first_event()
    envelope = to_cloudevent(event)
    envelope = copy.deepcopy(envelope)
    envelope["id"] = "evt_other"
    with pytest.raises(CloudEventError, match="id does not match"):
        from_cloudevent(envelope)


def test_cloudevent_dataschema_matches_canonical_temporal_event_schema_id():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "temporal-event.schema.json").read_text(encoding="utf-8"))
    envelope = to_cloudevent(_first_event())
    assert envelope["dataschema"] == schema["$id"]

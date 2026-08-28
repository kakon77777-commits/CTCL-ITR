"""CloudEvents 1.0 JSON-envelope projection for ATL TemporalEvents."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


CLOUDEVENTS_SPECVERSION = "1.0"
DEFAULT_TYPE_PREFIX = "org.evemiss.itr"
TEMPORAL_EVENT_DATASCHEMA = "https://evemisslab.example/schemas/itr/temporal-event-v0.1.json"


class CloudEventError(ValueError):
    """Raised when a CloudEvents envelope cannot be mapped to an ATL event."""


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CloudEventError(f"{field} must be a non-empty string")
    return value


def to_cloudevent(
    event: Mapping[str, Any],
    *,
    type_prefix: str = DEFAULT_TYPE_PREFIX,
    dataschema: str = TEMPORAL_EVENT_DATASCHEMA,
) -> dict[str, Any]:
    """Wrap an ATL event in a lossless CloudEvents 1.0 JSON envelope."""
    event_id = _nonempty_string(event.get("event_id"), "event_id")
    source = _nonempty_string(event.get("source"), "source")
    event_type = _nonempty_string(event.get("event_type"), "event_type")
    subject = _nonempty_string(event.get("subject"), "subject")
    occurred_at = _nonempty_string(event.get("occurred_at"), "occurred_at")
    prefix = _nonempty_string(type_prefix, "type_prefix").rstrip(".")
    schema_uri = _nonempty_string(dataschema, "dataschema")

    return {
        "specversion": CLOUDEVENTS_SPECVERSION,
        "id": event_id,
        "source": source,
        "type": f"{prefix}.{event_type}",
        "subject": subject,
        "time": occurred_at,
        "datacontenttype": "application/json",
        "dataschema": schema_uri,
        "data": deepcopy(dict(event)),
    }


def from_cloudevent(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Recover the canonical ATL event from a reference CloudEvents envelope."""
    specversion = _nonempty_string(envelope.get("specversion"), "specversion")
    if specversion != CLOUDEVENTS_SPECVERSION:
        raise CloudEventError(f"unsupported specversion: {specversion}")
    envelope_id = _nonempty_string(envelope.get("id"), "id")
    _nonempty_string(envelope.get("source"), "source")
    _nonempty_string(envelope.get("type"), "type")

    data = envelope.get("data")
    if not isinstance(data, Mapping):
        raise CloudEventError("data must contain an ATL event object")
    event = deepcopy(dict(data))
    event_id = event.get("event_id")
    if envelope_id != event_id:
        raise CloudEventError("CloudEvent id does not match ATL data.event_id")
    return event


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Project ATL JSONL events to CloudEvents 1.0 JSON envelopes.")
    parser.add_argument("path", help="Path to ATL JSONL events")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print one JSON array instead of JSONL")
    args = parser.parse_args(argv)

    events = [json.loads(line) for line in Path(args.path).read_text(encoding="utf-8").splitlines() if line.strip()]
    projected = [to_cloudevent(event) for event in events]
    if args.pretty:
        print(json.dumps(projected, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in projected:
            print(json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

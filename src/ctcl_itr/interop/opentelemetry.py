"""Deterministic OpenTelemetry-style span projection for ATL events.

This module deliberately does not depend on the OpenTelemetry SDK and does not
emit OTLP payloads. It produces a loss-conscious intermediate representation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from hashlib import sha256
from typing import Any


class OpenTelemetryProjectionError(ValueError):
    """Raised when ATL events cannot be projected consistently."""


def _stable_hex(value: str, length: int) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:length]


def _trace_id(event: Mapping[str, Any]) -> str:
    trace = event.get("trace") or {}
    value = trace.get("trace_id") if isinstance(trace, Mapping) else None
    if isinstance(value, str) and len(value) == 32:
        return value.lower()
    run_id = event.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise OpenTelemetryProjectionError("run_id must be a non-empty string")
    return _stable_hex(run_id, 32)


def _span_id(event: Mapping[str, Any]) -> str:
    trace = event.get("trace") or {}
    value = trace.get("span_id") if isinstance(trace, Mapping) else None
    if isinstance(value, str) and len(value) == 16:
        return value.lower()
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        raise OpenTelemetryProjectionError("event_id must be a non-empty string")
    return _stable_hex(event_id, 16)


def _operation(event: Mapping[str, Any]) -> str | None:
    event_type = str(event.get("event_type") or "")
    actor = event.get("actor") or {}
    actor_type = actor.get("actor_type") if isinstance(actor, Mapping) else None
    if event_type.startswith("plan."):
        return "plan"
    if event_type.startswith("tool.") or actor_type == "tool":
        return "execute_tool"
    if actor_type in {"agent", "subagent"}:
        return "invoke_agent"
    return None


def _span_name(event: Mapping[str, Any], operation: str | None) -> str:
    actor = event.get("actor") or {}
    actor_id = actor.get("actor_id") if isinstance(actor, Mapping) else None
    if operation == "plan":
        return "plan"
    if operation == "execute_tool":
        return f"execute_tool {actor_id}" if actor_id else "execute_tool"
    if operation == "invoke_agent":
        return f"invoke_agent {actor_id}" if actor_id else "invoke_agent"
    return str(event.get("event_type") or "itr_event")


def _status(event: Mapping[str, Any]) -> str:
    raw = str(event.get("status") or "").lower()
    if raw in {"fail", "failed", "error", "denied", "blocked", "timeout"}:
        return "ERROR"
    if raw in {"ok", "pass", "approved", "allow", "confirmed", "succeeded", "executed"}:
        return "OK"
    return "UNSET"


def _attributes(event: Mapping[str, Any], operation: str | None) -> dict[str, Any]:
    actor = event.get("actor") or {}
    budget = event.get("budget") or {}
    attrs: dict[str, Any] = {
        "itr.event.id": event.get("event_id"),
        "itr.event.type": event.get("event_type"),
        "itr.run.id": event.get("run_id"),
        "itr.ledger.seq": event.get("ledger_seq"),
        "itr.causal.parent.count": len(event.get("causal_parent_ids") or []),
    }
    if isinstance(actor, Mapping):
        if actor.get("actor_id") is not None:
            attrs["itr.actor.id"] = actor.get("actor_id")
        if actor.get("actor_type") is not None:
            attrs["itr.actor.type"] = actor.get("actor_type")
    for source_key, target_key in (
        ("branch_id", "itr.branch.id"),
        ("parallel_group", "itr.parallel.group"),
        ("join_semantics", "itr.join.semantics"),
        ("join_quorum", "itr.join.quorum"),
    ):
        if event.get(source_key) is not None:
            attrs[target_key] = event.get(source_key)

    if isinstance(budget, Mapping):
        if budget.get("machine_runtime_ms") is not None:
            attrs["itr.machine_runtime_ms"] = budget.get("machine_runtime_ms")
        if budget.get("token_in") is not None:
            attrs["gen_ai.usage.input_tokens"] = budget.get("token_in")
        if budget.get("token_out") is not None:
            attrs["gen_ai.usage.output_tokens"] = budget.get("token_out")
        if budget.get("reasoning_tokens") is not None:
            attrs["gen_ai.usage.reasoning.output_tokens"] = budget.get("reasoning_tokens")

    if operation is not None:
        attrs["gen_ai.operation.name"] = operation
        actor_id = actor.get("actor_id") if isinstance(actor, Mapping) else None
        if operation == "invoke_agent" and actor_id:
            attrs["gen_ai.agent.name"] = actor_id
        if operation == "execute_tool" and actor_id:
            attrs["gen_ai.tool.name"] = actor_id
    return attrs


def project_event(event: Mapping[str, Any], event_index: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        raise OpenTelemetryProjectionError("event_id must be a non-empty string")
    parents = event.get("causal_parent_ids") or []
    if not isinstance(parents, list):
        raise OpenTelemetryProjectionError(f"causal_parent_ids must be an array for {event_id}")
    missing = [parent for parent in parents if parent not in event_index]
    if missing:
        raise OpenTelemetryProjectionError(f"unknown causal parent {missing[0]} for {event_id}")

    trace_id = _trace_id(event)
    span_id = _span_id(event)
    parent_span_id = None
    links: list[dict[str, str]] = []
    if len(parents) == 1:
        parent_span_id = _span_id(event_index[parents[0]])
    elif len(parents) > 1:
        for parent_id in parents:
            parent = event_index[parent_id]
            links.append({
                "event_id": parent_id,
                "trace_id": _trace_id(parent),
                "span_id": _span_id(parent),
            })

    operation = _operation(event)
    occurred_at = event.get("occurred_at")
    return {
        "event_id": event_id,
        "name": _span_name(event, operation),
        "span_kind": "INTERNAL",
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "links": links,
        "start_time": occurred_at,
        "end_time": occurred_at,
        "status": _status(event),
        "attributes": _attributes(event, operation),
    }


def project_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    event_list = list(events)
    index: dict[str, Mapping[str, Any]] = {}
    for event in event_list:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise OpenTelemetryProjectionError("event_id must be a non-empty string")
        if event_id in index:
            raise OpenTelemetryProjectionError(f"duplicate event_id: {event_id}")
        index[event_id] = event
    return [project_event(event, index) for event in event_list]


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Project ATL JSONL events to OpenTelemetry-style span records.")
    parser.add_argument("path", help="Path to ATL JSONL events")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)

    events = [json.loads(line) for line in Path(args.path).read_text(encoding="utf-8").splitlines() if line.strip()]
    projected = project_events(events)
    print(json.dumps(projected, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

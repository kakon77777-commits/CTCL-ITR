import json
from pathlib import Path

from ctcl_itr.interop.opentelemetry import project_events


def _events():
    root = Path(__file__).resolve().parents[1]
    return [json.loads(line) for line in (root / "examples" / "multi_agent_branch_join.events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def test_plan_event_maps_to_genai_plan_operation():
    spans = {span["event_id"]: span for span in project_events(_events())}
    assert spans["evt_002"]["attributes"]["gen_ai.operation.name"] == "plan"


def test_agent_action_maps_to_invoke_agent_and_usage_attributes():
    spans = {span["event_id"]: span for span in project_events(_events())}
    span = spans["evt_006"]
    assert span["attributes"]["gen_ai.operation.name"] == "invoke_agent"
    assert span["attributes"]["gen_ai.agent.name"] == "agent:b"
    assert span["attributes"]["itr.machine_runtime_ms"] == 700


def test_single_parent_becomes_parent_span_id():
    spans = {span["event_id"]: span for span in project_events(_events())}
    assert spans["evt_005"]["parent_span_id"] == spans["evt_004"]["span_id"]
    assert spans["evt_005"]["links"] == []


def test_multi_parent_join_uses_links_without_privileged_parent():
    spans = {span["event_id"]: span for span in project_events(_events())}
    join = spans["evt_008"]
    assert join["parent_span_id"] is None
    assert {link["event_id"] for link in join["links"]} == {"evt_005", "evt_006", "evt_007"}
    assert {link["span_id"] for link in join["links"]} == {
        spans["evt_005"]["span_id"], spans["evt_006"]["span_id"], spans["evt_007"]["span_id"]
    }


def test_projection_ids_are_deterministic():
    first = project_events(_events())
    second = project_events(_events())
    assert [(x["trace_id"], x["span_id"]) for x in first] == [(x["trace_id"], x["span_id"]) for x in second]


def test_tool_event_maps_to_execute_tool_and_token_usage_attributes():
    events = _events()
    tool_event = dict(events[5])
    tool_event["event_id"] = "evt_tool"
    tool_event["ledger_seq"] = 99
    tool_event["event_type"] = "tool.completed"
    tool_event["causal_parent_ids"] = []
    tool_event["actor"] = {"actor_id": "web.search", "actor_type": "tool"}
    tool_event["budget"] = {
        "machine_runtime_ms": 50,
        "token_in": 120,
        "token_out": 30,
        "reasoning_tokens": 10,
    }
    span = project_events([tool_event])[0]
    assert span["attributes"]["gen_ai.operation.name"] == "execute_tool"
    assert span["attributes"]["gen_ai.tool.name"] == "web.search"
    assert span["attributes"]["gen_ai.usage.input_tokens"] == 120
    assert span["attributes"]["gen_ai.usage.output_tokens"] == 30
    assert span["attributes"]["gen_ai.usage.reasoning.output_tokens"] == 10

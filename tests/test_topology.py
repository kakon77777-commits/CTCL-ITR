import json
from pathlib import Path

import pytest

from ctcl_itr.topology import TopologyError, analyze_events, load_events


def event(seq, event_id, parents=(), runtime_ms=0):
    return {
        "schema_version": "0.1",
        "event_id": event_id,
        "ledger_seq": seq,
        "event_type": "action.completed",
        "run_id": "run:test",
        "causal_parent_ids": list(parents),
        "budget": {"machine_runtime_ms": runtime_ms},
    }


def test_branch_join_unit_metrics_and_critical_path_are_deterministic():
    events = [
        event(1, "evt_root"),
        event(2, "evt_fork", ["evt_root"]),
        event(3, "evt_a", ["evt_fork"]),
        event(4, "evt_b", ["evt_fork"]),
        event(5, "evt_c", ["evt_fork"]),
        event(6, "evt_join", ["evt_a", "evt_b", "evt_c"]),
        event(7, "evt_end", ["evt_join"]),
    ]
    result = analyze_events(events, weight_contract="unit")
    assert result["event_count"] == 7
    assert result["edge_count"] == 8
    assert result["roots"] == ["evt_root"]
    assert result["leaves"] == ["evt_end"]
    assert result["branch_nodes"] == ["evt_fork"]
    assert result["join_nodes"] == ["evt_join"]
    assert result["work"] == 7
    assert result["depth"] == 5
    assert result["critical_path"] == ["evt_root", "evt_fork", "evt_a", "evt_join", "evt_end"]
    assert result["structural_parallelism"] == pytest.approx(7 / 5)


def test_machine_runtime_weight_selects_slowest_causal_branch():
    events = [
        event(1, "evt_root"),
        event(2, "evt_a", ["evt_root"], runtime_ms=300),
        event(3, "evt_b", ["evt_root"], runtime_ms=700),
        event(4, "evt_c", ["evt_root"], runtime_ms=450),
        event(5, "evt_join", ["evt_a", "evt_b", "evt_c"], runtime_ms=200),
        event(6, "evt_validate", ["evt_join"], runtime_ms=100),
        event(7, "evt_commit", ["evt_validate"], runtime_ms=100),
    ]
    result = analyze_events(events, weight_contract="machine_runtime_ms")
    assert result["work"] == 1850
    assert result["depth"] == 1100
    assert result["critical_path"] == ["evt_root", "evt_b", "evt_join", "evt_validate", "evt_commit"]


def test_unknown_parent_is_rejected():
    with pytest.raises(TopologyError, match="unknown causal parent"):
        analyze_events([event(1, "evt_a", ["evt_missing"])])


def test_cycle_is_rejected():
    events = [event(1, "evt_a", ["evt_b"]), event(2, "evt_b", ["evt_a"])]
    with pytest.raises(TopologyError, match="cycle"):
        analyze_events(events)


def test_duplicate_event_id_is_rejected():
    events = [event(1, "evt_a"), event(2, "evt_a")]
    with pytest.raises(TopologyError, match="duplicate event_id"):
        analyze_events(events)


def test_loader_reads_jsonl(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    rows = [event(1, "evt_a"), event(2, "evt_b", ["evt_a"])]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    assert load_events(path) == rows


def test_poset_width_is_one_for_chain():
    events = [
        event(1, "evt_1"),
        event(2, "evt_2", ["evt_1"]),
        event(3, "evt_3", ["evt_2"]),
    ]
    assert analyze_events(events)["poset_width"] == 1


def test_poset_width_is_three_for_three_incomparable_branches():
    events = [
        event(1, "evt_root"),
        event(2, "evt_a", ["evt_root"]),
        event(3, "evt_b", ["evt_root"]),
        event(4, "evt_c", ["evt_root"]),
        event(5, "evt_join", ["evt_a", "evt_b", "evt_c"]),
    ]
    assert analyze_events(events)["poset_width"] == 3


def test_reference_multi_agent_demo_has_expected_topology_metrics():
    demo_path = Path(__file__).resolve().parents[1] / "examples" / "multi_agent_branch_join.events.jsonl"
    events = load_events(demo_path)
    result = analyze_events(events, weight_contract="machine_runtime_ms")
    assert result["work"] == 1850
    assert result["depth"] == 1100
    assert result["poset_width"] == 3
    assert result["branch_nodes"] == ["evt_004"]
    assert result["join_nodes"] == ["evt_008"]
    assert "evt_006" in result["critical_path"]


def test_cli_emits_json_analysis_for_reference_demo():
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    demo = root / "examples" / "multi_agent_branch_join.events.jsonl"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "ctcl_itr.topology", str(demo), "--weight", "machine_runtime_ms"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "RuntimeWarning" not in completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["depth"] == 1100
    assert payload["poset_width"] == 3

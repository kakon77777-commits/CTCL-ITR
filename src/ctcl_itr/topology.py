"""Causal topology analysis for CTCL-ITR Agent Temporal Ledger events."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Iterable


class TopologyError(ValueError):
    """Raised when an ATL causal graph is malformed."""


SUPPORTED_WEIGHT_CONTRACTS = {"unit", "machine_runtime_ms"}


def load_events(path: str | Path) -> list[dict[str, Any]]:
    """Load ATL events from newline-delimited JSON."""
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TopologyError(f"invalid JSON at line {line_no}: {exc.msg}") from exc
        if not isinstance(obj, dict):
            raise TopologyError(f"event at line {line_no} is not an object")
        rows.append(obj)
    return rows


def _event_weight(event: dict[str, Any], weight_contract: str) -> float:
    if weight_contract == "unit":
        return 1.0
    if weight_contract == "machine_runtime_ms":
        value = (event.get("budget") or {}).get("machine_runtime_ms", 0)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TopologyError(f"invalid machine_runtime_ms for {event.get('event_id')}")
        if value < 0:
            raise TopologyError(f"negative machine_runtime_ms for {event.get('event_id')}")
        return float(value)
    raise TopologyError(f"unsupported weight contract: {weight_contract}")


def _build_graph(events: Iterable[dict[str, Any]]):
    by_id: dict[str, dict[str, Any]] = {}
    by_seq: dict[int, str] = {}
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise TopologyError("event_id must be a non-empty string")
        if event_id in by_id:
            raise TopologyError(f"duplicate event_id: {event_id}")
        ledger_seq = event.get("ledger_seq")
        if not isinstance(ledger_seq, int) or isinstance(ledger_seq, bool):
            raise TopologyError(f"ledger_seq must be an integer for {event_id}")
        if ledger_seq in by_seq:
            raise TopologyError(f"duplicate ledger_seq: {ledger_seq}")
        by_id[event_id] = event
        by_seq[ledger_seq] = event_id

    parents: dict[str, list[str]] = {event_id: [] for event_id in by_id}
    children: dict[str, list[str]] = {event_id: [] for event_id in by_id}

    for event_id, event in by_id.items():
        raw_parents = event.get("causal_parent_ids", [])
        if not isinstance(raw_parents, list):
            raise TopologyError(f"causal_parent_ids must be an array for {event_id}")
        for parent in raw_parents:
            if parent == event_id:
                raise TopologyError(f"self-parent edge for {event_id}")
            if parent not in by_id:
                raise TopologyError(f"unknown causal parent {parent} for {event_id}")
            parents[event_id].append(parent)
            children[parent].append(event_id)

    key = lambda node_id: (by_id[node_id]["ledger_seq"], node_id)
    for node_id in by_id:
        parents[node_id].sort(key=key)
        children[node_id].sort(key=key)

    indegree = {node_id: len(parents[node_id]) for node_id in by_id}
    ready = sorted([node_id for node_id, deg in indegree.items() if deg == 0], key=key)
    order: list[str] = []
    while ready:
        node_id = ready.pop(0)
        order.append(node_id)
        for child in children[node_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort(key=key)
    if len(order) != len(by_id):
        raise TopologyError("cycle detected in causal graph")

    return by_id, parents, children, order, key


def _poset_width(order, children, key):
    """Return exact finite-poset width via Dilworth's theorem.

    Reachability induces the strict partial-order comparability graph. The
    minimum chain decomposition size equals |V| minus the maximum matching in
    the corresponding bipartite graph.
    """
    reachable = {node_id: set() for node_id in order}
    for node_id in reversed(order):
        for child in children[node_id]:
            reachable[node_id].add(child)
            reachable[node_id].update(reachable[child])

    adjacency = {
        node_id: sorted(reachable[node_id], key=key)
        for node_id in order
    }
    matched_right = {}

    def augment(left, seen):
        for right in adjacency[left]:
            if right in seen:
                continue
            seen.add(right)
            previous = matched_right.get(right)
            if previous is None or augment(previous, seen):
                matched_right[right] = left
                return True
        return False

    matching = 0
    for left in sorted(order, key=key):
        if augment(left, set()):
            matching += 1
    return len(order) - matching


def analyze_events(events: Iterable[dict[str, Any]], weight_contract: str = "unit") -> dict[str, Any]:
    """Analyze an ATL causal DAG without mutating the input events."""
    if weight_contract not in SUPPORTED_WEIGHT_CONTRACTS:
        raise TopologyError(f"unsupported weight contract: {weight_contract}")

    event_list = list(events)
    by_id, parents, children, order, key = _build_graph(event_list)
    weights = {node_id: _event_weight(by_id[node_id], weight_contract) for node_id in by_id}

    distance: dict[str, float] = {}
    predecessor: dict[str, str | None] = {}
    path_key: dict[str, tuple[tuple[int, str], ...]] = {}

    for node_id in order:
        if not parents[node_id]:
            distance[node_id] = weights[node_id]
            predecessor[node_id] = None
            path_key[node_id] = (key(node_id),)
            continue

        candidates = []
        for parent in parents[node_id]:
            candidate_distance = distance[parent] + weights[node_id]
            candidate_key = path_key[parent] + (key(node_id),)
            candidates.append((candidate_distance, candidate_key, parent))
        # Prefer larger distance; for ties choose lexicographically smallest path by ledger sequence / id.
        best_distance = max(item[0] for item in candidates)
        tied = [item for item in candidates if item[0] == best_distance]
        _, best_key, best_parent = min(tied, key=lambda item: item[1])
        distance[node_id] = best_distance
        predecessor[node_id] = best_parent
        path_key[node_id] = best_key

    if order:
        depth = max(distance.values())
        terminal_candidates = [node_id for node_id in order if distance[node_id] == depth]
        terminal = min(terminal_candidates, key=lambda node_id: path_key[node_id])
        critical_path: list[str] = []
        cursor: str | None = terminal
        while cursor is not None:
            critical_path.append(cursor)
            cursor = predecessor[cursor]
        critical_path.reverse()
    else:
        depth = 0.0
        critical_path = []

    work = sum(weights.values())
    roots = sorted([node_id for node_id in by_id if not parents[node_id]], key=key)
    leaves = sorted([node_id for node_id in by_id if not children[node_id]], key=key)
    branch_nodes = sorted([node_id for node_id in by_id if len(children[node_id]) > 1], key=key)
    join_nodes = sorted([node_id for node_id in by_id if len(parents[node_id]) > 1], key=key)
    poset_width = _poset_width(order, children, key)

    return {
        "weight_contract": weight_contract,
        "event_count": len(by_id),
        "edge_count": sum(len(v) for v in parents.values()),
        "roots": roots,
        "leaves": leaves,
        "branch_nodes": branch_nodes,
        "join_nodes": join_nodes,
        "work": work,
        "depth": depth,
        "critical_path": critical_path,
        "structural_parallelism": (work / depth) if depth > 0 else None,
        "poset_width": poset_width,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Analyze a CTCL-ITR ATL causal event ledger.")
    parser.add_argument("path", help="Path to ATL JSONL events")
    parser.add_argument(
        "--weight",
        default="unit",
        choices=sorted(SUPPORTED_WEIGHT_CONTRACTS),
        help="Node weight contract",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)

    try:
        result = analyze_events(load_events(args.path), weight_contract=args.weight)
    except TopologyError as exc:
        parser.exit(2, f"topology error: {exc}\n")

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

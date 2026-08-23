"""Multi-snapshot aggregation for CTCL-ITR v0.2.14 geometry trajectories."""
from __future__ import annotations

from typing import Any

from .calibration_geometry_drift_motion import _gradient_key
from .calibration_geometry_trajectory_common import _direction_reversal_count, _elapsed_days


def _weight_key(weights: dict[str, float], families: list[str]) -> str:
    return "|".join(f"{f}={float(weights[f]):.12g}" for f in families)


def _supported_nodes(geometry: dict[str, Any], subject: str) -> dict[str, dict[str, Any]]:
    return {x["cell_key"]: x for x in geometry["subjects"][subject]["supported_graph"]["nodes"]}


def _support_trajectory(geometries, subject):
    counts = [len(_supported_nodes(g, subject)) for g in geometries]
    changes = [b - a for a, b in zip(counts, counts[1:])]
    directions = ["expansion" if x > 0 else "contraction" if x < 0 else "flat" for x in changes]
    return {
        "supported_cell_counts": counts,
        "step_changes": changes,
        "step_directions": directions,
        "direction_reversal_count": _direction_reversal_count([float(x) for x in changes]),
        "net_supported_cell_change": counts[-1] - counts[0],
        "minimum_supported_cell_count": min(counts),
        "maximum_supported_cell_count": max(counts),
    }


class _UnionFind:
    def __init__(self, nodes):
        self.parent = {x: x for x in nodes}
    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _boundary_points(geometry, subject, kind, families):
    name = f"{kind}_stability_zero_crossings"
    out = {}
    for point in geometry["subjects"][subject]["boundaries"].get(name, []):
        weights = {f: float(point["estimated_reference_family_weights"][f]) for f in families}
        out[_weight_key(weights, families)] = weights
    return out


def _boundary_trajectories(geometries, pairwise, subject, kind, families, observations, times):
    nodes = {}
    for i, geometry in enumerate(geometries):
        for key, weights in _boundary_points(geometry, subject, kind, families).items():
            nodes[(i, key)] = weights
    uf = _UnionFind(nodes)
    matched_edges = []
    for i, drift in enumerate(pairwise):
        motion = drift["subjects"][subject]["stability_boundary_motion"][kind]
        for match in motion["matches"]:
            ak = _weight_key(match["base_weights"], families)
            bk = _weight_key(match["current_weights"], families)
            a, b = (i, ak), (i + 1, bk)
            if a in nodes and b in nodes:
                uf.union(a, b)
                matched_edges.append((a, b, match))
    groups = {}
    for node in nodes:
        groups.setdefault(uf.find(node), []).append(node)
    lineages = []
    for group_nodes in groups.values():
        group_nodes.sort(key=lambda x: (x[0], x[1]))
        group_set = set(group_nodes)
        points = [
            {
                "observation_index": i,
                "observation_id": observations[i]["observation_id"],
                "observed_at": observations[i]["observed_at"],
                "reference_family_weights": nodes[(i, key)],
            }
            for i, key in group_nodes
        ]
        velocities = []
        for a, b, match in matched_edges:
            if a not in group_set or b not in group_set:
                continue
            days = _elapsed_days(times[a[0]], times[b[0]])
            velocities.append({
                "from_observation_index": a[0],
                "to_observation_index": b[0],
                "from_observation_id": observations[a[0]]["observation_id"],
                "to_observation_id": observations[b[0]]["observation_id"],
                "elapsed_days": days,
                "l1_displacement": float(match["l1_displacement"]),
                "l1_speed_per_day": float(match["l1_displacement"]) / days,
                "signed_family_velocity_per_day": {
                    f: float(match["signed_family_displacement"][f]) / days for f in families
                },
            })
        velocities.sort(key=lambda x: x["from_observation_index"])
        accelerations = []
        for v0, v1 in zip(velocities, velocities[1:]):
            if v0["to_observation_index"] != v1["from_observation_index"]:
                continue
            dt = (v0["elapsed_days"] + v1["elapsed_days"]) / 2.0
            accelerations.append({
                "at_observation_index": v0["to_observation_index"],
                "at_observation_id": v0["to_observation_id"],
                "effective_elapsed_days": dt,
                "signed_family_acceleration_per_day2": {
                    f: (v1["signed_family_velocity_per_day"][f] - v0["signed_family_velocity_per_day"][f]) / dt
                    for f in families
                },
                "l1_speed_change_per_day2": (v1["l1_speed_per_day"] - v0["l1_speed_per_day"]) / dt,
            })
        obs_indices = sorted({x[0] for x in group_nodes})
        first_i, last_i = obs_indices[0], obs_indices[-1]
        first_weights = points[0]["reference_family_weights"]
        last_weights = points[-1]["reference_family_weights"]
        lineages.append({
            "first_observation_index": first_i,
            "last_observation_index": last_i,
            "observation_count": len(obs_indices),
            "lifespan_days": _elapsed_days(times[first_i], times[last_i]),
            "spans_all_observations": obs_indices == list(range(len(observations))),
            "points": points,
            "velocities": velocities,
            "accelerations": accelerations,
            "velocity_direction_reversal_count_by_family": {
                f: _direction_reversal_count([v["signed_family_velocity_per_day"][f] for v in velocities])
                for f in families
            },
            "total_path_l1": sum(v["l1_displacement"] for v in velocities),
            "net_signed_displacement": {f: last_weights[f] - first_weights[f] for f in families},
        })
    lineages.sort(key=lambda x: (x["first_observation_index"], x["last_observation_index"], str(x["points"])))
    return {
        "matching_is_descriptive_not_identity": True,
        "lineage_count": len(lineages),
        "spans_all_observations_count": sum(1 for x in lineages if x["spans_all_observations"]),
        "lineages": lineages,
    }


def _components(geometry, subject):
    return geometry["subjects"][subject]["supported_graph"].get("connected_components", [])


def _component_trajectories(geometries, pairwise, subject, observations, times):
    nodes = {}
    for i, geometry in enumerate(geometries):
        for comp in _components(geometry, subject):
            nodes[(i, str(comp["component_id"]))] = sorted(str(x) for x in comp.get("members", []))
    uf = _UnionFind(nodes)
    for i, drift in enumerate(pairwise):
        for link in drift["subjects"][subject]["component_motion"]["overlap_links"]:
            a = (i, str(link["base_component_id"])); b = (i + 1, str(link["current_component_id"]))
            if a in nodes and b in nodes: uf.union(a, b)
    groups = {}
    for node in nodes: groups.setdefault(uf.find(node), []).append(node)
    lineages = []
    for group_nodes in groups.values():
        group_nodes.sort(); group_set=set(group_nodes)
        obs_indices=sorted({x[0] for x in group_nodes}); first_i,last_i=obs_indices[0],obs_indices[-1]
        split=merge=0
        for i, drift in enumerate(pairwise):
            cm=drift["subjects"][subject]["component_motion"]
            for event in cm["split_events"]:
                if (i,str(event["base_component_id"])) in group_set: split += 1
            for event in cm["merge_events"]:
                if (i+1,str(event["current_component_id"])) in group_set: merge += 1
        lineages.append({
            "first_observation_index": first_i,
            "last_observation_index": last_i,
            "observation_count": len(obs_indices),
            "lifespan_days": _elapsed_days(times[first_i], times[last_i]),
            "spans_all_observations": obs_indices == list(range(len(observations))),
            "split_event_count": split,
            "merge_event_count": merge,
            "nodes": [
                {"observation_index":i,"observation_id":observations[i]["observation_id"],"component_id":cid,"members":nodes[(i,cid)]}
                for i,cid in group_nodes
            ],
        })
    lineages.sort(key=lambda x:(x["first_observation_index"],x["last_observation_index"],str(x["nodes"])))
    return {
        "lineage_identity_is_descriptive": True,
        "lineage_count": len(lineages),
        "spans_all_observations_count": sum(1 for x in lineages if x["spans_all_observations"]),
        "maximum_lifespan_days": max((x["lifespan_days"] for x in lineages), default=0.0),
        "lineages": lineages,
    }


def _max_run(values, target):
    best=cur=0
    for value in values:
        if value==target: cur+=1; best=max(best,cur)
        else: cur=0
    return best


def _support_excursion(statuses):
    support=[x!="unsupported" for x in statuses]
    return any(support[i-1] == support[i+1] != support[i] for i in range(1,len(support)-1))


def _sign_persistence(geometries, subject):
    maps=[_supported_nodes(g,subject) for g in geometries]
    keys=sorted(set().union(*(set(m) for m in maps)))
    trajectories=[]
    for key in keys:
        statuses=[m[key]["band_sign_class"] if key in m else "unsupported" for m in maps]
        trajectories.append({
            "cell_key": key,
            "status_sequence": statuses,
            "supported_observation_count": sum(1 for x in statuses if x!="unsupported"),
            "positive_observation_count": statuses.count("positive_band"),
            "supported_all_observations": all(x!="unsupported" for x in statuses),
            "positive_all_observations": all(x=="positive_band" for x in statuses),
            "status_change_count": sum(1 for a,b in zip(statuses,statuses[1:]) if a!=b),
            "support_excursion": _support_excursion(statuses),
            "maximum_consecutive_positive_band_run": _max_run(statuses,"positive_band"),
        })
    return {
        "union_cell_count": len(keys),
        "supported_all_observations_count": sum(1 for x in trajectories if x["supported_all_observations"]),
        "positive_all_observations_count": sum(1 for x in trajectories if x["positive_all_observations"]),
        "status_change_cell_count": sum(1 for x in trajectories if x["status_change_count"]),
        "support_excursion_cell_count": sum(1 for x in trajectories if x["support_excursion"]),
        "cell_trajectories": trajectories,
    }


def _gradient_map(geometry, subject):
    result={}
    for edge in geometry["subjects"][subject].get("local_gradients",[]):
        result[_gradient_key(edge)] = edge
    return result


def _gradient_trajectories(geometries, subject):
    maps=[_gradient_map(g,subject) for g in geometries]
    keys=sorted(set().union(*(set(m) for m in maps)))
    trajectories=[]
    all_abs=[]
    for key in keys:
        presence=[key in m for m in maps]
        slopes=[float(m[key]["point_estimate_slope"]) if key in m else None for m in maps]
        changes=[]
        for i in range(len(slopes)-1):
            if slopes[i] is not None and slopes[i+1] is not None:
                changes.append({"from_observation_index":i,"to_observation_index":i+1,"point_estimate_slope_change":slopes[i+1]-slopes[i]})
                all_abs.append(abs(slopes[i+1]-slopes[i]))
        trajectories.append({
            "edge_key": key,
            "presence_sequence": presence,
            "point_estimate_slope_sequence": slopes,
            "persistent_all_observations": all(presence),
            "presence_excursion": any(presence[i-1]==presence[i+1]!=presence[i] for i in range(1,len(presence)-1)),
            "step_changes": changes,
            "slope_change_direction_reversal_count": _direction_reversal_count([x["point_estimate_slope_change"] for x in changes]),
        })
    return {
        "edge_trajectory_count": len(trajectories),
        "persistent_all_observations_count": sum(1 for x in trajectories if x["persistent_all_observations"]),
        "presence_excursion_count": sum(1 for x in trajectories if x["presence_excursion"]),
        "mean_absolute_step_change": (sum(all_abs)/len(all_abs)) if all_abs else None,
        "max_absolute_step_change": max(all_abs) if all_abs else None,
        "edge_trajectories": trajectories,
    }


def subject_trajectory(geometries, pairwise, subject, families, observations, times):
    return {
        "supported_domain_trajectory": _support_trajectory(geometries,subject),
        "stability_boundary_trajectories": {
            "positive": _boundary_trajectories(geometries,pairwise,subject,"positive",families,observations,times),
            "negative": _boundary_trajectories(geometries,pairwise,subject,"negative",families,observations,times),
        },
        "component_trajectories": _component_trajectories(geometries,pairwise,subject,observations,times),
        "sign_region_persistence": _sign_persistence(geometries,subject),
        "local_gradient_trajectories": _gradient_trajectories(geometries,subject),
    }

"""Geometry motion stability and multi-snapshot trajectories for CTCL-ITR v0.2.14."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .calibration_geometry_drift import compare_surface_geometry
from .calibration_geometry_trajectory_common import (
    METHOD_ID, TIME_UNIT, CalibrationGeometryTrajectoryError,
    _elapsed_days, _validate_geometries, _validate_spec,
)
from .calibration_geometry_trajectory_motion import subject_trajectory


def _step_summary(drift, observations, times, index):
    subjects={}
    for subject in ("autonomy","governance"):
        q=drift["subjects"][subject]
        positive=q["stability_boundary_motion"]["positive"]
        subjects[subject]={
            "net_supported_cell_change": q["supported_domain_motion"]["net_supported_cell_change"],
            "split_count": q["component_motion"]["split_count"],
            "merge_count": q["component_motion"]["merge_count"],
            "positive_boundary_matched_count": positive["matched_count"],
            "positive_boundary_mean_l1_displacement": positive["mean_l1_displacement"],
            "support_frontier_mean_l1_displacement": q["support_frontier_motion"]["mean_supported_endpoint_l1_displacement"],
            "matched_gradient_edge_count": q["local_gradient_drift"]["matched_edge_count"],
            "max_absolute_point_estimate_slope_change": q["local_gradient_drift"]["max_absolute_point_estimate_slope_change"],
        }
    return {
        "step_index": index,
        "from_observation_id": observations[index]["observation_id"],
        "to_observation_id": observations[index+1]["observation_id"],
        "elapsed_seconds": (times[index+1]-times[index]).total_seconds(),
        "elapsed_days": _elapsed_days(times[index],times[index+1]),
        "subjects": subjects,
    }


def analyze_geometry_trajectory(
    geometries: list[dict[str, Any]], trajectory_spec: dict[str, Any]
) -> dict[str, Any]:
    spec,times=_validate_spec(trajectory_spec)
    geometry_list=_validate_geometries(geometries,spec)
    observations=deepcopy(spec["observations"])
    pairwise=[]
    for i in range(len(geometry_list)-1):
        drift_spec={
            "schema_version":"0.2.13",
            "drift_id":f"{spec['trajectory_id']}:step:{i:04d}",
            "generated_at":observations[i+1]["observed_at"],
            "method":"surface_geometry_drift_v1",
            "boundary_match_method":"greedy_l1_nearest_v1",
        }
        pairwise.append(compare_surface_geometry(geometry_list[i],geometry_list[i+1],drift_spec))
    families=list(geometry_list[0]["families"])
    subjects={
        subject:subject_trajectory(geometry_list,pairwise,subject,families,observations,times)
        for subject in ("autonomy","governance")
    }
    steps=[_step_summary(d,observations,times,i) for i,d in enumerate(pairwise)]
    return {
        "schema_version":"0.2.14",
        "trajectory_id":spec["trajectory_id"],
        "generated_at":spec["generated_at"],
        "method":METHOD_ID,
        "time_unit":TIME_UNIT,
        "observation_count":len(observations),
        "observations":observations,
        "measurement_contract":deepcopy(geometry_list[0]["measurement_contract"]),
        "families":families,
        "grid":deepcopy(geometry_list[0]["grid"]),
        "boundary_interpolation":deepcopy(geometry_list[0]["boundary_interpolation"]),
        "conditioning":{
            "compatible_geometry_contract_required":True,
            "consecutive_motion_delegates_to_v0_2_13":True,
            "boundary_component_matching_is_descriptive_not_identity":True,
            "unsupported_region_interpolated":False,
            "finite_difference_derivatives_are_descriptive":True,
        },
        "steps":steps,
        "subjects":subjects,
        "interpretation_boundary":[
            "Geometry Trajectory != Causal Mechanism",
            "Finite-Difference Boundary Velocity != Capability Velocity",
            "Finite-Difference Boundary Acceleration != Physical Acceleration",
            "Support Reversal != Universal System Regression",
            "Boundary Lineage != Persistent Boundary Identity",
            "Component Lineage != Persistent Component Identity",
            "Gradient Trajectory != Global Derivative Field",
            "Trajectory Report != Authority",
        ],
        "non_authoritative":True,
    }


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _main(argv=None):
    parser=argparse.ArgumentParser(description="Analyze a CTCL-ITR multi-snapshot geometry trajectory.")
    parser.add_argument("--trajectory",required=True)
    parser.add_argument("--geometry",action="append",required=True,help="Geometry report path; repeat in observation order.")
    parser.add_argument("--pretty",action="store_true")
    args=parser.parse_args(argv)
    report=analyze_geometry_trajectory([_load(x) for x in args.geometry],_load(args.trajectory))
    print(json.dumps(report,ensure_ascii=False,indent=2 if args.pretty else None,separators=None if args.pretty else (",",":"),sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

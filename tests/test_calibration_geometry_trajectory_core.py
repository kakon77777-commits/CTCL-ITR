import copy
import json
from pathlib import Path

import pytest

from ctcl_itr.calibration_geometry_trajectory import (
    CalibrationGeometryTrajectoryError,
    analyze_geometry_trajectory,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def reference_geometries():
    g0 = load("calibration_surface_geometry_report.json")
    g1 = load("calibration_surface_geometry_report_later.json")
    g2 = copy.deepcopy(g0)
    g2["geometry_id"] = "geometry:reference-base-regressed"
    g2["generated_at"] = "2026-08-25T00:30:00+00:00"
    g2["source_surface"] = {
        "schema_version": "0.2.11",
        "surface_id": "surface:reference-base-regressed",
        "method": "joint_empirical_binomial_simplex_surface_v1",
    }
    return [g0, g1, g2]


def spec():
    return {
        "schema_version": "0.2.14",
        "trajectory_id": "geometry-trajectory:test",
        "generated_at": "2026-08-25T01:00:00+00:00",
        "method": "surface_geometry_trajectory_v1",
        "time_unit": "day",
        "observations": [
            {"observation_id": "obs:current", "observed_at": "2026-08-23T00:00:00+00:00", "geometry_id": "geometry:reference-base-current"},
            {"observation_id": "obs:later", "observed_at": "2026-08-24T00:00:00+00:00", "geometry_id": "geometry:reference-base-later"},
            {"observation_id": "obs:regressed", "observed_at": "2026-08-25T00:00:00+00:00", "geometry_id": "geometry:reference-base-regressed"},
        ],
    }


def test_support_trajectory_detects_expansion_contraction_reversal():
    report = analyze_geometry_trajectory(reference_geometries(), spec())
    for subject in ("autonomy", "governance"):
        support = report["subjects"][subject]["supported_domain_trajectory"]
        assert support["supported_cell_counts"] == [6, 8, 6]
        assert support["step_changes"] == [2, -2]
        assert support["step_directions"] == ["expansion", "contraction"]
        assert support["direction_reversal_count"] == 1
        assert support["net_supported_cell_change"] == 0


def test_positive_boundary_lineage_has_velocity_reversal_and_acceleration():
    report = analyze_geometry_trajectory(reference_geometries(), spec())
    auto = report["subjects"]["autonomy"]["stability_boundary_trajectories"]["positive"]
    assert auto["lineage_count"] == 1
    lineage = auto["lineages"][0]
    assert lineage["spans_all_observations"] is True
    assert [round(x["reference_family_weights"]["code"], 12) for x in lineage["points"]] == [
        round(0.5528922561345437, 12),
        round(0.37677630955816144, 12),
        round(0.5528922561345437, 12),
    ]
    assert lineage["velocity_direction_reversal_count_by_family"]["code"] == 1
    assert lineage["velocities"][0]["signed_family_velocity_per_day"]["code"] < 0
    assert lineage["velocities"][1]["signed_family_velocity_per_day"]["code"] > 0
    assert lineage["accelerations"][0]["signed_family_acceleration_per_day2"]["code"] > 0
    assert abs(lineage["net_signed_displacement"]["code"]) < 1e-12
    assert lineage["total_path_l1"] > 0


def test_component_lineage_spans_all_three_observations():
    report = analyze_geometry_trajectory(reference_geometries(), spec())
    for subject in ("autonomy", "governance"):
        components = report["subjects"][subject]["component_trajectories"]
        assert components["lineage_count"] == 1
        assert components["spans_all_observations_count"] == 1
        lineage = components["lineages"][0]
        assert lineage["observation_count"] == 3
        assert lineage["lifespan_days"] == 2.0
        assert lineage["split_event_count"] == 0
        assert lineage["merge_event_count"] == 0


def test_sign_region_persistence_detects_support_excursion():
    report = analyze_geometry_trajectory(reference_geometries(), spec())
    auto = report["subjects"]["autonomy"]["sign_region_persistence"]
    cells = {x["cell_key"]: x for x in auto["cell_trajectories"]}
    excursion = cells["code=0.7|research=0.3"]
    assert excursion["status_sequence"] == ["unsupported", "positive_band", "unsupported"]
    assert excursion["support_excursion"] is True
    assert auto["support_excursion_cell_count"] >= 2
    assert auto["supported_all_observations_count"] == 6


def test_gradient_trajectory_tracks_middle_only_edges_and_persistent_edges():
    report = analyze_geometry_trajectory(reference_geometries(), spec())
    gradients = report["subjects"]["autonomy"]["local_gradient_trajectories"]
    by_key = {x["edge_key"]: x for x in gradients["edge_trajectories"]}
    middle = by_key["code=0.6|research=0.4<>code=0.7|research=0.3"]
    assert middle["presence_sequence"] == [False, True, False]
    assert middle["presence_excursion"] is True
    assert gradients["persistent_all_observations_count"] == 5
    assert gradients["presence_excursion_count"] == 2


def test_trajectory_rejects_non_increasing_timestamps():
    bad = spec()
    bad["observations"][2]["observed_at"] = bad["observations"][1]["observed_at"]
    with pytest.raises(CalibrationGeometryTrajectoryError, match="strictly increasing"):
        analyze_geometry_trajectory(reference_geometries(), bad)


def test_trajectory_rejects_geometry_contract_mismatch():
    geometries = reference_geometries()
    geometries[2]["grid"]["grid_step"] = 0.2
    with pytest.raises(CalibrationGeometryTrajectoryError, match="incompatible geometry contracts"):
        analyze_geometry_trajectory(geometries, spec())

from copy import deepcopy
import json
from pathlib import Path

import pytest

from ctcl_itr.calibration_joint_surface import analyze_joint_uncertainty_surface
from ctcl_itr.calibration_surface_geometry import (
    CalibrationSurfaceGeometryError,
    analyze_surface_geometry,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))




def reference_surface():
    return analyze_joint_uncertainty_surface(
        load("calibration_snapshot_base.json"),
        load("calibration_snapshot_current.json"),
        load("calibration_comparison_spec.json"),
        load("calibration_joint_surface_spec.json"),
    )


def geometry_spec(**overrides):
    spec = {
        "schema_version": "0.2.12",
        "geometry_id": "geometry:test",
        "generated_at": "2026-08-23T15:30:00+08:00",
        "method": "simplex_supported_surface_geometry_v1",
        "adjacency_tolerance": 1e-9,
        "zero_tolerance": 1e-12,
    }
    spec.update(overrides)
    return spec


def _cell(weights, *, cls="crosses_zero", delta=0.5, lower=-0.1, upper=1.0, supported=True):
    if not supported:
        return {
            "reference_family_weights": weights,
            "point_estimate": {
                "support_status": "unsupported",
                "support_reasons": ["synthetic"],
                "composition_adjusted_delta": None,
                "reference_base_horizon": None,
                "reference_current_horizon": None,
            },
            "resampling": {
                "supported_replicates": 0,
                "total_replicates": 32,
                "supported_fraction": 0.0,
                "support_status": "insufficient_resampling_support",
                "band": None,
                "mean": None,
                "sign_shares": None,
                "band_sign_class": "unsupported",
                "unsupported_reason_counts": {"synthetic": 32},
            },
        }
    return {
        "reference_family_weights": weights,
        "point_estimate": {
            "support_status": "supported",
            "support_reasons": [],
            "composition_adjusted_delta": delta,
            "reference_base_horizon": 6.0,
            "reference_current_horizon": 6.0 + delta,
        },
        "resampling": {
            "supported_replicates": 32,
            "total_replicates": 32,
            "supported_fraction": 1.0,
            "support_status": "supported",
            "band": {"lower": lower, "median": delta, "upper": upper},
            "mean": delta,
            "sign_shares": {"positive": 1.0, "negative": 0.0, "zero": 0.0},
            "band_sign_class": cls,
            "unsupported_reason_counts": {},
        },
    }


def synthetic_surface(families, cells, *, grid_step=0.1):
    return {
        "schema_version": "0.2.11",
        "surface_id": "surface:synthetic",
        "generated_at": "2026-08-23T15:30:00+08:00",
        "method": "joint_empirical_binomial_simplex_surface_v1",
        "base_snapshot_id": "snapshot:base",
        "current_snapshot_id": "snapshot:current",
        "comparison_id": "comparison:base-current",
        "measurement_contract": {
            "unit": "interaction_depth",
            "reliability_p": 0.9,
            "scope_id": "scope:test",
            "assessment_method": "monotone_binomial_pava_v1",
        },
        "families": families,
        "point_reference_family_weights": {f: 1.0 / len(families) for f in families},
        "resampling": {
            "method": "stratified_empirical_binomial_sha256_v1",
            "seed": "synthetic",
            "replicates": 32,
            "interval_p": 0.9,
            "minimum_supported_fraction": 0.5,
        },
        "mixture_grid": {
            "method": "simplex_grid_reference_mixture_v1",
            "grid_step": grid_step,
            "minimum_family_weight": 0.1,
            "max_grid_points": 1000,
            "total_points": len(cells),
        },
        "conditioning": {
            "outcome_counts_resampled": True,
            "trial_counts_fixed": True,
            "observed_family_weights_fixed": True,
            "reference_mixture_varied": True,
            "mixture_weights_resampled": False,
            "same_resampled_outcomes_reused_across_mixture_cells": True,
            "surface_cells_are_independent": False,
        },
        "subjects": {
            "autonomy": {"cells": deepcopy(cells), "surface_summary": {}},
            "governance": {"cells": deepcopy(cells), "surface_summary": {}},
        },
        "interpretation_boundary": "joint_sampling_x_reference_mixture_surface",
        "non_authoritative": True,
    }


def test_geometry_is_deterministic_non_authoritative_and_does_not_mutate_input():
    surface = reference_surface()
    spec = geometry_spec()
    original = deepcopy((surface, spec))

    first = analyze_surface_geometry(surface, spec)
    second = analyze_surface_geometry(surface, spec)

    assert first == second
    assert (surface, spec) == original
    assert first["conditioning"]["unsupported_cells_interpolated"] is False
    assert first["conditioning"]["local_gradients_supported_edges_only"] is True
    assert first["non_authoritative"] is True


def test_general_three_family_simplex_adjacency_uses_single_grid_transfer():
    cells = [
        _cell({"a": 0.2, "b": 0.4, "c": 0.4}, delta=0.2),
        _cell({"a": 0.3, "b": 0.3, "c": 0.4}, cls="positive_band", delta=0.4, lower=0.1),
        _cell({"a": 0.3, "b": 0.4, "c": 0.3}, supported=False),
    ]
    report = analyze_surface_geometry(synthetic_surface(["a", "b", "c"], cells), geometry_spec())
    graph = report["subjects"]["autonomy"]["supported_graph"]
    boundaries = report["subjects"]["autonomy"]["boundaries"]

    assert graph["supported_node_count"] == 2
    assert graph["supported_edge_count"] == 1
    edge = graph["edges"][0]
    assert edge["transfer_mass"] == pytest.approx(0.1)
    assert {edge["increased_family"], edge["decreased_family"]} == {"a", "b"}
    assert len(boundaries["support_edges"]) == 2


def test_reference_geometry_has_one_supported_component_and_expected_regions():
    report = analyze_surface_geometry(reference_surface(), geometry_spec())
    for subject in ("autonomy", "governance"):
        payload = report["subjects"][subject]
        graph = payload["supported_graph"]
        regions = payload["sign_regions"]
        boundaries = payload["boundaries"]

        assert graph["supported_node_count"] == 6
        assert graph["supported_edge_count"] == 5
        assert [c["size"] for c in graph["connected_components"]] == [6]
        assert [c["size"] for c in regions["crosses_zero"]["components"]] == [5]
        assert [c["size"] for c in regions["positive_band"]["components"]] == [1]
        assert regions["negative_band"]["components"] == []
        assert len(boundaries["support_edges"]) == 1
        assert len(boundaries["sign_class_edges"]) == 1
        assert len(boundaries["positive_stability_zero_crossings"]) == 1
        assert boundaries["negative_stability_zero_crossings"] == []


def test_positive_stability_boundary_interpolates_only_between_supported_neighbors():
    report = analyze_surface_geometry(reference_surface(), geometry_spec())
    auto = report["subjects"]["autonomy"]["boundaries"]["positive_stability_zero_crossings"]
    gov = report["subjects"]["governance"]["boundaries"]["positive_stability_zero_crossings"]

    assert len(auto) == 1
    assert auto[0]["estimated_reference_family_weights"]["code"] == pytest.approx(0.5528922561345437)
    assert auto[0]["interpolation_fraction"] == pytest.approx(0.5289225613454375)

    assert len(gov) == 1
    assert gov[0]["estimated_reference_family_weights"]["code"] == pytest.approx(0.5)
    assert gov[0]["interpolation_fraction"] == pytest.approx(0.0)

    # No boundary interpolation is allowed into the unsupported code=0.7 cell.
    for subject in ("autonomy", "governance"):
        for crossing in report["subjects"][subject]["boundaries"]["positive_stability_zero_crossings"]:
            assert 0.7 not in crossing["estimated_reference_family_weights"].values()


def test_local_gradients_exist_only_on_supported_edges_and_match_reference_slope():
    report = analyze_surface_geometry(reference_surface(), geometry_spec())
    auto = report["subjects"]["autonomy"]["local_gradients"]
    gov = report["subjects"]["governance"]["local_gradients"]

    assert len(auto) == len(gov) == 5
    assert max(abs(e["point_estimate_slope"]) for e in auto) == pytest.approx(2.386554621848722)
    assert max(abs(e["point_estimate_slope"]) for e in gov) == pytest.approx(2.632478632478632)
    assert all(e["transfer_mass"] == pytest.approx(0.1) for e in auto + gov)


def test_unsupported_gap_splits_supported_components_and_is_not_bridged():
    cells = [
        _cell({"x": 0.1, "y": 0.9}, delta=0.1),
        _cell({"x": 0.2, "y": 0.8}, supported=False),
        _cell({"x": 0.3, "y": 0.7}, cls="positive_band", delta=0.4, lower=0.1),
    ]
    report = analyze_surface_geometry(synthetic_surface(["x", "y"], cells), geometry_spec())
    graph = report["subjects"]["autonomy"]["supported_graph"]

    assert graph["supported_edge_count"] == 0
    assert sorted(c["size"] for c in graph["connected_components"]) == [1, 1]
    assert len(report["subjects"]["autonomy"]["boundaries"]["support_edges"]) == 2
    assert report["subjects"]["autonomy"]["local_gradients"] == []


def test_invalid_geometry_or_surface_contracts_are_rejected():
    surface = reference_surface()

    with pytest.raises(CalibrationSurfaceGeometryError, match="method"):
        analyze_surface_geometry(surface, geometry_spec(method="other"))

    bad = deepcopy(surface)
    bad["families"] = ["code", "research", "missing"]
    with pytest.raises(CalibrationSurfaceGeometryError, match="family"):
        analyze_surface_geometry(bad, geometry_spec())

    bad = deepcopy(surface)
    bad["subjects"]["autonomy"]["cells"][0]["reference_family_weights"]["code"] = 0.2
    with pytest.raises(CalibrationSurfaceGeometryError, match="sum"):
        analyze_surface_geometry(bad, geometry_spec())

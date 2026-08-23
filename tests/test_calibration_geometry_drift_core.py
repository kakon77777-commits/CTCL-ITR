import json
from copy import deepcopy
from pathlib import Path

import pytest

from ctcl_itr.calibration_geometry_drift import (
    CalibrationGeometryDriftError,
    compare_surface_geometry,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def drift_spec(**overrides):
    spec = {
        "schema_version": "0.2.13",
        "drift_id": "geometry-drift:test",
        "generated_at": "2026-08-24T01:00:00+00:00",
        "method": "surface_geometry_drift_v1",
        "boundary_match_method": "greedy_l1_nearest_v1",
    }
    spec.update(overrides)
    return spec


def reference_like_current():
    base = load("calibration_surface_geometry_report.json")
    current = deepcopy(base)
    current["geometry_id"] = "geometry:synthetic-current"
    current["generated_at"] = "2026-08-24T00:30:00+00:00"

    for subject in ("autonomy", "governance"):
        q = current["subjects"][subject]
        graph = q["supported_graph"]
        node_map = {n["cell_key"]: n for n in graph["nodes"]}
        for code in (0.7, 0.8):
            research = round(1 - code, 1)
            key = f"code={code}|research={research}"
            graph["nodes"].append({"cell_key":key,"reference_family_weights":{"code":code,"research":research},"band_sign_class":"positive_band"})
        for code in (0.4, 0.5):
            research = round(1 - code, 1)
            node_map[f"code={code}|research={research}"]["band_sign_class"] = "positive_band"
        graph["supported_node_count"] = 8
        graph["connected_components"] = [{"component_id":"supported:0000","size":8,"members":[n["cell_key"] for n in graph["nodes"]]}]
        graph["isolated_nodes"] = []
        q["boundaries"]["positive_stability_zero_crossings"] = [{"cell_a":"code=0.3|research=0.7","cell_b":"code=0.4|research=0.6","endpoint_field":"band.lower","endpoint_value_a":-0.1,"endpoint_value_b":0.1,"interpolation_fraction":0.5,"estimated_reference_family_weights":{"code":0.35,"research":0.65},"observed_cell":False}]
        q["boundaries"]["support_edges"] = [{"supported_cell":"code=0.8|research=0.2","unsupported_cell":"code=0.9|research=0.1","transfer_mass":0.1}]
        q["local_gradients"][0]["point_estimate_slope"] += 0.5
        q["local_gradients"].append({"cell_a":"code=0.6|research=0.4","cell_b":"code=0.7|research=0.3","transfer_mass":0.1,"increased_family":"code","decreased_family":"research","point_estimate_slope":3.0,"band_lower_slope":2.0,"band_upper_slope":4.0})
        q["local_gradients"].append({"cell_a":"code=0.7|research=0.3","cell_b":"code=0.8|research=0.2","transfer_mass":0.1,"increased_family":"code","decreased_family":"research","point_estimate_slope":3.5,"band_lower_slope":2.5,"band_upper_slope":4.5})
    return current


def test_support_domain_motion_and_sign_migration_are_separated():
    report = compare_surface_geometry(load("calibration_surface_geometry_report.json"), reference_like_current(), drift_spec())
    auto = report["subjects"]["autonomy"]
    domain = auto["supported_domain_motion"]
    assert domain["base_supported_cell_count"] == 6
    assert domain["current_supported_cell_count"] == 8
    assert domain["persistent_supported_cell_count"] == 6
    assert domain["gained_supported_cells"] == ["code=0.7|research=0.3","code=0.8|research=0.2"]
    assert domain["lost_supported_cells"] == []
    assert domain["net_supported_cell_change"] == 2
    migration = auto["sign_region_migration"]
    transitions = {(x["from_class"],x["to_class"]):x["count"] for x in migration["persistent_transitions"]}
    assert transitions[("crosses_zero","positive_band")] == 2
    assert transitions[("crosses_zero","crosses_zero")] == 3
    assert transitions[("positive_band","positive_band")] == 1
    assert migration["gained_by_current_class"]["positive_band"]["count"] == 2


def test_boundary_and_support_frontier_motion_are_descriptive_and_directional():
    report = compare_surface_geometry(load("calibration_surface_geometry_report.json"), reference_like_current(), drift_spec())
    auto = report["subjects"]["autonomy"]
    positive = auto["stability_boundary_motion"]["positive"]
    assert positive["matched_count"] == 1
    match = positive["matches"][0]
    assert match["current_weights"] == {"code":0.35,"research":0.65}
    assert match["signed_family_displacement"]["code"] < 0
    assert match["signed_family_displacement"]["research"] > 0
    assert match["l1_displacement"] > 0
    frontier = auto["support_frontier_motion"]
    assert frontier["base_edge_count"] == 1
    assert frontier["current_edge_count"] == 1
    assert frontier["matched_supported_endpoint_count"] == 1
    assert frontier["matched_supported_endpoints"][0]["signed_family_displacement"]["code"] > 0


def test_gradient_drift_matches_only_persistent_edges():
    report = compare_surface_geometry(load("calibration_surface_geometry_report.json"), reference_like_current(), drift_spec())
    gradients = report["subjects"]["autonomy"]["local_gradient_drift"]
    assert gradients["matched_edge_count"] == 5
    assert gradients["appeared_edge_count"] == 2
    assert gradients["disappeared_edge_count"] == 0
    first = next(x for x in gradients["matched_edges"] if x["edge_key"] == "code=0.1|research=0.9<>code=0.2|research=0.8")
    assert first["point_estimate_slope_change"] == pytest.approx(0.5)
    assert gradients["max_absolute_point_estimate_slope_change"] >= 0.5


def _component_geometry(component_members, *, geometry_id):
    base = load("calibration_surface_geometry_report.json")
    g = deepcopy(base)
    g["geometry_id"] = geometry_id
    for subject in ("autonomy","governance"):
        q = g["subjects"][subject]
        all_members = sorted({m for members in component_members for m in members})
        node_source = {n["cell_key"]:n for n in q["supported_graph"]["nodes"]}
        q["supported_graph"]["nodes"] = [deepcopy(node_source[m]) for m in all_members]
        q["supported_graph"]["supported_node_count"] = len(all_members)
        q["supported_graph"]["connected_components"] = [{"component_id":f"supported:{i:04d}","size":len(members),"members":list(members)} for i,members in enumerate(component_members)]
        q["supported_graph"]["edges"] = []
        q["supported_graph"]["supported_edge_count"] = 0
        q["local_gradients"] = []
        q["boundaries"]["positive_stability_zero_crossings"] = []
        q["boundaries"]["negative_stability_zero_crossings"] = []
        q["boundaries"]["support_edges"] = []
    return g


def test_component_overlap_reports_splits_and_merges_without_claiming_phase_transition():
    a,b,c,d = "code=0.1|research=0.9","code=0.2|research=0.8","code=0.3|research=0.7","code=0.4|research=0.6"
    base = _component_geometry([[a,b,c],[d]], geometry_id="geometry:base-components")
    current = _component_geometry([[a,b],[c,d]], geometry_id="geometry:current-components")
    comp = compare_surface_geometry(base,current,drift_spec())["subjects"]["autonomy"]["component_motion"]
    assert comp["split_count"] == 1
    assert comp["merge_count"] == 1
    assert comp["split_events"][0]["base_component_id"] == "supported:0000"
    assert comp["merge_events"][0]["current_component_id"] == "supported:0001"


def test_geometry_contract_mismatch_is_rejected():
    base = load("calibration_surface_geometry_report.json")
    current = reference_like_current()
    bad = deepcopy(current); bad["measurement_contract"]["scope_id"] = "scope:other"
    with pytest.raises(CalibrationGeometryDriftError, match="measurement_contract"): compare_surface_geometry(base,bad,drift_spec())
    bad = deepcopy(current); bad["grid"]["grid_step"] = 0.2
    with pytest.raises(CalibrationGeometryDriftError, match="grid"): compare_surface_geometry(base,bad,drift_spec())
    with pytest.raises(CalibrationGeometryDriftError, match="method"): compare_surface_geometry(base,current,drift_spec(method="other"))


def test_inputs_are_not_mutated():
    base = load("calibration_surface_geometry_report.json")
    current = reference_like_current(); spec = drift_spec()
    before = (deepcopy(base),deepcopy(current),deepcopy(spec))
    compare_surface_geometry(base,current,spec)
    assert (base,current,spec) == before

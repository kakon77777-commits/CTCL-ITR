"""Geometry-motion analyzers for CTCL-ITR v0.2.13."""

from __future__ import annotations

from typing import Any

from .calibration_geometry_drift_common import (
    BOUNDARY_MATCH_METHOD,
    SIGN_CLASSES,
    CalibrationGeometryDriftError,
    _finite,
    _node_map,
    _required_string,
)

def _supported_domain(base_q: dict[str, Any], current_q: dict[str, Any]) -> dict[str, Any]:
    base_keys=set(_node_map(base_q)); current_keys=set(_node_map(current_q)); persistent=sorted(base_keys&current_keys); gained=sorted(current_keys-base_keys); lost=sorted(base_keys-current_keys); union=base_keys|current_keys
    return {"base_supported_cell_count":len(base_keys),"current_supported_cell_count":len(current_keys),"persistent_supported_cell_count":len(persistent),"gained_supported_cell_count":len(gained),"lost_supported_cell_count":len(lost),"net_supported_cell_change":len(current_keys)-len(base_keys),"persistent_supported_cells":persistent,"gained_supported_cells":gained,"lost_supported_cells":lost,"union_supported_cell_count":len(union),"jaccard_overlap":(len(persistent)/len(union)) if union else 1.0}


def _components(subject_payload):
    result=[]
    for index,component in enumerate(subject_payload["supported_graph"].get("connected_components",[])):
        cid=component.get("component_id") or f"component:{index:04d}"; members=component.get("members")
        if not isinstance(members,list): raise CalibrationGeometryDriftError("connected component members must be an array")
        result.append({"component_id":str(cid),"members":set(str(x) for x in members)})
    return result


def _component_motion(base_q,current_q):
    base_components=_components(base_q); current_components=_components(current_q); links=[]; base_to_current={c["component_id"]:[] for c in base_components}; current_to_base={c["component_id"]:[] for c in current_components}
    for b in base_components:
        for c in current_components:
            shared=sorted(b["members"]&c["members"])
            if not shared: continue
            base_to_current[b["component_id"]].append(c["component_id"]); current_to_base[c["component_id"]].append(b["component_id"])
            links.append({"base_component_id":b["component_id"],"current_component_id":c["component_id"],"shared_member_count":len(shared),"shared_members":shared})
    split_events=[{"base_component_id":bid,"current_component_ids":sorted(cids),"overlap_count":len(cids)} for bid,cids in sorted(base_to_current.items()) if len(cids)>1]
    merge_events=[{"current_component_id":cid,"base_component_ids":sorted(bids),"overlap_count":len(bids)} for cid,bids in sorted(current_to_base.items()) if len(bids)>1]
    return {"base_component_count":len(base_components),"current_component_count":len(current_components),"overlap_link_count":len(links),"overlap_links":sorted(links,key=lambda x:(x["base_component_id"],x["current_component_id"])),"split_count":len(split_events),"merge_count":len(merge_events),"split_events":split_events,"merge_events":merge_events,"base_components_without_current_overlap":sorted(k for k,v in base_to_current.items() if not v),"current_components_without_base_overlap":sorted(k for k,v in current_to_base.items() if not v)}


def _class_bucket(keys,node_map):
    result={name:{"count":0,"cells":[]} for name in SIGN_CLASSES}
    for key in keys:
        cls=node_map[key]["band_sign_class"]; result[cls]["count"]+=1; result[cls]["cells"].append(key)
    return result


def _sign_migration(base_q,current_q):
    base_nodes=_node_map(base_q); current_nodes=_node_map(current_q); persistent=sorted(set(base_nodes)&set(current_nodes)); gained=sorted(set(current_nodes)-set(base_nodes)); lost=sorted(set(base_nodes)-set(current_nodes)); buckets={}
    for key in persistent:
        pair=(base_nodes[key]["band_sign_class"],current_nodes[key]["band_sign_class"]); buckets.setdefault(pair,[]).append(key)
    transitions=[{"from_class":a,"to_class":b,"count":len(cells),"cells":cells} for (a,b),cells in sorted(buckets.items())]
    return {"persistent_cell_count":len(persistent),"persistent_transitions":transitions,"gained_by_current_class":_class_bucket(gained,current_nodes),"lost_by_base_class":_class_bucket(lost,base_nodes)}


def _weight_key(weights,families): return "|".join(f"{f}={float(weights[f]):.12g}" for f in families)
def _l1(a,b,families): return sum(abs(float(b[f])-float(a[f])) for f in families)


def _greedy_point_match(base_points,current_points,families):
    def normalized(points,label):
        out=[]
        for index,point in enumerate(points):
            if not isinstance(point,dict) or not isinstance(point.get("estimated_reference_family_weights"),dict): raise CalibrationGeometryDriftError(f"{label} boundary point is invalid")
            weights={f:_finite(point["estimated_reference_family_weights"].get(f),f"{label}.{f}") for f in families}; out.append({"index":index,"weights":weights,"key":_weight_key(weights,families)})
        return out
    base=normalized(base_points,"base"); current=normalized(current_points,"current"); candidates=[]
    for b in base:
        for c in current: candidates.append((_l1(b["weights"],c["weights"],families),b["key"],c["key"],b,c))
    candidates.sort(key=lambda x:(x[0],x[1],x[2])); used_b=set(); used_c=set(); matches=[]
    for distance,_,_,b,c in candidates:
        if b["index"] in used_b or c["index"] in used_c: continue
        used_b.add(b["index"]); used_c.add(c["index"]); signed={f:c["weights"][f]-b["weights"][f] for f in families}; matches.append({"base_weights":b["weights"],"current_weights":c["weights"],"l1_displacement":distance,"signed_family_displacement":signed})
    distances=[x["l1_displacement"] for x in matches]
    return {"base_count":len(base),"current_count":len(current),"matched_count":len(matches),"appeared_count":len(current)-len(used_c),"disappeared_count":len(base)-len(used_b),"matches":matches,"appeared_weights":[c["weights"] for c in current if c["index"] not in used_c],"disappeared_weights":[b["weights"] for b in base if b["index"] not in used_b],"mean_l1_displacement":(sum(distances)/len(distances)) if distances else None,"max_l1_displacement":max(distances) if distances else None}


def _stability_boundary_motion(base_q,current_q,families):
    b=base_q["boundaries"]; c=current_q["boundaries"]
    return {"matching_method":BOUNDARY_MATCH_METHOD,"matching_is_descriptive_not_identity":True,"positive":_greedy_point_match(b.get("positive_stability_zero_crossings",[]),c.get("positive_stability_zero_crossings",[]),families),"negative":_greedy_point_match(b.get("negative_stability_zero_crossings",[]),c.get("negative_stability_zero_crossings",[]),families)}


def _support_frontier_points(subject_payload,families):
    nodes=_node_map(subject_payload); points=[]; signatures=[]
    for edge in subject_payload["boundaries"].get("support_edges",[]):
        supported=edge.get("supported_cell"); unsupported=edge.get("unsupported_cell")
        if supported not in nodes: raise CalibrationGeometryDriftError("support boundary supported_cell must be a supported node")
        points.append({"estimated_reference_family_weights":{f:float(nodes[supported]["reference_family_weights"][f]) for f in families}}); signatures.append(f"{supported}<->{unsupported}")
    return points,signatures


def _support_frontier_motion(base_q,current_q,families):
    base_points,base_edges=_support_frontier_points(base_q,families); current_points,current_edges=_support_frontier_points(current_q,families); match=_greedy_point_match(base_points,current_points,families)
    return {"base_edge_count":len(base_edges),"current_edge_count":len(current_edges),"persistent_edges":sorted(set(base_edges)&set(current_edges)),"appeared_edges":sorted(set(current_edges)-set(base_edges)),"disappeared_edges":sorted(set(base_edges)-set(current_edges)),"matched_supported_endpoint_count":match["matched_count"],"matched_supported_endpoints":match["matches"],"mean_supported_endpoint_l1_displacement":match["mean_l1_displacement"],"max_supported_endpoint_l1_displacement":match["max_l1_displacement"],"unsupported_region_interpolated":False}


def _gradient_key(edge):
    a=_required_string(edge.get("cell_a"),"gradient.cell_a"); b=_required_string(edge.get("cell_b"),"gradient.cell_b"); return "<>".join(sorted((a,b)))


def _gradient_map(subject_payload):
    result={}
    for edge in subject_payload.get("local_gradients",[]):
        key=_gradient_key(edge)
        if key in result: raise CalibrationGeometryDriftError(f"duplicate local gradient edge {key}")
        result[key]=edge
    return result


def _gradient_drift(base_q,current_q):
    base=_gradient_map(base_q); current=_gradient_map(current_q); persistent=sorted(set(base)&set(current)); appeared=sorted(set(current)-set(base)); disappeared=sorted(set(base)-set(current)); matches=[]
    for key in persistent:
        b=base[key]; c=current[key]; bp=_finite(b.get("point_estimate_slope"),f"{key}.base.point_estimate_slope"); cp=_finite(c.get("point_estimate_slope"),f"{key}.current.point_estimate_slope"); bl=_finite(b.get("band_lower_slope"),f"{key}.base.band_lower_slope"); cl=_finite(c.get("band_lower_slope"),f"{key}.current.band_lower_slope"); bu=_finite(b.get("band_upper_slope"),f"{key}.base.band_upper_slope"); cu=_finite(c.get("band_upper_slope"),f"{key}.current.band_upper_slope")
        matches.append({"edge_key":key,"base_point_estimate_slope":bp,"current_point_estimate_slope":cp,"point_estimate_slope_change":cp-bp,"absolute_point_estimate_slope_change":abs(cp-bp),"band_lower_slope_change":cl-bl,"band_upper_slope_change":cu-bu})
    abs_changes=[x["absolute_point_estimate_slope_change"] for x in matches]
    return {"matched_edge_count":len(matches),"appeared_edge_count":len(appeared),"disappeared_edge_count":len(disappeared),"matched_edges":matches,"appeared_edges":appeared,"disappeared_edges":disappeared,"mean_absolute_point_estimate_slope_change":(sum(abs_changes)/len(abs_changes)) if abs_changes else None,"max_absolute_point_estimate_slope_change":max(abs_changes) if abs_changes else None,"gradients_synthesized_for_missing_edges":False}


def _subject_motion(base_q,current_q,families):
    domain=_supported_domain(base_q,current_q); components=_component_motion(base_q,current_q); sign=_sign_migration(base_q,current_q); stability=_stability_boundary_motion(base_q,current_q,families); frontier=_support_frontier_motion(base_q,current_q,families); gradients=_gradient_drift(base_q,current_q); positive=stability["positive"]
    return {"supported_domain_motion":domain,"component_motion":components,"sign_region_migration":sign,"stability_boundary_motion":stability,"support_frontier_motion":frontier,"local_gradient_drift":gradients,"motion_summary":{"net_supported_cell_change":domain["net_supported_cell_change"],"split_count":components["split_count"],"merge_count":components["merge_count"],"positive_boundary_matched_count":positive["matched_count"],"positive_boundary_mean_l1_displacement":positive["mean_l1_displacement"],"support_frontier_mean_l1_displacement":frontier["mean_supported_endpoint_l1_displacement"],"matched_gradient_edge_count":gradients["matched_edge_count"],"max_absolute_point_estimate_slope_change":gradients["max_absolute_point_estimate_slope_change"]}}

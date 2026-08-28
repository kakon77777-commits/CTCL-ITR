"""Evidence-supported geometry for CTCL-ITR v0.2.12 uncertainty surfaces."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Iterable

METHOD_ID = "simplex_supported_surface_geometry_v1"
SOURCE_METHOD = "joint_empirical_binomial_simplex_surface_v1"
SIGN_CLASSES = ("positive_band", "negative_band", "crosses_zero", "zero_band")


class CalibrationSurfaceGeometryError(ValueError):
    """Raised when a surface-geometry contract or source surface is invalid."""


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationSurfaceGeometryError(f"{label} is required")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationSurfaceGeometryError(f"{label} must be a finite number")
    result = float(value)
    if not isfinite(result):
        raise CalibrationSurfaceGeometryError(f"{label} must be a finite number")
    return result


def _validate_spec(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationSurfaceGeometryError("geometry spec must be an object")
    spec = deepcopy(raw)
    if spec.get("schema_version") != "0.2.12":
        raise CalibrationSurfaceGeometryError("geometry spec must use schema_version 0.2.12")
    _required_string(spec.get("geometry_id"), "geometry_id")
    _required_string(spec.get("generated_at"), "generated_at")
    if spec.get("method") != METHOD_ID:
        raise CalibrationSurfaceGeometryError(f"method must be {METHOD_ID}")
    adjacency_tolerance = _finite_number(spec.get("adjacency_tolerance", 1e-9), "adjacency_tolerance")
    zero_tolerance = _finite_number(spec.get("zero_tolerance", 1e-12), "zero_tolerance")
    if not 0 < adjacency_tolerance <= 1e-3:
        raise CalibrationSurfaceGeometryError("adjacency_tolerance must be in (0, 1e-3]")
    if not 0 <= zero_tolerance <= 1e-6:
        raise CalibrationSurfaceGeometryError("zero_tolerance must be in [0, 1e-6]")
    spec["adjacency_tolerance"] = adjacency_tolerance
    spec["zero_tolerance"] = zero_tolerance
    return spec


def _composition_key(weights: dict[str, float], families: list[str]) -> str:
    return "|".join(f"{family}={float(weights[family]):.12g}" for family in families)


def _validate_band(band: Any, label: str) -> dict[str, float]:
    if not isinstance(band, dict):
        raise CalibrationSurfaceGeometryError(f"{label}.band must be an object")
    lower = _finite_number(band.get("lower"), f"{label}.band.lower")
    median = _finite_number(band.get("median"), f"{label}.band.median")
    upper = _finite_number(band.get("upper"), f"{label}.band.upper")
    if lower > median or median > upper:
        raise CalibrationSurfaceGeometryError(f"{label}.band must satisfy lower <= median <= upper")
    return {"lower": lower, "median": median, "upper": upper}


def _validate_surface(raw: dict[str, Any], tolerance: float) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CalibrationSurfaceGeometryError("surface report must be an object")
    surface = deepcopy(raw)
    if surface.get("schema_version") != "0.2.11":
        raise CalibrationSurfaceGeometryError("surface report must use schema_version 0.2.11")
    if surface.get("method") != SOURCE_METHOD:
        raise CalibrationSurfaceGeometryError(f"surface method must be {SOURCE_METHOD}")
    _required_string(surface.get("surface_id"), "surface_id")

    families = surface.get("families")
    if not isinstance(families, list) or len(families) < 2 or len(set(families)) != len(families):
        raise CalibrationSurfaceGeometryError("surface families must contain at least two unique names")
    if any(not isinstance(family, str) or not family for family in families):
        raise CalibrationSurfaceGeometryError("surface family names must be non-empty strings")

    mixture_grid = surface.get("mixture_grid")
    if not isinstance(mixture_grid, dict):
        raise CalibrationSurfaceGeometryError("surface mixture_grid must be an object")
    grid_step = _finite_number(mixture_grid.get("grid_step"), "mixture_grid.grid_step")
    if not 0 < grid_step < 1:
        raise CalibrationSurfaceGeometryError("mixture_grid.grid_step must be in (0, 1)")

    subjects = surface.get("subjects")
    if not isinstance(subjects, dict) or set(subjects) != {"autonomy", "governance"}:
        raise CalibrationSurfaceGeometryError("surface subjects must be autonomy and governance")

    normalized_subjects: dict[str, list[dict[str, Any]]] = {}
    for subject in ("autonomy", "governance"):
        payload = subjects[subject]
        cells = payload.get("cells") if isinstance(payload, dict) else None
        if not isinstance(cells, list) or not cells:
            raise CalibrationSurfaceGeometryError(f"{subject}.cells must be a non-empty array")
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, cell in enumerate(cells):
            label = f"{subject}.cells[{index}]"
            if not isinstance(cell, dict):
                raise CalibrationSurfaceGeometryError(f"{label} must be an object")
            weights = cell.get("reference_family_weights")
            if not isinstance(weights, dict) or set(weights) != set(families):
                raise CalibrationSurfaceGeometryError(f"{label} family weights must match the declared family set")
            normalized_weights: dict[str, float] = {}
            for family in families:
                value = _finite_number(weights[family], f"{label}.reference_family_weights.{family}")
                if value < -tolerance or value > 1 + tolerance:
                    raise CalibrationSurfaceGeometryError(f"{label} family weights must be in [0, 1]")
                normalized_weights[family] = value
            if abs(sum(normalized_weights.values()) - 1.0) > tolerance:
                raise CalibrationSurfaceGeometryError(f"{label} family weights must sum to one")
            key = _composition_key(normalized_weights, families)
            if key in seen:
                raise CalibrationSurfaceGeometryError(f"duplicate mixture composition: {key}")
            seen.add(key)

            point = cell.get("point_estimate")
            resampling = cell.get("resampling")
            if not isinstance(point, dict) or not isinstance(resampling, dict):
                raise CalibrationSurfaceGeometryError(f"{label} must contain point_estimate and resampling")
            support_status = resampling.get("support_status")
            band_class = resampling.get("band_sign_class")
            if band_class not in (*SIGN_CLASSES, "unsupported"):
                raise CalibrationSurfaceGeometryError(f"{label}.resampling.band_sign_class is invalid")
            supported = support_status == "supported"
            band: dict[str, float] | None = None
            delta: float | None = None
            if supported:
                if band_class == "unsupported":
                    raise CalibrationSurfaceGeometryError(f"{label} supported cell cannot use unsupported band class")
                band = _validate_band(resampling.get("band"), label)
                if point.get("support_status") != "supported":
                    raise CalibrationSurfaceGeometryError(f"{label} resampling-supported cell requires supported point estimate")
                delta = _finite_number(point.get("composition_adjusted_delta"), f"{label}.point_estimate.composition_adjusted_delta")
            normalized.append(
                {
                    "cell_index": index,
                    "cell_key": key,
                    "reference_family_weights": normalized_weights,
                    "supported": supported,
                    "band_sign_class": band_class,
                    "band": band,
                    "point_delta": delta,
                }
            )
        normalized_subjects[subject] = normalized

    # Geometry requires the same mixture coordinate set for both subjects.
    auto_keys = {cell["cell_key"] for cell in normalized_subjects["autonomy"]}
    gov_keys = {cell["cell_key"] for cell in normalized_subjects["governance"]}
    if auto_keys != gov_keys:
        raise CalibrationSurfaceGeometryError("autonomy and governance must use the same mixture family grid")

    return {
        "surface": surface,
        "families": list(families),
        "grid_step": grid_step,
        "subjects": normalized_subjects,
    }


def _adjacent(
    a: dict[str, float],
    b: dict[str, float],
    families: list[str],
    grid_step: float,
    tolerance: float,
) -> tuple[bool, str | None, str | None, float]:
    diffs = {family: b[family] - a[family] for family in families}
    increased = [family for family, delta in diffs.items() if delta > tolerance]
    decreased = [family for family, delta in diffs.items() if delta < -tolerance]
    unchanged = [family for family, delta in diffs.items() if abs(delta) <= tolerance]
    if len(increased) != 1 or len(decreased) != 1 or len(unchanged) != len(families) - 2:
        return False, None, None, 0.0
    inc = increased[0]
    dec = decreased[0]
    if abs(diffs[inc] - grid_step) > tolerance or abs(diffs[dec] + grid_step) > tolerance:
        return False, None, None, 0.0
    transfer_mass = 0.5 * sum(abs(delta) for delta in diffs.values())
    return True, inc, dec, transfer_mass


def _edge_payload(
    a: dict[str, Any],
    b: dict[str, Any],
    families: list[str],
    grid_step: float,
    tolerance: float,
) -> dict[str, Any] | None:
    if b["cell_key"] < a["cell_key"]:
        a, b = b, a
    ok, increased, decreased, transfer_mass = _adjacent(
        a["reference_family_weights"], b["reference_family_weights"], families, grid_step, tolerance
    )
    if not ok:
        return None
    return {
        "cell_a": a["cell_key"],
        "cell_b": b["cell_key"],
        "weights_a": deepcopy(a["reference_family_weights"]),
        "weights_b": deepcopy(b["reference_family_weights"]),
        "increased_family": increased,
        "decreased_family": decreased,
        "transfer_mass": transfer_mass,
    }


def _components(nodes: Iterable[str], edges: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    node_set = set(nodes)
    adjacency = {node: set() for node in node_set}
    for edge in edges:
        a, b = edge["cell_a"], edge["cell_b"]
        if a in node_set and b in node_set:
            adjacency[a].add(b)
            adjacency[b].add(a)
    components: list[list[str]] = []
    unseen = set(node_set)
    while unseen:
        start = min(unseen)
        stack = [start]
        unseen.remove(start)
        members: list[str] = []
        while stack:
            node = stack.pop()
            members.append(node)
            for nxt in sorted(adjacency[node], reverse=True):
                if nxt in unseen:
                    unseen.remove(nxt)
                    stack.append(nxt)
        components.append(sorted(members))
    components.sort(key=lambda members: members[0])
    return [
        {"component_id": f"{prefix}:{index:04d}", "size": len(members), "members": members}
        for index, members in enumerate(components)
    ]


def _interpolation_fraction(v0: float, v1: float, tolerance: float) -> float | None:
    if abs(v0) <= tolerance:
        return 0.0
    if abs(v1) <= tolerance:
        return 1.0
    if v0 * v1 >= 0:
        return None
    value = -v0 / (v1 - v0)
    if value < -tolerance or value > 1 + tolerance:
        return None
    return min(1.0, max(0.0, value))


def _interpolated_weights(
    wa: dict[str, float], wb: dict[str, float], families: list[str], fraction: float
) -> dict[str, float]:
    result = {
        family: (1.0 - fraction) * wa[family] + fraction * wb[family]
        for family in families
    }
    # Clean representation-level noise while preserving the simplex sum.
    return {family: 0.0 if abs(value) < 1e-15 else value for family, value in result.items()}


def _crossing_payload(
    edge: dict[str, Any],
    a: dict[str, Any],
    b: dict[str, Any],
    families: list[str],
    field: str,
    tolerance: float,
) -> dict[str, Any] | None:
    va = float(a["band"][field])
    vb = float(b["band"][field])
    if field == "lower":
        stable_a, stable_b = va > tolerance, vb > tolerance
    else:
        stable_a, stable_b = va < -tolerance, vb < -tolerance
    if stable_a == stable_b:
        return None
    fraction = _interpolation_fraction(va, vb, tolerance)
    if fraction is None:
        return None
    return {
        "cell_a": edge["cell_a"],
        "cell_b": edge["cell_b"],
        "endpoint_field": f"band.{field}",
        "endpoint_value_a": va,
        "endpoint_value_b": vb,
        "interpolation_fraction": fraction,
        "estimated_reference_family_weights": _interpolated_weights(
            a["reference_family_weights"], b["reference_family_weights"], families, fraction
        ),
        "observed_cell": False,
    }


def _subject_geometry(
    cells: list[dict[str, Any]],
    families: list[str],
    grid_step: float,
    adjacency_tolerance: float,
    zero_tolerance: float,
) -> dict[str, Any]:
    by_key = {cell["cell_key"]: cell for cell in cells}
    all_edges: list[dict[str, Any]] = []
    for i, a in enumerate(cells):
        for b in cells[i + 1 :]:
            edge = _edge_payload(a, b, families, grid_step, adjacency_tolerance)
            if edge is not None:
                all_edges.append(edge)
    all_edges.sort(key=lambda edge: (edge["cell_a"], edge["cell_b"]))

    supported_keys = sorted(cell["cell_key"] for cell in cells if cell["supported"])
    supported_set = set(supported_keys)
    supported_edges = [
        edge for edge in all_edges if edge["cell_a"] in supported_set and edge["cell_b"] in supported_set
    ]
    support_boundary_edges: list[dict[str, Any]] = []
    for edge in all_edges:
        a_supported = edge["cell_a"] in supported_set
        b_supported = edge["cell_b"] in supported_set
        if a_supported ^ b_supported:
            supported = edge["cell_a"] if a_supported else edge["cell_b"]
            unsupported = edge["cell_b"] if a_supported else edge["cell_a"]
            support_boundary_edges.append(
                {
                    "supported_cell": supported,
                    "unsupported_cell": unsupported,
                    "transfer_mass": edge["transfer_mass"],
                }
            )

    degree = {key: 0 for key in supported_keys}
    for edge in supported_edges:
        degree[edge["cell_a"]] += 1
        degree[edge["cell_b"]] += 1

    supported_graph = {
        "supported_node_count": len(supported_keys),
        "supported_edge_count": len(supported_edges),
        "nodes": [
            {
                "cell_key": key,
                "reference_family_weights": deepcopy(by_key[key]["reference_family_weights"]),
                "band_sign_class": by_key[key]["band_sign_class"],
            }
            for key in supported_keys
        ],
        "edges": deepcopy(supported_edges),
        "connected_components": _components(supported_keys, supported_edges, "supported"),
        "isolated_nodes": sorted(key for key, count in degree.items() if count == 0),
    }

    sign_regions: dict[str, Any] = {}
    for sign_class in SIGN_CLASSES:
        keys = sorted(
            cell["cell_key"]
            for cell in cells
            if cell["supported"] and cell["band_sign_class"] == sign_class
        )
        sign_regions[sign_class] = {
            "node_count": len(keys),
            "component_count": len(_components(keys, supported_edges, sign_class)),
            "components": _components(keys, supported_edges, sign_class),
        }

    sign_class_edges: list[dict[str, Any]] = []
    positive_crossings: list[dict[str, Any]] = []
    negative_crossings: list[dict[str, Any]] = []
    gradients: list[dict[str, Any]] = []

    for edge in supported_edges:
        a = by_key[edge["cell_a"]]
        b = by_key[edge["cell_b"]]
        if a["band_sign_class"] != b["band_sign_class"]:
            sign_class_edges.append(
                {
                    "cell_a": edge["cell_a"],
                    "cell_b": edge["cell_b"],
                    "class_a": a["band_sign_class"],
                    "class_b": b["band_sign_class"],
                    "transfer_mass": edge["transfer_mass"],
                }
            )
        positive = _crossing_payload(edge, a, b, families, "lower", zero_tolerance)
        if positive is not None:
            positive_crossings.append(positive)
        negative = _crossing_payload(edge, a, b, families, "upper", zero_tolerance)
        if negative is not None:
            negative_crossings.append(negative)

        transfer_mass = float(edge["transfer_mass"])
        gradients.append(
            {
                "cell_a": edge["cell_a"],
                "cell_b": edge["cell_b"],
                "transfer_mass": transfer_mass,
                "increased_family": edge["increased_family"],
                "decreased_family": edge["decreased_family"],
                "point_estimate_slope": (float(b["point_delta"]) - float(a["point_delta"])) / transfer_mass,
                "band_lower_slope": (float(b["band"]["lower"]) - float(a["band"]["lower"])) / transfer_mass,
                "band_upper_slope": (float(b["band"]["upper"]) - float(a["band"]["upper"])) / transfer_mass,
            }
        )

    support_boundary_edges.sort(key=lambda edge: (edge["supported_cell"], edge["unsupported_cell"]))
    sign_class_edges.sort(key=lambda edge: (edge["cell_a"], edge["cell_b"]))
    positive_crossings.sort(key=lambda item: (item["cell_a"], item["cell_b"]))
    negative_crossings.sort(key=lambda item: (item["cell_a"], item["cell_b"]))
    gradients.sort(key=lambda item: (item["cell_a"], item["cell_b"]))

    component_sizes = [component["size"] for component in supported_graph["connected_components"]]
    absolute_slopes = [abs(item["point_estimate_slope"]) for item in gradients]
    return {
        "supported_graph": supported_graph,
        "sign_regions": sign_regions,
        "boundaries": {
            "support_edges": support_boundary_edges,
            "sign_class_edges": sign_class_edges,
            "positive_stability_zero_crossings": positive_crossings,
            "negative_stability_zero_crossings": negative_crossings,
        },
        "local_gradients": gradients,
        "geometry_summary": {
            "supported_component_count": len(component_sizes),
            "largest_supported_component_size": max(component_sizes) if component_sizes else 0,
            "support_boundary_edge_count": len(support_boundary_edges),
            "sign_class_boundary_edge_count": len(sign_class_edges),
            "positive_stability_boundary_count": len(positive_crossings),
            "negative_stability_boundary_count": len(negative_crossings),
            "local_gradient_edge_count": len(gradients),
            "max_absolute_point_estimate_slope": max(absolute_slopes) if absolute_slopes else None,
        },
    }


def analyze_surface_geometry(surface_report: dict[str, Any], geometry_spec: dict[str, Any]) -> dict[str, Any]:
    """Analyze evidence-supported discrete geometry of a v0.2.11 joint surface."""

    spec = _validate_spec(geometry_spec)
    source = _validate_surface(surface_report, spec["adjacency_tolerance"])
    surface = source["surface"]
    families = source["families"]
    grid_step = source["grid_step"]

    subjects = {
        subject: _subject_geometry(
            source["subjects"][subject],
            families,
            grid_step,
            spec["adjacency_tolerance"],
            spec["zero_tolerance"],
        )
        for subject in ("autonomy", "governance")
    }

    return {
        "schema_version": "0.2.12",
        "geometry_id": spec["geometry_id"],
        "generated_at": spec["generated_at"],
        "method": METHOD_ID,
        "source_surface": {
            "schema_version": surface["schema_version"],
            "surface_id": surface["surface_id"],
            "method": surface["method"],
        },
        "measurement_contract": deepcopy(surface.get("measurement_contract", {})),
        "families": families,
        "grid": {
            "grid_step": grid_step,
            "adjacency_method": "simplex_single_transfer_v1",
            "adjacency_tolerance": spec["adjacency_tolerance"],
        },
        "boundary_interpolation": {
            "positive_stability": "supported_edge_lower_band_zero_crossing_linear_v1",
            "negative_stability": "supported_edge_upper_band_zero_crossing_linear_v1",
            "zero_tolerance": spec["zero_tolerance"],
        },
        "conditioning": {
            "supported_cells_only_for_graph": True,
            "unsupported_cells_interpolated": False,
            "sign_boundary_interpolation_supported_edges_only": True,
            "local_gradients_supported_edges_only": True,
        },
        "subjects": subjects,
        "interpretation_boundary": "evidence_supported_discrete_surface_geometry",
        "non_authoritative": True,
    }


def _main(argv=None) -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Analyze CTCL-ITR evidence-supported joint-surface geometry."
    )
    parser.add_argument("--surface", required=True)
    parser.add_argument("--geometry", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    def load(path: str) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    report = analyze_surface_geometry(load(args.surface), load(args.geometry))
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    _main()

# CTCL-ITR v0.2.13 — Geometry Drift & Boundary Motion

**Date:** 2026-08-23

v0.2.13 adds a comparison layer above v0.2.12 surface geometry. Instead of asking only where the evidence-supported geometry is at one observation, the release asks how that geometry changes between two compatible measurements.

## Added

- `ctcl_itr.calibration_geometry_drift`
  - `compare_surface_geometry()`;
  - strict geometry-contract compatibility checks;
  - supported-domain persistence / gain / loss;
  - Jaccard overlap and net supported-cell change;
  - connected-component overlap links;
  - descriptive split / merge diagnostics;
  - persistent-cell sign-class transition matrix;
  - gained/lost supported cells kept separate from sign migration;
  - positive / negative stability-boundary nearest-point displacement;
  - support-frontier movement through supported endpoints only;
  - persistent supported-edge local-gradient drift;
  - appeared/disappeared gradient edges.
- CLI
  - `ctcl-itr-geometry-drift`.
- JSON Schema Draft 2020-12 contracts
  - `calibration-geometry-drift-spec.schema.json`;
  - `calibration-geometry-drift-report.schema.json`.
- Canonical later evidence snapshot and derived later geometry.
- Exact-regenerated geometry-drift reference report.
- Dedicated validator and TDD regression suite.

## Reference frame

The canonical comparison holds the same base snapshot fixed:

```text
G0 = Geometry(base -> current)
G1 = Geometry(base -> later)
```

The later evidence extends the research-family measurement depth while preserving a bracketed reliability crossing. This is important: simply increasing success rates without extending measurement depth can push a crossing outside observed support and make the geometry less measurable rather than more supported.

## Reference motion

```text
Autonomy supported cells      = 6 -> 8
Governance supported cells    = 6 -> 8
supported-cell Jaccard        = 0.75
component split / merge       = 0 / 0
crosses_zero -> positive      = 2 persistent cells
new positive supported cells  = 2
support frontier code weight  = 0.6 -> 0.8
```

Positive-stability boundary displacement:

```text
Autonomy:
  code     0.5528922561345437 -> 0.37677630955816144
  Δcode   -0.1761159465763823
  L1       0.3522318931527646

Governance:
  code     0.5 -> 0.35854728749637416
  Δcode   -0.14145271250362584
  L1       0.28290542500725163
```

Gradient drift:

```text
persistent matched gradient edges = 5
appeared gradient edges            = 2
disappeared gradient edges         = 0
mean |Δ point slope|               = 0.555555555555559
max  |Δ point slope|               ≈ 1.0
```

## Matching boundary

Boundary points are matched deterministically within positive or negative boundary type using greedy nearest $L_1$ distance with lexicographic tie-breaking.

This is deliberately described as a **matching convention**, not a proof of persistent boundary identity.

## Epistemic boundary

```text
Geometry Drift != Causal Mechanism
Boundary Motion != Capability Velocity
Support Expansion != Universal Capability Expansion
Component Split/Merge != Physical Phase Transition
Nearest Boundary Match != Persistent Boundary Identity
Gradient Drift != Global Derivative Drift
Geometry Drift Report != Authority
```

## Compatibility

- v0.2.12 geometry semantics unchanged;
- v0.2.11 joint surface unchanged;
- v0.2.10 mixture sensitivity unchanged;
- v0.2.9 resampling unchanged;
- v0.2.7 calibration unchanged;
- governance / TemporalEvent / authorization semantics unchanged;
- no new runtime dependency.

## Verification

Full repository inventory: `183 tests`.

Fresh segmented backward-compatibility run:

```text
legacy governance / observability:       47 passed
legacy signals / integrity / topology:   30 passed
v0.2.7 Horizon calibration:               20 passed
v0.2.8 robustness:                        18 passed
v0.2.9 uncertainty:                       17 passed
v0.2.10 mixture sensitivity:              10 passed
v0.2.11 joint surface:                    13 passed
v0.2.12 surface geometry:                 14 passed
v0.2.13 geometry drift:                   14 passed
---------------------------------------------------
total:                                   183 passed / 0 failures
```

Integration gates:

```text
validate_pack.py                 PASS
validate_metrics.py              PASS
validate_signals.py              PASS
validate_calibration.py          PASS
validate_robustness.py           PASS
validate_uncertainty.py          PASS
validate_mixture_sensitivity.py  PASS
validate_joint_surface.py        PASS
validate_surface_geometry.py     PASS
validate_geometry_drift.py       PASS
compileall                       PASS
editable install                 ctcl-itr 0.2.13
installed CLI exact regeneration PASS
```

## Next

A natural next slice is **Geometry Motion Stability / Multi-Snapshot Trajectories**: compare more than two geometry observations, distinguish persistent boundary velocity from one-step displacement, and detect support-region expansion/reversal without converting descriptive motion into a causal claim.

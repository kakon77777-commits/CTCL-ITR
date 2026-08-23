# CTCL-ITR v0.2.14 — Geometry Motion Stability & Multi-Snapshot Trajectories

**Date:** 2026-08-23

v0.2.14 extends v0.2.13 pairwise geometry drift to an ordered trajectory of three or more compatible v0.2.12 geometry observations.

## Added

- `ctcl_itr.calibration_geometry_trajectory`
  - `analyze_geometry_trajectory()`;
  - strict observation ordering and geometry-contract compatibility;
  - v0.2.13 pairwise drift delegation for every consecutive step;
  - supported-cell count trajectories and expansion/contraction reversals;
  - positive/negative stability-boundary lineages;
  - per-day signed boundary velocity and L1 speed;
  - finite-difference boundary acceleration;
  - per-family velocity-direction reversal counts;
  - component overlap lineages and lifespan;
  - sign-region persistence / support excursions;
  - supported-edge local-gradient trajectories and presence excursions.
- CLI: `ctcl-itr-geometry-trajectory`.
- Draft 2020-12 trajectory spec/report schemas.
- Canonical regressed third observation and exact-regenerated trajectory report.
- Dedicated validator and TDD regression suite.
- Historical v0.2.13 exact-version pack-test compatibility fix.

## Canonical trajectory

```text
G0 = Geometry(base -> current)   2026-08-23
G1 = Geometry(base -> later)     2026-08-24
G2 = Geometry(base -> regressed) 2026-08-25
```

`G2` intentionally reuses the current outcome counts under a new observation identity and the same deterministic resampling seed. It demonstrates reversal semantics; it is not a prediction.

For both Autonomy and Governance:

```text
supported cells             = 6 -> 8 -> 6
support step changes        = +2, -2
support directions          = expansion, contraction
support reversal count      = 1
component lineage           = 1 lineage spanning all 3 observations
support-excursion cells      = 2
gradient presence excursions = 2
```

Positive stability boundary:

```text
Autonomy code:
0.5528922561345437 -> 0.37677630955816144 -> 0.5528922561345437
velocity signs: negative -> positive
finite-difference code acceleration: +0.3522318931527646 / day^2

Governance code:
0.5 -> 0.35854728749637416 -> 0.5
velocity signs: negative -> positive
finite-difference code acceleration: +0.2829054250072517 / day^2
```

## Epistemic boundary

```text
Geometry Trajectory != Causal Mechanism
Finite-Difference Boundary Velocity != Capability Velocity
Finite-Difference Boundary Acceleration != Physical Acceleration
Support Reversal != Universal System Regression
Boundary Lineage != Persistent Boundary Identity
Component Lineage != Persistent Component Identity
Gradient Trajectory != Global Derivative Field
Trajectory Report != Authority
```

## Compatibility

- v0.2.13 pairwise drift semantics preserved;
- v0.2.12 surface geometry preserved;
- v0.2.11 joint surface and earlier calibration/uncertainty layers preserved;
- governance / TemporalEvent / authorization semantics unchanged;
- no new runtime dependency.

## Verification

Complete repository test inventory: **198**.

```text
77 + 20 + 18 + 17 + 10 + 13 + 14 + 14 + 15 = 198 passed / 0 failures
```

Integration:

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
validate_geometry_trajectory.py  PASS
compileall                       PASS
editable install                 ctcl-itr 0.2.14
installed CLI exact regeneration PASS
```

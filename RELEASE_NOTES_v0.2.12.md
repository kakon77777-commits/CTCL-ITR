# CTCL-ITR v0.2.12 — Surface Geometry & Stability Boundaries

**Date:** 2026-08-23

v0.2.12 adds a read-only geometry layer above the v0.2.11 joint sampling × reference-mixture uncertainty surface. It treats mixture cells as a discrete simplex graph and summarizes only evidence-supported geometry.

## Added

- `ctcl_itr.calibration_surface_geometry`
- method `simplex_supported_surface_geometry_v1`
- general k-family simplex single-transfer adjacency
- supported-cell graph construction
- connected supported-region components
- isolated supported-cell detection
- per-sign-class connected components:
  - `positive_band`
  - `negative_band`
  - `crosses_zero`
  - `zero_band`
- supported↔unsupported boundary edges
- adjacent supported sign-class boundary edges
- conservative positive-stability boundary interpolation using `band.lower = 0`
- conservative negative-stability boundary interpolation using `band.upper = 0`
- supported-edge point-estimate / lower-band / upper-band local slopes
- `ctcl-itr-surface-geometry` CLI
- Draft 2020-12 geometry spec/report schemas
- canonical v0.2.11-derived geometry report
- dedicated validator and TDD regression suite

## Simplex adjacency

For declared grid step $h$, two cells are adjacent only when exactly one grid step is transferred from one task family to another:

$$
\sum_f |w_f^{(i)}-w_f^{(j)}| = 2h.
$$

This supports two or more task families and does not rely on one-dimensional ordering.

## Evidence-support rule

Only cells with:

```text
resampling.support_status = supported
```

participate in the supported graph, sign regions, local gradients, or zero-crossing interpolation.

Unsupported cells may touch a supported cell and therefore define a **support boundary edge**, but the analyzer never interpolates through them.

## Reference geometry

The canonical v0.2.11 surface has nine two-family mixture cells per subject:

```text
5 crosses-zero supported cells
1 positive-band supported cell
3 unsupported cells
```

v0.2.12 derives, for both Autonomy and Governance:

```text
supported connected components = 1
largest supported component    = 6
crosses-zero components        = 1 (size 5)
positive-band components       = 1 (size 1)
support boundary edges         = 1
sign-class boundary edges      = 1
positive stability boundaries  = 1
negative stability boundaries  = 0
local gradient edges           = 5
```

Positive-stability crossing estimates:

```text
Autonomy   code ≈ 0.5528922561345437
Governance code = 0.5
```

The Autonomy crossing lies inside the adjacent supported 50/50→60/40 edge. The Governance lower-band endpoint at 50/50 is numerically zero within tolerance, so the boundary is the observed 50/50 endpoint.

## Local gradients

For adjacent supported cells $i,j$, transferred mass is:

$$
m_{ij}=\frac12\sum_f|w_f^{(i)}-w_f^{(j)}|.
$$

Point-estimate slope is:

$$
g_{ij}=\frac{\Delta H_j-\Delta H_i}{m_{ij}}.
$$

Reference maximum absolute point-estimate slopes:

```text
Autonomy   ≈ 2.3865546218487226 per unit transferred mass
Governance ≈ 2.6324786324786325 per unit transferred mass
```

These are discrete edge-local diagnostics, not global derivatives.

## Interpretation boundary

```text
Surface Geometry != Causal Geometry
Interpolated Boundary != Observed Cell
Unsupported Region != Negative Region
Local Gradient != Global Derivative
Geometry Report != Authority
```

The output is descriptive and non-authoritative. It does not mutate governance state, authorization, resampling, Horizon calibration, or mixture-comparison semantics.

## Compatibility

- v0.2.11 joint-surface semantics preserved;
- v0.2.10 reference-mixture sensitivity preserved;
- v0.2.9 outcome-resampling semantics preserved;
- v0.2.8 robustness and v0.2.7 calibration preserved;
- governance/runtime authorization semantics unchanged;
- no TemporalEvent schema change;
- no new runtime dependency.

## Verification

Complete release testing is executed in eight disjoint groups:

```text
43 + 34 + 20 + 18 + 17 + 10 + 13 + 14 = 169 passed / 0 failures
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
compileall                       PASS
editable install                 ctcl-itr 0.2.12
installed CLI                    PASS
```

## Next

A natural next slice is geometry stability across repeated surface snapshots: compare component topology, boundary movement, supported-domain expansion/contraction, and local-gradient changes without treating topology changes as causal attribution.

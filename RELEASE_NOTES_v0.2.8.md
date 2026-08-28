# CTCL-ITR v0.2.8 — Calibration Robustness, Drift & Task-Family Profiles

**Date:** 2026-08-22

v0.2.8 adds a robustness layer above the evidence-backed v0.2.7 Horizon calibrator. It makes task-family composition, backend identity, benchmark version, and agent configuration explicit when comparing calibrated Horizons across snapshots.

## Added

- `ctcl_itr.calibration_robustness`
  - `build_calibration_snapshot()`;
  - `compare_calibration_snapshots()`;
  - task-family contract validation;
  - observed trial-mass weighting;
  - fixed-reference family weighting;
  - support-intersection mixture curves;
  - no-extrapolation interpolation;
  - pairwise drift decomposition;
  - task-family Horizon deltas and ranges;
  - family-direction agreement;
  - composition total-variation distance;
  - context diagnostics for backend / benchmark / agent-config changes.
- CLI
  - `ctcl-itr-calibration-robustness`.
- JSON Schema Draft 2020-12 contracts
  - `calibration-snapshot.schema.json`;
  - `calibration-comparison-spec.schema.json`;
  - `calibration-robustness-report.schema.json`.
- canonical base/current task-family snapshots;
- fixed 50/50 reference-mixture comparison spec;
- exact regenerated robustness report;
- dedicated `validate_robustness.py` validator;
- design / implementation plan and full release validation evidence.

## Core decomposition

For subject $s$ and task family $f$:

$$
H_{s,f}^{(0)},\quad H_{s,f}^{(1)},\quad
\Delta H_{s,f}=H_{s,f}^{(1)}-H_{s,f}^{(0)}.
$$

Observed family weights are derived from trial mass:

$$
w^{obs}_{s,f}=\frac{N_{s,f}}{\sum_j N_{s,j}}.
$$

The observed-mixture Horizon delta is:

$$
\Delta H^{obs}_s=H^{obs,(1)}_s-H^{obs,(0)}_s.
$$

Under one fixed reference family mixture:

$$
\Delta H^{adj}_s=H^{ref,(1)}_s-H^{ref,(0)}_s.
$$

The release reports the descriptive composition residual:

$$
R^{comp}_s=\Delta H^{obs}_s-\Delta H^{adj}_s.
$$

This is a standardization residual, not a causal estimate.

## Reference composition-illusion scenario

The canonical example intentionally changes trial composition:

```text
base:    code=80%, research=20%
current: code=20%, research=80%
reference mixture: code=50%, research=50%
```

Both task families improve within-family, yet the observed-mixture headline decreases because the current snapshot is dominated by the lower-Horizon `research` family.

Reference results:

```text
autonomy observed_mix_delta        = -0.6000000000000005
autonomy composition_adjusted_delta =  0.8470588235294114
governance observed_mix_delta        = -0.39999999999999947
governance composition_adjusted_delta = 0.8923076923076918
composition_total_variation           = 0.6
family_direction_agreement             = 1.0
comparison_kind                        = cross_backend
```

The example demonstrates why:

```text
Observed Horizon Delta != Capability Delta
```

## Support boundary

The mixture engine:

- linearly interpolates each family PAVA curve only inside observed support;
- intersects the supported depth range of every positively weighted family;
- refuses to emit a mixture Horizon when common support is absent;
- refuses unsupported target-reliability crossings;
- does not impute missing task families.

## Context diagnostics

A comparison records:

```text
backend_changed
benchmark_version_changed
agent_config_changed
family_set_changed
comparison_kind
```

The reference scenario is labeled `cross_backend` because the backend changes while benchmark version, agent configuration, and family set remain stable.

## Epistemic boundary

```text
Calibration Drift != Capability Attribution
Composition-Adjusted Delta != Backend-Causal Effect
Cross-Backend Comparison != Longitudinal Model Drift
Task-Family Average != Universal Capability
Robustness Report != Authority
```

The fixed-reference mixture controls one explicit composition axis. It does not remove hidden task difficulty changes, scaffold effects, backend effects, evaluator drift, or other confounding.

## External methodology context

Current public task-horizon work estimates reliability as a function of task difficulty/duration and has explicitly warned in 2026 that Horizon estimates become more sensitive to analysis assumptions as task suites saturate. CTCL-ITR v0.2.8 is informed by that measurement problem but deliberately does **not** claim methodological equivalence to METR and does not replace v0.2.7's empirical PAVA method with a logistic fit.

## Compatibility

- v0.2.7 calibration suites/profiles unchanged;
- v0.2.6 Horizon/signal contracts unchanged;
- v0.2.5 governance metrics unchanged;
- v0.2.4 durable store unchanged;
- TemporalEvent and governance schemas unchanged;
- no authorization semantics change;
- no new runtime dependency.

## Verification

Complete pytest coverage was executed as four disjoint groups because long monolithic invocations can exceed the execution wrapper budget:

```text
legacy governance / observability:     43 passed
legacy signals / integrity / topology: 34 passed
v0.2.7 Horizon calibration:             20 passed
v0.2.8 robustness:                      18 passed
--------------------------------------------------
total:                                 115 passed
failures:                                0
```

Validators and compilation:

```text
validator/validate_pack.py         PASS
validator/validate_metrics.py      PASS
validator/validate_signals.py      PASS
validator/validate_calibration.py  PASS
validator/validate_robustness.py   PASS
python -m compileall -q src validator  PASS
```

Installed package / CLI:

```text
ctcl-itr 0.2.8
ctcl-itr-calibration-robustness ...  PASS
```

## Next

A natural next slice is uncertainty and repeated-snapshot stability above the task-family layer: bootstrap or resampling profiles, drift bands, backend/scaffold stratification, and explicit sensitivity to reference-mixture choices without silently changing the v0.2.8 comparison semantics.

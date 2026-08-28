# CTCL-ITR v0.2.7 — Horizon Calibration & Evidence Profiles

**Date:** 2026-08-22

v0.2.7 replaces manually entered v0.2.6 Horizon depths with a reproducible, evidence-backed reference calibration pipeline.

## Added

- `ctcl_itr.horizon_calibration`
  - grouped repeated-trial evidence;
  - deterministic duplicate-depth aggregation;
  - empirical binomial success rates;
  - Wilson point intervals;
  - weighted non-increasing Pool Adjacent Violators Algorithm (PAVA);
  - target-reliability crossing by interpolation;
  - explicit insufficient-support states;
  - no unsupported Horizon extrapolation.
- v0.2.6 assessment bridge
  - emits a compatible `GovernanceHorizonAssessment` only when both autonomy and governance evidence are sufficiently supported;
  - generated assessment can be consumed unchanged by the v0.2.6 signal engine.
- CLI
  - `ctcl-itr-horizon-calibrate --suite <json>`.
- Draft 2020-12 schemas
  - `horizon-calibration-suite.schema.json`;
  - `horizon-evidence-profile.schema.json`.
- canonical repeated-trial suite and exact regenerated evidence profile.
- dedicated calibration validator and TDD regression suite.

## Reference method

```text
monotone_binomial_pava_v1
```

The reference method models reliability as a monotone empirical function of `interaction_depth`. It reports Wilson intervals at individual evidence depths but does not mislabel them as a Horizon confidence interval.

The method refuses to emit a Horizon when the target reliability is not bracketed by the observed evidence range.

## Reference result

Target reliability:

```text
p = 0.90
```

Evidence:

```text
autonomy:  4 depths / 80 trials
governance: 4 depths / 80 trials
```

Calibrated result:

```text
H_A = 12 interaction-depth units
H_G = 9 interaction-depth units
Delta_AG = 3
```

These values match the v0.2.6 reference assessment, but are now derived from repeated evidence rather than entered directly.

## Epistemic boundary

```text
Calibration != Authority
Evidence Profile != Policy Decision
Calibrated Horizon != Automatic Enforcement
```

The reference PAVA method is intentionally transparent and dependency-free. It does not claim methodological equivalence to external time-horizon benchmarks, does not use logistic extrapolation, and does not infer Horizon from a single runtime latency statistic.

## Verification

The v0.2.6 regression suite and all v0.2.7 tests pass. Legacy pack, metrics, and signals validators pass alongside the new calibration validator. Editable installation provides `ctcl-itr 0.2.7` and the installed calibration CLI reproduces the canonical evidence profile.

## Next

A natural next slice is calibration uncertainty / cross-suite robustness: repeated calibration snapshots, drift comparison, task-family stratification, and optional parametric calibration methods kept behind explicit method identifiers.

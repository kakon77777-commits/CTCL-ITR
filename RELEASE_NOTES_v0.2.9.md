# CTCL-ITR v0.2.9 — Calibration Uncertainty, Resampling & Drift Bands

**Date:** 2026-08-23

Adds deterministic, auditable outcome-sampling uncertainty above v0.2.8.

## Added
- `ctcl_itr.calibration_uncertainty`;
- deterministic SHA-256 counter Bernoulli resampling;
- fixed trial counts and fixed task-family composition during resampling;
- v0.2.7 recalibration and v0.2.8 comparison on every replicate;
- 90% percentile resampling bands;
- supported-replicate count/rate;
- explicit unsupported-reason counts;
- empirical positive/negative/zero sign shares;
- family-delta bands;
- `ctcl-itr-calibration-uncertainty` CLI;
- Draft 2020-12 spec/report schemas;
- canonical 256-replicate reference report;
- dedicated validator and TDD suite.

## Interpretation boundary
`Bootstrap sign share != posterior probability`
`Resampling band != causal effect`
`Conditional outcome-sampling uncertainty != composition uncertainty`
`Uncertainty report != authority`

The reference method is informed by hierarchical-bootstrap practice in contemporary Time Horizon evaluation, but it is a distinct count-level empirical-binomial resampling contract and does not claim methodological equivalence.

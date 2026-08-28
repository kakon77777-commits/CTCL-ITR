# CTCL-ITR v0.2.10 — Reference-Mixture Sensitivity & Uncertainty Decomposition

**Date:** 2026-08-23

v0.2.10 extends the calibration measurement stack above v0.2.9 by varying the fixed reference task-family composition used by v0.2.8. It keeps reference-mixture sensitivity distinct from v0.2.9 outcome-sampling uncertainty.

## Added

- `ctcl_itr.calibration_mixture_sensitivity`
  - deterministic bounded integer-simplex reference-mixture grids;
  - support-preserving delegation to v0.2.8 comparison semantics;
  - raw v0.2.8 snapshot-spec and calibrated-snapshot inputs;
  - per-mixture adjusted Horizon drift;
  - supported-grid fraction;
  - sensitivity min/max/span and argmin/argmax mixtures;
  - positive/negative/zero shares across supported mixtures;
  - unsupported-reason aggregation;
  - optional v0.2.9 uncertainty bridge with strict identity checks;
  - separate sampling-band width and mixture-sensitivity span axes.
- CLI
  - `ctcl-itr-mixture-sensitivity`.
- JSON Schema Draft 2020-12 contracts
  - `calibration-mixture-sensitivity-spec.schema.json`;
  - `calibration-mixture-sensitivity-report.schema.json`.
- canonical 9-point two-family simplex scan;
- exact regenerated reference report;
- dedicated validator and TDD regression suite.

## Core boundary

```text
Sampling uncertainty != reference-mixture sensitivity
Reference-mixture sensitivity != composition drift
Sensitivity span != causal effect
Uncertainty axes != additive total uncertainty
Sensitivity report != authority
```

The release intentionally reports an uncertainty/sensitivity vector rather than claiming:

$$
U_{total}=U_{sampling}+U_{mixture}.
$$

Reference representation:

$$
\mathbf U_s=(W^{sampling}_s,\;S^{mixture}_s).
$$

`W_sampling` is the v0.2.9 percentile-band width at the declared v0.2.8 reference mixture. `S_mixture` is the supported range of v0.2.8 composition-adjusted drift over the declared v0.2.10 simplex grid.

## Reference grid

```text
families = [code, research]
grid_step = 0.1
minimum_family_weight = 0.1
total candidate mixtures = 9
```

Reference results:

```text
Autonomy:
  supported grid = 6 / 9
  mixture sensitivity span = 0.6382047071702237
  sampling band width @ reference = 2.2120491350754494
  larger reported axis = sampling
  supported-mixture positive share = 1.0

Governance:
  supported grid = 6 / 9
  mixture sensitivity span = 0.7033639143730888
  sampling band width @ reference = 1.9594474153297696
  larger reported axis = sampling
  supported-mixture positive share = 1.0
```

The three most code-heavy candidate mixtures are unsupported in the reference case because existing v0.2.8 support/bracketing rules refuse to extrapolate a target crossing that the evidence does not support.

## Interpretation

In the canonical example, changing the reference mixture within the supported grid moves the composition-adjusted drift materially, but less than the width of the v0.2.9 outcome-sampling band at the declared 50/50 reference mixture.

This does **not** prove that sampling uncertainty is universally more important. The `larger_reported_axis` field is descriptive only for the declared contracts and examples.

## Methodology context

Contemporary task-horizon work has emphasized both bootstrap uncertainty and sensitivity to modeling/task-suite choices as benchmarks saturate. v0.2.10 addresses one explicit composition-choice axis using transparent standardization. It does not claim methodological equivalence to external time-horizon pipelines and does not infer a privileged scientific or ethical reference mixture.

## Compatibility

- v0.2.9 resampling semantics unchanged;
- v0.2.8 point-estimate robustness semantics unchanged;
- v0.2.7 PAVA calibration unchanged;
- v0.2.6 signals and all governance/runtime layers remain compatible;
- no TemporalEvent or authorization schema change;
- no authority mutation;
- no new runtime dependency.

## Verification

Final v0.2.10 code tree was verified in six disjoint pytest groups:

```text
legacy governance / observability:      43 passed
legacy signals / integrity / topology:  34 passed
v0.2.7 Horizon calibration:              20 passed
v0.2.8 robustness:                       18 passed
v0.2.9 uncertainty:                      17 passed
v0.2.10 mixture sensitivity:             10 passed
---------------------------------------------------
total:                                  142 passed / 0 failures
```

Integration gates:

```text
validator/validate_pack.py                    PASS
validator/validate_metrics.py                 PASS
validator/validate_signals.py                 PASS
validator/validate_calibration.py             PASS
validator/validate_robustness.py              PASS
validator/validate_uncertainty.py             PASS
validator/validate_mixture_sensitivity.py     PASS
python -m compileall -q src validator         PASS
editable install: ctcl-itr 0.2.10
installed CLI: PASS
```

## Next

A natural next slice is a joint two-axis sensitivity surface: pair outcome resampling with multiple reference-mixture choices under one explicitly conditioned design, or add benchmark/task-family selection diagnostics without collapsing the axes into a false scalar total uncertainty.

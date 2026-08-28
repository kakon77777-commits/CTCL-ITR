# CTCL-ITR v0.2.11 — Joint Sampling × Mixture Sensitivity Surface

**Date:** 2026-08-23

v0.2.11 combines the two uncertainty axes that were previously analyzed separately:

- v0.2.9: outcome-sampling uncertainty at one fixed reference mixture;
- v0.2.10: reference-mixture sensitivity at fixed observed outcomes.

The new joint surface reuses one resampled base/current evidence realization across every mixture cell in a replicate, preserving cross-cell dependence and producing conditional drift bands across the supported reference-mixture domain.

## Added

- `ctcl_itr.calibration_joint_surface`
- `ctcl_itr.calibration_joint_surface_core`
- method `joint_empirical_binomial_simplex_surface_v1`
- deterministic outcome resampling inherited from `stratified_empirical_binomial_sha256_v1`
- bounded simplex reference-mixture grid inherited from `simplex_grid_reference_mixture_v1`
- per-cell point estimates
- per-cell supported replicate counts and fractions
- per-cell percentile resampling bands
- per-cell empirical sign shares
- per-cell unsupported reason counts
- band-sign classes:
  - `positive_band`
  - `negative_band`
  - `crosses_zero`
  - `zero_band`
  - `unsupported`
- subject-level support/sign region summaries
- `ctcl-itr-joint-surface` CLI
- Draft 2020-12 spec/report schemas
- canonical 256-replicate × 9-mixture reference report
- dedicated `validate_joint_surface.py`
- TDD regression suite

## Core sampling rule

For replicate $r$, base/current outcome counts are resampled once:

$$
(E_0^{(r)},E_1^{(r)}).
$$

That same pair is evaluated over every legal reference mixture $w$:

$$
(E_0^{(r)},E_1^{(r)},w)
\mapsto
\Delta H^{(r)}(w).
$$

Mixture cells are therefore not independent random experiments.

## Reference result

The canonical report uses:

```text
replicates = 256
interval_p = 0.90
grid points = 9
```

Autonomy:

```text
point-supported cells = 6
resampling-supported cells = 6
positive-band cells = 1
crosses-zero cells = 5
unsupported cells = 3
```

Governance:

```text
point-supported cells = 6
resampling-supported cells = 6
positive-band cells = 1
crosses-zero cells = 5
unsupported cells = 3
```

For both subjects, the reference mixture domain therefore contains a region where the 90% resampling band crosses zero, a narrower region where the entire band is positive, and a more code-heavy region where the evidence no longer supports a band at all.

## Interpretation boundary

```text
Joint Surface != Causal Truth
Surface Cell != Independent Experiment
Sign-Stable Region != Guaranteed Improvement
Unsupported Region != Negative Drift
Joint Uncertainty Surface != Authority
```

The report is descriptive and non-authoritative. It does not mutate governance state or authorization.

## Compatibility

- v0.2.10 mixture-sensitivity semantics unchanged;
- v0.2.9 outcome-resampling semantics unchanged;
- v0.2.8 robustness comparison unchanged;
- v0.2.7 Horizon calibration unchanged;
- governance/runtime layers remain compatible;
- no new runtime dependency.

## Verification

Final release tree is verified as seven disjoint pytest groups:

```text
43 + 34 + 20 + 18 + 17 + 10 + 13 = 155 passed / 0 failures
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
compileall                       PASS
editable install                 ctcl-itr 0.2.11
installed CLI                    PASS
```

## Next

A natural next slice is surface geometry and stability boundaries: contiguous supported regions, sign-boundary interpolation, sensitivity gradients, and conservative region summaries without inventing evidence beyond supported grid cells.

import copy
import json
from pathlib import Path

import pytest

from ctcl_itr.calibration_uncertainty import (
    CalibrationUncertaintyError,
    bootstrap_calibration_uncertainty,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def uncertainty_spec(**overrides):
    spec = {
        "schema_version": "0.2.9",
        "uncertainty_id": "uncertainty:reference",
        "generated_at": "2026-08-23T00:30:00+00:00",
        "method": "stratified_empirical_binomial_sha256_v1",
        "seed": "ctcl-itr-v0.2.9-reference",
        "replicates": 40,
        "interval_p": 0.90,
        "minimum_supported_fraction": 0.50,
    }
    spec.update(overrides)
    return spec


def inputs():
    return (
        load("calibration_snapshot_base.json"),
        load("calibration_snapshot_current.json"),
        load("calibration_comparison_spec.json"),
    )


def test_same_seed_produces_exact_same_uncertainty_report():
    base, current, comparison = inputs()
    spec = uncertainty_spec()
    a = bootstrap_calibration_uncertainty(base, current, comparison, spec)
    b = bootstrap_calibration_uncertainty(base, current, comparison, spec)
    assert a == b


def test_different_seed_changes_resampled_summary():
    base, current, comparison = inputs()
    a = bootstrap_calibration_uncertainty(base, current, comparison, uncertainty_spec(seed="seed-a"))
    b = bootstrap_calibration_uncertainty(base, current, comparison, uncertainty_spec(seed="seed-b"))
    assert a["subjects"]["autonomy"]["bands"] != b["subjects"]["autonomy"]["bands"]


def test_bootstrap_does_not_mutate_inputs():
    base, current, comparison = inputs()
    spec = uncertainty_spec()
    originals = tuple(copy.deepcopy(x) for x in (base, current, comparison, spec))
    bootstrap_calibration_uncertainty(base, current, comparison, spec)
    assert (base, current, comparison, spec) == originals


@pytest.mark.parametrize(
    "patch",
    [
        {"replicates": 0},
        {"interval_p": 1.2},
        {"minimum_supported_fraction": 0.0},
        {"method": "unknown"},
        {"seed": ""},
    ],
)
def test_invalid_uncertainty_contract_is_rejected(patch):
    base, current, comparison = inputs()
    with pytest.raises(CalibrationUncertaintyError):
        bootstrap_calibration_uncertainty(base, current, comparison, uncertainty_spec(**patch))

def test_point_estimate_and_conditioning_preserve_v028_semantics():
    base, current, comparison = inputs()
    report = bootstrap_calibration_uncertainty(base, current, comparison, uncertainty_spec(replicates=60))
    autonomy = report["subjects"]["autonomy"]
    assert autonomy["point_estimate"]["observed_mix_delta"] == pytest.approx(-0.6000000000000005)
    assert autonomy["point_estimate"]["composition_adjusted_delta"] == pytest.approx(0.8470588235294114)
    assert autonomy["point_estimate"]["composition_total_variation"] == 0.6
    assert report["conditioning"] == {
        "composition_resampled": False,
        "observed_family_weights_fixed": True,
        "reference_family_weights_fixed": True,
        "trial_counts_fixed": True,
        "success_counts_resampled": True,
    }


def test_supported_bands_are_ordered_and_sign_shares_are_descriptive():
    base, current, comparison = inputs()
    report = bootstrap_calibration_uncertainty(base, current, comparison, uncertainty_spec(replicates=100))
    for subject in ("autonomy", "governance"):
        adjusted = report["subjects"][subject]["bands"]["composition_adjusted_delta"]
        assert adjusted["support_status"] == "supported"
        assert 0.0 < adjusted["supported_fraction"] <= 1.0
        band = adjusted["band"]
        assert band["lower"] <= band["median"] <= band["upper"]
        shares = report["subjects"][subject]["sign_shares"]["composition_adjusted_delta"]
        assert shares is not None
        assert sum(shares.values()) == pytest.approx(1.0)
        assert set(shares) == {"positive", "negative", "zero"}


def test_high_minimum_supported_fraction_can_suppress_unstable_band():
    base, current, comparison = inputs()
    report = bootstrap_calibration_uncertainty(
        base, current, comparison, uncertainty_spec(replicates=100, minimum_supported_fraction=1.0)
    )
    # Low-trial research/code slices make at least one mixture quantity unsupported in some resamples.
    candidates = [
        report["subjects"][subject]["bands"][name]
        for subject in ("autonomy", "governance")
        for name in ("observed_mix_delta", "composition_adjusted_delta")
    ]
    assert any(item["support_status"] == "insufficient_resampling_support" for item in candidates)
    for item in candidates:
        if item["support_status"] == "insufficient_resampling_support":
            assert item["band"] is None
            assert item["mean"] is None

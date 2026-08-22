def family_suite(calibration_id, depths, rates, *, trials, calibrated_at, scope_id="scope:reference"):
    successes = {
        subject: [round(rate * trials) for rate in rates[subject]]
        for subject in ("autonomy", "governance")
    }
    return {
        "schema_version": "0.2.7",
        "calibration_id": calibration_id,
        "calibrated_at": calibrated_at,
        "measurement_contract": {
            "unit": "interaction_depth",
            "reliability_p": 0.9,
            "scope_id": scope_id,
            "assessment_method": "monotone_binomial_pava_v1",
        },
        "evidence_confidence_p": 0.9,
        "minimums": {
            "min_distinct_depths": 4,
            "min_total_trials": trials * 4,
            "min_trials_per_depth": trials,
        },
        "subjects": {
            subject: [
                {
                    "depth": depth,
                    "trials": trials,
                    "successes": success,
                    "evidence_refs": [f"evidence:{calibration_id}:{subject}:{depth}"],
                }
                for depth, success in zip(depths[subject], successes[subject])
            ]
            for subject in ("autonomy", "governance")
        },
    }


def snapshot_spec(*, current=False, disjoint_support=False):
    observed_at = "2026-08-22T00:00:00+00:00" if not current else "2026-08-23T00:00:00+00:00"
    contract = {
        "unit": "interaction_depth",
        "reliability_p": 0.9,
        "scope_id": "scope:reference",
        "assessment_method": "monotone_binomial_pava_v1",
    }

    if disjoint_support:
        code_depths = {"autonomy": [10, 12, 14, 16], "governance": [9, 11, 13, 15]}
        research_depths = {"autonomy": [2, 4, 6, 8], "governance": [1, 3, 5, 7]}
    else:
        code_depths = {"autonomy": [4, 8, 12, 16], "governance": [3, 6, 9, 12]}
        research_depths = {"autonomy": [2, 4, 6, 8], "governance": [1, 3, 5, 7]}

    if not current:
        code_trials = 40
        research_trials = 10
        code_rates = {"autonomy": [1.0, 0.95, 0.90, 0.50], "governance": [1.0, 0.95, 0.90, 0.50]}
        research_rates = {"autonomy": [1.0, 1.0, 0.90, 0.50], "governance": [1.0, 1.0, 0.90, 0.50]}
        backend = "backend-alpha"
        suffix = "base"
    else:
        code_trials = 10
        research_trials = 40
        code_rates = {"autonomy": [1.0, 1.0, 1.0, 0.70], "governance": [1.0, 1.0, 1.0, 0.70]}
        research_rates = {"autonomy": [1.0, 1.0, 0.95, 0.70], "governance": [1.0, 1.0, 0.95, 0.70]}
        backend = "backend-beta"
        suffix = "current"

    code = family_suite(
        f"family:code:{suffix}",
        code_depths,
        code_rates,
        trials=code_trials,
        calibrated_at=observed_at,
    )
    research = family_suite(
        f"family:research:{suffix}",
        research_depths,
        research_rates,
        trials=research_trials,
        calibrated_at=observed_at,
    )

    return {
        "schema_version": "0.2.8",
        "snapshot_id": f"snapshot:{suffix}",
        "observed_at": observed_at,
        "backend_id": backend,
        "benchmark_id": "benchmark:reference",
        "benchmark_version": "1.0",
        "agent_config_id": "agent-config:stable",
        "measurement_contract": contract,
        "family_suites": {"code": code, "research": research},
    }


def comparison_spec():
    return {
        "schema_version": "0.2.8",
        "comparison_id": "comparison:base-current",
        "generated_at": "2026-08-23T00:10:00+00:00",
        "reference_family_weights": {"code": 0.5, "research": 0.5},
    }

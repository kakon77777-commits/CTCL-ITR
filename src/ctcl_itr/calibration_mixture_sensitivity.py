"""Public facade for CTCL-ITR v0.2.10 reference-mixture sensitivity."""

from __future__ import annotations

from .calibration_mixture_sensitivity_common import (
    CalibrationMixtureSensitivityError,
    METHOD_ID,
)
from .calibration_mixture_sensitivity_analyze import analyze_reference_mixture_sensitivity

__all__ = [
    "CalibrationMixtureSensitivityError",
    "METHOD_ID",
    "analyze_reference_mixture_sensitivity",
]

def _main(argv=None) -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Scan CTCL-ITR v0.2.8 reference-mixture sensitivity and compare it with v0.2.9 sampling uncertainty."
    )
    parser.add_argument("--base", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--sensitivity", required=True)
    parser.add_argument("--uncertainty-report")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    def load(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    report = analyze_reference_mixture_sensitivity(
        load(args.base),
        load(args.current),
        load(args.comparison),
        load(args.sensitivity),
        load(args.uncertainty_report) if args.uncertainty_report else None,
    )
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    _main()

"""Task-family calibration robustness and drift analysis for CTCL-ITR v0.2.8."""

from __future__ import annotations

from .calibration_robustness_common import CalibrationRobustnessError
from .calibration_robustness_snapshot import build_calibration_snapshot
from .calibration_robustness_compare import compare_calibration_snapshots

__all__ = [
    "CalibrationRobustnessError",
    "build_calibration_snapshot",
    "compare_calibration_snapshots",
]

def _main(argv=None) -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Compare CTCL-ITR task-family Horizon calibration snapshots with composition standardization."
    )
    parser.add_argument("--base", required=True, help="Path to base CalibrationSnapshot JSON")
    parser.add_argument("--current", required=True, help="Path to current CalibrationSnapshot JSON")
    parser.add_argument("--spec", required=True, help="Path to CalibrationComparisonSpec JSON")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    base_spec = json.loads(Path(args.base).read_text(encoding="utf-8"))
    current_spec = json.loads(Path(args.current).read_text(encoding="utf-8"))
    comparison_spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    report = compare_calibration_snapshots(
        build_calibration_snapshot(base_spec),
        build_calibration_snapshot(current_spec),
        comparison_spec,
    )
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    _main()

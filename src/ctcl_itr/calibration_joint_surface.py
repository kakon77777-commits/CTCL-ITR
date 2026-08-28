"""Public facade for CTCL-ITR v0.2.11 joint calibration surface."""

from .calibration_joint_surface_core import (
    CalibrationJointSurfaceError,
    METHOD_ID,
    analyze_joint_uncertainty_surface,
)

__all__ = [
    "CalibrationJointSurfaceError",
    "METHOD_ID",
    "analyze_joint_uncertainty_surface",
]


def _main(argv=None) -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Evaluate CTCL-ITR joint outcome-resampling x reference-mixture calibration surface."
    )
    parser.add_argument("--base", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--surface", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    def load(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    report = analyze_joint_uncertainty_surface(
        load(args.base),
        load(args.current),
        load(args.comparison),
        load(args.surface),
    )
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    _main()

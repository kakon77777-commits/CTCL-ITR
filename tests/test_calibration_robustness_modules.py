import importlib


def test_robustness_internal_modules_exist_and_facade_exports_public_api():
    for name in (
        'ctcl_itr.calibration_robustness_snapshot',
        'ctcl_itr.calibration_robustness_mixture',
        'ctcl_itr.calibration_robustness_compare',
    ):
        importlib.import_module(name)

    facade = importlib.import_module('ctcl_itr.calibration_robustness')
    assert callable(facade.build_calibration_snapshot)
    assert callable(facade.compare_calibration_snapshots)
    assert issubclass(facade.CalibrationRobustnessError, ValueError)

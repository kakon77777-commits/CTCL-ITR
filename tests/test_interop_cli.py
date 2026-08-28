import tomllib
from pathlib import Path


def test_pyproject_exposes_observability_export_cli_entry_points():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = project["project"]["scripts"]
    assert scripts["ctcl-itr-cloudevents"] == "ctcl_itr.interop.cloudevents:_main"
    assert scripts["ctcl-itr-otel"] == "ctcl_itr.interop.opentelemetry:_main"


def test_module_clis_do_not_emit_runpy_runtime_warning():
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    demo = root / "examples" / "multi_agent_branch_join.events.jsonl"
    for module in ["ctcl_itr.interop.cloudevents", "ctcl_itr.interop.opentelemetry"]:
        completed = subprocess.run(
            [sys.executable, "-m", module, str(demo)],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        assert "RuntimeWarning" not in completed.stderr

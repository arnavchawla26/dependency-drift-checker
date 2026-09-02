import json
import subprocess
import sys
from pathlib import Path

from depdrift.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_main_text_output(capsys):
    exit_code = main([str(FIXTURE)])
    out = capsys.readouterr().out
    assert exit_code == 0  # --fail-on-drift not passed, so drift alone isn't an error
    assert "black" in out
    assert "jinja2" in out


def test_main_fail_on_drift_returns_1_when_drift_found():
    exit_code = main([str(FIXTURE), "--fail-on-drift"])
    assert exit_code == 1


def test_main_fail_on_drift_returns_0_when_clean(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")
    (tmp_path / "app.py").write_text("import requests\n")

    exit_code = main([str(tmp_path), "--fail-on-drift"])
    assert exit_code == 0


def test_main_json_output_is_valid_and_matches_analysis(capsys):
    exit_code = main([str(FIXTURE), "--format", "json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    assert set(payload["unused_declared"]) == {"black", "python-dateutil"}
    assert set(payload["undeclared_imports"]) == {"jinja2"}


def test_main_markdown_output_has_headers(capsys):
    main([str(FIXTURE), "--format", "markdown"])
    out = capsys.readouterr().out
    assert "## Declared but unused" in out
    assert "## Imported but undeclared" in out


def test_main_ignore_flags(capsys):
    exit_code = main(
        [
            str(FIXTURE),
            "--fail-on-drift",
            "--ignore-declared",
            "black",
            "--ignore-declared",
            "python-dateutil",
            "--ignore-import",
            "jinja2",
        ]
    )
    assert exit_code == 0


def test_main_nonexistent_path_exits_2(capsys):
    exit_code = main(["/no/such/path/anywhere"])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "not a directory" in err


def test_main_no_manifest_found_exits_2(tmp_path, capsys):
    (tmp_path / "app.py").write_text("import requests\n")
    exit_code = main([str(tmp_path)])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "no requirements.txt or pyproject.toml" in err


def test_cli_end_to_end_as_subprocess():
    """Exercise the real console entry point via `python -m depdrift`,
    not just an in-process function call.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "depdrift", str(FIXTURE), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "black" in payload["unused_declared"]

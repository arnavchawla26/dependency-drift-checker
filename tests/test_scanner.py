from pathlib import Path

from depdrift.scanner import extract_imports, iter_python_files, scan_project

FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_extract_imports_plain_import():
    source = "import os\nimport requests\n"
    assert extract_imports(source) == [("os", 1), ("requests", 2)]


def test_extract_imports_dotted_import_uses_top_level():
    source = "import xml.etree.ElementTree\n"
    assert extract_imports(source) == [("xml", 1)]


def test_extract_imports_import_as():
    source = "import numpy as np\n"
    assert extract_imports(source) == [("numpy", 1)]


def test_extract_imports_from_import():
    source = "from collections import OrderedDict\n"
    assert extract_imports(source) == [("collections", 1)]


def test_extract_imports_from_dotted_module():
    source = "from os.path import join\n"
    assert extract_imports(source) == [("os", 1)]


def test_extract_imports_skips_relative_imports():
    source = "from . import helpers\nfrom ..pkg import thing\nfrom .sibling import x\n"
    assert extract_imports(source) == []


def test_extract_imports_multiple_names_one_statement():
    source = "import os, sys\n"
    assert extract_imports(source) == [("os", 1), ("sys", 1)]


def test_extract_imports_ignores_function_defs_and_strings():
    source = 'def f():\n    """import fake_module"""\n    return "import also_fake"\n'
    assert extract_imports(source) == []


def test_iter_python_files_excludes_default_dirs(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("import os\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hooks.py").write_text("import os\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "thing.py").write_text("import os\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.py").write_text("import os\n")

    found = {p.name for p in iter_python_files(tmp_path)}
    assert found == {"mod.py"}


def test_iter_python_files_excludes_egg_info_dirs(tmp_path):
    (tmp_path / "demo.egg-info").mkdir()
    (tmp_path / "demo.egg-info" / "gen.py").write_text("import os\n")
    (tmp_path / "real.py").write_text("import os\n")

    found = {p.name for p in iter_python_files(tmp_path)}
    assert found == {"real.py"}


def test_scan_project_records_parse_errors_without_raising(tmp_path):
    (tmp_path / "broken.py").write_text("def f(:\n    pass\n")
    (tmp_path / "fine.py").write_text("import os\n")

    result = scan_project(tmp_path)

    assert result.files_scanned == 2
    assert len(result.parse_errors) == 1
    assert result.parse_errors[0][0].name == "broken.py"
    assert result.module_names() == {"os"}


def test_scan_project_on_fixture_project():
    result = scan_project(FIXTURE)
    modules = result.module_names()
    assert {"os", "json", "requests", "yaml", "jinja2"} <= modules
    # relative imports (from . import helpers / from .helpers import greet)
    # must never show up as a top-level module named "helpers".
    assert "helpers" not in modules


def test_scan_project_tracks_import_locations():
    result = scan_project(FIXTURE)
    records = result.imports["requests"]
    assert len(records) == 1
    assert records[0].file.name == "app.py"
    assert records[0].lineno == 3

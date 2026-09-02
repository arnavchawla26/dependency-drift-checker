from pathlib import Path

from depdrift.analyze import analyze_project, local_module_names, stdlib_module_names

FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_stdlib_module_names_contains_common_modules():
    names = stdlib_module_names()
    assert {"os", "sys", "json", "re", "collections"} <= names


def test_local_module_names_flat_layout(tmp_path):
    (tmp_path / "mypkg").mkdir()
    (tmp_path / "mypkg" / "__init__.py").write_text("")
    (tmp_path / "standalone.py").write_text("")
    (tmp_path / "setup.py").write_text("")  # never counted as "local module"

    names = local_module_names(tmp_path)
    assert names == {"mypkg", "standalone"}


def test_local_module_names_src_layout(tmp_path):
    (tmp_path / "src" / "mypkg").mkdir(parents=True)
    (tmp_path / "src" / "mypkg" / "__init__.py").write_text("")

    names = local_module_names(tmp_path)
    assert "mypkg" in names


def test_local_module_names_ignores_plain_directories_without_init(tmp_path):
    (tmp_path / "not_a_package").mkdir()
    (tmp_path / "not_a_package" / "loose.py").write_text("")

    names = local_module_names(tmp_path)
    assert "not_a_package" not in names


def test_analyze_project_on_fixture_finds_expected_drift():
    result = analyze_project(FIXTURE)

    assert result.declared == {"requests", "pyyaml", "black", "python-dateutil"}
    assert set(result.unused_declared) == {"black", "python-dateutil"}
    assert set(result.undeclared_imports) == {"jinja2"}
    # requests/yaml are declared+used, so must not appear on either list.
    assert "requests" not in result.unused_declared
    assert "pyyaml" not in result.unused_declared
    assert "yaml" not in result.undeclared_imports


def test_analyze_project_respects_ignore_lists():
    result = analyze_project(
        FIXTURE,
        ignore_declared={"black", "python-dateutil"},
        ignore_imports={"jinja2"},
    )
    assert result.unused_declared == []
    assert result.undeclared_imports == []


def test_analyze_project_clean_project_has_no_drift(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")
    (tmp_path / "app.py").write_text("import requests\n\nrequests.get\n")

    result = analyze_project(tmp_path)

    assert result.unused_declared == []
    assert result.undeclared_imports == []


def test_analyze_project_no_manifests_found(tmp_path):
    (tmp_path / "app.py").write_text("import requests\n")

    result = analyze_project(tmp_path)

    assert result.manifest_files == []
    assert result.declared == set()
    # everything imported is "undeclared" since there's nothing declared
    assert "requests" in result.undeclared_imports

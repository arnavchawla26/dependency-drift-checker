from pathlib import Path

from depdrift.manifest import (
    find_and_parse_manifests,
    normalize_name,
    parse_pyproject_toml,
    parse_requirements_txt,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_normalize_name_collapses_separators_and_lowercases():
    assert normalize_name("PyYAML") == "pyyaml"
    assert normalize_name("python_dateutil") == "python-dateutil"
    assert normalize_name("Foo..Bar__Baz") == "foo-bar-baz"
    assert normalize_name("-leading-") == "leading"


def test_parse_requirements_txt_basic_names():
    text = """
    requests>=2.31
    PyYAML>=6.0
    """
    assert parse_requirements_txt(text) == {"requests", "pyyaml"}


def test_parse_requirements_txt_skips_comments_and_blank_lines():
    text = """
    # this is a full-line comment

    requests==2.31.0  # inline comment
    """
    assert parse_requirements_txt(text) == {"requests"}


def test_parse_requirements_txt_skips_option_lines():
    text = """
    -r other-requirements.txt
    --index-url https://pypi.org/simple
    -e ./local-package
    --hash=sha256:deadbeef
    requests==2.31.0
    """
    assert parse_requirements_txt(text) == {"requests"}


def test_parse_requirements_txt_handles_extras_and_markers():
    text = 'requests[security]>=2.31; python_version >= "3.8"\n'
    assert parse_requirements_txt(text) == {"requests"}


def test_parse_requirements_txt_skips_bare_url_requirements():
    text = "https://example.com/some_pkg.tar.gz\n"
    assert parse_requirements_txt(text) == set()


def test_parse_requirements_txt_handles_line_continuation():
    text = "requests \\\n    >=2.31\n"
    assert parse_requirements_txt(text) == {"requests"}


def test_parse_requirements_txt_from_fixture():
    text = (FIXTURE / "requirements.txt").read_text()
    names = parse_requirements_txt(text)
    assert names == {"requests", "pyyaml", "black", "python-dateutil"}


def test_parse_pyproject_toml_pep621_dependencies():
    text = """
    [project]
    name = "demo"
    dependencies = [
        "requests>=2.31",
        "click[extras]>=8.0",
    ]

    [project.optional-dependencies]
    dev = ["pytest>=7.0"]
    """
    assert parse_pyproject_toml(text) == {"requests", "click", "pytest"}


def test_parse_pyproject_toml_dependency_groups():
    text = """
    [dependency-groups]
    dev = ["pytest>=7.0", "mypy>=1.0"]
    """
    assert parse_pyproject_toml(text) == {"pytest", "mypy"}


def test_parse_pyproject_toml_poetry_style():
    text = """
    [tool.poetry.dependencies]
    python = "^3.11"
    requests = "^2.31"
    PyYAML = "^6.0"

    [tool.poetry.group.dev.dependencies]
    pytest = "^7.0"
    """
    names = parse_pyproject_toml(text)
    assert names == {"requests", "pyyaml", "pytest"}
    assert "python" not in names


def test_find_and_parse_manifests_combines_requirements_and_pyproject(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["click>=8.0"]\n'
    )
    result = find_and_parse_manifests(tmp_path)
    assert result.declared == {"requests", "click"}
    assert len(result.files_found) == 2


def test_find_and_parse_manifests_multiple_requirements_files(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest>=7.0\n")
    result = find_and_parse_manifests(tmp_path)
    assert result.declared == {"requests", "pytest"}


def test_find_and_parse_manifests_empty_when_nothing_present(tmp_path):
    result = find_and_parse_manifests(tmp_path)
    assert result.declared == set()
    assert result.files_found == []

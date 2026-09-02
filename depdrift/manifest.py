"""Parse dependency manifests (requirements.txt, pyproject.toml) into a
normalized set of declared package names.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# A PEP 508 requirement string starts with a "distribution name": letters,
# digits, and ., -, _ (must start/end with a letter or digit). We only need
# to capture that leading name; version specifiers, extras, and environment
# markers are discarded.
_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")

# Requirement-file option lines that never name a package and should be
# skipped outright (with or without a following value on the same line).
_OPTION_PREFIXES = (
    "-r",
    "--requirement",
    "-c",
    "--constraint",
    "-e",
    "--editable",
    "-f",
    "--find-links",
    "-i",
    "--index-url",
    "--extra-index-url",
    "--no-index",
    "--hash",
    "--trusted-host",
    "--pre",
    "--no-binary",
    "--only-binary",
)


def normalize_name(name: str) -> str:
    """Normalize a distribution name per PEP 503: lowercase, runs of
    ``-``/``_``/``.`` collapsed to a single ``-``.
    """
    return re.sub(r"[-_.]+", "-", name).lower().strip("-")


def _extract_requirement_name(line: str) -> str | None:
    """Pull the distribution name out of one PEP 508 requirement line, or
    return None if the line doesn't declare one (blank, comment, option,
    a local path, or a VCS/URL requirement with no explicit ``#egg=``
    name).
    """
    line = line.split(" #", 1)[0].strip()
    # A bare "#" at the start of the (already left-stripped) line, or after
    # splitting on " #", still needs handling for "#comment" with no
    # preceding space.
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(_OPTION_PREFIXES):
        return None
    if line.startswith(("http://", "https://", "git+", "./", "../", "/")):
        # VCS/URL/local-path requirement. Only recognizable if it declares
        # an explicit egg name via "#egg=name" (already stripped above) or
        # a "name @ url" form, which is handled by the generic match below
        # since it still starts with a valid name character in that case.
        return None
    match = _NAME_RE.match(line)
    if not match:
        return None
    return match.group(1)


def parse_requirements_txt(text: str) -> set[str]:
    """Return the set of normalized package names declared in a
    requirements.txt-style file. Line continuations, comments, blank
    lines, and pip options are ignored.
    """
    names: set[str] = set()
    # Join backslash line-continuations before splitting into logical lines.
    joined = text.replace("\\\n", " ")
    for raw_line in joined.splitlines():
        name = _extract_requirement_name(raw_line)
        if name:
            names.add(normalize_name(name))
    return names


def _names_from_pep508_list(items) -> set[str]:
    names: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        name = _extract_requirement_name(item)
        if name:
            names.add(normalize_name(name))
    return names


def _names_from_poetry_table(table: dict) -> set[str]:
    names: set[str] = set()
    for key in table:
        if key == "python":
            continue
        names.add(normalize_name(key))
    return names


def parse_pyproject_toml(text: str) -> set[str]:
    """Return the set of normalized package names declared in a
    pyproject.toml. Understands PEP 621 ``[project.dependencies]`` /
    ``[project.optional-dependencies]`` / ``[dependency-groups]`` and
    Poetry-style ``[tool.poetry.dependencies]`` /
    ``[tool.poetry.group.*.dependencies]``.
    """
    data = tomllib.loads(text)
    names: set[str] = set()

    project = data.get("project", {})
    if isinstance(project, dict):
        deps = project.get("dependencies")
        if isinstance(deps, list):
            names |= _names_from_pep508_list(deps)
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group_deps in optional.values():
                if isinstance(group_deps, list):
                    names |= _names_from_pep508_list(group_deps)

    dep_groups = data.get("dependency-groups")
    if isinstance(dep_groups, dict):
        for group_deps in dep_groups.values():
            if isinstance(group_deps, list):
                # Entries may be plain requirement strings or
                # {"include-group": "..."} references; only strings name a
                # package directly.
                names |= _names_from_pep508_list(
                    [d for d in group_deps if isinstance(d, str)]
                )

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        deps = poetry.get("dependencies")
        if isinstance(deps, dict):
            names |= _names_from_poetry_table(deps)
        groups = poetry.get("group")
        if isinstance(groups, dict):
            for group in groups.values():
                if isinstance(group, dict):
                    group_deps = group.get("dependencies")
                    if isinstance(group_deps, dict):
                        names |= _names_from_poetry_table(group_deps)

    return names


# Filenames (relative to the project root) checked for requirements.txt
# style syntax. "requirements*.txt" catches requirements-dev.txt etc.
_REQUIREMENTS_GLOB_PATTERNS = ("requirements*.txt", "requirements/*.txt")


@dataclass
class ManifestResult:
    """Aggregated manifest-parsing result for a project directory."""

    declared: set[str] = field(default_factory=set)
    files_found: list[Path] = field(default_factory=list)


def find_and_parse_manifests(root: Path) -> ManifestResult:
    """Locate and parse every supported manifest file directly under
    ``root`` (non-recursive — manifests nested in subdirectories, e.g. a
    vendored dependency's own requirements.txt, are intentionally not
    treated as this project's own declarations).
    """
    result = ManifestResult()
    seen: set[Path] = set()

    for pattern in _REQUIREMENTS_GLOB_PATTERNS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            result.declared |= parse_requirements_txt(path.read_text(encoding="utf-8"))
            result.files_found.append(path)

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        result.declared |= parse_pyproject_toml(pyproject.read_text(encoding="utf-8"))
        result.files_found.append(pyproject)

    return result

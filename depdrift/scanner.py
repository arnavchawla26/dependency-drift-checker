"""Walk a project's Python source and collect the top-level module names
it imports.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# Directories that never contain first-party project code worth scanning
# (or scanning them would blow up import results with vendored/third-party
# code that isn't the project's own).
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".eggs",
}


@dataclass
class ImportRecord:
    module: str
    file: Path
    lineno: int


@dataclass
class ScanResult:
    imports: dict[str, list[ImportRecord]] = field(default_factory=dict)
    parse_errors: list[tuple[Path, str]] = field(default_factory=list)
    files_scanned: int = 0

    def module_names(self) -> set[str]:
        return set(self.imports.keys())

    def add(self, module: str, file: Path, lineno: int) -> None:
        self.imports.setdefault(module, []).append(ImportRecord(module, file, lineno))


def iter_python_files(root: Path, exclude_dirs: set[str] | None = None):
    """Yield every ``.py`` file under ``root``, pruning excluded
    directories (and any directory ending in ``.egg-info``) as it walks.
    """
    excluded = DEFAULT_EXCLUDED_DIRS if exclude_dirs is None else exclude_dirs
    for dirpath, dirnames, filenames in _walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in excluded and not d.endswith(".egg-info")
        ]
        for filename in filenames:
            if filename.endswith(".py"):
                yield dirpath / filename


def _walk(root: Path):
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        yield Path(dirpath), dirnames, filenames


def extract_imports(source: str) -> list[tuple[str, int]]:
    """Parse Python source and return ``(top_level_module, lineno)`` pairs
    for every absolute import. Relative imports (``from . import x``,
    ``from ..pkg import y``) are skipped — they always refer to first-party
    code, never a dependency.
    """
    tree = ast.parse(source)
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                found.append((top, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import -> first-party
            if node.module:
                top = node.module.split(".")[0]
                found.append((top, node.lineno))
    return found


def scan_project(root: Path, exclude_dirs: set[str] | None = None) -> ScanResult:
    """Scan every Python file under ``root`` and collect the top-level
    modules it imports. Files that fail to parse (e.g. Python 2 syntax,
    or a genuinely broken file) are recorded in ``parse_errors`` rather
    than raising, so one bad file doesn't abort the whole scan.
    """
    result = ScanResult()
    for path in iter_python_files(root, exclude_dirs):
        result.files_scanned += 1
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            result.parse_errors.append((path, str(exc)))
            continue
        try:
            for module, lineno in extract_imports(source):
                result.add(module, path, lineno)
        except SyntaxError as exc:
            result.parse_errors.append((path, str(exc)))
    return result

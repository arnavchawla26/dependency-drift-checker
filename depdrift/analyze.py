"""Core drift analysis: cross-reference declared dependencies against
actual imports to flag declared-but-unused and imported-but-undeclared
packages.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from depdrift.manifest import ManifestResult, find_and_parse_manifests
from depdrift.mapping import import_names_for
from depdrift.scanner import ScanResult, scan_project

# Modules that are always available and never worth flagging as an
# undeclared dependency, beyond the interpreter's own stdlib list.
_ALWAYS_IGNORED = {"__future__", "builtins", "this"}


def stdlib_module_names() -> set[str]:
    """The set of standard-library top-level module names for the
    running interpreter, lowercased.
    """
    names = set(getattr(sys, "stdlib_module_names", ()))
    if not names:  # pragma: no cover - only hit on Python < 3.10
        import sysconfig

        names = set(sysconfig.get_config_var("py_version") and [] or [])
    return {n.lower() for n in names} | _ALWAYS_IGNORED


def local_module_names(root: Path) -> set[str]:
    """Best-effort detection of the project's own first-party top-level
    module/package names, so they aren't flagged as undeclared
    dependencies. Covers both a flat layout (packages/modules directly
    under root) and a ``src/`` layout.
    """
    names: set[str] = set()

    def collect_from(directory: Path) -> None:
        if not directory.is_dir():
            return
        for entry in directory.iterdir():
            if entry.is_dir() and (entry / "__init__.py").is_file():
                names.add(entry.name.lower())
            elif entry.is_file() and entry.suffix == ".py" and entry.stem != "setup":
                names.add(entry.stem.lower())

    collect_from(root)
    collect_from(root / "src")
    return names


@dataclass
class DriftResult:
    declared: set[str] = field(default_factory=set)
    used_imports: set[str] = field(default_factory=set)
    local_modules: set[str] = field(default_factory=set)
    manifest_files: list[Path] = field(default_factory=list)
    unused_declared: list[str] = field(default_factory=list)
    undeclared_imports: list[str] = field(default_factory=list)
    scan: ScanResult | None = None
    manifests: ManifestResult | None = None


def analyze_project(
    root: Path,
    exclude_dirs: set[str] | None = None,
    ignore_declared: set[str] | None = None,
    ignore_imports: set[str] | None = None,
) -> DriftResult:
    """Run the full drift analysis for a project rooted at ``root``.

    ``ignore_declared`` / ``ignore_imports`` take normalized names to
    exempt from each side of the comparison (e.g. a build-only tool that's
    declared but legitimately never imported).
    """
    root = Path(root)
    manifests = find_and_parse_manifests(root)
    scan = scan_project(root, exclude_dirs)

    stdlib = stdlib_module_names()
    local = local_module_names(root)
    used = {m.lower() for m in scan.module_names()}

    ignore_declared = {n.lower() for n in (ignore_declared or ())}
    ignore_imports = {n.lower() for n in (ignore_imports or ())}

    # declared-but-unused: none of a declared package's plausible import
    # names ever showed up in the scanned imports.
    unused_declared = []
    for dep in sorted(manifests.declared):
        if dep in ignore_declared:
            continue
        candidates = import_names_for(dep)
        if not candidates:
            continue  # e.g. a stub-only "types-*" package: nothing to check
        if not (candidates & used):
            unused_declared.append(dep)

    # Build the reverse index: every import name any declared package
    # could plausibly correspond to.
    declared_import_names: set[str] = set()
    for dep in manifests.declared:
        declared_import_names |= import_names_for(dep)

    undeclared_imports = []
    for module in sorted(used):
        if module in ignore_imports:
            continue
        if module in stdlib or module in local:
            continue
        if module in declared_import_names:
            continue
        undeclared_imports.append(module)

    return DriftResult(
        declared=manifests.declared,
        used_imports=used,
        local_modules=local,
        manifest_files=manifests.files_found,
        unused_declared=unused_declared,
        undeclared_imports=undeclared_imports,
        scan=scan,
        manifests=manifests,
    )

"""Render a DriftResult as text, markdown, or JSON."""
from __future__ import annotations

import json
from typing import Literal

from depdrift.analyze import DriftResult

Format = Literal["text", "markdown", "json"]


def to_dict(result: DriftResult) -> dict:
    return {
        "manifest_files": [str(p) for p in result.manifest_files],
        "declared_count": len(result.declared),
        "imports_scanned": len(result.used_imports),
        "unused_declared": result.unused_declared,
        "undeclared_imports": result.undeclared_imports,
    }


def render_json(result: DriftResult) -> str:
    return json.dumps(to_dict(result), indent=2, sort_keys=False)


def render_text(result: DriftResult) -> str:
    lines: list[str] = []
    files = ", ".join(str(p) for p in result.manifest_files) or "(none found)"
    lines.append(f"Manifests: {files}")
    lines.append(
        f"Declared dependencies: {len(result.declared)}    "
        f"Imported modules: {len(result.used_imports)}"
    )
    lines.append("")

    if result.unused_declared:
        lines.append(f"Declared but unused ({len(result.unused_declared)}):")
        for name in result.unused_declared:
            lines.append(f"  - {name}")
    else:
        lines.append("Declared but unused: none")
    lines.append("")

    if result.undeclared_imports:
        lines.append(f"Imported but undeclared ({len(result.undeclared_imports)}):")
        for name in result.undeclared_imports:
            lines.append(f"  - {name}")
    else:
        lines.append("Imported but undeclared: none")

    return "\n".join(lines)


def render_markdown(result: DriftResult) -> str:
    lines: list[str] = ["# Dependency drift report", ""]
    files = ", ".join(f"`{p}`" for p in result.manifest_files) or "_none found_"
    lines.append(f"**Manifests:** {files}  ")
    lines.append(
        f"**Declared:** {len(result.declared)}  **Imported modules:** "
        f"{len(result.used_imports)}"
    )
    lines.append("")

    lines.append(f"## Declared but unused ({len(result.unused_declared)})")
    lines.append("")
    if result.unused_declared:
        for name in result.unused_declared:
            lines.append(f"- `{name}`")
    else:
        lines.append("_None._")
    lines.append("")

    lines.append(f"## Imported but undeclared ({len(result.undeclared_imports)})")
    lines.append("")
    if result.undeclared_imports:
        for name in result.undeclared_imports:
            lines.append(f"- `{name}`")
    else:
        lines.append("_None._")

    return "\n".join(lines)


_RENDERERS = {
    "text": render_text,
    "markdown": render_markdown,
    "json": render_json,
}


def render(result: DriftResult, fmt: Format = "text") -> str:
    try:
        renderer = _RENDERERS[fmt]
    except KeyError as exc:
        raise ValueError(f"unknown format: {fmt!r}") from exc
    return renderer(result)

"""``depdrift`` command-line entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from depdrift.analyze import analyze_project
from depdrift.report import render


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="depdrift",
        description=(
            "Find phantom dependencies: packages declared but never imported, "
            "and modules imported but never declared."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project root to scan (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--ignore-declared",
        action="append",
        default=[],
        metavar="NAME",
        help="Declared package name to exempt from the unused check "
        "(repeatable).",
    )
    parser.add_argument(
        "--ignore-import",
        action="append",
        default=[],
        metavar="NAME",
        help="Imported module name to exempt from the undeclared check "
        "(repeatable).",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit with status 1 if any drift is found (useful in CI).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"depdrift: {root} is not a directory", file=sys.stderr)
        return 2

    result = analyze_project(
        root,
        ignore_declared=set(args.ignore_declared),
        ignore_imports=set(args.ignore_import),
    )

    if not result.manifest_files:
        print(
            f"depdrift: no requirements.txt or pyproject.toml found under {root}",
            file=sys.stderr,
        )
        return 2

    print(render(result, args.format))

    if args.fail_on_drift and (result.unused_declared or result.undeclared_imports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

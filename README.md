# depdrift

A dependency-drift checker for Python projects: it flags packages that are
**declared but never imported** and modules that are **imported but never
declared** — the "phantom dependency" problem. Pure static analysis, no
network calls, no installed environment required.

## Why

Requirements files rot. A package gets added for a spike and never removed;
another gets imported because it happened to be present transitively, then
breaks the day it's no longer pulled in as someone else's sub-dependency.
`depdrift` catches both directions by comparing your manifest against what
your code actually imports, using Python's own `ast` module rather than
executing anything.

## Install

```bash
git clone https://github.com/arnavchawla26/dependency-drift-checker.git
cd dependency-drift-checker
pip install -e ".[dev]"
```

Requires Python 3.11+ (uses the stdlib `tomllib` parser for
`pyproject.toml`).

## Usage

```bash
depdrift .                       # scan the current directory, text output
depdrift path/to/project         # scan a specific project
depdrift . --format json         # machine-readable output
depdrift . --format markdown     # for a PR comment / report
depdrift . --fail-on-drift       # exit 1 if anything is found (CI-friendly)

# exempt known false positives
depdrift . --ignore-declared black --ignore-import yaml
```

Example output:

```
Manifests: requirements.txt
Declared dependencies: 6    Imported modules: 5

Declared but unused (1):
  - black

Imported but undeclared (1):
  - yaml
```

(`yaml` is what `PyYAML` imports as — `depdrift` already knows about that
one; this example just shows what a *genuine* miss looks like.)

## What it understands

- **Manifests:** `requirements*.txt` (and `requirements/*.txt`), and
  `pyproject.toml` — both PEP 621 (`[project.dependencies]`,
  `[project.optional-dependencies]`, `[dependency-groups]`) and Poetry-style
  (`[tool.poetry.dependencies]`, `[tool.poetry.group.*.dependencies]`).
- **Imports:** every `.py` file under the project root (skipping
  `.git`, virtualenvs, `__pycache__`, `node_modules`, build output, and
  friends), parsed with `ast` — so this works even on code that can't be
  imported in the current environment. Relative imports (`from . import x`)
  are always treated as first-party.
- **Distribution-name vs. import-name mismatches:** a curated table covers
  the common ones (`PyYAML` → `yaml`, `beautifulsoup4` → `bs4`,
  `python-dateutil` → `dateutil`, `scikit-learn` → `sklearn`,
  `Pillow` → `PIL`, `opencv-python` → `cv2`, and ~40 more). Anything not in
  the table falls back to the naive guess (lowercase, `-` → `_`), which is
  correct for the large majority of packages.
- **First-party code:** any top-level package (a directory with
  `__init__.py`) or module (a `.py` file) directly under the project root,
  or under `src/`, is treated as local and never flagged as undeclared.
- **Standard library:** uses `sys.stdlib_module_names` for the running
  interpreter, so stdlib imports are never flagged.

## Tech stack

Python 3.11+, standard library only (`ast`, `tomllib`, `argparse`,
`pathlib`) — zero runtime dependencies. Tests use `pytest`.

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

## Current status

v1, functional: requirements.txt + pyproject.toml manifest parsing, AST-based
import scanning, curated name-mapping table, local-module detection, and
text/markdown/json reporting, all covered by tests.

**Known limitations (honest, not hidden):**
- No Node/`package.json` support — Python only, by design for v1.
- The distribution-name → import-name table is curated, not exhaustive; an
  unlisted mismatch falls back to the naive guess and may produce a false
  positive on either side. `--ignore-declared` / `--ignore-import` exist for
  exactly that.
- Imports inside `try/except ImportError` fallback blocks, or built
  dynamically (`importlib.import_module(f"...")`), aren't specially
  distinguished — they're still detected as ordinary imports if they use a
  literal module name at the AST level, but a fully dynamic import name is
  invisible to static analysis by nature.
- No registry lookups (PyPI, npm) for staleness/version-drift — that's a
  plausible v2 extension, not attempted here.

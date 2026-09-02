"""depdrift: find phantom dependencies in a Python project.

Compares what a project *declares* as a dependency (requirements.txt,
pyproject.toml) against what it *actually imports* in its source code,
flagging two kinds of drift:

- declared-but-unused: listed in the manifest, never imported anywhere.
- imported-but-undeclared: imported in code, but not listed in any manifest.
"""

__version__ = "0.1.0"

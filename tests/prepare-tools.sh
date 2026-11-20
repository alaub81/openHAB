#!/usr/bin/env bash
# Prepare the same pinned lint dependencies for local checks and CI.
# This file is sourced by the check entry points.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
for dependency in git bash docker node; do
  command -v "$dependency" >/dev/null || { echo "Missing dependency: $dependency" >&2; exit 1; }
done
EXPECTED_NODE="v$(cat "$PROJECT_DIR/.node-version")"
if [[ "$(node --version)" != "$EXPECTED_NODE" ]]; then
  echo "Node $EXPECTED_NODE is required; see .node-version." >&2
  exit 1
fi
if [[ ! -x "$PROJECT_DIR/.lint-venv/bin/python" ]]; then
  command -v python3 >/dev/null || { echo "Missing dependency: Python 3.9+" >&2; exit 1; }
  python3 -m venv "$PROJECT_DIR/.lint-venv"
fi
LINT_PYTHON="$PROJECT_DIR/.lint-venv/bin/python"
if ! "$LINT_PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  echo "Recreate .lint-venv with Python 3.9 or newer." >&2
  exit 1
fi
if ! "$LINT_PYTHON" - "$PROJECT_DIR/tests/requirements-lint.txt" <<'PY'
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys

try:
    for requirement in Path(sys.argv[1]).read_text().splitlines():
        name, expected = requirement.split("==")
        if version(name) != expected:
            sys.exit(1)
except PackageNotFoundError:
    sys.exit(1)
PY
then
  "$LINT_PYTHON" -m pip install --disable-pip-version-check --requirement "$PROJECT_DIR/tests/requirements-lint.txt"
fi

#!/usr/bin/env bash
# Run read-only checks in an isolated Python environment without starting containers.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"

if [[ $# -ne 0 ]]; then
  echo "Usage: ./tests/linter-check.sh" >&2
  exit 2
fi

if [[ ! -x .lint-venv/bin/python ]]; then
  python3 -m venv .lint-venv
fi

LINT_PYTHON="$PROJECT_DIR/.lint-venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
if ! "$LINT_PYTHON" -c 'from importlib.metadata import version; assert version("PyYAML") == "6.0.3"' >/dev/null 2>&1; then
  "$LINT_PYTHON" -m pip install --no-cache-dir --requirement tests/requirements-lint.txt
fi

"$LINT_PYTHON" -m unittest discover -s tests -p 'test_*.py'
exec "$LINT_PYTHON" tests/lint.py

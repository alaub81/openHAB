#!/usr/bin/env bash
# Run offline behavior checks with synthetic data and no running services.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -ne 0 ]]; then
  echo "Usage: ./tests/test-check.sh" >&2
  exit 2
fi
for dependency in git bash jq openssl node docker; do
  command -v "$dependency" >/dev/null || { echo "Missing dependency: $dependency" >&2; exit 1; }
done
# shellcheck source=tests/prepare-tools.sh
source "$PROJECT_DIR/tests/prepare-tools.sh"
cd -- "$PROJECT_DIR"
"$LINT_PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$LINT_PYTHON" tests/compose.advanced.py
exec "$LINT_PYTHON" tests/javascript-check.py

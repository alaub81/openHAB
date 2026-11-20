#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
# Run read-only checks in an isolated Python environment without starting containers.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"

if [[ $# -ne 0 ]]; then
  echo "Usage: ./tests/linter-check.sh" >&2
  exit 2
fi

# shellcheck source=tests/prepare-tools.sh
source "$PROJECT_DIR/tests/prepare-tools.sh"
"$LINT_PYTHON" tests/install_lint_tools.py
export PATH="$PROJECT_DIR/.lint-tools/bin:$PATH"
"$LINT_PYTHON" -m unittest discover -s tests -p 'test_lint.py'
"$LINT_PYTHON" -m unittest discover -s tests -p 'test_check_pipeline.py'
"$LINT_PYTHON" tests/lint.py
exec "$LINT_PYTHON" tests/source-check.py

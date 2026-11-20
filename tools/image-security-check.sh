#!/usr/bin/env bash
# Scan upstream defaults without starting Docker or using local installation data.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if (( $# != 1 )); then
  echo "Usage: ./tools/image-security-check.sh REPORT_DIRECTORY" >&2
  exit 2
fi
REPORT_DIRECTORY=$(mkdir -p -- "$1" && cd -- "$1" && pwd)
cd -- "$PROJECT_DIR"
# shellcheck source=tests/prepare-tools.sh
source "$PROJECT_DIR/tests/prepare-tools.sh"
command -v jq >/dev/null || { echo "Missing dependency: jq" >&2; exit 1; }
"$LINT_PYTHON" tests/install_lint_tools.py trivy
export PATH="$PROJECT_DIR/.lint-tools/bin:$PATH"
export SCAN_PLATFORM="${SCAN_PLATFORM:-linux/amd64}"
export SCAN_CATEGORY="${SCAN_PLATFORM//\//-}"
specifications=()
while IFS= read -r specification; do
  specifications+=("$specification")
done < <("$LINT_PYTHON" tests/stack_images.py)
if (( ${#specifications[@]} != 8 )); then
  echo "Expected all eight public stack images; review scanner coverage." >&2
  exit 1
fi
exec bash tests/scan-images.sh "$REPORT_DIRECTORY" "${specifications[@]}"

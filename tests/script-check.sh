#!/usr/bin/env bash
# Run optional script safety tests locally, without live services or containers.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -ne 0 ]]; then
  echo "Usage: ./tests/script-check.sh" >&2
  exit 2
fi

for dependency in python3 bash jq; do
  command -v "$dependency" >/dev/null || {
    echo "Missing dependency: $dependency" >&2
    exit 1
  }
done

export PYTHONDONTWRITEBYTECODE=1
cd -- "$PROJECT_DIR/tests"
exec python3 -m unittest test_maintenance test_certificates test_shelly_migration

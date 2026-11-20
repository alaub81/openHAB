#!/usr/bin/env bash
# Scan committed changes, falling back to full history when the base is unknown.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"
export PATH="$PROJECT_DIR/.lint-venv/bin:$PROJECT_DIR/.lint-tools/bin:$PATH"
if [[ "$(git rev-parse --is-shallow-repository)" == true ]]; then
  echo "Secret scanning requires full Git history; fetch with depth 0." >&2
  exit 1
fi
if [[ -n ${HEAD_SHA:-} && ! ${HEAD_SHA} =~ ^[a-fA-F0-9]{40}$ ]]; then
  echo "HEAD_SHA must be a full commit SHA." >&2
  exit 2
fi
LOG_RANGE=""
if [[ ${1:-} == --full && $# == 1 ]]; then
  :
elif (( $# != 0 )); then
  echo "Usage: ./tools/secret-check.sh [--full]" >&2
  exit 2
elif [[ ${BASE_SHA:-} =~ ^[a-fA-F0-9]{40}$ && ! ${BASE_SHA} =~ ^0+$ ]] &&
  git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null &&
  git merge-base --is-ancestor "$BASE_SHA" "${HEAD_SHA:-HEAD}"; then
  LOG_RANGE="${BASE_SHA}..${HEAD_SHA:-HEAD}"
fi
python3 tests/install_lint_tools.py gitleaks
if [[ -n "$LOG_RANGE" ]]; then
  exec gitleaks git --redact --no-banner "--log-opts=$LOG_RANGE" .
fi
exec gitleaks git --redact --no-banner .

#!/usr/bin/env bash
# Scan each image once; derive both the SARIF report and gate from that JSON.
set -euo pipefail
if (( $# < 2 )); then
  echo "Usage: scan-images.sh REPORT_DIRECTORY NAME=IMAGE|archive:/path/image.tar [...]" >&2
  exit 2
fi
REPORT_DIR=$1
shift
mkdir -p -- "$REPORT_DIR"
status=0
for specification in "$@"; do
  name=${specification%%=*}
  image=${specification#*=}
  if [[ ! "$name" =~ ^[a-z0-9-]+$ || "$image" == "$specification" || -z "$image" ]]; then
    echo "Invalid image specification: $specification" >&2
    exit 2
  fi
  target=("$image")
  if [[ -n "${SCAN_PLATFORM:-}" ]]; then
    target=(--platform "$SCAN_PLATFORM" "$image")
  fi
  if [[ "$image" == archive:* ]]; then
    target=(--input "${image#archive:}")
  fi
  if ! trivy image --image-src remote --scanners vuln --ignorefile /dev/null --ignore-unfixed=false \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --exit-code 0 \
    --timeout 10m --format json --output "$REPORT_DIR/$name.json" "${target[@]}"; then
    status=1
    continue
  fi
  if ! jq -e '.SchemaVersion >= 2 and (.ArtifactName | type == "string")' "$REPORT_DIR/$name.json" >/dev/null; then
    echo "Invalid scan report: $name" >&2
    status=1
    continue
  fi
  if ! trivy convert --ignorefile /dev/null --format sarif --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --output "$REPORT_DIR/$name.sarif" "$REPORT_DIR/$name.json"; then
    status=1
  else
    # Code scanning needs a distinct analysis category for every image and arch.
    if jq --arg category "$name-${SCAN_CATEGORY:-default}/" \
      '.runs[].automationDetails.id = $category' "$REPORT_DIR/$name.sarif" > "$REPORT_DIR/$name.sarif.tmp"; then
      mv -- "$REPORT_DIR/$name.sarif.tmp" "$REPORT_DIR/$name.sarif"
    else
      status=1
    fi
  fi
  # Conversion has no --ignore-unfixed flag: filter only the gate input.
  if ! jq '.Results = ((.Results // []) | map(if .Vulnerabilities then .Vulnerabilities |= map(
    select((.FixedVersion // "") != "")) else . end))' \
    "$REPORT_DIR/$name.json" > "$REPORT_DIR/$name.gate.json"; then
    status=1
    continue
  fi
  if ! trivy convert --ignorefile /dev/null --scanners vuln --format table \
    --severity HIGH,CRITICAL --exit-code 1 "$REPORT_DIR/$name.gate.json"; then
    status=1
  fi
done
exit "$status"

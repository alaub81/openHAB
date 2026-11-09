#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
# Configuration: adapt these anonymized examples in your local copy.
# Never commit real passwords or API tokens; CHANGE_ME placeholders are rejected.
# InfluxDB 2 InfluxQL compatibility API; use the database name from its DBRP mapping.
INFLUX_URL="http://localhost:8086"
INFLUX_DATABASE="openhab_db"
INFLUX_TOKEN="CHANGE_ME_INFLUXDB_API_TOKEN"
# Optional; example: "/etc/openhab/influxdb-token". Empty uses the inline token.
INFLUX_TOKEN_FILE=""
# Anonymized BME680 examples from the original measurement list.
MEASUREMENTS=(
    "ExampleBME680_Gas"
    "ExampleBME680_Temperature"
    "ExampleBME680_Altitude"
    "ExampleBME680_Pressure"
)
# true previews writes; false applies them. CLI flags override this value.
DRY_RUN=true
# Example limit: 50 targets/actions, not 50 stored data points.
MAX_ACTIONS=50
# Example: set to 1 only for an intentionally unauthenticated API.
ALLOW_ANONYMOUS=0
# Optional; example: "/etc/openhab/certs/ca.crt". Empty uses system CA trust.
API_CA_FILE=""
# End configuration

set -euo pipefail
export LC_ALL=C

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require() { [[ -n ${!1:-} ]] || die "Set $1 in the configuration block at the top of this script."; }

valid_name() { [[ $1 =~ ^[A-Za-z_][A-Za-z0-9_.:-]*$ ]] || die 'Unsupported name; use letters, digits, underscores, dots, colons or hyphens.'; }

initialize() {
    case "$DRY_RUN" in
        true) EXECUTE=false ;;
        false) EXECUTE=true ;;
        *) die 'DRY_RUN must be true or false.' ;;
    esac
    ARGS=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --execute) EXECUTE=true ;;
            --dry-run) EXECUTE=false ;;
            -h|--help) printf '%s\n' "$USAGE"; exit 0 ;;
            --*) die "Unknown option: $1" ;;
            *) ARGS+=("$1") ;;
        esac
        shift
    done
    for dependency in curl jq; do command -v "$dependency" >/dev/null || die "Missing dependency: $dependency"; done
    [[ $MAX_ACTIONS =~ ^[1-9][0-9]*$ ]] || die 'MAX_ACTIONS must be a positive integer.'
    umask 077
    MAINTENANCE_TMP=$(mktemp -d)
    trap 'rm -rf -- "$MAINTENANCE_TMP"' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
}

api() {
    local base=$1 auth=$2 method=$3 path=$4 expected=$5 token header status
    shift 5
    [[ $base =~ ^https?:// ]] && [[ $base != *[\?\#\@\ ]* ]] || die 'Use an HTTP(S) base URL without credentials, query or fragment.'
    case "$auth" in
        influx)
            token=$INFLUX_TOKEN
            [[ -z $INFLUX_TOKEN_FILE ]] || token=$(cat -- "$INFLUX_TOKEN_FILE")
            header=Token ;;
        *) die 'Unknown API authentication type.' ;;
    esac
    [[ $token != *$'\n'* && $token != *$'\r'* && $token != CHANGE_ME* && $token != YOUR_* ]] || die 'Invalid credential or placeholder; use a local token file.'
    local options=(--disable --silent --show-error --fail --connect-timeout 5 --max-time 30 --proto '=http,https')
    if [[ -n $token ]]; then
        printf 'Authorization: %s %s\n' "$header" "$token" > "$MAINTENANCE_TMP/auth-header"
        options+=(--header "@$MAINTENANCE_TMP/auth-header")
    else
        [[ ${ALLOW_ANONYMOUS:-0} == 1 ]] || die 'Supply the API token/token file, or explicitly set ALLOW_ANONYMOUS=1.'
    fi
    [[ -z ${API_CA_FILE:-} ]] || options+=(--cacert "$API_CA_FILE")
    RESPONSE="$MAINTENANCE_TMP/response"
    # No redirects, automatic write retries, disabled TLS verification, or response-body logging.
    status=$(curl "${options[@]}" --request "$method" "$@" \
        --output "$RESPONSE" --write-out '%{http_code}' "${base%/}$path") || die 'HTTP/TLS request failed; stopping without further actions.'
    case ",$expected," in *",$status,"*) ;; *) die "Unexpected HTTP status $status; stopping without further actions." ;; esac
}

check_plan() {
    [[ $1 -le $MAX_ACTIONS ]] || die 'Plan exceeds MAX_ACTIONS; select a smaller scope or review the limit.'
    if $EXECUTE; then printf 'EXECUTE: %s action(s)\n' "$1"; else printf 'DRY-RUN: %s action(s); no changes sent\n' "$1"; fi
}

uri() { jq -rn --arg value "$1" '$value | @uri'; }

influx_query() {
    require INFLUX_URL; require INFLUX_DATABASE
    local empty_ok=false
    [[ $1 != 'DROP MEASUREMENT '* ]] || empty_ok=true
    api "$INFLUX_URL" influx GET /query 200 --get --header 'Cache-Control: no-store' \
        --data-urlencode "db=$INFLUX_DATABASE" --data-urlencode "q=$1"
    jq -e --argjson empty_ok "$empty_ok" '(. == {} and $empty_ok) or
       (type == "object" and (has("error") | not) and
        (.results | type == "array" and length == 1) and
        (.results[0] | type == "object" and (if has("statement_id") then .statement_id == 0 else true end) and
          (has("error") | not) and
          ((.series // []) | type == "array" and all(.[]; . as $series |
             (.columns | type == "array" and all(.[]; type == "string")) and
             (.columns | length == (unique | length)) and
             (.values | type == "array") and
             all(.values[]; type == "array" and length == ($series.columns | length))))))' \
        "$RESPONSE" >/dev/null || die 'Invalid or failed InfluxDB 2 InfluxQL response.'
}

drop_measurements() {
    local measurement names=()
    while IFS= read -r measurement; do
        [[ -n $measurement ]] || continue
        valid_name "$measurement"
        names+=("$measurement")
    done < "$1"
    check_plan "${#names[@]}"
    for measurement in ${names[@]+"${names[@]}"}; do printf 'DROP MEASUREMENT "%s"\n' "$measurement"; done
    if $EXECUTE; then
        for measurement in ${names[@]+"${names[@]}"}; do influx_query "DROP MEASUREMENT \"$measurement\""; done
    fi
}

USAGE='Usage: delete-influxdb2-measurement.sh [MEASUREMENT ...] [--execute]
Configure at the top: INFLUX_URL, INFLUX_DATABASE and API token.
DRY_RUN=true previews; --execute drops the selected measurements completely, including all history.'
initialize "$@"

if [[ ${#ARGS[@]} -eq 0 ]]; then ARGS=(${MEASUREMENTS[@]+"${MEASUREMENTS[@]}"}); fi
[[ ${#ARGS[@]} -gt 0 ]] || die 'Set MEASUREMENTS or specify measurement arguments; use --help.'
for measurement in "${ARGS[@]}"; do valid_name "$measurement"; done
printf '%s\n' "${ARGS[@]}" | sort -u > "$MAINTENANCE_TMP/names"
drop_measurements "$MAINTENANCE_TMP/names"

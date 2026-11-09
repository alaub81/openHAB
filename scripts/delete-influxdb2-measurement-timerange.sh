#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
# Configuration: adapt these anonymized examples in your local copy.
# Never commit real passwords or API tokens; CHANGE_ME placeholders are rejected.
# Native InfluxDB 2 HTTP API, matching the example Compose organization/bucket.
INFLUX_URL="http://localhost:8086"
INFLUX_ORG="myorg"
INFLUX_BUCKET="openhab_db"
INFLUX_TOKEN="CHANGE_ME_INFLUXDB_API_TOKEN"
# Optional; example: "/etc/openhab/influxdb-token". Empty uses the inline token.
INFLUX_TOKEN_FILE=""
# Example window from the original scripts, with inclusive API start/stop boundaries.
# Whole-second UTC: YYYY-MM-DDTHH:MM:SSZ. Adapt before deleting real data.
START="2025-06-02T16:10:00Z"
STOP="2025-06-07T09:15:00Z"
# Anonymized energy-meter example from the original script.
MEASUREMENTS=("ExampleEnergyMeter_ImportedPower")
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

check_range() {
    require START; require STOP
    local value canonical
    for value in "$START" "$STOP"; do
        [[ $value =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || die 'Use UTC timestamps with whole seconds: YYYY-MM-DDTHH:MM:SSZ.'
        if canonical=$(date -u -d "$value" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null); then :
        elif canonical=$(date -ju -f '%Y-%m-%dT%H:%M:%SZ' "$value" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null); then :
        else die 'Invalid calendar date.'; fi
        [[ $canonical == "$value" ]] || die 'Invalid calendar date.'
    done
    [[ $START < $STOP ]] || die 'START must be before STOP.'
}

delete_v2() {
    require INFLUX_URL; require INFLUX_ORG; require INFLUX_BUCKET
    check_range
    local measurement path index=0 names=()
    while IFS= read -r measurement; do
        [[ -n $measurement ]] || continue
        [[ $measurement == '*' ]] || valid_name "$measurement"
        names+=("$measurement")
    done < "$1"
    check_plan "${#names[@]}"
    path="/api/v2/delete?org=$(uri "$INFLUX_ORG")&bucket=$(uri "$INFLUX_BUCKET")"
    for measurement in ${names[@]+"${names[@]}"}; do
        index=$((index + 1))
        jq -n --arg start "$START" --arg stop "$STOP" --arg measurement "$measurement" \
            '{start:$start,stop:$stop} + (if $measurement == "*" then {} else
                {predicate:("_measurement=" + ($measurement | tojson))} end)' > "$MAINTENANCE_TMP/delete-$index.json"
        cat "$MAINTENANCE_TMP/delete-$index.json"
    done
    if $EXECUTE; then
        for ((index=1; index<=${#names[@]}; index++)); do
            api "$INFLUX_URL" influx POST "$path" 204 --header 'Content-Type: application/json' \
                --data-binary "@$MAINTENANCE_TMP/delete-$index.json"
        done
    fi
}

USAGE='Usage: delete-influxdb2-measurement-timerange.sh [MEASUREMENT ...] [--execute]
Configure at the top: INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, START and STOP.
DRY_RUN=true previews; --execute deletes selected measurement data within the explicit range.'
initialize "$@"

if [[ ${#ARGS[@]} -eq 0 ]]; then ARGS=(${MEASUREMENTS[@]+"${MEASUREMENTS[@]}"}); fi
[[ ${#ARGS[@]} -gt 0 ]] || die 'Set MEASUREMENTS or specify measurement arguments; use --help.'
for measurement in "${ARGS[@]}"; do valid_name "$measurement"; done
printf '%s\n' "${ARGS[@]}" | sort -u > "$MAINTENANCE_TMP/names"
delete_v2 "$MAINTENANCE_TMP/names"

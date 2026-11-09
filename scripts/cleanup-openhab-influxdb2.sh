#!/usr/bin/env bash
#########################################################################
#Name: cleanup-openhab-influxdb2.sh
#Subscription: This Script deletes unused item entrys in the influxdb2 
#              with InfluxDB Queries over http API
#
#by A. Laub
#andreas[-at-]laub-home.de
#
#License:
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License as published by the
#Free Software Foundation, either version 3 of the License, or (at your option)
#any later version.
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#or FITNESS FOR A PARTICULAR PURPOSE.
#########################################################################

# Configuration: adapt these anonymized examples in your local copy.
# Never commit real passwords or API tokens; CHANGE_ME placeholders are rejected.
# openHAB connection, as in the original local-server examples.
OPENHAB_URL="https://localhost:8443"
OPENHAB_TOKEN="CHANGE_ME_OPENHAB_API_TOKEN"
# Optional; example: "/etc/openhab/openhab-api-token". Empty uses the inline token.
OPENHAB_TOKEN_FILE=""
# InfluxDB 2 InfluxQL compatibility API; use the database name from its DBRP mapping.
INFLUX_URL="http://localhost:8086"
INFLUX_DATABASE="openhab_db"
INFLUX_TOKEN="CHANGE_ME_INFLUXDB_API_TOKEN"
# Optional; example: "/etc/openhab/influxdb-token". Empty uses the inline token.
INFLUX_TOKEN_FILE=""
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
        openhab) token=${OPENHAB_TOKEN:-}; [[ -z ${OPENHAB_TOKEN_FILE:-} ]] || token=$(cat -- "$OPENHAB_TOKEN_FILE"); header=Bearer ;;
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

item_list() {
    require OPENHAB_URL
    api "$OPENHAB_URL" openhab GET '/rest/items?recursive=false&fields=name' 200
    jq -e 'type == "array" and length > 0 and all(.[];
        .name | type == "string" and test("^[A-Za-z_][A-Za-z0-9_]*$")) and
        ([.[].name] | length == (unique | length))' "$RESPONSE" >/dev/null || die 'Empty or invalid Item list; cleanup refused.'
    jq -r '.[].name' "$RESPONSE" | sort -u > "$MAINTENANCE_TMP/items"
}

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

measurement_list() {
    influx_query 'SHOW MEASUREMENTS'
    jq -e 'all(.results[0].series[]?; .name == "measurements" and .columns == ["name"] and all(.values[]; .[0] | type == "string"))' \
        "$RESPONSE" >/dev/null || die 'Unexpected measurement-list schema.'
    jq -r '.results[0].series[]?.values[][0]' "$RESPONSE" | sort -u > "$MAINTENANCE_TMP/measurements"
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

USAGE='Usage: cleanup-openhab-influxdb2.sh [--execute]
Configure both APIs, INFLUX_DATABASE and credentials at the top.
Compares all measurement names with the current openHAB Item list.
DRY_RUN=true previews; --execute drops entire orphan measurements, including all history.'
initialize "$@"

[[ ${#ARGS[@]} -eq 0 ]] || die 'Unexpected arguments; use --help.'
item_list
cp "$MAINTENANCE_TMP/items" "$MAINTENANCE_TMP/items-before"
measurement_list
comm -13 "$MAINTENANCE_TMP/items" "$MAINTENANCE_TMP/measurements" > "$MAINTENANCE_TMP/orphans"
if $EXECUTE; then
    item_list
    cmp -s "$MAINTENANCE_TMP/items-before" "$MAINTENANCE_TMP/items" || die 'Item list changed; generate a new preview.'
fi
drop_measurements "$MAINTENANCE_TMP/orphans"

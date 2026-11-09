#!/usr/bin/env bash
#########################################################################
#Name: delete-wrong-influxdb2-measurements.sh
#Subscription: This Script deletes entries in measurements
#              in influxdb which are too high or too small.
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
# Native InfluxDB 2 HTTP API, matching the example Compose organization/bucket.
INFLUX_URL="http://localhost:8086"
INFLUX_ORG="myorg"
INFLUX_BUCKET="openhab_db"
INFLUX_TOKEN="CHANGE_ME_INFLUXDB_API_TOKEN"
# Optional; example: "/etc/openhab/influxdb-token". Empty uses the inline token.
INFLUX_TOKEN_FILE=""
# Anonymized DHT22 example; the original comparison was humidity below 2%.
MEASUREMENT="ExampleDHT22_Humidity"
VALUE_FIELD="value"
OPERATOR="<"
THRESHOLD="2"
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

# InfluxDB's complete supported timestamp domain; user time bounds are not used.
MIN_TIME='1677-09-21T00:12:43.145224194Z'
MAX_TIME='2262-04-11T23:47:16.854775807Z'

flux_query() {
    jq -n --arg query "$1" '{query:$query,type:"flux",dialect:{header:true,annotations:[]}}' > "$MAINTENANCE_TMP/query.json"
    api "$INFLUX_URL" influx POST "/api/v2/query?org=$(uri "$INFLUX_ORG")" 200 \
        --header 'Accept: application/csv' --header 'Content-Type: application/json' \
        --data-binary "@$MAINTENANCE_TMP/query.json"
}

point_interval() {
    local stamp=$1 second fraction canonical epoch
    [[ $stamp =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(\.([0-9]{1,9}))?Z$ ]] || die 'Invalid timestamp in Flux response.'
    second=${BASH_REMATCH[1]}Z; fraction=${BASH_REMATCH[3]:-0}
    fraction="${fraction}000000000"; fraction=${fraction:0:9}
    if epoch=$(date -u -d "$second" '+%s' 2>/dev/null); then
        canonical=$(date -u -d "@$epoch" '+%Y-%m-%dT%H:%M:%SZ')
    elif epoch=$(date -ju -f '%Y-%m-%dT%H:%M:%SZ' "$second" '+%s' 2>/dev/null); then
        canonical=$(date -u -r "$epoch" '+%Y-%m-%dT%H:%M:%SZ')
    else die 'Invalid calendar timestamp in Flux response.'; fi
    [[ $canonical == "$second" ]] || die 'Invalid calendar timestamp in Flux response.'
    POINT_START="${second%Z}.${fraction}Z"
    [[ ! $POINT_START < $MIN_TIME && $POINT_START < $MAX_TIME ]] || die 'Timestamp outside the InfluxDB storage domain.'
    # InfluxDB 2 delete bounds are inclusive: equal bounds select exactly this timestamp.
    POINT_STOP=$POINT_START
}

USAGE='Usage: delete-wrong-influxdb2-measurements.sh [MEASUREMENT] [--execute]
Configure org, bucket, token, measurement, field, comparison and threshold at the top.
Scans all history using Flux; deletes matching complete points at their exact timestamps.
Deletes all fields of each matching point. DRY_RUN=true previews writes.'
initialize "$@"
[[ ${#ARGS[@]} -le 1 ]] || die 'Specify at most one measurement.'
[[ ${#ARGS[@]} -eq 0 ]] || MEASUREMENT=${ARGS[0]}
require INFLUX_URL; require INFLUX_ORG; require INFLUX_BUCKET; require MEASUREMENT
valid_name "$MEASUREMENT"; valid_name "$VALUE_FIELD"
case "$OPERATOR" in '<'|'<='|'='|'>='|'>') ;; *) die 'Unsupported comparison operator.' ;; esac
[[ $THRESHOLD =~ ^-?(0|[1-9][0-9]*)([.][0-9]+)?$ ]] || die 'THRESHOLD must be a plain decimal.'
flux_operator=$OPERATOR
[[ $flux_operator != '=' ]] || flux_operator='=='
bucket=$(jq -rn --arg value "$INFLUX_BUCKET" '$value|tojson')
measurement=$(jq -rn --arg value "$MEASUREMENT" '$value|tojson')
field=$(jq -rn --arg value "$VALUE_FIELD" '$value|tojson')

# Discover every tag key so deletion predicates identify a complete series.
flux_query "import \"influxdata/influxdb/schema\"
schema.measurementTagKeys(bucket: $bucket, measurement: $measurement,
    start: time(v: \"$MIN_TIME\"), stop: time(v: \"$MAX_TIME\"))"
header_seen=false; tag_keys=()
while IFS= read -r line || [[ -n $line ]]; do
    line=${line%$'\r'}; [[ -n $line ]] || continue; line=${line#,}
    if [[ $line == 'result,table,_value' ]]; then header_seen=true; continue; fi
    $header_seen && [[ $line =~ ^[A-Za-z0-9_]*,[0-9]+,[A-Za-z_][A-Za-z0-9_]*$ ]] || die 'Unexpected tag-key CSV response.'
    tag=${line##*,}
    case "$tag" in _field|_measurement|_start|_stop) ;; *) valid_name "$tag"; tag_keys+=("$tag") ;; esac
done < "$RESPONSE"

flux_query "import \"types\"
from(bucket: $bucket)
    |> range(start: time(v: \"$MIN_TIME\"), stop: time(v: \"$MAX_TIME\"))
    |> filter(fn: (r) => r._measurement == $measurement and r._field == $field)
    |> filter(fn: (r) => types.isNumeric(v: r._value))
    |> filter(fn: (r) => float(v: r._value) $flux_operator float(v: $THRESHOLD))"
: > "$MAINTENANCE_TMP/points"
header_seen=false; columns=(); time_index=0; value_index=0; measurement_index=0; field_index=0
while IFS= read -r line || [[ -n $line ]]; do
    line=${line%$'\r'}; [[ -n $line ]] || continue; line=${line#,}
    IFS=, read -r -a cells <<< "$line"
    if [[ $line == *'_time'* && $line == *'_value'* ]]; then
        columns=("${cells[@]}")
        schema=$(printf '%s\n' "${columns[@]}" | sort | tr '\n' ' ')
        expected=$(printf '%s\n' _field _measurement _start _stop _time _value result table ${tag_keys[@]+"${tag_keys[@]}"} | sort -u | tr '\n' ' ')
        [[ $schema == "$expected" ]] || die 'Unexpected columns or incomplete tag coverage; deletion refused.'
        for ((index=0; index<${#columns[@]}; index++)); do
            case "${columns[index]}" in
                _time) time_index=$index ;; _value) value_index=$index ;;
                _measurement) measurement_index=$index ;; _field) field_index=$index ;;
            esac
        done
        header_seen=true; continue
    fi
    $header_seen && [[ ${#cells[@]} -eq ${#columns[@]} ]] || die 'Invalid point CSV response.'
    [[ ${cells[measurement_index]} == "$MEASUREMENT" && ${cells[field_index]} == "$VALUE_FIELD" ]] || die 'Unexpected measurement or field.'
    value=${cells[value_index]}
    [[ $value =~ ^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$ ]] || die 'Invalid numeric field value.'
    jq -en --arg value "$value" --arg threshold "$THRESHOLD" --arg op "$OPERATOR" '
        ($value|tonumber) as $v | ($threshold|tonumber) as $t |
        if $op == "<" then $v < $t elif $op == "<=" then $v <= $t elif $op == "=" then $v == $t
        elif $op == ">=" then $v >= $t else $v > $t end' >/dev/null || die 'Server returned a point outside the comparison.'
    predicate="_measurement=$measurement"
    for tag in ${tag_keys[@]+"${tag_keys[@]}"}; do
        for ((index=0; index<${#columns[@]}; index++)); do
            [[ ${columns[index]} == "$tag" ]] || continue
            tag_value=${cells[index]}
            [[ -n $tag_value && $tag_value != *\"* && $tag_value != *$'\r'* ]] || die 'Empty or quoted CSV tag value; deletion refused.'
            predicate+=" AND $(jq -rn --arg value "$tag" '$value|tojson')=$(jq -rn --arg value "$tag_value" '$value|tojson')"
        done
    done
    point_interval "${cells[time_index]}"
    printf '%s\t%s\t%s\n' "$POINT_START" "$POINT_STOP" "$predicate" >> "$MAINTENANCE_TMP/points"
done < "$RESPONSE"
sort -u "$MAINTENANCE_TMP/points" > "$MAINTENANCE_TMP/plan"
count=$(wc -l < "$MAINTENANCE_TMP/plan" | tr -d ' ')
check_plan "$count"
index=0
while IFS=$'\t' read -r start stop predicate; do
    index=$((index + 1))
    jq -n --arg start "$start" --arg stop "$stop" --arg predicate "$predicate" \
        '{start:$start,stop:$stop,predicate:$predicate}' > "$MAINTENANCE_TMP/delete-$index.json"
    cat "$MAINTENANCE_TMP/delete-$index.json"
done < "$MAINTENANCE_TMP/plan"
if $EXECUTE; then
    for ((index=1; index<=count; index++)); do
        api "$INFLUX_URL" influx POST "/api/v2/delete?org=$(uri "$INFLUX_ORG")&bucket=$(uri "$INFLUX_BUCKET")" 204 \
            --header 'Content-Type: application/json' --data-binary "@$MAINTENANCE_TMP/delete-$index.json"
    done
fi

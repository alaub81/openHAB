#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
# Configuration: adapt these anonymized examples in your local copy.
# Never commit a real API token. The placeholder is rejected before any request.
OPENHAB_URL="https://localhost:8443"
OPENHAB_TOKEN="CHANGE_ME_OPENHAB_API_TOKEN"
# Optional; example: "/etc/openhab/openhab-api-token". Empty uses OPENHAB_TOKEN.
OPENHAB_TOKEN_FILE=""
# Bridge and two representative devices, matching the original monitoring setup.
BRIDGE_UID="digitalstrom:dssBridge:examplebridge"
MONITORED_THINGS=(
    "digitalstrom:GR:examplebridge:000000000000000000000001"
    "digitalstrom:circuit:examplebridge:000000000000000000000002"
)
# Example groups for refreshing shutter and lighting sensor states.
REFRESH_ITEMS=("Rolladen_ALL" "Lichter_DSS_ALL")
# Optional; example: "/etc/openhab/certs/ca.crt". Empty uses system CA trust.
API_CA_FILE=""
# End configuration

set -euo pipefail
export LC_ALL=C

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require() { [[ -n ${!1:-} ]] || die "Set $1 in the configuration block at the top of this script."; }

valid_name() { [[ $1 =~ ^[A-Za-z_][A-Za-z0-9_.:-]*$ ]] || die 'Unsupported name; use letters, digits, underscores, dots, colons or hyphens.'; }

initialize() {
    ARGS=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help) printf '%s\n' "$USAGE"; exit 0 ;;
            --*) die "Unknown option: $1" ;;
            *) ARGS+=("$1") ;;
        esac
        shift
    done
    for dependency in curl jq; do command -v "$dependency" >/dev/null || die "Missing dependency: $dependency"; done
    umask 077
    MAINTENANCE_TMP=$(mktemp -d)
    trap 'rm -rf -- "$MAINTENANCE_TMP"' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
}

api() {
    local method=$1 path=$2 expected=$3 token status
    shift 3
    [[ $OPENHAB_URL =~ ^https?:// ]] && [[ $OPENHAB_URL != *[\?\#\@\ ]* ]] || die 'Use an HTTP(S) base URL without credentials, query or fragment.'
    token=$OPENHAB_TOKEN
    [[ -z $OPENHAB_TOKEN_FILE ]] || token=$(cat -- "$OPENHAB_TOKEN_FILE")
    [[ $token != *$'\n'* && $token != *$'\r'* && $token != CHANGE_ME* && $token != YOUR_* ]] || die 'Invalid credential or placeholder; use a local token file.'
    local options=(--disable --silent --show-error --fail --connect-timeout 5 --max-time 30 --proto '=http,https')
    [[ -n $token ]] || die 'Set OPENHAB_TOKEN or OPENHAB_TOKEN_FILE.'
    printf 'Authorization: Bearer %s\n' "$token" > "$MAINTENANCE_TMP/auth-header"
    options+=(--header "@$MAINTENANCE_TMP/auth-header")
    [[ -z ${API_CA_FILE:-} ]] || options+=(--cacert "$API_CA_FILE")
    RESPONSE="$MAINTENANCE_TMP/response"
    # No redirects, automatic write retries, disabled TLS verification, or response-body logging.
    status=$(curl "${options[@]}" --request "$method" "$@" \
        --output "$RESPONSE" --write-out '%{http_code}' "${OPENHAB_URL%/}$path") || die 'HTTP/TLS request failed; stopping without further actions.'
    case ",$expected," in *",$status,"*) ;; *) die "Unexpected HTTP status $status; stopping without further actions." ;; esac
}

uri() { jq -rn --arg value "$1" '$value | @uri'; }

binding_main() {
    [[ ${#ARGS[@]} -ge 1 ]] || die 'Specify an action; use --help.'
    local action=${ARGS[0]} target status detail unhealthy=false
    local targets=()
    case "$action" in status|fullstatus|restart|autorestart|refresh) ;; *) die 'Unknown binding action.' ;; esac
    if [[ $action == refresh ]]; then
        if [[ ${#ARGS[@]} -eq 1 ]]; then ARGS+=( ${REFRESH_ITEMS[@]+"${REFRESH_ITEMS[@]}"} ); fi
        [[ ${#ARGS[@]} -ge 2 ]] || die 'Set REFRESH_ITEMS or specify Item/group arguments.'
        for target in "${ARGS[@]:1}"; do
            [[ $target =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die 'Invalid Item name.'
        done
        require OPENHAB_URL
        for target in "${ARGS[@]:1}"; do
            printf 'REFRESH %s\n' "$target"
            api POST "/rest/items/$(uri "$target")" 200,201,202,204 \
                --header 'Content-Type: text/plain' --data-binary REFRESH
        done
        return
    fi
    require OPENHAB_URL; require BRIDGE_UID
    targets=("$BRIDGE_UID")
    if [[ ${#ARGS[@]} -gt 1 ]]; then targets+=("${ARGS[@]:1}")
    else targets+=(${MONITORED_THINGS[@]+"${MONITORED_THINGS[@]}"}); fi
    for target in "${targets[@]}"; do valid_name "$target"; done
    # Read every target before changing anything. Invalid/failed reads abort.
    for target in "${targets[@]}"; do
        api GET "/rest/things/$(uri "$target")/status" 200
        jq -e 'type == "object" and (.status | type == "string") and
            (.statusDetail | type == "string") and
            (.status | IN("ONLINE", "OFFLINE", "UNKNOWN", "UNINITIALIZED", "INITIALIZING", "REMOVING", "REMOVED"))' \
            "$RESPONSE" >/dev/null || die 'Invalid Thing status response.'
        status=$(jq -r .status "$RESPONSE"); detail=$(jq -r .statusDetail "$RESPONSE")
        printf '%s: %s (%s)\n' "$target" "$status" "$detail"
        [[ $action != fullstatus ]] || jq . "$RESPONSE"
        if [[ $action == restart || $action == autorestart ]]; then
            [[ $detail != DISABLED ]] || die 'A selected Thing is disabled; automatic restart refused.'
        fi
        if [[ $status != ONLINE || $detail != NONE ]]; then unhealthy=true; fi
    done
    case "$action" in
        status|fullstatus) return ;;
        autorestart) $unhealthy || return 0 ;;
    esac
    printf 'Restart bridge %s\n' "$BRIDGE_UID"
    REENABLE_UID=$BRIDGE_UID
    trap 'binding_cleanup $?' EXIT
    api PUT "/rest/things/$(uri "$BRIDGE_UID")/enable" 200,202,204 \
        --header 'Content-Type: text/plain' --data-binary false
    sleep 3
    api PUT "/rest/things/$(uri "$BRIDGE_UID")/enable" 200,202,204 \
        --header 'Content-Type: text/plain' --data-binary true
    REENABLE_UID=''
    printf 'Re-enable accepted; check Thing status after binding initialization.\n'
}

binding_cleanup() {
    local result=$1
    if [[ -n ${REENABLE_UID:-} ]]; then
        printf 'Interrupted restart: attempting to re-enable %s.\n' "$REENABLE_UID" >&2
        (trap - EXIT; api PUT "/rest/things/$(uri "$REENABLE_UID")/enable" 200,202,204 \
            --header 'Content-Type: text/plain' --data-binary true) ||
            printf 'Re-enable failed: manually enable %s in MainUI.\n' "$REENABLE_UID" >&2
    fi
    rm -rf -- "$MAINTENANCE_TMP"
    exit "$result"
}

USAGE='Usage: digitalstrom_binding_tools.sh ACTION [TARGET ...]
Actions: status, fullstatus, restart, autorestart, refresh.
Configure at the top: OPENHAB_URL, credentials; BRIDGE_UID for status/restart actions.
Extra TARGETs: Thing UIDs to monitor, or Item/group names for refresh.
restart, autorestart and refresh act immediately; no dry-run mode.'
initialize "$@"
binding_main

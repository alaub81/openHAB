#!/usr/bin/env python3
"""
Shelly Deprecated Channel Link Migrator for openHAB
===================================================

Purpose
-------
This script helps migrate openHAB Item-Channel links for Shelly Things when the
Shelly binding logs deprecated channel warnings such as:

    Channel meter#currentWatts is deprecated and will be removed in a future
    release; use meter#currentPower instead.

The script does not use a hard-coded migration list as its primary source.
Instead, it parses the openHAB log file and extracts the deprecated channel ID
and the suggested replacement channel ID from the log messages.

It then uses the openHAB REST API to:

1. Load all Things from /rest/things
2. Resolve the Shelly device ID from the log file to the real openHAB Thing UID
3. Resolve the old and new channel IDs to full openHAB Channel UIDs
4. Load all existing Item-Channel links from /rest/links
5. Find Items currently linked to deprecated Shelly channels
6. Check whether the Item type matches the expected type of the new channel
7. Create a new Item-Channel link to the replacement channel
8. Delete the old link only after successful creation

Safety Features
---------------
By default, DRY_RUN is enabled. In dry-run mode, the script only prints what it
would do and does not modify openHAB.

The script also includes additional safety checks for known Shelly migration
edge cases, for example:

- meterN#lastPower1 -> meterN#lastEnergy1
  This changes the dimension from power to energy, e.g. W -> Wh.
  The script skips this migration unless the Item is already Number:Energy.

- device#totalKWH -> device#totalEnergy
  This is skipped because the Shelly binding documentation marks it as requiring
  manual review / rediscovery due to possible naming collisions.

- meterN#reactiveWatts -> meterN#reactivePower
  This is allowed but logged with a note because the unit was corrected to VAR.

Usage
-----
Set OPENHAB_URL, OPENHAB_TOKEN_FILE and OPENHAB_LOG in the environment.
Run with no arguments for a dry run. Add --execute --backup-file PATH only
when ready to apply. The backup file must not already exist. See tools/README.md.
Requires Python 3 and requests. TLS verification stays enabled; REQUESTS_CA_BUNDLE
can select a local CA. This tool changes links only; it does not send Item commands.
"""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import re
import sys
import requests
from urllib.parse import quote


# ============================================================================
# Configuration
# ============================================================================

OPENHAB_URL = ""
LOGFILE = ""
BACKUP_FILE = None

# True  = do not change anything, only print planned actions
# False = actually delete old links and create new links
DRY_RUN = True

# If True, links are migrated even if the new channel type cannot be detected.
# Recommended initial value: False.
MIGRATE_IF_CHANNEL_TYPE_UNKNOWN = False

# If True, generic Number Items are allowed for channels such as Number:Power
# or Number:Energy. This usually works in openHAB but loses semantic UoM detail.
ALLOW_GENERIC_NUMBER_ITEM = True


# ============================================================================
# Regex for Shelly deprecated log messages
# ============================================================================

# Example:
# shellypstripg4-000000000001: Channel meter1#currentWatts is deprecated
# and will be removed in a future release; use meter1#currentPower instead.
DEPRECATED_RE = re.compile(
    r"-\s+(?P<shelly_id>[^:]+):\s+Channel\s+"
    r"(?P<old_channel>[^\s]+)\s+is deprecated .*? use\s+"
    r"(?P<new_channel>[^\s]+)\s+instead\."
)


# ============================================================================
# REST session
# ============================================================================

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json"
})


def enc(value: str) -> str:
    return quote(value, safe="")


def request(method, path, **kwargs):
    response = session.request(method, f"{OPENHAB_URL}{path}", timeout=(5, 30),
                               allow_redirects=False, **kwargs)
    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"{method} failed with HTTP {response.status_code}; stopping")
    return response


def get_json(path: str):
    return request("GET", path).json()


# ============================================================================
# Log file parsing
# ============================================================================

def parse_logfile(path: str):
    """
    Read Shelly deprecated warnings and build:

        (shelly_id, old_channel_id) -> new_channel_id
    """
    mappings = {}

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = DEPRECATED_RE.search(line)
            if not m:
                continue

            shelly_id = m.group("shelly_id").strip()
            old_channel = m.group("old_channel").strip()
            new_channel = m.group("new_channel").strip()

            mappings[(shelly_id, old_channel)] = new_channel

    return mappings


# ============================================================================
# Thing / Channel helper functions
# ============================================================================

def get_thing_uid(thing):
    return thing.get("UID") or thing.get("uid")


def get_thing_channels(thing):
    return thing.get("channels", []) or []


def get_channel_uid(channel):
    return channel.get("uid") or channel.get("UID")


def get_channel_id_from_uid(channel_uid: str):
    """
    Full channel UID example:

        shelly:shellyplusplug:exampledevice:meter#currentPower

    Result:

        meter#currentPower
    """
    return channel_uid.split(":")[-1]


def build_shelly_lookup(things):
    """
    Build a lookup table:

        shellypstripg4-000000000001 -> real openHAB Thing UID

    The lookup intentionally searches broadly in:

    - Thing UID
    - Thing label
    - Thing properties

    This is important because the Shelly ID from the log is not always identical
    to one segment of the openHAB Thing UID.
    """
    lookup = {}

    for thing in things:
        thing_uid = get_thing_uid(thing)
        if not thing_uid:
            continue

        if not thing_uid.startswith("shelly:"):
            continue

        label = str(thing.get("label", ""))
        properties = thing.get("properties", {}) or {}

        candidates = {thing_uid, label}
        candidates.update(str(v) for v in properties.values())

        for value in candidates:
            for token in re.findall(r"shelly[a-z0-9]+-[a-fA-F0-9]+", value):
                lookup[token.lower()] = thing_uid

    return lookup


def find_channel(things_by_uid, thing_uid, channel_id):
    """
    Find a channel inside a Thing by its channel ID, for example:

        meter#currentPower
        meter1#totalEnergy
        device#accumulatedPower
    """
    thing = things_by_uid.get(thing_uid)
    if not thing:
        return None

    for channel in get_thing_channels(thing):
        channel_uid = get_channel_uid(channel)
        if not channel_uid:
            continue

        if get_channel_id_from_uid(channel_uid) == channel_id:
            return channel

    return None


def get_channel_item_type(channel):
    """
    Try to read the expected Item type for a channel from the REST response.

    Depending on the openHAB version, REST output, or binding implementation, the
    field names may differ. Therefore, several variants are checked.
    """
    if not channel:
        return None

    for key in ("itemType", "acceptedItemType", "acceptedItemTypes"):
        value = channel.get(key)
        if value:
            if isinstance(value, list):
                return value[0] if value else None
            return value

    channel_type = channel.get("channelType") or {}
    for key in ("itemType", "acceptedItemType", "acceptedItemTypes"):
        value = channel_type.get(key)
        if value:
            if isinstance(value, list):
                return value[0] if value else None
            return value

    # Some REST responses contain "type" as a Channel Type UID, not as an Item
    # type. Therefore "type" is intentionally not used here as Item type.
    return None


# ============================================================================
# Item helper functions
# ============================================================================

_item_cache = {}


def get_item(item_name):
    if item_name in _item_cache:
        return _item_cache[item_name]

    data = get_json(f"/rest/items/{enc(item_name)}")
    _item_cache[item_name] = data
    return data


def get_item_type(item_name):
    item = get_item(item_name)
    if not item:
        return None
    return item.get("type")


# ============================================================================
# Type and risk checks
# ============================================================================

def is_number_type(item_type):
    return item_type == "Number" or str(item_type).startswith("Number:")


def is_compatible_item_type(item_type, channel_item_type):
    """
    Check whether the Item type and Channel type are compatible.

    Returns:

        (True,  reason) -> compatible
        (False, reason) -> incompatible, should not be migrated
        (None,  reason) -> unknown / cannot be checked safely
    """
    if not item_type or not channel_item_type:
        return None, "Item type or channel type is unknown"

    if item_type == channel_item_type:
        return True, "Item type matches exactly"

    # Generic Number Item linked to Number:Power / Number:Energy etc.
    # This often works in openHAB, but it loses semantic UoM information.
    if item_type == "Number" and str(channel_item_type).startswith("Number:"):
        if ALLOW_GENERIC_NUMBER_ITEM:
            return True, f"Item is generic Number, channel expects {channel_item_type}"
        return False, f"Item is generic Number, channel expects {channel_item_type}"

    # Number:Power Item linked to a generic Number channel.
    # Example: powerFactor changed from Number:Dimensionless to Number.
    # This can be problematic.
    if str(item_type).startswith("Number:") and channel_item_type == "Number":
        return False, f"Item is {item_type}, channel is generic Number"

    # Different UoM dimensions are critical:
    # Number:Power -> Number:Energy
    # Number:Dimensionless -> Number:Power
    if str(item_type).startswith("Number:") and str(channel_item_type).startswith("Number:"):
        return False, f"Dimension change: Item {item_type}, channel {channel_item_type}"

    # Switch/String/Contact/etc.
    if item_type != channel_item_type:
        return False, f"Type conflict: Item {item_type}, channel {channel_item_type}"

    return True, "Item type is compatible"


def classify_known_shelly_risk(old_channel_uid, new_channel_uid, item_type):
    """
    Known Shelly-specific edge cases from the binding change documentation.

    Returns:

        ("ok",   reason)
        ("note", reason)
        ("warn", reason)
        ("skip", reason)
    """
    old_id = get_channel_id_from_uid(old_channel_uid)
    new_id = get_channel_id_from_uid(new_channel_uid)

    # Critical: Power -> Energy
    # Documentation: meterN#lastPower1 -> meterN#lastEnergy1
    # Unit changed: W -> Wh
    if old_id.endswith("#lastPower1") and new_id.endswith("#lastEnergy1"):
        if item_type == "Number:Energy":
            return "ok", "lastPower1 -> lastEnergy1, Item is already Number:Energy"
        return "skip", "Power -> Energy: Item must be Number:Energy"

    # Critical according to documentation because of collision / rediscovery.
    if old_id == "device#totalKWH" and new_id == "device#totalEnergy":
        return "skip", "device#totalKWH -> device#totalEnergy requires manual review / rediscovery"

    # Reactive power: unit was corrected to VAR.
    # Usually still Number:Power, but a note is useful.
    if old_id.endswith("#reactiveWatts") and new_id.endswith("#reactivePower"):
        return "note", "Reactive power: unit was corrected to VAR"

    # Typo fix.
    if old_id.endswith("#nmTreshhold") and new_id.endswith("#nmThreshold"):
        return "ok", "Typo fix nmTreshhold -> nmThreshold"

    # Returned energy rename.
    if old_id.endswith("#accumulatedReturned") and new_id.endswith("#accumulatedReturnedEnergy"):
        if item_type in ("Number:Energy", "Number", None):
            return "note", "Returned energy rename, please verify Item type"
        return "warn", "Probably an energy channel, but Item type looks unusual"

    # Safe power rename.
    if old_id.endswith("#accumulatedWatts") and new_id.endswith("#accumulatedPower"):
        return "ok", "Device accumulated power rename: Power remains Power"

    # Safe power renames from the observed logs.
    if old_id.endswith("#currentWatts") and new_id.endswith("#currentPower"):
        return "ok", "currentWatts -> currentPower: Power remains Power"

    # Normal meter energy renames.
    if (
        old_id.startswith("meter")
        and old_id.endswith("#totalKWH")
        and new_id.startswith("meter")
        and new_id.endswith("#totalEnergy")
    ):
        return "ok", "meter totalKWH -> totalEnergy: Energy remains Energy"

    return "ok", "No known risk case"


# ============================================================================
# Link modification
# ============================================================================

def delete_link(item_name, channel_uid):
    path = f"/rest/links/{enc(item_name)}/{enc(channel_uid)}"

    if DRY_RUN:
        print(f"[DRY] DELETE {item_name} -> {channel_uid}")
        return

    request("DELETE", path)


def create_link(item_name, channel_uid, configuration=None):
    path = f"/rest/links/{enc(item_name)}/{enc(channel_uid)}"

    payload = {
        "itemName": item_name,
        "channelUID": channel_uid,
        "configuration": configuration or {}
    }

    if DRY_RUN:
        print(f"[DRY] PUT    {item_name} -> {channel_uid} config={configuration or {}}")
        return

    request("PUT", path, json=payload)


# ============================================================================
# Additional check: existing powerFactor links
# ============================================================================

def warn_powerfactor_links(links):
    """
    powerFactor is not primarily a relinking issue, but an Item / persistence
    compatibility issue:

        previously: Number:Dimensionless
        now:        Number
    """
    printed_header = False

    for link in links:
        channel_uid = link.get("channelUID", "")
        item_name = link.get("itemName")

        if not channel_uid.endswith("#powerFactor"):
            continue

        item_type = get_item_type(item_name)

        if item_type == "Number:Dimensionless":
            if not printed_header:
                print()
                print("PowerFactor check:")
                printed_header = True

            print(f"[WARN-POWERFACTOR] {item_name}")
            print(f"                   Channel: {channel_uid}")
            print(f"                 Item type: {item_type}")
            print("                     Reason: powerFactor is now Number, previously Number:Dimensionless")
            print("                             Please review Item and persistence manually")


# ============================================================================
# Main
# ============================================================================

def main():
    print("Shelly Channel Link Migration")
    print("============================")
    print(f"openHAB URL: {OPENHAB_URL}")
    print(f"Log file:    {LOGFILE}")
    print(f"Dry run:     {DRY_RUN}")
    print()

    deprecated = parse_logfile(LOGFILE)
    print(f"Deprecated mappings found in log: {len(deprecated)}")

    if not deprecated:
        print("No matching deprecated channel log lines found.")
        return

    things = get_json("/rest/things")
    links = get_json("/rest/links")

    if not isinstance(things, list) or not isinstance(links, list):
        raise RuntimeError("Invalid Things/links response; no changes sent")
    if any(not isinstance(link, dict) or not link.get("itemName") or
           not link.get("channelUID") for link in links):
        raise RuntimeError("Invalid link record; no changes sent")
    plan = []
    existing = {(link["itemName"], link["channelUID"]) for link in links}
    things_by_uid = {
        get_thing_uid(t): t
        for t in things
        if get_thing_uid(t)
    }

    shelly_lookup = build_shelly_lookup(things)

    full_mapping = {}

    unresolved_thing = 0
    unresolved_old_channel = 0
    unresolved_new_channel = 0

    for (shelly_id, old_channel_id), new_channel_id in deprecated.items():
        thing_uid = shelly_lookup.get(shelly_id.lower())

        if not thing_uid:
            print(f"[WARN] No Thing found for log ID: {shelly_id}")
            unresolved_thing += 1
            continue

        old_channel = find_channel(things_by_uid, thing_uid, old_channel_id)
        new_channel = find_channel(things_by_uid, thing_uid, new_channel_id)

        if not old_channel:
            print(f"[WARN] Old channel not found in Thing: {thing_uid} / {old_channel_id}")
            unresolved_old_channel += 1
            continue

        if not new_channel:
            print(f"[WARN] New channel not found in Thing: {thing_uid} / {new_channel_id}")
            unresolved_new_channel += 1
            continue

        old_channel_uid = get_channel_uid(old_channel)
        new_channel_uid = get_channel_uid(new_channel)

        full_mapping[old_channel_uid] = {
            "new_channel_uid": new_channel_uid,
            "old_channel": old_channel,
            "new_channel": new_channel,
            "shelly_id": shelly_id,
            "thing_uid": thing_uid,
        }

    print(f"Resolvable channel mappings: {len(full_mapping)}")
    print(f"Unresolved Things:           {unresolved_thing}")
    print(f"Old channels not found:      {unresolved_old_channel}")
    print(f"New channels not found:      {unresolved_new_channel}")
    print()

    migrated = 0
    skipped = 0
    warnings = 0
    notes = 0
    candidates = 0

    for link in links:
        item_name = link.get("itemName")
        old_channel_uid = link.get("channelUID")
        config = link.get("configuration") or {}

        if old_channel_uid not in full_mapping:
            continue

        candidates += 1

        mapping_entry = full_mapping[old_channel_uid]
        new_channel_uid = mapping_entry["new_channel_uid"]
        new_channel = mapping_entry["new_channel"]

        item_type = get_item_type(item_name)
        new_channel_type = get_channel_item_type(new_channel)

        # Check known Shelly-specific edge cases first.
        risk_status, risk_reason = classify_known_shelly_risk(
            old_channel_uid,
            new_channel_uid,
            item_type
        )

        if risk_status == "skip":
            print(f"[SKIP-RISK] {item_name}")
            print(f"            old: {old_channel_uid}")
            print(f"            new: {new_channel_uid}")
            print(f"      Item type: {item_type}")
            print(f"   Channel type: {new_channel_type}")
            print(f"         Reason: {risk_reason}")
            print()
            skipped += 1
            continue

        if risk_status == "warn":
            print(f"[WARN-RISK] {item_name}")
            print(f"            old: {old_channel_uid}")
            print(f"            new: {new_channel_uid}")
            print(f"      Item type: {item_type}")
            print(f"   Channel type: {new_channel_type}")
            print(f"         Reason: {risk_reason}")
            warnings += 1

        if risk_status == "note":
            print(f"[NOTE] {item_name}: {risk_reason}")
            notes += 1

        # General type check against the new channel.
        compatible, reason = is_compatible_item_type(item_type, new_channel_type)

        if compatible is False:
            print(f"[SKIP-TYPE-MISMATCH] {item_name}")
            print(f"                     old: {old_channel_uid}")
            print(f"                     new: {new_channel_uid}")
            print(f"               Item type: {item_type}")
            print(f"        New channel type: {new_channel_type}")
            print(f"                  Reason: {reason}")
            print()
            skipped += 1
            continue

        if compatible is None:
            print(f"[WARN-TYPE-UNKNOWN] {item_name}")
            print(f"                  old: {old_channel_uid}")
            print(f"                  new: {new_channel_uid}")
            print(f"            Item type: {item_type}")
            print(f"     New channel type: {new_channel_type}")
            print(f"               Reason: {reason}")

            warnings += 1

            if not MIGRATE_IF_CHANNEL_TYPE_UNKNOWN:
                print("               Action: skipped because the channel type is unknown")
                print()
                skipped += 1
                continue

        print(f"[MIGRATE] {item_name}")
        print(f"          old: {old_channel_uid}")
        print(f"          new: {new_channel_uid}")
        print(f"    Item type: {item_type}")
        print(f" Channel type: {new_channel_type}")
        print(f"        Check: {reason}")

        # Preserve existing target link configuration; do not overwrite it.
        if (item_name, new_channel_uid) in existing:
            print("[SKIP] Target link already exists; review manually")
            skipped += 1
            continue
        plan.append((item_name, old_channel_uid, new_channel_uid, config))
        migrated += 1
        print()

    warn_powerfactor_links(links)
    if len(plan) > 50:
        raise RuntimeError("More than 50 migrations; narrow the log input first")
    if not DRY_RUN and plan:
        if get_json("/rest/links") != links:
            raise RuntimeError("Links changed during planning; run a new preview")
        # Exclusive creation and owner-only permissions; no extra config file.
        fd = os.open(BACKUP_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as backup:
            json.dump(links, backup, indent=2)
    for item_name, old_uid, new_uid, config in plan:
        create_link(item_name, new_uid, config)
        delete_link(item_name, old_uid)

    print()
    print("Summary")
    print("=======")
    print(f"Candidates with existing link: {candidates}")
    print(f"Planned/applied migrations:     {migrated}")
    print(f"Skipped:                       {skipped}")
    print(f"Warnings:                      {warnings}")
    print(f"Notes:                         {notes}")

    if DRY_RUN:
        print()
        print("DRY_RUN is enabled. No changes were made.")
        print("Review the plan, then rerun with --execute --backup-file PATH to apply.")


def configure():
    global OPENHAB_URL, LOGFILE, DRY_RUN, BACKUP_FILE
    parser = argparse.ArgumentParser(description="Preview Shelly link migrations; no changes by default.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-file", type=Path)
    args = parser.parse_args()
    OPENHAB_URL = os.environ.get("OPENHAB_URL", "").rstrip("/")
    parsed = urlsplit(OPENHAB_URL)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        parser.error("Set OPENHAB_URL to an HTTP(S) base URL without credentials or path")
    LOGFILE = os.environ.get("OPENHAB_LOG", "")
    if not Path(LOGFILE).is_file():
        parser.error("Set OPENHAB_LOG to a readable log file")
    token = os.environ.get("OPENHAB_TOKEN", "")
    if os.environ.get("OPENHAB_TOKEN_FILE"):
        token = Path(os.environ["OPENHAB_TOKEN_FILE"]).read_text().strip()
    if not token or any(c in token for c in "\r\n") or token.startswith(("CHANGE_ME", "YOUR_")):
        parser.error("Supply OPENHAB_TOKEN_FILE or OPENHAB_TOKEN")
    session.auth = (token, "")
    DRY_RUN = not args.execute
    BACKUP_FILE = args.backup_file
    if args.execute and not BACKUP_FILE:
        parser.error("--execute requires --backup-file PATH (a new local file)")


if __name__ == "__main__":
    try:
        configure()
        main()
    except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
        detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f"Migration stopped: {detail}. Check inputs/connectivity and backup; completed actions are not rolled back.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Aborted. Check links and backup before retrying.", file=sys.stderr)
        sys.exit(130)

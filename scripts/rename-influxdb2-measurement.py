#!/usr/bin/env python3
"""Copy/merge an InfluxDB 2 measurement, verify field values, then optionally delete it.

The Flux set/to approach follows the SMA Bridge's influx2_copy_item.py generator.
This standalone tool adds execution, snapshots, merging and exact verification.
Requires only Python's standard library. Stop writers to BOTH measurements first.
"""

import argparse
import calendar
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request

# Configuration: adapt these anonymized examples in your local copy.
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "myorg"
INFLUX_BUCKET = "openhab_db"
INFLUX_TOKEN = "CHANGE_ME_INFLUXDB_API_TOKEN"
INFLUX_TOKEN_FILE = ""  # Optional example: "/etc/openhab/influxdb-token".
API_CA_FILE = ""  # Optional example: "/etc/openhab/certs/ca.crt".
OLD_MEASUREMENT = "ExampleDHT22_Humidity"
NEW_MEASUREMENT = "ExampleRoom_Humidity"
RENAME_ITEM_TAG = True  # Change only item=OLD_MEASUREMENT to item=NEW_MEASUREMENT.
DELETE_SOURCE = True  # False copies/merges and retains the source.
DRY_RUN = True  # --execute enables writes for one invocation.
BACKUP_DIR = "backups/influxdb-measurement-moves"
REQUEST_TIMEOUT = 120
MAX_EXPORT_BYTES = 1024 * 1024 * 1024  # Per export; snapshots are stored on disk.
# End configuration

# Complete InfluxDB 2 storage timestamp domain, including future points.
MIN_TIME = "1677-09-21T00:12:43.145224194Z"
MAX_TIME = "2262-04-11T23:47:16.854775807Z"
# Flux range stop is exclusive; the delete endpoint uses an inclusive valid storage bound.
DELETE_MAX_TIME = "2262-04-11T23:47:16.854775806Z"
META_COLUMNS = {"", "result", "table", "_start", "_stop", "_time", "_value", "_field", "_measurement"}


def flux_literal(value):
    """Escape names and reject Flux string interpolation."""
    if not value or "${" in value or any(ord(char) < 32 for char in value):
        raise ValueError("Names must be nonempty, without control characters or Flux interpolation")
    return json.dumps(value, ensure_ascii=False)


def read_query(bucket, measurement):
    return (f"from(bucket: {flux_literal(bucket)})\n"
            f"    |> range(start: time(v: {flux_literal(MIN_TIME)}), stop: time(v: {flux_literal(MAX_TIME)}))\n"
            f"    |> filter(fn: (r) => r._measurement == {flux_literal(measurement)})\n")


def copy_query(bucket, org, old, new, rename_item):
    """Keep all fields, types, timestamps and tags; rename only the selected Item tag."""
    query = "source = " + read_query(bucket, old)
    if rename_item:
        query += ("output = union(tables: [\n"
                  f"    source |> filter(fn: (r) => if exists r.item then r.item == {flux_literal(old)} else false)"
                  f" |> set(key: \"item\", value: {flux_literal(new)}),\n"
                  f"    source |> filter(fn: (r) => if exists r.item then r.item != {flux_literal(old)} else false),\n"
                  "    source |> filter(fn: (r) => not exists r.item),\n])\n")
    else:
        query += "output = source\n"
    return (query + f"output |> set(key: \"_measurement\", value: {flux_literal(new)})\n"
            f"    |> to(bucket: {flux_literal(bucket)}, org: {flux_literal(org)})\n"
            "    |> count(column: \"_value\") |> yield(name: \"copied_field_values\")\n")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Influx2API:
    def __init__(self, url, org, bucket, token, ca_file="", timeout=120, max_bytes=1024**3):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
            raise ValueError("Use an HTTP(S) base URL without credentials, path, query or fragment")
        if not token or token.startswith(("CHANGE_ME", "YOUR_")) or any(char.isspace() for char in token):
            raise ValueError("Set a real local InfluxDB API token or token file")
        if timeout <= 0 or max_bytes <= 0:
            raise ValueError("Timeout and export size limit must be positive")
        self.url, self.org, self.bucket, self.token = url.rstrip("/"), org, bucket, token
        self.timeout, self.max_bytes = timeout, max_bytes
        context = ssl.create_default_context(cafile=ca_file or None)
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))

    def post(self, path, payload, output=None):
        request = urllib.request.Request(self.url + path, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": "Token " + self.token, "Content-Type": "application/json",
                     "Accept": "application/csv" if output else "application/json"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                expected = 200 if output else 204
                if response.status != expected:
                    raise RuntimeError(f"Unexpected API status {response.status}")
                if output:
                    size = 0
                    with Path(output).open("xb") as target:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > self.max_bytes:
                                raise RuntimeError("Export size limit exceeded; source retained")
                            target.write(chunk)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"InfluxDB request failed with HTTP {error.code}; source deletion stopped") from None
        except urllib.error.URLError:
            raise RuntimeError("InfluxDB connection/TLS request failed; source deletion stopped") from None

    def query(self, query, output):
        self.post("/api/v2/query?" + urllib.parse.urlencode({"org": self.org}),
                  {"query": query, "type": "flux", "dialect": {"header": True,
                   "annotations": ["datatype", "group", "default"]}}, output)

    def delete(self, measurement):
        self.post("/api/v2/delete?" + urllib.parse.urlencode({"org": self.org, "bucket": self.bucket}),
                  {"start": MIN_TIME, "stop": DELETE_MAX_TIME,
                   "predicate": "_measurement=" + json.dumps(measurement)})


def timestamp_ns(value):
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z", value)
    if not match:
        raise ValueError("Unexpected non-UTC timestamp in export")
    seconds = calendar.timegm(datetime.strptime(match[1], "%Y-%m-%dT%H:%M:%S").timetuple())
    return seconds * 10**9 + int((match[2] or "0").ljust(9, "0"))


def field_value(kind, value):
    if kind == "double":
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Nonfinite numeric value in export")
        value = number.hex()
    elif kind in {"long", "unsignedLong"}:
        value = str(int(value))
    elif kind == "boolean":
        if value not in {"true", "false"}:
            raise ValueError("Invalid boolean in export")
    elif kind != "string":
        raise ValueError("Unsupported field datatype in export")
    return json.dumps([kind, value], ensure_ascii=False)


def create_table(db, table):
    db.execute(f"CREATE TABLE {table} (identity TEXT PRIMARY KEY, value TEXT NOT NULL)")


def import_snapshot(db, table, path, measurement, old, new, rename_item):
    """Index annotated CSV on disk, preserving nanoseconds and field types."""
    create_table(db, table)
    header, kinds, defaults = None, None, []
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        for row in csv.reader(source, strict=True):
            if not row or not any(row):
                continue
            if row[0] == "#datatype":
                kinds, header, defaults = row, None, []
                continue
            if row[0] == "#default":
                defaults = row
                continue
            if row[0].startswith("#"):
                continue
            if row[0] == "error":
                raise RuntimeError("InfluxDB returned a streamed query error")
            if row[0] == "" and "_time" in row and "_value" in row:
                if not kinds or len(row) != len(kinds) or len(row) != len(set(row)):
                    raise ValueError("Invalid annotated CSV header")
                if not {"_measurement", "_field", "_value", "_time"}.issubset(row):
                    raise ValueError("Missing field columns in export")
                header = row
                continue
            if not header or len(row) != len(header):
                raise ValueError("Malformed CSV export or missing datatype annotations")
            record = dict(zip(header, row))
            for index, name in enumerate(header):
                if record[name] == "" and index < len(defaults):
                    record[name] = defaults[index]
            if record["_measurement"] != measurement:
                raise ValueError("Unexpected measurement in export")
            tags = []
            for index, name in enumerate(header):
                if name in META_COLUMNS:
                    continue
                if kinds[index] != "string":
                    raise ValueError("Unexpected non-string tag column")
                value = record[name]
                if rename_item and name == "item" and value == old:
                    value = new
                tags.append((name, value))
            identity = json.dumps([timestamp_ns(record["_time"]), sorted(tags), record["_field"]], ensure_ascii=False)
            value = field_value(kinds[header.index("_value")], record["_value"])
            try:
                db.execute(f"INSERT INTO {table} VALUES (?, ?)", (identity, value))
            except sqlite3.IntegrityError:
                raise ValueError("Duplicate point identity after Item-tag mapping; source retained") from None
    db.commit()
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def equal_tables(db, left, right):
    for first, second in ((left, right), (right, left)):
        if db.execute(f"SELECT 1 FROM (SELECT * FROM {first} EXCEPT SELECT * FROM {second}) LIMIT 1").fetchone():
            return False
    return True


def check_query_errors(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        if any(row and row[0] == "error" for row in csv.reader(source, strict=True)):
            raise RuntimeError("InfluxDB returned a streamed copy error; source retained")


def move_measurement(api, old, new, backup_root, *, execute=False, delete_source=True, rename_item=True):
    if old == new:
        raise ValueError("Source and target must differ")
    for name in (api.org, api.bucket, old, new):
        flux_literal(name)
    Path(backup_root).mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix="move-", dir=backup_root))
    manifest = {"source": old, "target": new, "bucket": api.bucket, "org": api.org,
                "rename_item_tag": rename_item, "delete_source": delete_source, "status": "planning"}
    def status(value):
        manifest["status"] = value
        (folder/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with sqlite3.connect(folder/"verification.sqlite3") as db:
        def snapshot(table, measurement, transform=False):
            path = folder/(table+".csv")
            api.query(read_query(api.bucket, measurement), path)
            return import_snapshot(db, table, path, measurement, old, new, transform)
        source_count = snapshot("source_before", old, rename_item)
        target_count = snapshot("target_before", new)
        if not source_count:
            raise ValueError("Source measurement is empty; nothing copied or deleted")
        create_table(db, "expected")
        db.execute("INSERT INTO expected SELECT * FROM target_before")
        db.execute("INSERT OR REPLACE INTO expected SELECT * FROM source_before")
        db.commit()
        manifest.update(source_field_values=source_count, target_field_values=target_count)
        status("planned")
        print(f"Source field values: {source_count}; target field values: {target_count}; snapshots: {folder}")
        if not execute:
            status("dry_run")
            print("DRY-RUN: source values would overwrite matching target values; no database writes sent.")
            return folder
        snapshot("source_preflight", old, rename_item)
        snapshot("target_preflight", new)
        if not equal_tables(db, "source_before", "source_preflight") or not equal_tables(db, "target_before", "target_preflight"):
            raise RuntimeError("Source/target changed during planning; stop writers and run a new preview")
        status("copying")
        api.query(copy_query(api.bucket, api.org, old, new, rename_item), folder/"copy-result.csv")
        check_query_errors(folder/"copy-result.csv")
        snapshot("source_after_copy", old, rename_item)
        snapshot("target_after_copy", new)
        if not equal_tables(db, "source_before", "source_after_copy") or not equal_tables(db, "expected", "target_after_copy"):
            status("verification_failed_source_retained")
            raise RuntimeError("Copy verification failed; source retained and snapshots available")
        status("copy_verified")
        if delete_source:
            # No database-level transaction spans copy/verification/delete. Writers MUST be stopped.
            api.delete(old)
            if snapshot("source_after_delete", old, rename_item):
                status("delete_not_verified")
                raise RuntimeError("Source still contains data after deletion; inspect snapshots before retrying")
            status("move_verified")
            print("Target verified; source data deleted and empty source verified.")
        else:
            print("Copy/merge verified; source retained (--copy-only).")
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", default=OLD_MEASUREMENT)
    parser.add_argument("--new", default=NEW_MEASUREMENT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--copy-only", action="store_true")
    args = parser.parse_args(argv)
    token = Path(INFLUX_TOKEN_FILE).read_text().strip() if INFLUX_TOKEN_FILE else INFLUX_TOKEN
    api = Influx2API(INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, token, API_CA_FILE, REQUEST_TIMEOUT, MAX_EXPORT_BYTES)
    execute = args.execute or (not DRY_RUN and not args.dry_run)
    os.umask(0o077)
    move_measurement(api, args.old, args.new, BACKUP_DIR, execute=execute,
                     delete_source=DELETE_SOURCE and not args.copy_only, rename_item=RENAME_ITEM_TAG)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, csv.Error, sqlite3.Error) as error:
        detail = str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
        raise SystemExit(f"Stopped: {detail}. Keep the snapshots; completed target writes are not rolled back.")

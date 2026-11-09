# Copy, merge and move an InfluxDB 2 measurement

[`rename-influxdb2-measurement.py`](rename-influxdb2-measurement.py) is a standalone
Python 3.9+ tool using only the standard library. It copies all source field values
into a new or existing target measurement in the same bucket and, by default,
deletes the source after successful verification. It uses native InfluxDB 2
bucket/token APIs; it needs no InfluxQL DBRP mapping.

The Flux `set`/`to` copy pattern follows the SMA MQTT Bridge's
`tools/influx2_copy_item.py` generator. That generator only prepares Flux for an
empty destination. This tool adds actual HTTP execution, merging into an existing
target, disk snapshots, typed-value verification and optional source deletion.

## Configuration

Edit the examples near the top of the Python file:

```python
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "myorg"
INFLUX_BUCKET = "openhab_db"
INFLUX_TOKEN = "CHANGE_ME_INFLUXDB_API_TOKEN"
OLD_MEASUREMENT = "ExampleDHT22_Humidity"
NEW_MEASUREMENT = "ExampleRoom_Humidity"
RENAME_ITEM_TAG = True
DELETE_SOURCE = True
DRY_RUN = True
BACKUP_DIR = "backups/influxdb-measurement-moves"
```

Use a real local token with read and write permissions for the bucket. Optional
`INFLUX_TOKEN_FILE` and `API_CA_FILE` settings show example paths in comments.
Token files override the inline token; TLS verification remains enabled. Compose's
`.env` is not loaded. No real credentials belong in the repository.

## Behavior

- All supported history is copied, including future timestamps. There is no
  user-configured time window.
- Timestamp precision, field names/types and tags are retained. No aggregation
  or sampling is performed.
- For an existing target, source values replace target values with the same
  timestamp, complete tag set and field name. Other target values remain.
- With `RENAME_ITEM_TAG=True`, only `item=OLD_MEASUREMENT` becomes
  `item=NEW_MEASUREMENT`. Other Item-tag values and all other tags remain unchanged.
  If this transformation makes two source records ambiguous, execution aborts.
- Mixed field-type conflicts that the database refuses stop the operation. No
  conversion is silently applied, and the source is retained if copy fails.

For example, source `Old` has `value=10`, while the same target timestamp/tag set
has `value=5` and `extra="keep"`. After merging, the target has `value=10` and
`extra="keep"`. An existing target measurement is never dropped or recreated.

## Run

**Stop writers to both measurements before execution**, including relevant
persistence/rules/bridges. The tool does not stop services automatically.

```bash
# Read source/target and save a reviewable plan and snapshots; no database writes:
python3 scripts/rename-influxdb2-measurement.py

# Copy, verify and delete the original source data:
python3 scripts/rename-influxdb2-measurement.py --execute

# Copy/merge and verify, retaining the source:
python3 scripts/rename-influxdb2-measurement.py --execute --copy-only

# Optional name overrides:
python3 scripts/rename-influxdb2-measurement.py --old Old_Item --new New_Item
```

## Verification and recovery

Every run creates a private subdirectory of `BACKUP_DIR`. It stores the original
source/target as annotated CSV, additional verification exports, a SQLite
comparison index and a status manifest. SQLite keeps comparisons on disk rather
than loading entire histories into RAM. Counts in the output refer to field
values, not distinct timestamps.

Before copying, both measurements are reread and compared with the snapshots.
After copying, the tool compares the source again and checks the target against
the exact expected source-over-target merge, including types, values, tags and
nanosecond timestamps. Source deletion is sent only after these checks pass.
The source is queried again to verify that it is empty.

There is **no transaction or lock** spanning export, copy, verification and delete.
The checks detect changes between snapshots but cannot prevent a write in the
last gap before deletion. Keep writers stopped until the operation finishes.
An HTTP/Flux failure or verification mismatch stops further deletion. A failed
or interrupted copy can leave a partially updated target; there is no automatic
rollback. Preserve the exports and inspect the manifest before retrying.

Exports contain private data and stay under ignored `backups/`. They are recovery
material, not a complete native bucket backup or an automatic restore facility.
Take a [native backup](../docs/influxdb.md) first. Repeated exports/SQLite indexes
need free disk space; `MAX_EXPORT_BYTES` limits each response, not total disk use.
The tool runs only when invoked and introduces no background service.

Native deletion removes the original measurement's data across the full storage
time domain. An empty measurement name may remain visible in metadata/index
caches until maintenance; no other measurement or bucket is deleted.

Offline tests cover merging, source precedence, Item-tag mapping, field types,
nanoseconds, error handling and source retention. Isolated InfluxDB 2.9 checks
verify the same core path against real query/write/delete APIs. Live credentials,
custom server configuration and concurrent-writer operation are not validated.

References: [Flux `to`](https://docs.influxdata.com/flux/v0/stdlib/influxdata/influxdb/to/),
[InfluxDB 2 delete API](https://docs.influxdata.com/influxdb/v2/write-data/delete-data/).

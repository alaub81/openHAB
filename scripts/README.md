# Maintenance scripts

These optional tools run manually, not at container startup. Each is standalone;
copy the script you need and edit its configuration block near the top. Public
examples follow the original scripts, with anonymized identifiers and explicit
credential placeholders. Optional file settings have example paths in comments.
The InfluxDB tools now target **InfluxDB 2.x OSS**; the old 1.x tools were removed.
Their originals remain in the ignored local archive.

Bash tools require Bash, curl 7.55+ and jq 1.6+. The Python measurement mover uses
only Python 3.9+'s standard library. No shared runtime helper, environment file,
Docker socket access or CLI inside a database container is required. Configuration
is set in the script, not automatically loaded from Compose's `.env`.

## InfluxDB tools

| Script | Operation |
| --- | --- |
| `delete-influxdb2-measurement.sh` | Drops the configured `MEASUREMENTS` completely: all history, fields and tags, without `START`/`STOP`. Optional positional measurement names override the configured array. |
| `cleanup-openhab-influxdb2.sh` | Compares **all** measurement names with the current openHAB Item list and drops complete orphan measurements. Empty/invalid Item lists abort; Items are reread before execution. |
| `cleanup-influxdb2-integer.sh` | Reads field-type-conflict warnings from `OPENHAB_LOG` and drops the named **complete measurements**, including valid readings and all fields. It does not selectively remove integer values. |
| `delete-influxdb2-measurement-timerange.sh` | Deletes the selected measurements' data between the configured `START` and `STOP`. |
| `delete-influxdb2-timerange.sh` | Deletes **all measurement data** between `START` and `STOP`. Requires `--all-measurements` as the first argument. |
| `delete-wrong-influxdb2-measurements.sh` | Uses Flux to find values matching `MEASUREMENT`, `VALUE_FIELD`, `OPERATOR` and `THRESHOLD` across all history. Deletes complete points at precisely those timestamps, with predicates covering all tags. All fields of each selected point are removed. |
| `rename-influxdb2-measurement.py` | Copies/merges a source into a new or existing target, verifies typed values, tags and nanosecond timestamps, then deletes the source. Source values overwrite overlaps. [Detailed guide](rename-influxdb2-measurement.md). |

## Connection and credentials

`INFLUX_URL="http://localhost:8086"` connects directly to the published HTTP port.
In an old `docker exec ... influx` command, localhost meant the container; here it
means the machine running the script. Use the actual host/port if running elsewhere.
Prefer HTTPS outside a trusted local connection.

All InfluxDB tools authenticate with an **InfluxDB 2 API token**. Inline tokens
and optional token files are supported; files take precedence. `API_CA_FILE`
selects a private CA, otherwise system trust is used. TLS verification stays
active. Keep real credentials and configured local copies out of Git.

The three whole-measurement tools use InfluxDB 2's `/query` compatibility API
with `SHOW MEASUREMENTS` / `DROP MEASUREMENT`. Configure `INFLUX_DATABASE` with
the database name of a DBRP mapping to the intended bucket. The mapping must
resolve the intended default retention policy; the scripts do not create or
change it. The `influx v1 dbrp list` command can inspect mappings using an existing
CLI authentication profile. The compatibility endpoint is part of InfluxDB 2;
using it does not require an InfluxDB 1 server.

The timerange tools, wrong-value tool and Python mover use native bucket/org/token
APIs. They need `INFLUX_ORG` and `INFLUX_BUCKET`, without a DBRP mapping. The
wrong-value tool requires Flux with `types.isNumeric` (Flux 0.187+; available in
the repository's InfluxDB 2.9 image). No server version is detected automatically.

## Preview and execution

The InfluxDB tools currently default to `DRY_RUN=true` (Python: `True`). Bash
`--execute` / `--dry-run` override the configured mode for one invocation. Decide
preview behavior individually when adapting a script. Digitalstrom has no dry run.

```bash
# Complete measurement deletion, without user time bounds:
bash scripts/delete-influxdb2-measurement.sh --dry-run
bash scripts/delete-influxdb2-measurement.sh --execute

# Selected measurement data within the configured interval:
bash scripts/delete-influxdb2-measurement-timerange.sh --dry-run

# Complete bucket data within the configured interval:
bash scripts/delete-influxdb2-timerange.sh --all-measurements --dry-run
```

Full deletion and cleanup use `DROP MEASUREMENT`, without a time filter. Only
the timerange scripts have user-configured `START`/`STOP`. In InfluxDB 2.9's native
delete endpoint both boundaries are **inclusive**; UTC whole-second configuration
is supported by the timerange scripts. Wrong-value deletion uses identical start
and stop timestamps to avoid deleting a point one nanosecond later.

## Limits and checks

- Back up before deleting. See the [InfluxDB backup guide](../docs/influxdb.md).
  A preview is not a locked snapshot. Completed actions are not rolled back.
- Cleanup assumes measurement names equal Item names. Custom measurements and
  intentionally retained histories may appear as deletion targets; review them.
- `MAX_ACTIONS=50` limits measurements or selected timestamps/series, not the
  number of stored data points. Full measurement deletion can affect many points.
- Unsupported names, malformed responses and failed requests stop execution.
  Whole-measurement Bash tools accept simple letters/digits/underscore/dot/colon/
  hyphen names beginning with a letter or underscore. The Python mover escapes
  more general names and rejects Flux interpolation/control characters.
- The wrong-value Bash parser accepts standard unquoted Flux CSV fields. It
  refuses incomplete tag coverage, empty tag values and CSV-quoted tag values;
  it does not guess tag identities. Its preview reads data but sends no deletions.
- Tokens use private temporary header files in Bash; do not run with `bash -x`.
- Offline tests simulate API responses. Separate, isolated checks against the
  repository's InfluxDB 2.9 image verify actual protocol behavior; they do not
  establish compatibility with a live installation's bindings or credentials.

Run `./tests/linter-check.sh` for configuration checks and
`./tests/script-check.sh` separately for optional script tests. ShellCheck:
`shellcheck scripts/*.sh certs/generate-certs.sh`.

## Digitalstrom

See [Digitalstrom maintenance](digitalstrom_binding_tools.md). Status actions
only read; restart and refresh actions execute directly.

References: [InfluxDB 2 compatibility API](https://docs.influxdata.com/influxdb/v2/reference/api/influxdb-1x/),
[InfluxQL data management](https://docs.influxdata.com/influxdb/v2/query-data/influxql/manage-data/),
[native delete API](https://docs.influxdata.com/influxdb/v2/write-data/delete-data/),
[Flux numeric type check](https://docs.influxdata.com/flux/v0/stdlib/types/isnumeric/).

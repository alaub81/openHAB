# InfluxDB tuning and backups

The root Compose file provides InfluxDB 2 through the optional `influxdb` profile,
using the image tag from `docker-compose.yml` and initialization settings from
the local `.env`. Query/storage tuning and the backup mount are commented out
in the standard file. They are examples, not requirements for the widgets or
Blockly libraries.

The optional [`docker-compose.local.yml.example`](../docker-compose.local.yml.example)
instead contains active tuning settings and the backup mount. If you copy and
load that complete example, adapt or remove those settings before starting.
See [local overrides](deployment.md#image-versions-and-local-overrides).

## Optional query tuning

Enable the five commented `INFLUXD_QUERY_*` settings together when they match
your workload. The example was used on an 8 GiB Raspberry Pi 5:

| Setting | Example | Meaning |
| --- | ---: | --- |
| `INFLUXD_QUERY_CONCURRENCY` | `4` | Maximum concurrent Flux queries |
| `INFLUXD_QUERY_QUEUE_SIZE` | `10` | Maximum waiting queries; excess requests are rejected |
| `INFLUXD_QUERY_INITIAL_MEMORY_BYTES` | `67108864` | Initial query allocation: 64 MiB |
| `INFLUXD_QUERY_MEMORY_BYTES` | `1073741824` | Maximum memory per query: 1 GiB |
| `INFLUXD_QUERY_MAX_MEMORY_BYTES` | `2147483648` | Maximum combined query memory: 2 GiB |

These budgets do not cap total InfluxDB/container memory. Storage caches, indexes
and runtime overhead also consume RAM. Larger dashboards and longer query ranges
may hit the limits or queue; inspect errors and response times before tightening
them. The initial budget must not exceed the per-query budget.

## Optional storage tuning

| Setting | Example | Tradeoff |
| --- | --- | --- |
| `INFLUXD_STORAGE_MAX_CONCURRENT_COMPACTIONS` | `1` | Limits full/level compactions, potentially smoothing load but slowing background work; does not limit cache snapshots |
| `INFLUXD_STORAGE_WAL_FSYNC_DELAY` | `100ms` | Batches fsync calls at the cost of additional write latency |
| `INFLUXD_STORAGE_CACHE_MAX_MEMORY_SIZE` | `2147483648` | Cache limit of 2 GiB **per shard**, not for the database as a whole |
| `INFLUXD_STORAGE_CACHE_SNAPSHOT_MEMORY_SIZE` | `536870912` | Snapshots a shard's cache at 512 MiB; a larger threshold retains more data in memory before flushing |

The cache values are generous examples. Measure available host RAM, query load,
active shards and disk behavior before enabling them. They are ceilings or
thresholds, not a fixed reservation of the full configured memory.

`INFLUXD_NATS_PORT` is omitted because it has had no effect since InfluxDB 2.2.
The standard file omits the cold-cache snapshot duration because `10m` is already
the default; the Local example explicitly retains that value.
Long fsync-delay alternatives such as 15 or 30 seconds are not included: write
acknowledgements follow fsync and can be delayed significantly.

Validate with `docker compose config --quiet` and recreate InfluxDB during a
maintenance window after changing active environment values. Clients briefly
lose their database connection. `docker compose restart` alone does not apply
changed environment variables. Measure again during representative dashboard
and persistence activity; one idle snapshot cannot establish optimal settings.

## Manual backups

The optional volume line is:

```yaml
- "/backup/influxdb:/backup"
```

Create `/backup/influxdb` on the **Docker host**, ensure the InfluxDB container's
user can write to it, and uncomment that line under the service's `volumes`.
Recreate InfluxDB to apply the mount. The mount only provides a destination;
it does not create a backup or a schedule.

The Local example already enables this mount. Create and check the destination's
permissions before loading it; remove the mount if no backup destination is wanted.

The following example uses the existing operator token from the container's
initialization environment. It must still be a valid operator token for the
running database; editing initialization variables does not rotate credentials.
If that token is unavailable or revoked, provide a valid operator token through
your deployment's credential mechanism before running the backup.

```bash
docker compose exec -T influxdb sh -ec '
  test -w /backup
  export INFLUX_HOST=http://localhost:8086
  export INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"
  influx backup "/backup/$(date +%Y%m%d-%H%M%S)"
'
```

Keep successful backup directories together, copy them off-host and test a
restore in a separate instance. A destination on the same disk does not protect
against disk failure. Check version-specific backup/restore compatibility before
upgrades. This backup covers InfluxDB, not openHAB userdata or Grafana/PostgreSQL.

## References

- [InfluxDB configuration options](https://docs.influxdata.com/influxdb/v2/reference/config-options/)
- [WAL and cache behavior](https://docs.influxdata.com/influxdb/v2/reference/internals/storage-engine/)
- [InfluxDB backups](https://docs.influxdata.com/influxdb/v2/admin/backup-restore/backup/)

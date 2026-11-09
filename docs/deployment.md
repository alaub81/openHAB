# Deploy and operate the Docker stack

The [quick start](../README.md#quick-start-docker-stack) is for a new installation.
Run commands from the Compose project directory and keep the same project name,
Compose files and environment file for an existing deployment.

## Host requirements and storage

Use Linux with Docker Engine 25+ and Compose 2.20.2+ for the configured
`start_interval` healthchecks. Check with `docker version` and
`docker compose version`. Install Git and OpenSSL for checkout and certificate
preparation. Choose image versions available for the host's CPU architecture.

openHAB uses `network_mode: host` for local device access and discovery. Its
HTTP/HTTPS ports are configured through `.env`. Mosquitto, InfluxDB and Grafana
publish their configured ports; PostgreSQL and the renderer have no published
host ports. The internal backend network connects the database and rendering
services. The app network also allows services to reach external sources.

## Optional service profiles

Copy `.env.example` to `.env` for a new installation. openHAB is the only service
without a profile and always participates in ordinary `up` commands. Configure
`COMPOSE_PROFILES` in the local `.env`:

| Profile | Services |
| --- | --- |
| `mqtt` | Mosquitto |
| `influxdb` | InfluxDB |
| `grafana` | Grafana, PostgreSQL and the Image Renderer together |

The example enables the complete stack with
`COMPOSE_PROFILES=mqtt,influxdb,grafana`. Remove profiles you do not need, or
leave the value empty for openHAB alone. The Grafana
profile can use an external InfluxDB or another data source; the local InfluxDB
profile is independent. Configure external connections in the applications.

```bash
# Start the selection saved in .env.
docker compose up -d

# Enable all optional services for this command.
docker compose --profile '*' up -d
```

Command-line profiles add to those selected in `.env`; they do not subtract
profiles already enabled there. An explicitly targeted service can also start
without enabling its profile manually. For normal operation, use the profile
selection so related services are managed together. Disabling a profile does
not stop an already running container: stop the unwanted services explicitly
before changing the selection. For example, stop `grafana renderer postgres`
together when retiring the bundled Grafana package. Keep their volumes.

Compose resolves variables before filtering profiles. Retain the complete
template's declarations, even for unused services. The renderer-token `:?`
checks still reject an empty or missing token during configuration parsing;
the template placeholder may remain only while `grafana` is disabled. Set a
real shared token before enabling it.

## Storage

| Storage | Purpose |
| --- | --- |
| `data/openhab/conf/` and `data/openhab/addons/` | Bind-mounted configuration and add-ons |
| `data/mosquitto/conf/` | Bind-mounted broker configuration, password file and TLS certificates |
| `data/influxdb/conf/` | Bind-mounted optional InfluxDB configuration |
| `data_openhab_userdata` | openHAB runtime state, JSONDB and installed add-ons |
| `data_influxdb` | InfluxDB database |
| `data_postgres` | Grafana's PostgreSQL database |
| `data_grafana` | Grafana plugins and local files |
| `data_mosquitto_data` and `data_mosquitto_log` | MQTT persistence and logs |

Docker prefixes named volumes with the effective Compose project name.
`PROJECT_NAME` in `.env` controls bridge-interface names; the template does not
set `COMPOSE_PROJECT_NAME`. Preserve your existing directory name or explicit
`docker compose -p ...` selection to reuse the same volumes. Keep `PROJECT_NAME`
short as documented in `.env`.

## Credentials and permissions

The repository tracks a sanitized `.env.example`; local `.env` files are ignored.
Copy the template once for a new installation, then replace placeholders for
enabled services in the server's local `.env`. Generate
separate values with `openssl rand -hex 32`. The renderer token is shared by
Grafana and the renderer; missing or empty values fail Compose validation.

InfluxDB initialization variables and PostgreSQL's initial password apply when
initializing empty database storage. Editing them alone does not rotate
credentials in an existing database. Preserve working credentials when updating.

The Compose file sets openHAB's `USER_ID` and `GROUP_ID` to `9001`. Ensure its
bind-mounted directories are writable by those IDs, or adapt both IDs and
ownership to your existing installation. Creating a matching host account is
optional; numeric ownership is sufficient. Do not change ownership of an
existing deployment until its current IDs and mounts have been checked.

Grafana uses its image-default non-root user. Existing root-based installations
should follow the [Grafana migration guide](grafana-non-root-migration.md) before
removing their user override. When enabling `mqtt`, complete
[MQTT preparation](mqtt.md) before the broker's first startup because its password
file and certificates are bind mounts.

## Connect the applications

Compose starts infrastructure; it does not create Things, linked Items, Grafana
dashboards, data sources or application-specific rules.

Follow only the optional integration steps you need:

1. Complete openHAB's first-run setup and create its administrator account.
2. For MQTT, install the MQTT binding. With the local `mqtt` profile, openHAB uses
   the host network, so configure its
   broker Thing with `127.0.0.1` and the published MQTT port from `.env`, plus the
   username/password created during MQTT setup. Port 1883 is plaintext; for TLS
   use the certificate's matching host name, the published TLS port and CA trust.
3. For InfluxDB persistence, install InfluxDB Persistence and configure a connection.
   With the local `influxdb` profile, use the
   published address, normally `http://127.0.0.1:8086`, your organization, bucket
   and an appropriate read/write token. The included
   [`influxdb.persist`](../data/openhab/conf/persistence/influxdb.persist) applies
   `everyUpdate` and `restoreOnStartup` to all Items for this persistence service;
   adapt that broad policy to your own retention and write-volume requirements.
4. For the `grafana` profile, sign in to Grafana. If using local InfluxDB, add a
   data source using Flux,
   `http://db:8086`, the same organization/bucket, and an appropriate read token.
   This is a container-network address; `localhost` inside Grafana is Grafana
   itself. For external services, use their reachable addresses. PostgreSQL is
   already selected through Grafana's environment settings.
5. Install bindings supplying the Items needed by your selected
   [widgets](../data/openhab/conf/yaml/widgets/README.md). For Blockly rules, install the JavaScript
   Scripting automation add-on and follow the
   [library guide](../data/openhab/conf/yaml/block_libraries/README.md).

For email, enable `GRAFANA_SMTP_ENABLED` and configure all relevant SMTP settings
in `.env`. The SMTP password must match the existing mail account.

## Healthchecks and shutdown

All six available services have healthchecks. openHAB and the renderer inherit their
probe commands from the images; Compose adjusts timings. Other probes check
the MQTT listener, InfluxDB health, PostgreSQL readiness and Grafana's database
health. openHAB's local MQTT/InfluxDB dependencies and Grafana's local InfluxDB
dependency use `required: false`, allowing those profiles to stay disabled.
When selected, healthchecks coordinate startup; unavailable optional dependencies
can generate warnings without preventing the application from starting.
Grafana requires its PostgreSQL and renderer services, both in the same profile.

openHAB is checked every five minutes after startup, with 30-second checks during
its startup period. Grafana is checked every five minutes; the other services
every minute. Database and broker startup checks run every five seconds.
`unhealthy` is a status: Docker's restart policy alone does not restart an
unhealthy but still running container. Autoheal and Watchtower are not included.
Watchtower labels are provided as optional comments for an existing external
Watchtower deployment; its own selection settings determine what it updates.

Graceful stop periods are two minutes for openHAB and one minute each for
InfluxDB and PostgreSQL. These are maximum shutdown waits, not ongoing delays.

```bash
docker compose ps
docker compose logs --tail=100 openhab
```

When the `grafana` profile is enabled, check its HTTP endpoint after startup:

```bash
docker compose exec -T grafana wget -qO- http://localhost:3000/api/health
```

Run the Grafana HTTP check after startup; an immediate connection refusal can
mean the HTTP listener is not ready yet. A successful Grafana check reports
`database: ok`. If a dependency remains unhealthy, inspect its logs before
recreating dependent services.

## Updates and backups

When first updating from the older revision that tracked `.env`, save a copy
outside the checkout before pulling. The update removes that tracked path;
restore your deployment copy afterward if needed. Do not overwrite it with the
new example. For the previous full-stack behavior, add
`COMPOSE_PROFILES=mqtt,influxdb,grafana` to the preserved local `.env` before
running Compose commands. This repository-local migration leaves an existing
local `.env` in place while removing it from Git tracking.

Back up the deployment configuration, openHAB userdata, databases and other
persistent volumes before an upgrade. See [InfluxDB backups](influxdb.md#manual-backups)
and the database/volume backup procedure in the
[Grafana guide](grafana-non-root-migration.md). Keep copies off the Docker host.

Review `.env` changes while preserving real credentials, image versions, project
identity and host-specific mounts. Check database release and major-version
migration requirements before changing image tags. The PostgreSQL 18 mount in
this repository must not be applied blindly to older PostgreSQL installations.

Validate with `docker compose config --quiet`. `docker compose up -d` recreates
services with changed configuration, retaining their mounted volumes. An ordinary
`restart` does not apply changed environment variables or mounts. Use
`--pull never` for configuration-only work when the required image tags already
exist locally; it prevents downloads but does not pin a tag to the image ID of
the currently running container. The Grafana migration guide shows exact-image
pinning when that is required.

Do not use `down -v` for routine updates: it removes the project's named volumes.
The optional [InfluxDB tuning block](influxdb.md) is disabled by default and should
be adapted separately from an image upgrade.

## References

- [Docker Compose services](https://docs.docker.com/reference/compose-file/services/)
- [Compose up](https://docs.docker.com/reference/cli/docker/compose/up/)
- [openHAB Docker deployment](https://www.openhab.org/docs/installation/docker.html)
- [InfluxDB Persistence](https://www.openhab.org/addons/persistence/influxdb/)
- [Grafana InfluxDB data source](https://grafana.com/docs/grafana/latest/datasources/influxdb/configure-influxdb-data-source/)

# openHAB Docker setup, widgets and Blockly libraries

Run openHAB with MQTT, time-series storage and Grafana dashboards using Docker
Compose. Add reusable MainUI widgets and Blockly blocks for climate control,
weather, batteries, windows, doors and alarms to your own openHAB installation.

## Features

- **Optional infrastructure:** openHAB runs on its own; Compose profiles add
  Mosquitto, InfluxDB 2, or Grafana with PostgreSQL and the Image Renderer.
- **Twelve MainUI widgets:** compact overview cells, DWD warning and pollen
  strips, and thermostat list controls with configurable Item selections.
- **Five Blockly libraries:** shared alarm handling, battery and humidity
  monitoring, thermostat control, and Thing enable/disable actions.
- **File-based configuration:** versioned YAML sources loaded directly by
  openHAB, with inactive Thing and Item examples for optional integrations.
- **Operational defaults:** healthchecks, graceful shutdown periods, non-root
  Grafana, shared renderer authentication, and optional InfluxDB tuning.
- **Maintenance tools and checks:** administrative scripts, widget/rule
  generators, regression checks, and a read-only repository linter.

## Quick start: Docker stack

Use a Linux Docker host with Git, Docker Engine 25+ and Compose 2.20.2+.
The supplied configuration targets openHAB 5.2.3 and uses host networking for
openHAB. Existing installations can use the widgets and libraries independently;
skip to the [openHAB quick start](#quick-start-widgets-and-blockly-libraries).

### 1. Prepare a new installation

```bash
git clone https://github.com/alaub81/openHAB.git
cd openHAB
cp .env.example .env
chmod 600 .env
```

Edit your local `.env` using [`.env.example`](.env.example) as the reference.
Set the timezone, ports and desired image versions. Choose optional services:

| `COMPOSE_PROFILES` | Services started with openHAB |
| --- | --- |
| `mqtt,influxdb,grafana` (default) | All bundled services |
| Empty | None; openHAB only |
| `mqtt` | Mosquitto |
| `influxdb` | InfluxDB 2 |
| `grafana` | Grafana, PostgreSQL and the Image Renderer |

Combine any profiles with commas. Configure credentials for the services you
enable; generate each password/token separately with `openssl rand -hex 32`.
For Grafana, set its server URL and replace the shared
`GRAFANA_RENDERING_RENDERER_TOKEN`. Configure SMTP only if you need email.
Keep unused service declarations from the template; Compose also resolves
variables belonging to inactive profiles.

Only `.env.example` is versioned; `.env` is ignored by Git. Keep an existing
`.env` when updating, and preserve its credentials, project identity and volumes.

### 2. Prepare MQTT and permissions

If enabling `mqtt`, complete the [MQTT setup](docs/mqtt.md) **before starting the
broker**: replace the public example login (`mosquitto` / `mosquitto-mqtt`)
and provide TLS certificates. Skip this step when
using openHAB alone or an external broker.

For a new checkout, allow openHAB's configured UID/GID `9001:9001` to write its
bind-mounted configuration and add-ons directories:

```bash
sudo chown -R 9001:9001 data/openhab
```

For different IDs or an existing installation, follow the
[deployment guide](docs/deployment.md) instead of changing ownership blindly.

### 3. Validate and start

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=100 openhab
```

Allow openHAB to finish its first startup. Enabled services use these default ports:

| Service | URL |
| --- | --- |
| openHAB | `http://YOURSERVERNAME:8080` or `https://YOURSERVERNAME:8443` |
| Grafana | `http://YOURSERVERNAME:3000` |
| InfluxDB | `http://YOURSERVERNAME:8086` |

Complete openHAB's setup and add the bindings you need. Configure MQTT, persistence
and Grafana data sources for the local profiles or external services you use.
These application connections and dashboards are not provisioned by Compose; see
[connecting the services](docs/deployment.md#connect-the-applications).

## Quick start: widgets and Blockly libraries

The Docker setup already mounts the bundled YAML into openHAB. On another
installation, copy only the desired `.yml` files from:

- [`data/openhab/conf/yaml/widgets/`](data/openhab/conf/yaml/widgets/) to
  `$OPENHAB_CONF/yaml/widgets/`.
- [`data/openhab/conf/yaml/block_libraries/`](data/openhab/conf/yaml/block_libraries/)
  to `$OPENHAB_CONF/yaml/block_libraries/`.

Keep the `version: 1` wrapper intact. Reload MainUI after loading the files.
Widgets and libraries appear file-managed; no manual MainUI import is required.
Files ending in `.example` remain inactive until deliberately adapted and renamed.

**Widgets:** add a personal widget to a page and select your own Items/groups.
For example, place this component inside an `oh-grid-cells` container:

```yaml
component: widget:batterie_ladestaende_cell
config:
  title: Batteries
  batteryGroup: MyBatteryGroup
```

The [widget catalog](data/openhab/conf/yaml/widgets/README.md) lists all widgets, their requirements,
and Page YAML examples for the battery, humidity, light, and window cells.
Widgets display or control existing Items; they do not create your semantic
model or alarm rules. Existing widget IDs and UI labels are retained.

**Blockly libraries:** install the **JavaScript Scripting** automation add-on,
create a rule with suitable triggers and a Blockly script action, then choose
the blocks from the library toolbox. Select your Items, configure thresholds or
device profile IDs, and add notification actions where required. Loading a
library does not create or run a rule. Start with the
[library catalog and rule setup](data/openhab/conf/yaml/block_libraries/README.md).

## Guides and development

- [Documentation index](docs/README.md)
- [Deployment, service connections, healthchecks and updates](docs/deployment.md)
- [MQTT passwords and TLS](docs/mqtt.md)
- [InfluxDB tuning and backups](docs/influxdb.md)
- [Grafana migration from root to its image-default user](docs/grafana-non-root-migration.md)
- [Thing templates and Somfy sun sensors](data/openhab/conf/yaml/things/README.md)
- [Development tools](tools/README.md) and [repository checks](tests/README.md)

Run `./tests/linter-check.sh` to validate the repository without starting containers.

Related projects: [SMA MQTT Bridge](https://github.com/alaub81/sma-mqtt-bridge)
and [BMW MQTT Bridge](https://github.com/alaub81/bmw-mqtt-bridge). Their services
are configured separately; this Compose file does not deploy either bridge.

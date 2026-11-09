# Documentation

Start with the [repository quick start](../README.md). The guides below cover
installation details, reusable openHAB components, and maintenance.

## Deployment and operations

| Guide | Contents |
| --- | --- |
| [Deployment](deployment.md) | Host requirements, permissions, connections between services, healthchecks, updates and troubleshooting |
| [MQTT](mqtt.md) | Create the broker password file and prepare TLS certificates before first startup |
| [InfluxDB](influxdb.md) | Optional resource tuning, backup destination and manual backups |
| [Grafana non-root migration](grafana-non-root-migration.md) | Back up an existing Grafana instance and prepare volume permissions |

## openHAB components

| Catalog | Contents |
| --- | --- |
| [Widgets](../data/openhab/conf/yaml/widgets/README.md) | All twelve widgets, Item requirements and Page YAML examples |
| [Blockly libraries](../data/openhab/conf/yaml/block_libraries/README.md) | All five libraries, installation and rule setup |
| [Things and Item templates](../data/openhab/conf/yaml/things/README.md) | Inactive Shelly and Somfy examples |

Runtime YAML and its component-specific documentation remain together under
[`data/openhab/conf/yaml/`](../data/openhab/conf/yaml/). The `docs/` directory
contains cross-cutting deployment and operations guides. Markdown files do not
need to be copied to openHAB. Existing German file names, Item identifiers and UI
labels are preserved.

Private investigation records and original configurations are retained only in
the ignored local `archive/` directory. They are not required for installation.
Example Item names and UI labels remain illustrative; select your own Items.
Run repository-relative commands from the repository root unless stated otherwise.

## Maintenance and development

- [Maintenance scripts](../scripts/README.md) documents explicit targets, credentials,
  dry runs and the effect of each administrative operation.
- [Development tools](../tools/README.md) describes generators and component checks.
- [Repository checks](../tests/README.md) describes the linter and its prerequisites.

Earlier setup articles: [openHAB 4 Docker installation](https://www.laub-home.de/wiki/OpenHAB_4_Docker_Installation)
and [openHAB 3 Docker installation](https://www.laub-home.de/wiki/OpenHAB_3_Docker_Installation).
Use the current Compose file and guides for this repository's configuration.

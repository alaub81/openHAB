# openHAB Setup and Tools

In this repsoitory I collect everything needed to have a good running openHAB Setup. This Setup is based on a docker compose deployment. Included you can find the following toolset:

* openHAB - Smart Home Hub
* InfluxDB2 - for persistence
* grafana inclusive renderer - for the visualization of data
* postgres - for grafana configuration
* Mosquitto MQTT - MQTT Broker for IoT Devices

## Docker compose project

Just clone that complete repository (e.g. under `/opt/`):

```bash
git clone https://github.com/alaub81/openHAB.git
```

And configure the `.env`file.

* Change the passwords!
* If you like to have grafana configured for mailing, change `GF_SMTP_ENABLED=true` and configure you mail setup.

Then you can create an openhab user and group on the host system if you like to map them.

```bash
groupadd -g 9001 openhab
useradd -u 9001 -g openhab -r -s /sbin/nologin openhab
```

Now we need the certificates for the secure mqtt connection of Mosquitto. For the generation of the certs we will use the `generate-certs.sh`. Just configure the script upfront:

* Configure at least the `IP` Variable, use the FQDN
* Change all other variables to your needs!

```bash
cd /opt/openHAB/certs
chmod +x generate-certs.sh
./generate-certs.sh
```

After that you schould be able to start the whole setup with:

```bash
cd /opt/openHAB
docker compose up -d
```

Now the Setup should be reachable:

* openHAB: <http://YOURSERVERNAME:8080> und <https://YOURSERVERNAME:8433>
* Grafana: <http://YOURSERVERNAME:3000>
* InfluxDB: <http://YOURSERVERNAME:8086>

### Configure Mosquitto User

to connect to the secure MQTT Broker, you need at minimum one configured user. Just create the first one:

```bash
cd /opt/openHAB
docker compose exec mosquitto mosquitto_passwd -c /mosquitto/config/mosquitto.passwd mosquitto
```

### Container healthchecks

The healthcheck settings were synchronized with the Raspberry Pi on 2026-10-31.
The root `docker-compose.yml` contains the active timings for its six services.
Existing probe commands are retained; openHAB and the renderer inherit their
probe commands from their container images.

The [healthcheck overrides](deploy/healthchecks/) also preserve the timings of
all 20 configured checks across the Pi's three Compose projects:

| Override | Existing base file on the Pi | Checks |
| --- | --- | ---: |
| [openhab.yml](deploy/healthchecks/openhab.yml) | `/opt/openhab5/docker-compose.yml` | 9 |
| [tools.yml](deploy/healthchecks/tools.yml) | `/opt/tools/docker-compose.yml` | 9 |
| [portwatcher.yml](deploy/healthchecks/portwatcher.yml) | `/opt/portwatcher/docker-compose.yml` | 2 |

Use each override together with the corresponding **existing Pi base file**.
The openHAB override includes the SMA bridge and both BMW bridges, whose service
definitions are present in the Pi's base file but are not part of this
repository's root Compose file. Smokeping has no configured healthcheck.
The overrides contain healthcheck timings only and inherit the existing probe
commands, images, volumes, credentials and startup dependencies from the base file.

For example, with this repository checked out at `/opt/openHAB`, validate the
combined configuration using:

```bash
docker compose -f /opt/openhab5/docker-compose.yml \
  -f /opt/openHAB/deploy/healthchecks/openhab.yml config --quiet
```

For a future deployment, use the same pair of files with `up -d`; Compose will
recreate services whose configuration changed. The repository synchronization
itself does not require recreating the already updated Pi containers.

`interval` controls checks during normal operation. `start_interval: 5s` provides
fast readiness checks during the configured `start_period`, so dependent services
can start promptly. A successful check ends the startup phase immediately.
The MariaDB configuration retains five retries and a 60-second startup period;
Autoheal's own check runs every 60 seconds and its monitoring loop every 120
seconds. `unhealthy` alone does not restart a container; Autoheal selects the
containers carrying its configured label.

## Grafana process user

Grafana uses the image default non-root user. For an existing installation that
previously ran as root, follow the [migration and verification guide](docs/grafana-non-root-migration.md)
to back up data, adjust volume permissions, and verify the running service.

## Scripts / Tools

here you can find some usefull scripts I am using to administrate my openHAB setup. For example there are some scripts to do things in the persistence layer - influxDB. Or to bring more stability into the digitalstrom binding. Just have a look at the descriptions on top of each script.

To make the scripts running, please add the execute right to them and then just start it, e.g.:

```bash
cd scripts
chmod +x cleanup-influxdb-integer.sh
./cleanup-influxdb-integer.sh
```

## Development tools and archived migrations

`scripts/` contains the administrative shell scripts. Reusable widget and rule
generators, source code and checks are kept in [tools/](tools/README.md).
One-off migration scripts and deployment exports were moved to
`archive/scripts-cleanup-20261108/`; see the tools README for the inventory.
The archive is local and excluded from Git. The tools are eligible for versioning.

## Repository checks

Run `./tests/linter-check.sh` to check configuration and source syntax without
starting containers. See [tests/README.md](tests/README.md) for prerequisites,
coverage, and the intentionally excluded Pi 5 comparison file.

## Links

If you need more Details about the setup:

* <https://www.laub-home.de/wiki/OpenHAB_4_Docker_Installation>
* <https://www.laub-home.de/wiki/OpenHAB_3_Docker_Installation>

## Historical project material

The [2026-10-30 project import](archive/chatgpt-project-2026-10-30/README.md) preserves
widget drafts, deployment exports and SMA reference packages from the former
ChatGPT project folder. See its manifest and private-backup notes before cleanup.

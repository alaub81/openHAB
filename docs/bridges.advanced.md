# Optional SMA and BMW MQTT bridges

This opt-in extension deploys the published SMA MQTT Bridge and BMW CarData MQTT
Bridge images alongside the existing openHAB stack. It does not copy their source
code, widgets or application configuration into this repository.

| Profile | Service | Purpose |
| --- | --- | --- |
| `sma` | `sma-mqtt-bridge` | Publish measurements from configured supported SMA sources through Homie MQTT |
| `bmw` | `bmw-mqtt-bridge` | Forward BMW CarData telemetry to your MQTT broker, with optional Homie discovery |

Both profiles are **disabled by default**. The ordinary
[`docker-compose.yml`](../docker-compose.yml) and [`.env.example`](../.env.example)
remain unchanged. Loading the extension does not enable either profile.
SMA sources and command gates are configured in the private `smab.env`; upstream
defaults disable sources and writes. An existing file keeps its own settings.
The BMW bridge forwards telemetry and has no vehicle commands.

## 1. Prepare the existing stack

Use a Linux Docker host and complete the [standard quick start](../README.md#quick-start-docker-stack),
including MQTT accounts and certificates if using the local `mqtt` profile.
The extension requires Docker Compose **2.24.0+** for optional `env_file` support,
in addition to the base setup requirements.
It is a companion to the base file, not a standalone Compose application.

For a **new installation**, prepare the stack environment file:

```bash
cp .env.example .env
cat .env.advanced.example >> .env
chmod 600 .env
```

For an **existing installation**, keep `.env` and all working credentials. Add
the settings from [`.env.advanced.example`](../.env.advanced.example) once, without
duplicating assignments. Do not replace `.env` with the advanced supplement: it
does not contain the base stack settings. SMA application settings belong in
`smab.env`; do not copy them into `.env`. An additional JSON file is not required.

The supplement sets:

```dotenv
COMPOSE_FILE=docker-compose.yml:docker-compose.advanced.yml
```

This Linux file list makes ordinary `docker compose` commands load the base file
and [`docker-compose.advanced.yml`](../docker-compose.advanced.yml), in that order.
Keep any existing custom Compose files and the same Compose project name when
adapting an existing deployment. Run commands from the repository root. If you
use `-f` explicitly, supply both files; explicit `-f` replaces `COMPOSE_FILE`.
See Docker's [multiple-file guide](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/).

For personal overrides, create an ignored `docker-compose.local.yml` and load it
**last**. This layer can retain host-specific image variables, tuning, mounts or
additional services without changing the public files:

```dotenv
COMPOSE_FILE=docker-compose.yml:docker-compose.advanced.yml:docker-compose.local.yml
```

Do not add that third path until the local file exists. `.env`, `smab.env`, the
local override, the private SMA configuration directory and supplied Pi5 reference
file are ignored by Git. Keep independent backups of them. Git updates do not
back up or distribute these files. Retain the existing Compose project name;
changing it can select new empty named volumes.

Leave the existing assignment below in place until the bridges are configured:

```dotenv
COMPOSE_PROFILES=mqtt,influxdb,grafana
```

Add `sma`, `bmw`, or both to that **existing** assignment when ready:

```dotenv
COMPOSE_PROFILES=mqtt,influxdb,grafana,sma,bmw
```

The bridge profiles do not require the local `mqtt` profile: both can use an
external broker. Set its reachable address, port, account and TLS settings.
Keep `BMB_BMW_CLIENT_ID` and `BMB_BMW_GCID` declared even when the BMW profile is
disabled: Compose evaluates their required-variable checks before filtering
profiles. The advanced template provides placeholders for an unused BMW service;
replace them with real IDs before enabling and authenticating it. Other unused
bridge credentials may be absent. Compose validation does not establish that
credentials, image tags or physical devices work.

## 2. Configure MQTT connections

Create bridge accounts in your broker, or select accounts you already manage.
Set SMA MQTT credentials in `smab.env` and BMW MQTT credentials in `.env`. The
template placeholders are not working credentials. Editing either ENV file does
not create broker users. Follow the [MQTT guide](mqtt.md) for the bundled broker.

The network addresses intentionally differ:

| Bridge | Network | Local broker address | Port |
| --- | --- | --- | --- |
| SMA | Linux host | `127.0.0.1` | Published host port, normally `1883`; update `SMAB_MQTT_PORT` if `MOSQUITTO_MQTT_PORT` differs |
| BMW | `app-nw` and `backend-nw` | `mosquitto` on `app-nw` | Container port `1883`, even if its published host port differs |

`localhost` inside BMW's container is not the broker. A public MQTT listener is
not needed for communication between BMW and the local broker. Neither bridge
publishes an additional host port. The examples below explicitly select
plaintext for the local host/container network; SMA itself defaults to verified
MQTT TLS on port 8883. BMW's upstream CarData connection is encrypted independently.

The template explicitly sets `BMB_MQTT_LOCAL_HOST=mosquitto` for the bundled
broker. If the variable is absent or empty, the Compose fallback is
`host.docker.internal`; ordinary Linux Engine installations need that name
configured separately. Set a reachable broker address in `.env` rather than
relying on this fallback. `BMB_MQTT_LOCAL_CLIENT_ID` can select a unique client
identity; use different IDs when running additional bridge instances.

For a remote broker, enable MQTT TLS and use its certificate-matching hostname
and TLS port. Verification defaults to enabled. For SMA with a private CA, put
its public certificate under `./data/sma-mqtt-bridge/` and select its **container** path in
`smab.env`, for example `SMAB_MQTT_TLS_CA_FILE=/data/sma-mqtt-bridge/config/ca.crt`.
For BMW, uncomment its optional read-only CA mount and set
`BMB_MQTT_LOCAL_TLS_CA_FILE=/etc/bridge-mqtt-ca.crt` in `.env`. Ensure files exist
and are readable by the image's non-root user. Mount only the public CA
certificate, not the CA private key. For a publicly trusted BMW MQTT broker,
the image's system CA bundle is used by default.

## 3. Enable SMA measurements

Keep your existing `smab.env` in the project root. Its full contents are loaded
through the service's `env_file`; the Compose service does not overlay runtime
settings through `environment`. `.env` contains only the SMA image tag, ENV-file
path and container UID/GID:

```dotenv
SMAB_BRIDGE_VERSION=latest
SMAB_ENV_FILE=./smab.env
SMAB_UID=10001
SMAB_GID=10001
```

For a new installation, create `smab.env` and start with this example, adapting
addresses, account, password and the exact supported model before enabling `sma`:

```dotenv
SMAB_MQTT_HOST=127.0.0.1
SMAB_MQTT_PORT=1883
SMAB_MQTT_TLS=false
SMAB_MQTT_USERNAME=sma-bridge
SMAB_MQTT_PASSWORD=CHANGE_ME_SMA_MQTT_PASSWORD
SMAB_INVERTER1_ENABLED=true
SMAB_INVERTER1_HOST=inverter.example.invalid
SMAB_INVERTER1_PROFILE=sma-stp8-0-3av-40
SMAB_COMMANDS_ENABLED=false
```

Create the broker account first; generate a password with `openssl rand -hex 32`
and set the same value on both sides. Modbus TCP must be enabled on the inverter.
Use the upstream [ENV reference](https://github.com/alaub81/sma-mqtt-bridge/blob/main/smab.example.env)
and [profile guide](https://github.com/alaub81/sma-mqtt-bridge/blob/main/docs/PROFILES.md)
for devices, firmware, unit IDs, additional inverters, eCharger, BYD and plant
calculations. These settings all belong in `smab.env`; no Compose mapping is
needed for additional application variables. Do not assume compatibility from
a similar model name. Retain any existing command-gate choices in a working
installation; the integration does not change them or issue commands itself.

The `./data/sma-mqtt-bridge` bind contains optional custom profiles, JSON configuration
and certificates. The public extension mounts it read-only, with runtime state
in `data_smab_state`. The directory must be readable by UID/GID `10001:10001`, or
the configured replacement. For a new default directory:

```bash
mkdir -p data/sma-mqtt-bridge
chmod 600 smab.env
```

No JSON file is required. The optional ENV-file declaration allows the disabled
profile to coexist with a checkout that has no `smab.env`; prepare and verify the
file before enabling `sma`. The profile does not enable sources by itself.

For Sunny Home Manager UDP or supplemental phase telegrams, follow the upstream
[Home Manager guide](https://github.com/alaub81/sma-mqtt-bridge/blob/main/docs/HOME_MANAGER_MODBUS.md).
Configure its actual serial, host and multicast interface in `smab.env`.
Host networking is selected so UDP multicast can reach the bridge; Modbus alone
does not require it. Enable at least one configured source before starting.
Then add `sma` to `COMPOSE_PROFILES` and run:

```bash
docker compose config --quiet
docker compose pull sma-mqtt-bridge
docker compose run --rm --no-deps sma-mqtt-bridge --check-config
docker compose up -d sma-mqtt-bridge
docker compose ps sma-mqtt-bridge
docker compose logs --tail=100 sma-mqtt-bridge
```

Review the configuration check for the expected enabled sources and command-gate
settings. It does not test broker or device reachability. Check those after startup.
The image supplies the heartbeat healthcheck; this extension only adjusts timing.

The stack's `.env` is not passed wholesale into either bridge. SMA receives
`smab.env`; BMW receives only the explicitly mapped settings. Do not put unrelated
service credentials into `smab.env`.

## 4. Authenticate and start BMW

Obtain `BMB_BMW_CLIENT_ID` and `BMB_BMW_GCID` through the upstream
[BMW setup guide](https://github.com/alaub81/bmw-mqtt-bridge/blob/main/docs/configuration.md#get-your-bmw-ids).
A BMW account with the necessary CarData streaming access is required. Replace
both placeholders, configure the local broker, then add `bmw` to
`COMPOSE_PROFILES`.

For the first start, authenticate interactively before starting the service:

```bash
docker compose config --quiet
docker compose pull bmw-mqtt-bridge
docker compose run --rm --no-deps -it bmw-mqtt-bridge ./bmw_flow.sh
docker compose up -d bmw-mqtt-bridge
docker compose ps bmw-mqtt-bridge
docker compose logs --tail=100 bmw-mqtt-bridge
```

Follow the displayed BMW device-login instructions. Tokens are stored in the
named `data_bmb_token` volume, not in `.env` or this repository. Subsequent starts
reuse them while valid. For reauthentication, stop the bridge first and repeat
the helper. Do not run a second bridge against the same account/token volume.
Existing standalone token volumes are not migrated automatically.

The healthcheck command is taken from the bridge's detailed Compose example. It
checks process liveness and prolonged local/BMW MQTT outages every 120 seconds,
with a 5-second probe timeout. Both application networks and these timings are
defined in Advanced and inherited by any local instances using `extends`.
Values and update rates depend on BMW and the subscribed data; this setup does
not add vehicle commands.

## 5. Connect openHAB and maintain the services

Install/configure openHAB's MQTT binding against the same broker. SMA publishes
Homie discovery. For BMW, set `BMB_MQTT_HOMIE=1` in `.env` before starting or
recreating its container; its default and the example value are `0` (disabled).
Then create the discovered Things and link their channels to your Items as
described upstream. Docker does not create Items or widgets.

- [SMA openHAB setup and widgets](https://github.com/alaub81/sma-mqtt-bridge/tree/main/openHAB)
- [BMW openHAB setup and widgets](https://github.com/alaub81/bmw-mqtt-bridge/tree/main/openHAB)

Widget sources and manual imports remain in those repositories. This extension
does not create a second copy of them.

To update, select the desired published image tag in `.env`, pull and recreate
only that bridge. Preserve its named volume and the Compose project identity:

```bash
docker compose pull sma-mqtt-bridge
docker compose up -d sma-mqtt-bridge
```

Use the equivalent commands for `bmw-mqtt-bridge`. Back up `.env`, `smab.env`,
the optional SMA configuration directory, the chosen Compose files,
`data_smab_state` (SMA topic/state ownership) and `data_bmb_token`
(BMW credentials/cache). Actual Docker volume names include the project prefix.
Do not use `down -v` to update. Images supply their non-root users; the extension
keeps read-only root filesystems and bounded local Docker logs.

To disable a bridge, stop its running service **before** removing the profile
from `.env`:

```bash
docker compose stop sma-mqtt-bridge
```

Use the BMW service name for BMW. Removing a profile does not stop an existing
container. Keep the volumes for later use. Explicitly targeting a service or
using `--profile '*'` can start it even when it is absent from `COMPOSE_PROFILES`;
see [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/).

## Repository checks and verification limits

Run the existing basic linter, then the separate advanced configuration check:

```bash
./tests/linter-check.sh
.lint-venv/bin/python tests/compose.advanced.py
```

The second command reuses the linter's pinned PyYAML environment. It validates the
combined templates through Docker Compose for all 32 profile combinations,
checks default-off behavior, required BMW ID declarations, external-broker selections and isolation of bridge
environment settings. It uses temporary example ENV files and does not read your
local `.env` or `smab.env`, contact the Docker daemon or start containers.
Synthetic SMA ENV fixtures verify that runtime settings come from the separate
file and are not shadowed by similarly named stack variables. The existing CI runs
the basic linter; this additional profile check is a separate manual command.

These are configuration checks, not a live acceptance test. Image availability,
BMW OAuth, real device access, LAN multicast, MQTT discovery, TLS trust and actual
openHAB widget use require a later test on the intended host. No authentication,
device commands or deployment are performed by these checks.

# Digitalstrom binding maintenance

[`digitalstrom_binding_tools.sh`](digitalstrom_binding_tools.sh) is a standalone
Bash script. It requires curl 7.55+ and jq 1.6+. Copy this single script and edit
the configuration block near the top before running it. No shared helper or
extra configuration file is required.

Set `OPENHAB_URL`, `OPENHAB_TOKEN`, `BRIDGE_UID`, `MONITORED_THINGS` and
`REFRESH_ITEMS` to match your installation. Optional `OPENHAB_TOKEN_FILE` and
`API_CA_FILE` settings include example paths in comments; leave them empty to
use the inline token and system CA trust. Token files take precedence. The
placeholder token is refused before any API request. Keep real tokens local.

## Digitalstrom actions

The examples keep the original setup's shape: a digitalSTROM bridge, a shutter
Thing (`GR`), a circuit Thing and shutter/lighting groups. Bridge/device IDs are
synthetic; the API token is an explicit placeholder. Optional token-file and
private-CA settings have commented example paths. Replace the examples locally.

```bash
bash scripts/digitalstrom_binding_tools.sh status
bash scripts/digitalstrom_binding_tools.sh fullstatus
bash scripts/digitalstrom_binding_tools.sh restart
bash scripts/digitalstrom_binding_tools.sh autorestart
bash scripts/digitalstrom_binding_tools.sh refresh
```

`status` and `fullstatus` only read. `restart` acts immediately, `autorestart`
restarts only if a monitored Thing is unhealthy, and `refresh` immediately sends
`REFRESH` to the configured groups. No execution-mode flag is needed.
A binding restart re-enables after three seconds. On failure/interruption the
script attempts re-enabling again; check MainUI if it reports failure. Accepted
requests do not establish that hardware is online. Ping, log inspection and
refresh after restart are explicit operator steps.

# Development tools

These tools run locally to prepare and verify changes. openHAB does not need them
at runtime. Current widget and Blockly library sources are maintained under
`data/openhab/conf/yaml/`, together with their documentation. Start with the
[widget catalog](../data/openhab/conf/yaml/widgets/README.md) or
[library catalog](../data/openhab/conf/yaml/block_libraries/README.md).

| Directory | Contents |
| --- | --- |
| `battery-widget/` | Battery widget regression test |
| `humidity-widget/` | Humidity widget regression test |
| `window-widget/` | Widget generator and regression test |
| `state-alarms/` | State/temperature-window JavaScript sources, library generator, and simulated alarm checks |
| `humidity-alarms/` | JavaScript source and simulated test for the original humidity monitor |
| `heatpump-daily/` | Blockly generator and simulated test for daily heat-pump consumption |
| `migrate_shelly_links.py` | Existing Shelly link migration tool |

The `window-widget/build.py` and `state-alarms/build.py` generators update widget
and library YAML files. Run them manually; they do not run at startup.
The humidity source is not automatically synchronized with the current YAML
library; compare them before making changes.

Run `./tests/test-check.sh` for the shared offline behavior checks. The runner
exports public YAML to temporary JSON and invokes Node on Linux or macOS;
Ruby and `osascript` are not required. Battery/humidity CLIs retain compatibility
with their older per-widget commands. Current window, Shelly, state/temperature,
humidity and DWD checks use synthetic data; see the
[test guide](../tests/README.md#offline-behavior-tests) for coverage and limits.
The heat-pump verifier and installed-rule wiring checks still need JavaScript
produced by openHAB's Blockly generator. Private historical data and performance
comparisons remain explicit local options.

## Shelly link migration

`migrate_shelly_links.py` is an existing Python tool, independent of the Bash
maintenance scripts. Install `requests` in your own virtual environment.
Set `OPENHAB_URL`, `OPENHAB_LOG` and `OPENHAB_TOKEN_FILE` (or `OPENHAB_TOKEN`).
There are no built-in server addresses or credentials.

```bash
export OPENHAB_URL=https://openhab.example.invalid:8443
export OPENHAB_LOG=/path/to/openhab.log
export OPENHAB_TOKEN_FILE=/path/to/local-token
python3 tools/migrate_shelly_links.py
# After reviewing the preview; choose a new backup filename:
python3 tools/migrate_shelly_links.py --execute --backup-file backups/shelly-links.json
```

Create the `backups/` directory first. Execution saves all original links to an
owner-only file, refuses changed links or existing backup files, and stops at the
first failed request. New links are created before old links are removed; existing
target links are skipped. An interrupted run can leave both links present, and
completed migrations are not rolled back automatically. Check the backup before
retrying. Type/dimension checks and known-risk exclusions remain enabled; a
preview is not proof that a device's new channel works. Requests have timeouts,
verify TLS and refuse redirects. `REQUESTS_CA_BUNDLE` selects a local CA.

## Local originals

Original private configurations and historical experiments remain in the ignored
local `archive/` directory. They are not required to build or use public YAML.
Git does not back up this directory. Administrative Bash scripts are kept under
[`scripts/`](../scripts/).

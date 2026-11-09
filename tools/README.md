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
| `state-alarms/` | JavaScript source, library generator, and simulated alarm test |
| `humidity-alarms/` | JavaScript source and simulated test for the original humidity monitor |
| `heatpump-daily/` | Blockly generator and simulated test for daily heat-pump consumption |
| `migrate_shelly_links.py` | Existing Shelly link migration tool |

The `window-widget/build.py` and `state-alarms/build.py` generators update widget
and library YAML files. Run them manually; they do not run at startup.
The humidity source is not automatically synchronized with the current YAML
library; compare them before making changes.

The battery and humidity widget tests run on macOS using `osascript`. Their widget
documentation contains the commands and YAML-to-JSON conversion instructions.
The other JavaScript tests expose functions that take a Node VM and the required
source data; they are not standalone CLI programs.

## Local archive dated 2026-11-08

The following were moved to `archive/scripts-cleanup-20261108/` without deletion:

- `heating-library/`, `battery-alarms/`: one-time migration/activation scripts.
- `window-alarms/`, `bedroom-window-alarms/`: rule exports and migration helpers.
- `state-alarms/`: exported example, window, and bathroom rules.
- `humidity-alarms/`: old REST generator, exports, status, and UID migration.
- `heatpump-daily/`: activation script, prepared rule, and original checksum.
- `window-widget/contact-metadata.json`: historical contact/alarm assignment snapshot;
  current assignments live in the Contact Items' `contactOverview` metadata.

Repository paths in the archived scripts were adjusted for their new location.
Running these historical scripts can change the live configuration. They were
not executed during cleanup, and their prepared state has not been compared
with the current server.

`archive/` remains excluded by `.gitignore`, so Git does not back it up. `tools/`
is versioned. Administrative shell
scripts remain unchanged under `scripts/`.

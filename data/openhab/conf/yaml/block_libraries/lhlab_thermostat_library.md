# lhlab: thermostat control

[lhlab_thermostat_library.yml](lhlab_thermostat_library.yml) adds an **OFF** option to the log-level selection in all three heating blocks:

- Thermostat Control (HEAT / COOL)
- Thermostat Control
- Shelly Walldisplay Thermostat Control

Internal UID: `lhlab_thermostat_library`. The unchanged **Thing controller** is in the separate [Thing library](lhlab_thing_library.md).

## Enable OFF

1. Reload MainUI to load the updated library definition.
2. Open the desired heating rule in Blockly.
3. Select **OFF** under **set loglevel**.
4. Save the rule to regenerate JavaScript.

Existing rules retain their settings. Library updates do not automatically replace saved rule code. Server-side log-level guards also take effect only after each rule is resaved.

## Log-level behavior

| Selection | Behavior |
| --- | --- |
| `info`, `warn`, `error`, `debug` | Diagnostics use that level as before. Log expressions are evaluated only when the logger enables the level. |
| `OFF` | Skips every log call owned by the block, including direct warnings about invalid times. |

Guards precede log calls, skipping additional Item reads, string construction, and Quantity calculations used only in log arguments. For example, diagnostic HEAT/COOL boundaries are no longer constructed when logging is disabled.

After regeneration, a server WARN level also suppresses evaluation of info/debug arguments. OFF disables the block's own messages independently of server level. Other rules and openHAB scripting-framework logs are unaffected.

Switching thresholds, setpoint calculations, presence, booster, Smart Grid, window handling, and timers are unchanged. Window control continues with logging OFF.

## Installation and splitting the previous library

The file uses `version: 1` with block key `lhlab_thermostat_library`. All three thermostat definitions, OFF option, function code, and current toolbox defaults were copied from the active library.

Copy both YAML files to the server. Container paths:

```text
/openhab/conf/yaml/block_libraries/lhlab_thermostat_library.yml
/openhab/conf/yaml/block_libraries/lhlab_thing_library.yml
```

Markdown files are documentation and need not be deployed. Old/new libraries can coexist during migration because their UIDs differ.

1. Copy both YAML files and reload MainUI.
2. Verify **lhlab – Thermostatsteuerung** and **lhlab – Thing-Steuerung** appear file-managed/read-only.
3. Optionally check from the local repository first:

```sh
   python3 archive/scripts-cleanup-20261108/heating-library/migrate.py --check
   ```

4. Migrate existing rule references:

```sh
   python3 archive/scripts-cleanup-20261108/heating-library/migrate.py
   ```

5. Only after successful verification, delete the old editable **Blocklibraries lhlab.wiki**, UID `Blocklibraries_lhlab.wiki`, in Developer Tools.

The script uses local `openhab_api_key` and `http://openhab.laub.loc:8080`, overridable with `--url`/`--token-file`. It checks both new libraries and matching block definitions, backs up affected rules, replaces only Blockly type references, then verifies saved contents and enabled status. On failure it attempts restoration; failed restores are logged in the backup directory.

No rules are created/deleted, and generated JavaScript, setpoints, triggers, and log levels are unchanged by this migration. Disabled rules are migrated and remain disabled. Repeating a successful migration does nothing. The old library is not deleted automatically.

**Migration timing:** Saving reloads rule scripts and can reset private caches and active window/delay timers. Migrate when those timers are not needed. The script does not automatically change heating states to bypass this consideration.

At preparation, 41 block references in 22 rules were affected, including five disabled rules. Backups are in `archive/heating-library-split-20261030/`. The previous MainUI export `lhlab_block_libraries.yml` was replaced by two valid file libraries.

For later function changes, reload MainUI and resave affected Blockly rules after updating YAML. For this split alone, the generated rule code was already identical and is preserved by the migration.

## Validation

- All 92 log calls in the three heating blocks are guarded.
- JavaScript syntax-tree comparison confirmed unchanged nonlogging statements.
- 194 checks compare commands, setpoint updates, MQTT actions, and logs, including HEAT/COOL, manual control, booster, Smart Grid, window timers, and invalid night times.
- OFF produces no block-owned logs; enabled info/debug/warn/error output remains.
- In a representative HEAT test, Quantity calls fall from six to three because diagnostic-only constructions disappear. This is a behavior test, not a measurement of total CPU savings.
- The saved original library was read before splitting. All block definitions, level choices, full functions, and toolbox defaults were transferred unchanged.
- Both file libraries are loaded on the server. On 2026-10-30, 41 references in 22 rules were migrated and all 19 thermostat blocks set to OFF. Fifteen thermostat rules remain active and four disabled. Other rule/heating instructions remain unchanged; existing scripts received targeted logging guards without regenerating divergent older rule flows.
- The old UI library was removed. Reread rules showed no old references, all thermostat levels OFF, and unchanged enabled states. Backups and verification are in `archive/thermostats-off-20261030/`.
- REST comparison normalizes empty module input maps and rule-tag ordering. Changed tags, nonempty input connections, and rule-code changes remain detectable.

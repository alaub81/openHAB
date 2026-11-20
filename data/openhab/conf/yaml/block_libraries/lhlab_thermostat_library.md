# lhlab: thermostat control

## Block presets

The two standard thermostat blocks retain text presets of `19:00` for night
start and `08:15` for night stop. They also accept Item selection blocks referring
to DateTime Items. The Shelly block already uses Item selection blocks for both
night-time inputs. Literal times supplied by text blocks remain supported there.

The Shelly block retains example MQTT broker, RPC-topic, and source values;
adapt them to your installation. The broker uses a Thing selection block, and
the MQTT topics use text blocks. General numeric control defaults such as
hysteresis, offsets, and window delays are unchanged. Updating the library does
not overwrite inputs already saved in existing rules.

## Optional window contacts

All three thermostat blocks use `undefined` as the default for the optional
window-contact input. This means no window contact is configured and no window
interlock is applied. The helpers already handle this value without looking up
an Item. Connect an Item selection block to enable monitoring of a contact or
contact group; existing connected inputs remain unchanged.

Updating the library does not replace the `MyItem` shadow in saved rules. For an
unset window-contact input, replace that shadow with the `undefined` block and
save the rule to regenerate its JavaScript. Keep any actual contact selection.

## Configurable Shelly schedule profiles

The **Shelly Walldisplay Thermostat Control** block provides five number fields:

| Field | Meaning | Previous setup mapping, for migration reference only |
| --- | --- | ---: |
| `PROFILE_WINDOW` | Open-window profile | 0 |
| `PROFILE_ABSENCE` | Absence profile | 1 |
| `PROFILE_BOOSTER` | Booster profile | 2 |
| `PROFILE_SGGREEN` | Smart Grid green profile | 3 |
| `PROFILE_NIGHT` | Night setback profile | 4 |

Every field initially shows `-1` (not configured). Enter the nonnegative integer
profile ID actually configured on your device. Zero is valid. Multiple modes
may intentionally share an ID. Invalid, missing, or fractional IDs abort the
execution before MQTT calls, delays, or Item commands. Empty MQTT broker/topic/
source settings also abort before any external action. No fallback to the old
profile numbers is applied.

Normal operation continues to disable the device schedule and use the normal
setpoint; it does not require a sixth profile. Priority remains booster, open
window, absence/Smart Grid, night, then normal operation. Setpoint calculations
and MQTT request contents are otherwise unchanged. Different devices can use
different profile mappings in their respective rules. Schedule rule IDs inside
Thing configuration are separate from these profile IDs.

### Configuring existing rules before later activation

Updating the library file does not rewrite JavaScript already saved in a rule.
Before using an existing Shelly Blockly rule with this version, reload MainUI,
open the rule, set the five profile fields and MQTT inputs, then regenerate/save
while keeping the rule disabled.
Check the device's actual profile IDs before enabling the rule. Old block XML
without the new fields must be completed; regenerated code does not silently
retain the previous mapping. Do not use the historical library-split migration
script for this behavior update.

The library definition was installed on 2026-11-20 and verified to match the
repository file byte for byte. The four existing Shelly Walldisplay rules remain
disabled and were not regenerated. Profile-selection behavior was verified
locally with simulated Items, MQTT actions, and time; it has not been executed
against a live thermostat.

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
2. Verify both libraries appear file-managed/read-only.
3. Create rules and explicitly select your Items, Thing UIDs and MQTT settings.
4. If migrating from a UI library, back up affected rules and replace the old
   blocks while preserving inputs, triggers, actions and enabled state. Verify
   each rule before removing the old UI library.

Saving reloads rule scripts and may reset private caches and active delay timers.
For future function changes, update YAML and resave affected Blockly rules.

## Validation

- All 92 log calls in the three heating blocks are guarded.
- JavaScript syntax-tree comparison confirmed unchanged nonlogging statements.
- 194 checks compare commands, setpoint updates, MQTT actions, and logs, including HEAT/COOL, manual control, booster, Smart Grid, window timers, and invalid night times.
- OFF produces no block-owned logs; enabled info/debug/warn/error output remains.
- In a representative HEAT test, Quantity calls fall from six to three because diagnostic-only constructions disappear. This is a behavior test, not a measurement of total CPU savings.
- The saved original library was read before splitting. All block definitions, level choices, full functions, and toolbox defaults were transferred unchanged.

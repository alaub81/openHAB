# lhlab: humidity alarms

## Explicit sensor and alarm groups

The sensor-group and alarm-group inputs start empty. Select your own groups;
the library no longer preselects `Humidity_Innen_ALL` or `Humidity_Alarm`.
Thresholds and timing defaults remain, as do semantic room matching and the
optional override/external-alarm lists. The library does not create groups or rules.

New monitor blocks use the openHAB Item picker for both groups. Select actual
Group Items; the picker itself is not restricted to groups. The sensor threshold
block also uses the Item picker for its sensor. For externally evaluated alarms,
connect a normal Blockly list containing Item selection blocks. Overrides remain
a list of sensor threshold blocks, and both lists are optional.

Reload MainUI after installing the YAML to get the new presets when adding
blocks. Existing saved inputs are preserved; text Item names remain supported
and can be replaced manually with Item selection blocks.

[lhlab_humity_alarm_library.yml](lhlab_humity_alarm_library.yml) supplies group-based Blockly room alarms. This YAML is the canonical repository definition and contains the blocks and complete evaluation code; no extra JavaScript file is copied to the server.

File name and internal UID are **`lhlab_humity_alarm_library`**. The old library created in Developer Tools uses `lhlab_humidity_library`. Rules using that old UID need their block references updated when migrating.

## Installation and migration from the UI library

Container destination:

```text
/openhab/conf/yaml/block_libraries/lhlab_humity_alarm_library.yml
```

On the Docker host, use the corresponding mounted configuration directory. Markdown is documentation only and is not required by openHAB.

1. Copy the YAML file and reload MainUI.
2. Verify UID `lhlab_humity_alarm_library` is file-managed/read-only.
3. Create a Blockly rule, select your sensor/alarm groups, and add group-member
   state-change triggers for both groups.
4. Configure notification actions. The optional current-alarm message value is
   supplied by [lhlab_alarm_library.yml](lhlab_alarm_library.yml).

For an existing UI library, back up the affected rules first and replace their
old monitor/threshold blocks with this library's blocks, preserving inputs and
actions. Verify the saved rules before removing the old library. Resaving resets
private script caches. JavaScript Scripting must be installed.

## Blocks

### Humidity monitor

| Setting | Example configuration (adapt to your Items) |
| --- | --- |
| Sensor group | Select your own group |
| Alarm group | Select your own group |
| Threshold | 75%; alarm at or above threshold |
| Overrides | `MyBathroomHumidity`: 80% |
| Externally evaluated alarms | `MyExternalHumidityAlarm` |
| Minimum repeat interval | 12 hours |
| Batching delay | 2 seconds |

The alarm/clearance action areas choose notification behavior, using normal push blocks and the alarm library's current-alarm message value. The library selects no recipients or channels.

### Sensor threshold override

This value block describes a sensor Item and percentage threshold. Put it in a normal Blockly list at the overrides input. An empty list uses the common threshold everywhere. Duplicate overrides for one sensor are rejected.

## Groups and semantic rooms

Configure two group-member-state-change triggers, for example:

- `Humidity_Innen_ALL`: a sensor reading changes.
- `Humidity_Alarm`: a room alarm changes, including the externally supplied utility-room alarm.

Repeated updates with unchanged values do not trigger the rule. A virtual room alarm changing intentionally causes another execution for notification; unchanged alarm states receive no new command.

Sensors and alarms are paired by semantic room, using direct `hasLocation` or `isPointOf` via equipment. Each room requires exactly one sensor and alarm Item. Ambiguity is rejected. Unmapped sensors are skipped with at most one warning log per hour.

New rooms need a sensor in the sensor group and an alarm Item in the alarm group, both correctly located. No Items are created automatically.

For an externally evaluated room alarm, its existing rule or MQTT source remains responsible for evaluation. The rule does not overwrite that alarm but handles its warnings, reminders, and clearance. The block's percentage threshold does not apply to this external alarm.

## Behavior and resources

- Sensor events evaluate only the corresponding room. Assignments are cached for up to five minutes and rebuilt as needed.
- Evaluation uses percentage units. `NULL`, `UNDEF`, conversion failures, and values outside 0–100% leave the existing alarm unchanged.
- A short timer batches nearby warnings/clearances. Later events do not postpone an active timer.
- Twelve-hour cooldowns use timestamps, not long-running timers. Reminders require a subsequent suitable event after the interval; they are not sent autonomously.
- Clearance includes previously reported rooms even after the cooldown has elapsed.
- Normal evaluation uses no database queries, HTTP calls, or per-reading info logs.

Assignments and notification timestamps live in the rule's nonpersistent private cache. Restart or script reload may report existing alarms again. Failed notification actions retry on the next suitable event without confirming external delivery.

## Changes and validation

Edit the YAML, copy it to the server, reload MainUI, and resave affected Blockly rules to regenerate embedded code. Updating a library does not automatically replace code already saved in a rule.

Local simulations cover humidity evaluation, threshold overrides, room matching,
cooldowns, batching and recovery. They do not prove notification delivery or the
configuration of a live installation. The older source in `tools/humidity-alarms/`
is not automatically synchronized with the canonical YAML library.

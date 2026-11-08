# lhlab: humidity alarms

[lhlab_humity_alarm_library.yml](lhlab_humity_alarm_library.yml) supplies group-based Blockly room alarms. This YAML is the canonical repository definition and contains the blocks and complete evaluation code; no extra JavaScript file is copied to the server.

File name and internal UID are **`lhlab_humity_alarm_library`**. The old library created in Developer Tools uses `lhlab_humidity_library`. The existing rule therefore needs a one-time block-reference migration.

## Installation and migration from the UI library

Container destination:

```text
/openhab/conf/yaml/block_libraries/lhlab_humity_alarm_library.yml
```

On the Docker host, use the corresponding mounted configuration directory. Markdown is documentation only and is not required by openHAB.

1. Copy the YAML file. Old/new libraries can coexist during migration because their UIDs differ.
2. Reload MainUI and verify UID `lhlab_humity_alarm_library` is file-managed/read-only. Both libraries have the same display name; check UID and read-only status.
3. Run the one-time migration from the local repository working directory.
4. Open rule **Luftfeuchtigkeit – Raumalarme und Benachrichtigungen** (`e53dfb734c`) in Blockly and verify all blocks appear.
5. Only then delete the old editable `lhlab_humidity_library` in Developer Tools → Blockly libraries. Keep the rule itself.

```sh
python3 archive/scripts-cleanup-20261108/humidity-alarms/migrate-library-uid.py
```

The script uses local `openhab_api_key`, `http://openhab.laub.loc:8080`, `curl`, and Python 3. It checks the new file-managed library and backs up the current rule locally. It replaces only Blockly references `lhlab_humidity_library_monitor` and `lhlab_humidity_library_threshold` with prefix `lhlab_humity_alarm_library_`. Triggers, thresholds, notification actions, and generated JavaScript stay unchanged. The old library is not deleted automatically. Resaving may reset the private script cache.

Override connection settings with `--url` and `--token-file`. A second successful migration run makes no changes.

openHAB loads YAML automatically. The saved rule already includes generated JavaScript, so no new rule or recreated triggers are needed. The previous configuration is backed up in `archive/humidity-alarms-20261030/before.json`.

[lhlab_alarm_library.yml](lhlab_alarm_library.yml) is also needed: both notification areas use its current-alarm message block. JavaScript Scripting must be installed.

## Blocks

### Humidity monitor

| Setting | Current configuration |
| --- | --- |
| Sensor group | `Humidity_Innen_ALL` |
| Alarm group | `Humidity_Alarm` |
| Threshold | 75%; alarm at or above threshold |
| Overrides | `Badezimmer_Klima_Luftfeuchtigkeit`: 80% |
| Externally evaluated alarms | `LaubRaspi5_BME280_Humidity_Alarm` |
| Minimum repeat interval | 12 hours |
| Batching delay | 2 seconds |

The alarm/clearance action areas choose notification behavior, using normal push blocks and the alarm library's current-alarm message value. The library selects no recipients or channels.

The installed rule retains its push recipients, `oh:humidity` icon, and `Luftfeuchtigkeit` tag. Alexa actions are disabled.

### Sensor threshold override

This value block describes a sensor Item and percentage threshold. Put it in a normal Blockly list at the overrides input. An empty list uses the common threshold everywhere. Duplicate overrides for one sensor are rejected.

## Groups and semantic rooms

The rule has two group-member-state-change triggers:

- `Humidity_Innen_ALL`: a sensor reading changes.
- `Humidity_Alarm`: a room alarm changes, including the externally supplied utility-room alarm.

Repeated updates with unchanged values do not trigger the rule. A virtual room alarm changing intentionally causes another execution for notification; unchanged alarm states receive no new command.

Sensors and alarms are paired by semantic room, using direct `hasLocation` or `isPointOf` via equipment. Each room requires exactly one sensor and alarm Item. Ambiguity is rejected. Unmapped sensors are skipped with at most one warning log per hour.

New rooms need a sensor in the sensor group and an alarm Item in the alarm group, both correctly located. No Items are created automatically. `GF_Humidity_Alarm` is not needed.

For the utility room, MQTT remains responsible for evaluation. The rule does not overwrite that alarm but handles its warnings, reminders, and clearance. The block's percentage threshold does not apply to this external alarm.

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

Files under `archive/scripts-cleanup-20261108/humidity-alarms/` belong to the original REST deployment. They are not automatically synchronized with this YAML and are not a second installation step.

File conversion was checked against the complete previous JSON library. The requested UID changed; both block definitions and function code remained identical. Reference migration was checked locally for completeness and repeatability. The underlying version passed 42 behavior tests, official openHAB Blockly generation, and rule saving/reopening. Native checks mapped 17 internally evaluated sensors and one external sensor completely.

The file migration was verified on openHAB on 2026-10-30: `lhlab_humity_alarm_library` is file-managed and matches the repository, including function code. The old UI library was removed. The existing rule uses both new block types and matching generated code. Both group triggers, 75/80% thresholds, 12-hour cooldown, two-second batching, and existing recipients are retained. `GF_Humidity_Alarm`, the former notification rule, and temporary test objects are gone.

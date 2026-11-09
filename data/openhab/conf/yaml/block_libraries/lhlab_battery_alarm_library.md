# lhlab: battery alarms

## Select the battery group as an Item

New monitor blocks use the standard openHAB Item selection block for the battery
group. Select your existing Group Item from the Item picker instead of typing its
name into a text block. The selection starts empty; choose your battery group.
The picker is
not restricted to Group Items, so select an actual group containing batteries.
The library does not create this group or its members.

Existing rules with a text block remain supported: the group input still accepts
both text and the openHAB Item block. Generated monitoring code and alarm behavior
are unchanged. For a later deployment, reload MainUI after updating the library.
Newly placed blocks receive the Item selector; existing text inputs are not
replaced automatically. You can manually replace their text block with an Item
selection block and select the same group.

The rule-specific deployment record below describes the previous installation;
its archived activation script is not a setup step for a different installation.

[lhlab_battery_alarm_library.yml](lhlab_battery_alarm_library.yml) contains the **Batterien überwachen** Blockly block and its complete JavaScript implementation. Internal UID: `lhlab_battery_alarm_library`.

## Installation

Copy the YAML file into the mounted openHAB configuration directory. Container path:

```text
/openhab/conf/yaml/block_libraries/lhlab_battery_alarm_library.yml
```

Reload MainUI. The library appears file-managed and read-only. No additional JavaScript file is needed on the server. Loading it creates no rule and does not change existing battery alarms.

The prepared replacement for rule `ab43d2daf7` is in local archive `archive/battery-alarms-20261030/rule.json`. After installation, the historical replacement can be activated from this working directory:

```sh
python3 archive/scripts-cleanup-20261108/battery-alarms/activate.py
```

The one-time helper uses repository file `openhab_api_key` and `http://openhab.laub.loc:8080`. It first checks the file-managed library and function code, refuses to overwrite an independently modified battery rule, and backs up the current rule before saving. Override connection settings with `--url` and `--token-file`. Local archive templates are not part of YAML installation or a fresh Git checkout.

The existing [lhlab_alarm_library.yml](lhlab_alarm_library.yml) is also required: the prepared rule uses its current-alarm message block for push text.

## Configuration

| Setting | Prepared value |
| --- | --- |
| Battery group | Empty; select your battery Group Item |
| Warning threshold | At most 15% |
| Minimum repeat interval | 12 hours |
| Notification batching | 2 seconds |
| Confirm low reading after | 5 minutes; configurable, 0 disables waiting |
| Low-battery action | Existing push recipient; text from current-alarm message block |
| Recovery action | Empty; no recovery notifications |

The existing trigger remains a member of `Battery_ALL` changing state. No cron trigger is required. Group membership includes new batteries.

The library sends no push itself. Blockly action areas choose recipients/channels; the recovery area can be populated later. Messages contain affected Item labels and, for warnings, percentages. Concurrent events are combined into one message.

## Behavior

- A first low reading is marked pending. After the confirmation delay, the current value is reread; a warning is generated only if still at or below threshold. No further sensor update is required. More low readings do not extend the deadline. Recovery cancels the pending confirmation; a later low reading starts a new delay. Unknown values prevent sending.
- First execution reads the group once. Subsequent group events read only the changed battery. A manual run without a triggering Item checks the full group.
- Percentage Quantities and plain Number Items from 0 to 100 are supported. This installation has 55 `Number:Dimensionless` and two plain Number Items.
- `NULL`, `UNDEF`, conversion failures, and out-of-range values create neither alarms nor false recovery messages. Previously known low readings remain pending, but sending is suspended while unknown.
- Every valid group event also checks whether known low batteries have passed the 12-hour cooldown, without rereading all 57 healthy batteries. An unchanged low battery can therefore be reported again after another battery's event.
- Due candidates are reread before sending. Removed group members are excluded. A battery recovering during batching produces no transient warning.
- Brief recovery does not reset the 12-hour cooldown, preventing repeated warnings around the threshold.

There are no 12-hour timers per battery. One shared timer waits for the next confirmation or batch. Batteries becoming low at different times retain separate confirmation deadlines. Batching defines the minimum wait before sending; five-minute confirmation does not add another two seconds. Evaluation makes no database/HTTP calls and generates no per-reading info logs.

## State and changes

Group state and cooldowns live in the rule's private script cache. Restart/reload rebuilds them, so still-low batteries may be reported again. Repeated reminders require a new group event. Failed notification actions retry on the next suitable event; this does not confirm external delivery.

Edit the YAML for future changes, copy it to the server, reload MainUI, and resave the affected Blockly rule to regenerate embedded JavaScript.

## Validation and deployment status

The 2026-11-03 extension adds configurable confirmation delay. Local simulated-clock checks covered five-minute waiting, rereading without a sensor event, early recovery, a new deadline after recovery, repeated lows without extension, unknown readings, and zero delay. This extension is not yet active on the server. The following results concern the earlier version. Install the new YAML and resave the existing Blockly rule, checking the new confirmation setting. The historical activation script uses the old archive template and is unsuitable for this update.

The earlier version passed 33 behavior tests covering exact thresholds, 0%, plain Numbers, invalids, cooldowns, brief recovery, removed members, and combined notifications. Generation and saving/reopening were checked with Blockly 11.2.2 and the official openHAB generator.

Native openHAB checks confirmed 57 valid readings, 57 checks during initialization, and exactly one check on a single battery change. No notifications were sent; temporary test objects were removed.

The YAML library was installed and the replacement rule activated on 2026-10-30. REST checks confirmed `IDLE`/`NONE`, with library code and saved rule matching. Re-running the activation script recognizes this state without resaving.

openHAB adds empty `inputs: {}` to saved rule modules. The activation script treats this as an omitted field while still detecting nonempty input connections and script changes as real differences.

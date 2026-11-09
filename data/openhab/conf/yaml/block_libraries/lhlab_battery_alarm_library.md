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

[lhlab_battery_alarm_library.yml](lhlab_battery_alarm_library.yml) contains the **Batterien überwachen** Blockly block and its complete JavaScript implementation. Internal UID: `lhlab_battery_alarm_library`.

## Installation

Copy the YAML file into the mounted openHAB configuration directory. Container path:

```text
/openhab/conf/yaml/block_libraries/lhlab_battery_alarm_library.yml
```

Reload MainUI. The library appears file-managed and read-only. No additional JavaScript file is needed on the server. Loading it creates no rule and does not change existing battery alarms.

Create a Blockly rule, select your battery group, and configure notification
actions. The [alarm library](lhlab_alarm_library.yml) provides the optional
current-alarm message value for those actions.

## Configuration

| Setting | Prepared value |
| --- | --- |
| Battery group | Empty; select your battery Group Item |
| Warning threshold | At most 15% |
| Minimum repeat interval | 12 hours |
| Notification batching | 2 seconds |
| Confirm low reading after | 5 minutes; configurable, 0 disables waiting |
| Low-battery action | Caller-selected actions; optional current-alarm message block |
| Recovery action | Empty; no recovery notifications |

Add a member-state-change trigger for the selected battery group. No cron trigger is required. Group membership includes new batteries.

The library sends no push itself. Blockly action areas choose recipients/channels; the recovery area can be populated later. Messages contain affected Item labels and, for warnings, percentages. Concurrent events are combined into one message.

## Behavior

- A first low reading is marked pending. After the confirmation delay, the current value is reread; a warning is generated only if still at or below threshold. No further sensor update is required. More low readings do not extend the deadline. Recovery cancels the pending confirmation; a later low reading starts a new delay. Unknown values prevent sending.
- First execution reads the group once. Subsequent group events read only the changed battery. A manual run without a triggering Item checks the full group.
- Percentage Quantities and plain Number Items from 0 to 100 are supported.
- `NULL`, `UNDEF`, conversion failures, and out-of-range values create neither alarms nor false recovery messages. Previously known low readings remain pending, but sending is suspended while unknown.
- Every valid group event also checks whether known low batteries have passed the 12-hour cooldown, without rereading all healthy batteries. An unchanged low battery can therefore be reported again after another battery's event.
- Due candidates are reread before sending. Removed group members are excluded. A battery recovering during batching produces no transient warning.
- Brief recovery does not reset the 12-hour cooldown, preventing repeated warnings around the threshold.

There are no 12-hour timers per battery. One shared timer waits for the next confirmation or batch. Batteries becoming low at different times retain separate confirmation deadlines. Batching defines the minimum wait before sending; five-minute confirmation does not add another two seconds. Evaluation makes no database/HTTP calls and generates no per-reading info logs.

## State and changes

Group state and cooldowns live in the rule's private script cache. Restart/reload rebuilds them, so still-low batteries may be reported again. Repeated reminders require a new group event. Failed notification actions retry on the next suitable event; this does not confirm external delivery.

Edit the YAML for future changes, copy it to the server, reload MainUI, and resave the affected Blockly rule to regenerate embedded JavaScript.

## Validation

Local simulated-clock checks cover confirmation delays, recovery, cooldowns,
invalid readings, batching and group membership. These checks do not establish
notification delivery or the state of any live installation. Resave affected
Blockly rules after updating the library to regenerate their embedded code.

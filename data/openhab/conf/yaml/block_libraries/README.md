# Blockly libraries

These five libraries add reusable blocks to openHAB's Blockly editor. Each YAML
contains the file-provider wrapper, block definitions, code templates and helper
functions. No extra JavaScript file or local generator is needed at runtime.
Detailed documentation stays beside each YAML file.

## Catalog

| Library/source | Blocks and purpose | Guide |
| --- | --- | --- |
| [lhlab_alarm_library.yml](lhlab_alarm_library.yml) | DWD warning monitoring, generic alarm groups, delayed Contact/Switch and temperature-dependent window monitoring, alarm records and current-alarm values | [Alarm management](lhlab_alarm_library.md) |
| [lhlab_battery_alarm_library.yml](lhlab_battery_alarm_library.yml) | Battery-group monitoring with confirmation, batching and reminder cooldowns | [Battery alarms](lhlab_battery_alarm_library.md) |
| [lhlab_humity_alarm_library.yml](lhlab_humity_alarm_library.yml) | Room-based humidity monitoring, per-sensor thresholds and external alarm integration | [Humidity alarms](lhlab_humity_alarm_library.md) |
| [lhlab_thermostat_library.yml](lhlab_thermostat_library.yml) | Heating, heating/cooling, and Shelly wall-display controllers | [Thermostat control and Shelly profiles](lhlab_thermostat_library.md) |
| [lhlab_thing_library.yml](lhlab_thing_library.yml) | Enable or disable a selected Thing | [Thing control](lhlab_thing_library.md) |

The spelling `lhlab_humity_alarm_library` is the existing library UID and filename;
preserve it in rule references.

## Install and create a rule

1. Install the **JavaScript Scripting** automation add-on in openHAB.
2. Copy the selected `.yml` files into `$OPENHAB_CONF/yaml/block_libraries/`.
   The repository's Docker setup already mounts them there. Keep `version: 1`
   and `blocks:` intact; the map key is the library UID.
3. Reload MainUI and open a Blockly script action in a new rule. The libraries
   appear under their configured names, such as **lhlab – Alarmverwaltung**.
4. Drag the appropriate block into the script, select your Items or Things,
   and adapt example values. The Item picker also lists ordinary Items where a
   Group is expected; select a real Group Item for group inputs.
5. Add rule triggers and configure the block's action areas. Save the rule to
   generate its JavaScript, then test it with your actual Item states.

Libraries are file-managed and read-only in MainUI. Resolve duplicate UI-managed
libraries with the same UID before installing a file-managed copy. Historical
library-split migration instructions in the individual guides apply only to
installations using those old library IDs; a fresh installation does not run
archived migration scripts.

## Rule inputs and triggers

| Use case | Inputs and execution |
| --- | --- |
| Battery monitoring | Select a group of numeric percentage Items. Trigger on member state changes; evaluate once after startup or manually to initialize existing values. Configure thresholds, confirmation and action areas. |
| Humidity monitoring | Select sensor and alarm groups, map them to semantic rooms, and trigger on relevant group-member changes, including externally supplied alarm changes. |
| Contact/Switch alarms | Select a source and a dedicated Switch alarm Item. Trigger on source changes and initialize after startup; configure delay and reminders. |
| Temperature-dependent windows | Select a Contact, temperature and dedicated Switch alarm Item. Trigger on contact/temperature state changes and all inputs to the temperature-limit expression; initialize after startup. No periodic trigger is needed. |
| DWD warnings | Adapt the shared Item prefix, slot count and binding/rule triggers to your warning Items. The prefix is text, not a single selectable Item. |
| Thermostats | Assign setpoints, modes, sensors and actuators. Add triggers for relevant state changes and schedule requirements; loading a block does not create periodic execution. |
| Thing control | Select a Thing and choose enable/disable. A restart requires an explicitly composed disable, delay and enable sequence. |

The generic alarm-group key, such as `hausalarme`, is an internal identifier,
not an openHAB Group Item. Optional memory inputs require String Items. Battery
and humidity group selections start empty; source/alarm blocks may retain
editable example names such as `MyContact` and `MyAlarm`.

Alarm libraries expose action areas rather than choosing recipients. Install
`lhlab_alarm_library` as well when using its **current alarm** value block for
messages from battery or humidity callbacks. Add your own push, email or other
actions. Existing alarm Items may also supply the independent
[overview widgets](../widgets/README.md).

## Shelly profiles and future updates

The wall-display controller requires five explicitly configured, nonnegative
profile IDs. They start at `-1` (unset), and zero is valid. Use the profile IDs
actually configured on your device; complete the MQTT inputs too. See the
[profile mapping guide](lhlab_thermostat_library.md#configurable-shelly-schedule-profiles).

Updating a library does not replace JavaScript already saved in a rule. Reload
MainUI and resave affected Blockly scripts after a code update. Existing saved
inputs remain; newly inserted blocks receive the current presets. Saving can
reset rule-private caches and pending timers, so schedule controller changes
appropriately.

Return to the [repository quick start](../../../../../README.md) or the
[documentation index](../../../../../docs/README.md).

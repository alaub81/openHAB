# Light alarms as a grid cell

File-based MainUI definition, `version: 1`. Copy `licht_alarm_cell.yml` to `$OPENHAB_CONF/yaml/widgets/`.

The cell matches the window and humidity widgets: 120 pixels high, up to three prioritized entries, an alarm counter, and a native detail view with all room alarms. Active alarms appear first and red; unknown states appear gray. The header bulb lights only when at least one room alarm is ON. Each bulb in compact and detail entries follows its own alarm: ON lights it, other states do not. Additional entries are indicated by `+N weitere`.

```yaml
component: widget:licht_alarm_cell
config:
  title: Lichtalarme
  alarmGroup: Licht_Alarm_ALL
```

Add this configuration to an existing `oh-grid-cells` group. The existing Overview configuration supplies `Licht_Alarm_ALL`. Its Switch members are displayed. The compact view removes the words Licht, Light, Beleuchtung, and Alarm from Item labels.

The display reflects the alarm Item's current ON/OFF state, rather than the lamp's switching state. A light being on therefore does not automatically mean an alarm. Delays and reminders remain the responsibility of the existing rule, for example for `BadOG_Licht_Alarm`. The widget changes no Items, lights, or rules and sends no messages.

MainUI's temporary `-` state produces a loading indicator. `NULL` and `UNDEF` appear as unknown. A neutral no-room-alarms-loaded hint remains until group members load. Reload after group membership changes; alarm states are tracked live.

The YAML structure and agreement between compact and expanded display functions were checked locally. The file has not yet been installed on the server or added to the Overview; visual verification in MainUI is pending.

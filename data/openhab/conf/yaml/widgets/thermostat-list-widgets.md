# Thermostat list widgets

These three stepper widgets display and command existing thermostat Items.
They share a parameter layout but use different operating-mode controls.

| Source | Widget ID | Mode Item |
| --- | --- | --- |
| [thermostat_widget.yml](thermostat_widget.yml) | `thermostat_list_widget` | Switch: `ON` / `OFF` |
| [thermostat_heat_cool_list_widget.yml](thermostat_heat_cool_list_widget.yml) | `thermostat_heat_cool_list_widget` | String: `OFF` / `HEAT` / `COOL` |
| [thermostat_wd_widget.yml](thermostat_wd_widget.yml) | `thermostat_wd_list_widget` | Switch: `ON` / `OFF` |

For the newer compact climate row, use the separate
[compact heating/cooling guide](climate_heatcool_compact_list_widget.md).

## Installation and parameters

Copy the selected file to `$OPENHAB_CONF/yaml/widgets/` and reload MainUI.
Place the widget inside a list or `oh-list-card`, not an `oh-grid-cells` container.

| Parameter | Expected Item/value |
| --- | --- |
| `title` | Optional display text |
| `item` | Required writable `Number:Temperature` setpoint |
| `isttemp` | Measured `Number:Temperature` |
| `isthumidity` | Humidity percentage; normally `Number:Dimensionless` with `%` |
| `istthermostat` | Mode Item of the type listed above |
| `istvalve` | Switch actuator feedback |
| `setbackStart`, `setbackEnd` | DateTime Items for daily setback times |
| `booster` | Switch booster state |
| `setpointEffective` | Effective `Number:Temperature` setpoint |
| `seticon` | Optional icon name |
| `min`, `max`, `step` | Stepper bounds/increment; defaults 18, 30 and 0.1 |

Although the editor marks only `item` required, status expressions also read
mode and actuator feedback. Assign those Items for normal operation and verify
the selected widget with your available feedback. Some legacy dialog text calls
humidity `Number:Humidity`; the UI wording is retained in the source.

## Page fragment

This example belongs in an existing layout block's default slot. Replace the
example names with your Items. The plus/minus controls change the setpoint;
mode controls issue commands to `istthermostat`.

```yaml
- component: oh-list-card
  config:
    title: Heating
  slots:
    default:
      - component: widget:thermostat_list_widget
        config:
          title: Living room
          item: MyRoomSetpoint
          isttemp: MyRoomTemperature
          isthumidity: MyRoomHumidity
          istthermostat: MyRoomHeatingEnabled
          istvalve: MyRoomHeatingActuator
```

For heating/cooling, select `widget:thermostat_heat_cool_list_widget` and a
String mode Item. For the wall-display variant, select
`widget:thermostat_wd_list_widget` with a Switch mode Item. Device links, MQTT
Things and [thermostat Blockly rules](../block_libraries/lhlab_thermostat_library.md)
are configured separately; the widgets do not create them.

# Climate: compact heating/cooling list widget

Documentation for [`climate_heatcool_compact_list_widget.yml`](climate_heatcool_compact_list_widget.yml), widget ID `climate_heatcool_compact_list_widget`, describing the local version dated 2026-10-26.

The widget combines room name, measured temperature, humidity, setpoint adjustment, and operating modes in one compact list row. A second line explains operating status with symbols and, when applicable, the effective setpoint difference.

## Installation

1. Copy the YAML file to `$OPENHAB_CONF/yaml/widgets/`; it already includes `version: 1` and `widgets:`.
2. Reload MainUI.
3. Add the personal widget inside a list or `oh-list-card`.
4. Select the appropriate Items, especially setpoint and operating mode.

The root is `f7-list-item`: this is a list widget, not a standalone card or grid cell. Several rooms can share one list.

## Items and parameters

Only `item` is required by the configuration dialog. For full functionality, also assign `istthermostat` and the sensors/feedback Items actually available.

| Parameter | Expected value | Function/default |
| --- | --- | --- |
| `title` | Text | Room name; falls back to setpoint Item name. |
| `item` | Writable `Number:Temperature` | Required setpoint adjusted by the stepper. |
| `isttemp` | `Number:Temperature` | Measured room temperature; `-` if unassigned. |
| `isthumidity` | Percentage, normally `Number:Dimensionless` with `%` | Optional humidity in parentheses below measured temperature. |
| `istthermostat` | String: `OFF`, `HEAT`, `COOL` | Feedback and command target for mode controls. |
| `istvalve` | Switch: `ON`/`OFF` | Actuator feedback; affects colors and booster display. |
| `setbackStart` | DateTime | Start of daily setback. |
| `setbackEnd` | DateTime | End of daily setback. |
| `smartgrid` | String, especially `red`, `orange`, `green` | Affects day/setback symbol in cooling mode. |
| `manualActorMode` | Writable String: `AUTO`, `FORCE_ON`, `FORCE_OFF` | Optional manual actuator mode, cycled by the large left icon. |
| `booster` | Switch: `ON`/`OFF` | Feedback for an externally controlled booster. |
| `setpointEffective` | `Number:Temperature` | Effective setpoint after external adjustments. |
| `seticon` | Icon name | Left icon; default `iconify:mdi:heated-floor`. |
| `min` | Number | Stepper minimum; default `18`. |
| `max` | Number | Stepper maximum; default `30`. |
| `step` | Number | Step size; default `0.1`. |

Setpoint, measured, and effective temperatures should use the same unit. Comparisons use numeric state components; setpoint differences are not converted between units.

The YAML dialog still describes humidity as `Number:Humidity`. For new percentage Items, use `Number:Dimensionless` with `%`. This documentation does not change that dialog text.

## Controls

| Control | Action |
| --- | --- |
| Minus/plus | Changes `item` by `step` within `min`/`max`. |
| Chart icon | Intended to open the Analyzer with setpoint and optional measured/effective temperatures and actuator feedback. |
| Power icon | Sends `OFF` to `istthermostat`. |
| Flame | Sends `HEAT`, or `OFF` if already heating. |
| Snowflake | Sends `COOL`, or `OFF` if already cooling. |
| Large left icon | Cycles `AUTO → FORCE_ON → FORCE_OFF → AUTO` if `manualActorMode` is assigned; otherwise sends no command. |

The stepper adjusts the normal setpoint, not `setpointEffective`. Booster and Smart Grid are displayed without dedicated switches in this row.

The widget does not calculate valve control, hysteresis, setback temperature, or Smart Grid adjustments. Existing rules or the thermostat must do that. Changing `manualActorMode` affects the actuator only if its rule/integration handles that mode.

## Status symbols

Manual forced modes replace the remaining status line. Next priority is thermostat OFF. Otherwise day/setback, heating/cooling, and setpoint adjustment symbols are combined.

| Symbol | Meaning |
| --- | --- |
| `Ⓜ+` | `manualActorMode = FORCE_ON`. |
| `Ⓜ-` | `manualActorMode = FORCE_OFF`. |
| `⏻` | Thermostat OFF unless manual forced mode takes priority. |
| `☀︎` | Normal period or corresponding Smart Grid state in cooling mode. |
| `☾︎` | Setback period or Smart Grid `red` in cooling mode. |
| `≋` | Heating (`HEAT`). |
| `❅` | Cooling (`COOL`). |
| `▲` | Booster ON, mode HEAT, actuator ON. |
| `▼` | Booster ON, mode COOL, actuator ON. |
| `△` | Effective setpoint above normal setpoint, unless an active booster arrow takes priority. |
| `▽` | Effective setpoint below normal setpoint, unless an active booster arrow takes priority. |

If booster is not ON and the setpoints differ, the difference to one decimal place and the effective setpoint are shown, for example `+1.5 (23.0 °C)`. Equal values omit this addition.

### Setback and Smart Grid

Only hours/minutes of `setbackStart` and `setbackEnd` are evaluated; calendar dates are ignored. Overnight periods such as 22:00–06:00 work. Equal start/end means no active setback.

In COOL mode, an assigned, existing `smartgrid` Item overrides the time check: `red` gives the moon symbol; all other states give the sun symbol. The normal time check is skipped in this case.

Time evaluation uses `dayjs()`. There is no clock parameter or timer, so recalculation exactly at a boundary is not guaranteed without another update. Rules must remain responsible for actual control.

## Colors

The first matching condition determines stepper color:

| Condition | Color |
| --- | --- |
| Booster ON, actuator ON, HEAT | `deeporange` |
| Booster ON, actuator ON, COOL | Blue |
| Actuator ON, HEAT | Yellow |
| Actuator ON, COOL | Light blue |
| HEAT/COOL without previous match | Green |
| OFF | Red |
| No matching feedback | Gray |

For the left actuator icon, FORCE_ON is yellow and FORCE_OFF black. Otherwise booster plus actuator ON is yellow, actuator ON is green, and actuator OFF red. Missing usable feedback is gray. This color therefore describes a different aspect than stepper color.

## Example

Replace the example `Raum_...` names with actual Items:

```yaml
component: oh-list-card
config:
  title: Raumklima
slots:
  default:
    - component: widget:climate_heatcool_compact_list_widget
      config:
        title: Wohnzimmer
        item: Raum_Solltemperatur
        isttemp: Raum_Isttemperatur
        isthumidity: Raum_Luftfeuchtigkeit
        istthermostat: Raum_Thermostatmodus
        istvalve: Raum_Heizaktor
        setbackStart: Raum_Absenkbeginn
        setbackEnd: Raum_Absenkende
        smartgrid: Raum_SmartGrid
        manualActorMode: Raum_ManuellerAktormodus
        booster: Raum_Booster
        setpointEffective: Raum_EffektiveSolltemperatur
        seticon: iconify:mdi:heated-floor
        min: 18
        max: 30
        step: 0.1
```

Omit unused optional parameters. Mode controls are always present in the current layout and need `istthermostat` assigned to operate.

## Persistence, layout, and limitations

- Current display/control needs no history. Analyzer charts need persisted values for the relevant Items. Configure heating-control persistence independently.
- Measurements prefer `displayState`, falling back to raw `state`. Not every field handles `NULL`/`UNDEF`, so these may appear as text.
- Titles can wrap to two lines. The right control area has fixed width; on phones use a sufficiently wide list rather than half a grid cell.
- Uncached Iconify icons may require internet access on first use.
- The current chart button supplies `actionAnalyzerItems` as a URL-like `#/analyzer?items=...` string. If it does not open, inspect this argument: MainUI expects a list of Item names. This documentation does not change the button.

References: [Stepper](https://www.openhab.org/docs/ui/components/oh-stepper.html), [units and dimensions](https://www.openhab.org/docs/concepts/units-of-measurement.html).

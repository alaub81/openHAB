# MainUI widgets

The twelve YAML files in this directory are reusable, file-managed openHAB
widgets. Each file contains `version: 1` and a `widgets:` map. Its map key is the
widget ID used in Page YAML; that ID can differ from the filename.
Detailed documentation stays beside its YAML source.

## Install

The repository's Docker setup already mounts this directory at
`/openhab/conf/yaml/widgets/`. For another openHAB 5.2 installation, copy only
the desired `.yml` files to `$OPENHAB_CONF/yaml/widgets/`. Keep their wrappers
intact and reload MainUI. File-managed widgets are read-only in the UI; edit the
source file for future changes. Resolve an existing UI widget with the same ID
before installing a file-managed copy.

Add a personal widget to the appropriate Page container and select your own
Items. Creating the widget definition does not create Things, Items or rules.
You do not need the full Docker stack or the local `tools/` directory to use it.

## Catalog

| Source | Widget ID | Display and requirements | Guide |
| --- | --- | --- | --- |
| [astro_progress_cell.yml](astro_progress_cell.yml) | `astro_progress_cell` | Sun/moon overview; Astro Items and a regularly updated clock Item | [Astro](astro_progress_cell.md) |
| [batterie_ladestaende_cell.yml](batterie_ladestaende_cell.yml) | `batterie_ladestaende_cell` | Battery levels; group of numeric percentage Items | [Batteries](batterie_ladestaende_cell.md) |
| [fenster_tueren_cell.yml](fenster_tueren_cell.yml) | `fenster_tueren_cell` | Windows/doors; Contact group, optional alarm Items and `contactOverview` metadata | [Windows and doors](fenster_tueren_cell.md) |
| [licht_alarm_cell.yml](licht_alarm_cell.yml) | `licht_alarm_cell` | Existing light alarms; group of ON/OFF alarm Items | [Light alarms](licht_alarm_cell.md) |
| [luftfeuchtigkeit_alarm_cell.yml](luftfeuchtigkeit_alarm_cell.yml) | `luftfeuchtigkeit_alarm_cell` | Room humidity alarms; alarm group, sensor group and semantic root group | [Humidity](luftfeuchtigkeit_alarm_cell.md) |
| [wetterstation_cell.yml](wetterstation_cell.yml) | `wetterstation_cell_v1` | Weather cell; temperature Item plus optional weather readings | [Weather station](wetterstation_cell.md) |
| [dwd_warnleiste.yml](dwd_warnleiste.yml) | `dwd_warnleiste` | Expandable warnings; DWD warning-slot Items | [DWD warnings](dwd_warnleiste.md) |
| [dwd_pollenleiste.yml](dwd_pollenleiste.yml) | `dwd_pollenleiste` | Pollen exposure; DWD Pollenflug Items | [DWD pollen](dwd_pollenleiste.md) |
| [climate_heatcool_compact_list_widget.yml](climate_heatcool_compact_list_widget.yml) | `climate_heatcool_compact_list_widget` | Compact climate row; setpoint, mode and available feedback Items | [Compact climate control](climate_heatcool_compact_list_widget.md) |
| [thermostat_widget.yml](thermostat_widget.yml) | `thermostat_list_widget` | Heating stepper row; setpoint, Switch mode and feedback Items | [Thermostat list widgets](thermostat-list-widgets.md) |
| [thermostat_heat_cool_list_widget.yml](thermostat_heat_cool_list_widget.yml) | `thermostat_heat_cool_list_widget` | Heating/cooling stepper row; setpoint, String mode and feedback Items | [Thermostat list widgets](thermostat-list-widgets.md) |
| [thermostat_wd_widget.yml](thermostat_wd_widget.yml) | `thermostat_wd_list_widget` | Wall-display stepper row; setpoint, Switch mode and feedback Items | [Thermostat list widgets](thermostat-list-widgets.md) |

## Page YAML: four overview cells

Insert this fragment into an existing layout block's `slots.default`, or add the
widgets through the Page designer. Replace all `My...` names with actual Item
names. These are component instances, not complete widget-definition files.

```yaml
- component: oh-grid-cells
  config: {}
  slots:
    default:
      - component: widget:batterie_ladestaende_cell
        config:
          title: Batteries
          batteryGroup: MyBatteryGroup
      - component: widget:luftfeuchtigkeit_alarm_cell
        config:
          title: Humidity
          alarmGroup: MyHumidityAlarms
          sensorGroup: MyHumiditySensors
          modelGroup: MySemanticModel
      - component: widget:licht_alarm_cell
        config:
          title: Light alarms
          alarmGroup: MyLightAlarms
      - component: widget:fenster_tueren_cell
        config:
          title: Windows and doors
          contactGroup: MyContacts
          alarmGroupItem: MyWindowAlarmSummary
          closeAlarmItem: MyCloseWindowsAdvisory
          testMode: live
```

The window cell's `alarmGroupItem` and `closeAlarmItem` are optional ON/OFF
Items; omit those lines if unused. Individual contact-to-alarm assignments live
in each Contact Item's `contactOverview` metadata. The old `equipmentGroup`
parameter is retained for compatibility and is not queried.

The light cell expects alarm Items, not the lamps' ordinary switching Items.
The humidity cell needs semantic room assignments to pair sensors and alarms;
its `modelGroup` must contain the relevant model hierarchy. Battery levels
must be numeric percentages from 0 to 100. All these Item/group selections
start empty; configure every new instance. Copying an already configured instance
also copies its explicit selections.

## Containers, behavior and dependencies

- Cell widgets belong in `oh-grid-cells`. Thermostat rows belong in a list or
  `oh-list-card`; DWD strips need a container that can grow vertically.
- Alarm overview widgets read existing alarm states. The separate
  [Blockly libraries](../block_libraries/README.md) can implement alarm rules,
  but other rules or bindings can provide those Items too.
- Thermostat widgets send commands to selected setpoint/mode Items. Configure
  the corresponding device or control rule independently; displaying a widget
  does not install a thermostat controller.
- Keep preview/test settings in live mode for ordinary use. Available demo
  modes are documented per widget and do not create real sensor data.
- Native openHAB icons and Iconify names are used as specified by each widget.
  The historical deployment records and ignored archives are not runtime files.

Return to the [repository quick start](../../../../../README.md) or the
[documentation index](../../../../../docs/README.md).

# Humidity alarms as a grid cell

## Explicit group selection

`alarmGroup`, `sensorGroup`, and `modelGroup` all require explicit selections.
There are no implicit groups named `Humidity_Alarm`, `Humidity_Innen_ALL`, or
`Home`. Existing explicit instance settings remain valid. Semantic room
assignments and optional `humidityOverview` overrides are still required as
described below; this change does not create model Items or alarm rules.

File-based MainUI definition, `version: 1`. Copy `luftfeuchtigkeit_alarm_cell.yml` to `$OPENHAB_CONF/yaml/widgets/`. The cell uses the window widget's 120-pixel height, compact three-row summary, and native detail view. Active alarms appear first and red. Unknown states and sensor assignment problems appear gray.

## Configuration

```yaml
component: widget:luftfeuchtigkeit_alarm_cell
config:
  title: Luftfeuchtigkeit
  alarmGroup: MyHumidityAlarms
  sensorGroup: MyHumiditySensors
  modelGroup: MySemanticModel
```

Add this configuration to an existing `oh-grid-cells` group. All three groups are configurable. All group selections are explicit; no alarm/sensor pairs are hardcoded.

- **Alarm group:** Switch members supply alarm states.
- **Humidity sensor group:** Numeric members are candidates for automatic assignment and must be present in the loaded model.
- **Semantic root group:** Nested groups must include the relevant equipment and sensors, usually the complete house model.

## Automatic assignment

The widget loads the root group with nested members and `semantics` metadata. It reads alarm and sensor rooms from `semantics.config.hasLocation`. For sensors under equipment, it follows `isPointOf`, or `isPartOf` for nested equipment, until it finds the room. Cycles terminate traversal. Exact room Item names are compared, rather than labels or name fragments.

Each alarm expects exactly one sensor from the configured sensor group in the same room. Multiple sensors produce an ambiguous-assignment indication. Missing sensors and rooms are also explicitly reported. The alarm state remains visible, and ON still takes priority.

### New or renamed sensors

Add the sensor to the humidity sensor group and assign it to its room or equipment in that room in the semantic model. The room also needs an alarm Item in the alarm group. Reload after changing names, memberships, or semantics. The widget then rebuilds assignments without code changes.

When replacing a sensor, remove the old Item from the sensor group to avoid ambiguity. The widget creates no alarm Items or rules. The existing alarm rule also requires a valid semantic assignment.

### Optional explicit override

The alarm Item's `humidityOverview` metadata can specify a sensor Item name:

```yaml
value: Mein_Feuchtesensor
config: {}
```

This explicit assignment takes priority, including when a room contains multiple sensors. The sensor may be outside the model or sensor group. Update explicitly configured metadata when renaming that sensor; automatic assignment needs no override.

## Measurements and loading

Compact entries show the percentage and alarm state, for example `78 % · Alarm`. Details also show readings for rooms without an alarm. Values are rounded to at most one decimal place. Missing or invalid readings appear as `— %`. Values outside 0–100 or with other units are excluded; unitless numbers count as percentages.

Each view uses two cached structure queries: model group and alarm group. Sensors are selected through model group memberships rather than individual queries. Loading the full model may take longer in large installations than the former fixed assignments. The detail view mounts only on opening. Alarm and sensor states then follow MainUI's reactive Item store.

MainUI's temporary alarm state `-` produces a loading indication. `NULL` and `UNDEF` remain unknown. Missing sensor readings do not block alarm states. Until model or alarm members load, a neutral loading hint remains. Incorrect group names or connection failures must be resolved in configuration or connectivity.

The widget does not recalculate thresholds or change lights, Items, rules, or notifications. The alarm rule remains responsible for alarms and clearance. Alarm state is not proof of notification delivery.

## Validation

JavaScript checks cover percentage formatting, placeholder-to-live transitions, direct/indirect room assignment, renaming, ambiguity, missing assignments, duplicate model paths, cycles, and metadata priority. They also verify that former Item names are no longer hardcoded mappings. Formatting uses `Number.parseFloat` because MainUI does not expose a standalone `parseFloat`.

```sh
ruby -ryaml -rjson -e 'puts JSON.generate(YAML.load_file(ARGV[0]))' \
  data/openhab/conf/yaml/widgets/luftfeuchtigkeit_alarm_cell.yml > /tmp/widget.json
osascript -l JavaScript tools/humidity-widget/verify.js /tmp/widget.json
```

An optional second argument accepts a complete local Item export to check the 18 existing alarms. With the saved export, 52 checks passed and all 18 alarms found exactly one sensor. The test uses a restricted JavaScript context, not MainUI's complete parser. Live server checks, installation, and visual MainUI verification are pending.

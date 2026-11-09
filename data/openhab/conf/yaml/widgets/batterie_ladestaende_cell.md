# Battery levels as a grid cell

## Explicit group selection

`batteryGroup` has no default and no fallback to an installation-specific group.
Select your own numeric battery group in every widget instance. A missing group
is a configuration to complete, not evidence that all batteries are charged.
Existing instances with an explicit group selection keep that selection.

File-based MainUI definition, `version: 1`. Copy `batterie_ladestaende_cell.yml` to `$OPENHAB_CONF/yaml/widgets/`. The cell uses the same 120-pixel height and compact style as the window, light, and humidity summaries.

## Configuration

```yaml
component: widget:batterie_ladestaende_cell
config:
  title: Batterien
  batteryGroup: MyBatteryGroup
```

Place it inside `oh-grid-cells`. The dialog lets you select a title and battery group. There are no hardcoded sensor Item names and no dependency on alarm Items or rules. New batteries are included through group membership. Reload the page after changing members or labels.

## Display

- The compact cell shows the three lowest valid levels in ascending order, or fewer if fewer valid values exist.
- If **all** numeric battery Items have a valid level of exactly **100%**, the rows are replaced by a shield/check icon and the full-charge message. Missing values and empty groups cannot produce this state.
- Tapping opens the native detail view with all numeric battery Items sorted from 0 to 100. Ties use alphabetical labels. Comparisons use unrounded values.
- Missing or invalid measurements appear last as `— %`. Their count appears in the compact footer; they are never treated as 0% or empty batteries.
- The compact view removes battery-related words from labels; the detail view uses full Item labels.

## Dynamic battery icon

As in `live_energy_flow`, the icon consists of an outline, terminal, and proportional fill bar: 0% empty, 50% half full, 100% full. The header shows the lowest known level; each row has its own indicator. Unknown values have a gray outline and no fill.

Colors match the solar widget: red below 20%, orange from 20% to below 30%, green from 30%. This is a visual classification only. The widget creates no alarms, commands, or notifications. Reduced-motion settings disable the short fill animation.

## Values and loading

Supported types are `Number` and `Number:Dimensionless`, with percentage values from 0 to 100. Bare numbers count as percentages. Decimal dots and commas are supported, with display rounding to at most one decimal place. Other units, negative values, values above 100, `NULL`, and `UNDEF` appear as missing measurements.

Each view caches the battery group structure query. Live states come from MainUI's reactive Item store. Temporary state `-` produces a loading hint while known values remain visible. Before group members load, a neutral no-batteries-loaded hint remains visible. The detail view mounts only when opened. Percentage formatting uses MainUI-compatible `Number.parseFloat`.

## Validation

```sh
ruby -ryaml -rjson -e 'puts JSON.generate(YAML.load_file(ARGV[0]))' \
  data/openhab/conf/yaml/widgets/batterie_ladestaende_cell.yml > /tmp/battery-widget.json
osascript -l JavaScript tools/battery-widget/verify.js /tmp/battery-widget.json
```

Checks cover numeric sorting, 0%, decimals, invalid data, live changes, the full-charge state, and actual display bindings including fill widths in both views. An optional second argument accepts a complete local Item export. With the available 57-battery export, 50 checks passed. The test uses a restricted JavaScript context, not MainUI's complete parser.

The file was created and checked locally. Installation and visual verification on the running openHAB system are pending.

## Editor preview

MainUI's editor also displays sections with `visible: false`. Therefore a conditional array repeater creates the compact empty/full indicator. The missing-value hint cannot cover valid battery rows in the editor. Regression checks also cover normal values, full charge, and missing values under editor conditions.

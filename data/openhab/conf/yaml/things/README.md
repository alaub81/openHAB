# Thing and Item templates

Files ending in `.yml.example` are inactive templates. Adapt only the examples
you need, then save them with a `.yml` extension in `$OPENHAB_CONF/yaml/things/`.
Keep their `version: 1` / `things:` wrapper intact. These are file-provider
definitions, not MainUI export documents.

| Template | Purpose |
| --- | --- |
| [shelly_walldisplay_mqtt.yml.example](shelly_walldisplay_mqtt.yml.example) | MQTT Thing example for a Shelly wall display |
| [shelly_walldisplay_screen.yml.example](shelly_walldisplay_screen.yml.example) | Four HTTP Things for wall-display screen ON/OFF commands |
| [somfy_sonnensensor_ost.yml.example](somfy_sonnensensor_ost.yml.example) | East sun-sensor example |
| [somfy_sonnensensor_sued.yml.example](somfy_sonnensensor_sued.yml.example) | South sun-sensor example |
| [somfy_sonnensensor_west.yml.example](somfy_sonnensensor_west.yml.example) | West sun-sensor example |

Replace example Thing UIDs, bridge references, device IDs, topics and settings
with your own. Install the corresponding binding and configure its bridge.
Create/link Items separately; an example Thing does not create a complete
widget or controller setup.

For screen control, install the [HTTP binding](https://www.openhab.org/addons/bindings/http/),
replace the four example hostnames in the screen template with device IP addresses,
and activate it as `.yml`. Adapt and activate the matching
[screen Items](../../items/shelly_walldisplay_screen.items.example) as `.items`.
The Items use the existing location groups `GF_Dining`, `AT_LinusRoom`,
`C_Corridor` and `FF_Bathroom`; adapt these names to your own location model.
Send ON/OFF to an individual screen Item.
The WRITEONLY channels map ON/OFF to JSON booleans and call
`/rpc/Ui.Screen.Set?params={"on":true}` or `{"on":false}`. The binding handles URL
escaping. No transformation add-on or rule is needed. Item states reflect the last
command through autoupdate; they do not track touches, automatic sleep or changes
from other clients. No requests are made until a command is sent.
Before the first command, Thing status may be `UNKNOWN` and Item state `NULL`.
If these UIDs already exist as MainUI-managed Things/Items, use those definitions
or remove them before activating the file templates to avoid duplicate providers.

The [Shelly thermostat Item example](../../items/shelly_walldisplay_thermostat.items.example)
is also inactive until adapted and saved as an `.items` file. Select those Items
explicitly in your widgets and Blockly rules.

For the reason behind the file-based sun-sensor definitions and the original
investigation, see [Somfy sun sensors](somfy_sonnensensoren.md). When migrating
an existing Thing, preserve its UID, bridge and Item links, and ensure the same
UID is not simultaneously defined through MainUI and YAML.

Return to the [documentation index](../../../../../docs/README.md).

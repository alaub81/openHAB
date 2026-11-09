# Thing and Item templates

Files ending in `.yml.example` are inactive templates. Adapt only the examples
you need, then save them with a `.yml` extension in `$OPENHAB_CONF/yaml/things/`.
Keep their `version: 1` / `things:` wrapper intact. These are file-provider
definitions, not MainUI export documents.

| Template | Purpose |
| --- | --- |
| [shelly_walldisplay_mqtt.yml.example](shelly_walldisplay_mqtt.yml.example) | MQTT Thing example for a Shelly wall display |
| [somfy_sonnensensor_ost.yml.example](somfy_sonnensensor_ost.yml.example) | East sun-sensor example |
| [somfy_sonnensensor_sued.yml.example](somfy_sonnensensor_sued.yml.example) | South sun-sensor example |
| [somfy_sonnensensor_west.yml.example](somfy_sonnensensor_west.yml.example) | West sun-sensor example |

Replace example Thing UIDs, bridge references, device IDs, topics and settings
with your own. Install the corresponding binding and configure its bridge.
Create/link Items separately; an example Thing does not create a complete
widget or controller setup.

The [Shelly thermostat Item example](../../items/shelly_walldisplay_thermostat.items.example)
is also inactive until adapted and saved as an `.items` file. Select those Items
explicitly in your widgets and Blockly rules.

For the reason behind the file-based sun-sensor definitions and the original
investigation, see [Somfy sun sensors](somfy_sonnensensoren.md). When migrating
an existing Thing, preserve its UID, bridge and Item links, and ensure the same
UID is not simultaneously defined through MainUI and YAML.

Return to the [documentation index](../../../../../docs/README.md).

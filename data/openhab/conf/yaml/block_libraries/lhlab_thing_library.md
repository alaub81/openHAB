# lhlab: Thing control

[lhlab_thing_library.yml](lhlab_thing_library.yml) is a separate file-managed Blockly library, UID `lhlab_thing_library`. It carries the unchanged **Thing controller** block from `Blocklibraries_lhlab.wiki`.

## Function

The block enables or disables the selected Thing. It does not implement a new standalone restart flow. As before, calling rules compose restarts from disabling, an appropriate delay, and re-enabling.

The split changes no existing flows, Thing UIDs, timers, or delays. Loading the library creates no Things/rules and performs no Thing action.

## Installation

Container destination:

```text
/openhab/conf/yaml/block_libraries/lhlab_thing_library.yml
```

Install together with [lhlab_thermostat_library.yml](lhlab_thermostat_library.yml), then reload MainUI. Both should appear under their new UIDs as file-managed/read-only.

Create a Blockly rule and select your own Thing in the controller block.
For an existing UI library, back up affected rules, replace old Thing controller
blocks with this library's block, preserve inputs/delays and verify before
removing the old library. Saving may reset active rule timers.

## Changes and validation

Edit YAML for future behavior changes, copy it, and resave affected Blockly rules. This split preserves block configuration, template, and helper definitions. Migration checks covered complete reference replacement, unchanged JavaScript, and repeatability.

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

See the [thermostat documentation](lhlab_thermostat_library.md#installation-and-splitting-the-previous-library) for the complete migration sequence. From the local repository:

```sh
python3 archive/scripts-cleanup-20261108/heating-library/migrate.py --check
python3 archive/scripts-cleanup-20261108/heating-library/migrate.py
```

Delete old UI library `Blocklibraries_lhlab.wiki` only after successful migration. Until then both versions may coexist. The script changes only Blockly references, preserving generated code and enabled status. Saving reloads rule scripts and may reset active delay timers.

## Existing uses

At preparation, the old Thing controller appeared 22 times across three rules:

- **Roomba Thing Status**
- **BLUGW Things Neustart**
- **Sonnensensor Überwachung** — disabled; remains disabled.

The new type is `lhlab_thing_library_Thing controller`. Migration automatically replaces prefix `Blocklibraries_lhlab.wiki_`.

## Changes and validation

Edit YAML for future behavior changes, copy it, and resave affected Blockly rules. This split preserves block configuration, template, and helper definitions. Migration checks covered complete reference replacement, unchanged JavaScript, and repeatability.

The library is installed as file-managed. All three Thing rules were migrated on 2026-10-30. Their generated scripts remain unchanged; sun-sensor monitoring remains disabled. A final check of all rules found no `Blocklibraries_lhlab.wiki` references. The old UI library is removed.

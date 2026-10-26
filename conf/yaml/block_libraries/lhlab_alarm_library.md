# lhlab – Alarmverwaltung

Generic Blockly alarm handling for openHAB 5.2. The library detects new, changed and cleared alarms. Notification delivery belongs to the caller's Blockly statements; the library never sends push messages, speaks on Echo devices or runs other rules itself.

## Install from a file (openHAB 5.2.3)

Copy `lhlab_alarm_library.yml` into `$OPENHAB_CONF/yaml/block_libraries/`. Replace the previous file at the same path; it was missing the file-based wrapper. The file begins with:

```yaml
version: 1
blocks:
  lhlab_alarm_library:
    component: BlockLibrary
    # config, props and slots follow
```

The UID is the map key below `blocks`, not a top-level `uid` field. This is the `ui:blocks` provider format, confirmed in the openHAB core implementation: [YamlBlocksDTO](https://github.com/openhab/openhab-core/blob/5.2.3/bundles/org.openhab.core.model.yaml/src/main/java/org/openhab/core/model/yaml/internal/uicomponents/YamlBlocksDTO.java) and [YamlBlocksProvider](https://github.com/openhab/openhab-core/blob/5.2.3/bundles/org.openhab.core.model.yaml/src/main/java/org/openhab/core/model/yaml/internal/uicomponents/YamlBlocksProvider.java).

openHAB loads the file automatically. Reopen the Blockly editor to see **lhlab – Alarmverwaltung**. The library is file-managed and read-only in MainUI; edit this canonical YAML file for future changes. No manual editor import is required.

If an editable UI library with the same UID was already created, resolve that duplicate before using the file-based definition. Do not edit JSONDB files directly.

## DWD monitor block

The additional **DWD-Warnungen überwachen** statement block reads all configured warning slots after a short quiet period. Inputs are the common Item prefix, slot count, optional memory Item and debounce delay. For this installation they are `DWDUnwetterWarnungen_`, `5`, `DWDUnwetterWarnungen_AlarmMemory` and `2` seconds.

Expected Item suffixes are `Warning_N`, `Type_N`, `Severity_N`, `Valid_From_N`, `Valid_To_N`, `Headline_N`, `Description_N` and `Instruction_N`. OFF slots require no description values. Active slots require a valid event, severity, start/end times, headline and description. Instruction is optional. If any slot is unknown, an active warning is incomplete, or identities are ambiguous, the prior snapshot is retained and a warning is logged. It retries settling up to three times.

Identity uses the event text plus the start instant, not the slot number. Identical warnings moved to another slot are not re-sent. Changes to the severity, end time, headline, description or instruction update the notification. Changes to the event text or onset create a new identity, followed by clearance of the previous identity. This is a content-based identity because the configured Items do not expose the DWD CAP identifier; it is not a complete CAP update/cancellation tracker. The supplied five slots cover one location. Do not combine multiple regions or identical simultaneous events with this prefix setup.

The three action areas run once for every new, changed or ended warning. Clearance is for that particular warning; other warnings may remain active. Optional execution context `alarmSeed: true` records the complete current snapshot without invoking any action area, for a deliberate first-run baseline only.

The prepared configuration for rule `5bbc5e0b3e` keeps its five `updatedN` / `NEW` channel triggers and its five alarm-Item transitions to OFF. Each action area contains standard push notification and script invocation blocks. Push references use the stable warning identity and tapping a notification opens `/overview/`. The Echo script UID is `9cacbaff96`, with context key `Message`; it retains its own 07:15–20:30 schedule. `DWDUnwetterWarnungen_AlarmMemory` is a String Item in the existing `pEveryChange` group.

## Blocks

### Alarmdaten

Describes one alarm, with values supplied by normal Blockly blocks:

| Input | Meaning |
| --- | --- |
| Kennung | Stable identity, e.g. `fenster-kueche`; must not depend on position in a list. |
| aktiv | Boolean or raw `ON` / `OFF`, `OPEN` / `CLOSED`. Unknown/missing states stop the entire group evaluation. |
| Titel | Title of the active alarm. |
| Meldung | Message of the active alarm. |
| zusätzlicher Vergleichswert | Optional text affecting change detection, e.g. severity and validity times. |

Inactive entries need no populated title/message. An active entry with missing, NULL or UNDEF title/message also stops evaluation, retaining the previous snapshot.

### Alarmgruppe

Accepts a group key, a standard Blockly list of `Alarmdaten`, and an optional String Item name for persistent memory. Insert **Lists → create list with** into the list input, and put each `Alarmdaten` block inside that list. This also applies when there is only one alarm. Individual alarm entries now have their own output type to prevent connecting them directly to the list input. The list must be a **complete snapshot** of this alarm group. An empty list clears all previously active alarms; it must never be used to represent unavailable source data. Use an entry with unknown active state to suspend evaluation instead.

The three statement areas are:

- **bei neuem Alarm**: runs for every newly active identity.
- **bei geändertem Alarm**: runs if title, message or comparison text changed.
- **bei Entwarnung**: runs for every identity no longer active.

Changing list order does not generate messages. Identical active entries do not generate messages again. Duplicate active identities are rejected before actions run. Changes in whitespace are considered changes; normalize source text if that is undesirable.

Place push blocks and script invocation blocks **inside the appropriate area**, rather than unconditionally after the group block. These areas run synchronously. Keep all activities for one group in one block in one script action; reusing a key in multiple script actions creates separate memories. Do not recursively evaluate the same group from its own callbacks.

### aktueller Alarm

A value block available inside each statement area. Select message, title, stable ID, event kind (`NEW`, `CHANGED`, `CLEARED`), group key, previous message/title, or comparison value. Outside these areas the block returns an empty string.

At clearance, title/message refer to the former alarm, not to an automatically composed all-clear message. Compose an appropriate message yourself. A clearance of one entry is not an all-clear for the complete group.

## Push and the existing Echo script

A push notification block can use **aktueller Alarm → Meldung**, and optionally **Titel**, as its inputs. Group and identity can be used to build a notification reference. Notification icons, recipients and page actions remain caller choices.

The inspected Echo script `9cacbaff96` expects an execution context field named **`Message`** (case-sensitive). Its time window is already **07:15–20:30**. Invoke that script from the selected action areas and supply the alarm message as `Message`; do not duplicate its schedule in the library.

This library does not change or invoke existing rule `5bbc5e0b3e` or the Echo script. The DWD monitor now reads the five warning slots and composes suitable stable identities, titles, message texts and comparison values. Channel triggers remain in the calling rule.

## State and optional persistence

Without a memory Item, the library uses a rule/script-private cache. It survives normal executions but is lost when the script is reloaded or openHAB restarts. Currently active alarms are then considered new. See [JavaScript Scripting cache](https://www.openhab.org/addons/automation/jsscripting/#cache).

For restart recovery, create a dedicated String Item per alarm group, pass its Item name as the memory input, and configure persistence with `everyChange` and `restoreOnStartup`. Wait for restored memory and complete source data before the first evaluation. An uninitialized memory Item starts with no known alarms; malformed saved JSON causes an error without dispatching messages. Do not trigger the rule from changes to its own memory Item.

The library stores JSON text, not shared JavaScript objects. State is committed after each event's synchronous statements return normally. A thrown exception leaves that event pending for a later evaluation. Earlier successful events remain committed. This does not confirm push delivery or Alexa playback, provide an autonomous retry timer, or guarantee exactly-once external delivery. If push succeeds and a later action throws, a later evaluation may retry both. Use notification references where suitable. If storing the optional memory Item fails, cache state may already reflect the event; after a reload the older persisted state may be replayed.

## Validation status

Offline checks cover new/changed/cleared events, unchanged messages, list reordering, unknown states, duplicate identities, action exceptions and retries on the next evaluation, special object-key names, optional memory recovery and invalid memory types/content. Generated code templates were also expanded and executed with mocked openHAB APIs.

The extended file-based library was loaded and checked on openHAB 5.2.3. A triggerless native test with an active synthetic warning passed, including date formatting and snapshot processing, with no push or Alexa actions. The final rule was saved through REST, opened successfully in Blockly, regenerated with the installed Blockly generator and saved in MainUI. No test notifications were sent. External push delivery and actual Alexa playback remain untested.

## openHAB 5.2.3 code generation fix

Both value blocks omit the optional `BlockCodeTemplate.config.order`. In openHAB 5.2.3, a named order is looked up under `javascriptGenerator.forBlock`, which returns an undefined order for `ORDER_ATOMIC` and causes Blockly to reject the generated value. Omitting it selects the supported numeric `javascriptGenerator.ORDER_NONE` default. Both expressions are already explicitly parenthesized. See the [5.2.3 generator implementation](https://github.com/openhab/openhab-webui/blob/5.2.3/bundles/org.openhab.ui/web/src/assets/definitions/blockly/libraries.js).

Deployment status: the extended file library is loaded on the host and the memory Item exists in pEveryChange. Rule 5bbc5e0b3e is saved and ready with all ten original triggers. All temporary test rules and the temporary result Item were removed. The empty current warning set was recorded as the initial baseline. No test notifications were sent.

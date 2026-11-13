# lhlab: alarm management

## Example block presets

New blocks include editable example values: DWD Item prefix
`DWDUnwetterWarnungen_`, alarm-group key `hausalarme`, example identity
`fenster-kueche`, a kitchen-window message, and source/alarm placeholders
`MyContact` and `MyAlarm`. Adapt them to your own Items and rules. The DWD
prefix is functional: it determines the Item names read by the monitor and
must match the documented suffix pattern. These presets do not create Items
or notification rules.

## Item selection

New blocks use the openHAB Item picker for source Items, alarm Items, and optional
memory Items. The source/alarm examples remain `MyContact` and `MyAlarm`; choose
existing Items in your installation. A memory Item must be a String Item. Leave
it empty when memory should last only until the script reloads.

The DWD prefix remains a text input because it describes multiple Item names.
The alarm-group key, such as `hausalarme`, is an internal identifier rather than
an openHAB Group Item. Identities, titles, messages, and comparison values also
remain text inputs. The active input expects a state or Boolean, not an Item name.

Existing saved blocks keep their connected inputs. Reload MainUI after installing
the YAML to use the new presets when adding blocks. Existing text inputs remain
supported and can be replaced manually with Item selection blocks.

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

The additional **DWD-Warnungen überwachen** statement block reads all configured warning slots after a short quiet period. Inputs are the common Item prefix, slot count, optional memory Item and debounce delay. Example values are `DWDUnwetterWarnungen_`, `5`, `DWDUnwetterWarnungen_AlarmMemory` and `2` seconds.

Expected Item suffixes are `Warning_N`, `Type_N`, `Severity_N`, `Valid_From_N`, `Valid_To_N`, `Headline_N`, `Description_N` and `Instruction_N`. OFF slots require no description values. Active slots require a valid event, severity, start/end times, headline and description. Instruction is optional. If any slot is unknown, an active warning is incomplete, or identities are ambiguous, the prior snapshot is retained and a warning is logged. It retries settling up to three times.

Identity uses the event text plus the start instant, not the slot number. Identical warnings moved to another slot are not re-sent. Changes to the severity, end time, headline, description or instruction update the notification. Changes to the event text or onset create a new identity, followed by clearance of the previous identity. This is a content-based identity because the configured Items do not expose the DWD CAP identifier; it is not a complete CAP update/cancellation tracker. The supplied five slots cover one location. Do not combine multiple regions or identical simultaneous events with this prefix setup.

The three action areas run once for every new, changed or ended warning. Clearance is for that particular warning; other warnings may remain active. Optional execution context `alarmSeed: true` records the complete current snapshot without invoking any action area, for a deliberate first-run baseline only.

### Configurable DWD notification text

Two String-output blocks can be used inside the DWD monitor's **new**, **changed**
and **ended** action areas:

- **DWD-Warntext erstellen** selects **Push** or **Sprache (Alexa)**. Description
  and period are enabled by default; behavioral instructions are disabled.
  Push puts the original description first, followed by the compact period on
  a separate line. Speech adds the warning level and event, then the period
  and description, with whitespace flattened. No description or instruction is
  automatically summarized or cut off.
- **aktuelle DWD-Warnung** exposes the readable event name, warning level,
  formatted push title, original headline, description, instructions, push or
  speech period, formatted begin/end and raw ISO begin/end. Combine these values
  with Blockly's standard text-join block for custom messages. Missing fields
  and use outside an alarm callback return empty text.

For a frost warning, the default push title is `DWD · Wetterwarnung: Frost`.
The push body is:

```text
Es tritt leichter Frost zwischen 0 °C und -3 °C auf.
Heute 20:00 bis morgen 09:00 Uhr.
```

The corresponding speech text is:

```text
Wetterwarnung: Frost. Heute ab 20 Uhr bis morgen um 9 Uhr. Es tritt leichter Frost zwischen 0 °C und -3 °C auf.
```

Relative dates are computed when text is generated, in `Europe/Berlin`, using
calendar days across daylight-saving transitions. Same-day periods omit the
second day; warnings already in progress show only their end. Later dates use
`dd.MM.`, including the year when it differs from the current year. Push and
speech have separate clock formats. Previously delivered notifications retain
their original text; relative dates are not recalculated when viewed later.

The formatter generates a specific clearance message when called in the ended
action area and retains the notice that other warnings may still be active.
Checkboxes apply to active warnings; clearance omits the old description,
period and instructions. A push formatter with all components disabled returns
empty text; speech still identifies the warning.

The full original message remains available through **aktueller Alarm →
Meldung**. Existing alarm identities, content comparisons, memory format version
and generic alarm callers remain compatible. The optional `dwd` object stores
source fields alongside each alarm, so clearance never reads a reused warning
slot. Unchanged legacy records are enriched silently on the next evaluation.
Until then, clearance can derive the event from a legacy title; unavailable
individual source fields remain empty. Presentation options and relative dates
do not participate in change detection.

The installed DWD rule uses a separate formatter for push and Alexa in each
action area, with instructions off. The field block supplies new/updated push
titles. Notification references, icons, tags, Overview links, triggers and the
existing Alexa announcement rule's time window remain unchanged. Reopen the
Blockly editor after updating the file-managed library to load the new blocks.

The presentation definitions and utility are maintained by
`tools/dwd-messages/build.py` and `tools/dwd-messages/format.js`. Run the builder
after editing them. `tools/dwd-messages/verify.js` exercises formatting and
monitor state with isolated Items, memory, timers and delivery captures; its
`verifyDwd(time, sources)` entry point accepts the installed openHAB time API.

## Blocks

### State monitoring: windows and lights

The additional block monitors a Contact or Switch Item with a delay and limited reminders. Each source uses a dedicated Switch alarm Item. Existing alarm-group and DWD blocks retain their behavior.

| Setting | Kitchen example |
| --- | --- |
| Source Item | `Fenster_Kuche_Zustand` |
| Active state | `OPEN`; return state automatically `CLOSED` |
| Alarm Item | `Kueche_Fenster_Alarm` |
| Delay | 15 minutes |
| Additional reminders | 2; at most three successful alarm/reminder actions per opening |
| Reminder interval | 5 minutes |
| Title | `Fensteralarm` |

For lights, select ON; the return state is then OFF. Delay and reminder interval are in minutes, with a minimum of one. Additional reminders must be an integer from 0 to 20. Source and alarm Items must differ. Each alarm Item must be managed by exactly one responsible rule.

Both Blockly action areas use the existing current-alarm value block for message, title, and identity:

- **Alarm/reminder:** runs after the delay and for configured reminders; event kind is `NEW` or `REMINDER`.
- **Clearance:** runs once when a confirmed return state ends a previously active alarm. The message already contains suitable clearance text; event kind is `CLEARED`.

For light alarms (`ON`/`OFF`), the clearance message includes the total time since
the light was first observed ON, in completed minutes: for example,
`Abstellkammer wurde nach 23 Minuten ausgeschaltet.` Reminders do not reset this
duration. After a script reload or restart, an already active alarm has no known
start time; its clearance uses `mehr als 15 Minuten` instead (with the configured
delay). Window clearance messages remain unchanged. Failed clearance actions
retain the duration measured when OFF was first confirmed.

The block sends no notifications and starts no Alexa rule itself. Those actions remain visible in the two statement areas. Identity is the alarm Item name, suitable as a stable push reference. Alarm states use `postUpdate` only when changed. There are no regular info logs; unexpected execution failures are logged as errors.

#### Behavior and state

- An initial active state starts one timer. Further evaluations of the same state do not postpone its deadline.
- Closing or switching off cancels the source's timer. Only a genuinely active alarm generates clearance.
- Before each timed message, the source is reread. A contact closed since the last trigger therefore produces no open-window warning even if its closing trigger was missed.
- `NULL`, `UNDEF`, and unexpected states produce neither new warnings nor clearance. An untriggered warning starts a full new delay after valid active data returns. Existing alarms remain; due reminders retry missing source data after one minute.
- Timers and execution state live in the private script cache. Reload/restart restarts a pending delay. A persisted alarm Item already ON stays active without replaying old messages or granting a new reminder budget. The next confirmed return state still clears it.
- If action statements throw, execution retries after one minute while the event still applies. Exactly-once external delivery is not guaranteed: a successful push can repeat if a later action fails. Stable push references limit duplicate entries.
- A failed clearance action is discarded if the source becomes active again before retry.

Temperature thresholds use the separate temperature-window block below. The
ordinary Contact/Switch block does not evaluate temperatures.

#### Example setup

Choose your own Contact Item, Switch alarm Item, delay and reminder settings.
Trigger the rule on source state changes and optionally at system start.
Configure notification actions in the block's action areas; no external speech
rule is required. The generator in `tools/state-alarms/` uses synthetic Item names.

### Temperature-dependent windows

The **Fenster temperaturabhängig überwachen** block is part of this same library.
It manages one Contact Item and one dedicated Switch alarm Item. It does not
replace existing rules automatically. Install this updated YAML before converting
any rule; keep exactly one responsible rule/block per alarm Item.

| Input | Meaning |
| --- | --- |
| Window Item | Contact Item with `OPEN` / `CLOSED` states. |
| Temperature Item | `Number:Temperature`, converted to °C; a plain `Number` is interpreted as °C. |
| Temperature limit | Numeric value in °C, or a connected Blockly expression returning a number. |
| Alarm Item | Dedicated Switch Item, different from the window and temperature Items. |
| Delay | Minutes continuously observed OPEN with temperature at or below the limit; minimum 1. |
| Additional reminders | 0–20; 2 means at most three successful alarm/reminder callbacks. |
| Reminder interval | Minutes between successful callbacks; minimum 1. |
| Title | Title returned by the current-alarm value block. |

The two action areas work with **aktueller Alarm → Meldung / Titel / Kennung**,
just like the ordinary state-monitor block. The identity is the alarm Item name;
event kind is `NEW`, `REMINDER` or `CLEARED`. Push, speech, recipients, icons and
references remain caller choices. This block itself never sends notifications.

#### Conditions and clearance

- An open window starts the delay only when temperature is **at or below** the
  limit. Equality matches the old temperature rules.
- Temperature falling to the limit while the window is already open starts the
  full delay. Further qualifying changes do not postpone it.
- Closing the window or temperature rising **above** the limit cancels the
  countdown and reminders. A later qualifying condition starts a new full delay.
  No hysteresis is applied; every crossing of the limit ends/starts a cycle.
- Only an active alarm produces clearance. Window closure says the window is
  closed. Temperature clearance explicitly says that the window is **still open**
  and reports the temperature and current limit. After a temperature clearance,
  closing the window produces no second clearance for that cycle.
- Before a timed action, the block re-reads the contact, temperature and limit.
  A missed close/warm-up trigger therefore cannot produce a stale warning.
- Alarm messages measure completed minutes from the start of the qualifying
  cold/open condition, which can be later than the window's opening. They include
  the current temperature and current limit.

Connect seasonal/setpoint logic **directly to the temperature-limit input**.
The generator wraps that expression in a function; it is evaluated only for an
open window and again before each timed action. For example, a Blockly conditional
expression can return `20.5` in winter and `18` otherwise. An Item-based setpoint
expression must return a finite number in °C. Avoid a variable calculated once
before the monitor: a timer would retain that old value. The expression must
only read/compute a value, without side effects.

#### Runtime and triggers

Use **state-change** triggers for the window and temperature Items, plus each Item
read by the limit expression (for example season or thermostat setpoint). Add a
system-start trigger after restored states are available. Do not use a cron
trigger, an every-update trigger or the alarm Item itself as a trigger. Connecting
an Item or expression in Blockly does not create these rule triggers.

The block is event-driven: there are no group scans, persistence queries, sleeps,
background intervals or periodic baseline checks. With a closed window, it only
reads the contact and alarm, and never reads temperature or evaluates the limit.
An inactive closed/warm window keeps no timer. A qualifying window keeps at most
one timer, reused across source events, until the next deadline/reminder. Only
changed alarm states are posted; there are no normal info logs. State is kept in
the script-private cache without JSON serialization on each event.

Temperature state changes still invoke the containing rule, even with the window
closed; the early return reduces its work rather than eliminating that invocation.
These are structural safeguards, not a measurement of CPU use on the live server.

Unknown contact states, invalid temperature/units and invalid limits generate no
alarm or clearance. They cancel timers instead of polling for recovery. A pending
first warning starts a fresh full delay when valid data returns through a rule
trigger. An already active alarm and its remaining reminder budget are retained;
valid data resumes the budget, without replaying elapsed reminders. A confirmed
closed contact can clear an alarm even if the temperature/limit is unavailable.

Script reload/restart loses pending delays and starts a fresh delay for a cold,
open window whose alarm is OFF. A restored alarm already ON is retained without
replaying notifications or granting reminders; closure or warm-up still clears it.
Failed action callbacks retry after one minute using the same single timer, only
while the event still applies. Missing data suspends retries until a new event.
Reopening into a cold condition discards a pending failed clearance. Callback
failures can duplicate external actions if an earlier action already succeeded;
use stable notification references. Unexpected timer failures are logged without
creating an automatic error polling loop.

#### Build and offline verification

The generator updates the state/temperature sections of this YAML and writes
synthetic Blockly examples and a JSON library export into the supplied directory:

```bash
python3 tools/state-alarms/build.py /tmp/openhab-state-alarms
node tools/state-alarms/check.cjs /tmp/openhab-state-alarms/library.json
```

The checks run both JavaScript sources and their generated YAML utilities with
virtual Items and time. They also expand and execute the new block's code template.
Coverage includes fixed deadlines, bounded reminders, dynamic limits, °C/°F/K,
invalid data, independent windows, cancelled callbacks, restored alarms, callback
failures and distinct closure/warm-up messages. A resource check executes 1,000
closed-window evaluations without temperature/limit reads, timers, writes or
messages. Ordinary state-monitor checks guard the existing window/light behavior.
This new block has not yet been validated in the live MainUI Blockly generator or
with real notifications. Converting an existing temperature rule requires an
explicit migration after the updated library has been installed.

### Alarm data (`Alarmdaten`)

Describes one alarm, with values supplied by normal Blockly blocks:

| Input | Meaning |
| --- | --- |
| Identity (`Kennung`) | Stable identity, e.g. `fenster-kueche`; must not depend on position in a list. |
| Active (`aktiv`) | Boolean or raw `ON` / `OFF`, `OPEN` / `CLOSED`. Unknown/missing states stop the entire group evaluation. |
| Title (`Titel`) | Title of the active alarm. |
| Message (`Meldung`) | Message of the active alarm. |
| Additional comparison value | Optional text affecting change detection, e.g. severity and validity times. |

Inactive entries need no populated title/message. An active entry with missing, NULL or UNDEF title/message also stops evaluation, retaining the previous snapshot.

### Alarm group (`Alarmgruppe`)

Accepts a group key, a standard Blockly list of `Alarmdaten`, and an optional String Item name for persistent memory. Insert **Lists → create list with** into the list input, and put each `Alarmdaten` block inside that list. This also applies when there is only one alarm. Individual alarm entries now have their own output type to prevent connecting them directly to the list input. The list must be a **complete snapshot** of this alarm group. An empty list clears all previously active alarms; it must never be used to represent unavailable source data. Use an entry with unknown active state to suspend evaluation instead.

The three statement areas are:

- **bei neuem Alarm**: runs for every newly active identity.
- **bei geändertem Alarm**: runs if title, message or comparison text changed.
- **bei Entwarnung**: runs for every identity no longer active.

Changing list order does not generate messages. Identical active entries do not generate messages again. Duplicate active identities are rejected before actions run. Changes in whitespace are considered changes; normalize source text if that is undesirable.

Place push blocks and script invocation blocks **inside the appropriate area**, rather than unconditionally after the group block. These areas run synchronously. Keep all activities for one group in one block in one script action; reusing a key in multiple script actions creates separate memories. Do not recursively evaluate the same group from its own callbacks.

### Current alarm (`aktueller Alarm`)

A value block available inside each statement area. Select message, title, stable ID, event kind (`NEW`, `CHANGED`, `CLEARED`), group key, previous message/title, or comparison value. Outside these areas the block returns an empty string.

At clearance, title/message refer to the former alarm, not to an automatically composed all-clear message. Compose an appropriate message yourself. A clearance of one entry is not an all-clear for the complete group.

## Notification actions

A push notification block can use **aktueller Alarm → Meldung**, and optionally
**Titel**, as inputs. Group and identity can build a notification reference.
Recipients, icons and page actions remain caller choices. To call another rule,
select your own rule UID and supply its expected parameters. No private rule UID
or speech schedule is required by the library.

## State and optional persistence

Without a memory Item, the library uses a rule/script-private cache. It survives normal executions but is lost when the script is reloaded or openHAB restarts. Currently active alarms are then considered new. See [JavaScript Scripting cache](https://www.openhab.org/addons/automation/jsscripting/#cache).

For restart recovery, create a dedicated String Item per alarm group, pass its Item name as the memory input, and configure persistence with `everyChange` and `restoreOnStartup`. Wait for restored memory and complete source data before the first evaluation. An uninitialized memory Item starts with no known alarms; malformed saved JSON causes an error without dispatching messages. Do not trigger the rule from changes to its own memory Item.

The library stores JSON text, not shared JavaScript objects. State is committed after each event's synchronous statements return normally. A thrown exception leaves that event pending for a later evaluation. Earlier successful events remain committed. This does not confirm push delivery or Alexa playback, provide an autonomous retry timer, or guarantee exactly-once external delivery. If push succeeds and a later action throws, a later evaluation may retry both. Use notification references where suitable. If storing the optional memory Item fails, cache state may already reflect the event; after a reload the older persisted state may be replayed.

## Validation status

Offline checks cover new/changed/cleared events, unchanged messages, list reordering, unknown states, duplicate identities, action exceptions and retries on the next evaluation, special object-key names, optional memory recovery and invalid memory types/content. Generated code templates were also expanded and executed with mocked openHAB APIs.

The extended file-based library was loaded and checked on openHAB 5.2.3. A triggerless native test with an active synthetic warning passed, including date formatting and snapshot processing, with no push or Alexa actions. The final rule was saved through REST, opened successfully in Blockly, regenerated with the installed Blockly generator and saved in MainUI.

The configurable DWD presentation blocks passed 59 assertions in the installed
runtime, including captured delivery calls from the native-generated rule. On
13 November 2026, a separately requested one-shot test sent the current frost
warning through push and the existing Echo announcement group. The user
confirmed that the iPhone displayed the complete shortened message and Alexa
read it correctly. Instructions were disabled on both channels.

## openHAB 5.2.3 code generation fix

Both value blocks omit the optional `BlockCodeTemplate.config.order`. In openHAB 5.2.3, a named order is looked up under `javascriptGenerator.forBlock`, which returns an undefined order for `ORDER_ATOMIC` and causes Blockly to reject the generated value. Omitting it selects the supported numeric `javascriptGenerator.ORDER_NONE` default. Both expressions are already explicitly parenthesized. See the [5.2.3 generator implementation](https://github.com/openhab/openhab-webui/blob/5.2.3/bundles/org.openhab.ui/web/src/assets/definitions/blockly/libraries.js).

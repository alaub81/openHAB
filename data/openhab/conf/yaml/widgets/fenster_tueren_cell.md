# Windows and doors as a grid cell

File-based MainUI definition `fenster_tueren_cell.yml`, `version: 1`. Copy it to `$OPENHAB_CONF/yaml/widgets/`. It uses the standard 120-pixel `oh-cell` height inside `oh-grid-cells`.

## Display

- Counts open contacts, distinct assigned active alarms, and unknown states.
- Shows three prioritized entries: active alarms, open contacts, then unknown states. Additional entries are indicated by `+N weitere`.
- The compact list uses smaller text, 14-pixel icons, and a lower footer. Height remains 120 pixels; long names can wrap to two lines.
- A closed contact with an active alarm remains visible.
- Shared room alarms count once per alarm Item, even if multiple contacts use it.
- The window-closing advisory is shown separately. The aggregate alarm is considered without assigning it indiscriminately to every contact.
- Tapping opens the native expanded cell with all contacts, full names, and states. Contacts without an alarm assignment explicitly indicate that they have no individual alarm.
- Active alarm means the current alarm Item state; it does not prove historical triggering or message delivery.
- Startup uses a neutral loading indicator. MainUI's temporary `-` does not produce misleading unknown-contact rows. Real `NULL`/`UNDEF` states remain unknown; known open contacts and alarms can appear while other states load.

## Semantic icon selection

`metadata.contactOverview.config.kind` on each Contact Item specifies `window`, `door`, or `contact`. The current 14 windows and two doors were derived from their actual semantic equipment groups: `Window` maps to `window`; `Door`, `FrontDoor`, and `BackDoor` map to `door`. No Item-name patterns are used. Missing/invalid assignments use a neutral icon.

This removes a separate REST query for equipment groups. Technical group `Fenster_Uebersicht_Equipment` remains. The old `equipmentGroup` parameter is still accepted for compatibility but is no longer queried. Semantic parent relationships, alarm assignments, and rules were unchanged by this optimization.

Add new contacts to the contact group and set their alarm assignment and semantic icon type in `contactOverview`. The historical assignment snapshot is archived locally at `archive/scripts-cleanup-20261108/window-widget/contact-metadata.json`; current assignments are maintained in the Contact Items' `contactOverview` metadata. Reload after changing members or display metadata. Live states continue to follow MainUI's Item store.

## Alarm assignment

Each Contact Item uses the `contactOverview` namespace:

```yaml
value: BadOG_Fenster_Alarm
config:
  shared: false
  kind: window
```

`value` names the alarm Item. `shared: true` marks a shared room alarm. `kind` controls only the icon. Optional `config.label` supplies a shorter label. Without metadata, no individual alarm is assumed.

| Contact | Alarm Item | Dedicated rule |
| --- | --- | --- |
| Bathroom | `BadOG_Fenster_Alarm` | Active |
| Attic bathroom | `BadDG_Fenster_Alarm` | Active |
| Hobby room | `Hobbyraum_Fenster_Alarm` | Active |
| Utility room | `Technikraum_Fenster_Alarm` | Active |
| Entrance door | `Eingang_Tuer_Alarm` | Active |
| Bedroom left | `Schlafzimmer_Fenster_links_Alarm` | Active |
| Bedroom right | `Schlafzimmer_Fenster_rechts_Alarm` | Active |
| Children's room left | `Kinderzimmer_Fenster_links_Alarm` | Active |
| Children's room right | `Kinderzimmer_Fenster_rechts_Alarm` | Active |
| Kitchen | `Kueche_Fenster_Alarm` | Active, state monitor block |
| Office left | `Buero_Fenster_links_Alarm` | Active, state monitor block |
| Office right | `Buero_Fenster_rechts_Alarm` | Active, state monitor block |
| Linus's room left | `Linuszimmer_Fenster_links_Alarm` | Active, state monitor block |
| Linus's room right | `Linuszimmer_Fenster_rechts_Alarm` | Active, state monitor block |
| Dining room | `Esszimmer_Fenster_Alarm` | Active, state monitor block |
| Patio door | `Terrasse_Tuer_Alarm` | Active, state monitor block |

All 16 contacts have separate alarm Items and `shared: false`. Left/right bedroom and children's-room rules use separate Items, timer keys, and notification references. Children's-room warnings occur after 15 minutes, followed by two reminders five minutes apart.

All 16 contacts now have active dedicated rules. The six newly configured office-left/right, Linus-left/right, dining-room, and patio-door rules warn after 30 minutes, then 10 and 20 minutes later if still open. Closing cancels that contact's timer and active alarm. Other existing rules and timings were unchanged. The general close-windows advisory operates independently.

## Overview configuration

```yaml
component: widget:fenster_tueren_cell
config:
  title: Fenster & Türen
  contactGroup: Fenster_ALL
  alarmGroupItem: Fenster_Alarm_ALL
  closeAlarmItem: Fenster_Schliessen_Alarm
  testMode: live
```

At the user's request, the new cell is inserted directly after the existing `oh-label-cell` for `Fenster_ALL`. The old cell remains.

## Tests

`testMode` accepts `live`, `mixed`, `closed`, `unknown`, and `loading`. Only the four explicitly selected sample modes generate demo data. Missing, invalid, or temporarily unavailable parameters never activate a demo. Samples are marked `TEST` and change no contacts or alarm Items.

Checks cover all 16 real contacts, both semantic doors, targeted assignments, shared-alarm counting, real unknowns, and closed contacts with active alarms. Isolated expression tests distinguish cold start, loaded contacts with pending alarm states, complete state, and actual alarms. Five browser previews showed live, closed, open/alarmed, unknown, and deliberate loading states. Checks also used a 390-pixel screen with roughly 175-pixel cards: height remained 120 pixels and long names wrapped to two lines.

## Loading and performance

- The closed cell makes one contact-group query with `fetchMetadata: contactOverview`, replacing two sequential equipment/contact queries. Native details mount on opening and also need only one contact-group query.
- The contact list is converted once into a display model. Text, counts, colors, and prioritized entries reuse it rather than repeatedly rebuilding and sorting the list.
- Each Item read requests the reactive MainUI proxy once. For 16 closed contacts, the isolated actual-binding comparison reduced proxy reads per evaluation from 1,269 to 38. This does not measure total mobile-app load time.
- Initial rendering is a neutral loading indication rather than a premature all-clear. The summary appears when required states arrive; real unknowns and known alarms remain visible.
- Native opening animation is disabled. Browser checks then immediately showed the expanded title and all 16 contacts without waiting for an animation-completion event. The background fades on opening and does not intercept detail-view input.
- The widget remains file-based. Generator and regression test are `tools/window-widget/build.py` and `verify.js`. Background and detail views retain separate local contexts using the same small helper functions.

Actual loading still depends on REST/SSE connectivity and the mobile WebView. Already-open clients must reload the Overview once to use the updated widget file.

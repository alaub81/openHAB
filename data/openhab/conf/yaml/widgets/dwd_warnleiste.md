# DWD warning strip

A narrow, responsive warning list for openHAB MainUI. Each warning expands independently to show its headline, description, and optional instructions. Up to five slots are available, with all Items selected in the instance configuration.

## Setup

1. Copy `dwd_warnleiste.yml` to `$OPENHAB_CONF/yaml/widgets/`. Like the other widgets, it uses the file-based `version: 1` / `widgets:` format.
2. Reload MainUI if necessary and add the personal widget `dwd_warnleiste` to a layout page.
3. Select the eight Items for each required warning slot. Leave unused slots empty. A slot is considered only if its alarm Item is selected.
4. Keep test mode set to live, or return to live after previewing samples.

The default `full` view needs a sufficiently wide column on a responsive layout page. Height must grow with warnings and expanded text. A small fixed-height cell can clip long text; a responsive row is a suitable initial test location on the Pi and iPhone.

The complete file is for file-based installation. For manual creation in the developer widget editor, use only the contents beneath `widgets: dwd_warnleiste:`, remove four leading spaces, and prepend `uid: dwd_warnleiste`. Do not create both variants with the same ID.

## Item mapping per slot

| Setting | DWD channel | Type |
| --- | --- | --- |
| Warning present | `warningN` | Switch |
| Event | `eventN` | String |
| Severity | `severityN` | String |
| Valid from | `onsetN` | DateTime |
| Valid to | `expiresN` | DateTime |
| Headline | `headlineN` | String |
| Description | `descriptionN` | String |
| Instruction | `instructionN` | String |

`N` is the slot number. `ON` means the binding provides a warning; its validity may still begin in the future. The widget displays that interval and removes warnings based on the alarm Item, without its own expiry calculation.

## Behavior

- Only ON slots are displayed; OFF slots consume no space.
- Order is Extreme, Severe, Moderate, Minor, then onset time within a level.
- Colors are violet, red, orange, and yellow respectively; severity also appears as text.
- Event keywords select icons. Thunderstorms take priority over accompanying rain or wind; unknown events use a warning triangle.
- Long thunderstorm titles are shortened; other event titles wrap. The original headline remains in the expanded content.
- Advance information is labeled `Vorabinfo`.
- Description and instruction paragraphs are preserved. Empty instructions are hidden.
- Missing, `NULL`, or `UNDEF` alarm states produce an availability hint, never an all-clear.
- When all configured alarm Items are OFF, the no-active-warnings message appears.
- No Item commands, rules, or additional groups are required.

## Testing

Test mode provides zero, one, two, or five clearly labeled samples without changing Items. Samples work even before Items are selected.

1. One warning: open and close its single row.
2. Two warnings: open independently; the frost sample must hide its empty instruction section.
3. Five warnings: verify highest severity first, long events, paragraphs, and advance information.
4. No warnings: verify the compact all-clear row.
5. Check wrapping and complete expanded text on the 7-inch display and iOS app.
6. Return to live and select the real Items.

Local checks covered YAML, expressions with ON/OFF/UNDEF mock states, sample counts, sorting, combined thunderstorm events, unknown events, and invalid times. Expression tests used JavaScript with a simplified date function, not MainUI's parser. The initial local validation did not cover rendering, touch, or live integration; subsequent browser checks are recorded below.

References: [YAML configuration](https://www.openhab.org/docs/configuration/yaml/), [widget context](https://www.openhab.org/docs/ui/components/oh-context.html), [DWD warning events](https://www.dwd.de/DE/leistungen/opendata/help/warnungen/warning_codes_pdf.pdf?__blob=publicationFile&v=6).

## Fix dated 2026-10-25

Helpers now receive dependencies explicitly: functions in the same `oh-context` cannot call each other through `fn`. Styles are on the widget root with relative selectors for MainUI CSS scoping. Live display and expansion were checked in the browser.

The user transferred the corrected canonical file. The Overview again uses `widget:dwd_warnleiste`, retaining all 40 Item assignments and live mode. Browser checks covered an active wind-gust warning, formatting, and independently expandable descriptions/instructions. The temporary UI-managed `dwd_warnleiste_livefix` copy is no longer used on the Overview.

## Dashboard spacing

The outer card follows normal MainUI margins and theme corner rounding. The previous `margin: 0` and fixed `--f7-card-border-radius: 16px` were removed so the strip aligns with the other dashboard cards.

## Fixed display views

The same widget supports three `displayMode` values. Existing instances default
to `full` and retain their expandable warning list.

| Mode | Intended use | Visible warnings | Recommended canvas height |
| --- | --- | --- | --- |
| `full` | Responsive pages and warning details | All five slots, individually expandable | Automatic |
| `overview` | Entrance display | Three highest-priority warnings | 345 px |
| `compact` | Office display | Three highest-priority warnings | 168 px |

Display views automatically fill their canvas item's height. Resize the canvas
item directly in the Page designer or change its `h` value in Page YAML. For
three readable rows, about 345 px for the overview and 168 px for compact mode
are recommended, with widths of at least 295 and 222 px respectively. Smaller
canvas areas remain resizable but may clip warning content. Display modes use zero outer margin and preserve theme rounding,
background, warning colors and event icons. Overview titles occupy up to two lines; compact titles occupy one line with
ellipsis. Compact periods omit today’s date and shorten future intervals;
additional warnings are counted in the footer. Short views show the end time
and include the start time for warnings that have not begun yet. They do not
filter out lower warning levels.

Tap the display card to open `widget:dwd_warnleiste` in a popup using `full`
mode. All 40 Item selections, title and test mode are forwarded explicitly.
The dashboard card follows its canvas height while the popup provides the
complete warning list and expandable official text. Missing alarm states are
kept distinct from a confirmed all-clear, including when other slots are ON.

Configure existing instances with these additional properties:

```yaml
# Entrance canvas item: 295 x 345 px
component: widget:dwd_warnleiste
config:
  displayMode: overview
  # Retain the existing title, testMode and warning-slot Item selections.
```

```yaml
# Office canvas item: 222 x 168 px
component: widget:dwd_warnleiste
config:
  title: DWD
  displayMode: compact
  # Configure all required warning slots, as in the full view.
```

The display instance still needs its alarm Items; these short examples only
illustrate presentation settings. `testMode` continues to provide synthetic
preview data without issuing Item commands. Run
`./tests/test-check.sh` for the widget's synthetic behavior checks.

### Deployment dated 2026-11-21

The live `page_eingang` instance uses `overview` in its existing 295 x 345 px
canvas area. The `buero` warning label was replaced by `compact` in the existing
222 x 168 px area, using the same five warning-slot mappings as the entrance.
The UI-managed pages retain their layout and other controls. The canonical
widget remains file-managed. The original widget and both page definitions are
backed up on the deployment host under
`/opt/openhab5/backups/dwd-display-20261121/`.

Browser validation covered the entrance at 800 x 480 CSS pixels and the office
at 1024 x 600 with the sidebar closed. A temporary hidden preview page verified
five warnings, long titles, future start/end times, all-clear and unavailable
states. Both display bodies fit without vertical overflow at their configured
sizes. Tapping the compact five-warning sample showed all five warnings in the
full popup; both live pages opened the current warning details. The preview page
was removed afterward, and both production instances remain in live mode.

YAML/Compose validation, source checks and synthetic JavaScript checks passed.
The wrapper's exact Node version gate requires 24.22.1; these checks were run
through their Python entry points using the available Node 24.22.3 runtime.

### Three-row display refinement

Both display views now show up to three warnings; a five-warning state displays
`+2 weitere`. The overview uses 18 px event text with smaller icons and spacing.
Compact mode uses 14 px single-line event titles, 22 px icons and 10 px time
labels. Long compact titles use ellipsis and remain complete in the full popup.
Future intervals retain both endpoints, using `Ab 17:00 – morgen 07:00` rather
than repeating the longer date labels. The configured canvas dimensions and
full view are unchanged. Browser checks with five synthetic warnings confirmed
three rows fit within both 295 x 345 and 222 x 168 px cards without body overflow.

### Canvas-controlled display height

Both display views now use `height: 100%` on the outer card and inner summary,
with zero minimum height on the outer card. The `displayHeight` parameter was
removed from the widget editor and the entrance/office instances; old saved
values are ignored. The full list and popup retain automatic height. An unsaved
office editor preview verified 168 → 204 → 168 px resizing with the card and
summary matching the canvas at both heights. The saved canvas areas remain
unchanged, and no DWD widget was added to the living room.

### Automatic display typography and icons

The canvas-sized display card is a CSS size-query container. Overview and
compact views derive a bounded scale from both its width and height, then apply
that scale to headings, time labels, counts, weather/status icons, padding and
gaps. Compact event text ranges from about 11 to 19 px and overview text from
14 to 25 px. Width limits prevent excessively large content in narrow cards.
The full list and popup retain their existing typography.

A temporary preview verified three warning rows with five synthetic warnings
in compact cards at 222 x 130, 222 x 168, 222 x 204 and 300 x 240 px, plus overview
cards at 295 x 260, 295 x 345 and 400 x 450 px. All displayed rows stayed inside
their body area. The 168-to-204 px compact comparison increased event text from
about 14 to 17 px and icons from 22 to 27 px without changing widget settings.

### Theme-aware readability

Full, overview and compact modes use shared theme-aware secondary text colors.
Warning levels, timestamps and the display footer blend 85% of the theme text
color with 15% of the card background, at medium font weight and full opacity.
The count badge and full-view warning outlines also follow the current theme.
Severity colors, icons, layout, automatic sizing and warning behavior remain
unchanged.

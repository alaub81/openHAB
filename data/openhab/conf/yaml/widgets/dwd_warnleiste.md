# DWD warning strip

A narrow, responsive warning list for openHAB MainUI. Each warning expands independently to show its headline, description, and optional instructions. Up to five slots are available, with all Items selected in the instance configuration.

## Setup

1. Copy `dwd_warnleiste.yml` to `$OPENHAB_CONF/yaml/widgets/`. Like the other widgets, it uses the file-based `version: 1` / `widgets:` format.
2. Reload MainUI if necessary and add the personal widget `dwd_warnleiste` to a layout page.
3. Select the eight Items for each required warning slot. Leave unused slots empty. A slot is considered only if its alarm Item is selected.
4. Keep test mode set to live, or return to live after previewing samples.

Use a sufficiently wide column on a responsive layout page. Height must grow with warnings and expanded text. A small fixed-height cell can clip long text; a responsive row is a suitable initial test location on the Pi and iPhone.

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

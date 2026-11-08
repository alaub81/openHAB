# DWD pollen strip

A MainUI widget styled like the DWD warning strip, using normal card margins and corners. Eight pollen types are prepared: alder, hazel, ash, birch, grasses, rye, mugwort, and ambrosia.

## Installation

1. Copy `dwd_pollenleiste.yml` to `$OPENHAB_CONF/yaml/widgets/`.
2. Reload MainUI and add personal widget `dwd_pollenleiste` to a layout page.
3. Select today's Item for each required pollen type.
4. Use a full row on a responsive page, allowing height to grow with the expanded summary.

No alarm Switch or extra rule is required. The widget reads pollen Items directly and does not change the existing pollen alarm rule or `Pollen_Alarm`.

## Behavior

- By default, types with exposure on any configured day are shown. Highest exposure sorts first; ties favor the earlier day. `0-1` is included as possible low exposure.
- Known zero values for all types produce a no-exposure-reported message.
- Missing, invalid, and `-1` values mean no data, never zero exposure.
- Partial availability produces a hint. If the remaining types report zero, the statement explicitly applies only to available types.
- The expand-all control includes unexposed and unknown types. An optional setting includes all selected types directly in the main list.
- Colors indicate index levels, with accompanying text. They are display categories, not medical thresholds.

## Optional forecast

The binding supplies `today`, `tomorrow`, and `dayafter_to` for each type. Tomorrow and day-after-tomorrow Items are optional. A column appears if at least one Item is assigned for that day; missing readings for other types then show no data.

Types with exposure only on a future day are also included. Color and main text use the highest-exposure day, with earlier days winning ties. Values for today and configured future days appear below. The complete table includes every configured type, even when today's exposure is zero.

## Optional source timestamp

`updatedItem` may be a DateTime Item linked to bridge channel `updates#last_update`. The widget shows the DWD publication time and flags a date other than today. Without it, source freshness cannot be assessed. This is not a local fetch timestamp.

## Supported Item states

Raw values are `0`, `0-1`, `1`, `1-2`, `2`, `2-3`, and `3`: none, none-to-low, low, low-to-moderate, moderate, moderate-to-high, and high.

Translated states such as `keine (0)` or `gering bis mittel (1-2)` are supported when the index is in trailing parentheses. `-1`, `NULL`, `UNDEF`, unselected Items, and invalid values count as missing data. Descriptive text without an index is not guessed.

Reference: [DWD Pollenflug binding](https://www.openhab.org/addons/bindings/dwdpollenflug/).

## Existing Item configuration

All eight today Items already exist in this installation. Add this instance after loading the widget file:

```yaml
component: widget:dwd_pollenleiste
config:
  title: DWD Pollenflug
  location: Zuhause
  testMode: live
  alderToday: DWD_Pollenflugindex_home_Alder_Today
  alderTomorrow: DWD_Pollenflugindex_home_Alder_Tomorrow
  alderDayAfter: DWD_Pollenflugindex_home_Alder_Dayafter_To
  hazelToday: DWD_Pollenflugindex_home_Hazel_Today
  hazelTomorrow: DWD_Pollenflugindex_home_Hazel_Tomorrow
  hazelDayAfter: DWD_Pollenflugindex_home_Hazel_Dayafter_To
  ashToday: DWD_Pollenflugindex_home_Ash_Today
  ashTomorrow: DWD_Pollenflugindex_home_Ash_Tomorrow
  ashDayAfter: DWD_Pollenflugindex_home_Ash_Dayafter_To
  birchToday: DWD_Pollenflugindex_home_Birch_Today
  birchTomorrow: DWD_Pollenflugindex_home_Birch_Tomorrow
  birchDayAfter: DWD_Pollenflugindex_home_Birch_Dayafter_To
  grassesToday: DWD_Pollenflugindex_home_Grasses_Today
  grassesTomorrow: DWD_Pollenflugindex_home_Grasses_Tomorrow
  grassesDayAfter: DWD_Pollenflugindex_home_Grasses_Dayafter_To
  ryeToday: DWD_Pollenflugindex_home_Rye_Today
  ryeTomorrow: DWD_Pollenflugindex_home_Rye_Tomorrow
  ryeDayAfter: DWD_Pollenflugindex_home_Rye_Dayafter_To
  mugwortToday: DWD_Pollenflugindex_home_Mugwort_Today
  mugwortTomorrow: DWD_Pollenflugindex_home_Mugwort_Tomorrow
  mugwortDayAfter: DWD_Pollenflugindex_home_Mugwort_Dayafter_To
  ambrosiaToday: DWD_Pollenflugindex_home_Ambrosia_Today
  ambrosiaTomorrow: DWD_Pollenflugindex_home_Ambrosia_Tomorrow
  ambrosiaDayAfter: DWD_Pollenflugindex_home_Ambrosia_Dayafter_To
```

Tomorrow and day-after-tomorrow Items have since been added and assigned on the Overview. Actual day-after-tomorrow names end in `_Dayafter_To`. A DWD publication-time Item remains optional.

## Test modes and validation

`testMode` offers live data, no exposure, mixed exposure, future-only exposure, and missing data. Samples are clearly marked and change no Items.

Local checks covered all seven raw levels, translated values including hyphen variants, unknowns, partial availability, sorting, test modes, and every widget expression. Functions do not refer to siblings in the same `oh-context`; dependencies are passed explicitly.

MainUI rendering was checked with eight live Items and labeled samples. The expanded table fit a 320-pixel column with a 300-pixel card without overflowing cells or horizontal scrolling. Normal MainUI corners (8 pixels in the tested theme) and card margins are used. The temporary preview page was removed. At the user's request, the Overview received the pollen strip directly below the severe-weather warning, with all 24 Items assigned in live mode.

## Persistence

Source Items need no persistence. In particular, `restoreOnStartup` is not recommended: restarting after midnight could otherwise present yesterday's forecast as today's. The binding should supply current states. Separate historical storage without restoration can be configured for later analysis. Other rules' alarm memory is independent.

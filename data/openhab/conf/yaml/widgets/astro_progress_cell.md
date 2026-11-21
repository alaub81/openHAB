# Sun and moon: Cell and Canvas views

`astro_progress_cell.yml` is a file-based MainUI widget definition (`version: 1`). Copy it to `$OPENHAB_CONF/yaml/widgets/`.

The widget uses `oh-cell` at its standard height of 120 pixels inside `oh-grid-cells` on a layout page. Background content follows the normal card spacing and rounded corners. Below 230 pixels of content width, moon times stack vertically; the cell remains 120 pixels high.

## Canvas display mode

The same `astro_progress_cell` definition also supports `displayMode: display`.
In this mode a dedicated card fills 100% of the canvas item's width and height.
Resize the item in the Page designer or change its `w` and `h` values in Page
YAML. There is no separate widget height setting. Existing instances default
to `displayMode: cell` and keep their standard 120 px Cell height.

```yaml
component: widget:astro_progress_cell
config:
  displayMode: display
  # Retain the existing Astro Item selections and optional detailsGroup.
```

Display typography, sunrise/sunset icons, moon icon, arrows, progress thickness,
padding and gaps share a bounded scale derived from both canvas dimensions.
Narrow cards constrain scaling to keep time labels readable. Moon times stack
vertically up to 520 px of canvas width; wider displays place them side by side.
Long sunrise/sunset labels may use ellipsis, while the existing tooltip and
accessible label retain the full date. Normal Cell sizing and layout are
unchanged. Display mode keeps the same colors, dynamic phase icon, percentage
signs and optional group action.

The definition uses one shared expression context for the original Cell and
the display card. Countdown, stale-data handling, timestamps, phase selection
and progress calculations are unchanged; no Items, rules or clock setup change.

## Display

- Sunrise and sunset with the classic `oh:sunrise` and `oh:sunset` icons.
- Remaining daylight during the day, a countdown before sunrise, and a no-more-daylight message after sunset.
- Day length and progress through today's sunrise-to-sunset interval (0–100%).
- A subdued moon row with the dynamic `oh:astro:moon_phase` icon, illuminated percentage, moonrise, and moonset.
- An optional Item group opened by tapping the cell.

Moonrise and moonset use their actual dates. Today's events are not rearranged into an artificial overnight interval. `⁺¹`/`⁻¹` mark the next/previous day; other days show a date. Tomorrow's moonset is never invented by adding 24 hours.

The phase comes from `phase#name`. The percentage is the illuminated fraction of the moon's disc, not measured local illuminance. The binding icon shows eight phase stages, with the precise percentage next to it.

A `+` after the percentage indicates waxing, and `−` indicates waning. The same `moonPhaseItem` supplies the icon and sign: `WAXING_CRESCENT`, `FIRST_QUARTER`, and `WAXING_GIBBOUS` produce `+`; `WANING_GIBBOUS`, `THIRD_QUARTER`, and `WANING_CRESCENT` produce `−`. Full, new, and unknown phases have no sign. Missing percentages show only `—`. No additional Items, rules, or persistence are required. Demo mode shows `75 % +`.

Invalid times appear as `—`. Stale or incomplete sun times are excluded from day length and countdown calculations. Times and events use the display device's local timezone, as configured on that device. Devices should use the same local time.

## Overview configuration

```yaml
component: widget:astro_progress_cell
config:
  title: Sonne & Mond
  detailsGroup: Astro
  sunriseItem: LocalSun_Rise_StartTime
  sunsetItem: LocalSun_Set_StartTime
  moonriseItem: LocalMoon_Rise_StartTime
  moonsetItem: LocalMoon_Set_StartTime
  illuminationItem: LocalMoon_Phase_MoonIllumination
  moonPhaseItem: LocalMoon_Phase_Name
  clockItem: MyClock
  demoMode: false
```

Item selection is configurable; the widget contains no hardcoded installation-specific Item names. The details group is optional.

## Clock and phase Items

Link a String Item to the Astro binding's `phase#name` channel and select it as
`moonPhaseItem`. Configure the other Astro Items for your own location.

## Time from NTP

A regularly updated DateTime Item makes the countdown and progress bar recalculate without navigation. Multiple widgets can share an NTP Item.

1. Link the NTP binding's `dateTime` channel to a DateTime Item.
2. Set `refreshInterval: 60` on the NTP Thing (the default is 60 seconds).
3. Select that Item as `clockItem`; `MyClock` is an example name.

No additional clock rule or persistence is needed. Reference: [NTP binding](https://www.openhab.org/addons/bindings/ntp/).

## Alternative without NTP: clock Item and rule

If you do not use NTP, you can provide your own clock Item and rule:

- DateTime Item `Astro_Widget_Now`, without persistence or semantic tags.
- UI rule `astro_widget_clock` with cron `0 * * * * ?` and system start level 100 triggers.
- A JavaScript action that updates only the clock Item:

```javascript
items.getItem('Astro_Widget_Now').postUpdate(time.ZonedDateTime.now().toString());
```

Run the rule once during setup and select `clockItem: Astro_Widget_Now`. Minute updates then drive the countdown and daily progress. Use only one of the two clock approaches.

## Demo mode and validation

`demoMode: true` displays samples marked `TEST` for the current calendar day at 15:30. It does not change Items. Use `demoMode: false` for live data.

Checks covered daytime, before sunrise, after sunset, stale/missing data, local dates, day rollover, percentages, and the phase icon. Native MainUI checks used card widths of 320 and 175 pixels at 120 pixels high, without horizontal or vertical overflow. On the daylight-saving transition day used for testing, sample times were explicitly constructed as local times.

## Canvas deployment and verification, 2026-11-21

The existing `page_wohnzimmer` instance now uses display mode in its unchanged
199 x 121 px canvas item. The Overview instance remains in default Cell mode;
no Astro widget was added to the entrance or office pages. The original widget
and Wohnzimmer page are backed up on the server under
`/opt/openhab5/backups/astro-display-20261121/`.

A temporary preview covered 160 x 90, 199 x 121, 199 x 160, 260 x 130,
300 x 180 and 420 x 230 px display cards. Card dimensions followed the canvas,
and content stayed within the available bounds. Increasing the 199 px wide
card from 121 to 160 px increased its summary from about 13 to 16 px and the sun
icons from 17 to 21 px. The 420 x 230 px card uses a 22 px summary and 27 px sun
icons. Missing sun data was checked at 260 x 130 px without clipping the hint.
Live checks confirmed the moon icon/percentage, progress and Astro group popup.
The comparison Cell and live Overview retained their original 120 px height.
The temporary preview was removed after validation.

## Theme-aware readability

Cell and display modes use secondary text blended from 85% theme text color
and 15% card background. Day length and moon details use medium font weight
and full opacity, so moon icons are no longer dimmed with the entire row.
The progress track and moon separator also follow the theme. Layout, automatic
sizing, sun color, Item bindings, phase icons and detail actions remain unchanged.

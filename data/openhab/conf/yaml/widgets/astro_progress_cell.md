# Astro progress bar as a grid cell

`astro_progress_cell.yml` is a file-based MainUI widget definition (`version: 1`). Copy it to `$OPENHAB_CONF/yaml/widgets/`.

The widget uses `oh-cell` at its standard height of 120 pixels inside `oh-grid-cells` on a layout page. Background content follows the normal card spacing and rounded corners. Below 230 pixels of content width, moon times stack vertically; the cell remains 120 pixels high.

## Display

- Sunrise and sunset with the classic `oh:sunrise` and `oh:sunset` icons.
- Remaining daylight during the day, a countdown before sunrise, and a no-more-daylight message after sunset.
- Day length and progress through today's sunrise-to-sunset interval (0–100%).
- A subdued moon row with the dynamic `oh:astro:moon_phase` icon, illuminated percentage, moonrise, and moonset.
- An optional Item group opened by tapping the cell.

Moonrise and moonset use their actual dates. Today's events are not rearranged into an artificial overnight interval. `⁺¹`/`⁻¹` mark the next/previous day; other days show a date. Tomorrow's moonset is never invented by adding 24 hours.

The phase comes from `phase#name`. The percentage is the illuminated fraction of the moon's disc, not measured local illuminance. The binding icon shows eight phase stages, with the precise percentage next to it.

A `+` after the percentage indicates waxing, and `−` indicates waning. The same `moonPhaseItem` supplies the icon and sign: `WAXING_CRESCENT`, `FIRST_QUARTER`, and `WAXING_GIBBOUS` produce `+`; `WANING_GIBBOUS`, `THIRD_QUARTER`, and `WANING_CRESCENT` produce `−`. Full, new, and unknown phases have no sign. Missing percentages show only `—`. No additional Items, rules, or persistence are required. Demo mode shows `75 % +`.

Invalid times appear as `—`. Stale or incomplete sun times are excluded from day length and countdown calculations. Times and events use the display device's local timezone, Europe/Amsterdam or Europe/Berlin in this installation. Devices should use the same local time.

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
  clockItem: OU_External_Services_DateTime
  demoMode: false
```

Item selection is configurable; the widget contains no hardcoded installation-specific Item names. The details group is optional.

## Installation-specific additions

- `LocalMoon_Phase_Name`: new String Item linked to `astro:moon:local:phase#name`, in group `Astro`, with `Calculation` + `Info` semantics, no persistence group, and `autoupdate=false`.
- `OU_External_Services_DateTime`: existing DateTime Item linked to `ntp:ntp:local:dateTime`, configured as `clockItem`.

The original five Astro Items remain. The former helper Item `Astro_Widget_Now` and rule `astro_widget_clock` were removed when switching to NTP. The widget definition itself did not change; no replacement widget file is needed for that switch.

## Time from NTP: current setup

A regularly updated DateTime Item makes the countdown and progress bar recalculate without navigation. Multiple widgets can share an NTP Item.

1. Link the NTP binding's `dateTime` channel to a DateTime Item.
2. Set `refreshInterval: 60` on the NTP Thing (the default is 60 seconds).
3. Select that Item as `clockItem`; this installation uses `OU_External_Services_DateTime`.

No additional clock rule or persistence is needed. Reference: [NTP binding](https://www.openhab.org/addons/bindings/ntp/).

## Alternative without NTP: clock Item and rule

This original approach is retained as an alternative and is no longer active here:

- DateTime Item `Astro_Widget_Now`, without persistence or semantic tags.
- UI rule `astro_widget_clock` with cron `0 * * * * ?` and system start level 100 triggers.
- A JavaScript action that updates only the clock Item:

```javascript
items.getItem('Astro_Widget_Now').postUpdate(time.ZonedDateTime.now().toString());
```

Run the rule once during setup and select `clockItem: Astro_Widget_Now`. Minute updates then drive the countdown and daily progress. Use only one of the two clock approaches.

## Demo mode and validation

`demoMode: true` displays samples marked `TEST` for the current calendar day at 15:30. It does not change Items. The Overview uses live mode.

Checks covered daytime, before sunrise, after sunset, stale/missing data, local dates, day rollover, percentages, and the phase icon. Native MainUI checks used card widths of 320 and 175 pixels at 120 pixels high, without horizontal or vertical overflow. On the daylight-saving transition day used for testing, sample times were explicitly constructed as local times.

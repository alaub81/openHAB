# Weather station as a grid cell

Documentation for [`wetterstation_cell.yml`](wetterstation_cell.yml), widget ID `wetterstation_cell_v1`, describing the local version dated 2026-10-26.

The cell displays temperature and supplementary weather data at the standard 120-pixel height. It supports an outdoor station or aggregated indoor readings. Unassigned supplementary fields are hidden.

## Installation

1. Copy the YAML file to `$OPENHAB_CONF/yaml/widgets/`; it already includes `version: 1` and `widgets:`.
2. Reload MainUI.
3. Add the personal widget inside `oh-grid-cells`.
4. Select at least `temperatureItem`, then optional sensors as needed.

The root is `oh-cell`. It does not expand; tapping executes the configured action. Without a custom action, it opens the temperature Item in the Analyzer.

## Display

- Top: title/icon and optional illuminance at the right.
- Main reading: temperature with optional feels-like temperature alongside.
- Optional UV index at the right, with category and color.
- Optional minimum/maximum below, marked `↓`/`↑`.
- Bottom left: humidity, one-hour rainfall, then 24-hour rainfall.
- Bottom right: wind direction/speed, with gust speed below and a separate `f7:tornado` icon.
- Optional background temperature trend.

Temperature and normal reading font sizes depend on cell width, not the number of assigned Items. Equally wide indoor/outdoor cells use the same sizes. Lower measurement rows are 14 pixels high with a one-pixel gap; cell height stays 120 pixels. Gust icons remain visible in narrow cells. The extra gust text is omitted to prioritize the complete reading. Unassigned fields disappear; rain quantities are labeled `1h` and `24h`.

Very long rain values may use smaller text. Some sizes adapt to width, but many long readings can still compete for space. Short formatting and appropriate units improve readability.

## Title and measurements

| Parameter | Value | Function/default |
| --- | --- | --- |
| `title` | Text | Default `Garten`; e.g. `Haus` for indoor view. |
| `icon` | Icon name | Default `oh:temperature`; F7, Material, and Iconify also supported. |
| `iconColor` | Color | Optional for supported icon families; classic OH icons keep their own colors. |
| `temperatureItem` | Temperature Item | Required main reading. |
| `feelsLikeItem` | Feels-like temperature Item | Optional, already calculated by a binding/rule. |
| `minItem` | Minimum Item | Optional minimum. |
| `maxItem` | Maximum Item | Optional maximum. |
| `humidityItem` | Humidity Item | Optional percentage. |
| `luxItem` | Illuminance, e.g. `Number:Illuminance` | Optional top-right reading. |

The widget calculates neither feels-like temperature nor daily extrema. Source Items define the extrema period. Aggregated indoor values also work.

## Rain

| Parameter | Value | Function/default |
| --- | --- | --- |
| `rainItem` | Binary rain state | Whether it is raining, not a quantity. |
| `rainWetState` | Raw state | Rain detected; default `ON`, alternatives include `OPEN` or `1`. |
| `rainDryState` | Raw state | Dry; default `OFF`, alternatives include `CLOSED` or `0`. |
| `rain1hItem` | Rainfall over the last hour | Optional, e.g. millimeters. |
| `rain24hItem` | Rainfall over the last 24 hours | Optional, e.g. millimeters. |

Raw state matching is exact and case-sensitive. Rain uses a blue rain-cloud icon, dry a gray rain-cloud icon, and other/unavailable states a gray question mark. A 24-hour quantity without a binary sensor uses a blue droplet.

With `rain24hItem`, the quantity appears beside the rain/droplet icon; otherwise only the status icon appears. Periods are also provided as tooltips/accessibility text. The one-hour quantity also comes from its Item; the widget calculates no rain totals.

The 24-hour quantity must be a **rolling total over the last 24 hours**, not a lifetime counter or a daily total reset at midnight. The widget does not calculate that rolling sum.

## Wind

| Parameter | Value | Function |
| --- | --- | --- |
| `windSpeedItem` | Speed with desired unit | Numeric part to one decimal; unit retained. |
| `windGustIcon` | Gust icon | Configurable; default `f7:tornado`. |
| `windGustItem` | Gust speed with desired unit | Optional, below speed; one decimal. |
| `windDirectionItem` | Origin as degrees or compass direction | Origin text plus an arrow rotated by 180°. |

For degrees, `0 = N`, `90 = O`, `180 = S`, `270 = W`. Values map to the nearest of 16 German compass abbreviations:

`N, NNO, NO, ONO, O, OSO, SO, SSO, S, SSW, SW, WSW, W, WNW, NW, NNW`.

Text states must use these abbreviations, especially `O` for east. Arrow rotation uses this list. Text gives the meteorological origin; the arrow points **where the wind is going**.

| Origin text | Arrow points |
| --- | --- |
| `N` | South |
| `O` | West |
| `SW` | Northeast |
| `W` | East |

Speed and gust icons are colored independently. A displayed zero or unknown value gives gray; positive values give turquoise. The displayed value rounded to one decimal is decisive. Direction-icon styling is unchanged.

The widget does not convert speed units. Unsupported direction text makes the arrow unreliable; supply appropriate raw degrees or abbreviations.

## UV index

| Parameter | Value | Default |
| --- | --- | --- |
| `uvItem` | Numeric raw index without unit | Hidden if unassigned. |
| `uvIcon` | Icon name | `iconify:mdi:sun-wireless` |
| `uvLowColor` | Low category color | `green` |
| `uvMediumColor` | Moderate category color | `#f1c40f` |
| `uvHighColor` | High category color | `orange` |
| `uvVeryHighColor` | Very high category color | `red` |
| `uvExtremeColor` | Extreme category color | `purple` |

| Index | Category |
| --- | --- |
| 0 to below 3 | Low |
| 3 to below 6 | Moderate |
| 6 to below 8 | High |
| 8 to below 11 | Very high |
| 11 or above | Extreme |

Decimal dots/commas are accepted. Invalid, negative, or unit-bearing raw states show `—` in gray. Valid readings use at most one decimal and a German decimal comma. UI category labels remain German.

## Trend and persistence

| Parameter | Function/default |
| --- | --- |
| `showTrend` | Show/hide trend; default `true`. |
| `trendItem` | Optional alternate history Item; defaults to `temperatureItem`. |
| `trendColor` | First color; default `#2196f3`. |
| `trendColorEnd` | Second gradient color; default `#5ac8fa`. Use equal colors for a solid line. |
| `trendStrokeWidth` | Width; default `3`, dialog range 1–10. |
| `trendOpacity` | Opacity 0–100%; default `20`. |

The `oh-trend` line needs history in the default persistence service. The cell stores no data and has no persistence-service or trend-period parameter.

Current readings need no history. Set `showTrend: false` if no historical storage is wanted. Extrema and rain quantities still depend on their source Items' calculations.

## Tap action

The **Action** parameter group controls the entire cell. By default the temperature Item opens in the Analyzer. An indoor summary can open the temperature group:

```yaml
action: group
actionGroupPopupItem: Temperatur_Innen_ALL
```

Place these settings in the widget instance's `config`. They do not change the displayed sensor readings.

## Existing outdoor station example

These Item names come from the existing garden configuration. Place the instance inside `oh-grid-cells`:

```yaml
component: widget:wetterstation_cell_v1
config:
  title: Garten
  icon: f7:leaf_arrow_circlepath
  iconColor: green
  temperatureItem: Shelly_Wetterstation_Temperature
  feelsLikeItem: Shelly_Wetterstation_Feels_like
  minItem: Shelly_Wetterstation_Temperature_Min
  maxItem: Shelly_Wetterstation_Temperature_Max
  humidityItem: Shelly_Wetterstation_Humidity
  luxItem: Shelly_Wetterstation_Illuminance
  rainItem: Shelly_Wetterstation_Rain_flag
  rainWetState: 'ON'
  rainDryState: 'OFF'
  rain24hItem: Shelly_Wetterstation_Rain_last_24h
  windSpeedItem: Shelly_Wetterstation_Wind_speed_avg
  windDirectionItem: Shelly_Wetterstation_Direction_avg
  uvItem: Shelly_Wetterstation_uvindex
  showTrend: true
  trendColor: '#2196f3'
  trendColorEnd: '#5ac8fa'
  trendStrokeWidth: 3
  trendOpacity: 20
```

## Indoor summary example

```yaml
component: widget:wetterstation_cell_v1
config:
  title: Haus
  icon: f7:house
  iconColor: orange
  temperatureItem: Temperatur_Innen_ALL
  minItem: Temperatur_Innen_ALL_Min
  maxItem: Temperatur_Innen_ALL_Max
  humidityItem: Humidity_Innen_ALL
  luxItem: Innenbeleuchtungsstaerken_ALL
  showTrend: true
  action: group
  actionGroupPopupItem: Temperatur_Innen_ALL
```

## Missing data and icons

Missing Items, empty states, `NULL`, and `UNDEF` appear as `—` in general reading fields. Unassigned optional sections are hidden. Assignment and validity are separate checks: a selected but invalid Item can still show its section with a placeholder.

Classic `oh:` icons come from openHAB; MainUI supports F7/Material icons. Uncached Iconify icons may need internet access on first use.

References: [Grid cells](https://www.openhab.org/docs/ui/building-pages), [icons](https://www.openhab.org/docs/ui/components/oh-icon.html).

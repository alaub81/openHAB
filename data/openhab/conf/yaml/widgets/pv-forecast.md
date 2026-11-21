# PV forecast

`pv_forecast` uses one definition for the expandable Cell view and compact fixed
canvas cards. It reads existing forecast energy Items and compares each day's
forecast with the selected average daily household consumption. It sends no
Item commands.

## Installation and sources

Install `pv-forecast.yml` in `$OPENHAB_CONF/yaml/widgets/`, retaining the `version`
and `widgets` wrapper. Configure `todayItem`, `tomorrowItem`, `day2Item` and
`day3Item` for the available forecast days. `remainingItem` supplies today's
remaining forecast, while `averageItem` supplies the daily household average.
The existing Cell configuration can be copied to display instances.

Energy values may contain kWh, Wh or MWh; unitless values are treated as kWh.
Missing, unavailable, negative and malformed values remain unknown and display
an em dash. Zero is a valid energy value. A missing or zero household average
produces a neutral traffic signal rather than a false red or green signal.
Default daily thresholds are green at 110% and yellow at 70% of the average.
Existing configurable colors, traffic lamps, rounding and thresholds apply to
both views.

## Display selection

| Setting | Behavior |
| --- | --- |
| `displayMode: cell` | Existing expandable Cell; default for existing instances |
| `displayMode: display` | Fixed card without a title/header, with an optional remaining/average footer |
| `startDay: 0` | Begin with today; default |
| `startDay: 1` | Begin with tomorrow |
| `dayCount` | Show 1–4 consecutive available days; default 4 |

Only today through three days from now are available. Starting tomorrow with
`dayCount: 4` therefore shows the three available future days. Invalid counts
fall back to all available days. Day selection also works in Cell mode.

A display card shows the traffic signal, day name and forecast number.
The shared `Prognosen · kWh` footer legend supplies the unit for all values.
The small footer uses the original remaining-forecast and household-average
values, traffic signal and Analyzer links. `showRemaining` and `showAverage`
control its two entries; hiding both also releases the footer space.
It inherits the theme's background and corner rounding, with no outer margin.
The display card fills its canvas item with `height: 100%` and zero minimum
height. Resize the canvas item directly in the Page designer or change that
item’s `h` value in Page YAML; no widget height parameter is needed. A parent
with an explicit height is required in display mode. About 60 px or more is
recommended for readable days and footer. The existing areas are 195 x 80,
402 x 60 and 290 x 70 px. `showTitle` continues to control the Cell title; display mode always
omits the header. German day names are retained and can be overridden with the
existing label properties. Demo mode is marked with `TEST` and changes no Items.

Configure an existing instance as follows, retaining its source selections:

```yaml
component: widget:pv_forecast
config:
  displayMode: display
  startDay: 1
  dayCount: 2
  showTitle: false
  decimals: 0
  dayFontSize: 11
```

Tap a display day to open the Analyzer outside the fixed card. The selected
`forecastChartItems` are used, with `day3ChartItems` taking precedence for the
last day. Without chart Items, the corresponding daily energy Item is used.
The original Cell retains its inline detail selection and separate chart link.

## Deployment and verification, 2026-11-21

The existing forecast compositions were replaced with instances of this widget:

| Page | Existing canvas area | Days |
| --- | --- | --- |
| `page_eingang` | 195 x 80 px | Tomorrow and the following day |
| `buero` | 402 x 60 px | Today plus three future days |
| `page_wohnzimmer` | 290 x 70 px | Today plus three future days |

Each replacement retains the background card's position and dimensions; only
its related forecast labels, values and icons were removed. Other page
components, including DWD displays, were preserved. The Overview Cell retains
its configuration. Server backups of the original widget and all three pages
are under `/opt/openhab5/backups/pv-forecast-display-20261121/`.

Synthetic checks cover energy units, missing states, threshold boundaries, day
selection and display actions. Browser checks cover the three live page sizes,
readable day/value placement and the Analyzer navigation. No display test mode
is enabled on the production pages.

### Today and footer refinement

The entrance continues to start tomorrow with two days. Office and living room
start today and show all four available days. All three instances enable the
remaining-forecast and daily-average footer. Day columns reserve 18 px for this
footer, use reduced line spacing and scale the numeric font with the number of
visible days. The office uses 14 px traffic signals in its 60 px card; the other
displays use 16 px. Browser validation checks that day content and footer fit
without clipping or overlap, retaining each original canvas size.

### Forecast caption

The display footer starts with the existing `material:solar_power` icon in the
footer's muted color. It reads `Prognosen` on all three displays. Remaining forecast and household
average are grouped together at the right edge of the footer. The existing remaining forecast, traffic signal, average and
Analyzer actions are retained. Browser checks confirmed that all footer entries
fit without horizontal overflow in the three deployed card widths.

### Canvas-controlled height

The separate `displayHeight` property has been removed from the widget editor
and the three live page instances. Old saved values are ignored. Display mode
now inherits 100% of its canvas item's height; Cell mode retains automatic
height and its existing 120 px minimum. Browser validation changed only the
office canvas height in an unsaved editor preview from 60 to 96 px, confirmed
that the card matched both sizes, and restored the original 60 px layout.
The entrance and living room retain their original 80 and 70 px canvas heights.

### Automatic display typography and icons

Display mode uses CSS size queries for day names, numbers, traffic signals,
footer text and icons. The scale considers both canvas dimensions and the
number of visible days. Numbers are bounded to 11–22 px and day labels to 9–16
px; narrow columns constrain number size independently. The shared footer caption `Prognosen in kWh` avoids repeating the unit in each column. The footer has its own 8–12
px width/height budget, and its reserved space grows with the text.

The manual day/traffic size settings continue to apply to Cell mode. Display
mode scales automatically, while preserving theme colors, threshold logic,
source selections and Analyzer actions. Original page sizes are unchanged.

Browser checks compared 402 x 60 and 402 x 90 px cards: numbers grew from about
18 to 22 px, and traffic signals remain at least 22 px high in the contrast-enhanced layout. Additional checks covered
195 x 80 px with two future days, 290 x 70 px with four days and zero/one decimal
place, and 520 x 100 px. Day values and footers fit without overflow in these
cases. The temporary preview page was removed after validation.

### Display contrast and shared unit

Display mode derives secondary text from 85% of the current theme/custom text
color and 15% of the current card background. Day labels and footer use medium
weight. In dark mode this produces brighter text, while light mode produces
darker text without hardcoding white. Cell text colors remain unchanged; traffic signals share the display styling.

Day traffic signals now have a minimum height of 22 px with approximately 5 px
lamps, a theme-aware housing border. The active lamp uses its configured status color
with a stronger 4 px glow and a fine outline blended from the status and theme
text colors. The outline stays darker in light mode and lighter in dark mode
to distinguish the active lamp even when the glow is hard to see. No brightness
filter is applied.
The existing `trafficGlow` setting can disable the glow. Inactive lamps remain visible at bounded lower opacity. Unknown signals
stay neutral. The remaining-forecast signal has a 14 px minimum; its reserved
footer space grows with the signal. Configured status colors, thresholds, unit
conversion, missing-data behavior and Analyzer links remain intact.

Each display day places the number vertically centered beside its signal and
the day label on the row below. Day signals scale from 22 to 30 px and the smaller footer signal
from 14 to 18 px; this layout also fits a 60 px high card. The footer reads `Prognosen in kWh`;
individual day, remaining and average numbers omit the repeated unit.
Display values default to one decimal place via `displayDecimals`, independently
of the original Cell `decimals` setting. Tooltips
retain their explicit kWh information. Day count, automatic sizing and page
positions are unchanged. Browser checks covered the deployed 195 x 80,
402 x 66 and 290 x 70 px cards in both dark and light modes, plus green, yellow,
red and unavailable states. The local test browser was restored to Auto mode.

### Shared Cell traffic styling

Cell and display mode use the same theme-aware traffic housing, visible inactive
lamps, neutral unknown state and subtle active glow. Cell day positioning,
configured traffic heights, typography, footer and expansion behavior remain
unchanged. Explicit housing/status colors and `trafficGlow` are respected.

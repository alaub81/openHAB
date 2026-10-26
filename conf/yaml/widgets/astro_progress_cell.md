# Astro Progressbar als Grid-Zelle

`astro_progress_cell.yml` ist eine filebasierte MainUI-Widget-Definition (`version: 1`). Die Datei gehört nach `$OPENHAB_CONF/yaml/widgets/`.

Das Widget verwendet `oh-cell` mit der normalen Höhe von 120 Pixeln. Es gehört in ein `oh-grid-cells` auf einer Layout-Seite. Die Hintergrund-Inhalte übernehmen die normalen Kartenabstände und Rundungen. Unter 230 Pixeln Inhaltsbreite stehen die Mondzeiten untereinander; die Zelle bleibt 120 Pixel hoch.

## Anzeige

- Sonnenaufgang und Sonnenuntergang mit klassischen `oh:sunrise`- und `oh:sunset`-Icons.
- Tagsüber verbleibendes Tageslicht, vor Sonnenaufgang ein Countdown zum Aufgang, danach „Heute kein Tageslicht mehr“.
- Tageslänge und Fortschritt des heutigen Zeitraums zwischen Sonnenaufgang und Sonnenuntergang (0–100 %).
- Dezente Mondzeile mit dem dynamischen Icon `oh:astro:moon_phase`, beleuchtetem Anteil in Prozent, Mondaufgang und Monduntergang.
- Antippen öffnet optional eine konfigurierte Item-Gruppe mit Details.

Mondaufgang und Monduntergang werden jeweils mit ihrem tatsächlichen Datum dargestellt. Die Reihenfolge der heutigen Ereignisse wird nicht zu einem künstlichen Nachtintervall umgedeutet. `⁺¹`/`⁻¹` markieren den Folge-/Vortag; weitere Tage erhalten eine Datumsangabe. Es wird kein morgiger Monduntergang erfunden oder durch Addition von 24 Stunden berechnet.

Die Mondphase kommt aus `phase#name`. Der Prozentwert ist der beleuchtete Anteil der Mondscheibe, keine gemessene Beleuchtungsstärke am Standort. Das Binding-Icon zeigt die entsprechende Phase in acht Stufen; der genaue Prozentwert steht daneben.

Hinter dem Prozentwert zeigt `+` einen zunehmenden Mond an (z. B. `75 % +`), `−` einen abnehmenden Mond (z. B. `75 % −`). Die Zuordnung verwendet dasselbe `moonPhaseItem` wie das Icon: `WAXING_CRESCENT`, `FIRST_QUARTER` und `WAXING_GIBBOUS` ergeben `+`; `WANING_GIBBOUS`, `THIRD_QUARTER` und `WANING_CRESCENT` ergeben `−`. Bei Vollmond, Neumond oder unbekannter Phase entfällt der Zusatz. Fehlt der Prozentwert, erscheint nur `—`. Zusätzliche Items, Regeln oder Persistence sind dafür nicht erforderlich. Im Testmodus erscheint `75 % +`.

Ungültige Zeiten erscheinen als `—`. Veraltete oder unvollständige Sonnenzeiten werden nicht für Tageslänge und Countdown verwendet. Die Uhrzeit und Ereignisse werden in der lokalen Zeitzone des Anzeigegeräts dargestellt; für die vorhandene Installation ist dies Europe/Amsterdam bzw. Europe/Berlin. Die Geräte sollten auf dieselbe Ortszeit eingestellt sein.

## Konfiguration auf der Overview

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

Die Item-Auswahl ist konfigurierbar; im Widget sind keine installationsspezifischen Item-Namen fest hinterlegt. Auch die Details-Gruppe ist optional.

## Ergänzungen in dieser Installation

- `LocalMoon_Phase_Name`: neues String-Item, Channel `astro:moon:local:phase#name`, Gruppe `Astro`, Semantik `Calculation` + `Info`, keine Persistence-Gruppe und `autoupdate=false`.
- `OU_External_Services_DateTime` („NTP Datum und Zeit“): vorhandenes DateTime-Item am Channel `ntp:ntp:local:dateTime`, als `clockItem` konfiguriert.

Die ursprünglichen fünf Astro-Items bleiben erhalten. Das bisherige Hilfs-Item `Astro_Widget_Now` und die Regel `astro_widget_clock` wurden bei der Umstellung auf NTP entfernt. Die Widget-Definition selbst ist unverändert; für die Umstellung muss keine neue Widget-Datei kopiert werden.

## Uhrzeit über NTP – aktuell verwendete Variante

Das Widget benötigt ein regelmäßig aktualisiertes DateTime-Item, damit Countdown und Progressbar auch ohne Seitenwechsel neu berechnet werden. Ein NTP-Item kann von mehreren Widgets gemeinsam verwendet werden.

1. Im NTP-Binding den Channel `dateTime` mit einem DateTime-Item verknüpfen.
2. Am NTP-Thing `refreshInterval: 60` einstellen (Standard: 60 Sekunden).
3. Das Item im Widget unter „Aktuelle Uhrzeit“ beziehungsweise `clockItem` auswählen. In dieser Installation: `OU_External_Services_DateTime`.

Eine zusätzliche Uhrzeitregel ist dann nicht erforderlich. Für dieses Uhrzeit-Item wird keine Persistence benötigt.

Referenz: [NTP-Binding](https://www.openhab.org/addons/bindings/ntp/).

## Alternative ohne NTP: Uhrzeit-Item mit Regel

Diese ursprüngliche Variante bleibt als Alternative dokumentiert und ist in dieser Installation nicht mehr aktiv:

- DateTime-Item `Astro_Widget_Now`, ohne Persistence und ohne semantische Tags.
- UI-Regel `astro_widget_clock` („Astro Widget – Uhrzeit aktualisieren“) mit zwei Triggern: Cron `0 * * * * ?` und System-Startlevel 100.
- JavaScript-Aktion, die ausschließlich das Uhrzeit-Item aktualisiert:

```javascript
items.getItem('Astro_Widget_Now').postUpdate(time.ZonedDateTime.now().toString());
```

Die Regel bei der Einrichtung einmal ausführen und im Widget `clockItem: Astro_Widget_Now` auswählen. Danach sorgen die minütlichen Updates für einen laufenden Countdown und Tagesfortschritt. Es wird jeweils nur eine der beiden Uhrzeit-Varianten benötigt.

## Testmodus

`demoMode: true` zeigt mit „TEST“ gekennzeichnete Beispieldaten am aktuellen Kalendertag um 15:30. Er verändert keine Items. In der Overview ist der Live-Modus konfiguriert.

Geprüft: Tag, vor Sonnenaufgang, nach Sonnenuntergang, veraltete und fehlende Daten, lokales Datum, Tageswechsel, Prozentwerte und das Phasen-Icon. Der native MainUI-Test verwendet 320 und 175 Pixel Kartenbreite bei jeweils 120 Pixel Höhe; kein horizontaler oder vertikaler Überlauf. Auf dem heutigen Zeitumstellungstag werden Test-Uhrzeiten ausdrücklich als lokale Uhrzeiten gesetzt.

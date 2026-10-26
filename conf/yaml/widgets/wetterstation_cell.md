# Wetterstation als Grid-Zelle

Dokumentation zu [`wetterstation_cell.yml`](wetterstation_cell.yml), Widget-ID `wetterstation_cell_v1`. Beschrieben ist der lokale Dateistand vom 26.10.2026.

Die Zelle zeigt Temperatur und ergänzende Wetterdaten auf der normalen openHAB-Zellenhöhe von 120 Pixeln. Sie kann sowohl für eine Außenwetterstation als auch für zusammengefasste Innenwerte verwendet werden. Nicht zugeordnete Zusatzwerte werden ausgeblendet.

## Installation und Einbindung

1. Die YAML-Datei nach `$OPENHAB_CONF/yaml/widgets/` kopieren. Die Datei enthält bereits `version: 1` und den Abschnitt `widgets:`.
2. MainUI neu laden.
3. Das persönliche Widget innerhalb von `oh-grid-cells` hinzufügen.
4. Mindestens `temperatureItem` auswählen, die übrigen Sensoren nach Bedarf ergänzen.

Die Wurzel ist `oh-cell`. Die Zelle ist nicht aufklappbar; Antippen führt die konfigurierte Aktion aus. Ohne eigene Aktion öffnet sie den Analyzer für das Temperatur-Item.

## Anzeige

- Oben: Titel und Icon, rechts optional die Beleuchtungsstärke.
- Hauptwert: Temperatur, daneben optional die gefühlte Temperatur.
- Bei zugeordnetem UV-Item zusätzlich rechts der UV-Index mit Bewertung und Farbe.
- Darunter optional Minimum und Maximum, gekennzeichnet mit `↓` und `↑`.
- Unten links: Luftfeuchtigkeit, Niederschlag der letzten Stunde, danach Niederschlag der letzten 24 Stunden.
- Unten rechts: Windrichtung, Windgeschwindigkeit, darunter Böengeschwindigkeit mit der dezenten Beschriftung `Böen`.
- Optional eine Temperatur-Trendlinie im Hintergrund.

Die Schriftgrößen für Temperatur und normale Messwerte richten sich nach der Zellbreite, nicht nach der Anzahl zugeordneter Items. Gleich breite Haus- und Gartenzellen verwenden dafür dieselben Schriftgrößen. Die unteren Messwertzeilen sind 14 Pixel hoch und haben einen Pixel Abstand. Die Höhe bleibt bei 120 Pixeln. Bei einer inneren Breite bis 190 Pixel entfällt das wiederholte Wind-Icon in der Böenzeile, damit Wert und Beschriftung passen. Nicht zugeordnete Zusatzwerte verschwinden; die Regenmengen sind mit `1h` beziehungsweise `24h` gekennzeichnet.

Sehr lange Niederschlagswerte werden bei Bedarf etwas kleiner dargestellt. Die Schriftgrößen passen sich teilweise an die Breite der Zelle an. Die äußere Kartenhöhe bleibt unverändert. Viele lange Messwerttexte können auf schmalen Zellen dennoch Platz beanspruchen; kurze Formatierungen und passende Einheiten helfen bei der Lesbarkeit.

## Parameter: Titel und Messwerte

| Parameter | Inhalt | Funktion / Standard |
| --- | --- | --- |
| `title` | Text | Titel; Standard `Garten`. Für eine Innenansicht beispielsweise `Haus`. |
| `icon` | Icon-Name | Titel-Icon; Standard `oh:temperature`. Auch F7-, Material- und Iconify-Icons sind möglich. |
| `iconColor` | Farbe | Optionale Farbe für unterstützte Icon-Familien. Klassische OH-Icons behalten ihre eigene Farbe. |
| `temperatureItem` | Temperatur-Item | Großer Hauptwert. Pflichtfeld. |
| `feelsLikeItem` | Item mit gefühlter Temperatur | Optional. Der Wert muss bereits vom Binding oder einer Regel berechnet worden sein. |
| `minItem` | Minimum-Item | Optionaler Minimalwert. |
| `maxItem` | Maximum-Item | Optionaler Maximalwert. |
| `humidityItem` | Luftfeuchtigkeits-Item | Optionaler Prozentwert. |
| `luxItem` | Beleuchtungsstärke, z. B. `Number:Illuminance` | Optionaler Wert oben rechts. |

Das Widget berechnet weder gefühlte Temperatur noch Tagesminimum oder Tagesmaximum. Welchen Zeitraum die Extremwerte abdecken, bestimmen die zugeordneten Items. Auch aggregierte Innenwerte können verwendet werden.

## Regen

| Parameter | Inhalt | Funktion / Standard |
| --- | --- | --- |
| `rainItem` | Binärer Regenstatus | Zeigt, ob es gerade regnet. Keine Niederschlagsmenge. |
| `rainWetState` | Rohzustand | Regen erkannt; Standard `ON`. Beispielsweise auch `OPEN` oder `1`. |
| `rainDryState` | Rohzustand | Trocken; Standard `OFF`. Beispielsweise auch `CLOSED` oder `0`. |
| `rain1hItem` | Niederschlagsmenge der letzten Stunde | Optional, beispielsweise in Millimetern. |
| `rain24hItem` | Niederschlagsmenge der letzten 24 Stunden | Optional, beispielsweise in Millimetern. |

Die Rohzustände werden exakt und mit Beachtung der Groß-/Kleinschreibung verglichen:

- Regen: blaues Regenwolken-Icon.
- Trocken: graues Regenwolken-Icon.
- Anderer oder nicht verfügbarer Status: graues Fragezeichen-Icon.
- Nur eine 24-Stunden-Menge, ohne binären Sensor: blaues Tropfen-Icon.

Wenn `rain24hItem` zugeordnet ist, steht die Menge neben dem Regen- beziehungsweise Tropfensymbol. Ohne Mengen-Item zeigt der Bereich nur das Statussymbol. Die Zeiträume der Niederschlagsmengen sind zusätzlich als Tooltip beziehungsweise zugänglicher Text hinterlegt.

Die Stundenmenge wird ebenfalls vom zugeordneten Item geliefert; das Widget berechnet keine Niederschlagssummen.

Die 24-Stunden-Menge ist eine **rollierende Summe der letzten 24 Stunden**. Sie sollte nicht durch einen Gesamtzähler oder eine seit Mitternacht zurückgesetzte Tagesmenge ersetzt werden. Das Widget bildet diese Summe nicht selbst.

## Wind

| Parameter | Inhalt | Funktion |
| --- | --- | --- |
| `windSpeedItem` | Windgeschwindigkeit mit gewünschter Einheit | Der Zahlenanteil wird auf eine Nachkommastelle formatiert; die Einheit wird übernommen. |
| `windGustItem` | Böengeschwindigkeit mit gewünschter Einheit | Optional, unterhalb der Windgeschwindigkeit. Zahlenanteil auf eine Nachkommastelle. |
| `windDirectionItem` | Windherkunft als Gradwert oder Himmelsrichtung | Textanzeige der Herkunft und ein um 180° versetzter Richtungspfeil. |

Bei Gradwerten gilt `0 = N`, `90 = O`, `180 = S`, `270 = W`. Das Widget ordnet die Werte der nächstgelegenen von 16 Himmelsrichtungen zu:

`N, NNO, NO, ONO, O, OSO, SO, SSO, S, SSW, SW, WSW, W, WNW, NW, NNW`.

Für textuelle Zustände sollten genau diese Kürzel verwendet werden, insbesondere `O` für Osten. Die Pfeildrehung basiert auf dieser Liste.

**Text und Pfeil haben unterschiedliche Aufgaben:** Der Text nennt die meteorologische Windherkunft. Der Pfeil zeigt die Richtung, **in die der Wind weht**.

| Windherkunft im Text | Pfeilrichtung |
| --- | --- |
| `N` | Süden |
| `O` | Westen |
| `SW` | Nordosten |
| `W` | Osten |

Die Windgeschwindigkeit wird durch das Widget nicht in eine andere Einheit umgerechnet. Bei nicht auswertbaren Richtungstexten ist die Pfeilrichtung nicht verlässlich; deshalb passende Rohwerte beziehungsweise Kürzel zuordnen.

## UV-Index

| Parameter | Inhalt | Standard |
| --- | --- | --- |
| `uvItem` | Numerischer UV-Index ohne Einheit im Rohzustand | Ohne Zuordnung ausgeblendet. |
| `uvIcon` | Icon-Name | `iconify:mdi:sun-wireless` |
| `uvLowColor` | Farbe für „Niedrig“ | `green` |
| `uvMediumColor` | Farbe für „Mittel“ | `#f1c40f` |
| `uvHighColor` | Farbe für „Hoch“ | `orange` |
| `uvVeryHighColor` | Farbe für „Sehr hoch“ | `red` |
| `uvExtremeColor` | Farbe für „Extrem“ | `purple` |

| UV-Index | Text |
| --- | --- |
| 0 bis kleiner 3 | Niedrig |
| 3 bis kleiner 6 | Mittel |
| 6 bis kleiner 8 | Hoch |
| 8 bis kleiner 11 | Sehr hoch |
| Ab 11 | Extrem |

Dezimalpunkt und Dezimalkomma werden verarbeitet. Ungültige, negative oder mit Einheit versehene Rohzustände sind keine gültigen Indexwerte; dafür erscheint `—` mit grauer Kennzeichnung. Gültige Werte werden mit bis zu einer Nachkommastelle und deutschem Dezimalkomma angezeigt.

## Trendlinie und Persistence

| Parameter | Funktion / Standard |
| --- | --- |
| `showTrend` | Trend ein-/ausblenden; Standard `true`. |
| `trendItem` | Optionales anderes Item für den Verlauf; ohne Zuordnung wird `temperatureItem` verwendet. |
| `trendColor` | Erste Linienfarbe; Standard `#2196f3`. |
| `trendColorEnd` | Zweite Verlaufsfarbe; Standard `#5ac8fa`. Für eine einfarbige Linie beide Farben gleich setzen. |
| `trendStrokeWidth` | Linienbreite; Standard `3`, im Dialog 1 bis 10. |
| `trendOpacity` | Deckkraft in Prozent, 0 bis 100; Standard `20`. |

Die Trendlinie verwendet `oh-trend` und benötigt historische Werte in der Standard-Persistence. Die Zelle speichert selbst keine Daten und hat keinen eigenen Parameter für einen Persistence-Dienst oder Trendzeitraum.

Für die reine aktuelle Messwertanzeige ist keine Historie erforderlich. Wenn keine Verlaufsspeicherung gewünscht ist, `showTrend: false` einstellen. Für Minimum, Maximum und Regenmenge ist unabhängig davon die Berechnung beziehungsweise Quelle der jeweiligen Items maßgeblich.

## Aktion beim Antippen

Der Konfigurationsdialog enthält die Parametergruppe **Action**. Darüber kann die Aktion für die gesamte Zelle angepasst werden. Ohne eigene Auswahl wird das Temperatur-Item im Analyzer geöffnet.

Für eine Innenübersicht kann beispielsweise die Temperaturgruppe geöffnet werden:

```yaml
action: group
actionGroupPopupItem: Temperatur_Innen_ALL
```

Diese Angaben gehören in `config` der jeweiligen Widget-Instanz. Die angezeigten Sensorwerte werden dadurch nicht geändert.

## Beispiel: vorhandene Außenwetterstation

Die Namen stammen aus der bestehenden Garten-Konfiguration. Die Instanz wird als Kind eines `oh-grid-cells` eingesetzt:

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

## Beispiel: Innenübersicht

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

## Fehlende Daten und Icons

Bei fehlendem Item, leerem Zustand, `NULL` oder `UNDEF` zeigen die allgemeinen Messwertfelder `—`. Nicht zugeordnete optionale Bereiche werden ausgeblendet. Die Prüfung auf „zugeordnet“ unterscheidet sich dabei von der Prüfung auf einen gültigen Messwert: Ein ausgewähltes, aber ungültiges Item kann weiterhin seinen Bereich mit Platzhalter anzeigen.

Klassische `oh:`-Icons stammen aus openHAB; F7-/Material-Icons werden von MainUI unterstützt. Iconify-Icons können beim ersten Abruf eine Internetverbindung benötigen, wenn sie noch nicht zwischengespeichert sind.

Referenzen: [Grid-Zellen](https://www.openhab.org/docs/ui/building-pages), [Icons](https://www.openhab.org/docs/ui/components/oh-icon.html).

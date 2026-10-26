# Climate – kompaktes Heizen-/Kühlen-Listenwidget

Dokumentation zu [`climate_heatcool_compact_list_widget.yml`](climate_heatcool_compact_list_widget.yml), Widget-ID `climate_heatcool_compact_list_widget`. Beschrieben ist der lokale Dateistand vom 26.10.2026.

Das Widget kombiniert Raumname, Isttemperatur, Luftfeuchtigkeit, Sollwertverstellung und Betriebsarten in einer kompakten Listenzeile. Eine zweite Textzeile erklärt den Betriebszustand mit Symbolen und gegebenenfalls der Abweichung des wirksamen Sollwerts.

## Installation und Einbindung

1. Die YAML-Datei nach `$OPENHAB_CONF/yaml/widgets/` kopieren. Sie enthält bereits die Dateistruktur `version: 1` und `widgets:`.
2. MainUI neu laden.
3. Das persönliche Widget innerhalb einer Liste beziehungsweise einer `oh-list-card` hinzufügen.
4. Die passenden Items auswählen, insbesondere Solltemperatur und Betriebsart.

Die Wurzel ist ein `f7-list-item`. Das Widget ist deshalb ein **Listenwidget**, keine eigenständige Karte und keine Grid-Zelle. Mehrere Räume können untereinander in derselben Liste stehen.

## Benötigte Items und Parameter

Nur `item` ist im Konfigurationsdialog als Pflichtfeld definiert. Für die vollständige Bedienung sollten auch `istthermostat` und die tatsächlich vorhandenen Sensoren beziehungsweise Rückmeldungen zugeordnet werden.

| Parameter | Erwarteter Inhalt | Funktion / Standard |
| --- | --- | --- |
| `title` | Text | Raumname. Ohne Titel erscheint der Name des Sollwert-Items. |
| `item` | Schreibbares `Number:Temperature`-Item | Solltemperatur, die mit dem Stepper verändert wird. Pflichtfeld. |
| `isttemp` | `Number:Temperature` | Gemessene Raumtemperatur. Ohne Zuordnung wird `-` angezeigt. |
| `isthumidity` | Prozentwert, üblicherweise `Number:Dimensionless` mit `%` | Luftfeuchtigkeit unter der Isttemperatur, in Klammern. Optional. |
| `istthermostat` | String mit `OFF`, `HEAT`, `COOL` | Rückmeldung und Befehlsziel der Betriebsartenschalter. |
| `istvalve` | Switch mit `ON` / `OFF` | Rückmeldung des Heiz-/Kühlaktors. Beeinflusst Farben und Boosteranzeige. |
| `setbackStart` | DateTime | Beginn des täglichen Absenkzeitraums. |
| `setbackEnd` | DateTime | Ende des täglichen Absenkzeitraums. |
| `smartgrid` | String, insbesondere `red`, `orange`, `green` | Beeinflusst im Kühlmodus das Tag-/Absenksymbol. |
| `manualActorMode` | Schreibbarer String mit `AUTO`, `FORCE_ON`, `FORCE_OFF` | Optionaler manueller Aktormodus, über das große linke Icon umschaltbar. |
| `booster` | Switch mit `ON` / `OFF` | Rückmeldung eines extern geregelten Boosters. |
| `setpointEffective` | `Number:Temperature` | Tatsächlich wirksamer Sollwert nach externen Anpassungen. |
| `seticon` | Icon-Name | Linkes Icon; Standard `iconify:mdi:heated-floor`. |
| `min` | Zahl | Untergrenze des Steppers; Standard `18`. |
| `max` | Zahl | Obergrenze des Steppers; Standard `30`. |
| `step` | Zahl | Schrittweite; Standard `0.1`. |

Soll-, Ist- und effektive Solltemperatur sollten für die hier verwendeten Vergleiche dieselbe Temperatureinheit verwenden. Das Widget vergleicht die Zahlenanteile der Zustände und führt für die Sollwertdifferenz keine eigene Einheitenumrechnung durch.

Im YAML-Dialog steht bei der Luftfeuchtigkeit noch `Number:Humidity`. Für neue Prozent-Items ist `Number:Dimensionless` mit der Einheit `%` die passende openHAB-Dimension. Die Beschreibung im Dialog wurde durch diese Dokumentation nicht geändert.

## Bedienung

| Bedienelement | Aktion |
| --- | --- |
| Minus / Plus | Verändert `item` innerhalb von `min` und `max` um `step`. |
| Diagrammsymbol | Ist für den Analyzer mit Sollwert, optional Isttemperatur, effektivem Sollwert und Aktorrückmeldung vorgesehen. |
| Ein-/Aus-Symbol | Sendet `OFF` an `istthermostat`. |
| Flamme | Sendet `HEAT`; ist bereits `HEAT` aktiv, wird stattdessen `OFF` gesendet. |
| Schneeflocke | Sendet `COOL`; ist bereits `COOL` aktiv, wird stattdessen `OFF` gesendet. |
| Großes linkes Icon | Wenn `manualActorMode` zugeordnet ist: zyklisch `AUTO → FORCE_ON → FORCE_OFF → AUTO`. Ohne Zuordnung kein Befehl. |

Der Stepper verändert den normalen Sollwert, nicht `setpointEffective`. Für Booster und Smart Grid gibt es in dieser Zeile keine eigenen Schalter; deren Zustände werden angezeigt.

Das Widget berechnet keine Ventilsteuerung, Hysterese, Absenktemperatur oder Smart-Grid-Anpassung. Diese Aufgaben müssen die vorhandenen Regeln beziehungsweise das angebundene Thermostat übernehmen. Insbesondere wirkt das Umschalten von `manualActorMode` nur dann auf den Aktor, wenn die zugehörige Regel oder Anbindung diesen Modus auswertet.

## Statussymbole unter dem Raumnamen

Die Anzeige hat eine feste Priorität: Ein manueller Zwangsmodus ersetzt die übrige Statuszeile. Danach hat die Betriebsart `OFF` Vorrang. Erst im übrigen Betrieb werden Tag-/Absenksymbol, Heizen/Kühlen und Sollwertanpassung kombiniert.

| Symbol | Bedeutung |
| --- | --- |
| `Ⓜ+` | `manualActorMode = FORCE_ON`. |
| `Ⓜ-` | `manualActorMode = FORCE_OFF`. |
| `⏻` | Thermostatmodus `OFF`, sofern kein manueller Zwangsmodus Vorrang hat. |
| `☀︎` | Normalzeit beziehungsweise der entsprechende Smart-Grid-Zustand im Kühlmodus. |
| `☾︎` | Absenkzeit beziehungsweise Smart-Grid-Zustand `red` im Kühlmodus. |
| `≋` | Heizen (`HEAT`). |
| `❅` | Kühlen (`COOL`). |
| `▲` | Booster aktiv, Modus `HEAT` und Aktor `ON`. |
| `▼` | Booster aktiv, Modus `COOL` und Aktor `ON`. |
| `△` | Effektiver Sollwert ist höher als der normale Sollwert, wenn kein aktiver Boosterpfeil Vorrang hat. |
| `▽` | Effektiver Sollwert ist niedriger als der normale Sollwert, wenn kein aktiver Boosterpfeil Vorrang hat. |

Wenn `booster` nicht `ON` ist und sich beide Sollwerte unterscheiden, werden zusätzlich die Differenz mit einer Nachkommastelle und der effektive Sollwert angezeigt, beispielsweise `+1.5 (23.0 °C)`. Bei gleichen Werten entfällt dieser Zusatz.

### Absenkzeit und Smart Grid

Für `setbackStart` und `setbackEnd` werden nur Stunde und Minute ausgewertet. Das gespeicherte Kalenderdatum ist dafür unerheblich. Ein Zeitraum über Mitternacht, etwa 22:00 bis 06:00, wird unterstützt. Sind Anfang und Ende gleich, ergibt sich kein aktiver Absenkzeitraum.

Im Modus `COOL` hat ein zugeordnetes und vorhandenes `smartgrid`-Item Vorrang vor dieser Zeitprüfung: `red` ergibt das Mondsymbol, alle anderen Zustände ergeben das Sonnensymbol. Die normale Zeitprüfung wird in diesem Fall nicht verwendet.

Die Zeitprüfung nutzt `dayjs()` bei der Auswertung. Dieses Widget hat keinen eigenen Uhrzeit-Parameter und keinen Timer; eine Neuberechnung exakt an einer Zeitgrenze ist ohne weitere Aktualisierung nicht garantiert. Die tatsächliche Betriebssteuerung muss deshalb weiterhin durch die Regeln erfolgen.

## Farben

### Sollwert-Stepper

Die erste zutreffende Bedingung bestimmt die Farbe:

| Zustand | Farbe |
| --- | --- |
| Booster `ON`, Aktor `ON`, Modus `HEAT` | Dunkelorange (`deeporange`) |
| Booster `ON`, Aktor `ON`, Modus `COOL` | Blau |
| Aktor `ON`, Modus `HEAT` | Gelb |
| Aktor `ON`, Modus `COOL` | Hellblau |
| Modus `HEAT` oder `COOL`, ohne vorherige Treffer | Grün |
| Modus `OFF` | Rot |
| Keine passende Rückmeldung | Grau |

### Linkes Aktor-Icon

`FORCE_ON` ist gelb, `FORCE_OFF` schwarz. Im übrigen Betrieb ist das Icon bei eingeschaltetem Booster und Aktor gelb, bei Aktor `ON` grün und bei Aktor `OFF` rot. Ohne auswertbare Rückmeldung ist es grau. Die Farbe bezieht sich damit nicht auf denselben Sachverhalt wie die Stepperfarbe.

## Beispiel

Die folgenden `Raum_...`-Namen sind Beispiele und müssen durch vorhandene Items ersetzt werden:

```yaml
component: oh-list-card
config:
  title: Raumklima
slots:
  default:
    - component: widget:climate_heatcool_compact_list_widget
      config:
        title: Wohnzimmer
        item: Raum_Solltemperatur
        isttemp: Raum_Isttemperatur
        isthumidity: Raum_Luftfeuchtigkeit
        istthermostat: Raum_Thermostatmodus
        istvalve: Raum_Heizaktor
        setbackStart: Raum_Absenkbeginn
        setbackEnd: Raum_Absenkende
        smartgrid: Raum_SmartGrid
        manualActorMode: Raum_ManuellerAktormodus
        booster: Raum_Booster
        setpointEffective: Raum_EffektiveSolltemperatur
        seticon: iconify:mdi:heated-floor
        min: 18
        max: 30
        step: 0.1
```

Nicht benötigte optionale Parameter weglassen. Die Betriebsartenschalter sind im aktuellen Layout immer vorhanden; für ihre Nutzung muss `istthermostat` zugeordnet sein.

## Persistence, Darstellung und Grenzen des Dateistands

- Die aktuelle Anzeige und Bedienung benötigen keine Historie. Für die Analyzer-Verläufe werden gespeicherte Werte der betreffenden Items benötigt. Die Persistence der Heizungssteuerung ist unabhängig von diesem Widget zu konfigurieren.
- Für Messwerte wird bevorzugt `displayState`, sonst der rohe `state` verwendet. Vorhandene `NULL`-/`UNDEF`-Zustände werden nicht überall abgefangen und können deshalb als Text sichtbar sein.
- Der Titel darf auf zwei Zeilen umbrechen. Der rechte Bedienbereich hat eine feste Breite; das Widget sollte auf dem Handy in einer ausreichend breiten Liste stehen, nicht in einer halben Grid-Zelle.
- Iconify-Symbole können beim ersten Abruf eine Internetverbindung benötigen, solange sie nicht zwischengespeichert sind.
- Der Diagrammknopf erzeugt im aktuellen YAML für `actionAnalyzerItems` einen URL-artigen String mit `#/analyzer?items=...`. Falls der Analyzer nicht öffnet, ist diese Übergabe zu prüfen; die vorgesehene MainUI-Angabe ist eine Liste von Item-Namen. Diese Dokumentation ändert den bestehenden Button nicht.

Referenzen: [Stepper](https://www.openhab.org/docs/ui/components/oh-stepper.html), [Einheiten und Dimensionen](https://www.openhab.org/docs/concepts/units-of-measurement.html).

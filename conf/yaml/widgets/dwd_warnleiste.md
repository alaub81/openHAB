# DWD Warnleiste

Schmale, responsive Warnliste für openHAB MainUI. Jede Meldung lässt sich einzeln aufklappen. Dort stehen Headline, Description und – sofern vorhanden – Instruction. Bis zu fünf Warnplätze sind vorbereitet, alle Items werden am Einsatzort frei ausgewählt.

## Einrichten

1. `dwd_warnleiste.yml` nach `$OPENHAB_CONF/yaml/widgets/` auf deinem openHAB-System kopieren. Die Datei verwendet wie die anderen Widgets in diesem Repository das dateibasierte Format (`version: 1`, `widgets:`).
2. Die MainUI gegebenenfalls neu laden und auf der gewünschten Layout-Seite das persönliche Widget `dwd_warnleiste` hinzufügen.
3. Unter „Warnung 1“ und „Warnung 2“ jeweils die acht Items auswählen. Weitere Warnplätze bleiben leer, bis du sie brauchst. Ein Warnplatz wird nur berücksichtigt, wenn sein Alarm-Item ausgewählt ist.
4. „Testmodus“ auf **Live – verknüpfte Items** lassen bzw. nach dem Vorschautest dorthin zurückstellen.

Für eine schmale Dashboard-Zeile das Widget in eine ausreichend breite Spalte einer responsiven Layout-Seite setzen. Die Höhe muss mit den Meldungen und aufgeklappten Texten wachsen können. Eine kleine Zelle mit fester Höhe kann lange Texte abschneiden; für Pi und iPhone ist eine responsive Zeile die sinnvollste erste Testposition.

Die vollständige Datei ist für die dateibasierte Einrichtung bestimmt. Beim manuellen Anlegen im Entwickler-Widgeteditor stattdessen nur den Inhalt unter `widgets: dwd_warnleiste:` verwenden, um vier Leerzeichen ausrücken und `uid: dwd_warnleiste` voranstellen. Nicht beide Varianten gleichzeitig unter derselben ID anlegen.

## Item-Zuordnung je Warnplatz

| Einstellung | DWD-Channel | Typ |
| --- | --- | --- |
| Alarm / Warnung vorhanden | `warningN` | Switch |
| Event | `eventN` | String |
| Severity | `severityN` | String |
| Valid from | `onsetN` | DateTime |
| Valid to | `expiresN` | DateTime |
| Headline | `headlineN` | String |
| Description | `descriptionN` | String |
| Instruction | `instructionN` | String |

`N` steht für den Warnplatz. Der Status `ON` bedeutet, dass das Binding eine Meldung bereitstellt; deren Gültigkeitszeitraum kann noch in der Zukunft liegen. Das Widget zeigt diesen Zeitraum an und entfernt eine Meldung anhand des Alarm-Items, nicht anhand einer eigenen Zeitprüfung.

## Verhalten

- Nur `ON`-Warnplätze werden angezeigt. `OFF`-Warnplätze belegen keinen Platz.
- Sortierung: Extreme, Severe, Moderate, Minor; innerhalb gleicher Stufe nach Warnbeginn.
- Farben: Minor gelb, Moderate orange, Severe rot, Extreme violett. Der Schweregrad steht zusätzlich im Text.
- Symbole werden aus Event-Schlüsselwörtern ermittelt. Gewitter hat Vorrang vor begleitendem Regen oder Wind; unbekannte Ereignisse erhalten ein Warndreieck.
- Lange Gewittertitel werden gekürzt, andere Event-Titel umbrechen bei Bedarf. Die originale Headline bleibt im aufgeklappten Bereich erhalten.
- Vorabinformationen werden mit „Vorabinfo“ gekennzeichnet.
- Absätze der Beschreibung und Verhaltenshinweise bleiben erhalten. Leere Instructions werden ausgeblendet.
- Fehlende bzw. `NULL`-/`UNDEF`-Alarmzustände erzeugen einen Verfügbarkeitshinweis. Sie werden nicht als „keine Warnung“ interpretiert.
- Wenn alle zugeordneten Alarm-Items `OFF` sind, erscheint „Keine aktiven DWD-Warnungen“.
- Keine Item-Befehle, Regeln oder zusätzlichen Gruppen erforderlich.

## Gemeinsam testen

Der Testmodus bietet keine, eine, zwei oder fünf Beispielmeldungen. Diese sind deutlich gekennzeichnet und verändern keine Items. Auch ohne ausgewählte Items kann die Darstellung so geprüft werden.

1. **Eine Warnung:** Genau eine Zeile; antippen und wieder schließen.
2. **Zwei Warnungen:** Zwei Zeilen; beide unabhängig öffnen. Bei Frost bleibt der leere Instruction-Bereich ausgeblendet.
3. **Fünf Warnungen:** Höchste Stufe zuerst; langes Event, Absätze und Vorabinfo kontrollieren.
4. **Keine Warnung:** Kompakte Entwarnungszeile.
5. Auf dem 7-Zoll-Display und in der iOS-App testen, insbesondere Zeilenumbrüche und vollständige aufgeklappte Texte.
6. Zurück auf **Live** stellen und die eigenen Items auswählen.

Lokal geprüft: gültiges YAML sowie die Widget-Ausdrücke mit simulierten Item-Zuständen (ON, OFF, UNDEF), 0/1/2/5 Beispielmeldungen, Sortierung, Gewitterkombinationen, unbekannte Events und ungültige Zeitwerte. Die Ausdrucksprüfung nutzte JavaScript und eine vereinfachte Datumsfunktion, nicht den MainUI-Ausdrucksparser. Rendering, Touch-Bedienung und Live-Anbindung müssen noch in openHAB geprüft werden.

Referenzen: [YAML-Konfiguration](https://www.openhab.org/docs/configuration/yaml/), [Widget-Kontext](https://www.openhab.org/docs/ui/components/oh-context.html), [DWD-Warnereignisse](https://www.dwd.de/DE/leistungen/opendata/help/warnungen/warning_codes_pdf.pdf?__blob=publicationFile&v=6).

## Korrektur vom 25.10.2026

Hilfsfunktionen übergeben ihre Abhängigkeiten explizit; Funktionen desselben `oh-context` können sich nicht über `fn` gegenseitig aufrufen. Styles liegen am Widget-Root und verwenden relative Selektoren für das MainUI-CSS-Scoping. Die Live-Anzeige einschließlich Aufklappen wurde im Browser geprüft.

Die korrigierte kanonische Datei wurde vom Benutzer übertragen. Die Overview ist wieder auf `widget:dwd_warnleiste` umgestellt; alle 40 Item-Zuordnungen und der Live-Modus sind erhalten. Im Browser geprüft: eine aktive Windböenwarnung, korrekte Formatierung und einzeln aufklappbare Beschreibung einschließlich Verhaltenshinweisen. Die UI-verwaltete Übergangskopie `dwd_warnleiste_livefix` wird auf der Overview nicht mehr verwendet.

## Dashboard-Abstände

Die äußere Karte verwendet die normalen Kartenabstände von MainUI. Eine zuvor gesetzte Vorgabe `margin: 0` wurde entfernt, damit die Warnleiste seitlich mit den anderen Dashboard-Karten bündig abschließt.

Auch die äußere Eckenrundung folgt dem MainUI-Theme. Die feste Vorgabe `--f7-card-border-radius: 16px` wurde entfernt, damit sie zu den Standardkarten passt.

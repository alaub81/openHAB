# DWD Pollenleiste

MainUI-Widget im Stil der DWD-Warnleiste. Die äußere Karte verwendet die normalen MainUI-Abstände und -Ecken. Acht Pollenarten sind vorbereitet: Erle, Hasel, Esche, Birke, Gräser, Roggen, Beifuß und Ambrosia.

## Installation

1. `dwd_pollenleiste.yml` nach `$OPENHAB_CONF/yaml/widgets/` kopieren.
2. MainUI neu laden und auf der gewünschten Layout-Seite das persönliche Widget `dwd_pollenleiste` hinzufügen.
3. Im Konfigurationsdialog unter jeder gewünschten Pollenart das Heute-Item auswählen.
4. Als volle Zeile in einer responsiven Seite verwenden. Die Höhe muss mit der aufgeklappten Übersicht wachsen können.

Es ist kein Alarm-Switch und keine zusätzliche Regel erforderlich. Das Widget liest die Zustände direkt aus den Pollen-Items. Die bestehende Pollen-Alarmregel und `Pollen_Alarm` werden nicht verändert.

## Verhalten

- Standardmäßig erscheinen alle Arten mit einer Belastung an mindestens einem konfigurierten Tag. Sortiert wird nach der höchsten Belastung; bei gleicher Stufe kommt der frühere Tag zuerst. Auch `0-1` erscheint als gemeldete mögliche geringe Belastung.
- Bei ausschließlich bekannten Nullwerten erscheint „Keine Pollenbelastung gemeldet“.
- Fehlende, ungültige oder `-1`-Werte gelten als „keine Daten“. Sie werden nicht als Belastung null interpretiert.
- Bei teilweise fehlenden Daten erscheint ein Hinweis. Wenn die übrigen Arten null melden, wird die Aussage ausdrücklich auf die verfügbaren Arten beschränkt.
- „Alle Pollenarten anzeigen“ öffnet eine Übersicht auch der unbelasteten und unbekannten Arten.
- Optional zeigt „Auch unbelastete Arten direkt anzeigen“ alle ausgewählten Arten bereits in der Hauptliste.
- Die Farben kennzeichnen die Indexstufe; zusätzlich steht die Belastung im Text. Sie sind eine Darstellung des Widgets, keine medizinischen Schwellenwerte.

## Optionale Vorhersage

Das Binding stellt je Art `today`, `tomorrow` und `dayafter_to` bereit. Morgen- und Übermorgen-Items sind im Widget optional. Entsprechende Spalten erscheinen nur, wenn mindestens ein Item des betreffenden Tages zugeordnet ist. Fehlende Werte anderer Arten werden dann als „keine Daten“ angezeigt.

Auch ausschließlich für morgen oder übermorgen belastete Arten erscheinen direkt. Farbe und Haupttext beziehen sich auf den Tag mit der höchsten Belastung; bei Gleichstand wird der frühere Tag betont. Darunter stehen die Werte für heute und die konfigurierten Folgetage. Die vollständige Tabelle enthält die Werte aller konfigurierten Arten, auch wenn heute noch keine Belastung gemeldet ist.

## Optionale Datenstand-Anzeige

`updatedItem` kann ein DateTime-Item am Bridge-Channel `updates#last_update` sein. Das Widget zeigt den DWD-Ausgabezeitpunkt und weist darauf hin, wenn dessen Datum nicht heute ist. Ohne dieses Item kann das Widget die Aktualität der Quelle nicht selbst beurteilen. Der Datenstand ist kein lokaler Abrufzeitpunkt.

## Unterstützte Item-Zustände

Rohwerte: `0`, `0-1`, `1`, `1-2`, `2`, `2-3`, `3`. Die sieben Stufen entsprechen „keine“, „keine bis gering“, „gering“, „gering bis mittel“, „mittel“, „mittel bis hoch“ und „hoch“.

Auch bereits übersetzte Zustände wie `keine (0)` oder `gering bis mittel (1-2)` werden verarbeitet. Der Index muss dabei am Ende in Klammern stehen. `-1`, `NULL`, `UNDEF`, nicht ausgewählte oder ungültige Werte werden als fehlende Daten behandelt. Rein beschreibende Texte ohne Index werden nicht geraten.

Referenz: [DWD Pollenflug Binding](https://www.openhab.org/addons/bindings/dwdpollenflug/).

## Vorhandene Heute-Items

In dieser Installation sind alle acht Heute-Items bereits vorhanden. Diese Widget-Instanz kann in die Layout-Seite eingesetzt werden, nachdem die Widget-Datei geladen ist:

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

Die Morgen- und Übermorgen-Items wurden inzwischen ergänzt und sind in der Overview zugeordnet. Die tatsächlichen Übermorgen-Itemnamen enden auf `_Dayafter_To`. Ein DWD-Ausgabezeit-Item ist weiterhin optional.

## Testmodus und Prüfung

`testMode` bietet Live, keine Belastung, unterschiedliche Belastung, erst morgen / übermorgen belastet und fehlende Daten. Testdaten sind deutlich gekennzeichnet; es werden keine Items verändert.

Lokal geprüft: alle sieben Rohwertstufen, übersetzte Werte einschließlich Bindestrichvarianten, unbekannte Werte, Teilverfügbarkeit, Sortierung, Testmodi und sämtliche Widget-Ausdrücke. Die Funktionen verweisen nicht auf andere Funktionen desselben `oh-context`; Abhängigkeiten werden ausdrücklich übergeben.

Die Darstellung wurde direkt in MainUI mit den acht vorhandenen Live-Items und mit gekennzeichneten Beispieldaten geprüft. Auch die aufgeklappte Tabelle wurde in einer 320-Pixel-Spalte geprüft (Kartenbreite 300 Pixel): keine überstehenden Tabellenzellen und kein horizontaler Überlauf. Die normale MainUI-Rundung (im verwendeten Theme 8 Pixel) und die normalen Kartenabstände werden übernommen. Die temporäre Vorschauseite wurde anschließend entfernt; die Overview wurde anschließend auf Benutzerwunsch um die Pollenleiste direkt unter der Unwetterwarnung ergänzt. Alle 24 Heute-/Morgen-/Übermorgen-Items sind dort im Live-Modus zugeordnet.

## Persistence

Für die Quell-Items ist keine Persistence erforderlich. Insbesondere wird `restoreOnStartup` nicht empfohlen: Nach einem Neustart über Mitternacht könnte die Prognose des Vortags sonst als aktuelles Heute erscheinen. Das Binding soll aktuelle Zustände liefern. Optional kann für eine spätere Auswertung eine separate Speicherung ohne Wiederherstellung eingerichtet werden. Die Alarm-Merkstände anderer Regeln sind davon unabhängig.

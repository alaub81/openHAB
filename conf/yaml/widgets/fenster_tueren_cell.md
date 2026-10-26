# Fenster und Türen als Grid-Zelle

Filebasierte MainUI-Definition `fenster_tueren_cell.yml`, `version: 1`. Nach `$OPENHAB_CONF/yaml/widgets/` kopieren. Die Zelle verwendet die normale `oh-cell`-Höhe von 120 Pixeln und gehört in `oh-grid-cells`.

## Anzeige

- Anzahl offener Kontakte, Anzahl eindeutig zugeordneter aktiver Alarme und Hinweise auf unbekannte Zustände.
- Zwei priorisierte Einträge: aktive Alarme zuerst, dann offene Kontakte, dann unbekannte Zustände. Weitere Einträge werden mit `+N weitere` angekündigt.
- Ein geschlossener Kontakt mit weiterhin aktivem Alarm bleibt sichtbar.
- Raumalarme werden pro Alarm-Item nur einmal gezählt, auch wenn mehrere Kontakte denselben Alarm nutzen.
- Der Schließhinweis „Fenster schließen“ wird separat angezeigt. Der Sammelalarm wird berücksichtigt, aber nicht pauschal allen Kontakten zugeordnet.
- Beim Antippen öffnet sich die native erweiterte Zelle mit allen Kontakten, vollständigen Namen und Statusangaben. Kontakte ohne Alarmzuordnung zeigen ausdrücklich „Ohne Einzelalarm“.
- „Alarm aktiv“ ist der aktuelle Alarm-Item-Zustand. Historische Alarmauslösung oder Nachrichtenzustellung werden nicht behauptet.

## Symbolerkennung aus der Semantik

Für jeden Kontakt wird `metadata.semantics.config.isPointOf` gelesen. Das Widget sucht die entsprechende Gerätegruppe in der konfigurierten Equipment-Gruppe und prüft deren tatsächliche Tags. `Window` ergibt `oh:window`, `Door` beziehungsweise Tags wie `FrontDoor` und `BackDoor` ergeben `oh:door`. Ohne passende Gerätegruppe wird ein neutrales Kontaktsymbol verwendet. Es werden keine Item-Namensmuster zur Türerkennung verwendet.

Damit nur die relevanten Gerätegruppen geladen werden, enthält die technische Gruppe `Fenster_Uebersicht_Equipment` die 16 vorhandenen Fenster-/Tür-Gerätegruppen. Sie hat selbst keine semantischen Tags und keine Persistence. Die bestehenden semantischen Elternbeziehungen bleiben unverändert; die zusätzliche Gruppe ist rein funktional.

Neue Kontakte werden über die Kontakt-Gruppe aufgenommen. Ihre zugehörige semantische Gerätegruppe muss zusätzlich Mitglied der Equipment-Gruppe sein, damit das individuelle Tür-/Fenstersymbol automatisch aufgelöst werden kann. Gruppenmitglieder und Metadaten werden beim Laden der Seite gelesen; nach Änderungen die Seite neu laden. Zustände werden danach live aus dem Item-Store verfolgt.

## Alarmzuordnung

Am jeweiligen Contact-Item liegt der Metadaten-Namespace `contactOverview`:

```yaml
value: BadOG_Fenster_Alarm
config:
  shared: false
```

`value` nennt das Alarm-Item. `shared: true` bezeichnet einen gemeinsamen Raumalarm. Optional kann `config.label` einen kürzeren Anzeigenamen liefern. Ohne Metadaten wird kein Einzelalarm angenommen.

Bereits eingerichtet:

| Kontakt | Alarm |
| --- | --- |
| Badezimmer | `BadOG_Fenster_Alarm` |
| Dachbad | `BadDG_Fenster_Alarm` |
| Hobbyraum | `Hobbyraum_Fenster_Alarm` |
| Technikraum | `Technikraum_Fenster_Alarm` |
| Eingangstür | `Eingang_Tuer_Alarm` |
| Schlafzimmer links und rechts | gemeinsam `Schlafzimmer_Fenster_Alarm`, Raumalarm |
| Kinderzimmer rechts | `Kinderzimmer_Fenster_Alarm` |

Kinderzimmer links und die übrigen nicht genannten Kontakte haben keine Einzelalarm-Zuordnung. Die vorhandenen Alarmregeln wurden nicht verändert.

## Overview-Konfiguration

```yaml
component: widget:fenster_tueren_cell
config:
  title: Fenster & Türen
  contactGroup: Fenster_ALL
  equipmentGroup: Fenster_Uebersicht_Equipment
  alarmGroupItem: Fenster_Alarm_ALL
  closeAlarmItem: Fenster_Schliessen_Alarm
  testMode: live
```

Die neue Zelle wird auf Wunsch direkt hinter der bestehenden `oh-label-cell` für `Fenster_ALL` eingefügt. Die alte Zelle bleibt erhalten.

## Tests

`testMode` bietet `live`, `mixed`, `closed` und `unknown`. Beispieldaten tragen die Kennzeichnung `TEST` und verändern weder Kontakte noch Alarm-Items.

Geprüft wurden die 16 tatsächlichen Kontakte, beide semantisch erkannten Türen, die gezielten Alarmzuordnungen, die gemeinsame Alarmzählung, unbekannte Zustände, ein geschlossener Kontakt mit aktivem Raumalarm sowie die native Detailansicht mit allen 16 Kontakten. Bei 320 und 175 Pixel Kartenbreite bleibt die Höhe 120 Pixel; kein horizontaler oder vertikaler Überlauf. Lange Kontaktnamen können zweizeilig angezeigt werden.

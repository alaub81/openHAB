"""Refresh the two DWD presentation blocks in the canonical alarm library."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIBRARY = ROOT / 'data/openhab/conf/yaml/block_libraries/lhlab_alarm_library.yml'


def definitions():
    context = "(typeof lhlabAlarmEvent === 'undefined' ? null : lhlabAlarmEvent)"
    formatter = {
        'component': 'BlockType',
        'config': {
            'type': 'lhlab_dwd_format',
            'message0': 'DWD-Warntext erstellen\nAusgabe %1\nBeschreibung %2\nZeitraum %3\nVerhaltenshinweise %4',
            'args0': [
                {'type': 'field_dropdown', 'name': 'MODE', 'options': [['Push', 'push'], ['Sprache (Alexa)', 'speech']]},
                {'type': 'field_checkbox', 'name': 'DESCRIPTION', 'checked': True},
                {'type': 'field_checkbox', 'name': 'PERIOD', 'checked': True},
                {'type': 'field_checkbox', 'name': 'INSTRUCTION', 'checked': False},
            ],
            'output': 'String', 'colour': 15,
            'tooltip': 'Innerhalb der DWD-Aktionsbereiche verwenden. Push: Beschreibung vor Zeitraum. Sprache: Warnart, Zeitraum, Beschreibung. Verhaltenshinweise standardmäßig aus. Entwarnung nennt die beendete Warnung.'
        },
        'slots': {'code': [{'component': 'BlockCodeTemplate', 'config': {
            'template': "{{utility:lhlab_dwd_text}}(" + context + ", 'message', {mode: '{{field:MODE}}', description: '{{field:DESCRIPTION}}' === 'TRUE', period: '{{field:PERIOD}}' === 'TRUE', instruction: '{{field:INSTRUCTION}}' === 'TRUE'})"
        }}]}
    }
    field = {
        'component': 'BlockType',
        'config': {
            'type': 'lhlab_dwd_field', 'message0': 'aktuelle DWD-Warnung: %1',
            'args0': [{'type': 'field_dropdown', 'name': 'FIELD', 'options': [
                ['Kurzbezeichnung', 'event'], ['Warnstufe', 'severity'], ['Push-Titel', 'title'],
                ['Originalüberschrift', 'headline'], ['Beschreibung', 'description'],
                ['Verhaltenshinweise', 'instruction'], ['Zeitraum für Push', 'periodPush'],
                ['Zeitraum für Sprache', 'periodSpeech'], ['Beginn', 'begin'], ['Ende', 'end'],
                ['Beginn (ISO)', 'from'], ['Ende (ISO)', 'to'],
            ]}],
            'output': 'String', 'colour': 15,
            'tooltip': 'Innerhalb der DWD-Aktionsbereiche verwenden, z. B. mit „Text zusammenfügen“. Verwendet die gespeicherte Warnung, auch bei Entwarnung. Heute/morgen beziehen sich auf die Ausgabezeit in Europe/Berlin. Fehlende Felder liefern leeren Text.'
        },
        'slots': {'code': [{'component': 'BlockCodeTemplate', 'config': {
            'template': "{{utility:lhlab_dwd_text}}(" + context + ", '{{field:FIELD}}')"
        }}]}
    }
    utility = {'component': 'UtilityFunction', 'config': {
        'name': 'lhlab_dwd_text', 'code': (HERE / 'format.js').read_text().replace(
            'function lhlab_dwd_text(', 'function {{name}}(', 1)}}
    return [formatter, field], [utility]


def build():
    source = LIBRARY.read_text()
    for category, components in zip(['blocks', 'utilities'], definitions()):
        start = '      # dwd-presentation-' + category + '-begin\n'
        end = '      # dwd-presentation-' + category + '-end\n'
        if start in source:
            a = source.index(start)
            b = source.index(end, a) + len(end)
            source = source[:a] + source[b:]
        yaml = subprocess.check_output(
            ['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.parse(STDIN.read).to_yaml'],
            input=json.dumps(components, ensure_ascii=False), text=True)
        fragment = start + ''.join('      ' + line + '\n' for line in yaml.splitlines() if line != '---') + end
        if category == 'blocks':
            source = source.replace('      utilities:\n', fragment + '      utilities:\n', 1)
        else:
            source = source.rstrip() + '\n' + fragment
    LIBRARY.write_text(source)


if __name__ == '__main__':
    build()

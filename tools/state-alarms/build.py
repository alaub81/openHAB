# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Extend the canonical alarm YAML and build a normal Blockly kitchen example."""
import copy
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIBRARY = ROOT / 'data/openhab/conf/yaml/block_libraries/lhlab_alarm_library.yml'
UID = 'lhlab_alarm_library'
NS = 'https://developers.google.com/blockly/xml'
ET.register_namespace('', NS)


def read_library():
    command = ['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.generate(YAML.load_file(ARGV[0]))', str(LIBRARY)]
    doc = json.loads(subprocess.check_output(command, text=True))
    lib = doc['blocks'][UID]
    lib['uid'] = UID
    return lib


def definitions():
    block = {'component': 'BlockType', 'config': {
        'type': 'lhlab_state_monitor',
        'message0': 'Zustand überwachen\nQuell-Item %1\nAlarmzustand %2\nAlarm-Item %3\nWartezeit (Minuten) %4\nzusätzliche Erinnerungen %5\nErinnerungsabstand (Minuten) %6\nTitel %7\nbei Alarm / Erinnerung %8\nbei Entwarnung %9',
        'args0': [
            {'type': 'input_value', 'name': 'SOURCE', 'check': ['String', 'oh_item']},
            {'type': 'field_dropdown', 'name': 'ACTIVE', 'options': [['offen (OPEN)', 'OPEN'], ['eingeschaltet (ON)', 'ON']]},
            {'type': 'input_value', 'name': 'ALARM', 'check': ['String', 'oh_item']},
            {'type': 'field_number', 'name': 'DELAY', 'value': 15, 'min': 1},
            {'type': 'field_number', 'name': 'REPEATS', 'value': 2, 'min': 0, 'max': 20, 'precision': 1},
            {'type': 'field_number', 'name': 'INTERVAL', 'value': 5, 'min': 1},
            {'type': 'input_value', 'name': 'TITLE', 'check': 'String'},
            {'type': 'input_statement', 'name': 'NOTIFY'}, {'type': 'input_statement', 'name': 'CLEAR'}],
        'previousStatement': '', 'nextStatement': '', 'inputsInline': False, 'colour': 15,
        'tooltip': 'Wartet bei OPEN oder ON, setzt das eigene Switch-Alarm-Item und erinnert begrenzt. CLOSED oder OFF beendet Timer und Alarm. Meldung, Titel und Kennung liefert „aktueller Alarm“. Pro Alarm-Item genau eine Regel verwenden.'},
        'slots': {'code': [{'component': 'BlockCodeTemplate', 'config': {'template': '''{{utility:lhlab_state_monitor}}({
  source: [{{input:SOURCE}}][0], alarm: [{{input:ALARM}}][0], active: '{{field:ACTIVE}}',
  delayMinutes: {{field:DELAY}}, repeats: {{field:REPEATS}}, intervalMinutes: {{field:INTERVAL}}, title: [{{input:TITLE}}][0]
}, function(lhlabAlarmEvent) {
{{statements:NOTIFY}}
}, function(lhlabAlarmEvent) {
{{statements:CLEAR}}
});
'''}}], 'toolbox': []}}
    for name, value in [('SOURCE', 'MyContact'), ('ALARM', 'MyAlarm'), ('TITLE', 'Fensteralarm')]:
        is_item = name in ('SOURCE', 'ALARM')
        block['slots']['toolbox'].append({'component': 'PresetInput', 'config': {
            'name': name, 'type': 'oh_item' if is_item else 'text', 'shadow': True,
            'fields': {'itemName' if is_item else 'TEXT': value}}})
    utility = {'component': 'UtilityFunction', 'config': {'name': 'lhlab_state_monitor',
        'code': (HERE / 'monitor.js').read_text().replace('function lhlab_state_monitor(', 'function {{name}}(', 1)}}
    return block, utility


def extend_library():
    source = LIBRARY.read_text()
    for name, definition in zip(['block', 'utility'], definitions()):
        start, end = '      # state-monitor-' + name + '-begin\n', '      # state-monitor-' + name + '-end\n'
        if start in source:
            a = source.index(start)
            b = source.index(end, a) + len(end)
            source = source[:a] + source[b:]
        yaml = subprocess.check_output(['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.parse(STDIN.read).to_yaml'],
                                       input=json.dumps([definition], ensure_ascii=False), text=True)
        fragment = start + ''.join('      ' + line + '\n' for line in yaml.splitlines() if line != '---') + end
        if name == 'block':
            source = source.replace('      utilities:\n', fragment + '      utilities:\n', 1)
        else:
            source = source.rstrip() + '\n' + fragment
    LIBRARY.write_text(source)
    read_library()  # Parse the complete file, including existing DWD code.


def block(kind, fields=None, values=None, mutation=None):
    b = ET.Element('{' + NS + '}block', {'type': kind})
    if mutation is not None:
        b.append(mutation)
    for name, value in (fields or {}).items():
        ET.SubElement(b, '{' + NS + '}field', {'name': name}).text = str(value)
    for name, value in (values or {}).items():
        ET.SubElement(b, '{' + NS + '}value', {'name': name}).append(value)
    return b


def text(value):
    return block('text', {'TEXT': value})


def item(name, label):
    return block('oh_item', {'itemName': name}, mutation=ET.Element('{' + NS + '}mutation', {
        'itemName': name, 'itemLabel': label}))


def alarm_field(name):
    return block(UID + '_lhlab_alarm_field', {'FIELD': name})


def notification():
    attrs = {name: ('true' if name in ['hasIconInfo', 'hasTag', 'hasHeaderTitle', 'hasReferenceId'] else 'false')
             for name in ['hasUser', 'hasIconInfo', 'hasTag', 'hasHeaderTitle', 'hasReferenceId', 'hasMedia',
                          'hasAction', 'hasActionButton1', 'hasActionButton2', 'hasActionButton3']}
    return block('oh_sendCloudNotification', {'type': 'push'}, {
        'message': alarm_field('message'), 'headerTitle': alarm_field('title'),
        'icon': text('oh:window'), 'tag': text('FensterAlarm'), 'reference': alarm_field('id')},
        ET.Element('{' + NS + '}mutation', attrs))


def kitchen_xml():
    root = ET.Element('{' + NS + '}xml')
    monitor = block(UID + '_lhlab_state_monitor', {'ACTIVE': 'OPEN', 'DELAY': 15, 'REPEATS': 2, 'INTERVAL': 5}, {
        'SOURCE': item('MyContact', 'Example contact'),
        'ALARM': item('MyContactAlarm', 'Example contact alarm'), 'TITLE': text('Fensteralarm')})
    monitor.set('x', '30')
    monitor.set('y', '30')
    notify = notification()
    ET.SubElement(monitor, '{' + NS + '}statement', {'name': 'NOTIFY'}).append(notify)
    ET.SubElement(monitor, '{' + NS + '}statement', {'name': 'CLEAR'}).append(notification())
    root.append(monitor)
    return ET.tostring(root, encoding='unicode')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    extend_library()
    (args.output / 'library.json').write_text(json.dumps(read_library(), ensure_ascii=False, indent=2))
    (args.output / 'kitchen.xml').write_text(kitchen_xml())

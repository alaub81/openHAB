"""Build the daily heat-pump rule using only standard openHAB Blockly blocks.

Writes Blockly XML only. JavaScript must be generated from it by openHAB's
Blockly generator before activation. This script does not contact openHAB.
"""
import argparse
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

NS = 'https://developers.google.com/blockly/xml'
ET.register_namespace('', NS)
VARIABLES = ['Jetzt', 'Heute', 'Tagesbeginn', 'Messwert', 'Cachekennung',
             'Zaehlerstand', 'DB_Ergebnis', 'Ergebnis', 'Verbrauch_1',
             'Verbrauch_2', 'Verbrauch_Management', 'Summe']
FUNCTION = 'Tagesverbrauch je Zaehler'
METERS = [('Shelly_Warmepumpe_HTTP_Gesamtverbrauch_1', 'Verbrauch_1', 'wp.daily.1'),
          ('Shelly_Warmepumpe_HTTP_Gesamtverbrauch_2', 'Verbrauch_2', 'wp.daily.2'),
          ('Shelly_Warmepumpe_MGMT_Gesamtverbrauch', 'Verbrauch_Management', 'wp.daily.mgmt')]


def element(tag, **attrs):
    return ET.Element('{' + NS + '}' + tag, attrs)


def child(parent, tag, text=None, **attrs):
    result = element(tag, **attrs)
    result.text = text
    parent.append(result)
    return result


def block(kind, fields=None, values=None, mutation=None, comment=None):
    result = element('block', type=kind)
    if mutation is not None:
        result.append(mutation)
    for name, value in (fields or {}).items():
        field = child(result, 'field', str(value), name=name)
        if name == 'VAR':
            field.set('id', 'wp-' + value)
    for name, value in (values or {}).items():
        child(result, 'value', name=name).append(value)
    if comment:
        child(result, 'comment', comment, pinned='false', h='90', w='330')
    return result


def chain(*blocks):
    for current, following in zip(blocks, blocks[1:]):
        child(current, 'next').append(following)
    return blocks[0]


def text(value):
    return block('text', {'TEXT': value})


def variable(name):
    return block('variables_get', {'VAR': name})


def assign(name, value):
    return block('variables_set', {'VAR': name}, {'VALUE': value})


def compare(op, a, b):
    return block('logic_compare', {'OP': op}, {'A': a, 'B': b})


def combine(op, *parts):
    result = parts[0]
    for other in parts[1:]:
        result = block('logic_operation', {'OP': op}, {'A': result, 'B': other})
    return result


def condition(test, body, comment=None):
    result = block('controls_if', values={'IF0': test}, comment=comment)
    child(result, 'statement', name='DO0').append(body)
    return result


def key(suffix):
    return block('text_join', values={'ADD0': variable('Cachekennung'), 'ADD1': text(':' + suffix)},
                 mutation=element('mutation', items='2'))


def cached(suffix):
    return block('oh_get_value', {'cacheType': '.private'}, {'key': key(suffix)})


def missing(suffix):
    return block('oh_check_undefined_value', {'cacheType': '.private'}, {'key': key(suffix)})


def store(suffix, value):
    return block('oh_store_value', {'cacheType': '.private'}, {'key': key(suffix), 'value': value})


def state(item):
    return block('oh_getitem_state', values={'itemName': item})


def quantity(value):
    return block('oh_quantity', values={'quantity': value})


def as_text(value):
    return block('text_join', values={'ADD0': value}, mutation=element('mutation', items='1'))


def not_null(value):
    return compare('NEQ', value, block('logic_null'))


def call(item, prefix):
    mutation = element('mutation', name=FUNCTION)
    for name in ['Messwert', 'Cachekennung']:
        child(mutation, 'arg', name=name)
    return block('procedures_callreturn', values={'ARG0': text(item), 'ARG1': text(prefix)}, mutation=mutation)


def build(before):
    original = ET.fromstring(before['actions'][0]['configuration']['blockSource'])
    midnight = copy.deepcopy(next(b for b in original.iter('{' + NS + '}block')
                                 if b.get('type') == 'oh_zdt_amend'))
    # Keep the original day-boundary semantics, using one time snapshot per run.
    for node in midnight.iter():
        node.attrib.pop('id', None)
    base = midnight.find('{' + NS + '}value[@name="baseZdt"]')
    base.clear()
    base.set('name', 'baseZdt')
    base.append(variable('Jetzt'))

    persistence = block('oh_get_persistvalue',
                        {'methodName': 'deltaSince', 'returnTypeName': 'quantityState'},
                        {'itemName': block('oh_getitem', values={'itemName': variable('Messwert')}),
                         'dayInfoSince': variable('Tagesbeginn'),
                         'persistenceName': block('oh_persistence_dropdown', {'persistence': 'default'})})
    save = condition(not_null(variable('DB_Ergebnis')), chain(
        store('delta', as_text(variable('DB_Ergebnis'))),
        store('meter', variable('Zaehlerstand')),
        store('day', variable('Heute'))),
        'Mark only successful database results as processed. Retry missing results.')
    refresh = condition(combine('OR', missing('delta'),
                                compare('NEQ', cached('day'), variable('Heute')),
                                compare('NEQ', cached('meter'), variable('Zaehlerstand'))),
                        chain(assign('DB_Ergebnis', persistence), save),
                        'Query the database only on a new day, empty cache, or changed meter reading.')
    ready = condition(combine('AND',
                              block('logic_negate', values={'BOOL': missing('delta')}),
                              compare('EQ', cached('day'), variable('Heute')),
                              compare('EQ', cached('meter'), variable('Zaehlerstand'))),
                      assign('Ergebnis', cached('delta')))
    valid = condition(combine('AND', compare('NEQ', variable('Zaehlerstand'), text('NULL')),
                               compare('NEQ', variable('Zaehlerstand'), text('UNDEF'))),
                       chain(refresh, ready))
    mutation = element('mutation')
    for name in ['Messwert', 'Cachekennung']:
        child(mutation, 'arg', name=name, varid='wp-' + name)
    function = block('procedures_defreturn', {'NAME': FUNCTION}, mutation=mutation,
                     comment='Standard Blockly function, not a block library. Cache per source and calendar day; the database remains the calculation basis.')
    child(function, 'statement', name='STACK').append(chain(
        assign('Ergebnis', block('logic_null')),
        assign('Zaehlerstand', state(variable('Messwert'))), valid))
    child(function, 'value', name='RETURN').append(variable('Ergebnis'))
    function.set('x', '1100')
    function.set('y', '40')

    addition = block('oh_quantity_arithmetic', {'operand': 'add'}, {
        'first': quantity(variable('Verbrauch_1')),
        'second': block('oh_quantity_arithmetic', {'operand': 'add'}, {
            'first': quantity(variable('Verbrauch_2')),
            'second': quantity(variable('Verbrauch_Management'))})})
    changed = combine('OR', compare('EQ', state(text('Waermepumpe_Tagesverbrauch')), text('NULL')),
                      compare('EQ', state(text('Waermepumpe_Tagesverbrauch')), text('UNDEF')),
                      block('logic_negate', values={'BOOL': block('oh_quantity_compare', {'operand': 'equal'}, {
                          'first': quantity(variable('Summe')),
                          'second': state(text('Waermepumpe_Tagesverbrauch'))})}))
    publish = condition(changed, block('oh_event', {'eventType': 'postUpdate'}, {
        'itemName': text('Waermepumpe_Tagesverbrauch'), 'value': variable('Summe')}),
        'Do not publish unchanged totals as new Item updates.')
    total = condition(combine('AND', *[not_null(variable(v)) for _, v, _ in METERS]),
                      chain(assign('Summe', addition), publish),
                      'Add only complete, current results from all three sources.')
    main = chain(assign('Jetzt', block('oh_zdt_now')),
                 assign('Heute', block('oh_zdt_toText', {'withtime': 'without'}, {'date': variable('Jetzt')})),
                 assign('Tagesbeginn', midnight),
                 *[assign(v, call(item, prefix)) for item, v, prefix in METERS], total)
    main.set('x', '30')
    main.set('y', '40')
    root = element('xml')
    variables = child(root, 'variables')
    for name in VARIABLES:
        child(variables, 'variable', name, id='wp-' + name)
    root.extend([main, function])
    return ET.tostring(root, encoding='unicode')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(build(json.loads(args.before.read_text())))


if __name__ == '__main__':
    main()

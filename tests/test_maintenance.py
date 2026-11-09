# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Offline safety checks: fake curl responses, never a live service."""
import json
import os
import re
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# A fake curl records method/payload only; it never opens a network connection.
FAKE_CURL = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
def option(key, default=''):
    return args[args.index(key)+1] if key in args else default
method = option('--request', 'GET')
url = args[-1]
q = ''
for i, arg in enumerate(args):
    if arg == '--data-urlencode' and args[i+1].startswith('q='):
        q = args[i+1][2:]
auth_scheme = ''
header = option('--header')
if header.startswith('@'):
    auth_scheme = Path(header[1:]).read_text().split()[1]
payload = option('--data-binary')
if payload.startswith('@'):
    payload = Path(payload[1:]).read_text()
log = Path(os.environ['FAKE_LOG'])
previous = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
with log.open('a') as f:
    f.write(json.dumps(dict(method=method,url=url,q=q,payload=payload,auth_scheme=auth_scheme))+'\n')
fixtures = json.loads(os.environ.get('FAKE_FIXTURES', '{}'))
status = '200'
body = {'results':[{'statement_id':0}]}
if '/rest/items?' in url:
    key = 'items_after' if any('/rest/items?' in x['url'] for x in previous) else 'items'
    body = fixtures.get(key, fixtures.get('items', [{'name':'Keep'}]))
elif url.endswith('/status'):
    body = fixtures.get('thing', {'status':'OFFLINE','statusDetail':'NONE'})
elif '/enable' in url:
    status = '204'
elif q == 'SHOW MEASUREMENTS':
    body = fixtures.get('measurements', {'results':[{'statement_id':0,'series':[{'name':'measurements','columns':['name'],'values':[['Keep'],['Old']]}]}]})
elif q.startswith('DROP MEASUREMENT'):
    body = fixtures.get('write_response', {})
elif '/api/v2/query?' in url:
    query=json.loads(payload)['query']
    if 'schema.measurementTagKeys' in query:
        body=fixtures.get('tag_keys_csv', ',result,table,_value\n,_result,0,_field\n,_result,0,_measurement\n')
    else:
        body=fixtures.get('points_csv', ',result,table,_start,_stop,_time,_value,_field,_measurement\n,_result,0,1677-09-21T00:12:43.145224194Z,2262-04-11T23:47:16.854775807Z,2026-01-01T01:00:00.000000001Z,99,value,Old\n')
elif '/api/v2/delete?' in url:
    status = '204'
if fixtures.get('fail_write') and (q.startswith('DROP MEASUREMENT') or (method != 'GET' and '/api/v2/query?' not in url)):
    sys.exit(22)
status = fixtures.get('status', status)
Path(option('--output')).write_text(body if isinstance(body,str) else json.dumps(body))
print(status,end='')
'''


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        curl = self.path / 'curl'
        curl.write_text(FAKE_CURL)
        curl.chmod(0o700)
        (self.path / 'sleep').write_text('#!/bin/sh\nexit 0\n')
        (self.path / 'sleep').chmod(0o700)
        self.log = self.path / 'calls.jsonl'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('INFLUX_', 'OPENHAB_', 'ALLOW_', 'API_', 'BRIDGE_', 'MAX_ACTIONS'))}
        self.env.update(PATH=str(self.path)+os.pathsep+os.environ['PATH'], FAKE_LOG=str(self.log),
                        OPENHAB_URL='https://openhab.invalid', INFLUX_URL='https://influx.invalid',
                        INFLUX_DATABASE='example', INFLUX_ORG='example org', INFLUX_BUCKET='example/bucket',
                        OPENHAB_TOKEN='test-openhab-token', INFLUX_TOKEN='test-influx-token',
                        INFLUX_USERNAME='testuser', INFLUX_PASSWORD='test-influx-password',
                        START='2026-01-01T00:00:00Z', STOP='2026-01-02T00:00:00Z',
                        OPERATOR='>', THRESHOLD='90', BRIDGE_UID='binding:bridge:example')

    def configured_script(self, name, settings):
        # Copy one file alone and edit its configuration just as an operator would.
        source = (ROOT/'scripts'/name).read_text()
        before, rest = source.split('# Configuration: ', 1)
        config, after = rest.split('# End configuration', 1)
        for key, value in settings.items():
            if not re.fullmatch(r'[A-Z_][A-Z_0-9]*', key):
                continue
            if isinstance(value, (list, tuple)):
                literal = '('+' '.join(shlex.quote(str(item)) for item in value)+')'
            else:
                literal = shlex.quote(str(value))
            config = re.sub(r'^'+key+r'=(?:\([^)]*\)|[^\n]*)', lambda match: key+'='+literal,
                            config, flags=re.MULTILINE)
        folder = self.path/'standalone'
        folder.mkdir(exist_ok=True)
        script = folder/name
        script.write_text(before+'# Configuration: '+config+'# End configuration'+after)
        return script

    def run_script(self, name, *args, fixtures=None, ok=True, **settings):
        script = ROOT/'scripts'/name
        if '# Configuration: ' in script.read_text():
            script = self.configured_script(name, {**self.env, **settings})
        result = subprocess.run(['/bin/bash',str(script),*args],
                                env={**self.env, **{k:v for k,v in settings.items() if isinstance(v,str)},
                                     'FAKE_FIXTURES':json.dumps(fixtures or {})},
                                text=True, capture_output=True, timeout=15)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        return result

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def writes(self):
        return [x for x in self.calls() if x['q'].startswith('DROP MEASUREMENT') or (x['method'] != 'GET' and '/api/v2/query?' not in x['url'])]

    def test_all_entrypoints_have_offline_help(self):
        for path in sorted((ROOT/'scripts').glob('*.sh')):
            self.run_script(path.name, '--help')
        self.assertEqual(self.calls(), [])

    def test_cleanup_default_is_preview(self):
        result = self.run_script('cleanup-openhab-influxdb2.sh')
        self.assertIn('DROP MEASUREMENT "Old"',result.stdout)
        self.assertEqual(self.writes(), [])

    def test_cleanup_drops_whole_orphans_without_time_bounds(self):
        self.run_script('cleanup-openhab-influxdb2.sh','--execute',START='',STOP='')
        self.assertEqual([x['q'] for x in self.writes()], ['DROP MEASUREMENT "Old"'])
        self.assertTrue(all(x['auth_scheme']=='Token' for x in self.calls() if '/query' in x['url']))

    def test_invalid_item_lists_never_delete(self):
        for items in ([],{},[{'name':'Bad Item'}],[{'name':'Keep'},{'name':'Keep'}]):
            self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'items':items},ok=False)
        self.assertEqual(self.writes(), [])

    def test_changed_items_never_delete(self):
        self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'items_after':[{'name':'Keep'},{'name':'Old'}]},ok=False)
        self.assertEqual(self.writes(), [])

    def test_invalid_influx_response_never_deletes(self):
        for value in ('not json',{}, {'results':[{'statement_id':0,'error':'failure'}]}):
            self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'measurements':value},ok=False)
        self.assertEqual(self.writes(), [])

    def test_invalid_later_candidate_prevents_all_writes(self):
        response={'results':[{'statement_id':0,'series':[{'name':'measurements','columns':['name'],'values':[['AValid'],['Z invalid']]}]}]}
        self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'measurements':response},ok=False)
        self.assertEqual(self.writes(), [])

    def test_empty_measurement_list_is_noop(self):
        self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'measurements':{'results':[{'statement_id':0}]}})
        self.assertEqual(self.writes(), [])

    def test_log_conflicts_drop_whole_measurements(self):
        log=self.path/'openhab.log'
        log.write_text('field type conflict: input field "value" on measurement "Old" is type integer\n')
        self.run_script('cleanup-influxdb2-integer.sh',OPENHAB_LOG=str(log))
        self.assertEqual(self.writes(), [])
        self.run_script('cleanup-influxdb2-integer.sh','--execute',OPENHAB_LOG=str(log))
        self.assertEqual(self.writes()[0]['q'],'DROP MEASUREMENT "Old"')

    def test_unknown_log_format_is_refused(self):
        log=self.path/'openhab.log';log.write_text('field type conflict: unrecognized message\n')
        self.run_script('cleanup-influxdb2-integer.sh','--execute',OPENHAB_LOG=str(log),ok=False)
        self.assertEqual(self.calls(), [])

    def test_full_measurement_preview_never_contacts_api(self):
        self.run_script('delete-influxdb2-measurement.sh','Old')
        self.assertEqual(self.calls(), [])

    def test_full_measurement_drop_ignores_time_environment(self):
        self.run_script('delete-influxdb2-measurement.sh','Old','--execute',START='invalid',STOP='invalid')
        self.assertEqual(self.writes()[0]['q'],'DROP MEASUREMENT "Old"')
        self.assertNotIn('time',self.writes()[0]['q'])
        self.assertEqual(self.writes()[0]['auth_scheme'],'Token')

    def test_measurement_array_and_execution_are_configurable(self):
        self.run_script('delete-influxdb2-measurement.sh',MEASUREMENTS=['Old'],DRY_RUN='false')
        self.assertEqual([x['q'] for x in self.writes()],['DROP MEASUREMENT "Old"'])

    def test_timerange_execution_encodes_scope(self):
        self.run_script('delete-influxdb2-measurement-timerange.sh','Old','--execute')
        call=self.writes()[0]
        self.assertIn('org=example%20org&bucket=example%2Fbucket',call['url'])
        self.assertEqual(json.loads(call['payload']),dict(start=self.env['START'],stop=self.env['STOP'],predicate='_measurement="Old"'))
        self.assertEqual(call['auth_scheme'],'Token')

    def test_invalid_ranges_and_names_never_write(self):
        for settings in ({'START':''},{'STOP':'2026-02-30T00:00:00Z'},{'STOP':self.env['START']}):
            self.run_script('delete-influxdb2-measurement-timerange.sh','Old','--execute',ok=False,**settings)
        for name in ('*','Bad"name','Good;DROP'):
            self.run_script('delete-influxdb2-measurement.sh',name,'--execute',ok=False)
        self.assertEqual(self.calls(), [])

    def test_file_configuration_takes_precedence_over_environment(self):
        script=self.configured_script('delete-influxdb2-measurement.sh',{**self.env,'MEASUREMENTS':['Old'],'DRY_RUN':'false'})
        result=subprocess.run(['/bin/bash',str(script)],text=True,capture_output=True,
            env={**self.env,'INFLUX_URL':'https://other.invalid'},timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(self.writes()[0]['url'].startswith('https://influx.invalid/'))

    def test_bucket_delete_needs_explicit_scope_flag(self):
        self.run_script('delete-influxdb2-timerange.sh','--execute',ok=False)
        self.assertEqual(self.calls(), [])
        self.run_script('delete-influxdb2-timerange.sh','--all-measurements','--execute')
        self.assertNotIn('predicate',json.loads(self.writes()[0]['payload']))

    def test_max_actions_and_first_failed_write_stop_execution(self):
        self.run_script('delete-influxdb2-measurement.sh','First','Second','--execute',MAX_ACTIONS='1',ok=False)
        self.assertEqual(self.writes(), [])
        self.run_script('delete-influxdb2-measurement.sh','First','Second','--execute',fixtures={'fail_write':True},ok=False)
        self.assertEqual(len(self.writes()),1)

    def test_http_and_logical_errors_stop_deletion(self):
        self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'status':'401'},ok=False)
        self.assertEqual(self.writes(), [])
        self.run_script('delete-influxdb2-measurement.sh','First','Second','--execute',
            fixtures={'write_response':{'results':[{'statement_id':0,'error':'database not found'}]}},ok=False)
        self.assertEqual(len(self.writes()),1)

    def test_wrong_point_deletion_preserves_nanosecond_precision(self):
        self.run_script('delete-wrong-influxdb2-measurements.sh','Old')
        self.assertEqual(self.writes(), [])
        self.run_script('delete-wrong-influxdb2-measurements.sh','Old','--execute')
        body=json.loads(self.writes()[0]['payload'])
        self.assertEqual(body,dict(start='2026-01-01T01:00:00.000000001Z',stop='2026-01-01T01:00:00.000000001Z',predicate='_measurement="Old"'))

    def test_wrong_point_last_nanosecond_does_not_touch_next_second(self):
        csv=',result,table,_start,_stop,_time,_value,_field,_measurement\n,_result,0,start,stop,2026-01-01T01:00:00.999999999Z,99,value,Old\n'
        self.run_script('delete-wrong-influxdb2-measurements.sh','Old','--execute',fixtures={'points_csv':csv})
        self.assertEqual(json.loads(self.writes()[0]['payload'])['stop'],'2026-01-01T01:00:00.999999999Z')

    def test_wrong_points_refuse_tags_and_unexpected_values(self):
        self.run_script('delete-wrong-influxdb2-measurements.sh','Old','--execute',
            fixtures={'tag_keys_csv':',result,table,_value\n,_result,0,room\n'},ok=False)
        for csv in ('error,reference\nbroken,42\n',',result,table,_start,_stop,_time,_value,_field,_measurement\n,_result,0,start,stop,2026-01-01T01:00:00Z,20,value,Old\n'):
            self.run_script('delete-wrong-influxdb2-measurements.sh','Old','--execute',fixtures={'points_csv':csv},ok=False)
        self.assertEqual(self.writes(), [])

    def test_wrong_point_deletion_includes_complete_tag_predicate(self):
        tags=',result,table,_value\n,_result,0,item\n,_result,0,room\n'
        points=',result,table,_start,_stop,_time,_value,_field,_measurement,item,room\n,_result,0,start,stop,2026-01-01T01:00:00Z,99,value,Old,Old,lab\n'
        self.run_script('delete-wrong-influxdb2-measurements.sh','Old','--execute',fixtures={'tag_keys_csv':tags,'points_csv':points})
        self.assertEqual(json.loads(self.writes()[0]['payload'])['predicate'],'_measurement="Old" AND "item"="Old" AND "room"="lab"')

    def test_configured_binding_refresh_targets(self):
        self.run_script('digitalstrom_binding_tools.sh','refresh',REFRESH_ITEMS=['MySensors'])
        self.assertEqual(self.writes()[0]['payload'],'REFRESH')

    def test_binding_restart_executes_without_extra_flag(self):
        self.run_script('digitalstrom_binding_tools.sh','restart')
        self.assertEqual([x['payload'] for x in self.writes()],['false','true'])

    def test_binding_status_actions_only_read(self):
        for action in ('status', 'fullstatus'):
            self.run_script('digitalstrom_binding_tools.sh',action,
                            MONITORED_THINGS=['digitalstrom:circuit:examplebridge:exampledevice'])
        self.assertGreater(len(self.calls()),0)
        self.assertEqual(self.writes(), [])

    def test_binding_autorestart_leaves_online_things_running(self):
        self.run_script('digitalstrom_binding_tools.sh','autorestart',
                        fixtures={'thing':{'status':'ONLINE','statusDetail':'NONE'}})
        self.assertEqual(self.writes(), [])

    def test_binding_does_not_accept_execution_mode_flags(self):
        for flag in ('--dry-run', '--execute'):
            self.run_script('digitalstrom_binding_tools.sh','restart',flag,ok=False)
        self.assertEqual(self.calls(), [])

    def test_binding_invalid_or_disabled_status_never_restarts(self):
        for thing in ({}, {'status':'UNINITIALIZED','statusDetail':'DISABLED'}):
            self.run_script('digitalstrom_binding_tools.sh','autorestart',fixtures={'thing':thing},ok=False)
        self.assertEqual(self.writes(), [])

    def test_interrupted_binding_restart_attempts_reenable(self):
        self.run_script('digitalstrom_binding_tools.sh','restart',fixtures={'fail_write':True},ok=False)
        self.assertEqual([x['payload'] for x in self.writes()],['false','true'])

    def test_binding_refresh_sends_command_without_extra_flag(self):
        self.run_script('digitalstrom_binding_tools.sh','refresh','MyGroup')
        self.assertEqual(len(self.writes()),1)
        self.assertEqual(self.writes()[0]['payload'],'REFRESH')


if __name__ == '__main__':
    unittest.main()

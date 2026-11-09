"""Offline safety checks: fake curl responses, never a live service."""
import json
import os
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
payload = option('--data-binary')
if payload.startswith('@'):
    payload = Path(payload[1:]).read_text()
log = Path(os.environ['FAKE_LOG'])
previous = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
with log.open('a') as f:
    f.write(json.dumps(dict(method=method,url=url,q=q,payload=payload))+'\n')
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
elif q.startswith('SELECT * INTO'):
    body = {'results':[{'statement_id':0,'series':[{'name':'result','columns':['time','written'],'values':[['1970-01-01T00:00:00Z',2]]}]}]}
elif q.startswith('SELECT'):
    body = fixtures.get('points', {'results':[{'statement_id':0,'series':[{'name':'Old','columns':['time','value'],'values':[['2026-01-01T01:00:00.000000001Z',99]]}]}]})
elif '/api/v2/query?' in url:
    body = fixtures.get('csv', ',result,table,_value\n,_result,0,Keep\n,_result,0,Old\n')
elif '/api/v2/delete?' in url:
    status = '204'
if fixtures.get('fail_write') and method != 'GET' and '/api/v2/query?' not in url:
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
                        START='2026-01-01T00:00:00Z', STOP='2026-01-02T00:00:00Z',
                        OPERATOR='>', THRESHOLD='90', BRIDGE_UID='binding:bridge:example')

    def run_script(self, name, *args, fixtures=None, ok=True, **env):
        result = subprocess.run(['/bin/bash',str(ROOT/'scripts'/name),*args], env={**self.env, **env, 'FAKE_FIXTURES':json.dumps(fixtures or {})}, text=True, capture_output=True, timeout=15)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        return result

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def writes(self):
        return [x for x in self.calls() if x['method'] != 'GET' and '/api/v2/query?' not in x['url']]

    def test_all_entrypoints_have_offline_help(self):
        for path in sorted((ROOT/'scripts').glob('*.sh')):
            if path.name != 'maintenance-common.sh':
                self.run_script(path.name, '--help')
        self.assertEqual(self.calls(), [])

    def test_v1_cleanup_default_is_preview(self):
        result = self.run_script('cleanup-openhab-influxdb.sh')
        self.assertIn('DROP MEASUREMENT "Old"',result.stdout)
        self.assertEqual(self.writes(), [])

    def test_v1_cleanup_execute_only_orphans(self):
        self.run_script('cleanup-openhab-influxdb.sh','--execute')
        self.assertEqual([x['q'] for x in self.writes()], ['DROP MEASUREMENT "Old"'])

    def test_invalid_item_lists_never_delete(self):
        for items in ([],{},[{'name':'Bad Item'}],[{'name':'Keep'},{'name':'Keep'}]):
            self.run_script('cleanup-openhab-influxdb.sh','--execute',fixtures={'items':items},ok=False)
        self.assertEqual(self.writes(), [])

    def test_changed_items_never_delete(self):
        self.run_script('cleanup-openhab-influxdb.sh','--execute',fixtures={'items_after':[{'name':'Keep'},{'name':'Old'}]},ok=False)
        self.assertEqual(self.writes(), [])

    def test_invalid_influx_response_never_deletes(self):
        for value in ('not json',{}, {'results':[{'statement_id':0,'error':'failure'}]}):
            self.run_script('cleanup-openhab-influxdb.sh','--execute',fixtures={'measurements':value},ok=False)
        self.assertEqual(self.writes(), [])

    def test_invalid_later_candidate_prevents_all_writes(self):
        response={'results':[{'statement_id':0,'series':[{'name':'measurements','columns':['name'],'values':[['AValid'],['Z invalid']]}]}]}
        self.run_script('cleanup-openhab-influxdb.sh','--execute',fixtures={'measurements':response},ok=False)
        self.assertEqual(self.writes(), [])

    def test_empty_measurement_list_is_a_noop(self):
        self.run_script('cleanup-openhab-influxdb.sh','--execute',fixtures={'measurements':{'results':[{'statement_id':0}]}})
        self.assertEqual(self.writes(), [])

    def test_field_conflicts_are_whole_measurement_deletions(self):
        log=self.path/'openhab.log'
        log.write_text('field type conflict: input field "value" on measurement "Old" is type integer\n')
        self.run_script('cleanup-influxdb-integer.sh',OPENHAB_LOG=str(log))
        self.assertEqual(self.writes(), [])
        self.run_script('cleanup-influxdb-integer.sh','--execute',OPENHAB_LOG=str(log))
        self.assertEqual(self.writes()[0]['q'],'DROP MEASUREMENT "Old"')

    def test_malformed_field_conflict_is_refused(self):
        log=self.path/'openhab.log'; log.write_text('field type conflict: unrecognized message\n')
        self.run_script('cleanup-influxdb-integer.sh','--execute',OPENHAB_LOG=str(log),ok=False)
        self.assertEqual(self.calls(), [])

    def test_basic_password_file_authentication(self):
        password=self.path/'local-password'; password.write_text('local-test-password\n')
        self.run_script('cleanup-openhab-influxdb.sh',INFLUX_USERNAME='testuser',INFLUX_PASSWORD_FILE=str(password),INFLUX_TOKEN='')
        self.assertEqual(self.writes(), [])

    def test_v2_dry_run_makes_no_requests(self):
        result=self.run_script('delete-influxdb2-measurement.sh','Old')
        self.assertIn('DRY-RUN',result.stdout)
        self.assertEqual(self.calls(), [])

    def test_v2_execute_encodes_scope(self):
        self.run_script('delete-influxdb2-measurement.sh','Old','--execute')
        call=self.writes()[0]
        self.assertIn('org=example%20org&bucket=example%2Fbucket',call['url'])
        self.assertEqual(json.loads(call['payload']),dict(start=self.env['START'],stop=self.env['STOP'],predicate='_measurement="Old"'))

    def test_v2_requires_valid_range_and_names(self):
        for env in ({'START':''},{'STOP':'2026-02-30T00:00:00Z'},{'STOP':self.env['START']}):
            self.run_script('delete-influxdb2-measurement.sh','Old','--execute',ok=False,**env)
        for name in ('*','Bad"name','Good;DROP'):
            self.run_script('delete-influxdb2-measurement.sh',name,'--execute',ok=False)
        self.assertEqual(self.calls(), [])

    def test_bucket_delete_requires_explicit_scope_flag(self):
        self.run_script('delete-influxdb2-timerange.sh','--execute',ok=False)
        self.assertEqual(self.calls(), [])
        self.run_script('delete-influxdb2-timerange.sh','--all-measurements','--execute')
        self.assertNotIn('predicate',json.loads(self.writes()[0]['payload']))

    def test_v2_cleanup_and_csv_failure(self):
        self.run_script('cleanup-openhab-influxdb2.sh','--execute',fixtures={'csv':'error,reference\nbroken,42\n'},ok=False)
        self.assertEqual(self.writes(), [])
        self.run_script('cleanup-openhab-influxdb2.sh','--execute')
        self.assertEqual(len(self.writes()),1)
        self.assertEqual(json.loads(self.writes()[0]['payload'])['predicate'],'_measurement="Old"')

    def test_max_actions_and_failed_write(self):
        self.run_script('delete-influxdb2-measurement.sh','First','Second','--execute',MAX_ACTIONS='1',ok=False)
        self.assertEqual(self.writes(), [])
        self.run_script('delete-influxdb2-measurement.sh','First','Second','--execute',fixtures={'fail_write':True},ok=False)
        self.assertEqual(len(self.writes()),1)

    def test_credentials_and_http_failure(self):
        self.run_script('cleanup-openhab-influxdb.sh','--execute',OPENHAB_TOKEN='',ok=False)
        self.assertEqual(self.calls(), [])
        self.run_script('cleanup-openhab-influxdb.sh','--execute',fixtures={'status':'401'},ok=False)
        self.assertEqual(self.writes(), [])

    def test_copy_keeps_source(self):
        self.run_script('rename-influxdb-measurement.sh','Old','New','--execute')
        self.assertEqual(len(self.writes()),1)
        self.assertTrue(self.writes()[0]['q'].startswith('SELECT * INTO "New" FROM "Old"'))

    def test_wrong_point_deletion_is_scoped(self):
        self.run_script('delete-wrong-influxdb-measurements.sh','Old')
        self.assertEqual(self.writes(), [])
        self.run_script('delete-wrong-influxdb-measurements.sh','Old','--execute')
        self.assertEqual(self.writes()[0]['q'],'DELETE FROM "Old" WHERE time = \'2026-01-01T01:00:00.000000001Z\'')

    def test_tagged_or_out_of_range_points_are_refused(self):
        for extra,stamp,value in (({'tags':{'room':'example'}},'2026-01-01T01:00:00Z',99),({},'2025-01-01T00:00:00Z',99),({},'2026-01-01T01:00:00Z',20)):
            response={'results':[{'statement_id':0,'series':[dict(name='Old',columns=['time','value'],values=[[stamp,value]],**extra)]}]}
            self.run_script('delete-wrong-influxdb-measurements.sh','Old','--execute',fixtures={'points':response},ok=False)
        self.assertEqual(self.writes(), [])

    def test_binding_restart_is_preview_then_explicit(self):
        self.run_script('digitalstrom_binding_tools.sh','restart')
        self.assertEqual(self.writes(), [])
        self.run_script('digitalstrom_binding_tools.sh','restart','--execute')
        self.assertEqual([x['payload'] for x in self.writes()],['false','true'])

    def test_binding_invalid_or_disabled_status_never_restarts(self):
        for thing in ({}, {'status':'UNINITIALIZED','statusDetail':'DISABLED'}):
            self.run_script('digitalstrom_binding_tools.sh','autorestart','--execute',fixtures={'thing':thing},ok=False)
        self.assertEqual(self.writes(), [])

    def test_interrupted_binding_restart_attempts_reenable(self):
        self.run_script('digitalstrom_binding_tools.sh','restart','--execute',fixtures={'fail_write':True},ok=False)
        self.assertEqual([x['payload'] for x in self.writes()],['false','true'])

    def test_binding_refresh_is_explicit(self):
        self.run_script('digitalstrom_binding_tools.sh','refresh','MyGroup')
        self.assertEqual(self.calls(), [])
        self.run_script('digitalstrom_binding_tools.sh','refresh','MyGroup','--execute')
        self.assertEqual(self.writes()[0]['payload'],'REFRESH')


if __name__ == '__main__':
    unittest.main()

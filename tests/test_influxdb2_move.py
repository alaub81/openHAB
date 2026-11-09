"""Offline copy/merge/move checks with a stateful fake InfluxDB, never a live API."""
from contextlib import redirect_stdout
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('influx2_move', ROOT/'scripts/rename-influxdb2-measurement.py')
move = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(move)


def point(value='1.5', *, stamp='2026-01-01T00:00:00.000000001Z', kind='double', field='value', tags=None):
    return dict(value=value, time=stamp, kind=kind, field=field, tags={'item':'Old','room':'example'} if tags is None else tags)


def identity(row):
    return row['time'], tuple(sorted(row['tags'].items())), row['field']


def export_csv(path, measurement, points):
    with Path(path).open('x',newline='') as output:
        writer=csv.writer(output)
        for index,row in enumerate(points):
            tags=sorted(row['tags'])
            header=['','result','table','_time','_value','_field','_measurement',*tags]
            writer.writerow(['#datatype','string','long','dateTime:RFC3339',row['kind'],'string','string',*['string']*len(tags)])
            writer.writerow(['#default','_result',*['']*(len(header)-2)])
            writer.writerow(header)
            writer.writerow(['','',str(index),row['time'],row['value'],row['field'],measurement,*[row['tags'][t] for t in tags]])


class FakeAPI:
    org='example-org'
    bucket='example-bucket'
    def __init__(self, source=None, target=None):
        self.points={'Old':copy.deepcopy([point()] if source is None else source), 'New':copy.deepcopy(target or [])}
        self.writes=[]
        self.reads=0
        self.corrupt_copy=False
        self.stream_error=False
        self.change_preflight=False

    def query(self, query, output):
        if '|> to(' in query:
            self.writes.append('copy')
            target={identity(row):row for row in self.points['New']}
            for row in copy.deepcopy(self.points['Old']):
                if 'key: "item"' in query and row['tags'].get('item')=='Old':
                    row['tags']['item']='New'
                target[identity(row)]=row
            self.points['New']=list(target.values())
            if self.corrupt_copy:
                self.points['New'][0]['value']='999'
            Path(output).write_text('error,reference\nfailed,42\n' if self.stream_error else '')
        else:
            self.reads+=1
            if self.change_preflight and self.reads==3:
                self.points['Old'].append(point('2',stamp='2026-01-01T00:00:01Z'))
            measurement=re.search(r'r\._measurement == (".*")',query)[1]
            measurement=json.loads(measurement)
            export_csv(output,measurement,self.points[measurement])

    def delete(self, measurement):
        self.writes.append('delete '+measurement)
        self.points[measurement]=[]


class InfluxMoveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.stdout=io.StringIO()
        self.addCleanup(self.stdout.close)

    def run_move(self, api, **options):
        with redirect_stdout(self.stdout):
            return move.move_measurement(api,'Old','New',self.folder,**options)

    def test_dry_run_exports_both_measurements_without_writes(self):
        api=FakeAPI()
        folder=self.run_move(api)
        self.assertEqual(api.writes,[])
        self.assertTrue((folder/'source_before.csv').exists())
        self.assertTrue((folder/'target_before.csv').exists())
        self.assertEqual(json.loads((folder/'manifest.json').read_text())['status'],'dry_run')
        self.assertEqual(folder.stat().st_mode & 0o777,0o700)

    def test_move_overwrites_overlaps_keeps_extra_target_values_and_renames_item(self):
        target=[point('99',tags={'item':'New','room':'example'}),point('8',stamp='2026-01-01T00:00:05Z',tags={'item':'New','room':'example'})]
        api=FakeAPI(target=target)
        folder=self.run_move(api,execute=True)
        self.assertEqual(api.writes,['copy','delete Old'])
        self.assertEqual(api.points['Old'],[])
        self.assertEqual(len(api.points['New']),2)
        self.assertEqual(api.points['New'][0]['value'],'1.5')
        self.assertEqual(api.points['New'][0]['tags'],{'item':'New','room':'example'})
        self.assertEqual(json.loads((folder/'manifest.json').read_text())['status'],'move_verified')

    def test_all_field_types_and_nanoseconds_are_verified(self):
        source=[point('9223372036854775806',kind='long',field='signed'),
                point('18446744073709551614',kind='unsignedLong',field='unsigned'),
                point('false',kind='boolean',field='enabled'),
                point('text, with "quotes"\nand newline',kind='string',field='description')]
        api=FakeAPI(source=source,target=[point('4',stamp='2026-01-01T00:00:00.000000002Z',tags={'item':'New','room':'example'})])
        self.run_move(api,execute=True)
        self.assertEqual(len(api.points['New']),5)
        self.assertEqual(api.writes[-1],'delete Old')

    def test_empty_source_never_writes_or_deletes(self):
        api=FakeAPI(source=[])
        with self.assertRaises(ValueError):
            self.run_move(api,execute=True)
        self.assertEqual(api.writes,[])

    def test_copy_only_retains_source(self):
        api=FakeAPI()
        self.run_move(api,execute=True,delete_source=False)
        self.assertEqual(api.writes,['copy'])
        self.assertTrue(api.points['Old'])

    def test_corrupt_copy_never_deletes_source(self):
        api=FakeAPI();api.corrupt_copy=True
        with self.assertRaises(RuntimeError):
            self.run_move(api,execute=True)
        self.assertEqual(api.writes,['copy'])
        self.assertTrue(api.points['Old'])

    def test_streamed_error_never_deletes_source(self):
        api=FakeAPI();api.stream_error=True
        with self.assertRaises(RuntimeError):
            self.run_move(api,execute=True)
        self.assertEqual(api.writes,['copy'])
        self.assertTrue(api.points['Old'])

    def test_changed_source_aborts_before_copy(self):
        api=FakeAPI();api.change_preflight=True
        with self.assertRaises(RuntimeError):
            self.run_move(api,execute=True)
        self.assertEqual(api.writes,[])

    def test_ambiguous_tag_mapping_refuses_writes(self):
        api=FakeAPI(source=[point(),point(tags={'item':'New','room':'example'})])
        with self.assertRaises(ValueError):
            self.run_move(api,execute=True)
        self.assertEqual(api.writes,[])

    def test_other_item_tag_values_and_other_tags_are_preserved(self):
        api=FakeAPI(source=[point(tags={'item':'Different','room':'example'})])
        self.run_move(api,execute=True)
        self.assertEqual(api.points['New'][0]['tags'],{'item':'Different','room':'example'})

    def test_identity_and_injection_are_rejected(self):
        api=FakeAPI()
        with self.assertRaises(ValueError):
            move.move_measurement(api,'Old','Old',self.folder)
        for value in ('','${die(msg: 1)}','bad\nname'):
            with self.assertRaises(ValueError):
                move.flux_literal(value)
        self.assertEqual(api.writes,[])

    def test_generated_copy_keeps_full_time_domain_and_field_values(self):
        query=move.copy_query('bucket','org','Old','New',True)
        self.assertIn(move.MIN_TIME,query)
        self.assertIn(move.MAX_TIME,query)
        self.assertIn('set(key: "_measurement", value: "New")',query)
        self.assertIn('set(key: "item", value: "New")',query)
        self.assertNotIn('aggregateWindow',query)
        self.assertNotIn('delete',query)
        self.assertNotIn('key: "item"',move.copy_query('bucket','org','Old','New',False))

    def test_api_refuses_placeholder_tokens_and_credential_urls(self):
        for url,token in (('http://localhost:8086','CHANGE_ME_TOKEN'),('http://user:pass@localhost:8086','valid-example-token')):
            with self.assertRaises(ValueError):
                move.Influx2API(url,'org','bucket',token)


if __name__=='__main__':
    unittest.main()

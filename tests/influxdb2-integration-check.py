# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Opt-in real InfluxDB 2.9 checks in a temporary container with synthetic data.

First pull influxdb:2.9-alpine, then run this file explicitly. No host ports,
existing services or data volumes are used; the owned container is removed.
"""
import importlib.util,json,os,re,shlex,subprocess,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTAINER='openhab-influxdb2-test-'+uuid.uuid4().hex[:10]
TOKEN='openhab-maintenance-test-token-only-00000000'
ORG='maintenance-test';BUCKET='fixtures'
spec=importlib.util.spec_from_file_location('move_integration',ROOT/'scripts/rename-influxdb2-measurement.py')
move=importlib.util.module_from_spec(spec);spec.loader.exec_module(move)

def curl(method,path,data=None,kind='application/json'):
    args=['docker','exec','-i',CONTAINER,'curl','--silent','--show-error','--max-time','90','--request',method,
          '--header','Authorization: Token '+TOKEN,'--header','Content-Type: '+kind,'--write-out','%{http_code}']
    if data is not None: args+=['--data-binary','@-']
    args+=['http://localhost:8086'+path]
    result=subprocess.run(args,input=data,capture_output=True,timeout=100)
    if result.returncode: raise RuntimeError(result.stderr.decode())
    body,status=result.stdout[:-3],int(result.stdout[-3:])
    return status,body

class DockerAPI(move.Influx2API):
    def post(self,path,payload,output=None):
        status,body=curl('POST',path,json.dumps(payload).encode())
        if status!=(200 if output else 204): raise RuntimeError(f'Unexpected HTTP {status}: {body.decode()}')
        if output: Path(output).write_bytes(body)

def write(lines):
    status,body=curl('POST','/api/v2/write?org='+ORG+'&bucket='+BUCKET+'&precision=ns',lines.encode(),'text/plain')
    assert status==204,(status,body)

SHIM=r'''#!/usr/bin/env python3
import os,subprocess,sys
from pathlib import Path
args=sys.argv[1:];output=None;input_data=None;i=0
while i<len(args):
    if args[i]=='--output': output=args[i+1];del args[i:i+2];continue
    if args[i]=='--header' and args[i+1].startswith('@'):
        args[i+1]=Path(args[i+1][1:]).read_text().strip()
    if args[i]=='--data-binary' and args[i+1].startswith('@'):
        input_data=Path(args[i+1][1:]).read_bytes();args[i+1]='@-'
    i+=1
if args[-1].startswith('https://openhab.invalid/'):
    import json
    body=json.dumps([{'name':name} for name in ('New','Range','Wrong','Keep')]).encode()
    if output: Path(output).write_bytes(body)
    print('200',end='');sys.exit(0)
result=subprocess.run(['docker','exec','-i',os.environ['TEST_CONTAINER'],'curl',*args],input=input_data,capture_output=True)
if output: Path(output).write_bytes(result.stdout[:-3])
sys.stdout.buffer.write(result.stdout[-3:]);sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
'''

def script(folder,name,**settings):
    text=(ROOT/'scripts'/name).read_text()
    before,rest=text.split('# Configuration: ',1);config,after=rest.split('# End configuration',1)
    values=dict(INFLUX_URL='http://localhost:8086',INFLUX_DATABASE=BUCKET,INFLUX_ORG=ORG,
        INFLUX_BUCKET=BUCKET,INFLUX_TOKEN=TOKEN,DRY_RUN='false')
    values.update(settings)
    for key,value in values.items():
        config=re.sub('^'+key+'=.*$',lambda m:key+'='+shlex.quote(str(value)),config,flags=re.M)
    path=folder/name;path.write_text(before+'# Configuration: '+config+'# End configuration'+after)
    return path

def main():
    if len(sys.argv)!=1:
        raise SystemExit('Usage: python3 tests/influxdb2-integration-check.py')
    image='influxdb:2.9-alpine'
    if subprocess.run(['docker','image','inspect',image],capture_output=True).returncode:
        raise SystemExit('Pull the opt-in test image first: docker pull '+image)
    subprocess.run(['docker','run','--detach','--rm','--pull','never','--name',CONTAINER,
        '--network','none','--memory','512m','--cpus','1','--pids-limit','128',
        '--tmpfs','/var/lib/influxdb2:rw,nosuid,size=128m','--tmpfs','/etc/influxdb2:rw,nosuid,size=8m',
        '-e','DOCKER_INFLUXDB_INIT_MODE=setup','-e','DOCKER_INFLUXDB_INIT_USERNAME=testadmin',
        '-e','DOCKER_INFLUXDB_INIT_PASSWORD=local-test-password-only','-e','DOCKER_INFLUXDB_INIT_ORG='+ORG,
        '-e','DOCKER_INFLUXDB_INIT_BUCKET='+BUCKET,'-e','DOCKER_INFLUXDB_INIT_ADMIN_TOKEN='+TOKEN,
        image,'influxd','--reporting-disabled'],capture_output=True,check=True)
    try:
        for attempt in range(30):
            try: status,body=curl('GET','/api/v2/orgs?org='+ORG)
            except RuntimeError:
                time.sleep(1);continue
            if status==200 and json.loads(body).get('orgs'): break
            time.sleep(1)
        else: raise RuntimeError('Test database did not initialize')
        api=DockerAPI('http://localhost:8086',ORG,BUCKET,TOKEN)
        t1=move.timestamp_ns('2026-01-01T00:00:00.000000001Z');t2=t1+1;t3=t1+5*10**9
        write(f'Old,item=Old,room=lab value=1.5,enabled=true,count=9223372036854775806i,total=18446744073709551614u,text="a,b" {t1}\n'
              f'Old,item=Old,room=lab value=2.5 {t2}\nNew,item=New,room=lab value=99.0,extra="keep" {t1}\nNew,item=New,room=lab value=8.0 {t3}')
        with tempfile.TemporaryDirectory(prefix='openhab-influx-integration-') as temp:
            folder=Path(temp)
            result=move.move_measurement(api,'Old','New',folder/'move',execute=True)
            manifest=json.loads((result/'manifest.json').read_text())
            assert manifest['status']=='move_verified',manifest
            print('PASS real InfluxDB 2.9: move/merge, overwritten target value, preserved extra fields, tags, field types and nanoseconds')
            bucket=json.loads(curl('GET','/api/v2/buckets?org='+ORG+'&name='+BUCKET)[1])['buckets'][0]
            completed=subprocess.run(['docker','exec',CONTAINER,'influx','v1','dbrp','create','--db',BUCKET,'--rp','autogen',
                '--bucket-id',bucket['id'],'--default','--org',ORG,'--token',TOKEN],capture_output=True,text=True)
            assert completed.returncode==0,completed.stderr
            shim=folder/'curl';shim.write_text(SHIM);shim.chmod(0o700)
            env={**os.environ,'PATH':str(folder)+os.pathsep+os.environ['PATH'],'TEST_CONTAINER':CONTAINER}
            # Full deletion includes older and future values, without user time bounds.
            write('Whole value=1.0 978307200000000001\nWhole value=2.0 1893456000000000001')
            full=script(folder,'delete-influxdb2-measurement.sh')
            completed=subprocess.run(['/bin/bash',str(full),'Whole'],env=env,capture_output=True,text=True,timeout=100)
            assert completed.returncode==0,completed.stdout+completed.stderr
            api.query(move.read_query(BUCKET,'Whole'),folder/'whole-check.csv')
            assert not (folder/'whole-check.csv').read_text().strip()
            print('PASS real InfluxDB 2.9: complete DROP MEASUREMENT through compatibility API')
            # Delete only one timestamp interval; leave the point 1 ns after its stop.
            write(f'Range value=1.0 {t1}\nRange value=3.0 {t1-1+10**9}\nRange value=2.0 {t3}')
            ranged=script(folder,'delete-influxdb2-measurement-timerange.sh',START='2026-01-01T00:00:00Z',STOP='2026-01-01T00:00:01Z')
            completed=subprocess.run(['/bin/bash',str(ranged),'Range'],env=env,capture_output=True,text=True,timeout=100)
            assert completed.returncode==0,completed.stdout+completed.stderr
            api.query(move.read_query(BUCKET,'Range'),folder/'range-check.csv')
            assert '2026-01-01T00:00:05.000000001Z' in (folder/'range-check.csv').read_text()
            assert '2026-01-01T00:00:00.000000001Z' not in (folder/'range-check.csv').read_text()
            assert '2026-01-01T00:00:01Z' not in (folder/'range-check.csv').read_text()
            print('PASS real InfluxDB 2.9: timerange deletion includes its stop and preserves out-of-range data')
            write(f'Wrong,item=Wrong,room=lab value=1.0,extra="remove" {t1}\nWrong,item=Wrong,room=lab value=50.0 {t2}')
            wrong=script(folder,'delete-wrong-influxdb2-measurements.sh',OPERATOR='<',THRESHOLD='2')
            completed=subprocess.run(['/bin/bash',str(wrong),'Wrong'],env=env,capture_output=True,text=True,timeout=100)
            assert completed.returncode==0,completed.stdout+completed.stderr
            api.query(move.read_query(BUCKET,'Wrong'),folder/'wrong-check.csv')
            remaining=(folder/'wrong-check.csv').read_text()
            assert '2026-01-01T00:00:00.000000002Z' in remaining,remaining
            assert '2026-01-01T00:00:00.000000001Z' not in remaining,remaining
            print('PASS real InfluxDB 2.9: field comparison, complete tag predicates and exact single-timestamp point deletion')
            write(f'IntegerConflict value=1.0 {t1}')
            log=folder/'openhab.log'
            log.write_text('field type conflict: input field "value" on measurement "IntegerConflict" is type integer\n')
            integer=script(folder,'cleanup-influxdb2-integer.sh',OPENHAB_LOG=str(log))
            completed=subprocess.run(['/bin/bash',str(integer)],env=env,capture_output=True,text=True,timeout=100)
            assert completed.returncode==0,completed.stdout+completed.stderr
            api.query(move.read_query(BUCKET,'IntegerConflict'),folder/'integer-check.csv')
            assert not (folder/'integer-check.csv').read_text().strip()
            print('PASS real InfluxDB 2.9: conflict-log tool drops entire measurement')
            write(f'Orphan value=1.0 {t1}\nKeep value=1.0 {t1}')
            cleanup=script(folder,'cleanup-openhab-influxdb2.sh',OPENHAB_URL='https://openhab.invalid',OPENHAB_TOKEN='test-openhab-token')
            completed=subprocess.run(['/bin/bash',str(cleanup)],env=env,capture_output=True,text=True,timeout=100)
            assert completed.returncode==0,completed.stdout+completed.stderr
            api.query(move.read_query(BUCKET,'Orphan'),folder/'orphan-check.csv')
            api.query(move.read_query(BUCKET,'Keep'),folder/'keep-check.csv')
            assert not (folder/'orphan-check.csv').read_text().strip()
            assert (folder/'keep-check.csv').read_text().strip()
            print('PASS real InfluxDB 2.9: complete orphan cleanup preserves mocked openHAB Item measurements')

    finally:
        subprocess.run(['docker','rm','--force',CONTAINER],capture_output=True)


if __name__ == "__main__":
    main()

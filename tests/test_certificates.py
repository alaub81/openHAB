# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Exercise certificate setup only in a temporary copy of the repository paths."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'certs').mkdir()
        self.script=self.root/'certs/generate-certs.sh'
        shutil.copyfile(ROOT/'certs/generate-certs.sh',self.script)

    def run_script(self,*args,ok=True):
        result=subprocess.run(['/bin/bash',str(self.script),*args],env={**os.environ,'MQTT_HOST':'mqtt.example.invalid'},text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode==0,ok,result.stdout+result.stderr)
        return result

    def test_default_dry_run_creates_nothing(self):
        self.run_script()
        self.assertEqual(list(self.root.rglob('*')),[self.root/'certs',self.script])

    def test_existing_key_is_never_overwritten(self):
        key=self.root/'certs/ca.key';key.write_text('retain me')
        self.run_script('--execute',ok=False)
        self.assertEqual(key.read_text(),'retain me')
        self.assertFalse((self.root/'certs/server.crt').exists())

    @unittest.skipUnless(shutil.which('openssl'),'OpenSSL not installed')
    def test_fresh_certificate_generation_and_repeat_refusal(self):
        self.run_script('--execute')
        certs=self.root/'certs'
        subprocess.run(['openssl','verify','-CAfile',str(certs/'ca.crt'),str(certs/'server.crt'),str(certs/'client.crt')],capture_output=True,check=True)
        result=subprocess.run(['openssl','x509','-in',str(certs/'server.crt'),'-text','-noout'],capture_output=True,text=True,check=True)
        self.assertIn('DNS:mqtt.example.invalid',result.stdout)
        broker=self.root/'data/mosquitto/conf/certs'
        self.assertEqual({p.name for p in broker.iterdir()},{'ca.crt','server.crt','server.key'})
        self.assertEqual((certs/'ca.key').stat().st_mode & 0o777,0o600)
        original=(certs/'ca.key').read_bytes()
        self.run_script('--execute',ok=False)
        self.assertEqual((certs/'ca.key').read_bytes(),original)


if __name__=='__main__':
    unittest.main()

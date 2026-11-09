# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Migration safety checks using a fake requests module; no network dependency."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class ShellyMigrationTests(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('requests')
        fake.Session = Mock
        spec = importlib.util.spec_from_file_location('shelly_migration',ROOT/'tools/migrate_shelly_links.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules',requests=fake):
            spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.backup = Path(self.temp.name)/'links.json'
        m=self.module
        m.DRY_RUN=False
        m.BACKUP_FILE=self.backup
        m.OPENHAB_URL='https://openhab.invalid'
        m.LOGFILE='unused.log'
        self.old='shelly:device:example:meter#currentWatts'
        self.new='shelly:device:example:meter#currentPower'
        self.links=[dict(itemName='MyPower',channelUID=self.old,configuration={'profile':'default'})]
        m.parse_logfile=Mock(return_value={('device','meter#currentWatts'):'meter#currentPower'})
        m.build_shelly_lookup=Mock(return_value={'device':'shelly:device:example'})
        m.find_channel=Mock(side_effect=lambda things,uid,ch:dict(uid=self.old if ch.endswith('Watts') else self.new,itemType='Number:Power'))
        m.get_item_type=Mock(return_value='Number:Power')
        m.get_json=Mock(side_effect=lambda path: [{'UID':'shelly:device:example'}] if path=='/rest/things' else self.links)
        m.request=Mock()
        self.output=io.StringIO()
        self.addCleanup(self.output.close)

    def run_main(self):
        with redirect_stdout(self.output):
            self.module.main()

    def test_default_preview_does_not_write_backup_or_links(self):
        self.module.DRY_RUN=True
        self.run_main()
        self.module.request.assert_not_called()
        self.assertFalse(self.backup.exists())

    def test_backup_and_create_before_delete(self):
        self.run_main()
        self.assertEqual(json.loads(self.backup.read_text()),self.links)
        self.assertEqual(self.backup.stat().st_mode & 0o777,0o600)
        self.assertEqual([c.args[0] for c in self.module.request.call_args_list],['PUT','DELETE'])
        self.assertEqual(self.module.request.call_args_list[0].kwargs['json']['configuration'],{'profile':'default'})

    def test_failed_create_never_deletes_original(self):
        self.module.request.side_effect=RuntimeError('failed write')
        with self.assertRaises(RuntimeError):
            self.run_main()
        self.assertEqual([c.args[0] for c in self.module.request.call_args_list],['PUT'])
        self.assertTrue(self.backup.exists())

    def test_existing_target_is_not_overwritten(self):
        self.links.append(dict(itemName='MyPower',channelUID=self.new,configuration={'profile':'special'}))
        self.run_main()
        self.module.request.assert_not_called()
        self.assertFalse(self.backup.exists())

    def test_existing_backup_refuses_all_writes(self):
        self.backup.write_text('retain me')
        with self.assertRaises(FileExistsError):
            self.run_main()
        self.module.request.assert_not_called()
        self.assertEqual(self.backup.read_text(),'retain me')

    def test_changed_links_refuse_all_writes(self):
        self.module.get_json.side_effect=[[{'UID':'shelly:device:example'}],self.links,[]]
        with self.assertRaises(RuntimeError):
            self.run_main()
        self.module.request.assert_not_called()
        self.assertFalse(self.backup.exists())

    def test_failed_preflight_read_refuses_all_writes(self):
        self.module.get_item_type.side_effect=RuntimeError('failed Item lookup')
        with self.assertRaises(RuntimeError):
            self.run_main()
        self.module.request.assert_not_called()
        self.assertFalse(self.backup.exists())

    def test_http_wrapper_times_out_and_rejects_redirects(self):
        # Restore the real wrapper to exercise its request options.
        method=self.module.request
        spec=importlib.util.spec_from_file_location('shelly_wrapper',ROOT/'tools/migrate_shelly_links.py')
        module=importlib.util.module_from_spec(spec)
        fake=types.ModuleType('requests'); fake.Session=Mock
        with patch.dict('sys.modules',requests=fake):
            spec.loader.exec_module(module)
        module.OPENHAB_URL='https://openhab.invalid'
        module.session.request.return_value.status_code=302
        with self.assertRaises(RuntimeError):
            module.request('GET','/rest/links')
        self.assertEqual(module.session.request.call_args.kwargs,dict(timeout=(5,30),allow_redirects=False))
        method.assert_not_called()


if __name__=='__main__':
    unittest.main()

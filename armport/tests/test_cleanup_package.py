"""The reviewed cleanup port must reach the staged guest and retain exact pins.

The ARM64 archive reader is mocked; this exercises actual guest staging and
the APK builder's changed-payload boundary, without building or signing an APK.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import build_thor_apk as apk
import stage_app_assets as stage


class CleanupPackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.source = self.work / 'donor'
        self.source.mkdir()
        self.helper = 'game_device_diagnostic.py'
        (self.source / self.helper).write_bytes(b'# authenticated retained cleanup helper\n')
        self.old_pin = stage.pin(self.source / self.helper)
        client = {'format': 1, 'scope': 'actual_client_startup_guest',
                  'files': {self.helper: self.old_pin}}
        (self.source / 'client-manifest.json').write_bytes(stage.encoded(client))
        runtime = {'format': 1, 'files': {
            **client['files'], 'client-manifest.json': stage.pin(self.source / 'client-manifest.json')}}
        (self.source / 'runtime-manifest.json').write_bytes(stage.encoded(runtime))
        self.armport = self.work / 'client.zip'
        self.armport.write_bytes(b'archive-reader fixture')
        self.output = self.work / 'staged'
        self.document = {'files': {'CityOfHeroes.exe': {'sha256': 'c' * 64}},
                         'client_run_id': 123, 'data_run_id': 123}

    def test_existing_donor_cleanup_helper_is_replaced_and_admitted_once(self):
        with mock.patch.object(stage.package, 'unpack', return_value=self.document):
            stage.stage(self.source, self.armport, self.output, '2' * 40)
        current = ROOT / 'android/guest' / self.helper
        self.assertEqual((self.output / self.helper).read_bytes(), current.read_bytes())
        actual = stage.pin(current)
        self.assertNotEqual(actual, self.old_pin)
        for name in ('client-manifest.json', 'runtime-manifest.json'):
            manifest = json.loads((self.output / name).read_text())
            self.assertEqual(manifest['files'][self.helper], actual)
            self.assertEqual(list(manifest['files']).count(self.helper), 1)
        runtime = json.loads((self.output / 'runtime-manifest.json').read_text())
        self.assertEqual(runtime['files']['client-manifest.json'],
                         stage.pin(self.output / 'client-manifest.json'))
        self.assertIn(self.helper, apk.CHANGED_RUNTIME)
        self.assertNotIn(self.helper, apk.ADDED_RUNTIME)

    def test_altered_donor_cleanup_helper_is_rejected_before_staging(self):
        (self.source / self.helper).write_bytes(b'# unauthenticated donor helper\n')
        with mock.patch.object(stage.package, 'unpack', return_value=self.document), \
                self.assertRaisesRegex(ValueError, 'Donor app payload differs: ' + self.helper):
            stage.stage(self.source, self.armport, self.output, '2' * 40)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()

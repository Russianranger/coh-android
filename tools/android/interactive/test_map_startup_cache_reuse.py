"""Check authenticated data-generation reuse; host reader fixtures are not native proof."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools/android/interactive'), str(ROOT/'tools'), str(ROOT/'android/guest')]
import local_character_server as server
import test_map_startup_native_contract as fixtures


class StartupCacheGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MapStartupContractReaderTests.setUpClass()
        cls.fixture = fixtures.MapStartupContractReaderTests()

    def instance(self, root, package, raw=None):
        value = object.__new__(server.LocalCharacterServer)
        value.map_package = copy.deepcopy(package)
        value.map_package_dir = root
        value.creation_report = {}
        if raw is not None: (root/'MapServer.exe').write_bytes(raw)
        return value

    def test_historical_package_returns_unchanged_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            value = self.instance(Path(tmp), self.fixture.old)
            self.assertEqual(value.data_cache_native_package(), self.fixture.old)
            self.assertEqual(value.creation_report, {})

    def test_exact_new_consumer_reuses_original_generation_and_reports_actual_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self.fixture.candidate()
            value = self.instance(Path(tmp), package, self.fixture.raw)
            self.assertEqual(value.data_cache_native_package(), self.fixture.old)
            self.assertEqual(value.map_package, package)
            proof = value.creation_report['server_data_cache_native_consumer']
            self.assertEqual(proof['actual_mapserver_sha256'], package['files']['MapServer.exe']['sha256'])
            self.assertTrue(proof['cache_donor_identity_preserved'])
            self.assertFalse(proof['physical_loading_gain_validated'])

    def test_changed_candidate_bytes_cannot_borrow_historical_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            value = self.instance(Path(tmp), self.fixture.candidate(), b'changed native bytes')
            with self.assertRaises(ValueError): value.data_cache_native_package()
            self.assertEqual(value.creation_report, {})

    def test_changed_parser_sources_cannot_borrow_historical_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self.fixture.candidate()
            package['native_map_startup']['receipt']['build_input']['retained_sources_sha256']['Common/fxinfo.c'] = '0'*64
            self.fixture.reseal(package)
            value = self.instance(Path(tmp), package, self.fixture.raw)
            with self.assertRaises(ValueError): value.data_cache_native_package()

    def test_changed_dependency_cannot_borrow_historical_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self.fixture.candidate()
            name = next(n for n in package['files'] if n != 'MapServer.exe')
            package['files'][name]['sha256'] = '0'*64
            package['native_map_startup']['receipt']['retained_native_files'][name]['sha256'] = '0'*64
            self.fixture.reseal(package)
            value = self.instance(Path(tmp), package, self.fixture.raw)
            with self.assertRaises(ValueError): value.data_cache_native_package()


if __name__ == '__main__': unittest.main()

"""0.13.76: the guest names the cooked mesh file and passes it only to an admitted server."""
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server

SHA = 'ab' * 32


class Owner:
    def __init__(self, root):
        self.root = root


def method():
    for name in dir(server):
        cls = getattr(server, name)
        if isinstance(cls, type) and 'map_metrics_environment' in vars(cls):
            return vars(cls)['map_metrics_environment']
    raise AssertionError('map_metrics_environment not found')


class PhysxCacheGuest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.metrics = types.SimpleNamespace(
            verify_current_map=lambda path, package: None, trusted_bins_available=lambda: True,
            physx_cache_available=lambda: True)
        patcher = mock.patch.dict(sys.modules, {'armport_server_metrics_contract': self.metrics})
        patcher.start(); self.addCleanup(patcher.stop)

    def run_it(self, package, environment):
        value = types.SimpleNamespace(owner=Owner(self.root), map_package=package, creation_report={})
        with mock.patch.dict(os.environ, environment, clear=False):
            for key in ('COH_PHYSX_CACHE', 'COH_TRUSTED_BINS'):
                if key not in environment:
                    os.environ.pop(key, None)
            result = method()(value, {'ARMPORT_PHYSX_CACHE': 'Z:\\stale', 'KEEP': '1'}, self.root / 'runtime')
        return result, value.creation_report['physx_cache']

    def test_requested_and_admitted_passes_one_file_per_server_build(self):
        package = {'armport_server_metrics': {}, 'files': {'MapServer.exe': {'sha256': SHA}}}
        environment, record = self.run_it(package, {'COH_PHYSX_CACHE': '1'})
        path = self.root / 'physx-cooked' / ('meshes-' + SHA[:24] + '.bin')
        self.assertEqual(environment['ARMPORT_PHYSX_CACHE'], server.base.windows_path(path))
        self.assertEqual(environment['KEEP'], '1')
        self.assertEqual((self.root / 'physx-cooked').stat().st_mode & 0o777, 0o700)
        self.assertEqual(record, {'format': 1, 'requested': True, 'applied': True,
                                  'environment_variable': 'ARMPORT_PHYSX_CACHE', 'file': path.name,
                                  'bytes_before_start': 0, 'reason': None})
        path.write_bytes(b'x' * 77)
        _, record = self.run_it(package, {'COH_PHYSX_CACHE': '1'})
        self.assertEqual(record['bytes_before_start'], 77)

    def test_not_requested_removes_an_inherited_variable(self):
        package = {'armport_server_metrics': {}, 'files': {'MapServer.exe': {'sha256': SHA}}}
        environment, record = self.run_it(package, {})
        self.assertNotIn('ARMPORT_PHYSX_CACHE', environment)
        self.assertEqual((record['requested'], record['applied'], record['reason']), (False, False, 'not_requested'))
        self.assertFalse((self.root / 'physx-cooked').exists())

    def test_the_0_13_36_server_and_a_build_without_the_layer_cook_as_before(self):
        environment, record = self.run_it({'files': {'MapServer.exe': {'sha256': SHA}}}, {'COH_PHYSX_CACHE': '1'})
        self.assertNotIn('ARMPORT_PHYSX_CACHE', environment)
        self.assertEqual((record['applied'], record['reason']), (False, 'no_metrics_mapserver'))
        self.metrics.physx_cache_available = lambda: False
        package = {'armport_server_metrics': {}, 'files': {'MapServer.exe': {'sha256': SHA}}}
        environment, record = self.run_it(package, {'COH_PHYSX_CACHE': '1'})
        self.assertNotIn('ARMPORT_PHYSX_CACHE', environment)
        self.assertEqual((record['applied'], record['reason']), (False, 'switch_not_in_admitted_build'))

    def test_a_link_or_a_bad_identity_never_stops_the_start(self):
        package = {'armport_server_metrics': {}, 'files': {'MapServer.exe': {'sha256': 'short'}}}
        environment, record = self.run_it(package, {'COH_PHYSX_CACHE': '1'})
        self.assertNotIn('ARMPORT_PHYSX_CACHE', environment)
        self.assertEqual((record['applied'], record['reason']), (False, 'error'))
        (self.root / 'elsewhere').mkdir()
        (self.root / 'physx-cooked').symlink_to(self.root / 'elsewhere')
        package['files']['MapServer.exe']['sha256'] = SHA
        environment, record = self.run_it(package, {'COH_PHYSX_CACHE': '1'})
        self.assertNotIn('ARMPORT_PHYSX_CACHE', environment)
        self.assertEqual((record['applied'], record['reason']), (False, 'error'))
        self.assertEqual(list((self.root / 'elsewhere').iterdir()), [])


if __name__ == '__main__':
    unittest.main()

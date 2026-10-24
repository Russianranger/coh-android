"""Exercise the cache-producer rejection path that failed in the retained guest."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import stage_app_assets
import server_cache_package


class CacheDependency(unittest.TestCase):
    def test_unsupported_producer_remains_rejected_with_dependencies_present(self):
        self.assertIn('native_monorail_contract.py', stage_app_assets.GUEST_DEPENDENCIES)
        self.assertIn('native_map_startup_contract.py', stage_app_assets.GUEST_DEPENDENCIES)
        with tempfile.TemporaryDirectory() as temporary:
            exe = Path(temporary) / 'MapServer.exe'
            exe.write_bytes(b'unqualified producer')
            with self.assertRaisesRegex(ValueError, 'Monorail native identity differs'):
                server_cache_package.verify_mapserver_compatibility(exe, {})

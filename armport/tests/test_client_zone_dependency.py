"""The optional-zone presence checker is a mandatory server dependency."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))
sys.path.insert(0, str(ROOT / 'android/guest'))
import stage_app_assets
import zone_asset_package
from diagnostic import DiagnosticError


class ZoneDependency(unittest.TestCase):
    def test_helper_alone_does_not_enable_optional_payloads(self):
        self.assertIn('zone_asset_package.py', stage_app_assets.GUEST_DEPENDENCIES)
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary)
            (assets / 'zone_asset_package.py').write_text('helper only')
            self.assertFalse(zone_asset_package.present(assets))
            self.assertFalse(zone_asset_package.present(assets, audio=True))
            (assets / zone_asset_package.ARCHIVE).write_bytes(b'incomplete')
            with self.assertRaisesRegex(DiagnosticError, 'Incomplete all-zone'):
                zone_asset_package.present(assets)


if __name__ == '__main__':
    unittest.main()

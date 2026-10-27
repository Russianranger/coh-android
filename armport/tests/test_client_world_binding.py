"""Retained world bytes must keep their own pins with current validation code."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))
import stage_app_assets as stage


class WorldBinding(unittest.TestCase):
    def setUp(self):
        self.current = (ROOT / 'android/guest/atlas_world_assets.py').read_text()
        self.donor = ("MANIFEST_SHA256 = '" + '1' * 64 + "'\n"
                      "ARCHIVE_SHA256 = '" + '2' * 64 + "'\n"
                      "ARCHIVE_BYTES, PAYLOAD_BYTES, FILE_COUNT = 101, 202, 3\n"
                      "FILES_SHA256 = '" + '3' * 64 + "'\n")

    def normalized(self, raw):
        tree = ast.parse(raw)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(n, ast.Name) and n.id in stage.WORLD_PINS
                    for target in node.targets for n in ast.walk(target)):
                node.value = ast.Constant('pin')
        return ast.dump(tree, include_attributes=False)

    def test_old_archive_pins_with_current_validation_unchanged(self):
        bound = stage.bind_world_helper(self.current, self.donor)
        self.assertEqual(stage.world_pin_values(bound)[0], stage.world_pin_values(self.donor)[0])
        self.assertEqual(self.normalized(bound), self.normalized(self.current))
        self.assertIn("'World archive size differs from reviewed payload bytes'", bound)

    def test_reject_missing_duplicate_and_executable_pins(self):
        for bad in (self.donor.replace('FILE_COUNT', 'OTHER'),
                    self.donor + 'FILE_COUNT = 8\n',
                    self.donor.replace('101, 202, 3', "__import__('os').getpid(), 202, 3"),
                    self.donor.replace('101, 202, 3', 'True, 202, 3')):
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                stage.bind_world_helper(self.current, bad)


if __name__ == '__main__':
    unittest.main()

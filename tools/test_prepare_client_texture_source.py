from pathlib import Path
import shutil
import tempfile
import unittest

import prepare_client_texture_source as source


class TextureSourceTests(unittest.TestCase):
    def test_overlay_closure_and_unchanged_parsers(self):
        expected = source.expected_texture_receipt()
        self.assertFalse(expected['parse6_schema_changes'])
        self.assertFalse(expected['full_texture_asset_changes'])
        self.assertEqual(set(source.FILES), set(expected['patched_sha256']))
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary)
            for name in source.FILES:
                target = staged / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source.ROOT / 'upstream/ouroboros' / name, target)
            receipt = source.apply_texture_overlay(staged)
            self.assertEqual(expected, receipt)
            self.assertTrue((staged / source.RECEIPT).is_file())
            self.assertEqual(expected['overlay_sha256'][source.OVERLAY_FILE], source.digest(staged / source.OVERLAY_FILE))
            with self.assertRaisesRegex(ValueError, 'Fresh'):
                source.apply_texture_overlay(staged)
        for name, digest in expected['source_sha256'].items():
            self.assertEqual(digest, source.digest(source.ROOT / 'upstream/ouroboros' / name))

    def test_mismatched_input_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary)
            for name in source.FILES:
                target = staged / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source.ROOT / 'upstream/ouroboros' / name, target)
            (staged / source.FILES[0]).write_text('altered source')
            with self.assertRaisesRegex(ValueError, 'closure differs'):
                source.apply_texture_overlay(staged)

    def test_overlay_crlf_checkout_has_identical_receipt_and_installs_lf(self):
        expected = source.expected_texture_receipt()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repository'
            staged = Path(temporary) / 'staged'
            staged.mkdir()
            for name in (*source.FILES,):
                original = source.ROOT / 'upstream/ouroboros' / name
                destination = root / 'upstream/ouroboros' / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(original.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
                target = staged / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            for name in (source.PATCH, source.OVERLAY + '/' + source.OVERLAY_FILE, 'upstream-lock.json'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                value = (source.ROOT / name).read_bytes().replace(b'\r\n', b'\n')
                target.write_bytes(value.replace(b'\n', b'\r\n'))
            self.assertEqual(expected, source.expected_texture_receipt(root))
            self.assertEqual(expected, source.apply_texture_overlay(staged, root))
            self.assertNotIn(b'\r\n', (staged / source.OVERLAY_FILE).read_bytes())
            for name in source.FILES:
                self.assertNotIn(b'\r\n', (staged / name).read_bytes())
                self.assertIn(b'\r\n', (root / 'upstream/ouroboros' / name).read_bytes())


if __name__ == '__main__': unittest.main()

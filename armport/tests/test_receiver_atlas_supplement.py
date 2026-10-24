import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stage_atlas_supplement as atlas


class AtlasSupplement(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'atlas.zip'
        self.name = 'data/texture_library/test.texture'
        self.data = b'original texture'
        self.document = dict(file_count=1, payload_bytes=len(self.data), files={
            self.name: dict(bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())})
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr(self.name, self.data)

    def test_original_bytes_and_existing_conflicts(self):
        output = self.root / 'data'
        atlas.unpack(self.archive, self.document, output)
        target = output / 'texture_library/test.texture'
        self.assertEqual(target.read_bytes(), self.data)
        atlas.unpack(self.archive, self.document, output)
        target.write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'replace different'):
            atlas.unpack(self.archive, self.document, output)
        self.assertEqual(target.read_bytes(), b'different')

    def test_no_extra_members_or_bad_hashes(self):
        self.document['files'][self.name]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            atlas.unpack(self.archive, self.document, self.root / 'data')
        with zipfile.ZipFile(self.archive, 'a') as z:
            z.writestr('data/extra.texture', b'extra')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            atlas.unpack(self.archive, self.document, self.root / 'data')

    def test_parent_links_refused(self):
        output = self.root / 'data'
        output.mkdir()
        (output / 'texture_library').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Linked'):
            atlas.unpack(self.archive, self.document, output)

    def test_recovery_rejects_other_apk(self):
        with self.assertRaisesRegex(ValueError, 'APK identity'):
            atlas.recover(self.archive, self.root / 'out')

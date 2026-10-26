import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stage_atlas_materials as material


class AtlasMaterials(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / 'materials.zip'
        self.output = self.root / 'layer'
        self.name = 'data/texture_library/atlas.texture'
        self.raw = b'reviewed material'
        self.selected = {self.name: dict(bytes=len(self.raw), sha256=hashlib.sha256(self.raw).hexdigest())}
        # The baseline is in the archive but must not leak into the delta layer.
        with zipfile.ZipFile(self.archive, 'w') as value:
            value.writestr(self.name, self.raw)
            value.writestr('data/object_library/baseline.geo', b'baseline')
        self.document = dict(archive=dict(bytes=self.archive.stat().st_size,
            sha256=material.digest(self.archive)), files=self.selected | {
                'data/object_library/baseline.geo': dict(bytes=8, sha256=hashlib.sha256(b'baseline').hexdigest())})

    def stage(self):
        material.stage(self.archive, self.document, self.selected, self.output)

    def test_stages_only_selected_files(self):
        self.stage()
        self.assertEqual(material.verify(self.output, self.selected)['files'], 1)
        self.assertFalse((self.output / 'object_library').exists())

    def test_wrong_archive_rejected_before_output(self):
        self.archive.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'archive identity'):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_wrong_member_rejected_atomically(self):
        self.selected[self.name]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'member digest'):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_cache_mutation_missing_and_extra_rejected(self):
        self.stage()
        target = self.output / self.name.removeprefix('data/')
        for content in (b'changed', b''):
            target.write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'digest differs'):
                material.verify(self.output, self.selected)
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            material.verify(self.output, self.selected)
        target.write_bytes(self.raw)
        (self.output / 'extra').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            material.verify(self.output, self.selected)

    def test_output_collision_preserves_existing_file(self):
        self.output.mkdir()
        (self.output / 'keep').write_bytes(b'untouched')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.stage()
        self.assertEqual((self.output / 'keep').read_bytes(), b'untouched')

    def test_links_rejected(self):
        self.stage()
        target = self.output / self.name.removeprefix('data/')
        target.unlink()
        target.symlink_to(self.archive)
        with self.assertRaisesRegex(ValueError, 'Linked'):
            material.verify(self.output, self.selected)
        parent = self.root / 'alias'
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Linked'):
            material.stage(self.archive, self.document, self.selected, parent / 'new-layer')


if __name__ == '__main__':
    unittest.main()

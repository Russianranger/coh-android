import hashlib
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stage_atlas_supplement as atlas
import smoke_run


class AtlasSupplement(unittest.TestCase):
    def setUp(self):
        # Deliberately rejected fixtures must not emit CI error annotations.
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
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

    def test_reviewed_subset_requires_matching_size_and_hash(self):
        import copy
        atlas.verify_reviewed_subset(self.document, self.document)
        for mutation in ('missing', 'sha256', 'bytes'):
            reviewed = copy.deepcopy(self.document)
            if mutation == 'missing':
                reviewed['files'].clear()
            else:
                reviewed['files'][self.name][mutation] = 0
            with self.assertRaisesRegex(ValueError, 'repository manifest'):
                atlas.verify_reviewed_subset(self.document, reviewed)

    def test_runtime_collision_checked_before_any_supplement_copy(self):
        source, dest = self.root / 'supplement', self.root / 'runtime'
        source.mkdir(); dest.mkdir()
        (source / 'new.texture').write_bytes(b'new')
        (source / 'overlap.texture').write_bytes(b'reviewed')
        (dest / 'OVERLAP.texture').write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'earlier data'):
            smoke_run.merge_tree(source, dest, strict=True)
        self.assertFalse((dest / 'new.texture').exists())
        self.assertEqual((dest / 'OVERLAP.texture').read_bytes(), b'different')
        (dest / 'OVERLAP.texture').write_bytes(b'reviewed')
        self.assertEqual(smoke_run.merge_tree(source, dest, strict=True), 1)
        self.assertFalse((dest / 'overlap.texture').exists())
        self.assertEqual((dest / 'new.texture').read_bytes(), b'new')

    def test_shadowed_earlier_layer_conflict_is_not_hidden(self):
        first, second, source, dest = (self.root / name for name in ('first', 'second', 'source', 'runtime'))
        for root in (first, second, source): root.mkdir()
        for root, data in ((first, b'first'), (second, b'shadowed'), (source, b'first')):
            (root / 'overlap.texture').write_bytes(data)
        smoke_run.merge_tree(first, dest)
        smoke_run.merge_tree(second, dest)
        with self.assertRaisesRegex(ValueError, 'earlier data'):
            smoke_run.merge_tree(source, dest, strict=True, earlier_roots=[first, second])

    def test_geometry_joins_original_case_directory(self):
        first, source, dest = (self.root / name for name in ('first', 'source', 'runtime'))
        original = Path('object_library/Villain_Lairs/office01/Trays/Start')
        lower = Path(str(original).lower())
        (first / original).mkdir(parents=True)
        (source / lower).mkdir(parents=True)
        (first / original / 'start.rootnames').write_bytes(b'Def _ofc1_start_01')
        (source / lower / 'start.geo').write_bytes(b'reviewed geometry')
        smoke_run.merge_tree(first, dest)
        smoke_run.merge_tree(source, dest, strict=True, earlier_roots=[first])
        self.assertEqual((dest / original / 'start.geo').read_bytes(), b'reviewed geometry')
        self.assertFalse((dest / lower).exists())
        folded = [p.relative_to(dest).as_posix().casefold() for p in dest.rglob('*')]
        self.assertEqual(len(folded), len(set(folded)))

    def test_case_alias_file_keeps_first_layer_bytes(self):
        first, second, dest = (self.root / name for name in ('first', 'second', 'runtime'))
        (first / 'Textures').mkdir(parents=True)
        (second / 'textures').mkdir(parents=True)
        (first / 'Textures/White.texture').write_bytes(b'first')
        (second / 'textures/white.texture').write_bytes(b'second')
        smoke_run.merge_tree(first, dest)
        smoke_run.merge_tree(second, dest)
        self.assertEqual((dest / 'Textures/White.texture').read_bytes(), b'first')
        self.assertEqual(len([p for p in dest.rglob('*') if p.is_file()]), 1)

    def test_ambiguous_existing_directory_is_rejected(self):
        source, dest = self.root / 'source', self.root / 'runtime'
        source.mkdir(); dest.mkdir()
        (dest / 'Textures').mkdir(); (dest / 'textures').mkdir()
        (source / 'new.texture').write_bytes(b'new')
        with self.assertRaisesRegex(ValueError, 'Case-ambiguous'):
            smoke_run.merge_tree(source, dest)
        self.assertFalse((dest / 'new.texture').exists())

    def test_file_directory_case_collision_is_rejected(self):
        for existing_directory in (False, True):
            with self.subTest(existing_directory=existing_directory):
                root = self.root / str(existing_directory)
                source, dest = root / 'source', root / 'runtime'
                source.mkdir(parents=True); dest.mkdir()
                if existing_directory:
                    (dest / 'Textures').mkdir()
                    (source / 'textures').write_bytes(b'file')
                else:
                    (dest / 'Textures').write_bytes(b'file')
                    (source / 'textures').mkdir()
                    (source / 'textures/new.texture').write_bytes(b'new')
                with self.assertRaisesRegex(ValueError, 'conflicts with an existing entry'):
                    smoke_run.merge_tree(source, dest)

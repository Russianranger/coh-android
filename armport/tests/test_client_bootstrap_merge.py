"""The app bootstrap uses M3's reviewed case-equivalent merger."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import smoke_run


class ClientBootstrapMerge(unittest.TestCase):
    def setUp(self):
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

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

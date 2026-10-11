"""Host preflight mechanics; real payload installers run in the release gate."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('runtime_asset_preflight', Path(__file__).with_name('qualify_runtime_asset_preflight.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def pin(raw): return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class RuntimeAssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root/'runtime'; self.runtime.mkdir()

    def test_materializes_only_hash_matching_original_sources(self):
        path = self.root/'source.zip'
        raw = b'exact original input'; name = 'data/object_library/example.geo'
        with zipfile.ZipFile(path, 'w') as z: z.writestr('assets/'+name[5:], raw); z.writestr('assets/unrelated.bin', b'not selected')
        with zipfile.ZipFile(path) as z:
            result = module.materialize(self.runtime, {name: pin(raw)}, [z], {})
        self.assertEqual(result['files'], 1)
        self.assertEqual((self.runtime/name).read_bytes(), raw)
        self.assertFalse((self.runtime/'data/unrelated.bin').exists())
        self.assertEqual((self.runtime/name).stat().st_mode & 0o222, 0)

    def test_wrong_bytes_and_missing_source_are_refused(self):
        name = 'data/defs/example.attribute'
        for source in ({}, {name: b'different data'}):
            with self.subTest(source=bool(source)), self.assertRaisesRegex(ValueError, 'source missing'):
                module.materialize(self.runtime, {name: pin(b'expected')}, [], source)
        self.assertFalse((self.runtime/name).exists())

    def test_unsafe_paths_and_existing_destination_are_refused(self):
        for name in ('../escape', '/absolute', 'data/../escape', 'data\\escape', 'data//escape'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unsafe'):
                module.materialize(self.runtime, {name: pin(b'payload')}, [], {name: b'payload'})
        name = 'data/defs/x.attribute'; path = self.runtime/name; path.parent.mkdir(parents=True); path.write_bytes(b'old')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            module.materialize(self.runtime, {name: pin(b'new')}, [], {name: b'new'})
        self.assertEqual(path.read_bytes(), b'old')

    def test_case_conflicting_zip_sources_are_refused(self):
        path = self.root/'source.zip'
        with zipfile.ZipFile(path, 'w') as z: z.writestr('data/x', b'1'); z.writestr('data/X', b'2')
        with zipfile.ZipFile(path) as z, self.assertRaisesRegex(ValueError, 'Case-conflicting'):
            module.materialize(self.runtime, {'data/x': pin(b'1')}, [z], {})

    def test_input_pin_rejects_mutation_and_symlinks(self):
        path = self.root/'source'; path.write_bytes(b'exact')
        module.checked(path, pin(b'exact'))
        path.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'pin differs'): module.checked(path, pin(b'exact'))
        link = self.root/'link'; link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'Regular'): module.checked(link, pin(b'other'))

    def test_receipt_normalization_retains_negative_scope_flags(self):
        value = {'elapsed_seconds': 1.2, 'native_runtime_booted': False,
                 'proof': [{'preparation_elapsed_seconds': 99, 'status': 'passed'}]}
        self.assertEqual(module.stable(value), {'native_runtime_booted': False, 'proof': [{'status': 'passed'}]})
        self.assertIn('elapsed_seconds', value)


if __name__ == '__main__': unittest.main()

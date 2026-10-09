#!/usr/bin/env python3
"""Adversarial fixture checks against the actual Java Android asset importer."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / 'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java'
HOST = Path(__file__).parent / 'java/io/github/russianranger/cohatlas/AssetImporterHost.java'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive(entries, *, symlink=None, directory=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            kind = stat.S_IFLNK if name == symlink else stat.S_IFDIR if name == directory else stat.S_IFREG
            info.external_attr = (kind | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return output.getvalue()


def index(entries):
    return ''.join(f'{len(data)}\t{sha(data)}\t{name}\n' for name, data in entries).encode('ascii')


class AssetImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java = shutil.which('java') or os.environ.get('ATLAS_JAVA')
        javac = shutil.which('javac') or os.environ.get('ATLAS_JAVAC')
        if not cls.java:
            raise unittest.SkipTest('A JDK is required for the actual Java importer fixture tests')
        cls.compiler = [javac] if javac else [cls.java, '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        cls.compile_dir = tempfile.TemporaryDirectory(prefix='coh-atlas-java-')
        subprocess.run(cls.compiler + ['--release', '8', '-d', cls.compile_dir.name, str(CORE), str(HOST)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'compile_dir'):
            cls.compile_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='coh-atlas-import-')
        self.root = Path(self.temp.name)
        self.assets = self.root / 'apk-assets'
        self.assets.mkdir()
        self.base = self.root / 'private'
        self.selected = self.root / 'selected.zip'
        self.asset_entries = [('assets/maps/atlas.bin', b'atlas map payload'), ('assets/texture/hero.texture', b'hero texture')]
        self.text_entries = [('data/defs/empty.def', b''), ('data/server/db/costume.txt', b'costume template\n')]
        self.manifest = b'{"fixture":"reviewed"}\n'
        self.build()

    def tearDown(self):
        self.temp.cleanup()

    def build(self, *, asset_entries=None, text_entries=None, zip_entries=None, index_entries=None, symlink=None, directory=None, user_bytes=None):
        a = self.asset_entries if asset_entries is None else asset_entries
        t = self.text_entries if text_entries is None else text_entries
        user = user_bytes if user_bytes is not None else archive([('asset-manifest.json', self.manifest)] + (a if zip_entries is None else zip_entries), symlink=symlink, directory=directory)
        text = archive(t)
        ai = index(a if index_entries is None else index_entries)
        ti = index(t)
        self.selected.write_bytes(user)
        (self.assets / 'atlas-text.zip').write_bytes(text)
        (self.assets / 'atlas-assets-index.tsv').write_bytes(ai)
        (self.assets / 'atlas-text-index.tsv').write_bytes(ti)
        properties = {
            'format': '1', 'source.commit': '1' * 40, 'data.commit': '2' * 40, 'repository.commit': '3' * 40,
            'asset.archive.bytes': str(len(user)), 'asset.archive.sha256': sha(user),
            'asset.manifest.bytes': str(len(self.manifest)), 'asset.manifest.sha256': sha(self.manifest),
            'asset.count': str(len(a)), 'asset.bytes': str(sum(len(b) for _, b in a)),
            'text.archive.bytes': str(len(text)), 'text.archive.sha256': sha(text),
            'text.count': str(len(t)), 'text.bytes': str(sum(len(b) for _, b in t)),
            'asset.index.bytes': str(len(ai)), 'asset.index.sha256': sha(ai),
            'text.index.bytes': str(len(ti)), 'text.index.sha256': sha(ti),
            'total.count': str(len(a) + len(t)), 'total.bytes': str(sum(len(b) for _, b in a + t)),
            'storage.reserve.bytes': str(256 * 1024 * 1024), 'storage.per.file.bytes': '4096',
        }
        self.write_properties(properties)
        return properties

    def write_properties(self, properties):
        (self.assets / 'atlas-import.properties').write_text(''.join(f'{k}={v}\n' for k, v in properties.items()), encoding='ascii')

    def run_import(self, mode='import'):
        result = subprocess.run([self.java, '-cp', self.compile_dir.name, 'io.github.russianranger.cohatlas.AssetImporterHost', str(self.assets), str(self.base), mode, str(self.selected)], check=True, capture_output=True, text=True)
        values = {}
        for line in result.stdout.splitlines():
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                values[k] = v.replace('\\:', ':').replace('\\=', '=')
        return values

    def assert_failed_unpublished(self, mode='import', *, status='error'):
        result = self.run_import(mode)
        self.assertEqual(status, result['status'], result)
        self.assertEqual('false', result['committed'])
        self.assertFalse((self.base / 'active.properties').exists())
        self.assertFalse(list(self.base.glob('.import-*')))
        self.assertFalse(list(self.base.glob('generation-*')))
        return result

    def test_complete_import_and_reimport_atomic_generation(self):
        first = self.run_import()
        self.assertEqual('ok', first['status'], first)
        self.assertEqual('false', first['stopAcceptedAfterCommit'])
        self.assertEqual('4', first['count'])
        data = Path(first['dataDirectory'])
        self.assertEqual(b'atlas map payload', (data / 'maps/atlas.bin').read_bytes())
        self.assertEqual(b'', (data / 'defs/empty.def').read_bytes())
        self.assertEqual(first['generation'], self.run_import('inspect')['generation'])
        second = self.run_import()
        self.assertEqual('ok', second['status'], second)
        self.assertNotEqual(first['generation'], second['generation'])
        self.assertEqual(second['generation'], self.run_import('inspect')['generation'])
        self.assertEqual('ok', self.run_import('recover')['status'])
        self.assertFalse(data.exists())

    def test_wrong_archive_hash_preserves_previous_generation(self):
        first = self.run_import()
        pointer = (self.base / 'active.properties').read_bytes()
        changed = bytearray(self.selected.read_bytes())
        changed[35] ^= 1
        self.selected.write_bytes(changed)
        self.assertEqual('error', self.run_import()['status'])
        self.assertEqual(pointer, (self.base / 'active.properties').read_bytes())
        self.assertEqual(first['generation'], self.run_import('inspect')['generation'])

    def test_truncated_untrusted_input(self):
        self.selected.write_bytes(self.selected.read_bytes()[:-9])
        self.assert_failed_unpublished()

    def test_oversized_untrusted_input(self):
        with self.selected.open('ab') as out:
            out.write(b'extra')
        self.assert_failed_unpublished()

    def test_unexpected_archive_member(self):
        self.build(zip_entries=self.asset_entries + [('assets/z/extra.bin', b'x')])
        self.assert_failed_unpublished()

    def test_missing_archive_member(self):
        self.build(zip_entries=self.asset_entries[:-1])
        self.assert_failed_unpublished()

    def test_out_of_order_member(self):
        self.build(zip_entries=list(reversed(self.asset_entries)))
        self.assert_failed_unpublished()

    def test_duplicate_paths(self):
        entries = [self.asset_entries[0], self.asset_entries[0]]
        self.build(asset_entries=entries)
        self.assert_failed_unpublished()

    def test_traversal_rejected_even_if_pinned(self):
        self.build(asset_entries=[('assets/../../escape', b'bad')])
        self.assert_failed_unpublished()
        self.assertFalse((self.root / 'escape').exists())

    def test_unsafe_path_components(self):
        for name in ['assets/a\\b', 'assets//b', 'assets/./b', 'assets/C:/b', 'assets/b./c', '/assets/file']:
            with self.subTest(name=name):
                self.build(asset_entries=[(name, b'bad')])
                self.assert_failed_unpublished()

    def test_symlink_entry_rejected_even_if_pinned(self):
        self.build(symlink=self.asset_entries[0][0])
        self.assert_failed_unpublished()

    def test_directory_entry_rejected_even_if_pinned(self):
        self.build(directory=self.asset_entries[0][0])
        self.assert_failed_unpublished()

    def test_manifest_payload_hash_checked(self):
        user = archive([('asset-manifest.json', b'x' * len(self.manifest))] + self.asset_entries)
        self.build(user_bytes=user)
        self.assert_failed_unpublished()

    def test_per_file_hash_checked(self):
        bad = [(self.asset_entries[0][0], b'x' * len(self.asset_entries[0][1])), self.asset_entries[1]]
        self.build(zip_entries=bad)
        self.assert_failed_unpublished()

    def test_per_file_size_checked(self):
        bad = [(self.asset_entries[0][0], b'x'), self.asset_entries[1]]
        self.build(zip_entries=bad)
        self.assert_failed_unpublished()

    def test_corrupt_apk_index_rejected(self):
        (self.assets / 'atlas-assets-index.tsv').write_bytes(b'bad')
        self.assert_failed_unpublished()

    def test_corrupt_bundled_text_rejected(self):
        (self.assets / 'atlas-text.zip').write_bytes(b'bad')
        self.assert_failed_unpublished()

    def test_truncated_central_directory_even_if_pinned(self):
        raw = self.selected.read_bytes()
        self.build(user_bytes=raw[:-10])
        self.assert_failed_unpublished()

    def test_local_central_name_disagreement(self):
        raw = self.selected.read_bytes()
        # Same-width name mutation in only the local header; central index stays pinned.
        position = raw.find(b'assets/maps/atlas.bin')
        raw = raw[:position] + b'assets/maps/other.bin' + raw[position + len(b'assets/maps/atlas.bin'):]
        self.build(user_bytes=raw)
        self.assert_failed_unpublished()

    def test_destination_collision_between_archives(self):
        self.build(text_entries=[('data/maps/atlas.bin', b'overwrite')])
        self.assert_failed_unpublished()

    def test_assets_reuse_text_directory_case(self):
        self.build(asset_entries=[('assets/objects/mixed/b.geo', b'model')], text_entries=[('data/Objects/Mixed/a.txt', b'def')])
        result = self.run_import()
        self.assertEqual('ok', result['status'], result)
        data = Path(result['dataDirectory'])
        self.assertEqual(b'model', (data / 'Objects/Mixed/b.geo').read_bytes())
        self.assertFalse((data / 'objects').exists())

    def test_new_apk_contract_can_replace_old_generation(self):
        first = self.run_import()
        properties = self.build()
        properties['repository.commit'] = '4' * 40
        self.write_properties(properties)
        self.assertEqual('error', self.run_import('inspect')['status'])
        second = self.run_import()
        self.assertEqual('ok', second['status'], second)
        self.assertNotEqual(first['generation'], second['generation'])
        self.assertTrue(Path(first['dataDirectory']).exists())

    def test_missing_active_content_can_be_reimported(self):
        first = self.run_import()
        shutil.rmtree(Path(first['dataDirectory']))
        second = self.run_import()
        self.assertEqual('ok', second['status'], second)
        self.assertNotEqual(first['generation'], second['generation'])

    def test_missing_active_receipt_can_be_reimported(self):
        first = self.run_import()
        (Path(first['dataDirectory']).parent / 'complete.properties').unlink()
        second = self.run_import()
        self.assertEqual('ok', second['status'], second)
        self.assertTrue(Path(first['dataDirectory']).exists())

    def test_storage_preflight(self):
        self.assertIn('storage', self.assert_failed_unpublished('no-space')['message'])

    def test_storage_filling_during_extraction_preserves_previous(self):
        first = self.run_import()
        result = self.run_import('fill-space')
        self.assertEqual('error', result['status'], result)
        self.assertIn('storage filled', result['message'])
        self.assertEqual(first['generation'], self.run_import('inspect')['generation'])
        self.assertFalse(list(self.base.glob('.import-*')))

    def test_cancellation_copy_extract_publish_preserves_previous(self):
        first = self.run_import()
        pointer = (self.base / 'active.properties').read_bytes()
        for mode in ['cancel-before', 'cancel-copy', 'cancel-extract', 'cancel-publish']:
            with self.subTest(mode=mode):
                result = self.run_import(mode)
                self.assertEqual('cancelled', result['status'], result)
                self.assertEqual('false', result['committed'])
                self.assertEqual(pointer, (self.base / 'active.properties').read_bytes())
                self.assertEqual(first['generation'], self.run_import('inspect')['generation'])
                self.assertFalse(list(self.base.glob('.import-*')))

    def test_single_active_writer(self):
        self.base.mkdir()
        (self.base / 'import.lock').touch()
        self.assertIn('already running', self.assert_failed_unpublished('locked')['message'])

    def test_recovery_removes_only_owned_partials_and_orphans(self):
        first = self.run_import()
        partial = self.base / ('.import-' + 'a' * 32)
        partial.mkdir()
        (partial / 'unfinished').write_bytes(b'partial')
        orphan = self.base / ('generation-' + 'b' * 32)
        orphan.mkdir()
        pointer_temp = self.base / ('.pointer-' + 'c' * 32 + '.tmp')
        pointer_temp.write_bytes(b'incomplete')
        unowned = self.base / 'personal-files'
        unowned.mkdir()
        self.assertEqual(first['generation'], self.run_import('recover')['generation'])
        self.assertFalse(partial.exists())
        self.assertFalse(orphan.exists())
        self.assertFalse(pointer_temp.exists())
        self.assertTrue(unowned.exists())

    def test_recovery_does_not_follow_abandoned_symlink(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'keep').write_bytes(b'keep')
        self.base.mkdir()
        (self.base / ('.import-' + 'd' * 32)).symlink_to(outside, target_is_directory=True)
        self.assertEqual('absent', self.run_import('recover')['status'])
        self.assertEqual(b'keep', (outside / 'keep').read_bytes())

    def test_process_death_during_copy_and_before_publication_recovers(self):
        first = self.run_import()
        pointer = (self.base / 'active.properties').read_bytes()
        for mode in ['kill-copy', 'kill-publish']:
            with self.subTest(mode=mode):
                process = subprocess.run([self.java, '-cp', self.compile_dir.name, 'io.github.russianranger.cohatlas.AssetImporterHost', str(self.assets), str(self.base), mode, str(self.selected)], capture_output=True, text=True)
                self.assertEqual(17, process.returncode, process.stderr)
                self.assertEqual(pointer, (self.base / 'active.properties').read_bytes())
                self.assertEqual(first['generation'], self.run_import('recover')['generation'])
                self.assertFalse(list(self.base.glob('.import-*')))
                self.assertFalse(list(self.base.glob('.pointer-*')))
                self.assertEqual(1, len(list(self.base.glob('generation-*'))))

    def test_invalid_active_pointer_preserves_content(self):
        first = self.run_import()
        (self.base / 'active.properties').write_text('generation=../../outside\n')
        self.assertEqual('error', self.run_import('recover')['status'])
        self.assertTrue(Path(first['dataDirectory']).exists())

    def test_symlink_private_directory_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.base.symlink_to(outside, target_is_directory=True)
        self.assertEqual('error', self.run_import()['status'])
        self.assertFalse(list(outside.iterdir()))

    def test_provider_close_failure_occurs_before_publication(self):
        first = self.run_import()
        result = self.run_import('bad-close')
        self.assertEqual('error', result['status'], result)
        self.assertEqual('false', result['committed'])
        self.assertEqual(first['generation'], self.run_import('inspect')['generation'])

    def test_zip64_entry_count(self):
        entries = [(f'data/defs/{i:05}.def', b'') for i in range(65536)]
        self.build(text_entries=entries)
        result = self.run_import()
        self.assertEqual('ok', result['status'], result)
        self.assertEqual(str(65536 + len(self.asset_entries)), result['count'])


if __name__ == '__main__':
    unittest.main()

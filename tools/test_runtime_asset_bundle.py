"""Boundary tests for reviewed asset transport and fail-closed extraction."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import stat
import struct
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

import runtime_asset_bundle as bundle


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = self.root / 'assets.zip'
        self.manifest = self.root / 'manifest.json'
        self.output = self.root / 'staged'
        self.bodies = {'fonts/example.ttf': b'font bytes', 'texture_library/white.texture': b'texture bytes'}
        self.expected = {'source_commit': bundle.SOURCE, 'text_data_commit': bundle.TEXT,
                         'donors': [{'archive': 'fonts.pigg', 'bytes': 42, 'sha256': 'a' * 64}],
                         'asset_count': len(self.bodies), 'asset_bytes': sum(map(len, self.bodies.values())),
                         'extensions': dict(Counter(Path(p).suffix for p in self.bodies))}
        self.document = dict(self.expected, schema_version=1,
                             status='reviewed_base_assets_byte_checked_runtime_unvalidated',
                             files=[{'path': name, 'size': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                                     'donor': 'fonts.pigg'} for name, body in sorted(self.bodies.items())])

    def write(self, *, doc=None, payloads=None, extra=None, omit=None, symlink=None, embedded=None):
        doc = self.document if doc is None else doc
        payloads = self.bodies if payloads is None else payloads
        data = bundle.canonical(doc)
        self.manifest.write_bytes(data)
        with zipfile.ZipFile(self.archive, 'w') as result:
            result.writestr(bundle.zip_info(bundle.MANIFEST_NAME), data if embedded is None else embedded)
            for name, body in payloads.items():
                if name == omit:
                    continue
                info = bundle.zip_info('assets/' + name)
                if name == symlink:
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                result.writestr(info, body)
            for name, body in (extra or []):
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    result.writestr(bundle.zip_info(name), body)

    def stage(self):
        return bundle.stage(self.archive, self.manifest, self.output, expected=self.expected, root=self.root)

    def test_valid_bundle_round_trip(self):
        self.write()
        result = self.stage()
        self.assertEqual(result['asset_count'], 2)
        self.assertFalse((self.output / bundle.INCOMPLETE).exists())
        self.assertEqual({p.relative_to(self.output).as_posix(): p.read_bytes()
                          for p in self.output.rglob('*') if p.is_file()}, self.bodies)
        self.assertEqual(result['manifest_sha256'], bundle.sha256(self.manifest))

    def test_unknown_source_and_donor_provenance_rejected_before_output(self):
        for key, value in [('source_commit', 'f' * 40), ('text_data_commit', '0' * 40), ('donors', [])]:
            with self.subTest(key=key):
                self.write(doc=dict(self.document, **{key: value}))
                with self.assertRaisesRegex(ValueError, 'Manifest differs'):
                    self.stage()
                self.assertFalse(self.output.exists())

    def test_embedded_manifest_cannot_replace_reviewed_manifest(self):
        self.write(embedded=b' ' * len(bundle.canonical(self.document)))
        with self.assertRaisesRegex(ValueError, 'manifest mismatch'):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_hash_failure_leaves_incomplete_marker(self):
        bodies = dict(self.bodies)
        bodies['fonts/example.ttf'] = b'wrongbytes'
        self.assertEqual(len(bodies['fonts/example.ttf']), len(self.bodies['fonts/example.ttf']))
        self.write(payloads=bodies)
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.stage()
        self.assertTrue((self.output / bundle.INCOMPLETE).is_file())

    def test_missing_unlisted_and_duplicate_zip_entries_rejected(self):
        for kwargs in ({'omit': 'fonts/example.ttf'}, {'extra': [('unexpected.bin', b'x')]},
                       {'omit': 'fonts/example.ttf',
                        'extra': [('assets/texture_library/white.texture', b'texture bytes')]}):
            with self.subTest(kwargs=kwargs):
                self.write(**kwargs)
                with self.assertRaises(ValueError):
                    self.stage()
                self.assertFalse(self.output.exists())

    def test_symlink_entry_rejected(self):
        self.write(symlink='fonts/example.ttf')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_traversal_windows_alias_and_text_paths_rejected(self):
        for name in ('../font.ttf', '/font.ttf', 'c:/font.ttf', 'a\\b.ttf', 'a./font.ttf',
                     'aux.ttf', 'bin/font.ttf', '_devonly/font.ttf', 'defs/text.def',
                     'fonts/Example.ttf', 'a\x00.ttf', 'a /font.ttf'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                bundle.safe_asset(name)

    def test_casefold_collision_and_file_directory_collision_rejected(self):
        for names in (('fonts/straße.ttf', 'fonts/strasse.ttf'), ('a.ttf', 'a.ttf/child.ttf')):
            document = copy.deepcopy(self.document)
            document['files'][0]['path'], document['files'][1]['path'] = sorted(names)
            with self.subTest(names=names), self.assertRaisesRegex(ValueError, 'collision|colliding'):
                bundle.validate_manifest(document, self.expected)

    def test_serialized_cache_disguised_as_asset_rejected(self):
        document, bodies = copy.deepcopy(self.document), dict(self.bodies)
        bodies['fonts/example.ttf'] = b'CrypticSxx'
        document['files'][0]['sha256'] = hashlib.sha256(bodies['fonts/example.ttf']).hexdigest()
        self.write(doc=document, payloads=bodies)
        with self.assertRaisesRegex(ValueError, 'Serialized cache'):
            self.stage()
        self.assertTrue((self.output / bundle.INCOMPLETE).exists())

    def test_size_limits_rejected_before_output(self):
        self.write()
        with patch.object(bundle, 'MAX_TOTAL', 1), self.assertRaisesRegex(ValueError, 'limit'):
            self.stage()
        with patch.object(bundle, 'MAX_ENTRIES', 1), self.assertRaisesRegex(ValueError, 'limit'):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_declared_size_mismatch_rejected_before_output(self):
        self.write(payloads=dict(self.bodies, **{'fonts/example.ttf': b'x'}))
        with self.assertRaisesRegex(ValueError, 'size mismatch'):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_existing_or_incomplete_output_is_never_reused(self):
        self.write()
        self.output.mkdir()
        (self.output / bundle.INCOMPLETE).write_text('previous failure')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.stage()
        self.assertEqual((self.output / bundle.INCOMPLETE).read_text(), 'previous failure')

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            bundle.decode_manifest(b'{"files": [], "files": []}')

    def test_manifest_totals_recomputed(self):
        self.document['files'][0]['size'] += 1
        with self.assertRaisesRegex(ValueError, 'totals mismatch'):
            bundle.validate_manifest(self.document, self.expected)

    def test_symlink_archive_and_parent_rejected(self):
        self.write()
        link = self.root / 'alias.zip'
        try:
            link.symlink_to(self.archive)
        except OSError:
            self.skipTest('Symlink creation unavailable on this runner')
        with self.assertRaisesRegex(ValueError, 'regular ZIP'):
            bundle.stage(link, self.manifest, self.output, expected=self.expected, root=self.root)
        parent = self.root / 'alias'
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            bundle.stage(self.archive, self.manifest, parent / 'new', expected=self.expected, root=self.root)

    def test_directory_limits_checked_before_zipfile_allocation(self):
        self.write()
        data = bytearray(self.archive.read_bytes())
        # EOCD records a hostile number of members; do not allocate its directory.
        struct.pack_into('<HH', data, len(data) - 14, 65535, 65535)
        self.archive.write_bytes(data)
        with patch.object(bundle.zipfile, 'ZipFile') as parser:
            with self.assertRaisesRegex(ValueError, 'ZIP directory'):
                self.stage()
            parser.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_underreported_directory_count_rejected_before_zipfile_allocation(self):
        self.write()
        data = bytearray(self.archive.read_bytes())
        # Python ZipFile ignores this count and otherwise allocates all three
        # actual headers before stage() can inspect infolist().
        struct.pack_into('<HH', data, len(data) - 14, 1, 1)
        self.archive.write_bytes(data)
        with patch.object(bundle.zipfile, 'ZipFile') as parser:
            with self.assertRaisesRegex(ValueError, 'central directory count'):
                self.stage()
            parser.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_central_variable_length_cannot_skip_past_directory(self):
        self.write()
        data = bytearray(self.archive.read_bytes())
        central_offset, = struct.unpack_from('<L', data, len(data) - 6)
        # Filename/extra/comment lengths begin at byte 28 of a central header.
        struct.pack_into('<HHH', data, central_offset + 28, 65535, 65535, 65535)
        self.archive.write_bytes(data)
        with patch.object(bundle.zipfile, 'ZipFile') as parser:
            with self.assertRaisesRegex(ValueError, 'variable fields exceed bounds'):
                self.stage()
            parser.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_unreviewed_donor_rejected_before_any_output(self):
        inputs = self.root / 'donors'
        inputs.mkdir()
        (inputs / 'fonts.pigg').write_bytes(b'unreviewed')
        receipt = self.root / 'receipt.json'
        with patch.object(bundle, 'provenance', return_value=self.expected):
            with self.assertRaisesRegex(ValueError, 'donor size/SHA256 mismatch'):
                bundle.build(inputs, self.archive, self.manifest, receipt, root=self.root)
        self.assertFalse(any(p.exists() for p in (self.archive, self.manifest, receipt)))

    def test_deflate_default_and_stored_option_have_identical_payloads(self):
        assets = self.root / 'inputs'
        for name, body in self.bodies.items():
            target = assets / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        data = bundle.canonical(self.document)
        compressed, stored = self.root / 'deflate.zip', self.root / 'stored.zip'
        bundle.write_bundle(compressed, assets, data, self.document['files'])
        bundle.write_bundle(stored, assets, data, self.document['files'], compression='stored')
        with zipfile.ZipFile(compressed) as first, zipfile.ZipFile(stored) as second:
            self.assertTrue(all(info.compress_type == zipfile.ZIP_DEFLATED for info in first.infolist()))
            self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED for info in second.infolist()))
            self.assertEqual({info.filename: first.read(info) for info in first.infolist()},
                             {info.filename: second.read(info) for info in second.infolist()})
        self.manifest.write_bytes(data)
        result = bundle.stage(compressed, self.manifest, self.output, expected=self.expected, root=self.root)
        self.assertEqual(result['asset_count'], len(self.bodies))
        self.assertEqual(bundle.compression_receipt('deflate')['deflate_level'], 6)
        self.assertIsNone(bundle.compression_receipt('stored')['deflate_level'])
        self.assertIn('zlib version', bundle.compression_receipt('deflate')['archive_byte_reproducibility'])
        self.assertFalse((self.output / bundle.INCOMPLETE).exists())

    def test_deterministic_archive_bytes_and_changed_staging_rejected(self):
        assets = self.root / 'inputs'
        for name, body in self.bodies.items():
            target = assets / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        first, second = self.root / 'first.zip', self.root / 'second.zip'
        data = bundle.canonical(self.document)
        bundle.write_bundle(first, assets, data, self.document['files'])
        bundle.write_bundle(second, assets, data, self.document['files'])
        self.assertEqual(first.read_bytes(), second.read_bytes())
        (assets / 'fonts/example.ttf').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'asset changed'):
            bundle.write_bundle(self.root / 'changed.zip', assets, data, self.document['files'])


if __name__ == '__main__':
    unittest.main()

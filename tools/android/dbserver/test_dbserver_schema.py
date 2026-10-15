"""Verify minimal real schema staging and fail-closed evidence/input checks."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import prepare_dbserver_schema as stage


class DbServerSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='coh-schema-tests-')
        cls.root = Path(cls.directory.name)
        cls.output = cls.root / 'staged'
        cls.manifest = stage.prepare(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_minimal_inventory_and_full_generated_payloads_remain_exact(self):
        paths = {p.relative_to(self.output).as_posix() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(paths, set(self.manifest['files']) | {'schema-manifest.json'})
        self.assertEqual(len(self.manifest['files']), 62)
        self.assertFalse(any(name.lower().endswith(('.exe', '.dll', '.pigg', '.bin')) for name in paths))
        for name, record in self.manifest['files'].items():
            data = (self.output / name).read_bytes()
            self.assertEqual(len(data), record['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'])
        with zipfile.ZipFile(stage.ROOT / 'docs/schema-generation-evidence/accepted-36088012666.zip') as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read(stage.ARCHIVE_MEMBER))) as inner:
                self.assertEqual(len(inner.infolist()), 56)
                for member in inner.infolist():
                    self.assertEqual((self.output / member.filename).read_bytes(), inner.read(member.filename))

    def test_sql_contract_retains_ordered_columns_and_exact_attribute_identity(self):
        tables = self.manifest['expected_tables']
        attributes = self.manifest['expected_attributes']
        self.assertEqual(len(tables), 99)
        self.assertEqual(sum(map(len, tables.values())), 5935)
        self.assertEqual(tables['testdatabasetypes'][:6],
                         ['containerid', 'active', 'test_byte', 'test_short', 'test_int', 'test_float'])
        self.assertEqual({name: len(rows) for name, rows in attributes.items()},
                         {'attributes': 56411, 'badgestatsattributes': 1771, 'pophelpattributes': 90})
        self.assertEqual(attributes['pophelpattributes'][:2],
                         [{'id': 1, 'name': 'codeph_got_xp'},
                          {'id': 2, 'name': 'codeph_found_exploration_badge'}])
        self.assertFalse(self.manifest['android_execution_validated'])
        self.assertFalse(self.manifest['gameplay_validated'])
        for item in self.manifest['optional_inputs']:
            self.assertFalse((self.output / item['path']).exists())

    def test_changed_archive_is_refused_before_output_creation(self):
        with tempfile.TemporaryDirectory(prefix='coh-schema-corrupt-') as temporary:
            directory = Path(temporary)
            receipt = stage.ROOT / stage.RECEIPT
            (directory / receipt.name).write_bytes(receipt.read_bytes())
            artifact = bytearray(receipt.with_suffix('.zip').read_bytes())
            artifact[-1] ^= 1
            (directory / 'accepted-36088012666.zip').write_bytes(artifact)
            output = directory / 'output'
            with self.assertRaisesRegex(ValueError, 'artifact hash/size mismatch'):
                stage.prepare(output, receipt_path=directory / receipt.name)
            self.assertFalse(output.exists())

    def test_changed_source_pin_is_refused_before_reading_payloads(self):
        receipt = json.loads((stage.ROOT / stage.RECEIPT).read_text())
        with tempfile.TemporaryDirectory(prefix='coh-schema-wrong-pin-') as temporary:
            path = Path(temporary) / 'receipt.json'
            for key in ('source_commit', 'text_data_commit'):
                changed = copy.deepcopy(receipt)
                changed[key] = '0' * 40
                path.write_text(json.dumps(changed))
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'source/data/run pins differ'):
                    stage.accepted_payloads(receipt_path=path)

    def test_existing_output_is_preserved(self):
        before = (self.output / 'schema-manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'new directory'):
            stage.prepare(self.output)
        self.assertEqual((self.output / 'schema-manifest.json').read_bytes(), before)

    def test_supplemental_crlf_checkout_preserves_canonical_identity(self):
        name = 'data/server/db/servers.cfg'
        accepted = stage.supplemental_payload(stage.ROOT, name)
        with tempfile.TemporaryDirectory(prefix='coh-schema-text-') as temporary:
            root = Path(temporary)
            path = root / 'upstream/ouroboros' / name
            path.parent.mkdir(parents=True)
            path.write_bytes(accepted.replace(b'\n', b'\r\n'))
            self.assertEqual(stage.supplemental_payload(root, name), accepted)
            path.write_bytes(accepted + b'\nUseFakeAuth 0\n')
            with self.assertRaisesRegex(ValueError, 'immutable pin'):
                stage.supplemental_payload(root, name)

    def test_symlinked_supplemental_is_refused(self):
        name = 'data/server/db/servers.cfg'
        with tempfile.TemporaryDirectory(prefix='coh-schema-link-') as temporary:
            root = Path(temporary)
            source = root / 'input.txt'
            source.write_bytes(stage.supplemental_payload(stage.ROOT, name))
            link = root / 'upstream/ouroboros' / name
            link.parent.mkdir(parents=True)
            link.symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'linked input'):
                stage.supplemental_payload(root, name)


if __name__ == '__main__':
    unittest.main()

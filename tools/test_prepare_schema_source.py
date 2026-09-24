"""Exercise real patch application and provenance gates without compiling CoH."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import prepare_schema_source as schema


class SchemaSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / 'source'
        self.source.mkdir()
        self.expected = schema.expected_schema_receipt()
        pg = self.expected['postgresql_build_input']
        original = schema.ROOT / 'upstream/ouroboros'
        for name in (*schema.SCHEMA_FILES, *pg['patched_sha256']):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original / name, target)
        schema.apply_patch(self.source, (schema.ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                           .read_bytes().replace(b'\r\n', b'\n'))
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(schema.ROOT / 'database/postgresql/overlay' / name, target)
        self.pg_path = self.source / 'postgresql-build-input.json'
        self.pg_path.write_text(json.dumps(pg))

    def test_real_patch_records_expected_hashes_without_changing_upstream(self):
        receipt = schema.apply_schema_overlay(self.source)
        self.assertEqual(receipt, self.expected)
        self.assertEqual(json.loads((self.source / schema.RECEIPT).read_text()), receipt)
        for name, digest in receipt['patched_sha256'].items():
            self.assertEqual(schema.sha256(self.source / name), digest)
            self.assertEqual(schema.sha256(schema.ROOT / 'upstream/ouroboros' / name),
                             receipt['source_sha256'][name])
        self.assertEqual(json.loads(self.pg_path.read_text()), receipt['postgresql_build_input'])
        self.assertEqual(receipt['runtime_validation'], 'unverified')

    def test_dirty_schema_source_is_rejected_before_other_files_change(self):
        target = self.source / schema.SCHEMA_FILES[0]
        target.write_bytes(target.read_bytes() + b'\n// unrecorded edit\n')
        with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
            schema.apply_schema_overlay(self.source)
        untouched = schema.SCHEMA_FILES[1]
        self.assertEqual(schema.sha256(self.source / untouched), self.expected['source_sha256'][untouched])
        self.assertFalse((self.source / schema.RECEIPT).exists())

    def test_pg_source_or_overlay_drift_rejected(self):
        pg = self.expected['postgresql_build_input']
        for names in (pg['patched_sha256'], pg['overlay_sha256']):
            with self.subTest(category=next(iter(names))):
                target = self.source / next(iter(names))
                original = target.read_bytes()
                target.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
                    schema.apply_schema_overlay(self.source)
                target.write_bytes(original)
        self.assertFalse((self.source / schema.RECEIPT).exists())

    def test_stale_pg_receipt_rejected(self):
        pg = json.loads(self.pg_path.read_text())
        pg['source_commit'] = 'f' * 40
        self.pg_path.write_text(json.dumps(pg))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            schema.apply_schema_overlay(self.source)

    def test_known_crlf_overlay_profile_keeps_actual_raw_receipt(self):
        pg = json.loads(self.pg_path.read_text())
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            pg['overlay_sha256'][name] = schema.sha256(target)
        self.pg_path.write_text(json.dumps(pg))
        receipt = schema.apply_schema_overlay(self.source)
        self.assertEqual(receipt, schema.expected_schema_receipt(postgresql_build_input=pg))
        self.assertEqual(receipt['postgresql_build_input'], pg)
        self.assertEqual(receipt['postgresql_build_input_canonical_sha256'], schema.canonical_hash(pg))

    def test_unknown_overlay_profile_rejected_even_with_matching_local_bytes(self):
        pg = json.loads(self.pg_path.read_text())
        name = next(iter(pg['overlay_sha256']))
        target = self.source / name
        target.write_bytes(target.read_bytes() + b'// unexpected change\n')
        pg['overlay_sha256'][name] = schema.sha256(target)
        self.pg_path.write_text(json.dumps(pg))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            schema.apply_schema_overlay(self.source)

    def test_second_application_and_upstream_target_rejected(self):
        schema.apply_schema_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            schema.apply_schema_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            schema.apply_schema_overlay(schema.ROOT / 'upstream/ouroboros')

    def test_preexisting_output_rejected_without_invoking_pg_stager(self):
        with self.assertRaisesRegex(ValueError, 'new directory'):
            schema.prepare(self.source)


if __name__ == '__main__':
    unittest.main()

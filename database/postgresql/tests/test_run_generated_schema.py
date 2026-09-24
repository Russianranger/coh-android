"""Pure preflight/expectation tests; never starts a database or game executable."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import run_generated_schema as driver


class GeneratedSchemaDriverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def archive(self, members):
        path = self.root / 'schema.zip'
        records = []
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in members:
                archive.writestr(name, data)
                records.append({'path': name, 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()})
        return path, {'bytes': path.stat().st_size, 'sha256': driver.sha256(path), 'files': records}

    def test_contract_follows_actual_updated_template_variables(self):
        source = (driver.ROOT / 'upstream/ouroboros/DBServer/src/dbinit.c').read_text()
        templates, attributes = driver.schema_contract(source)
        self.assertIn('ents', templates)
        self.assertNotIn('doors', templates)  # Registered, but never updated as a SQL template.
        self.assertNotIn('maps', templates)
        self.assertEqual(attributes['attributes'], 'data/server/db/templates/vars.attribute')
        modified = source.replace('    tpltUpdateSqlcolumns(testdatabasetypes_list->tplt);', '')
        without_unused, _ = driver.schema_contract(modified)
        self.assertNotIn('testdatabasetypes', without_unused)
        self.assertEqual(len(without_unused), len(templates) - 1)

    def test_template_reader_tracks_child_tables_and_implicit_columns(self):
        result = driver.template_columns('Name "unicodestring[64]" indexed\nPowers[80].Name "attribute"\nLevel "int4"\n', 'Ents')
        self.assertEqual(result, {'ents': ['containerid', 'active', 'name'],
                                  'powers': ['containerid', 'subid', 'name', 'level']})
        self.assertEqual(driver.template_columns('', 'Unused'), {})

    def test_malformed_or_duplicate_template_columns_refused(self):
        for text in ('A "int4"\na "int4"\n', 'Broken[2] "int4"\n', 'A "int4" unknown\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.template_columns(text, 'Ents')

    def test_attributes_preserve_ids_and_loader_ascii_case(self):
        self.assertEqual(driver.attribute_rows('2 "Second"\n1 "FIRST"\n'),
                         [{'id': 1, 'name': 'first'}, {'id': 2, 'name': 'second'}])
        for text in ('1 "A"\n1 "B"', '1 "A"\n2 "a"', '2 "B"', '0 "Bad"'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.attribute_rows(text)

    def test_private_config_replaces_all_sql_secrets_without_touching_other_flags(self):
        source = '''// Owner's local settings
SqlDbProvider mssql
SqlDbName old
SqlLogin "Password=old-secret;"
SqlInit "CREATE DATABASE old;"
SqlAllowDDL 1
UseFakeAuth 1
UseQueueServer 0
NoStats 0
'''
        actual = driver.private_config(source, 'SqlDbProvider postgresql\nSqlDbName coh_schema_test\nSqlLogin "Password=new-secret;"\n')
        self.assertNotIn('old-secret', actual)
        self.assertNotIn('SqlInit', actual)
        self.assertIn('NoStats 0', actual)
        self.assertEqual(actual.count('SqlLogin '), 1)
        with self.assertRaises(ValueError):
            driver.private_config(source.replace('UseFakeAuth 1', 'UseFakeAuth 0'), '')

    def test_secret_redaction_covers_known_secrets_and_driver_diagnostics(self):
        actual = driver.redact('opaque-token; Password=other; PWD=third\nmore opaque-token', ['opaque-token'])
        for secret in ('opaque-token', 'other', 'third'):
            self.assertNotIn(secret, actual)
        self.assertEqual(actual.count('[redacted]'), 4)

    def test_archive_bytes_are_verified_and_loaded_without_path_extraction(self):
        path, record = self.archive([('data/server/db/templates/ents.template', b'Name "int4"\n')])
        files = driver.archive_payloads(path, record)
        self.assertEqual(files['data/server/db/templates/ents.template'][1], b'Name "int4"\n')
        record['files'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            driver.archive_payloads(path, record)

    def test_archive_traversal_or_duplicate_case_paths_rejected(self):
        path, record = self.archive([('../escape', b'x')])
        with self.assertRaises(ValueError):
            driver.archive_payloads(path, record)
        path.unlink()
        path, record = self.archive([('data/server/db/templates/a.template', b'x'),
                                     ('data/server/db/templates/A.template', b'x')])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            driver.archive_payloads(path, record)

    def test_failed_generation_refuses_before_cluster_or_work_creation(self):
        runtime = self.root / 'runtime'
        runtime.mkdir()
        (runtime / 'runtime-inputs.json').write_text(json.dumps({
            'source_commit': driver.generation.SOURCE_COMMIT,
            'data_commit': driver.generation.DATA_COMMIT, 'binary_assets_supplied': False}))
        report = self.root / 'report.json'
        report.write_text(json.dumps({'status': 'schema_data_only_generation_failed'}))
        with patch.object(driver, 'initialize') as initialize:
            with self.assertRaisesRegex(ValueError, 'has not passed acceptance'):
                driver.run(runtime, report, self.root / 'reference', self.root / 'work',
                           self.root / 'output', 'unused-pg-bin', 'unused-driver')
        initialize.assert_not_called()
        self.assertFalse((self.root / 'work').exists())
        self.assertFalse((self.root / 'output').exists())

    def test_catalog_missing_extra_or_reordered_columns_fail(self):
        expected = {'ents': ['containerid', 'active', 'name']}
        valid = {'columns': [{'table_name': 'ents', 'column_name': name} for name in expected['ents']]}
        driver.validate_catalog(valid, expected)
        for rows in (valid['columns'][:-1], list(reversed(valid['columns'])),
                     valid['columns'] + [{'table_name': 'extra', 'column_name': 'id'}]):
            with self.assertRaisesRegex(ValueError, 'differ'):
                driver.validate_catalog({'columns': rows}, expected)

    def test_private_and_publishable_output_cannot_be_same_directory(self):
        with patch.object(driver, 'initialize') as initialize:
            with self.assertRaisesRegex(ValueError, 'must be separate'):
                driver.run(self.root / 'runtime', self.root / 'report', self.root / 'reference',
                           self.root / 'same', self.root / 'same', 'unused', 'unused')
        initialize.assert_not_called()


if __name__ == '__main__':
    unittest.main()

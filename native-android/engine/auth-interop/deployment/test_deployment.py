"""Synthetic metadata controls. None connects to SQL or authenticates an account."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from admit_schema import AdmissionError, COLUMNS, PARAMETERS, MAX_INPUT_BYTES, admit, read_metadata
from source_audit import decoded, procedure_parameters


def fixture():
    return {'schema': 'coh-auth-critical-schema-v1',
            'parameters': [{'schema': 'dbo', 'procedure': name, 'ordinal': ordinal,
                            'type': kind, 'max_length': size, 'output': output, 'user_defined': False,
                            'scale': 3 if kind == 'datetime' else 0}
                           for name, fields in PARAMETERS.items()
                           for ordinal, (kind, size, output) in enumerate(fields, 1)],
            'columns': [{'schema': 'dbo', 'table': table, 'column': column,
                         'type': kind, 'max_length': size, 'user_defined': False}
                        for (table, column), (kind, size) in COLUMNS.items()]}


class MetadataTests(unittest.TestCase):
    def test_exact_binding_fixture_is_only_metadata(self):
        report = admit(fixture())
        self.assertTrue(report['critical_interfaces_compatible'])
        self.assertFalse(report['deployment_ready'])
        self.assertFalse(report['real_account_login_verified'])
        self.assertFalse(report['procedure_bodies_verified'])
        self.assertFalse(report['complete_schema_compatible'])
        self.assertFalse(report['db_map_handoff_verified'])

    def test_legacy_eleven_parameter_procedure_fails(self):
        data = fixture()
        data['parameters'] = [r for r in data['parameters'] if r['procedure'] != 'ap_GStat' or r['ordinal'] < 12]
        report = admit(data)
        self.assertFalse(report['critical_interfaces_compatible'])
        self.assertIn({'code': 'parameter_count', 'interface': 'ap_GStat', 'expected': 13, 'observed': 11}, report['failures'])

    def test_existing_2019_schema_needs_driver_conversion_test(self):
        data = fixture()
        for row in data['parameters']:
            if (row['procedure'], row['ordinal']) == ('ap_GPwd', 3):
                row.update(type='int', max_length=4)
            if (row['procedure'], row['ordinal']) == ('ap_GStat', 10):
                row.update(type='datetime2')
        report = admit(data)
        self.assertEqual(report['failures'], [
            {'code': 'odbc_conversion_unqualified', 'interface': 'ap_GPwd', 'ordinal': 3},
            {'code': 'odbc_conversion_unqualified', 'interface': 'ap_GStat', 'ordinal': 10}])
        self.assertFalse(report['deployment_ready'])

    def test_all_parameter_fields_are_checked(self):
        original = fixture()
        for index, _ in enumerate(original['parameters']):
            for key, value in [('ordinal', 999), ('type', 'nvarchar'), ('max_length', 1),
                               ('output', not original['parameters'][index]['output']), ('user_defined', True), ('scale', 38)]:
                if original['parameters'][index][key] == value:
                    continue
                with self.subTest(index=index, key=key):
                    data = copy.deepcopy(original)
                    data['parameters'][index][key] = value
                    self.assertFalse(admit(data)['critical_interfaces_compatible'])

    def test_all_required_columns_are_checked(self):
        original = fixture()
        for index, _ in enumerate(original['columns']):
            with self.subTest(index=index):
                data = copy.deepcopy(original)
                del data['columns'][index]
                self.assertFalse(admit(data)['critical_interfaces_compatible'])

    def test_missing_metadata_does_not_succeed(self):
        self.assertFalse(admit({'schema': 'coh-auth-critical-schema-v1', 'parameters': [], 'columns': []})['critical_interfaces_compatible'])

    def test_duplicates_aliases_unexpected_fields_and_secrets_reject(self):
        for table in ('parameters', 'columns'):
            data = fixture()
            data[table].append(copy.deepcopy(data[table][0]))
            with self.assertRaises(AdmissionError):
                admit(data)
        for key in ('password', 'connectionString', 'account', 'server_logs'):
            data = fixture()
            data[key] = 'SECRET_VALUE_MUST_NOT_APPEAR'
            with self.assertRaises(AdmissionError) as error:
                admit(data)
            self.assertNotIn('SECRET', str(error.exception))
        for table in ('parameters', 'columns'):
            data = fixture()
            data[table][0]['schema'] = 'SECRET_VALUE_MUST_NOT_APPEAR'
            with self.assertRaises(AdmissionError) as error:
                admit(data)
            self.assertNotIn('SECRET', str(error.exception))

    def test_types_bool_integer_and_limits(self):
        for key, value in [('ordinal', True), ('ordinal', 0), ('ordinal', 1025),
                           ('max_length', True), ('max_length', 32768), ('type', '\nint'),
                           ('scale', -1), ('scale', 39), ('output', 1), ('user_defined', 0)]:
            with self.subTest(key=key, value=value):
                data = fixture()
                data['parameters'][0][key] = value
                with self.assertRaises(AdmissionError):
                    admit(data)
        data = fixture()
        data['columns'] = data['columns'] * 1025
        with self.assertRaises(AdmissionError):
            admit(data)

    def test_duplicate_json_nonfinite_invalid_and_oversized(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'metadata.json'
            for payload in [b'{"schema":1,"schema":2}', b'{"n":NaN}', b'{"n":Infinity}', b'\xff',
                            b'[' * 3000, b' ' * (MAX_INPUT_BYTES + 1)]:
                path.write_bytes(payload)
                with self.assertRaises(AdmissionError):
                    read_metadata(path)
            path.write_text(json.dumps(fixture()))
            data, digest = read_metadata(path)
            self.assertEqual(data, fixture())
            self.assertEqual(len(digest), 64)

    def test_metadata_query_does_not_read_account_rows_or_execute_procedures(self):
        sql = (Path(__file__).parent / 'inspect_schema.sql').read_text()
        sql = re.sub(r'--[^\n]*', '', sql)
        self.assertFalse(re.search(r'\b(CREATE|ALTER|DROP|DELETE|INSERT|UPDATE|EXEC|EXECUTE|MERGE|TRUNCATE)\b', sql, re.I))
        relations = re.findall(r'\b(?:FROM|JOIN)\s+([\w.]+)', sql, re.I)
        self.assertTrue(relations)
        self.assertTrue(all(name.startswith('sys.') for name in relations))

    def test_utf16_schema_and_lf_normalization(self):
        self.assertEqual(decoded('CREATE TABLE\r\n'.encode('utf-16')), 'CREATE TABLE\n')
        self.assertEqual(decoded(b'\xef\xbb\xbfCREATE TABLE\r\n'), 'CREATE TABLE\n')

    def test_source_sql_signatures_handle_comments_and_datetime_scale(self):
        sql = '''-- CREATE PROCEDURE dbo.ap_GStat @bad int AS
        CREATE PROCEDURE [dbo].[ap_GStat]
        @a varchar(14), /* no fake param */ @time datetime2(3) OUTPUT
        AS SELECT 1;'''
        self.assertEqual(procedure_parameters(sql, 'ap_GStat'), [[('varchar', 14, False), ('datetime2', 3, True)]])
        with self.assertRaises(ValueError):
            procedure_parameters('CREATE PROCEDURE dbo.ap_GStat @a strange AS SELECT 1', 'ap_GStat')


if __name__ == '__main__':
    unittest.main()

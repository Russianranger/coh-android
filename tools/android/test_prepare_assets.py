"""Reject actual failed Wine import paths before packaging the next APK."""
import unittest
from prepare_assets import ODBC_ANSI_ALIASES, ODBC_REQUIRED_IMPORTS, verify_odbc_imports


class OdbcImportTests(unittest.TestCase):
    def dump(self, names):
        return '\tDLL Name: ODBC32.dll\n\tvma: Hint/Ord Member-Name Bound-To\n' + ''.join(
            '\t13614\t 29  '+name+'\n' for name in names)

    def original_imports(self):
        return ['SQLAllocHandle', 'SQLBindParameter', 'SQLColumnsA', 'SQLDisconnect',
                'SQLDriverConnectA', 'SQLEndTran', 'SQLExecDirectA', 'SQLFetch',
                'SQLFreeHandle', 'SQLGetData', 'SQLGetDiagRec', 'SQLGetDiagRecA',
                'SQLGetInfoA', 'SQLMoreResults', 'SQLSetConnectAttr', 'SQLSetEnvAttr']

    def test_original_stub_import_table_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'stubbed or broken'):
            verify_odbc_imports(self.dump(self.original_imports()))

    def test_previous_ansi_info_route_is_rejected(self):
        names = [ODBC_ANSI_ALIASES.get(name, name) for name in self.original_imports()]
        names = [{'SQLGetInfoA':'SQLGetInfo', 'SQLColumnsA':'SQLColumnsW'}.get(name, name) for name in names]
        with self.assertRaisesRegex(ValueError, 'stubbed or broken'):
            verify_odbc_imports(self.dump(names))

    def test_previous_ansi_columns_route_is_rejected(self):
        names = [ODBC_ANSI_ALIASES.get(name, name) for name in self.original_imports()]
        names = [{'SQLGetInfoA':'SQLGetInfoW', 'SQLColumnsA':'SQLColumns'}.get(name, name) for name in names]
        with self.assertRaisesRegex(ValueError, 'stubbed or broken'):
            verify_odbc_imports(self.dump(names))

    def test_wide_metadata_preserves_remaining_fixture_imports(self):
        names = [ODBC_ANSI_ALIASES.get(name, name) for name in self.original_imports()]
        names = [{'SQLGetInfoA':'SQLGetInfoW', 'SQLColumnsA':'SQLColumnsW'}.get(name, name) for name in names]
        self.assertEqual(verify_odbc_imports(self.dump(names)), sorted(names))

    def test_each_missing_required_operation_is_rejected(self):
        names = sorted(ODBC_REQUIRED_IMPORTS)
        for missing in names:
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'lacks required'):
                verify_odbc_imports(self.dump([name for name in names if name != missing]))

    def test_wide_import_does_not_allow_a_forbidden_import_alongside(self):
        for forbidden in ['SQLGetInfoA', 'SQLGetInfo', 'SQLColumnsA', 'SQLColumns', 'SQLExecDirectA', 'SQLDriverConnectA']:
            with self.subTest(forbidden=forbidden), self.assertRaisesRegex(ValueError, 'stubbed or broken'):
                verify_odbc_imports(self.dump([*ODBC_REQUIRED_IMPORTS, forbidden]))

    def test_export_or_unrelated_library_is_not_an_import_proof(self):
        text = self.dump(sorted(ODBC_REQUIRED_IMPORTS))
        with self.assertRaisesRegex(ValueError, 'Windows ODBC manager'):
            verify_odbc_imports(text.replace('ODBC32.dll', 'OTHER.dll'))


if __name__ == '__main__':
    unittest.main()

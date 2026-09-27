"""Reject the actual failed Wine import pattern before packaging the next APK."""
import unittest
from prepare_assets import ODBC_ANSI_ALIASES, verify_odbc_imports


class OdbcImportTests(unittest.TestCase):
    def dump(self, names):
        return '\tDLL Name: ODBC32.dll\n\tvma: Hint/Ord Member-Name Bound-To\n' + ''.join(
            '\t13614\t 29  '+name+'\n' for name in names)

    def test_original_failed_import_table_is_rejected(self):
        names = ['SQLAllocHandle', 'SQLBindParameter', 'SQLColumnsA', 'SQLDisconnect',
                 'SQLDriverConnectA', 'SQLEndTran', 'SQLExecDirectA', 'SQLFetch',
                 'SQLFreeHandle', 'SQLGetData', 'SQLGetDiagRec', 'SQLGetDiagRecA',
                 'SQLGetInfoA', 'SQLMoreResults', 'SQLSetConnectAttr', 'SQLSetEnvAttr']
        with self.assertRaisesRegex(ValueError, 'unimplemented Wine ANSI alias'):
            verify_odbc_imports(self.dump(names))
        mapped = [ODBC_ANSI_ALIASES.get(name, name) for name in names]
        self.assertEqual(verify_odbc_imports(self.dump(mapped)), sorted(mapped))

    def test_each_missing_required_operation_is_rejected(self):
        names = [*ODBC_ANSI_ALIASES.values(), 'SQLGetDiagRecA']
        for missing in names:
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'lacks required'):
                verify_odbc_imports(self.dump([name for name in names if name != missing]))

    def test_export_or_unrelated_library_is_not_an_import_proof(self):
        text = self.dump([*ODBC_ANSI_ALIASES.values(), 'SQLGetDiagRecA'])
        with self.assertRaisesRegex(ValueError, 'Windows ODBC manager'):
            verify_odbc_imports(text.replace('ODBC32.dll', 'OTHER.dll'))


if __name__ == '__main__':
    unittest.main()

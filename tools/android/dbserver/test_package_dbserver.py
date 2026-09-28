"""Import parsing must reject missing/stubbed/broken real server dependencies."""
import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from test_package_reference_runtime import pe_file
from package_dbserver import imported_functions


def image(names=('SQLGetInfoW', 'SQLColumnsW')):
    data = bytearray(pe_file(('odbc32.dll',)))
    struct.pack_into('<I', data, 512, 0x1200)
    for index, name in enumerate(names):
        rva = 0x1500 + index * 64
        struct.pack_into('<I', data, 1024 + index * 4, rva)
        start = rva - 0x1000 + 512
        data[start:start + len(name) + 3] = b'\0\0' + name.encode() + b'\0'
    return data


class ImportTests(unittest.TestCase):
    def test_named_import_lookup(self):
        self.assertEqual(imported_functions(image()), ['SQLColumnsW', 'SQLGetInfoW'])

    def test_missing_lookup_rejected(self):
        data = image()
        struct.pack_into('<I', data, 512, 0)
        with self.assertRaisesRegex(ValueError, 'Missing import lookup'):
            imported_functions(data)

    def test_iat_fallback(self):
        data = image()
        struct.pack_into('<I', data, 512, 0)
        struct.pack_into('<I', data, 528, 0x1200)
        self.assertEqual(imported_functions(data), ['SQLColumnsW', 'SQLGetInfoW'])

    def test_ordinal_cannot_satisfy_named_contract(self):
        data = image()
        struct.pack_into('<I', data, 1024, 0x80000001)
        with self.assertRaisesRegex(ValueError, 'Ordinal'):
            imported_functions(data)

    def test_out_of_bounds_name(self):
        data = image()
        struct.pack_into('<I', data, 1024, 0x7ffffff0)
        with self.assertRaisesRegex(ValueError, 'outside PE raw bounds'):
            imported_functions(data)

    def test_lookalike_library_rejected(self):
        data = image()
        with self.assertRaisesRegex(ValueError, 'Missing ODBC'):
            imported_functions(data, 'odbc32-fake.dll')


if __name__ == '__main__':
    unittest.main()

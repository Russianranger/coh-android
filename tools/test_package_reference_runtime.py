"""Reject mixed architectures, stale receipts and incomplete portable packages."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from package_reference_runtime import (DYNAMIC_DLLS, PRODUCTS, SYMBOLS,
                                       dependency_report, package, pe_info)


def pe_file(imports=(), delay=(), machine=0x14c):
    data = bytearray(2048)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<HH', data, 132, machine, 1)
    struct.pack_into('<H', data, 148, 224)
    optional = 152
    struct.pack_into('<H', data, optional, 0x10b)
    struct.pack_into('<I', data, optional + 28, 0x400000)
    struct.pack_into('<I', data, optional + 60, 512)
    struct.pack_into('<I', data, optional + 92, 16)
    struct.pack_into('<4I', data, optional + 224 + 8, 1536, 0x1000, 1536, 512)
    for names, index, table_rva, table_offset, descriptor_size in (
            (imports, 1, 0x1000, 512, 20), (delay, 13, 0x1100, 768, 32)):
        if not names:
            continue
        struct.pack_into('<II', data, optional + 96 + index * 8,
                         table_rva, descriptor_size * (len(names) + 1))
        for offset, name in enumerate(names):
            nrva = 0x1300 + index * 16 + offset * 64
            npos = nrva - 0x1000 + 512
            data[npos:npos + len(name) + 1] = name.encode() + b'\0'
            if index == 1:
                struct.pack_into('<5I', data, table_offset + offset * descriptor_size,
                                 0, 0, 0, nrva, 0)
            else:
                struct.pack_into('<8I', data, table_offset + offset * descriptor_size,
                                 1, nrva, 0, 0, 0, 0, 0, 0)
    return bytes(data)


class PackageTests(unittest.TestCase):
    def test_import_and_delay_tables(self):
        info = pe_info(pe_file(('KERNEL32.dll', 'VCRUNTIME140.dll'), ('NVCPL.dll',)))
        self.assertEqual(info['pe_machine'], 332)
        self.assertEqual(info['imports'], ['KERNEL32.dll', 'VCRUNTIME140.dll'])
        self.assertEqual(info['delay_imports'], ['NVCPL.dll'])

    def test_wrong_architecture_and_truncation(self):
        with self.assertRaisesRegex(ValueError, 'Win32 x86'):
            pe_info(pe_file(machine=0x8664))
        with self.assertRaisesRegex(ValueError, 'outside file'):
            pe_info(pe_file(('KERNEL32.dll',))[:-1])

    def test_import_name_outside_sections(self):
        data = bytearray(pe_file(('KERNEL32.dll',)))
        struct.pack_into('<I', data, 512 + 12, 0xffff0000)
        with self.assertRaisesRegex(ValueError, 'RVA outside'):
            pe_info(data)

    def test_optional_driver_is_not_excuse_for_mandatory_import(self):
        mandatory = dependency_report({'test.exe': pe_info(pe_file(('NVCPL.dll',)))})
        self.assertEqual(mandatory['unresolved'], ['test.exe -> NVCPL.dll'])
        optional = dependency_report({'test.exe': pe_info(pe_file(delay=('NVCPL.dll',)))})
        self.assertEqual(optional['unresolved'], [])

    def fixture(self, root):
        binary = root / 'binaries'
        binary.mkdir()
        for name in PRODUCTS + DYNAMIC_DLLS:
            (binary / name).write_bytes(pe_file(('KERNEL32.dll',)))
        for name in SYMBOLS:
            (binary / name).write_bytes(b'fixture symbols')
        (binary / 'CrashRpt.dll').write_bytes(pe_file(('VCRUNTIME140.dll',)))
        crt = root / 'crt'
        crt.mkdir()
        (crt / 'VCRUNTIME140.dll').write_bytes(pe_file(('KERNEL32.dll',)))
        (root / 'upstream-lock.json').write_text(json.dumps({'commit': '1' * 40}))
        patch = root / 'patches/postgresql/0001-dbserver-postgresql.patch'
        patch.parent.mkdir(parents=True)
        patch.write_bytes(b'fixture patch\n')
        overlay = root / 'database/postgresql/overlay'
        overlay.mkdir(parents=True)
        receipt = root / 'postgresql-build-input.json'
        receipt.write_text(json.dumps({'source_commit': '1' * 40,
                                      'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
                                      'overlay_sha256': {}, 'patched_sha256': {}}))
        cache = root / 'CMakeCache.txt'
        cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n')
        return binary, receipt, cache, [crt]

    def test_complete_flat_package_and_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.fixture(root)
            out = root / 'package'
            manifest = package(*inputs, out, '2' * 40, root=root)
            self.assertFalse(manifest['postgresql_persistence_fixture'])
            self.assertEqual(manifest['dependency_report']['unresolved'], [])
            self.assertEqual(manifest['files']['CrashRpt.dll']['imports'], ['VCRUNTIME140.dll'])
            with zipfile.ZipFile(out / 'coh-reference-win32.zip') as archive:
                self.assertIn('TestClient.exe', archive.namelist())
                self.assertIn('VCRUNTIME140.dll', archive.namelist())
                self.assertIn(('Commit: ' + '1' * 40).encode(), archive.read('build-info.txt'))
                self.assertTrue(all('/' not in name for name in archive.namelist()))
            self.assertEqual(len((out / 'SHA256SUMS.txt').read_text().splitlines()), 2)

    def test_missing_crt_fails_before_creating_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary, receipt, cache, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'Unresolved runtime imports'):
                package(binary, receipt, cache, [], root / 'out', '2' * 40, root=root)
            self.assertFalse((root / 'out').exists())

    def test_fixture_enabled_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.fixture(root)
            inputs[2].write_text('COH_PG_PERSISTENCE_TESTS:BOOL=ON\n')
            with self.assertRaisesRegex(ValueError, 'fixture mode OFF'):
                package(*inputs, root / 'out', '2' * 40, root=root)

    def test_stale_patch_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.fixture(root)
            (root / 'patches/postgresql/0001-dbserver-postgresql.patch').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'patch mismatch'):
                package(*inputs, root / 'out', '2' * 40, root=root)


if __name__ == '__main__':
    unittest.main()

"""Keep the diagnostic TestClient bound to its source and accepted base runtime."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

import package_resume_client as diagnostic
from package_reference_runtime import file_record
from prepare_resume_client_source import expected_resume_receipt
from test_package_reference_runtime import pe_file


class ResumeClientPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = expected_resume_receipt()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.binary = self.root / 'bin'
        self.binary.mkdir()
        self.exe = self.binary / diagnostic.EXECUTABLE
        self.exe.write_bytes(pe_file(('KERNEL32.dll', 'VCRUNTIME140.dll')))
        (self.binary / diagnostic.SYMBOL).write_bytes(b'fixture symbols')
        self.receipt = self.root / diagnostic.RECEIPT
        self.receipt.write_text(json.dumps(self.expected), encoding='utf-8')
        self.cache = self.root / 'CMakeCache.txt'
        self.cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n')
        self.output = self.root / 'package'
        self.commit = '2' * 40
        self.runtime = self.output / 'runtime'
        self.accepted_exe = self.root / diagnostic.EXECUTABLE
        self.accepted_exe.write_bytes(pe_file(('KERNEL32.dll',)))
        dll = self.root / 'VCRUNTIME140.dll'
        dll.write_bytes(pe_file(('KERNEL32.dll',)))
        self.accepted = {
            'source_commit': self.expected['source_commit'],
            'postgresql_build_input': copy.deepcopy(self.expected['postgresql_build_input']),
            'files': {diagnostic.EXECUTABLE: file_record(self.accepted_exe),
                      dll.name: file_record(dll)},
        }

    def package(self):
        return diagnostic.package(self.binary, self.receipt, self.cache, self.output,
                                  self.commit, 'https://github.com/example/repo/actions/runs/123')

    def verify(self):
        return diagnostic.verify_resume_client_package(self.runtime, self.commit, self.accepted)

    def rewrite_manifest(self, update):
        path = self.runtime / 'build-info.json'
        manifest = json.loads(path.read_text())
        update(manifest)
        path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_separate_flat_client_and_symbols_use_accepted_dependencies(self):
        before = copy.deepcopy(self.accepted)
        original = self.accepted_exe.read_bytes()
        built = self.package()
        executable, verified = self.verify()
        self.assertEqual(executable, self.runtime / diagnostic.EXECUTABLE)
        self.assertEqual(verified, built)
        self.assertEqual(set(p.name for p in self.runtime.iterdir()), diagnostic.PACKAGE_FILES)
        self.assertEqual(set(p.name for p in (self.output / 'symbols').iterdir()),
                         {diagnostic.SYMBOL, 'build-info.json'})
        self.assertFalse(list(self.runtime.glob('*.dll')))
        self.assertEqual(self.accepted, before)
        self.assertEqual(self.accepted_exe.read_bytes(), original)
        self.assertEqual(verified['status'], diagnostic.STATUS)
        self.assertFalse(verified['postgresql_persistence_fixture'])

    def test_stale_resume_patch_or_patched_source_receipt_rejected(self):
        receipt = copy.deepcopy(self.expected)
        name = next(iter(receipt['patched_sha256']))
        receipt['patched_sha256'][name] = '0' * 64
        self.receipt.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'differs from pinned source'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_stale_postgresql_receipt_rejected(self):
        receipt = copy.deepcopy(self.expected)
        receipt['postgresql_build_input']['patch_sha256'] = '0' * 64
        self.receipt.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_wrong_architecture_rejected_before_package_creation(self):
        self.exe.write_bytes(pe_file(machine=0x8664))
        with self.assertRaisesRegex(ValueError, 'Win32 x86'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_persistence_fixture_build_rejected(self):
        self.cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=ON\n')
        with self.assertRaisesRegex(ValueError, 'fixture mode OFF'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_missing_symbols_rejected_before_package_creation(self):
        (self.binary / diagnostic.SYMBOL).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing, empty or symlink'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_stale_repository_commit_rejected(self):
        self.package()
        with self.assertRaisesRegex(ValueError, 'repository commit mismatch'):
            diagnostic.verify_resume_client_package(self.runtime, '3' * 40, self.accepted)

    def test_runtime_must_match_exact_postgresql_receipt_even_for_known_eol_profile(self):
        self.package()
        pg = self.accepted['postgresql_build_input']
        alternate = copy.deepcopy(pg)
        for name, digest in pg['overlay_sha256'].items():
            if Path(name).suffix.lower() not in ('.c', '.h'):
                continue
            raw = (diagnostic.ROOT / 'database/postgresql/overlay' / name).read_bytes()
            lf = raw.replace(b'\r\n', b'\n')
            for data in (lf, lf.replace(b'\n', b'\r\n')):
                candidate = hashlib.sha256(data).hexdigest()
                if candidate != digest:
                    alternate['overlay_sha256'][name] = candidate
                    break
            if alternate != pg:
                break
        self.assertNotEqual(alternate, pg)
        # Prove this is a legitimate profile, while still rejecting a mixed build.
        expected_resume_receipt(postgresql_build_input=alternate)
        self.accepted['postgresql_build_input'] = alternate
        with self.assertRaisesRegex(ValueError, 'PostgreSQL receipts differ'):
            self.verify()

    def test_missing_accepted_runtime_dependency_rejected(self):
        self.package()
        del self.accepted['files']['VCRUNTIME140.dll']
        with self.assertRaisesRegex(ValueError, 'unresolved.*TestClient.exe -> VCRUNTIME140.dll'):
            self.verify()

    def test_new_unapproved_dependency_rejected_at_acceptance(self):
        self.exe.write_bytes(pe_file(('unexpected.dll',)))
        self.package()
        with self.assertRaisesRegex(ValueError, 'unresolved.*unexpected.dll'):
            self.verify()

    def test_allowed_windows_api_and_optional_delay_import(self):
        self.exe.write_bytes(pe_file(('KERNEL32.dll', 'api-ms-win-core-file-l1-1-0.dll'),
                                    ('NVCPL.dll',)))
        self.package()
        self.verify()

    def test_optional_driver_mandatory_import_remains_rejected(self):
        self.exe.write_bytes(pe_file(('NVCPL.dll',)))
        self.package()
        with self.assertRaisesRegex(ValueError, 'unresolved.*NVCPL.dll'):
            self.verify()

    def test_modified_executable_bytes_rejected(self):
        self.package()
        target = self.runtime / diagnostic.EXECUTABLE
        target.write_bytes(target.read_bytes() + b'unrecorded bytes')
        with self.assertRaisesRegex(ValueError, 'size/SHA-256 or PE metadata mismatch'):
            self.verify()

    def test_rehashed_wrong_architecture_still_rejected(self):
        self.package()
        target = self.runtime / diagnostic.EXECUTABLE
        data = bytearray(target.read_bytes())
        struct.pack_into('<H', data, 132, 0x8664)
        target.write_bytes(data)
        self.rewrite_manifest(lambda manifest: manifest['files'][diagnostic.EXECUTABLE].update(
            sha256=hashlib.sha256(data).hexdigest(), size=len(data), pe_machine=0x8664))
        with self.assertRaisesRegex(ValueError, 'Win32 x86'):
            self.verify()

    def test_hidden_import_in_manifest_rejected(self):
        self.package()
        self.rewrite_manifest(lambda manifest: manifest['files'][diagnostic.EXECUTABLE].update(imports=[]))
        with self.assertRaisesRegex(ValueError, 'PE metadata mismatch'):
            self.verify()

    def test_rehashed_receipt_file_must_equal_embedded_receipt(self):
        self.package()
        target = self.runtime / diagnostic.RECEIPT
        changed = copy.deepcopy(self.expected)
        changed['source_commit'] = '0' * 40
        target.write_text(json.dumps(changed))
        self.rewrite_manifest(lambda manifest: manifest['files'].update(
            {diagnostic.RECEIPT: file_record(target)}))
        with self.assertRaisesRegex(ValueError, 'Packaged and embedded.*differ'):
            self.verify()

    def test_added_dll_or_nested_file_rejected(self):
        self.package()
        for name in ('unapproved.dll', 'nested/notes.txt'):
            with self.subTest(name=name):
                path = self.runtime / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'unlisted')
                with self.assertRaisesRegex(ValueError, 'only the executable and two flat receipts'):
                    self.verify()
                path.unlink()

    def test_unrelated_build_role_rejected(self):
        self.package()
        self.rewrite_manifest(lambda manifest: manifest.update(build_role='reference_runtime'))
        with self.assertRaisesRegex(ValueError, 'separately identified'):
            self.verify()


if __name__ == '__main__':
    unittest.main()

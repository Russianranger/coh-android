"""Reject substituted binaries, source receipts, protocol formats and build roles."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_mapserver_progress as progress
from package_reference_runtime import file_record
from test_package_reference_runtime import pe_file


class MapServerProgressPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = progress.expected_progress_receipt()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.args = SimpleNamespace(repository_commit='a' * 40, run_url='', output=self.root / 'out',
                                    directory=self.root / 'build', build_input=self.root / progress.RECEIPT,
                                    cache=self.root / 'CMakeCache.txt')
        self.args.directory.mkdir()
        self.args.build_input.write_text(json.dumps(self.receipt, indent=2) + '\n')
        self.args.cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n')
        (self.args.directory / 'MapServer.exe').write_bytes(pe_file(('KERNEL32.dll', 'VCRUNTIME140.dll')))
        (self.args.directory / 'MapServer.pdb').write_bytes(b'MapServer progress symbols')
        dll = self.root / 'VCRUNTIME140.dll'
        dll.write_bytes(pe_file(('KERNEL32.dll',)))
        self.reference = {'source_commit': self.receipt['source_commit'],
                          'postgresql_build_input': copy.deepcopy(self.receipt['game_build_input']['postgresql_build_input']),
                          'files': {'VCRUNTIME140.dll': file_record(dll)}}
        self.runtime = self.args.output / 'runtime'

    def package(self):
        return progress.package(self.args, self.reference)

    def verify(self, commit=None):
        return progress.verify_mapserver_progress_package(self.runtime, commit or self.args.repository_commit, self.reference)

    def rewrite(self, value):
        (self.runtime / 'build-info.json').write_text(json.dumps(value, indent=2) + '\n')

    def test_separate_mapserver_only_runtime_and_symbols_preserve_reference(self):
        before = copy.deepcopy(self.reference)
        manifest = self.package()
        executable, actual = self.verify()
        self.assertEqual(actual, manifest)
        self.assertEqual(executable, self.runtime / 'MapServer.exe')
        self.assertEqual({p.name for p in self.runtime.iterdir()}, progress.PACKAGE_FILES)
        self.assertEqual({p.name for p in (self.args.output / 'symbols').iterdir()}, {'MapServer.pdb', 'build-info.json'})
        self.assertEqual(self.reference, before)
        self.assertEqual(manifest['build_targets'], ['MapServer'])
        self.assertEqual(manifest['progress_contract'], self.receipt['progress_contract'])
        self.assertFalse(manifest['runtime_execution_validated'])

    def test_rehashed_source_or_contract_cannot_weaken_expected_source(self):
        original = self.package()
        for mutation in (lambda value: value['build_input']['patched_sha256'].update({'MapServer/src/svr/svr_tick.c': '0' * 64}),
                         lambda value: value['build_input']['progress_contract'].update(format=2)):
            value = copy.deepcopy(original)
            mutation(value)
            value['progress_contract'] = value['build_input']['progress_contract']
            source = self.runtime / progress.RECEIPT
            source.write_text(json.dumps(value['build_input'], indent=2) + '\n')
            value['files'][source.name] = file_record(source)
            self.rewrite(value)
            with self.assertRaisesRegex(ValueError, 'differs from pinned source'):
                self.verify()

    def test_unknown_identity_fixture_or_build_target_rejected(self):
        original = self.package()
        with self.assertRaisesRegex(ValueError, 'repository commit mismatch'):
            self.verify('b' * 40)
        for fields in ({'build_role': 'loopback_game_diagnostic'}, {'build_targets': ['MapServer', 'TestClient']},
                       {'postgresql_persistence_fixture': True}, {'runtime_execution_validated': True},
                       {'progress_contract': dict(original['progress_contract'], mapping_bytes=128)}):
            self.rewrite(dict(original, **fields))
            with self.assertRaises(ValueError):
                self.verify()

    def test_fixture_cache_must_have_one_explicit_off(self):
        for text in ('', 'COH_PG_PERSISTENCE_TESTS:BOOL=ON\n',
                     'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCOH_PG_PERSISTENCE_TESTS:BOOL=OFF\n'):
            self.args.cache.write_text(text)
            with self.assertRaisesRegex(ValueError, 'fixture mode OFF'):
                self.package()
            self.assertFalse(self.args.output.exists())

    def test_missing_symbols_wrong_architecture_and_imports_rejected(self):
        symbol = self.args.directory / 'MapServer.pdb'
        symbol.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing, empty or symlink'):
            self.package()
        symbol.write_bytes(b'symbols')
        executable = self.args.directory / 'MapServer.exe'
        executable.write_bytes(pe_file(machine=0x8664))
        with self.assertRaisesRegex(ValueError, 'Win32 x86'):
            self.package()
        executable.write_bytes(pe_file(('unexpected.dll',)))
        with self.assertRaisesRegex(ValueError, 'unresolved.*unexpected.dll'):
            self.package()
        self.assertFalse(self.args.output.exists())

    def test_modified_executable_embedded_receipt_or_extra_payload_rejected(self):
        original = self.package()
        executable = self.runtime / 'MapServer.exe'
        data = executable.read_bytes()
        executable.write_bytes(data + b'changed')
        with self.assertRaisesRegex(ValueError, 'PE metadata mismatch'):
            self.verify()
        executable.write_bytes(data)
        changed = copy.deepcopy(original)
        changed['files'][progress.RECEIPT]['sha256'] = '0' * 64
        self.rewrite(changed)
        with self.assertRaisesRegex(ValueError, 'embedded source receipt bytes differ'):
            self.verify()
        self.rewrite(original)
        for name in ('TestClient.exe', 'extra.dll', 'nested/receipt.json'):
            path = self.runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'foreign')
            with self.assertRaisesRegex(ValueError, 'only MapServer and flat receipts'):
                self.verify()
            path.unlink()
        link = self.runtime / 'linked'
        link.symlink_to(executable)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.verify()

    def test_crlf_source_receipt_has_exact_actual_byte_record(self):
        self.args.build_input.write_bytes(self.args.build_input.read_bytes().replace(b'\n', b'\r\n'))
        actual = self.package()
        self.assertEqual(actual['files'][progress.RECEIPT], file_record(self.args.build_input))
        self.verify()


if __name__ == '__main__':
    unittest.main()

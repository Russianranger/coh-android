"""Reject stale source evidence, fixture binaries and substituted loopback donors."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_loopback_game as game
from package_reference_runtime import file_record
from test_package_reference_runtime import pe_file


class LoopbackGamePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipts = {variant: game.expected_game_receipt(variant=variant) for variant in game.RECEIPTS}

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.args = SimpleNamespace(repository_commit='a' * 40, run_url='', output=self.root / 'out')
        for variant, prefix in (('creation', 'create'), ('resume', 'resume')):
            directory = self.root / variant
            directory.mkdir()
            setattr(self.args, prefix + '_directory', directory)
            receipt_path = directory / 'game-loopback-build-input.json'
            receipt_path.write_text(json.dumps(self.receipts[variant], indent=2) + '\n')
            setattr(self.args, prefix + '_build_input', receipt_path)
            cache = directory / 'CMakeCache.txt'
            cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n')
            setattr(self.args, prefix + '_cache', cache)
            for name in ('MapServer', 'TestClient') if variant == 'creation' else ('TestClient',):
                (directory / (name + '.exe')).write_bytes(pe_file(('KERNEL32.dll', 'VCRUNTIME140.dll')) + variant.encode())
                (directory / (name + '.pdb')).write_bytes((variant + name + ' symbols').encode())
        dll = self.root / 'VCRUNTIME140.dll'
        dll.write_bytes(pe_file(('KERNEL32.dll',)))
        self.reference = {'source_commit': self.receipts['creation']['source_commit'],
                          'postgresql_build_input': copy.deepcopy(self.receipts['creation']['postgresql_build_input']),
                          'files': {'VCRUNTIME140.dll': file_record(dll)}}
        self.runtime = self.args.output / 'runtime'

    def package(self):
        return game.package(self.args, self.reference)

    def verify(self, commit=None):
        return game.verify_loopback_game_package(self.runtime, commit or self.args.repository_commit, self.reference)

    def rewrite(self, fn):
        path = self.runtime / 'build-info.json'
        value = json.loads(path.read_text())
        fn(value)
        path.write_text(json.dumps(value, indent=2) + '\n')

    def test_separate_three_executable_donor_preserves_reference_and_symbols(self):
        before = copy.deepcopy(self.reference)
        manifest = self.package()
        selected, actual = self.verify()
        self.assertEqual(actual, manifest)
        self.assertEqual(set(selected), set(game.EXECUTABLES))
        self.assertEqual(set(p.name for p in self.runtime.iterdir()), game.PACKAGE_FILES)
        self.assertEqual(set(p.name for p in (self.args.output / 'symbols').iterdir()), {*game.SYMBOLS, 'build-info.json'})
        self.assertEqual(self.reference, before)
        self.assertFalse(list(self.runtime.glob('*.dll')))
        self.assertFalse(manifest['runtime_execution_validated'])
        self.assertEqual(manifest['status'], game.STATUS)
        self.assertNotEqual(manifest['files']['TestClientCreate.exe']['sha256'],
                            manifest['files']['TestClientResume.exe']['sha256'])

    def test_stale_or_swapped_source_receipts_rejected_before_output(self):
        for variant, prefix in (('creation', 'create'), ('resume', 'resume')):
            for mutation in ('hash', 'variant'):
                with self.subTest(variant=variant, mutation=mutation):
                    changed = copy.deepcopy(self.receipts[variant])
                    if mutation == 'hash':
                        changed['patched_sha256'][next(iter(changed['patched_sha256']))] = '0' * 64
                    else:
                        changed['variant'] = 'resume' if variant == 'creation' else 'creation'
                    path = getattr(self.args, prefix + '_build_input')
                    path.write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError, 'differs from pinned source'):
                        self.package()
                    self.assertFalse(self.args.output.exists())
                    path.write_text(json.dumps(self.receipts[variant], indent=2) + '\n')

    def test_fixture_mode_missing_on_or_duplicate_off_rejected(self):
        for prefix in ('create', 'resume'):
            for text in ('', 'COH_PG_PERSISTENCE_TESTS:BOOL=ON\n',
                         'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCOH_PG_PERSISTENCE_TESTS:BOOL=ON\n'):
                with self.subTest(prefix=prefix, text=text):
                    cache = getattr(self.args, prefix + '_cache')
                    cache.write_text(text)
                    with self.assertRaisesRegex(ValueError, 'fixture mode OFF'):
                        self.package()
                    self.assertFalse(self.args.output.exists())
                    cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n')

    def test_missing_symbols_and_wrong_architecture_rejected(self):
        symbol = self.args.resume_directory / 'TestClient.pdb'
        symbol.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing, empty or symlink'):
            self.package()
        self.assertFalse(self.args.output.exists())
        symbol.write_bytes(b'symbols')
        (self.args.create_directory / 'MapServer.exe').write_bytes(pe_file(machine=0x8664))
        with self.assertRaisesRegex(ValueError, 'Win32 x86'):
            self.package()
        self.assertFalse(self.args.output.exists())

    def test_unresolved_new_import_rejected_before_output(self):
        (self.args.resume_directory / 'TestClient.exe').write_bytes(pe_file(('unexpected.dll',)))
        with self.assertRaisesRegex(ValueError, 'unresolved.*unexpected.dll'):
            self.package()
        self.assertFalse(self.args.output.exists())

    def test_stale_build_commit_or_fixture_provenance_rejected(self):
        original = self.package()
        with self.assertRaisesRegex(ValueError, 'repository commit mismatch'):
            self.verify('b' * 40)
        for mutation in (lambda v: v.update(postgresql_persistence_fixture=True),
                         lambda v: v.update(runtime_execution_validated=True),
                         lambda v: v['variants']['resume'].update(postgresql_persistence_fixture=True)):
            self.rewrite(lambda v: (v.clear(), v.update(copy.deepcopy(original)), mutation(v)))
            with self.assertRaisesRegex(ValueError, 'fixture'):
                self.verify()

    def test_rehashed_consistent_receipts_cannot_weaken_source_contract(self):
        self.package()
        changed = copy.deepcopy(self.receipts['resume'])
        changed['patched_sha256'][next(iter(changed['patched_sha256']))] = '0' * 64
        path = self.runtime / game.RECEIPTS['resume']
        path.write_text(json.dumps(changed))
        self.rewrite(lambda v: (v['variants']['resume'].update(build_input=changed),
                                v['files'].update({path.name: file_record(path)})))
        with self.assertRaisesRegex(ValueError, 'differs from pinned source'):
            self.verify()

    def test_modified_executable_or_hidden_import_rejected(self):
        original = self.package()
        executable = self.runtime / 'MapServer.exe'
        data = executable.read_bytes()
        executable.write_bytes(data + b'changed')
        with self.assertRaisesRegex(ValueError, 'PE metadata mismatch'):
            self.verify()
        executable.write_bytes(data)
        self.rewrite(lambda v: v['files']['MapServer.exe'].update(imports=[]))
        with self.assertRaisesRegex(ValueError, 'dependency report differs'):
            self.verify()

    def test_extra_nested_or_symlink_file_rejected(self):
        self.package()
        for name in ('extra.dll', 'nested/receipt.json'):
            path = self.runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'unlisted')
            with self.assertRaisesRegex(ValueError, 'only three executables'):
                self.verify()
            path.unlink()
        path = self.runtime / 'extra.dll'
        path.symlink_to(self.runtime / 'MapServer.exe')
        with self.assertRaisesRegex(ValueError, 'Symlinks are not allowed'):
            self.verify()

    def test_dependency_inventory_and_source_pin_cannot_be_substituted(self):
        self.package()
        del self.reference['files']['VCRUNTIME140.dll']
        self.reference['files']['placeholder.txt'] = {'size': 1, 'sha256': 'a' * 64}
        with self.assertRaisesRegex(ValueError, 'unresolved.*VCRUNTIME140.dll'):
            self.verify()
        self.reference['source_commit'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'source commit mismatch'):
            self.verify()


if __name__ == '__main__':
    unittest.main()

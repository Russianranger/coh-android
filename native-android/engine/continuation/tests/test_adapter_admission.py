"""Reject substituted adapter artifacts before any Android operation."""
import copy
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_adapter_android import REQUIRED, c, validate, validate_checkout, bounded_execute, COMMAND_OUTPUT_MAX


class AdapterAdmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        fixture = self.root / 'original_matrix.h'
        fixture.write_text('admission-test-only fixture, never executed\n')
        result = {'passed': True, 'checks': 1, 'fixture_only': True, 'authentic_world_entry': False}
        self.proof = {'passed': True, 'fixture_only': True, 'prerequisites_available': False,
            'authentic_server_interoperability': False, 'physical_thor_accepted': False,
            'android_emulator_qualified': False, 'source_revision': 'a'*40, 'source_tree': 'b'*40,
            'clean_worktree_before': True, 'clean_worktree_after': True,
            'source_inputs_unchanged': True,
            'source_sha256': {name: 'c'*64 for name in REQUIRED},
            'fixtures_sha256': {'original_matrix.h': c.digest(fixture)},
            'host': result, 'address': copy.deepcopy(result), 'undefined': copy.deepcopy(result),
            'android_builds': {}}
        for abi, machine in c.ABIS.items():
            folder = self.root / 'android' / abi
            folder.mkdir(parents=True)
            binary = folder / 'world-render-adapter-test'
            raw = bytearray(64)
            raw[:7] = b'\x7fELF\x02\x01\x01'
            struct.pack_into('<HHI', raw, 16, 3, machine, 1)
            binary.write_bytes(raw)
            receipt = {'passed': True, 'abi': abi, 'api': 26, 'executed': False,
                'binary': binary.name, 'binary_sha256': c.digest(binary),
                'source_revision': self.proof['source_revision'], 'source_tree': self.proof['source_tree'],
                'source_sha256': copy.deepcopy(self.proof['source_sha256']),
                'fixtures_sha256': copy.deepcopy(self.proof['fixtures_sha256']),
                'expected_native_result': copy.deepcopy(result)}
            self.proof['android_builds'][abi] = receipt
            c.write(folder / 'build.json', receipt)

    def reject(self, proof=None):
        with self.assertRaises(ValueError):
            validate(self.root, proof or self.proof)

    def test_complete_fixture_builds(self):
        expected, entries = validate(self.root, self.proof)
        self.assertEqual(set(entries), set(c.ABIS))
        self.assertTrue(expected['fixture_only'])

    def test_missing_abi_and_source(self):
        value = copy.deepcopy(self.proof)
        del value['android_builds']['arm64-v8a']
        self.reject(value)
        value = copy.deepcopy(self.proof)
        del value['source_sha256'][next(iter(REQUIRED))]
        self.reject(value)

    def test_dirty_source_and_overclaim(self):
        for key, bad in [('clean_worktree_before', False), ('clean_worktree_after', False),
                         ('physical_thor_accepted', True), ('prerequisites_available', True),
                         ('authentic_server_interoperability', True), ('fixture_only', False),
                         ('source_inputs_unchanged', False), ('android_executed', True)]:
            value = copy.deepcopy(self.proof)
            value[key] = bad
            self.reject(value)

    def test_all_build_inputs_required(self):
        for source in REQUIRED:
            value = copy.deepcopy(self.proof)
            del value['source_sha256'][source]
            self.reject(value)

    def test_compilation_receipt_cannot_claim_execution(self):
        receipt = self.proof['android_builds']['arm64-v8a']
        for key in ('android_executed', 'emulator_qualified'):
            receipt[key] = True
            c.write(self.root / 'android/arm64-v8a/build.json', receipt)
            self.reject()
            del receipt[key]

    def test_checkout_tree_must_match(self):
        state = {'source_revision': self.proof['source_revision'], 'source_git_status_porcelain': []}
        with mock.patch('run_adapter_android.c.git_state', return_value=state), \
                mock.patch('run_adapter_android.subprocess.check_output', return_value='d'*40+'\n'):
            with self.assertRaisesRegex(ValueError, 'source/tree'):
                validate_checkout(self.root, self.proof)

    def test_sanitizers_and_json_types(self):
        for mode in ('address', 'undefined'):
            value = copy.deepcopy(self.proof)
            value[mode]['checks'] = True
            self.reject(value)

    def test_changed_binary_even_unexecuted_arm64(self):
        binary = self.root / 'android/arm64-v8a/world-render-adapter-test'
        binary.write_bytes(binary.read_bytes() + b'changed')
        self.reject()

    def test_wrong_machine_with_updated_digest(self):
        binary = self.root / 'android/x86_64/world-render-adapter-test'
        raw = bytearray(binary.read_bytes())
        struct.pack_into('<H', raw, 18, c.ABIS['arm64-v8a'])
        binary.write_bytes(raw)
        receipt = self.proof['android_builds']['x86_64']
        receipt['binary_sha256'] = c.digest(binary)
        c.write(binary.parent / 'build.json', receipt)
        self.reject()

    def test_changed_matrix_fixture(self):
        (self.root / 'original_matrix.h').write_text('substituted')
        self.reject()

    def test_relocated_receipt_path_rejected(self):
        receipt = self.proof['android_builds']['x86_64']
        receipt['binary'] = '../../world-render-adapter-test'
        c.write(self.root / 'android/x86_64/build.json', receipt)
        self.reject()

    def test_mixed_receipt_and_source_revision(self):
        receipt = copy.deepcopy(self.proof['android_builds']['arm64-v8a'])
        receipt['source_revision'] = 'd'*40
        c.write(self.root / 'android/arm64-v8a/build.json', receipt)
        self.reject()

    def test_duplicate_json_rejected(self):
        (self.root / 'android/arm64-v8a/build.json').write_text('{"passed":true,"passed":false}')
        self.reject()

    def test_oversize_command_output_not_decoded(self):
        with self.assertRaisesRegex(ValueError, 'decode ceiling'):
            bounded_execute([sys.executable, '-c',
                f'import sys; sys.stdout.write("x"*{COMMAND_OUTPUT_MAX+1})'], self.root/'oversize.log')
        self.assertEqual((self.root/'oversize.log').stat().st_size, COMMAND_OUTPUT_MAX+1)

    def test_failed_command_retains_log(self):
        with self.assertRaisesRegex(RuntimeError, 'command failed'):
            bounded_execute([sys.executable, '-c', 'print("failed fixture"); raise SystemExit(7)'],
                            self.root/'failed.log')
        self.assertEqual((self.root/'failed.log').read_text(), 'failed fixture\n')


if __name__ == '__main__':
    unittest.main()

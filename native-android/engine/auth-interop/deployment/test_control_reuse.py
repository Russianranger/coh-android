"""Synthetic admission controls; these do not execute Windows binaries or SQL."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import checksum_candidate
import generate_odbc
import hosted_auth_stage as stage

ROOT = Path(__file__).resolve().parents[4]


class ControlReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.directory = self.base / 'artifact'
        self.generated = self.base / 'generated'
        self.config = self.base / 'pins'
        for path in (self.directory, self.generated, self.config):
            path.mkdir()
        self.pins = json.loads((stage.HERE / 'control-build-reuse-pins.json').read_text())
        self.receipt = json.loads((stage.HERE.parent / 'evidence/hosted-sql-metadata-38946462964/receipt.json').read_text())
        checksum_candidate.prepare(ROOT, self.generated)
        generate_odbc.prepare(ROOT, self.generated)
        for name in self.pins['generated_sources']:
            # The actual retained Windows source uses CRLF; current host uses LF.
            (self.directory / name).write_bytes((self.generated / name).read_bytes().replace(b'\n', b'\r\n'))
        for name in ('configure-controls', 'build-controls'):
            file = self.directory / (name + '.log')
            file.write_text('synthetic successful compile control\n')
            row = next(x for x in self.receipt['commands'] if x['name'] == name)
            row['log_sha256'] = stage.sha(file)
        for name in ('original-policy', 'candidate-policy', 'original-odbc'):
            data = bytearray(160)
            data[:2] = b'MZ'
            struct.pack_into('<I', data, 60, 64)
            data[64:68] = b'PE\0\0'
            struct.pack_into('<H', data, 68, 0x14c)
            struct.pack_into('<H', data, 88, 0x10b)
            struct.pack_into('<H', data, 156, 3)
            file = self.directory / (name + '.exe')
            file.write_bytes(data)
            row = self.receipt['control_executions'][name]
            execution, result = row.get('executed'), row.get('result')
            row.update(stage.pe_identity(file, 3), executed=execution)
            if result is not None:
                row['result'] = result
        self.repin()

    def repin(self):
        # Test-only authority changes pins so semantic refusal is exercised too.
        (self.directory / 'receipt.json').write_text(json.dumps(self.receipt))
        self.pins['files'] = {x.name: {'bytes': x.stat().st_size, 'sha256': stage.sha(x)} for x in self.directory.iterdir()}
        (self.config / 'control-build-reuse-pins.json').write_text(json.dumps(self.pins))

    def admit(self, tree=stage.ORIGINAL_TREE):
        with patch.object(stage, 'HERE', self.config):
            return stage.admit_control_reuse(self.directory, self.generated, tree)

    def test_same_generated_source_and_pinned_binaries_admitted_without_execution_claim(self):
        result = self.admit()
        self.assertFalse(result['rebuilt'])
        self.assertFalse(result['odbc_qualification_inherited'])
        self.assertFalse(result['real_account_login_verified'])
        self.assertTrue(all(x['executed'] is False for x in result['binaries'].values()))

    def test_reused_binary_materializes_to_actual_execution_path(self):
        output = self.base / 'output'
        output.mkdir()
        for name in ('original-policy', 'candidate-policy', 'original-odbc'):
            retained = output / ('reused-controls-' + name + '.exe')
            retained.write_bytes((self.directory / (name + '.exe')).read_bytes())
            executable = stage.materialize_control(retained, output, name)
            self.assertEqual(executable, output / (name + '.exe'))
            self.assertEqual(stage.sha(executable), stage.sha(retained))
            self.assertFalse(stage.pe_identity(executable, 3)['executed'])
        with self.assertRaisesRegex(ValueError, 'unknown_control_name'):
            stage.materialize_control(retained, output, 'unadmitted')

    def test_generated_source_or_imported_tree_change_refused(self):
        with self.assertRaisesRegex(ValueError, 'source_tree_mismatch'):
            self.admit('1' * 40)
        for name in self.pins['generated_sources']:
            file = self.generated / name
            original = file.read_bytes()
            file.write_bytes(original + b'\n// changed\n')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'generated_source_mismatch'):
                self.admit()
            file.write_bytes(original)

    def test_each_artifact_file_mutation_refused(self):
        for name in self.pins['files']:
            file = self.directory / name
            original = file.read_bytes()
            file.write_bytes(original + b'x')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'file_identity_mismatch'):
                self.admit()
            file.write_bytes(original)

    def test_overclaims_and_unqualified_target_refused(self):
        for key, value in [('passed', True), ('source_inputs_unchanged', False),
                           ('owned_localdb_cleanup_complete', False), ('real_account_login_verified', True),
                           ('original_authserver_started', True), ('repository_commit', '1' * 40),
                           ('failure', 'other')]:
            original = self.receipt[key]
            self.receipt[key] = value
            self.repin()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'receipt_scope_mismatch'):
                self.admit()
            self.receipt[key] = original
        row = next(x for x in self.receipt['commands'] if x['name'] == 'build-controls')
        for value in (1, False, None):
            row['returncode'] = value
            self.repin()
            with self.subTest(returncode=value), self.assertRaisesRegex(ValueError, 'target_not_qualified'):
                self.admit()

    def test_binary_identity_or_execution_scope_mismatch_refused(self):
        for name in ('original-policy', 'candidate-policy', 'original-odbc'):
            row = self.receipt['control_executions'][name]
            original = row['sha256']
            row['sha256'] = '1' * 64
            self.repin()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'binary_receipt_mismatch'):
                self.admit()
            row['sha256'] = original
        self.receipt['control_executions']['original-odbc']['executed'] = True
        self.repin()
        with self.assertRaisesRegex(ValueError, 'binary_receipt_mismatch'):
            self.admit()


if __name__ == '__main__':
    unittest.main()

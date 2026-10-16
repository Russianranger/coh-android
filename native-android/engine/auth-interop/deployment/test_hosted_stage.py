"""Fail-closed staging boundary tests; no SQL instance or network is used."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

import checksum_candidate
import generate_odbc
import hosted_auth_stage as stage

ROOT = Path(__file__).resolve().parents[4]
COMMIT = '1' * 40


class HostedStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.output = self.base / 'new-output'
        self.env = {'RUNNER_ENVIRONMENT': 'github-hosted', 'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Windows', 'RUNNER_TEMP': str(self.base)}

    def inspect(self, commit=COMMIT, tree=stage.ORIGINAL_TREE, status=''):
        return patch.object(stage, 'capture', side_effect=[commit, tree, status, '2' * 40])

    def test_non_hosted_and_non_windows_refused_before_inspection(self):
        variants = [('posix', self.env), ('nt', {}), ('nt', dict(self.env, RUNNER_ENVIRONMENT='self-hosted')),
                    ('nt', dict(self.env, GITHUB_ACTIONS='false')), ('nt', dict(self.env, RUNNER_OS='Linux'))]
        for system, env in variants:
            with self.subTest(system=system, env=env), patch.object(stage, 'capture') as command:
                with self.assertRaisesRegex(ValueError, 'fresh_github_hosted_windows_required'):
                    stage.require_hosted(ROOT, self.output, COMMIT, env, system)
                command.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_output_must_be_new_and_inside_runner_temp(self):
        self.output.mkdir()
        for output in (self.output, self.base, self.base.parent / 'elsewhere'):
            with self.subTest(output=output), patch.object(stage, 'capture') as command:
                with self.assertRaisesRegex(ValueError, 'new_output_directory_under_runner_temp_required'):
                    stage.require_hosted(ROOT, output, COMMIT, self.env, 'nt')
                command.assert_not_called()

    def test_exact_commit_and_original_tree_required(self):
        for commit, tree in [('3' * 40, stage.ORIGINAL_TREE), (COMMIT, '4' * 40)]:
            with self.inspect(commit, tree), patch.object(stage, 'pinned_sources') as pins:
                with self.assertRaisesRegex(ValueError, 'source_identity_mismatch'):
                    stage.require_hosted(ROOT, self.output, COMMIT, self.env, 'nt')
                pins.assert_not_called()

    def test_dirty_source_refused(self):
        with self.inspect(status=' M upstream/ouroboros/AuthServer/src/Account.cpp'), patch.object(stage, 'pinned_sources') as pins:
            with self.assertRaisesRegex(ValueError, 'tracked_source_inputs_modified'):
                stage.require_hosted(ROOT, self.output, COMMIT, self.env, 'nt')
            pins.assert_not_called()

    def test_clean_identity_requires_pinned_sources(self):
        with self.inspect(), patch.object(stage, 'pinned_sources') as pins:
            result = stage.require_hosted(ROOT, self.output, COMMIT, self.env, 'nt')
            pins.assert_called_once_with(ROOT)
            self.assertEqual(result['original_source_tree'], stage.ORIGINAL_TREE)
            self.assertFalse(self.output.exists())

    def pe(self, machine=0x14c, kind=0x10b, subsystem=2):
        data = bytearray(160)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 60, 64)
        data[64:68] = b'PE\0\0'
        struct.pack_into('<H', data, 68, machine)
        struct.pack_into('<H', data, 88, kind)
        struct.pack_into('<H', data, 156, subsystem)
        path = self.base / 'fixture.exe'
        path.write_bytes(data)
        return path

    def test_pe_header_does_not_claim_loadable_or_executed(self):
        record = stage.pe_identity(self.pe(), 2)
        self.assertTrue(record['header_identity_only'])
        self.assertFalse(record['executed'])
        for values in [dict(machine=0x8664), dict(kind=0x20b), dict(subsystem=3)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                stage.pe_identity(self.pe(**values), 2)

    def test_truncated_or_oversized_header_offset_refused(self):
        path = self.pe()
        path.write_bytes(path.read_bytes()[:100])
        with self.assertRaises(ValueError):
            stage.pe_identity(path, 2)
        data = bytearray(self.pe().read_bytes())
        struct.pack_into('<I', data, 60, 2**31)
        path.write_bytes(data)
        with self.assertRaises(ValueError):
            stage.pe_identity(path, 2)

    def test_generated_controls_keep_scopes_distinct(self):
        checksum = checksum_candidate.prepare(ROOT, self.base)
        odbc = generate_odbc.prepare(ROOT, self.base)
        self.assertFalse(checksum['upstream_worktree_modified'])
        self.assertFalse(checksum['patched_dbserver_built'])
        self.assertFalse(odbc['authserver_started'])
        self.assertFalse(odbc['real_account_login_verified'])
        self.assertEqual(len(odbc['original_function_sha256']), 6)
        candidate = (self.base / 'checksum-failclosed.patch').read_text()
        self.assertIn('+    if (ignore_checksum)', candidate)
        self.assertIn('+        return 1;', candidate)
        self.assertIn('sizeof(correct_game_checksum)', candidate)
        source = (self.base / 'original-odbc.cpp').read_text()
        self.assertIn('SQL_C_TINYINT, SQL_TINYINT', source)
        self.assertIn('SQL_C_TYPE_TIMESTAMP', source)
        self.assertIn('missing_stats_rejected', source)
        self.assertIn('sizeof(void*)==4', source)
        self.assertNotIn('CheckPassword(', source)

    def test_fast_completed_child_cannot_bypass_log_limit(self):
        process = Mock(returncode=0)
        process.poll.return_value = 0
        def completed(*args, **kwargs):
            kwargs['stdout'].write(b'x' * 65)
            kwargs['stdout'].flush()
            return process
        commands = stage.Commands(self.base)
        with patch.object(stage, 'LOG_LIMIT', 64), patch.object(stage.subprocess, 'Popen', side_effect=completed):
            with self.assertRaisesRegex(ValueError, 'completed_command_log_limit'):
                commands.run('fast', ['test-only'])
        self.assertEqual(commands.records[0]['log_original_bytes'], 65)
        self.assertEqual(commands.records[0]['log_bytes'], 64)
        self.assertTrue(commands.records[0]['log_truncated'])
        self.assertEqual((self.base / 'fast.log').stat().st_size, 64)

    def test_taskkill_error_still_waits_and_records_observed_child_exit(self):
        process = Mock(returncode=None, pid=100)
        process.poll.return_value = None
        def waited(**kwargs):
            process.returncode = -9
            process.poll.return_value = -9
            return -9
        process.wait.side_effect = waited
        commands = stage.Commands(self.base)
        with patch.object(stage.subprocess, 'Popen', return_value=process), \
             patch.object(stage.subprocess, 'run', side_effect=OSError), \
             patch.object(stage.time, 'monotonic', side_effect=[0, 2, 3]):
            with self.assertRaisesRegex(ValueError, 'command_timeout_or_log_limit'):
                commands.run('timeout', ['test-only'], timeout=1)
        process.wait.assert_called_once_with(timeout=15)
        self.assertEqual(commands.records[0]['termination'], {'attempted': True, 'observed': True, 'taskkill_error': 'OSError'})

    def test_failed_termination_never_claims_exit(self):
        process = Mock(returncode=None, pid=100)
        process.poll.return_value = None
        process.wait.side_effect = OSError
        process.kill.side_effect = OSError
        commands = stage.Commands(self.base)
        with patch.object(stage.subprocess, 'Popen', return_value=process), \
             patch.object(stage.subprocess, 'run', side_effect=OSError), \
             patch.object(stage.time, 'monotonic', side_effect=[0, 2, 3]):
            with self.assertRaisesRegex(ValueError, 'command_timeout_or_log_limit'):
                commands.run('not-stopped', ['test-only'], timeout=1)
        self.assertFalse(commands.records[0]['termination']['observed'])
        self.assertIsNone(commands.records[0]['returncode'])

    def test_partial_failure_cleanup_attempts_all_owned_operations(self):
        instance = 'cohauth-ci-' + 'a' * 24
        for fail_at in range(4):
            runner = Mock()
            count = 0
            def operation(*args, **kwargs):
                nonlocal count
                current = count
                count += 1
                if current == fail_at:
                    raise OSError
            runner.run.side_effect = operation
            self.assertEqual(stage.cleanup_owned_instance(runner, 'sqlcmd', 'localdb', instance), fail_at == 3)
            self.assertEqual([call.args[0] for call in runner.run.call_args_list],
                             ['localdb-drop-owned-schema', 'localdb-stop-owned-instance', 'localdb-delete-owned-instance'])
            self.assertEqual(runner.run.call_args_list[0].args[1][2], '(localdb)\\' + instance)
            self.assertEqual(runner.run.call_args_list[1].args[1][2], instance)
            self.assertEqual(runner.run.call_args_list[2].args[1][2], instance)
        runner = Mock()
        with self.assertRaisesRegex(ValueError, 'owned_instance_name_invalid'):
            stage.cleanup_owned_instance(runner, 'sqlcmd', 'localdb', 'MSSQLLocalDB')
        runner.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()

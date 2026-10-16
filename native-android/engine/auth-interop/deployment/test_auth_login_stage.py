"""Auth-only boundaries and negative receipt controls; no real service claims."""
import copy
import json
from pathlib import Path
import os
import struct
import tempfile
import unittest
from unittest.mock import patch

import auth_service_profile as profile
import hosted_auth_login as stage
import password_fixture

ROOT = Path(__file__).resolve().parents[4]


def fixture(case):
    good = case == 'valid'
    return {'schema': 'coh-auth-only-probe-v1', 'passed': True, 'case': case,
            'state': 5 if good else 12, 'protocol': 191021, 'shards': 0,
            'received_frames': 3 if good else 1, 'sent_bytes': 170,
            'failure_command': 1 if case in ('wrong-password', 'missing-account') else 0,
            'failure_reason': 3 if case == 'wrong-password' else 2 if case == 'missing-account' else 0,
            'system_error': 104 if case == 'corrupt-frame' else 0, 'elapsed_ms': 500,
            'socket_cleanup_complete': True, 'password_retained_after_close': False,
            'db_handoff_attempted': False, 'real_server_provenance_verified_by_probe': False,
            'openssl_runtime': 'OpenSSL 3.5.9 29 Sep 2026'}


class AuthLoginStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def test_all_four_exact_receipts_have_narrow_scope(self):
        for case in stage.CASES:
            with self.subTest(case=case):
                self.assertEqual(stage.admit_probe_result(fixture(case), case), fixture(case))

    def test_every_missing_and_extra_receipt_field_refused(self):
        for case in stage.CASES:
            for key in fixture(case):
                value = fixture(case)
                del value[key]
                with self.subTest(case=case, key=key), self.assertRaises(ValueError):
                    stage.admit_probe_result(value, case)
            value = fixture(case)
            value['credential'] = 'forbidden'
            with self.assertRaises(ValueError):
                stage.admit_probe_result(value, case)

    def test_typed_fields_cannot_claim_with_booleans(self):
        for key, value in fixture('valid').items():
            if type(value) is int:
                changed = fixture('valid')
                changed[key] = True
                with self.subTest(key=key), self.assertRaises(ValueError):
                    stage.admit_probe_result(changed, 'valid')

    def test_false_success_credential_retention_or_handoff_refused(self):
        for key, value in [('passed', False), ('socket_cleanup_complete', False),
                           ('password_retained_after_close', True), ('db_handoff_attempted', True),
                           ('real_server_provenance_verified_by_probe', True), ('protocol', 190516),
                           ('shards', 1), ('elapsed_ms', 20001), ('elapsed_ms', -1), ('sent_bytes', 0),
                           ('sent_bytes', 4097), ('openssl_runtime', 'OpenSSL 3.5.8 1 Jan 2026'),
                           ('openssl_runtime', 'OpenSSL 3.5.9 private_key=secret')]:
            result = fixture('valid')
            result[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                stage.admit_probe_result(result, 'valid')

    def test_positive_needs_three_frames_and_shards_ready(self):
        for key, value in [('received_frames', 2), ('state', 12), ('failure_command', 1),
                           ('failure_reason', 2), ('system_error', 104)]:
            result = fixture('valid')
            result[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                stage.admit_probe_result(result, 'valid')

    def test_each_negative_requires_source_failure(self):
        for case in ('wrong-password', 'missing-account', 'corrupt-frame'):
            for key, value in [('state', 5), ('received_frames', 3), ('failure_command', 3)]:
                result = fixture(case)
                result[key] = value
                with self.subTest(case=case, key=key), self.assertRaises(ValueError):
                    stage.admit_probe_result(result, case)
        for case in ('wrong-password', 'missing-account'):
            result = fixture(case)
            result['failure_reason'] = 99
            with self.assertRaises(ValueError):
                stage.admit_probe_result(result, case)

    def test_state_constants_still_match_original_native_header(self):
        value = (ROOT / 'native-android/engine/login/coh_login.h').read_text()
        import re
        enum = re.search(r'typedef enum \{([^}]+)\} CohLoginState;', value).group(1)
        values = [token.strip() for token in enum.split(',')]
        self.assertEqual(values.index('COH_LOGIN_SHARDS_READY'), 5)
        self.assertEqual(values.index('COH_LOGIN_FAILED'), 12)

    def test_config_explicit_encryption_normal_payment_and_no_debug(self):
        text = profile.configuration('cohauth-ci-' + 'a' * 24, 'ODBC Driver 17 for SQL Server', [21000, 21001, 21002], 'C:\\private\\log')
        for line in ('Encrypt = true;', 'DesApply = true;', 'ProtocolVersion = 191021;',
                     'FreeServer = false;', 'PayStatOverride = -1;', 'useQueue = false;',
                     'DumpPacket = false;', 'enableVerboseLogging = false;', 'enableDebugLogging = false;',
                     'allowUnknownServers = false;', 'DBConnectionNum = 2;'):
            self.assertIn(line, text)
        self.assertNotIn(password_fixture.ACCOUNT, text)
        self.assertNotIn(password_fixture.PASSWORD, text)
        self.assertNotIn('UseFakeAuth', text)

    def test_config_rejects_remote_instances_ports_driver_and_injection(self):
        good = ['cohauth-ci-' + 'a' * 24, 'ODBC Driver 17 for SQL Server', [21000, 21001, 21002], 'C:\\private\\log']
        for index, bad in [(0, 'production'), (0, 'cohauth-ci-' + 'a' * 24 + ';danger'),
                           (1, 'ODBC Driver 18 for SQL Server'), (2, [1, 2, 3]), (2, [21000]*3),
                           (2, [True, 21000, 21001]), (2, [21000, 21001]), (2, [21000, 21001, 60000]),
                           (3, 'a"; Encrypt = false;'), (3, 'line\nfeed'), (3, 'x' * 241), (3, '')]:
            values = copy.deepcopy(good)
            values[index] = bad
            with self.subTest(index=index, bad=bad), self.assertRaises(ValueError):
                profile.configuration(*values)

    def test_account_seed_does_not_register_shards_or_override_policy(self):
        sql = profile.account_sql()
        self.assertIn('auth-only server table must remain empty', sql)
        self.assertNotIn('INSERT INTO dbo.server', sql)
        self.assertNotIn(password_fixture.PASSWORD, sql)
        self.assertNotIn('UPDATE ', sql)

    def test_build_script_refuses_shell_and_expansion_tokens(self):
        path = self.base / 'command.cmd'
        stage.command_script(path, Path('C:/VS/vcvarsall.bat'), ['nmake', '/nologo', 'build_libs'])
        self.assertIn(' x64 >nul', path.read_text())
        for bad in ('x&whoami', 'x\ny', '%PATH%', '!name!', 'x|y', 'x>y', 'x"y'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                stage.command_script(path, Path('C:/VS/vcvarsall.bat'), ['nmake', bad])

    def test_native_windows_perl_required_for_msvc_openssl(self):
        msys, native = self.base/'msys-perl.exe', self.base/'native-perl.exe'
        msys.write_bytes(b'fixture')
        native.write_bytes(b'fixture')
        with patch.object(stage.prior, 'capture', side_effect=['msys', 'MSWin32']):
            self.assertEqual(stage.select_native_perl([msys,native]), native)
        with patch.object(stage.prior, 'capture', return_value='cygwin'):
            with self.assertRaisesRegex(ValueError, '^native_windows_perl_required$'):
                stage.select_native_perl([None,self.base/'absent',msys,native])

    def test_generated_project_uses_unchanged_controller_and_only_isolated_adapter(self):
        project = self.base / 'project'
        inputs = stage.prepare_probe_project(ROOT, project, self.base / 'openssl')
        cmake = (project / 'CMakeLists.txt').read_text()
        self.assertIn('wrapped_login.c', cmake)
        self.assertIn('libcrypto.lib', cmake)
        self.assertIn('ws2_32', cmake)
        self.assertIn('gdi32', cmake)  # Pinned OpenSSL VC-noCE-common ex_libs.
        self.assertTrue(all(path.is_file() for path in inputs))
        self.assertNotIn('DbServer', cmake)
        self.assertNotIn('MapServer', cmake)
        self.assertNotIn(password_fixture.PASSWORD, cmake)

    def test_probe_pe64_identity_is_header_only(self):
        path = self.base / 'probe.exe'
        data = bytearray(160)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 60, 64)
        data[64:68] = b'PE\0\0'
        struct.pack_into('<H', data, 68, 0x8664)
        struct.pack_into('<H', data, 88, 0x20b)
        struct.pack_into('<H', data, 156, 3)
        path.write_bytes(data)
        self.assertTrue(stage.probe_identity(path)['header_identity_only'])
        for offset, wrong in ((68, 0x14c), (88, 0x10b), (156, 2)):
            changed = bytearray(data)
            struct.pack_into('<H', changed, offset, wrong)
            path.write_bytes(changed)
            with self.assertRaises(ValueError):
                stage.probe_identity(path)
        path.write_bytes(data[:100])
        with self.assertRaises(ValueError):
            stage.probe_identity(path)

    def test_listener_inventory_preserves_empty_single_many(self):
        for raw, expected in [('[]', set()), ('[21000]', {21000}), ('[21000,21001,21002]', {21000,21001,21002})]:
            self.assertEqual(stage.decode_listener_ports(raw), expected)
        for bad in ('[null]', 'null', '21000', '{}', '[true]', '["21000"]', '[0]', '[65536]', '[' + ','.join(['1']*17) + ']'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                stage.decode_listener_ports(bad)

    def test_actual_listener_command_projects_existing_objects(self):
        with patch.object(stage.prior, 'capture', return_value='[]') as capture:
            self.assertEqual(stage.inspect_listeners(1234), set())
            command = capture.call_args.args[0][-1]
            self.assertIn('Where-Object OwningProcess -eq 1234 | ForEach-Object { [int]$_.LocalPort }', command)
            self.assertNotIn(').LocalPort', command)

    def test_powershell_projection_control_admits_only_exact_serializations(self):
        value = {'old_empty':'[null]', 'empty':'[]', 'one':'[21000]', 'many':'[21000,21001,21002]'}
        with patch.object(stage.prior, 'capture', return_value=json.dumps(value)) as capture:
            result = stage.qualify_listener_projection()
            self.assertTrue(result['passed'])
            self.assertFalse(result['real_service_started_by_control'])
            self.assertEqual(capture.call_args.args[0][0], 'pwsh')
        for key, wrong in [('empty','[null]'), ('one','[]'), ('many','[21000,21001]'), ('old_empty','null')]:
            changed = dict(value, **{key:wrong})
            with patch.object(stage.prior, 'capture', return_value=json.dumps(changed)):
                with self.assertRaises(ValueError):
                    stage.qualify_listener_projection()

    def test_reuse_source_closure_includes_headers_and_generated_policy(self):
        pins = json.loads((stage.HERE / 'probe-build-reuse-pins.json').read_text())
        actual = stage.admit_probe_source(ROOT, pins)
        self.assertEqual(actual, pins['generated_inputs'])
        prefix = 'native-android/engine/auth-interop/deployment/'
        required = ['windows/winsock_compat.h', 'windows/compat/arpa/inet.h', 'windows/compat/sys/socket.h',
                    'windows/compat/fcntl.h', 'windows/compat/poll.h', 'windows/compat/unistd.h',
                    'windows/wrapped_login.c', 'auth_service_profile.py', 'password_fixture.py']
        self.assertTrue(all(prefix+name in pins['source_files_sha256'] for name in required))
        self.assertIn('native-android/engine/login/coh_login.c', pins['source_files_sha256'])
        self.assertIn('native-android/engine/login/coh_login.h', pins['source_files_sha256'])
        self.assertIn('native-android/include/coh_native_core.h', pins['source_files_sha256'])
        self.assertEqual(actual['build_policy']['openssl_configuration'], ['VC-WIN64A','no-shared','no-asm','no-tests','no-module'])

    def test_reuse_rejects_transitive_header_change(self):
        pins = json.loads((stage.HERE / 'probe-build-reuse-pins.json').read_text())
        import shutil
        for name in pins['source_files_sha256']:
            destination = self.base / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        for name in ('native-android/engine/auth-interop/deployment/windows/compat/sys/socket.h',
                     'native-android/engine/login/coh_login.h'):
            path = self.base / name
            original = path.read_bytes()
            path.write_bytes(original+b'\n/* changed */\n')
            with self.assertRaisesRegex(ValueError, '^reused_probe_source_identity_mismatch$'):
                stage.admit_probe_source(self.base, pins)
            path.write_bytes(original)

    def test_reuse_rejects_fixture_generator_and_compile_policy_change(self):
        pins = json.loads((stage.HERE / 'probe-build-reuse-pins.json').read_text())
        for target, name, value in ((stage.profile,'fixture_header','different header'),
                                    (stage.inspect,'getsource','different project function')):
            with patch.object(target, name, return_value=value):
                with self.assertRaisesRegex(ValueError, '^reused_probe_generated_input_mismatch$'):
                    stage.admit_probe_source(ROOT, pins)
        with patch.dict(stage.PROBE_BUILD_POLICY, {'architecture':'ARM64'}):
            with self.assertRaisesRegex(ValueError, '^reused_probe_generated_input_mismatch$'):
                stage.admit_probe_source(ROOT, pins)

    def test_private_sql_command_discards_all_output(self):
        with patch.object(stage.subprocess, 'run') as run:
            run.return_value.returncode = 0
            stage.private_command(['sqlcmd', '-i', 'credential.sql'])
            self.assertEqual(run.call_args.kwargs['stdout'], stage.subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs['stderr'], stage.subprocess.DEVNULL)
            run.return_value.returncode = 1
            with self.assertRaisesRegex(ValueError, '^private_fixture_command_failed$'):
                stage.private_command(['sqlcmd', '-i', 'credential.sql'])

    def test_private_log_growth_refused_without_reading_contents(self):
        (self.base / 'private.log').write_bytes(b'private account data')
        self.assertEqual(stage.private_logs_bounded(self.base), 20)
        with (self.base / 'large.log').open('wb') as stream:
            stream.truncate(16 * 1024 * 1024)
        with self.assertRaisesRegex(ValueError, '^private_authserver_log_limit$'):
            stage.private_logs_bounded(self.base)

    def test_firewall_cleanup_requires_exact_owned_program(self):
        from unittest.mock import Mock
        runner = Mock()
        stage.firewall_rule(runner, 'cohauth-ci-' + 'a'*24, Path('C:/private/AuthServer.exe'), False)
        script = runner.run.call_args.args[1][-1]
        self.assertIn('rule ownership mismatch', script)
        self.assertIn('Get-NetFirewallApplicationFilter', script)
        self.assertIn('C:/private/AuthServer.exe', script)
        self.assertNotIn('Set-NetFirewallProfile', script)
        for name, binary in [('production', Path('C:/private/AuthServer.exe')), ('cohauth-ci-'+'a'*24, None),
                              ('cohauth-ci-'+'a'*24, Path("C:/bad'path/AuthServer.exe"))]:
            with self.assertRaises(ValueError):
                stage.firewall_rule(runner, name, binary, False)

    def test_real_prior_odbc_receipt_retained_without_reexecution(self):
        # Repository evidence contains the exact ten admitted files; no PE or SQL
        # invocation is needed to preserve this successful independent checkpoint.
        path = ROOT / 'native-android/engine/auth-interop/evidence/hosted-odbc-38948147656'
        with patch.object(stage.subprocess, 'run') as run:
            result = stage.admit_odbc_receipt(path)
            run.assert_not_called()
        self.assertEqual(result['run_id'], 38948147656)
        self.assertFalse(result['sql_only_controls_repeated'])
        self.assertFalse(result['previous_real_login_inherited'])

    def test_tampered_odbc_receipts_fail(self):
        import shutil
        path = self.base / 'prior'
        shutil.copytree(ROOT / 'native-android/engine/auth-interop/evidence/hosted-odbc-38948147656', path)
        receipt = path / 'receipt.json'
        original = receipt.read_bytes()
        receipt.write_bytes(original.replace(b'"passed": true', b'"passed":false', 1))
        with self.assertRaises(ValueError):
            stage.admit_odbc_receipt(path)
        receipt.write_bytes(original)
        (path / 'original-odbc.log').unlink()
        with self.assertRaises(ValueError):
            stage.admit_odbc_receipt(path)

    def test_known_openssl_fixture_admission_is_exact(self):
        archive = self.base / 'openssl.tar.gz'
        archive.write_bytes(b'not the qualified source')
        with self.assertRaises(ValueError):
            stage.admit_openssl(archive)


if __name__ == '__main__':
    unittest.main()

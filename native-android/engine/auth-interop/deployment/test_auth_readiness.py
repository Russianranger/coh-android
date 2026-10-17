"""Receipt and subprocess boundaries; does not execute Windows or ODBC."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import auth_readiness as readiness


def fixture():
    return {'schema': 'coh-auth-x86-odbc-readiness-v1', 'pointer_bytes': 4,
            'attempted_connections': 3, 'opened_connections': 3,
            'query_succeeded': True, 'sql_process_id': 123, 'connections_closed': True,
            'diagnostic_completed': True, 'errors': []}


class ReadinessTests(unittest.TestCase):
    def test_exact_x86_pool_health_is_separate_from_auth(self):
        result = readiness.admit(fixture(), 123)
        self.assertTrue(result['healthy'])
        self.assertFalse(result['authserver_internal_pool_observed'])
        self.assertFalse(result['encrypted_account_login_verified'])
        self.assertFalse(readiness.admit(fixture(), 124)['healthy'])

    def test_every_field_required_and_unknown_fields_refused(self):
        for key in fixture():
            value = fixture(); del value[key]
            with self.assertRaises(ValueError): readiness.admit(value, 123)
        value = fixture(); value['raw_log'] = 'private'
        with self.assertRaises(ValueError): readiness.admit(value, 123)

    def test_numeric_and_boolean_types_and_limits(self):
        for key, value in fixture().items():
            if type(value) is int:
                changed = fixture(); changed[key] = True
                with self.assertRaises(ValueError): readiness.admit(changed, 123)
            elif type(value) is bool:
                changed = fixture(); changed[key] = 1
                with self.assertRaises(ValueError): readiness.admit(changed, 123)
        for key, value in [('pointer_bytes', 8), ('attempted_connections', 4),
                           ('opened_connections', -1), ('sql_process_id', 2**32)]:
            changed = fixture(); changed[key] = value
            with self.assertRaises(ValueError): readiness.admit(changed, 123)
        for value in [0, True, 2**32]:
            with self.assertRaises(ValueError): readiness.admit(fixture(), value)

    def test_failed_or_partial_pool_is_not_healthy(self):
        for key, value in [('opened_connections', 2), ('query_succeeded', False),
                           ('connections_closed', False), ('diagnostic_completed', False)]:
            changed = fixture(); changed[key] = value
            self.assertFalse(readiness.admit(changed, 123)['healthy'])
        changed = fixture(); changed['attempted_connections'] = 1; changed['opened_connections'] = 0
        changed['errors'] = [{'sqlstate': '08001', 'native_error': -1}]
        self.assertFalse(readiness.admit(changed, 123)['healthy'])

    def test_diagnostics_never_accept_message_or_account_text(self):
        for errors in [[{'sqlstate': '08001', 'native_error': 1, 'message': 'private'}],
                       [{'sqlstate': 'private', 'native_error': 1}],
                       [{'sqlstate': '08001', 'native_error': True}],
                       [{'sqlstate': '08001', 'native_error': 2**31}],
                       [{'sqlstate': '08001', 'native_error': 1}] * 17, None]:
            value = fixture(); value['errors'] = errors
            with self.assertRaises(ValueError): readiness.admit(value, 123)

    def test_script_fixed_owned_instance_driver_and_read_only_query(self):
        program = readiness.script('cohauth-ci-' + 'a' * 24)
        self.assertIn('[IntPtr]::Size -ne 4', program)
        self.assertIn('ODBC Driver 17 for SQL Server', program)
        self.assertIn('$i -lt 3', program)
        self.assertIn("SERVERPROPERTY('ProcessID')", program)
        self.assertNotIn('Exception.Message', program)
        self.assertNotIn('user_auth', program)
        self.assertIn('$connection.Close();$connection.Dispose()', program)
        for instance in ['remote', 'cohauth-ci-' + 'a' * 24 + "';arbitrary", None]:
            with self.assertRaises(ValueError): readiness.script(instance)

    def test_bounded_child_output_and_timeout_never_exports_stderr(self):
        with tempfile.TemporaryDirectory() as temp:
            shell = Path(temp) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
            shell.parent.mkdir(parents=True); shell.write_bytes(b'fixture-not-executed')
            path_type = type(shell)
            with patch.object(readiness.os, 'name', 'nt'), patch.object(readiness, 'Path', path_type), \
                 patch.dict(readiness.os.environ, {'WINDIR': temp}), \
                 patch.object(readiness.subprocess, 'run') as run:
                run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps(fixture()).encode())
                self.assertTrue(readiness.observe('cohauth-ci-'+'a'*24, 123)['healthy'])
                self.assertEqual(run.call_args.kwargs['timeout'], 50)
                for returned in [SimpleNamespace(returncode=1, stdout=b'private', stderr=b'private'),
                                 SimpleNamespace(returncode=0, stdout=b'x'*8193)]:
                    run.return_value = returned
                    with self.assertRaisesRegex(ValueError, '^x86_sql_readiness_child_failed$'):
                        readiness.observe('cohauth-ci-'+'a'*24, 123)


if __name__ == '__main__':
    unittest.main()

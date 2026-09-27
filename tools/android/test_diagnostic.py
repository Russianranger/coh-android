"""Portable diagnostic gates and process cleanup; no PostgreSQL/Wine needed."""
import importlib.util
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('coh_android_diagnostic', ROOT / 'android/guest/diagnostic.py')
diagnostic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diagnostic
SPEC.loader.exec_module(diagnostic)


ODBC_HEADER = 'psqlODBC 16.00.0000; pointer bits 32; SQLWCHAR bytes 2'
ODBC_MARKERS = (
    'PASS all 65 stock DbServer ODBC connections coexist',
    'PASS indexes: duplicate field names, idempotence, schema isolation, legacy cleanup',
    'PASS foreign keys: absent table/constraint removal, add/remove, child rows, orphan rejection',
    'PASS SQLColumns: canonical PostgreSQL types, Unicode varchar, text and bytea',
    'PASS bound values: integer limits, byte 255, float, UTF-16, timestamp, 32 KiB bytea chunks, long text and NULL',
    'PASS atomic schema rebuild: row data, deleted-highest ID, foreign keys, indexes, conversion/dependency rollback, ASCII name keys',
    'PASS ID ordering, deleted highest ID, rollback and bulk-import startup state',
    'PASS column migration and connection reopen',
)
VERIFY_MARKER = 'PASS persisted fixture after reconnect/restart/restore'
RUNTIME_MARKER = 'COH_RUNTIME_PROBE_V1 PASS bits=32 dll=verified'


class DiagnosticAcceptanceTests(unittest.TestCase):
    def test_runtime_requires_exact_positive_architecture_and_dll_evidence(self):
        self.assertIsInstance(diagnostic.validate_runtime_probe(RUNTIME_MARKER + '\r\n'), dict)
        for text in ('', 'PASS\n', RUNTIME_MARKER.replace('32', '64'),
                     RUNTIME_MARKER.replace('verified', 'missing'),
                     'prefix ' + RUNTIME_MARKER, RUNTIME_MARKER + ' trailing'):
            with self.subTest(output=text), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_runtime_probe(text)

    def test_odbc_requires_real_32_bit_header_and_every_source_marker(self):
        output = '\n'.join((ODBC_HEADER,) + ODBC_MARKERS) + '\n'
        self.assertIsInstance(diagnostic.validate_probe(output), dict)
        for marker in ODBC_MARKERS:
            with self.subTest(missing=marker), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_probe(output.replace(marker + '\n', ''))
        for header in ('', ODBC_HEADER.replace('bits 32', 'bits 64'),
                       ODBC_HEADER.replace('bytes 2', 'bytes 4')):
            with self.subTest(header=header), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_probe(output.replace(ODBC_HEADER, header))

    def test_reconnect_gate_cannot_pass_from_initial_creation_output(self):
        initial = '\n'.join((ODBC_HEADER,) + ODBC_MARKERS) + '\n'
        persisted = ODBC_HEADER + '\n' + VERIFY_MARKER + '\n'
        self.assertIsInstance(diagnostic.validate_probe(persisted, verify=True), dict)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.validate_probe(initial, verify=True)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.validate_probe(persisted)

    def test_explicit_secrets_are_removed_without_erasing_useful_diagnostics(self):
        secrets = ['private-db-password', 'private-db-password-longer', 'private-auth-token']
        text = ('ODBC connection refused; password=private-db-password-longer; '
                'PWD=private-db-password; auth private-auth-token; pointer bits 32')
        redacted = diagnostic.redact(text, secrets)
        for secret in secrets:
            self.assertNotIn(secret, redacted)
        self.assertNotIn('longer', redacted, 'An overlapping short secret must not expose the longer secret suffix')
        self.assertIn('ODBC connection refused', redacted)
        self.assertIn('pointer bits 32', redacted)
        self.assertEqual(diagnostic.redact('No credentials here', []), 'No credentials here')


class OdbcDriverAcceptanceTests(unittest.TestCase):
    DRIVER_PATH = r'C:\Program Files (x86)\psqlODBC\1700\bin\psqlodbc35w.dll'

    def driver_output(self, name='PostgreSQL Unicode', path=None):
        return '\n'.join(('COH_ODBC_DRIVER_V1 NAME ' + name,
                          'COH_ODBC_DRIVER_V1 DLL ' + (self.DRIVER_PATH if path is None else path),
                          'COH_ODBC_DRIVER_V1 PASS bits=32')) + '\n'

    def test_registered_unicode_driver_evidence_accepts_both_names_and_registry_diagnostics(self):
        for name in ('PostgreSQL Unicode', 'PostgreSQL Unicode(x86)'):
            with self.subTest(name=name):
                output = ('COH_ODBC_DRIVER_V1 REG view=32 status=0\n' + self.driver_output(name)).replace('\n', '\r\n')
                result = diagnostic.validate_odbc_driver(output)
                self.assertEqual(result['driver_name'], name)
                self.assertEqual(result['driver_path'], self.DRIVER_PATH)
                self.assertEqual(result['pointer_bits'], 32)
                self.assertEqual(result['registry_view'], 32)
                self.assertIs(result['driver_dll_loaded'], True)

    def test_driver_probe_requires_one_of_each_marker(self):
        output = self.driver_output()
        for line in output.splitlines():
            with self.subTest(missing=line), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_odbc_driver(output.replace(line + '\n', ''))
            with self.subTest(duplicated=line), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_odbc_driver(output + line + '\n')

    def test_driver_probe_rejects_wrong_architecture_malformed_pass_and_failure_output(self):
        output = self.driver_output()
        invalid = (output.replace('PASS bits=32', 'PASS bits=64'),
                   output.replace('PASS bits=32', 'PASS bits=32 trailing'),
                   output.replace('COH_ODBC_DRIVER_V1 DLL ', 'COH_ODBC_DRIVER_V1 DLL'),
                   output + 'FAIL driver DLL export is missing\n',
                   output + 'COH_ODBC_DRIVER_V1 FAIL win32=126\n')
        for text in invalid:
            with self.subTest(output=text), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_odbc_driver(text)

    def test_driver_name_injection_and_nonabsolute_windows_dll_paths_are_refused(self):
        for name in ('PostgreSQL ANSI', 'PostgreSQL Unicode};Password=injected',
                     'PostgreSQL Unicode;Servername=elsewhere', ''):
            with self.subTest(name=name), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_odbc_driver(self.driver_output(name))
        for path in ('psqlodbc35w.dll', r'C:relative\psqlodbc35w.dll', '/usr/lib/psqlodbc35w.dll', ''):
            with self.subTest(path=path), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_odbc_driver(self.driver_output(path=path))


class OwnedWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / 'state'
        self.state.mkdir()

    def test_new_workspace_has_exact_ownership_marker_and_is_reusable(self):
        work = diagnostic.owned_workspace(self.state)
        self.assertEqual(work, self.state / 'diagnostic')
        marker = work / '.coh-diagnostic-owner.json'
        self.assertEqual(json.loads(marker.read_text()), {'format': 1, 'purpose': 'coh-android-diagnostic'})
        (work / 'prior-diagnostic.log').write_text('existing owned output')
        self.assertEqual(diagnostic.owned_workspace(self.state), work)

    def test_foreign_nonempty_directory_is_refused_without_touching_contents(self):
        work = self.state / 'diagnostic'
        work.mkdir()
        sentinel = work / 'unrelated-save.dat'
        sentinel.write_bytes(b'user data must survive')
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.owned_workspace(self.state)
        self.assertEqual(sentinel.read_bytes(), b'user data must survive')
        self.assertEqual(list(work.iterdir()), [sentinel])

    def test_wrong_or_malformed_owner_is_refused_without_rewriting_marker(self):
        work = self.state / 'diagnostic'
        work.mkdir()
        marker = work / '.coh-diagnostic-owner.json'
        for value in ('malformed', json.dumps({'format': 1, 'purpose': 'another-app'}),
                      json.dumps({'format': 2, 'purpose': 'coh-android-diagnostic'})):
            marker.write_text(value)
            with self.subTest(marker=value), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.owned_workspace(self.state)
            self.assertEqual(marker.read_text(), value)

    @unittest.skipIf(os.name == 'nt', 'Guest ownership checks run in the Linux filesystem')
    def test_symlinked_workspace_cannot_claim_an_unrelated_directory(self):
        foreign = self.state.parent / 'foreign'
        foreign.mkdir()
        (self.state / 'diagnostic').symlink_to(foreign, target_is_directory=True)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.owned_workspace(self.state)
        self.assertEqual(list(foreign.iterdir()), [])


class DiagnosticProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / 'state'
        self.state.mkdir()
        self.context = diagnostic.Context(self.state, total_timeout=30)

    def run_python(self, label, source, **options):
        return self.context.run(label, [sys.executable, '-u', '-c', source], **options)

    def test_event_redaction_preserves_json_delimiters_quotes_and_newlines(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.context.event('log', message='first "quoted" line\nPWD=example')
        event = json.loads(stream.getvalue())
        self.assertEqual(event['type'], 'log')
        self.assertTrue(event['message'].startswith('first "quoted" line\nPWD='))
        self.assertNotIn('example', event['message'])

    def test_child_output_and_exit_are_real_and_nonzero_cannot_pass(self):
        result = self.run_python('success', 'print("observed child output")')
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('observed child output', result['output'])
        self.assertGreaterEqual(result['elapsed_seconds'], 0)
        with self.assertRaises(diagnostic.DiagnosticError):
            self.run_python('failure', 'import sys;print("not successful");sys.exit(7)')
        result = self.run_python('inspected-failure', 'import sys;sys.exit(7)', check=False)
        self.assertEqual(result['exit_code'], 7)

    def test_stop_request_cancels_before_starting_another_child(self):
        sentinel = self.state / 'must-not-start'
        (self.state / 'stop-request').touch()
        self.assertTrue(self.context.cancelled())
        with self.assertRaises(diagnostic.Cancelled):
            self.run_python('cancel-before-start', 'from pathlib import Path;Path(' + repr(str(sentinel)) + ').touch()')
        self.assertFalse(sentinel.exists())

    def test_cancelled_diagnostic_still_allows_explicit_cleanup_commands(self):
        (self.state / 'stop-request').touch()
        result = self.run_python('cleanup', 'print("cleanup completed")', cleanup=True)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('cleanup completed', result['output'])

    def test_process_failure_does_not_disclose_registered_credentials(self):
        secret = 'diagnostic-private-credential[.*]$value'
        self.context.secrets.append(secret)
        with self.assertRaises(diagnostic.DiagnosticError) as caught:
            self.run_python('secret-failure', f'import sys;print({secret!r});sys.exit(7)')
        self.assertNotIn(secret, str(caught.exception))

    @staticmethod
    def process_alive(pid):
        # kill(0) uses the caller's PID namespace. Some CI sandboxes expose a
        # host /proc mount, where /proc/<child namespace PID> is unrelated.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        if sys.platform.startswith('linux'):
            try:
                target_status = Path('/proc', str(pid), 'status').read_text()
                own_status = Path('/proc/self/status').read_text()
                def namespaces(status):
                    return next((line.split()[1:] for line in status.splitlines()
                                 if line.startswith('NSpid:')), [])
                target_ids, own_ids = namespaces(target_status), namespaces(own_status)
                if len(target_ids) != len(own_ids) or not target_ids or target_ids[-1] != str(pid):
                    return True
                # A terminated descendant can briefly remain a zombie until
                # the host init reaps it; it cannot run or write further data.
                return Path('/proc', str(pid), 'stat').read_text().split(') ', 1)[1][0] != 'Z'
            except FileNotFoundError:
                return True
        return True

    def assert_stopped(self, pid):
        deadline = time.monotonic() + 3
        while self.process_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertFalse(self.process_alive(pid), 'Diagnostic left a synthetic process alive')

    @unittest.skipIf(os.name == 'nt', 'Guest cancellation owns POSIX process groups')
    def test_timeout_terminates_parent_and_descendant_processes(self):
        identities = self.state / 'processes.json'
        source = ('import json,os,subprocess,sys,time\n'
                  'from pathlib import Path\n'
                  'child=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\n'
                  f'Path({str(identities)!r}).write_text(json.dumps([os.getpid(),child.pid]))\n'
                  'time.sleep(60)\n')
        started = time.monotonic()
        with self.assertRaises(diagnostic.DiagnosticError):
            self.run_python('timeout-tree', source, timeout=0.5)
        self.assertLess(time.monotonic() - started, 10)
        self.assertTrue(identities.is_file(), 'Synthetic process never started')
        for pid in json.loads(identities.read_text()):
            self.assert_stopped(pid)

    @unittest.skipIf(os.name == 'nt', 'Guest cancellation owns POSIX process groups')
    def test_timeout_kills_a_descendant_that_ignores_term_and_closes_capture_pipes(self):
        identities = self.state / 'stubborn-processes.json'
        ready = self.state / 'descendant-ready'
        descendant = ('import os,signal,time\nfrom pathlib import Path\n'
                      'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                      'os.close(1);os.close(2)\n'
                      f'Path({str(ready)!r}).touch()\n'
                      'time.sleep(60)\n')
        source = ('import json,os,subprocess,sys,time\nfrom pathlib import Path\n'
                  f'child=subprocess.Popen([sys.executable,"-c",{descendant!r}])\n'
                  f'Path({str(identities)!r}).write_text(json.dumps([os.getpid(),child.pid]))\n'
                  'time.sleep(60)\n')
        def fixture_cleanup():
            if identities.is_file():
                for pid in json.loads(identities.read_text()):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        self.addCleanup(fixture_cleanup)
        with self.assertRaises(diagnostic.DiagnosticError):
            self.run_python('timeout-stubborn-descendant', source, timeout=1)
        self.assertTrue(ready.is_file(), 'Descendant did not reach the intended signal/pipe state')
        for pid in json.loads(identities.read_text()):
            self.assert_stopped(pid)

    def test_background_readiness_line_is_visible_before_process_exit(self):
        child = self.context.start('background-ready',
                                   [sys.executable, '-u', '-c', 'import time;print("server ready");time.sleep(60)'])
        self.addCleanup(child.stop)
        deadline = time.monotonic() + 3
        while 'server ready' not in child.text() and time.monotonic() < deadline:
            self.assertIsNone(child.process.poll())
            time.sleep(0.02)
        self.assertIn('server ready\n', child.text())
        self.assertIsNone(child.process.poll(), 'Readiness must be consumed while the server is running')

    @unittest.skipIf(os.name == 'nt', 'Guest cancellation owns POSIX process groups')
    def test_cancellation_during_run_terminates_and_reaps_child(self):
        identity = self.state / 'running.pid'
        source = ('import os,time\nfrom pathlib import Path\n'
                  f'Path({str(identity)!r}).write_text(str(os.getpid()))\n'
                  'time.sleep(60)\n')
        worker_error = []
        def cancel_after_start():
            deadline = time.monotonic() + 5
            while not identity.is_file() and time.monotonic() < deadline:
                time.sleep(0.02)
            if not identity.is_file():
                worker_error.append('Synthetic process never started')
            (self.state / 'stop-request').touch()
        thread = threading.Thread(target=cancel_after_start, daemon=True)
        thread.start()
        try:
            with self.assertRaises(diagnostic.Cancelled):
                self.run_python('cancel-during-run', source, timeout=10)
        finally:
            thread.join(timeout=6)
        self.assertFalse(thread.is_alive())
        self.assertEqual(worker_error, [])
        self.assert_stopped(int(identity.read_text()))


@unittest.skipIf(os.name == 'nt', 'Wine prefix ownership proof uses POSIX byte locks and Unix sockets')
class WineStoppedProofTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.prefix = root / 'prefix'
        self.prefix.mkdir()
        self.server_base = root / 'servers'
        self.server_base.mkdir()
        identity = self.prefix.stat()
        self.server_dir = self.server_base / f'server-{identity.st_dev:x}-{identity.st_ino:x}'
        self.server_dir.mkdir()
        self.lock = self.server_dir / 'lock'
        self.lock.touch()

    def verify(self):
        return diagnostic.verify_wine_stopped(self.prefix, server_base=self.server_base)

    def assert_stopped_proof(self):
        proof = self.verify()
        self.assertIs(proof['prefix_lock_free'], True)
        self.assertIs(proof['server_socket_inactive'], True)

    def unix_socket(self):
        try:
            return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        except PermissionError:
            self.skipTest('Executor forbids Unix socket creation; real endpoint acceptance requires hosted Linux')

    def test_free_prefix_lock_and_absent_server_socket_prove_stopped(self):
        self.assert_stopped_proof()
        self.assertEqual(self.lock.read_bytes(), b'')
        self.assertFalse((self.server_dir / 'socket').exists())

    def test_lock_held_by_an_independent_process_is_not_stopped(self):
        ready = self.server_base / 'lock-held'
        source = ('import fcntl,sys,time\nfrom pathlib import Path\n'
                  'lock=open(sys.argv[1],"r+")\n'
                  'fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB,1,0)\n'
                  'Path(sys.argv[2]).touch()\n'
                  'time.sleep(60)\n')
        child = subprocess.Popen([sys.executable, '-u', '-c', source, str(self.lock), str(ready)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        def cleanup():
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            child.stderr.close()
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 5
        while not ready.exists():
            self.assertIsNone(child.poll(), 'Byte-lock fixture exited before acquiring its lock')
            self.assertLess(time.monotonic(), deadline, 'Byte-lock fixture failed to become ready')
            time.sleep(0.02)
        with self.assertRaises(diagnostic.DiagnosticError):
            self.verify()
        self.assertIsNone(child.poll(), 'Verifying ownership must not terminate the lock holder')

    def test_live_unix_server_socket_prevents_stopped_proof(self):
        with self.unix_socket() as endpoint:
            endpoint.bind(str(self.server_dir / 'socket'))
            endpoint.listen(1)
            with self.assertRaises(diagnostic.DiagnosticError):
                self.verify()
            self.assertTrue((self.server_dir / 'socket').exists())

    def test_stale_unix_socket_with_connection_refused_is_stopped(self):
        with self.unix_socket() as endpoint:
            endpoint.bind(str(self.server_dir / 'socket'))
        self.assertTrue((self.server_dir / 'socket').exists())
        self.assert_stopped_proof()

    def test_missing_or_symlinked_lock_cannot_supply_ownership_proof(self):
        self.lock.unlink()
        with self.assertRaises(diagnostic.DiagnosticError):
            self.verify()
        unrelated = self.server_base / 'unrelated.lock'
        unrelated.write_bytes(b'unrelated lock must not change')
        self.lock.symlink_to(unrelated)
        with self.assertRaises(diagnostic.DiagnosticError):
            self.verify()
        self.assertEqual(unrelated.read_bytes(), b'unrelated lock must not change')


if __name__ == '__main__':
    unittest.main()

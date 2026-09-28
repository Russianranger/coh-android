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
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


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

    def test_timeout_observer_sees_flushed_output_while_child_lives_then_evidence_is_redacted(self):
        secret = 'private-timeout-diagnostic-password'
        self.context.secrets.append(secret)
        observed = []
        def observe(child):
            observed.append({'pid': child.process.pid, 'exit_code': child.process.poll(),
                             'text': child.text()})
        stream = io.StringIO()
        with redirect_stdout(stream), self.assertRaisesRegex(diagnostic.DiagnosticError, 'observed-timeout timed out'):
            self.run_python('observed-timeout',
                            f'import time;print("CHECK line 42",flush=True);print({secret!r},flush=True);time.sleep(60)',
                            timeout=0.5, before_stop=observe)
        self.assertEqual(len(observed), 1)
        self.assertIsNone(observed[0]['exit_code'], 'Observer ran after the timed-out process was stopped')
        self.assertIn('CHECK line 42\n', observed[0]['text'])
        self.assert_stopped(observed[0]['pid'])
        records = [record for record in self.context.report['processes'] if record['label'] == 'observed-timeout']
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['forced_stop'])
        self.assertIn('CHECK line 42\n', records[0]['output'])
        self.assertNotIn(secret, json.dumps(self.context.report))
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertTrue(events)
        self.assertNotIn(secret, json.dumps(events))

    def test_timeout_survives_observer_exception_and_child_is_still_cleaned_up(self):
        secret = 'private-observation-failure-secret'
        self.context.secrets.append(secret)
        observed = []
        def failing_observer(child):
            observed.append((child.process.pid, child.process.poll()))
            raise RuntimeError('observer failed: ' + secret)
        stream = io.StringIO()
        with redirect_stdout(stream), self.assertRaisesRegex(diagnostic.DiagnosticError, 'observer-failed-timeout timed out'):
            self.run_python('observer-failed-timeout',
                            'import time;print("CHECK line 43",flush=True);time.sleep(60)',
                            timeout=0.5, before_stop=failing_observer)
        self.assertEqual(len(observed), 1)
        self.assertIsNone(observed[0][1])
        self.assert_stopped(observed[0][0])
        failures = self.context.report['observation_failures']
        self.assertEqual(len(failures), 1)
        self.assertIn('observer failed', str(failures[0]))
        self.assertNotIn(secret, json.dumps(self.context.report))
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertNotIn(secret, json.dumps(events))
        records = [record for record in self.context.report['processes']
                   if record['label'] == 'observer-failed-timeout']
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['forced_stop'])

    def test_successful_process_does_not_invoke_failure_observer(self):
        observed = []
        result = self.run_python('observed-success', 'print("completed")',
                                 before_stop=lambda child: observed.append(child.label))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(observed, [])

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

    def inherited_output_source(self, exit_code=0):
        """A real child retains stdout after its initializer exits."""
        ready = self.state / 'service-ready'
        identity = self.state / 'service.pid'
        service = ('import os,time\nfrom pathlib import Path\n'
                   f'Path({str(identity)!r}).write_text(str(os.getpid()))\n'
                   f'Path({str(ready)!r}).touch()\n'
                   'print("service ready",flush=True)\ntime.sleep(60)\n')
        def cleanup():
            for child in self.context.children:
                child.stop()
        self.addCleanup(cleanup)
        source = ('import subprocess,sys,time\nfrom pathlib import Path\n'
                  f'subprocess.Popen([sys.executable,"-u","-c",{service!r}])\n'
                  f'while not Path({str(ready)!r}).exists():time.sleep(.01)\n'
                  f'print("initializer finished",flush=True)\nsys.exit({exit_code})\n')
        return source, identity

    def test_wineboot_completion_leaves_service_owned_until_cleanup(self):
        source, identity = self.inherited_output_source()
        result = self.run_python('wineboot', source, timeout=3, allow_background_output=True)
        child = self.context.children[-1]
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['forced_stop'])
        self.assertTrue(result['completion']['output_capture_open'])
        self.assertEqual(result['completion']['leader_exit_code'], 0)
        self.assertIn('initializer finished', result['output'])
        self.assertTrue(self.process_alive(int(identity.read_text())))
        self.assertTrue(child.reader.is_alive())
        child.stop()
        self.context.record(child, refresh=True)
        self.assert_stopped(int(identity.read_text()))
        self.assertTrue(result['output_capture_closed'])
        self.assertTrue(result['forced_stop'])

    def test_default_eof_policy_still_rejects_inherited_open_pipe(self):
        source, identity = self.inherited_output_source()
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'timed out'):
            self.run_python('strict-command', source, timeout=.5)
        result = self.context.report['processes'][-1]
        self.assertEqual(result['failure_observation']['leader_exit_code'], 0)
        self.assertTrue(result['failure_observation']['output_capture_open'])
        self.assert_stopped(int(identity.read_text()))

    def test_wineboot_nonzero_exit_is_rejected_and_inherited_child_stopped(self):
        source, identity = self.inherited_output_source(exit_code=7)
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'failed'):
            self.run_python('wineboot', source, timeout=3, allow_background_output=True)
        result = self.context.report['processes'][-1]
        self.assertEqual(result['failure_observation']['leader_exit_code'], 7)
        self.assertTrue(result['forced_stop'])
        self.assert_stopped(int(identity.read_text()))

    def test_genuinely_running_initializer_still_times_out_with_pre_signal_state(self):
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'timed out'):
            self.run_python('wineboot', 'import time;time.sleep(60)',
                            timeout=.2, allow_background_output=True)
        result = self.context.report['processes'][-1]
        self.assertIsNone(result['failure_observation']['leader_exit_code'])
        self.assertTrue(result['failure_observation']['output_capture_open'])
        self.assertNotEqual(result['exit_code'], 0)

    def test_background_output_policy_preserves_cancellation(self):
        timer = threading.Timer(.2, lambda: (self.state / 'stop-request').touch())
        timer.start()
        try:
            with self.assertRaises(diagnostic.Cancelled):
                self.run_python('wineboot', 'import time;time.sleep(60)',
                                timeout=3, allow_background_output=True)
        finally:
            timer.join(timeout=1)
        child = self.context.children[-1]
        self.assert_stopped(child.process.pid)
        self.assertFalse(child.reader.is_alive())

    def test_progress_events_continue_until_stop_without_extending_process_deadline(self):
        stream = io.StringIO()
        timer = threading.Timer(.4, lambda: (self.state / 'stop-request').touch())
        timer.start()
        try:
            with patch.object(diagnostic, 'PROGRESS_INTERVAL', .1), redirect_stdout(stream):
                with self.assertRaises(diagnostic.Cancelled):
                    self.run_python('initialization', 'import time;time.sleep(60)', timeout=2,
                                    progress_message='Preparing Windows environment')
        finally:
            timer.join(timeout=1)
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        progress = [event for event in events if event['type'] == 'stage']
        self.assertGreaterEqual(len(progress), 2)
        self.assertTrue(all(event['status'] == 'running' and
                            event['message'].startswith('Preparing Windows environment · ')
                            for event in progress))
        child = self.context.children[-1]
        self.assert_stopped(child.process.pid)
        self.assertLess(child.recorded['failure_observation']['elapsed_seconds'], 2)

    def test_late_background_output_stays_bounded_after_initializer_exit(self):
        trigger = self.state / 'emit-output'
        service = ('import time\nfrom pathlib import Path\n'
                   f'while not Path({str(trigger)!r}).exists():time.sleep(.01)\n'
                   f'print("x"*{diagnostic.OUTPUT_LIMIT+1024},flush=True)\ntime.sleep(60)\n')
        source = f'import subprocess,sys;subprocess.Popen([sys.executable,"-u","-c",{service!r}])'
        self.run_python('wineboot', source, timeout=3, allow_background_output=True)
        child = self.context.children[-1]
        self.addCleanup(child.stop)
        trigger.touch()
        deadline = time.monotonic()+3
        while not child.overflow and time.monotonic()<deadline:
            time.sleep(.02)
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'output bound'):
            self.context.check()
        self.assertLessEqual(len(child.output), diagnostic.OUTPUT_LIMIT)

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


class WineProcessOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.context = diagnostic.Context(self.root)
        self.owner = diagnostic.WineProcessOwner(self.context)

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.kill()
        process.wait(timeout=3)

    def test_detached_wine_descendant_closes_inherited_output_and_preserves_unrelated_process(self):
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(self.stop_process, sentinel)
        identity = self.root / 'detached.pid'
        source = ('import os,signal,time\nfrom pathlib import Path\n'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                  f'Path({str(identity)!r}).write_text(str(os.getpid()))\n'
                  'print("detached ready",flush=True)\ntime.sleep(60)\n')
        parent = ('import subprocess,sys,time\nfrom pathlib import Path\n'
                  f'subprocess.Popen([sys.executable,"-u","-c",{source!r}],start_new_session=True)\n'
                  f'while not Path({str(identity)!r}).exists():time.sleep(.01)\n'
                  'print("initializer done",flush=True)\n')
        def force_cleanup():
            if identity.exists():
                try:
                    os.kill(int(identity.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.addCleanup(force_cleanup)
        env = dict(os.environ, **self.owner.environment)
        self.context.run('wineboot', [sys.executable, '-u', '-c', parent], env=env,
                         timeout=3, allow_background_output=True)
        child = self.context.children[-1]
        self.addCleanup(child.stop)
        self.assertTrue(child.reader.is_alive())
        start = time.monotonic()
        receipt = self.owner.cleanup(start + 5)
        child.reader.join(timeout=1)
        self.assertTrue(receipt['complete'])
        self.assertEqual(receipt['candidates'], 1)
        self.assertEqual(receipt['remaining'], 0)
        self.assertEqual(receipt['term_signals'], 1)
        self.assertEqual(receipt['kill_signals'], 1)
        self.assertFalse(child.reader.is_alive(), 'Detached Wine stdout holder survived cleanup')
        self.assertIsNone(sentinel.poll(), 'Unrelated same-UID process must survive')
        self.assertLess(time.monotonic() - start, 5)
        for token in self.owner.environment.values():
            self.assertNotIn(token, json.dumps(diagnostic.redacted_value(self.context.report, self.context.secrets)))

    def test_identity_change_prevents_signal(self):
        candidate = {'proc_pid': 123, 'pid': 456, 'starttime': 20}
        changed = {**candidate, 'starttime': 21}
        with patch.object(diagnostic.os, 'pidfd_open', side_effect=OSError(diagnostic.errno.ENOSYS, 'unsupported')), \
             patch.object(self.owner, 'inspect', return_value=changed), \
             patch.object(diagnostic.os, 'kill') as kill:
            with self.assertRaisesRegex(diagnostic.DiagnosticError, 'identity changed'):
                self.owner.signal_owned(candidate, signal.SIGTERM)
        kill.assert_not_called()

    def test_dead_leader_live_worker_is_reaped_and_same_shape_sentinel_survives(self):
        fixture = self.root / 'owned-wine-thread-fixture'
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread',
                        str(ROOT / 'tools/android/owned_wine_thread_fixture.c'), '-o', str(fixture)],
                       check=True, capture_output=True, timeout=20)
        sentinel = subprocess.Popen([str(fixture)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    env=dict(os.environ, COH_WINE_SESSION='unrelated-thread-group'))
        self.addCleanup(self.stop_process, sentinel)
        self.addCleanup(sentinel.stdout.close)
        self.assertEqual(sentinel.stdout.readline(), b'worker_ready\n')
        identity = self.root / 'thread-group.pid'
        parent = ('import subprocess\nfrom pathlib import Path\n'
                  f'p=subprocess.Popen([{str(fixture)!r}],start_new_session=True)\n'
                  f'Path({str(identity)!r}).write_text(str(p.pid))\n')
        def force_cleanup():
            if identity.exists():
                try:
                    os.kill(int(identity.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.addCleanup(force_cleanup)
        self.context.run('wineboot-thread-group', [sys.executable, '-u', '-c', parent],
                         env=dict(os.environ, **self.owner.environment), timeout=3,
                         allow_background_output=True)
        child = self.context.children[-1]
        self.addCleanup(child.stop)
        deadline = time.monotonic() + 3
        while True:
            candidates = self.owner.scan(deadline)
            if self.owner.receipt['owned_live_workers']:
                break
            self.assertLess(time.monotonic(), deadline, 'Fixture leader did not exit its thread')
            time.sleep(.01)
        self.assertEqual(len(candidates), 1)
        group = Path('/proc') / str(candidates[0]['proc_pid'])
        self.assertEqual(self.owner.process_stat(group)['state'], 'Z')
        live = list(self.owner.live_tasks(group))
        self.assertEqual(len(live), 1)
        self.assertEqual(self.owner.status(live[0][0])['tgid'], candidates[0]['proc_pid'])
        pipe = os.readlink(Path('/proc/self/fd') / str(child.process.stdout.fileno()))
        self.assertEqual(os.readlink(live[0][0] / 'fd/1'), pipe,
                         'Live worker must retain the exact captured output pipe')
        self.assertTrue(child.reader.is_alive())
        started = time.monotonic()
        receipt = self.owner.cleanup(started + 5)
        child.reader.join(timeout=1)
        self.assertTrue(receipt['complete'])
        self.assertEqual(receipt['candidates'], 1)
        self.assertGreaterEqual(receipt['dead_leaders_with_live_tasks'], 2)
        self.assertEqual(receipt['owned_live_workers'], 1)
        self.assertEqual(receipt['remaining'], 0)
        self.assertEqual(receipt['term_signals'], 1)
        self.assertEqual(receipt['kill_signals'], 1)
        self.assertFalse(child.reader.is_alive(), 'Live worker retained pipe after whole-group cleanup')
        self.assertIsNone(sentinel.poll(), 'Unrelated dead-leader group must survive')
        self.assertLess(time.monotonic() - started, 5)

    def fake_dead_leader(self):
        group = self.root / '123'
        task = group / 'task/124'
        task.mkdir(parents=True)
        self.owner.proc_root = self.root
        self.owner.initialized = True
        self.owner.real_uid = 42
        self.owner.excluded = set()
        self.owner.direct_pid_view = True
        self.owner.diagnostic_starttime = 1
        leader = {'pid': 123, 'state': 'Z', 'parent': 1, 'starttime': 10}
        worker = {'pid': 124, 'state': 'S', 'parent': 1, 'starttime': 11}
        status = {'uid': 42, 'pid': 123, 'tgid': 123, 'namespace_pids': [123]}
        worker_status = {**status, 'pid': 124, 'namespace_pids': [124]}
        return group, task, leader, worker, status, worker_status

    def test_true_zombie_group_is_ignored_only_after_task_inspection(self):
        group, task, leader, worker, status, worker_status = self.fake_dead_leader()
        with patch.object(self.owner, 'status', return_value=status), \
             patch.object(self.owner, 'process_stat', side_effect=lambda path: leader if path == group else
                          {**worker, 'state': 'Z'}), \
             patch.object(self.owner, 'has_token', side_effect=AssertionError('Dead task environment read')):
            self.assertIsNone(self.owner.inspect(123))
        self.assertEqual(self.owner.receipt['scanned_tasks'], 1)

    def test_dead_leader_with_unreadable_live_worker_fails_closed(self):
        group, task, leader, worker, status, worker_status = self.fake_dead_leader()
        with patch.object(self.owner, 'status', side_effect=lambda path: status if path == group else worker_status), \
             patch.object(self.owner, 'process_stat', side_effect=lambda path: leader if path == group else worker), \
             patch.object(self.owner, 'has_token', side_effect=PermissionError('Live worker non-dumpable')):
            with self.assertRaisesRegex(diagnostic.DiagnosticError, 'Cannot inspect same-UID'):
                self.owner.cleanup(time.monotonic() + 1)
        self.assertFalse(self.owner.receipt['complete'])
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)

    def test_live_worker_wrong_group_or_changed_starttime_cannot_authorize_signal(self):
        group, task, leader, worker, status, worker_status = self.fake_dead_leader()
        candidate = {'proc_pid': 123, 'pid': 123, 'starttime': 10}
        for changed_group in (True, False):
            reads = [0]
            def process_stat(path):
                if path == group:
                    return leader
                reads[0] += 1
                return {**worker, 'starttime': 12} if reads[0] > 1 and not changed_group else worker
            bad_status = {**worker_status, 'tgid': 456} if changed_group else worker_status
            with self.subTest(changed_group=changed_group), \
                 patch.object(self.owner, 'status', side_effect=lambda path: status if path == group else bad_status), \
                 patch.object(self.owner, 'process_stat', side_effect=process_stat), \
                 patch.object(self.owner, 'has_token', return_value=True), \
                 patch.object(diagnostic.os, 'pidfd_open', return_value=19), \
                 patch.object(diagnostic.os, 'close'), \
                 patch.object(diagnostic.signal, 'pidfd_send_signal') as send, \
                 patch.object(diagnostic.os, 'kill') as kill:
                with self.assertRaises(diagnostic.DiagnosticError):
                    self.owner.signal_owned(candidate, signal.SIGKILL)
                send.assert_not_called()
                kill.assert_not_called()

    def test_dead_leader_live_worker_cannot_hide_lost_ownership_before_signal(self):
        group, task, leader, worker, status, worker_status = self.fake_dead_leader()
        candidate = {'proc_pid': 123, 'pid': 123, 'starttime': 10}
        with patch.object(self.owner, 'status', side_effect=lambda path: status if path == group else worker_status), \
             patch.object(self.owner, 'process_stat', side_effect=lambda path: leader if path == group else worker), \
             patch.object(self.owner, 'has_token', return_value=False), \
             patch.object(diagnostic.os, 'pidfd_open', return_value=19), \
             patch.object(diagnostic.os, 'close'), \
             patch.object(diagnostic.signal, 'pidfd_send_signal') as send, \
             patch.object(diagnostic.os, 'kill') as kill:
            with self.assertRaisesRegex(diagnostic.DiagnosticError, 'identity changed'):
                self.owner.signal_owned(candidate, signal.SIGKILL)
        send.assert_not_called()
        kill.assert_not_called()

    def test_same_uid_unreadable_environment_is_not_accepted_as_clean(self):
        proc = self.root / 'proc'
        proc.mkdir()
        (proc / '123').mkdir()
        self.owner.proc_root = proc
        self.owner.initialized = True
        self.owner.real_uid = 42
        self.owner.excluded = set()
        with patch.object(self.owner, 'inspect', side_effect=PermissionError('not dumpable')), \
             patch.object(self.owner, 'status', return_value={'uid': 42}):
            with self.assertRaisesRegex(diagnostic.DiagnosticError, 'Cannot inspect same-UID'):
                self.owner.cleanup(time.monotonic() + 1)
        self.assertFalse(self.owner.receipt['complete'])
        self.assertEqual(self.owner.receipt['inspection_failures'], 1)

    def test_preexisting_same_uid_process_is_excluded_before_unreadable_environment(self):
        self.owner.real_uid = 42
        self.owner.excluded = set()
        self.owner.direct_pid_view = True
        self.owner.diagnostic_starttime = 100
        status = {'uid': 42, 'pid': 123, 'namespace_pids': [123]}
        identity = {'pid': 123, 'state': 'S', 'parent': 1, 'starttime': 99}
        with patch.object(self.owner, 'status', return_value=status), \
             patch.object(self.owner, 'process_stat', return_value=identity), \
             patch.object(Path, 'open', side_effect=PermissionError('non-dumpable')) as read:
            self.assertIsNone(self.owner.inspect(123))
        read.assert_not_called()
        for starttime in (100, 101):
            with self.subTest(starttime=starttime), \
                 patch.object(self.owner, 'status', return_value=status), \
                 patch.object(self.owner, 'process_stat', return_value={**identity, 'starttime': starttime}), \
                 patch.object(Path, 'open', side_effect=PermissionError('non-dumpable')) as read:
                with self.assertRaises(PermissionError):
                    self.owner.inspect(123)
                read.assert_called_once()

    def test_ancestor_is_excluded_before_environment_inspection(self):
        proc = self.root / 'proc'
        proc.mkdir()
        (proc / '123').mkdir()
        self.owner.proc_root = proc
        self.owner.initialized = True
        self.owner.excluded = {123}
        with patch.object(self.owner, 'inspect', side_effect=AssertionError('ancestor inspected')):
            self.assertEqual(self.owner.scan(time.monotonic() + 1), [])

    def test_foreign_namespace_depth_is_excluded_without_reading_environment_or_namespace(self):
        self.owner.real_uid = 42
        self.owner.excluded = set()
        self.owner.direct_pid_view = False
        self.owner.namespace_depth = 2
        with patch.object(self.owner, 'status', return_value={'uid': 42, 'namespace_pids': [123]}), \
             patch.object(diagnostic.os, 'readlink', side_effect=AssertionError('foreign namespace inspected')):
            self.assertIsNone(self.owner.inspect(123))

    def test_pidfd_signal_failure_is_fail_closed_without_pid_fallback(self):
        candidate = {'proc_pid': 123, 'pid': 456, 'starttime': 20}
        with patch.object(diagnostic.os, 'pidfd_open', return_value=19), \
             patch.object(self.owner, 'inspect', return_value=candidate), \
             patch.object(diagnostic.signal, 'pidfd_send_signal', side_effect=PermissionError('denied')), \
             patch.object(diagnostic.os, 'close') as close, \
             patch.object(diagnostic.os, 'kill') as kill:
            with self.assertRaises(PermissionError):
                self.owner.signal_owned(candidate, signal.SIGTERM)
        close.assert_called_once_with(19)
        kill.assert_not_called()


class WineInitializationTests(unittest.TestCase):
    REGISTRATION_TRACE = ('002c:trace:wineboot:start_rundll32 machine 1 starting L"C:\\windows\\system32\\rundll32.exe"\n'
                          '002c:trace:wineboot:start_rundll32 machine 1 starting L"C:\\windows\\system32\\rundll32.exe"\n'
                          '002c:trace:wineboot:start_rundll32 machine 14c starting L"C:\\windows\\syswow64\\rundll32.exe"\n'
                          '002c:trace:wineboot:update_wineprefix wine: configuration in L"/private-prefix" has been updated.\n')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / 'state'
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        (self.assets / 'runtime-lock.json').write_text('{"runtime":"stable"}\n')
        self.wine = self.root / 'wine'
        self.context = diagnostic.Context(self.state, total_timeout=900)
        self.runner = diagnostic.Diagnostic(SimpleNamespace(state=self.state, assets=self.assets,
                                                            wine=self.wine, client_probe=False), self.context)
        self.addCleanup(self.runner.lock.close)
        self.addCleanup(lambda: [child.stop() for child in self.context.children])
        self.prefix = self.runner.wineprefix
        self.prefix.mkdir()
        self.timestamp = self.prefix / '.update-timestamp'
        self.marker = self.prefix / '.coh-wine-ready.json'

    def fake_wine(self, output, expected_timestamp=None):
        timestamp_check = ('assert not timestamp.exists(),"Interrupted timestamp was not removed"\n'
                           if expected_timestamp is None else
                           f'assert timestamp.read_text()=={expected_timestamp!r},"Warm timestamp changed"\n')
        source = (f'#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n'
                  'assert sys.argv[1:]==["wineboot","-i"],sys.argv\n'
                  'timestamp=Path(os.environ["WINEPREFIX"],".update-timestamp")\n' + timestamp_check +
                  'timestamp.write_text("1234\\n")\n'
                  f'print({output!r},end="",flush=True)\n')
        self.wine.write_text(source)
        self.wine.chmod(0o700)

    def test_interrupted_timestamp_is_removed_and_one_registration_is_required(self):
        self.timestamp.write_text('1234\n')
        sentinel = self.prefix / 'user.reg'
        sentinel.write_text('preserve existing settings')
        self.fake_wine(self.REGISTRATION_TRACE)
        self.runner.initialize_wine()
        receipt = self.context.report['wine_initialization']
        self.assertEqual(receipt['state'], 'initialized')
        self.assertTrue(receipt['update_timestamp_removed'])
        self.assertFalse(receipt['ready_prefix_reused'])
        self.assertEqual(receipt['timeout_seconds'], 600)
        self.assertEqual((receipt['registration_processes'], receipt['wow64_registration_processes'],
                          receipt['registration_passes']), (3, 1, 1))
        self.assertFalse(self.marker.exists(), 'wineboot exit alone cannot mark a prefix ready')
        self.assertEqual(sentinel.read_text(), 'preserve existing settings')

    def test_ready_prefix_reuses_stable_runtime_identity_without_forced_registration(self):
        self.fake_wine(self.REGISTRATION_TRACE)
        self.runner.initialize_wine()
        self.runner.mark_wine_ready()
        self.fake_wine('002c:trace:wineboot:main Operation done\n', expected_timestamp='1234\n')
        self.runner.initialize_wine()
        receipt = self.context.report['wine_initialization']
        self.assertTrue(receipt['ready_prefix_reused'])
        self.assertFalse(receipt['update_timestamp_removed'])
        self.assertFalse(self.marker.exists(), 'Warm readiness must be renewed by the current PE32 proof')
        self.assertEqual(receipt['registration_processes'], 0)
        self.assertEqual(receipt['registration_passes'], 0)
        self.assertEqual(receipt['runtime_lock_sha256'], diagnostic.file_hash(self.assets / 'runtime-lock.json'))

    def test_changed_runtime_or_missing_timestamp_requires_fresh_proof(self):
        self.fake_wine(self.REGISTRATION_TRACE)
        self.runner.initialize_wine()
        self.runner.mark_wine_ready()
        (self.assets / 'runtime-lock.json').write_text('{"runtime":"changed"}\n')
        self.runner.prepare_wine_initialization()
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.timestamp.exists())
        self.assertFalse(self.runner.wine_initialization['ready_prefix_reused'])

    def test_failed_warm_initialization_consumes_readiness_and_next_attempt_repairs(self):
        self.fake_wine(self.REGISTRATION_TRACE)
        self.runner.initialize_wine()
        self.runner.mark_wine_ready()
        self.fake_wine('err:environ:run_wineboot boot event wait timed out\n', expected_timestamp='1234\n')
        with self.assertRaises(diagnostic.DiagnosticError):
            self.runner.initialize_wine()
        self.assertFalse(self.marker.exists())
        self.runner.prepare_wine_initialization()
        self.assertFalse(self.runner.wine_initialization['ready_prefix_reused'])
        self.assertTrue(self.runner.wine_initialization['update_timestamp_removed'])

    def test_readiness_requires_regular_unlinked_timestamp(self):
        self.runner.prepare_wine_initialization()
        self.runner.wine_initialization['state'] = 'initialized'
        with self.assertRaises(diagnostic.DiagnosticError):
            self.runner.mark_wine_ready()
        self.assertFalse(self.marker.exists())
        foreign = self.root / 'foreign-timestamp'
        foreign.write_text('preserved')
        self.timestamp.symlink_to(foreign)
        with self.assertRaises(diagnostic.DiagnosticError):
            self.runner.mark_wine_ready()
        self.assertFalse(self.marker.exists())
        self.assertEqual(foreign.read_text(), 'preserved')

    def test_internal_bootstrap_timeout_is_rejected_even_with_exit_zero(self):
        self.fake_wine(self.REGISTRATION_TRACE + '002c:err:environ:run_wineboot boot event wait timed out\n')
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'internal bootstrap timed out'):
            self.runner.initialize_wine()
        self.assertEqual(self.context.report['processes'][-1]['exit_code'], 0)
        self.assertEqual(self.runner.wine_initialization['state'], 'failed')
        self.assertFalse(self.marker.exists())

    def test_missing_or_duplicate_registration_cannot_pass(self):
        for output in ('', self.REGISTRATION_TRACE * 2):
            with self.subTest(output=output):
                self.fake_wine(output)
                with self.assertRaisesRegex(diagnostic.DiagnosticError, 'registration evidence differs'):
                    self.runner.initialize_wine()
                self.assertFalse(self.marker.exists())

    def test_readiness_marker_is_written_only_after_real_runtime_fixture_validation(self):
        self.runner.initialize = Mock()
        self.runner.start_postgres = Mock()
        self.runner.prepare_database = Mock()
        self.runner.start_wine = Mock()
        self.runner.stop_postgres = Mock()
        self.runner.probe = Mock()
        self.runner.prepare_wine_initialization()
        self.runner.wine_initialization['state'] = 'initialized'
        with patch.object(self.context, 'run', return_value={'output': 'unverified exit zero'}):
            with self.assertRaises(diagnostic.DiagnosticError):
                self.runner.execute()
        self.assertFalse(self.marker.exists())
        self.timestamp.write_text('1234\n')
        with patch.object(self.context, 'run', return_value={'output': RUNTIME_MARKER + '\n'}):
            self.runner.execute()
        self.assertEqual(json.loads(self.marker.read_text()), self.runner.wine_ready_identity)
        self.assertEqual(self.runner.wine_initialization['state'], 'ready')

    def test_malformed_and_linked_markers_fail_closed(self):
        self.timestamp.write_text('existing timestamp')
        for value in ('not JSON', '[]', '{"format":1}',
                      '{"format":true,"purpose":"coh-wine-initialization","runtime_lock_sha256":"' + 'a' * 64 + '"}'):
            self.marker.write_text(value)
            with self.subTest(marker=value), self.assertRaises(diagnostic.DiagnosticError):
                self.runner.prepare_wine_initialization()
            self.assertEqual(self.timestamp.read_text(), 'existing timestamp')
        self.marker.unlink()
        foreign = self.root / 'unrelated'
        foreign.write_text('untouched')
        for path in (self.marker, self.timestamp):
            path.unlink(missing_ok=True)
            path.symlink_to(foreign)
            with self.subTest(path=path.name), self.assertRaises(diagnostic.DiagnosticError):
                self.runner.prepare_wine_initialization()
            path.unlink()
            self.assertEqual(foreign.read_text(), 'untouched')


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

"""Failure lifecycle: observations precede signals and obey owned-read bounds."""
import hashlib
import json
import mmap
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_diagnostic as guest
import game_hang_evidence as hang


class DispatchEvidenceTests(unittest.TestCase):
    stages = {'1': 'INITIALIZED', '4': 'MAIN_LOOP', '7': 'SQL_KEEPALIVE_FOREGROUND'}

    def record(self, *, sequence=2, stage=1, loops=0, flags=0, pid=41):
        raw = hang.DISPATCH_HEADER.pack(b'COHDBP1\0', 1, 128, pid, 42,
                                        sequence, stage, loops, flags, len(self.stages))
        return raw + bytes(128 - len(raw))

    def test_shared_mapping_publishes_live_stage_without_debugger(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            path.write_bytes(bytes(4096))
            with path.open('r+b') as output, mmap.mmap(output.fileno(), 4096) as mapping:
                mapping[:128] = self.record()
                first = hang.read_dispatch_record(path, self.stages)
                self.assertEqual(first['stage'], 'INITIALIZED')
                self.assertFalse(first['is_success_proof'])
                mapping[:128] = self.record(sequence=4, stage=7, loops=103)
                second = hang.read_dispatch_record(path, self.stages, first)
                self.assertEqual(second['stage'], 'SQL_KEEPALIVE_FOREGROUND')
                self.assertEqual(second['loop_count'], 103)
                self.assertEqual(bytes.fromhex(second['raw_record_hex']), mapping[:128])
                self.assertEqual(second['file_identity'], first['file_identity'])

    def test_incomplete_publication_waits_for_even_sequence_and_has_a_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            path.write_bytes(bytes(4096))
            with path.open('r+b') as output, mmap.mmap(output.fileno(), 4096) as mapping:
                mapping[:128] = self.record(sequence=3, stage=7)
                def complete():
                    time.sleep(.004)
                    mapping[:128] = self.record(sequence=4, stage=7)
                writer = threading.Thread(target=complete)
                writer.start()
                try:
                    self.assertEqual(hang.read_dispatch_record(path, self.stages)['sequence'], 4)
                finally:
                    writer.join()
                mapping[:128] = self.record(sequence=5)
                with self.assertRaisesRegex(hang.DispatchPublicationPending, 'incomplete or changing'):
                    hang.read_dispatch_record(path, self.stages)

    def test_startup_retries_odd_publication_but_keeps_corruption_fatal(self):
        class PublicationGatePassed(Exception):
            pass

        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / 'coh-db-progress-first.bin'
                diagnostic = object.__new__(guest.GameDiagnostic)
                diagnostic.runtime = root
                diagnostic.wine_env = {}
                diagnostic.dispatch_paths = {}
                diagnostic.dispatch_stages = self.stages
                diagnostic.schema = {'expected_tables': {}}
                diagnostic.schema_snapshot = Mock(return_value={})
                diagnostic.game = {'dispatch_progress': {'phases': {}}}
                diagnostic.ctx = SimpleNamespace(stage=Mock(), event=Mock(), deadline=time.monotonic() + 2)
                diagnostic.health = Mock()
                diagnostic.start_game = Mock(side_effect=lambda *_a, **_k:
                    path.write_bytes(self.record(sequence=3, stage=4, loops=1) + bytes(4096 - 128)))

                def wait(predicate, seconds, label):
                    if label == 'DbServer schema and local listener':
                        return True
                    if label == 'DbServer main-thread dispatch publication':
                        return guest.GameDiagnostic.wait(diagnostic, predicate, .5, label, interval=.001)
                    raise PublicationGatePassed()

                diagnostic.wait = wait
                read_record = hang.read_dispatch_record
                attempts = []

                def observe(*args, **kwargs):
                    attempts.append(None)
                    try:
                        return read_record(*args, **kwargs)
                    finally:
                        if len(attempts) == 1:
                            payload = self.record(sequence=4, stage=4, loops=1)
                            if corrupt:
                                payload = b'BADMAGIC' + payload[8:]
                            with path.open('r+b') as output, mmap.mmap(output.fileno(), 4096) as mapping:
                                mapping[:128] = payload

                with patch.object(guest, 'check_game_port'), \
                     patch.object(hang, 'read_dispatch_record', side_effect=observe):
                    if corrupt:
                        with self.assertRaisesRegex(guest.base.DiagnosticError, 'format, identity, stage') as raised:
                            diagnostic.start_services('first')
                        self.assertNotIsInstance(raised.exception, hang.DispatchPublicationPending)
                        self.assertEqual(diagnostic.game['dispatch_progress']['phases'], {})
                    else:
                        with self.assertRaises(PublicationGatePassed):
                            diagnostic.start_services('first')
                        self.assertEqual(diagnostic.game['dispatch_progress']['phases']['first']['sequence'], 4)
                self.assertEqual(len(attempts), 2)

    def test_replaced_file_is_fatal_even_when_old_publication_is_odd(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            path.write_bytes(self.record(sequence=3) + bytes(4096 - 128))
            replacement = Path(temporary) / 'replacement.bin'
            replacement.write_bytes(self.record(sequence=4) + bytes(4096 - 128))
            pread = os.pread
            replaced = False

            def read_and_replace(*args):
                nonlocal replaced
                payload = pread(*args)
                if not replaced:
                    os.replace(replacement, path)
                    replaced = True
                return payload

            with patch.object(hang.os, 'pread', side_effect=read_and_replace):
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'changed identity') as raised:
                    hang.read_dispatch_record(path, self.stages)
                self.assertNotIsInstance(raised.exception, hang.DispatchPublicationPending)

    def test_foreign_linked_malformed_or_regressed_records_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            path.write_bytes(self.record(sequence=8, loops=10) + bytes(4096 - 128))
            first = hang.read_dispatch_record(path, self.stages)
            for change in ({'pid': 99, 'sequence': 10, 'loops': 10},
                           {'sequence': 6, 'loops': 10}, {'sequence': 10, 'loops': 9},
                           {'sequence': 10, 'loops': 10, 'flags': 1},
                           {'sequence': 10, 'loops': 10, 'stage': 99}):
                with self.subTest(change=change):
                    path.write_bytes(self.record(**change) + bytes(4096 - 128))
                    with self.assertRaises(guest.base.DiagnosticError):
                        hang.read_dispatch_record(path, self.stages, first)
            path.write_bytes(self.record() + bytes(4096))
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'bounded regular file'):
                hang.read_dispatch_record(path, self.stages)
            link = Path(temporary) / 'link.bin'
            link.symlink_to(path)
            with self.assertRaises(OSError):
                hang.read_dispatch_record(link, self.stages)


class HangEvidenceTests(unittest.TestCase):
    def diagnostic(self, root):
        value = object.__new__(guest.GameDiagnostic)
        value.args = SimpleNamespace(state=root, wine='/owned/wine')
        value.ctx = guest.GameContext(root, total_timeout=60)
        value.ctx.event = Mock()
        value.game = {}
        value.services = []
        value.runtime = root / 'private-runtime'
        return value

    def test_timeout_captures_before_signal_and_final_fallback_does_not_replace_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.diagnostic(root)
            service = diagnostic.ctx.start('first-dbserver', [sys.executable, '-c', 'import time; time.sleep(60)'])
            diagnostic.services.append(service)
            observed = []

            def observe(_diagnostic, _deadline):
                query = diagnostic.ctx.children[-1]
                self.assertIsNone(query.process.poll())
                self.assertIsNone(service.process.poll())
                self.assertFalse(query.forced_stop)
                self.assertFalse(service.forced_stop)
                observed.append(query)
                return {'available': True, 'sessions': [{'query': 'SELECT dbo.AutoCommands.ContainerId'}]}

            try:
                with patch.object(hang, 'capture_postgres', side_effect=observe), \
                     patch.object(hang, 'capture_processes', return_value={'processes': []}), \
                     patch.object(hang, 'capture_windows', return_value=({'available': False}, None)):
                    with self.assertRaisesRegex(guest.base.DiagnosticError, 'game-query-first-ready timed out'):
                        diagnostic.ctx.run('game-query-first-ready',
                            [sys.executable, '-c', 'import time; time.sleep(60)'], timeout=.05,
                            before_stop=diagnostic.observe_odbc_failure)
                    diagnostic.observe_odbc_failure(observed[0])
                    hang.capture(diagnostic)
                self.assertEqual(len(observed), 1)
                self.assertIsNotNone(observed[0].process.poll())
                self.assertTrue(observed[0].forced_stop)
                self.assertIsNone(service.process.poll(), 'Service shutdown must follow observation')
                snapshot = json.loads((root / 'game-hang-captures/snapshot.json').read_text())
                self.assertTrue(snapshot['before_failed_query_stop'])
                self.assertTrue(snapshot['trigger_alive'])
                self.assertTrue(snapshot['trigger_alive_after'])
                self.assertTrue(snapshot['services'][0]['alive'])
                self.assertIn('timed out', snapshot['failure_observation']['reason'])
            finally:
                service.stop()

    def test_failure_observers_cannot_mask_original_error_or_prevent_query_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = self.diagnostic(Path(temporary))
            with patch.object(hang, 'capture', side_effect=PermissionError('snapshot denied')):
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'query timed out'):
                    diagnostic.ctx.run('query', [sys.executable, '-c', 'import time; time.sleep(60)'],
                        timeout=.01, before_stop=diagnostic.observe_odbc_failure)
            self.assertIsNotNone(diagnostic.ctx.children[0].process.poll())
            self.assertIn('snapshot denied', diagnostic.ctx.report['observation_failures'][0])

    def test_cancel_does_not_consume_snapshot_budget_before_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = self.diagnostic(Path(temporary))
            diagnostic.ctx.cancel_requested = True
            with patch.object(hang, 'capture_postgres') as probe:
                hang.capture(diagnostic)
            probe.assert_not_called()
            self.assertFalse(diagnostic.game['hang_capture']['attempted'])
            self.assertFalse((Path(temporary) / 'game-hang-captures').exists())

    def test_partial_capture_exports_explicit_errors_and_redacted_hash_bound_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.diagnostic(root)
            diagnostic.ctx.secrets = ['private-secret']
            with patch.object(hang, 'capture_postgres', side_effect=PermissionError('query private-secret denied')), \
                 patch.object(hang, 'capture_processes', return_value={'stack': {'available': False,
                                  'error_type': 'PermissionError', 'error': 'denied'}}), \
                 patch.object(hang, 'capture_windows', return_value=({'available': False}, 'partial private-secret\n')):
                hang.capture(diagnostic)
            output = root / 'game-hang-captures'
            snapshot = json.loads((output / 'snapshot.json').read_text())
            self.assertFalse(snapshot['postgres']['available'])
            self.assertFalse(snapshot['windows']['available'])
            self.assertFalse(snapshot['before_failed_query_stop'])
            manifest = json.loads((output / 'manifest.json').read_text())
            self.assertEqual(set(manifest['files']), {'snapshot.json', 'windows-contexts.jsonl'})
            for name, record in diagnostic.game['hang_capture_files'].items():
                raw = (output / name).read_bytes()
                self.assertNotIn(b'private-secret', raw)
                self.assertEqual(record, {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_sql_retains_full_last_query_beyond_report_tail_and_limits_private_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = self.diagnostic(Path(temporary))
            diagnostic.pg = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
            diagnostic.database = 'coh_test_' + 'a' * 16
            diagnostic.base_env = os.environ.copy()
            diagnostic.credentials = {'cohdiag_admin': 'private-secret'}
            diagnostic.socket_dir = Path('/owned/socket')
            diagnostic.port = 12345
            diagnostic.pgtool = lambda name: '/owned/' + name
            query = 'SELECT ' + 'x' * 20000
            response = {'sessions': [{'query': query, 'state': 'idle', 'wait_event': 'ClientRead'}],
                        'session_count': 1, 'track_activity_query_size': '32kB'}
            original_run = diagnostic.ctx.run
            captured = {}

            def probe(label, argv, **kwargs):
                captured.update(kwargs)
                return original_run(label, [sys.executable, '-c', 'print(' + repr(json.dumps(response)) + ')'],
                                    timeout=kwargs['timeout'], cleanup=True)

            diagnostic.ctx.run = probe
            actual = hang.capture_postgres(diagnostic, time.monotonic() + 3)
            self.assertEqual(actual['sessions'][0]['query'], query)
            self.assertGreater(len(query), len(diagnostic.ctx.report['processes'][0]['output']))
            self.assertIn("datname='coh_test_" + 'a' * 16 + "' AND usename='cohtest'", captured['input_text'])
            self.assertIn('wait_event_type, wait_event, query_start, xact_start', captured['input_text'])
            self.assertIn('LIMIT 80', captured['input_text'])
            self.assertNotIn('left(query', captured['input_text'].lower())
            self.assertTrue(captured['cleanup'])

    def make_owned_process(self, root):
        pid, tid = 201, 202
        process = root / str(pid)
        task = process / 'task' / str(tid)
        task.mkdir(parents=True)
        (process / 'fd').mkdir()
        (process / 'net').mkdir()
        def populate(path, own_pid):
            fields = ['S', '1'] + ['0'] * 17 + ['99', '0']
            (path / 'stat').write_text(str(own_pid) + ' (owned) ' + ' '.join(fields))
            (path / 'status').write_text('Uid:\t1000\t1000\t1000\t1000\nPid:\t' + str(own_pid)
                                        + '\nTgid:\t201\nName:\towned\n')
            for name in ('wchan', 'syscall', 'stack'):
                (path / name).write_text('owned-' + name)
        populate(process, pid)
        populate(task, tid)
        (process / 'cmdline').write_bytes(b'wine\0MapServer.exe\0')
        (process / 'fd/4').symlink_to('socket:[777]')
        for name in ('tcp', 'tcp6', 'udp', 'udp6'):
            (process / 'net' / name).write_text('header\n0: 01 02 03 04 05 06 07 08 777\n'
                                               '1: 01 02 03 04 05 06 07 08 888\n')
        (process / 'net/unix').write_text('header\n00: 01 02 03 04 05 777 /owned/socket\n')
        identity = {'proc_pid': pid, 'pid': pid, 'starttime': 99}
        owner = SimpleNamespace(proc_root=root, real_uid=1000, inspect=Mock(return_value=identity),
            scan=Mock(return_value=[identity]), process_stat=guest.base.WineProcessOwner.process_stat,
            status=guest.base.WineProcessOwner.status)
        return owner, identity, process

    def test_owned_tasks_permissions_and_socket_filter_are_honest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            owner, identity, process = self.make_owned_process(root)
            diagnostic = SimpleNamespace(wine_owner=owner, ctx=SimpleNamespace(children=[]))
            original = Path.open
            def read(path, *args, **kwargs):
                if path.name == 'stack':
                    raise PermissionError('kernel denies stack access')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'open', read):
                capture = hang.capture_processes(diagnostic, time.monotonic() + 3)
            record = capture['processes'][0]
            self.assertEqual(record['identity'], identity)
            self.assertEqual(record['stack']['error_type'], 'PermissionError')
            self.assertFalse(record['tasks'][0]['stack']['available'])
            self.assertEqual(record['tasks'][0]['identity']['pid'], 202)
            self.assertEqual(record['socket_fds'], [{'fd': 4, 'inode': '777'}])
            tables = capture['sockets']['tables']
            self.assertEqual(len(tables['tcp']['rows']), 1)
            self.assertIn('777', tables['tcp']['rows'][0])
            self.assertNotIn('888', json.dumps(tables))

    def test_changed_process_identity_discards_all_unverified_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            owner, identity, _ = self.make_owned_process(root)
            owner.inspect.side_effect = [identity, {**identity, 'starttime': 100}]
            diagnostic = SimpleNamespace(wine_owner=owner, ctx=SimpleNamespace(children=[]))
            capture = hang.capture_processes(diagnostic, time.monotonic() + 3)
            self.assertFalse(capture['processes'][0]['available'])
            self.assertNotIn('status', capture['processes'][0])
            self.assertNotIn('tasks', capture['processes'][0])
            self.assertFalse(capture['sockets']['available'])

    def test_proc_text_budget_is_explicit_and_cannot_read_past_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'data'
            path.write_bytes(b'x' * 100)
            capture = hang.ProcCapture(time.monotonic() + 3)
            capture.remaining = 12
            self.assertEqual(capture.read(path, 20), {'available': True, 'text': 'x' * 12,
                                                    'bytes': 12, 'truncated': True})
            self.assertEqual(capture.read(path, 20)['omitted'], 'aggregate text bound')

    def test_windows_contexts_require_terminal_receipt_and_an_observed_thread(self):
        complete = {'kind': 'complete', 'format': 1, 'errors': 0, 'truncated': False,
                    'processes': 3, 'threads': 10}
        scenarios = [(complete, False, True), ({**complete, 'threads': 0}, False, False),
                     ({**complete, 'errors': 1}, False, False),
                     ({**complete, 'truncated': True}, False, False), (complete, True, False),
                     ({'kind': 'thread'}, False, False)]
        for receipt, forced, expected in scenarios:
            with self.subTest(receipt=receipt, forced=forced), tempfile.TemporaryDirectory() as temporary:
                diagnostic = self.diagnostic(Path(temporary))
                diagnostic.wine_env = {'WINEPREFIX': '/owned/prefix'}
                raw = json.dumps(receipt) + '\n'
                child = SimpleNamespace(text=lambda: raw, overflow=False, forced_stop=forced,
                                        reader=SimpleNamespace(is_alive=lambda: False))
                def run(*_args, **kwargs):
                    self.assertTrue(kwargs['cleanup'])
                    self.assertLessEqual(kwargs['timeout'], 15)
                    diagnostic.ctx.children.append(child)
                    if forced:
                        raise guest.base.DiagnosticError('probe timed out')
                    return {'exit_code': 0}
                diagnostic.ctx.run = run
                with patch.object(Path, 'is_file', return_value=True), \
                     patch.object(Path, 'is_symlink', return_value=False):
                    metadata, output = hang.capture_windows(diagnostic, time.monotonic() + 20)
                self.assertEqual(metadata['available'], expected)
                self.assertFalse(metadata['current_execution_validated'])
                self.assertEqual(output, raw)


if __name__ == '__main__':
    unittest.main()

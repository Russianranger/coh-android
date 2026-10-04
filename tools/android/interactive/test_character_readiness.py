"""Readiness scans stay in owned logs and preserve native proof boundaries."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_reopen_diagnostic as reopen
import client_interactive_diagnostic as interactive
import test_guest as interaction_fixture
from test_character_reopen_guest import reopened, position, stamp, READY, LOG_NAME

SESSION = '0123456789abcdef0123456789abcdef'


class OwnedLogScanTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir()
        self.context = SimpleNamespace(report={}, secrets=[])
        owner = SimpleNamespace(root=self.root, ctx=self.context,
            args=SimpleNamespace(session_id=SESSION))
        self.value = server.LocalCharacterServer(owner)
        self.value.runtime = self.runtime

    def write(self, name, raw):
        path = self.runtime / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def test_missing_runtime_or_logger_directory_cannot_produce_native_ready_or_ground(self):
        for runtime in (None, self.root / 'missing', self.runtime):
            self.value.runtime = runtime
            logs = self.value.current_logs()
            self.assertEqual(logs, [])
            self.assertIsNone(server.ready_record(logs))
            self.assertIsNone(server.stable_ground_evidence(logs, {'sent_utc_ms': 1}, 100000))

    def test_scans_complete_logger_subtree_and_root_logs_without_visiting_data(self):
        self.write(LOG_NAME, READY.encode())
        self.write('logs/mapserver/nested/extra.log', b'complete nested diagnostic\n')
        self.write('root.log', b'root native diagnostic\n')
        self.write('data/old/logs/dbserver/entity_2026-10-01-01-00-00.log', READY.encode())
        self.write('data/huge/ignored.log', b'not owned native evidence\n')
        original = server.os.scandir
        visited = []
        def scan(descriptor):
            target = os.readlink('/proc/self/fd/' + str(descriptor))
            visited.append(Path(target))
            self.assertNotIn('data', Path(target).parts)
            return original(descriptor)
        with patch.object(Path, 'rglob', side_effect=AssertionError('full runtime traversal')), \
                patch.object(server.os, 'scandir', side_effect=scan):
            logs = self.value.current_logs()
        self.assertEqual([name for name, _ in logs],
            [LOG_NAME, 'logs/mapserver/nested/extra.log', 'root.log'])
        self.assertIsNotNone(server.ready_record(logs))
        metrics = self.context.report['character_observer_metrics']['native_log_reads']
        self.assertEqual(metrics['last_files'], 3)
        self.assertEqual(metrics['last_directories'], len(visited))
        self.assertEqual(metrics['reads'], 1)
        self.assertGreaterEqual(metrics['last_ms'], 0)

    def test_stale_native_records_in_data_are_not_current_owned_logger_records(self):
        self.write('data/' + LOG_NAME, READY.encode())
        self.assertEqual(self.value.current_logs(), [])
        self.assertIsNone(server.ready_record(self.value.current_logs()))

    def test_linked_runtime_root_and_logger_parents_are_refused_including_dangling_links(self):
        self.value.runtime = self.root / 'linked-runtime'
        self.value.runtime.symlink_to(self.runtime, target_is_directory=True)
        with self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        self.value.runtime.unlink()
        self.value.runtime.symlink_to(self.root / 'missing', target_is_directory=True)
        with self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        self.value.runtime = self.runtime
        for target in (self.root / 'missing', self.root / 'foreign'):
            if target.name == 'foreign': target.mkdir()
            link = self.runtime / 'logs'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
            link.unlink()
        self.write('logs/dbserver/first.log', b'first\n')
        (self.runtime / 'logs/mapserver').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(server.base.DiagnosticError): self.value.current_logs()

    def test_symlink_hardlink_fifo_and_foreign_log_ownership_cannot_be_read(self):
        outside = self.root / 'outside'
        outside.write_bytes(READY.encode())
        path = self.runtime / 'bad.log'
        path.symlink_to(outside)
        with self.assertRaises(OSError): self.value.current_logs()
        path.unlink()
        os.link(outside, path)
        with self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        path.unlink()
        path.write_bytes(b'native diagnostic\n')
        original = server.os.fstat
        def foreign(descriptor):
            value = original(descriptor)
            if os.readlink('/proc/self/fd/' + str(descriptor)) == str(path):
                attrs = dict(st_mode=value.st_mode, st_nlink=value.st_nlink,
                    st_uid=os.geteuid() + 1, st_size=value.st_size)
                return SimpleNamespace(**attrs)
            return value
        with patch.object(server.os, 'fstat', side_effect=foreign), \
                self.assertRaises(server.base.DiagnosticError):
            self.value.current_logs()
        self.assertEqual(outside.read_bytes(), READY.encode())

    def test_file_count_bytes_and_directory_bounds_remain_fail_closed(self):
        self.write('logs/dbserver/a.log', b'12345')
        with patch.object(server, 'SERVER_LOG_FILE_LIMIT', 4), \
                self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        self.write('logs/mapserver/b.log', b'12345')
        with patch.object(server, 'SERVER_LOG_TOTAL_LIMIT', 9), \
                self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        with patch.object(server, 'SERVER_LOG_COUNT_LIMIT', 1), \
                self.assertRaises(server.base.DiagnosticError): self.value.current_logs()
        for path in self.runtime.glob('logs/*/*.log'): path.unlink()
        with patch.object(server, 'SERVER_LOG_COUNT_LIMIT', 2), \
                self.assertRaises(server.base.DiagnosticError): self.value.current_logs()

    def test_partial_lines_cannot_become_ready_or_second_physics_sample(self):
        first = position('261001 01:30:30')
        second = position('261001 01:31:00')
        path = self.write(LOG_NAME, READY.rstrip('\n').encode())
        self.assertIsNone(server.ready_record(self.value.current_logs()))
        path.write_text(READY + first + second.rstrip('\n'))
        logs = self.value.current_logs()
        self.assertIsNotNone(server.ready_record(logs))
        self.assertIsNone(server.stable_ground_evidence(logs,
            {'sent_utc_ms': stamp('261001 01:30:01')}, stamp('261001 01:31:15')))
        with path.open('a') as output: output.write('\n')
        proof = server.stable_ground_evidence(self.value.current_logs(),
            {'sent_utc_ms': stamp('261001 01:30:01')}, stamp('261001 01:31:15'))
        self.assertEqual(proof['elapsed_ms'], 30000)

    def test_duplicate_routes_or_wrong_owned_route_cannot_supply_two_samples(self):
        first = position('261001 01:30:30')
        self.write(LOG_NAME, first.encode())
        self.write('logs/mapserver/entity.log', first.replace(
            'City_01_01_1:127.0.0.1:127.0.0.1 ', '').encode())
        self.write('logs/unrelated/entity.log', position('261001 01:31:00').encode())
        logs = self.value.current_logs()
        self.assertEqual(len(server.native_position_records(logs)), 1)
        self.assertIsNone(server.stable_ground_evidence(logs,
            {'sent_utc_ms': stamp('261001 01:30:01')}, stamp('261001 01:31:15')))

    def test_collection_retains_every_logger_byte_and_hash_without_full_tree_walk(self):
        raw = READY.encode() + b'\xff legacy byte\n'
        self.write(LOG_NAME, raw)
        self.write('logs/mapserver/nested/extra.log', b'nested\n')
        self.write('data/ignored.log', b'unrelated\n')
        target = self.root / 'evidence'
        target.mkdir()
        with patch.object(Path, 'rglob', side_effect=AssertionError('full runtime traversal')):
            self.value.collect_server_logs(target)
        with zipfile.ZipFile(target / 'character-server-logs.zip') as archive:
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(archive.read(LOG_NAME), raw)
            self.assertEqual(set(manifest['files']), {LOG_NAME, 'logs/mapserver/nested/extra.log'})
            self.assertEqual(manifest['files'][LOG_NAME]['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.context.report['character_server_logs']['truncated'])


class GroundObservationReceiptTests(unittest.TestCase):
    def instance(self, proof):
        value = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
        value.args = SimpleNamespace(session_id=SESSION)
        value.ctx = SimpleNamespace(report={'character_reopen': proof}, event=Mock())
        value.connected_announced = True
        return value

    def test_initial_ground_pair_is_preserved_when_save_replaces_latest_pair(self):
        ground = {'verified': True, 'samples': [{'utc_ms': 1000}, {'utc_ms': 31000}],
            'elapsed_ms': 30000, 'position': [132.82, 44.04, -597.78]}
        proof = reopened(client_pid=44, ground_evidence=ground, ground_observed_utc_ms=32000)
        value = self.instance(proof)
        with patch.object(reopen.creation.CharacterCreationDiagnostic, 'observe_console',
                return_value=('', {'pid': 44}, {})):
            value.observe_console()
            original = copy.deepcopy(ground)
            ground['samples'][-1]['utc_ms'] = 91000
            ground['position'] = [104.47, 31.96, -531.56]
            value.observe_console()
        metrics = value.ctx.report['character_observer_metrics']
        self.assertEqual(metrics['initial_ground_evidence'], original)
        self.assertEqual(metrics['last_native_ground_sample_to_event_ms'], 1000)
        value.ctx.event.assert_called_once()

    def test_native_ready_delay_uses_original_complete_logger_timestamp(self):
        proof = reopened(client_pid=44, stable_ground_verified=False,
            client_ready_evidence={'log_timestamp': '261001 01:29:50'},
            client_ready_observed_utc_ms=stamp('261001 01:30:59'))
        value = self.instance(proof)
        with patch.object(reopen.creation.CharacterCreationDiagnostic, 'observe_console',
                return_value=('', {'pid': 44}, {})):
            value.observe_console()
            proof['client_ready_observed_utc_ms'] += 100000
            value.observe_console()
        self.assertEqual(value.ctx.report['character_observer_metrics']['native_ready_to_observation_ms'], 69000)
        value.ctx.event.assert_not_called()

    def test_foreign_identity_or_unverified_ground_still_cannot_emit_relocation(self):
        for changes in ({'client_pid': 45}, {'session_id': 'f' * 32}, {'ordinary_stuck_observed': False}):
            value = self.instance(reopened(**dict({'client_pid': 44}, **changes)))
            with self.subTest(changes=changes), patch.object(
                    reopen.creation.CharacterCreationDiagnostic, 'observe_console',
                    return_value=('', {'pid': 44}, {})), self.assertRaises(server.base.DiagnosticError):
                value.observe_console()
            value.ctx.event.assert_not_called()


class ObserverCadenceTests(unittest.TestCase):
    def fixture(self):
        case = interaction_fixture.InteractionTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def test_slow_native_poll_does_not_add_another_five_second_idle_wait(self):
        case = self.fixture()
        original = case.d.observe_console
        calls = []
        def observe():
            calls.append(case.elapsed)
            case.elapsed += 6
            return original()
        case.d.observe_console = observe
        case.finish_when_ready()
        case.d.execute()
        self.assertAlmostEqual(calls[0], 0)
        self.assertLess(calls[1], 7)
        metrics = case.d.ctx.report['client_observer_metrics']['console_and_native_readiness']
        self.assertEqual(metrics['max_ms'], 6000)
        self.assertEqual(case.d.ctx.report['interaction_completion_reason'], 'finish_requested')
        self.assertTrue(case.d.startup_complete)

    def test_slow_registry_keeps_five_second_evidence_cadence_and_records_cost(self):
        case = self.fixture()
        original = case.d.ctx.run.side_effect
        def run(label, *args, **kwargs):
            if label == 'client-progress-registry': case.elapsed += 2.5
            return original(label, *args, **kwargs)
        case.d.ctx.run.side_effect = run
        observe = case.d.observe_console
        calls = []
        def record():
            calls.append(case.elapsed)
            return observe()
        case.d.observe_console = record
        case.finish_when_ready()
        case.d.execute()
        self.assertEqual(calls[:2], [0, 5])
        self.assertEqual(case.d.ctx.report['client_observer_metrics']['progress_registry']['max_ms'], 2500)
        self.assertEqual(case.d.ctx.report['client_launcher_timing']['started_monotonic'], 0)
        self.assertEqual(case.d.ctx.report['client_launcher_timing']['source'],
            'current_owned_launcher_start_returned')

    def test_translated_registry_is_not_started_during_incomplete_client_loading(self):
        case = self.fixture()
        complete = case.output
        original = case.d.ctx.run.side_effect
        queries = []
        def run(label, *args, **kwargs):
            if label == 'client-progress-registry': queries.append(case.elapsed)
            return original(label, *args, **kwargs)
        case.d.ctx.run.side_effect = run
        def output():
            if case.elapsed < 30:
                return complete.replace('Renderer initialization complete\n', '').replace('Loaded all data!\n', '')
            if case.elapsed < 60:
                return complete.replace('Loaded all data!\n', '')
            return complete
        case.d.ctx.start.return_value.text.side_effect = output
        case.finish_when_ready()
        case.d.execute()
        self.assertEqual(queries, [60, 80])
        policy = case.d.ctx.report['client_progress_poll_policy']
        self.assertEqual(policy['deferred_checks'], 12)
        self.assertTrue(policy['current_pid_window_and_registry_main_loop_required'])
        self.assertTrue(case.d.startup_complete)
        self.assertEqual(case.d.ctx.report['startup_elapsed_seconds'], 60)

    def test_ready_console_still_requires_current_registry_main_loop(self):
        case = self.fixture()
        case.registry = '    GameProgress    REG_SZ    game_loadData\n'
        with self.assertRaisesRegex(server.base.DiagnosticError, 'bounded deadline'):
            case.d.execute()
        self.assertFalse(case.d.startup_complete)
        self.assertFalse(any(kind == 'client_interaction_ready' for _, kind, _ in case.events))

    def test_incomplete_console_keeps_process_failure_checks_before_next_poll(self):
        case = self.fixture()
        case.output = case.output.replace('Loaded all data!\n', '')
        case.d.ctx.start.return_value.process.poll.side_effect = lambda: 3 if case.elapsed >= 1 else None
        with self.assertRaisesRegex(server.base.DiagnosticError, 'client exited'):
            case.d.execute()
        self.assertLess(case.elapsed, 2)
        self.assertFalse(any(call.args[0] == 'client-progress-registry' for call in case.d.ctx.run.call_args_list))


if __name__ == '__main__': unittest.main()

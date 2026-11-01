"""Lifecycle-boundary timings include preparation; they grant no readiness.

These controlled guest-method tests are not MapServer execution or Thor timing.
"""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_zoning as zoning
import test_saved_map_startup as saved
status = saved.status


class MapStartupTimingTests(unittest.TestCase):
    def fixture(self):
        fixture = saved.SavedMapStartupTests()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_initial_saved_map_includes_baseline_query_and_private_preparation(self):
        clock = {'now': 100.0}
        fixture = self.fixture()
        with patch.object(server.time, 'monotonic', side_effect=lambda: clock['now']), \
                patch.object(server.game, 'check_game_port'):
            value = fixture.instance(5)
            fixture.baseline(value)
            _, kings = fixture.fake_launch(value)
            def prepare():
                clock['now'] += 25
                return {'runtime': kings, 'graph': {'verified': True, 'map_id': 5}}
            value.prepare_kings_row_runtime.side_effect = prepare
            def query(_, label):
                if label == 'zoning-reopen-baseline':
                    clock['now'] += 5
                    return status(5, False)
                clock['now'] += 40
                (value.runtime / 'character-zoning-5-progress.bin').write_bytes(
                    saved.progress_bytes(sequence=4, completed=2))
                return status(5)
            value.query = Mock(side_effect=query)
            value.start_map()
        row = value.initial_startup_timing
        self.assertEqual(row['request_to_map_ready_seconds'], 70)
        self.assertEqual(row['process_spawn_to_map_ready_seconds'], 40)
        self.assertEqual(row['request_to_process_spawn_seconds'], 30)
        self.assertTrue(row['baseline_destination_not_started'])
        self.assertTrue(value.creation_report['map_ready'])
        self.assertFalse(row['physical_60_second_acceptance_validated'])
        self.assertFalse(row['android_tap_boundary_measured'])
        self.assertFalse(row['client_world_ready_observed'])
        self.assertFalse(row['movement_readiness_measured'])

    def test_dependency_failure_is_retained_without_new_readiness_or_deadline(self):
        value = self.fixture().instance()
        deadline = value.ctx.deadline
        with patch.object(server.login.LocalLoginServer, 'start', side_effect=OSError('dependency failed')):
            with self.assertRaises(OSError):
                value.start()
        row = value.initial_startup_timing
        self.assertEqual(row['status'], 'failed_before_map_readiness')
        self.assertEqual(row['failure_type'], 'OSError')
        self.assertIsNone(row['request_to_map_ready_seconds'])
        self.assertEqual(value.ctx.deadline, deadline)
        self.assertFalse(value.creation_report.get('map_ready', False))

    def test_clock_failure_invalidates_duration_without_granting_readiness(self):
        value = self.fixture().instance()
        for failed in (99, float('nan'), float('inf')):
            with self.subTest(clock=failed):
                row = value.begin_startup_timing('controlled_fixture', now=100, utc_ms=1000)
                value.mark_startup_timing(row, 'map_spawn_requested', now=110, utc_ms=1100)
                value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
                self.assertEqual(row['request_to_map_ready_seconds'], 20)
                value.mark_startup_timing(row, 'client_world_ready_observed', now=failed, utc_ms=1300)
                self.assertFalse(row['clock_valid'])
                self.assertIsNone(row['request_to_map_ready_seconds'])
                self.assertIsNone(row['process_spawn_to_map_ready_seconds'])
                self.assertFalse(row['physical_60_second_acceptance_validated'])
        with patch.object(server.time, 'monotonic', side_effect=OSError('clock unavailable')):
            row = value.begin_startup_timing('unavailable_clock')
        self.assertFalse(row['clock_valid'])
        self.assertEqual(row['status'], 'readiness_not_observed')

    def test_resident_return_and_cold_zoning_have_separate_records(self):
        value = self.fixture().instance()
        cold = value.begin_startup_timing('zoning_supervisor_request', map_id=5, epoch=1,
            now=100, utc_ms=1000)
        value.mark_startup_timing(cold, 'map_spawn_requested', now=130, utc_ms=1030)
        value.mark_startup_timing(cold, 'map_ready_observed', now=170, utc_ms=1070)
        warm = value.begin_startup_timing('zoning_supervisor_request', map_id=1, epoch=2,
            resident=True, now=200, utc_ms=2000)
        value.mark_startup_timing(warm, 'map_ready_observed', now=205, utc_ms=2005)
        self.assertEqual(cold['request_to_map_ready_seconds'], 70)
        self.assertFalse(cold['destination_already_resident'])
        self.assertEqual(warm['request_to_map_ready_seconds'], 5)
        self.assertTrue(warm['destination_already_resident'])
        self.assertIsNone(warm['process_spawn_to_map_ready_seconds'])
        self.assertEqual(warm['dependency_state_at_request'], 'already_running_for_zoning')
        self.assertFalse(warm['physical_60_second_acceptance_validated'])
        self.assertEqual(value.creation_report['map_startup_timing'][-2:], [cold, warm])

    def test_timing_only_attempt_exports_before_native_preparation_exists(self):
        value = self.fixture().instance()
        value.ctx.state = value.owner.args.state
        value.ctx.secrets = []
        value.collect_server_logs = Mock()
        row = value.initial_startup_timing
        row.update(status='failed_before_map_readiness', failure_type='OSError')
        self.assertNotIn('map_startup_observation', value.creation_report)
        value.persist_startup_observation()
        persisted = json.loads((value.ctx.state / 'map-startup-observation.json').read_text())
        target = value.owner.root / 'export'; target.mkdir()
        server.LocalCharacterServer.collect(value, target)
        exported = json.loads((target / 'map-startup-observation.json').read_text())
        for document in (persisted, exported):
            self.assertEqual(document['maps'], {})
            self.assertEqual(document['map_startup_timing'], [row])
            self.assertEqual(document['map_startup_timing'][0]['status'], 'failed_before_map_readiness')
            self.assertFalse(document['physical_startup_gain_validated'])

    def test_overlapped_initial_failure_keeps_attempt_and_same_lifecycle_exception(self):
        fixture = self.fixture()
        with patch.object(server.time, 'monotonic', return_value=100), \
                patch.object(server.game, 'check_game_port'):
            value = fixture.instance(5)
            fixture.baseline(value)
            fixture.fake_launch(value)
            value.overlap_client_initialization = True
            value.query = Mock(return_value=status(5, False))
            value.start_map()
            self.assertFalse(value.initial_map_startup['ready'])
            failure = server.base.DiagnosticError('asynchronous map startup failed')
            value.ctx.check.side_effect = failure
            deadline = value.initial_map_startup['deadline']
            with self.assertRaises(server.base.DiagnosticError) as raised:
                value.poll_initial_map_startup()
        self.assertIs(raised.exception, failure)
        self.assertEqual(value.initial_map_startup['deadline'], deadline)
        self.assertFalse(value.initial_map_startup['ready'])
        self.assertFalse(value.creation_report['map_ready'])
        row = value.initial_startup_timing
        self.assertEqual(row['status'], 'failed_before_map_readiness')
        self.assertEqual(row['failure_type'], 'DiagnosticError')
        self.assertIsNone(row['request_to_map_ready_seconds'])
        self.assertIn('map_spawn_requested', row['points'])

    def test_zoning_request_clock_precedes_validation_and_filesystem_guards(self):
        fixture = self.fixture()
        clock = {'now': 100.0}
        original_validate, original_exists = zoning.validate_request, Path.exists
        with patch.object(server.time, 'monotonic', side_effect=lambda: clock['now']), \
                patch.object(server.time, 'time', return_value=1000):
            value = fixture.instance(1)
            value.owner.MANUAL_SESSION = True
            value.creation_report.update(client_pid=44, recovery_requested=False)
            value.maps = {1: {'ready': True}}
            value._query_start = Mock()
            request = dict(format=1, session_id=value.owner.args.session_id, client_pid=44,
                character_id=1, epoch=1, action='prepare', from_map_id=1, to_map_id=5,
                requested_utc_ms=999900)
            def validate(*args, **kwargs):
                result = original_validate(*args, **kwargs)
                clock['now'] += 7
                return result
            def exists(path):
                if path.name in ('character-logout.json', 'character-relocation.json'):
                    clock['now'] += 3
                return original_exists(path)
            with patch.object(zoning, 'validate_request', side_effect=validate), \
                    patch.object(Path, 'exists', exists):
                value._accept_prepare(request, 1000000)
            row = value.pending['startup_timing']
            self.assertEqual(row['points']['request'], {'monotonic_seconds': 100, 'utc_ms': 1000000})
            self.assertEqual(value.pending['preparation_started_monotonic'], 113)
            value.mark_startup_timing(row, 'map_spawn_requested', now=130, utc_ms=1030000)
            value.mark_startup_timing(row, 'map_ready_observed', now=170, utc_ms=1070000)
            self.assertEqual(row['request_to_map_ready_seconds'], 70)
            before = list(value.creation_report['map_startup_timing'])
            with self.assertRaises(server.base.DiagnosticError):
                value._accept_prepare(dict(request, client_pid=999), 1000000)
            self.assertEqual(value.creation_report['map_startup_timing'], before)


if __name__ == '__main__':
    unittest.main()

"""Lifecycle-boundary timings include preparation; they grant no readiness.

These controlled guest-method tests are not MapServer execution or Thor timing.
"""
from pathlib import Path
from contextlib import redirect_stdout
import io
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

    def ready_events(self, value):
        return [call for call in value.ctx.event.call_args_list
                if call.args and call.args[0] == 'map_server_ready_observed']

    def initial_row(self, value, map_id=1):
        row = value.begin_startup_timing('initial_guest_service_request', map_id=map_id, now=100, utc_ms=1000)
        row['baseline_destination_not_started'] = True
        value.mark_startup_timing(row, 'map_spawn_requested', now=110, utc_ms=1100)
        return row

    def test_runtime_database_route_starts_before_parent_pg_and_includes_pre_odbc_work(self):
        clock = {'now': 100.0}
        fixture = self.fixture()
        with patch.object(server.time, 'monotonic', side_effect=lambda: clock['now']):
            value = fixture.instance(5)
            deadline = value.ctx.deadline
            value.sql = Mock(return_value='present')
            def initialize_parent():
                timing = value.initial_startup_timing
                self.assertEqual(timing['points']['runtime_database_route_start']['monotonic_seconds'], 100)
                self.assertNotIn('dependencies_start', timing['points'])
                clock['now'] += 20  # Parent private profile/PostgreSQL initialization.
                value.report['profile_reused'] = True
            with patch.object(server.login.LocalLoginServer, 'initialize', side_effect=initialize_parent):
                server.LocalCharacterServer.initialize(value)
            clock['now'] += 30  # Existing Wine/init and intervening display/setup route.
            value.capture_baseline, value.start_map = Mock(), Mock()
            def start_parent():
                clock['now'] += 5  # Existing ODBC/private DbServer preparation.
            with patch.object(server.login.LocalLoginServer, 'start', side_effect=start_parent):
                value.start()
        row = value.initial_startup_timing
        self.assertEqual(row['runtime_database_route_seconds'], 55)
        self.assertEqual(row['dependency_start_seconds'], 5)
        self.assertIn('contiguous wall-clock route', row['runtime_database_route_scope'])
        self.assertIn('not exclusive dependency CPU time', row['runtime_database_route_scope'])
        self.assertEqual(value.ctx.deadline, deadline)
        self.assertFalse(value.creation_report.get('map_ready', False))

    def test_runtime_database_route_missing_or_invalid_endpoint_remains_unknown(self):
        value = self.fixture().instance()
        row = value.begin_startup_timing('initial_guest_service_request', now=100, utc_ms=1000)
        value.mark_startup_timing(row, 'runtime_database_route_start', now=110, utc_ms=1100)
        value.mark_startup_timing(row, 'dependencies_start', now=120, utc_ms=1200)
        self.assertIsNone(row['runtime_database_route_seconds'])
        value.mark_startup_timing(row, 'dependencies_ready', now=99, utc_ms=1300)
        self.assertFalse(row['clock_valid'])
        self.assertIsNone(row['runtime_database_route_seconds'])
        self.assertIsNone(row['dependency_start_seconds'])
        missing = value.begin_startup_timing('initial_boundary_unavailable', now=200, utc_ms=2000)
        value.mark_startup_timing(missing, 'dependencies_ready', now=230, utc_ms=2300)
        self.assertIsNone(missing['runtime_database_route_seconds'])

    def test_legacy_initialize_does_not_invent_runtime_database_route_boundary(self):
        for unavailable in ('missing_initial_row', 'initial_boundary_unavailable'):
            with self.subTest(unavailable=unavailable):
                value = self.fixture().instance()
                if unavailable == 'missing_initial_row':
                    del value.initial_startup_timing
                else:
                    value.initial_startup_timing['kind'] = unavailable
                    value.initial_startup_timing['request_boundary_observed'] = False
                before = list(value.creation_report['map_startup_timing'])
                failure = server.base.DiagnosticError('parent PG initialization failed')
                with patch.object(server.login.LocalLoginServer, 'initialize', side_effect=failure):
                    with self.assertRaises(server.base.DiagnosticError) as raised:
                        server.LocalCharacterServer.initialize(value)
                self.assertIs(raised.exception, failure)
                self.assertEqual(value.creation_report['map_startup_timing'], before)
                self.assertTrue(all('runtime_database_route_start' not in row['points'] for row in before))

    def test_initial_ready_event_exact_shape_once_for_both_supported_maps(self):
        for map_id in (1, 5):
            with self.subTest(map_id=map_id):
                value = self.fixture().instance(map_id)
                deadline = value.ctx.deadline
                row = self.initial_row(value, map_id)
                value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
                value.mark_startup_timing(row, 'map_ready_observed', now=130, utc_ms=1300)
                events = self.ready_events(value)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].kwargs, dict(format=1, session_id=value.owner.args.session_id,
                    request_kind='initial_guest_service_request', epoch=None, destination_already_resident=False,
                    map_id=map_id, readiness_proof='existing_owned_completed_tick_and_DbServer_endpoint_status',
                    process_spawn_observed=True, native_ready_observed=True))
                self.assertEqual(row['request_to_map_ready_seconds'], 20)
                self.assertEqual(value.ctx.deadline, deadline)
                self.assertFalse(value.creation_report.get('map_ready', False))
                self.assertFalse(row['physical_60_second_acceptance_validated'])

    def test_ready_event_uses_real_context_json_event_api(self):
        value = self.fixture().instance()
        value.ctx.secrets, value.ctx.stage_name = [], 'local_atlas_startup'
        value.ctx.event = server.base.Context.event.__get__(value.ctx, type(value.ctx))
        row = self.initial_row(value)
        output = io.StringIO()
        with redirect_stdout(output):
            value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
        event = json.loads(output.getvalue())
        self.assertEqual(event['type'], 'map_server_ready_observed')
        self.assertEqual(event['request_kind'], 'initial_guest_service_request')
        self.assertEqual(event['session_id'], value.owner.args.session_id)
        self.assertEqual(event['readiness_proof'], 'existing_owned_completed_tick_and_DbServer_endpoint_status')

    def test_ready_event_requires_initial_cold_baseline_and_observed_boundaries(self):
        changes = ({'kind': 'zoning_supervisor_request'}, {'destination_already_resident': True},
            {'epoch': 1}, {'map_id': 101}, {'map_id': True}, {'clock_valid': False},
            {'request_boundary_observed': False}, {'baseline_destination_not_started': False})
        for changed in changes:
            with self.subTest(changed=changed):
                value = self.fixture().instance()
                row = self.initial_row(value)
                row.update(changed)
                value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
                self.assertEqual(self.ready_events(value), [])
        for missing in ('request', 'map_spawn_requested'):
            with self.subTest(missing=missing):
                value = self.fixture().instance()
                row = self.initial_row(value)
                del row['points'][missing]
                value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
                self.assertEqual(self.ready_events(value), [])

    def test_pending_or_invalid_clock_never_emits_ready_event(self):
        value = self.fixture().instance()
        row = self.initial_row(value)
        self.assertEqual(self.ready_events(value), [])
        self.assertEqual(row['status'], 'readiness_not_observed')
        for failed in (99, float('nan'), float('inf')):
            with self.subTest(clock=failed):
                row = self.initial_row(value)
                value.mark_startup_timing(row, 'map_ready_observed', now=failed, utc_ms=1200)
                self.assertFalse(row['clock_valid'])
                self.assertEqual(self.ready_events(value), [])
                self.assertFalse(value.creation_report.get('map_ready', False))

    def test_optional_ready_event_io_or_missing_sink_does_not_change_lifecycle(self):
        for error in (None, BrokenPipeError('report stream closed')):
            with self.subTest(error=error):
                value = self.fixture().instance()
                row = self.initial_row(value)
                if error is None:
                    del value.ctx.event
                else:
                    value.ctx.event.side_effect = error
                deadline = value.ctx.deadline
                value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
                value.mark_startup_timing(row, 'map_ready_observed', now=130, utc_ms=1300)
                self.assertEqual(row['request_to_map_ready_seconds'], 20)
                self.assertEqual(row['status'], 'map_readiness_observed')
                self.assertEqual(row['map_server_ready_event_error'],
                    'event_unavailable' if error is None else 'BrokenPipeError')
                self.assertEqual(value.ctx.deadline, deadline)
                self.assertFalse(value.creation_report.get('map_ready', False))
                if error is not None:
                    self.assertEqual(len(self.ready_events(value)), 1)

    def test_ready_event_never_swallows_cancellation_or_ownership_failure(self):
        for failure in (server.base.Cancelled('cancelled'), server.base.DiagnosticError('ownership failed')):
            with self.subTest(failure=failure):
                value = self.fixture().instance()
                row = self.initial_row(value)
                value.ctx.event.side_effect = failure
                with self.assertRaises(type(failure)) as raised:
                    value.mark_startup_timing(row, 'map_ready_observed', now=120, utc_ms=1200)
                self.assertIs(raised.exception, failure)

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
        self.assertEqual(len(self.ready_events(value)), 1)

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
        self.assertEqual(self.ready_events(value), [])

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
        self.assertEqual(self.ready_events(value), [])

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
        self.assertEqual(self.ready_events(value), [])

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

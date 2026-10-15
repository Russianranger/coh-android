"""Clock-driven cold Kings lifecycle bounds retain native readiness/save gates."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_zoning as zoning

SESSION = 'a' * 32
UTC_MS = 1791768151854
ERROR = zoning.base.DiagnosticError
BASELINE = '5 maps/City_Zones/City_01_02/City_01_02.txt NotReady 1 (Not started) Info\n'
READY = '5 maps/City_Zones/City_01_02/City_01_02.txt S: 1 / 2 Ip: 127.0.0.1:7003 Mem: 100\n'


class Clock:
    def __init__(self):
        self.now = 100.0

    def advance(self, seconds):
        self.now += seconds

    def utc(self):
        return (UTC_MS + round((self.now - 100) * 1000)) / 1000


class KingsPreparationBudgetTests(unittest.TestCase):
    def instance(self, *, available_seconds=1142):
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-kings-budget-')))
        self.clock = Clock()
        self.enterContext(patch.object(zoning.time, 'monotonic', side_effect=lambda: self.clock.now))
        self.enterContext(patch.object(zoning.time, 'time', side_effect=self.clock.utc))
        value = object.__new__(zoning.LocalCharacterZoningServer)
        value.runtime = root / 'atlas'
        value.runtime.mkdir()
        value.owner = SimpleNamespace(args=SimpleNamespace(state=root, session_id=SESSION, wine='wine'),
            wine_env={}, session_budget=SimpleNamespace(deadline=self.clock.now + available_seconds),
            client=SimpleNamespace(process=Mock()))
        value.owner.client.process.poll.return_value = None
        value.ctx = SimpleNamespace(event=Mock(), report={'client_launch': {'pid': 44}}, start=Mock(), check=Mock())
        value.ctx.start.return_value = SimpleNamespace(process=Mock(), output=bytearray(), overflow=False)
        value.ctx.start.return_value.process.poll.return_value = None
        value.active_map_id = 1
        value.monorail_qualified = True
        value.native_station_seen = {}
        value.creation_report = {'client_pid': 44, 'character_id': 1, 'connected_on_atlas': True,
                                 'recovery_requested': False}
        value.zoning_report = {'events': [], 'transfers': [], 'preparation_stage_observations': [],
                              'preparation_schedulers': []}
        value.pending, value.epoch = None, 0
        value.maps = {1: {'ready': True}}
        value.request_history, value.delivery_history = {}, {}
        value.zoning_next, value.zoning_query = 0, None
        value.enabled_announced = False
        value._query_start, value._query_poll = Mock(), Mock(return_value=None)
        value._map_progress = Mock(return_value={'windows_pid': 55, 'tick_completed': 0})
        value.live_progress = lambda record: record is not None and record['tick_completed'] > 0
        value.current_logs, value.map_native_events = Mock(return_value=[]), Mock(return_value=[])
        value._authorize_station = Mock()
        control = SimpleNamespace(environment={}, restored=False, sample=Mock(), restore=Mock(),
            report={'map_id': 5, 'capability': {'supported': False}, 'changed_threads': 0,
                    'restored_threads': 0, 'exited_threads': 0, 'restore_complete': True})
        self.control = control
        self.enterContext(patch.object(zoning.scheduler, 'PreparationScheduler', return_value=control))
        self.enterContext(patch.object(zoning.character.game, 'check_game_port'))
        return value

    def accept(self, value, *, target=5, request_age_ms=0):
        now_ms = round(self.clock.utc() * 1000)
        request = dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
            epoch=value.epoch + 1, action='prepare', from_map_id=1, to_map_id=target,
            requested_utc_ms=now_ms - request_age_ms)
        value._accept_prepare(request, now_ms)

    def prepare(self, value, seconds):
        runtime = value.runtime.with_name('kings')
        runtime.mkdir()
        def work():
            self.clock.advance(seconds)
            return {'runtime': runtime, 'graph': {'verified': True, 'map_id': 5}}
        value.prepare_kings_row_runtime = Mock(side_effect=work)

    def baseline_tick(self, value, *, query_seconds=5):
        self.clock.advance(query_seconds)
        value._query_poll.return_value = ('baseline', BASELINE)
        value.tick_zoning()
        value._query_poll.return_value = None

    def test_device_376_python_plus_274_native_is_separate_bounded_work(self):
        value = self.instance()
        original_session_deadline = value.owner.session_budget.deadline
        self.accept(value)
        self.prepare(value, 376)
        self.baseline_tick(value)
        self.assertEqual(value.pending['phase'], 'map_ready')
        self.assertEqual(value.pending['python_preparation_elapsed_ms'], 381000)
        self.assertEqual(value.pending['runtime_preparation_elapsed_ms'], 376000)
        self.assertEqual(value.pending['native_ready_started_utc_ms'], UTC_MS + 381000)
        self.assertEqual(value.pending['deadline'], 820)
        value.ctx.start.assert_called_once()
        value._authorize_station.assert_not_called()
        self.clock.advance(274)
        value._map_progress.return_value = {'windows_pid': 55, 'tick_completed': 5}
        def ready_query():
            self.clock.advance(5)
            return 'prepared_map', READY
        value._query_poll.side_effect = ready_query
        value.tick_zoning()
        event = value.zoning_report['events'][-1]
        self.assertEqual(event['status'], 'ready')
        self.assertEqual(event['native_ready_elapsed_ms'], 279000)
        self.assertEqual(event['preparation_elapsed_ms'], 660000)
        self.assertEqual(event['preparation_budget_seconds'], 720)
        self.assertEqual(event['python_preparation_budget_seconds'], 420)
        self.assertEqual(event['native_ready_budget_seconds'], 360)
        self.assertTrue(event['python_preparation_completed'])
        self.assertFalse(event['session_budget_extended'])
        self.assertEqual(value.owner.session_budget.deadline, original_session_deadline)
        self.assertEqual(value.zoning_report['transfers'], [])
        self.assertEqual(value.active_map_id, 1)

    def test_python_phase_exhaustion_does_not_launch_native_or_authorize(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 420)
        self.baseline_tick(value)
        value.ctx.start.assert_not_called()
        value._authorize_station.assert_not_called()
        event = value.zoning_report['events'][-1]
        self.assertEqual(event['status'], 'failed')
        self.assertEqual(event['preparation_phase'], 'python_inputs')
        self.assertEqual(event['python_preparation_elapsed_ms'], 425000)
        self.assertFalse(event['python_preparation_completed'])
        self.assertIn('Python preparation timed out', event['message'])
        self.assertTrue(event['current_map_verified'])
        self.assertFalse(event['transfer_requested'])
        self.assertIsNone(value.pending)
        self.assertEqual(value.maps, {1: {'ready': True}})

    def test_native_request_age_is_not_granted_again_after_observation(self):
        value = self.instance()
        self.accept(value, request_age_ms=4000)
        self.assertEqual(value.pending['preparation_overall_deadline'], 816)
        self.assertEqual(value.pending['preparation_deadline_utc_ms'], UTC_MS - 4000 + 720000)
        self.assertEqual(value.pending['preparation_absolute_cap_basis'], 'validated_request_utc_ms')
        self.prepare(value, 376)
        self.baseline_tick(value)
        self.assertEqual(value.pending['deadline'], 816)
        self.clock.now = 816
        value.tick_zoning()
        self.assertEqual(value.zoning_report['events'][-1]['status'], 'failed')
        value._authorize_station.assert_not_called()
        self.assertFalse(value.zoning_report['failure']['transfer_requested'])

    def test_stale_native_request_is_refused_before_any_preparation(self):
        value = self.instance()
        with self.assertRaisesRegex(ERROR, 'stale, foreign'):
            self.accept(value, request_age_ms=zoning.REQUEST_AGE_MS + 1)
        value._query_start.assert_not_called()
        value.ctx.start.assert_not_called()
        self.assertEqual(value.epoch, 0)

    def test_cooperative_input_check_enforces_python_bound_and_restores_context(self):
        value = self.instance()
        self.accept(value)
        original_check = value.ctx.check
        checkpoints = []
        def work():
            for _ in range(420):
                self.clock.advance(1)
                value.ctx.check()
                checkpoints.append(self.clock.now)
            raise AssertionError('An expired Python phase continued preparing inputs')
        value.prepare_kings_row_runtime = Mock(side_effect=work)
        self.baseline_tick(value)
        self.assertIs(value.ctx.check, original_check)
        self.assertEqual(value.zoning_report['events'][-1]['python_preparation_elapsed_ms'], 420000)
        self.assertEqual(len(checkpoints), 414)
        original_check.assert_called()
        value.ctx.start.assert_not_called()
        value._authorize_station.assert_not_called()
        # The shared context is again usable for the ordinary source-map save.
        value.ctx.check()

    def test_cooperative_logout_check_stops_inputs_and_restores_context(self):
        value = self.instance()
        self.accept(value)
        original_check = value.ctx.check
        def work():
            self.clock.advance(10)
            (value.owner.args.state / 'character-logout.json').write_text('{}')
            value.ctx.check()
            raise AssertionError('A requested ordinary save continued destination staging')
        value.prepare_kings_row_runtime = Mock(side_effect=work)
        self.baseline_tick(value)
        self.assertIs(value.ctx.check, original_check)
        self.assertIn('cancelled for the requested ordinary save', value.zoning_report['events'][-1]['message'])
        self.assertFalse(value.zoning_report['events'][-1]['transfer_requested'])
        value.ctx.start.assert_not_called()

    def test_abort_during_python_preparation_restores_existing_context_check(self):
        value = self.instance()
        self.accept(value)
        original_check = value.ctx.check
        def work():
            self.clock.advance(10)
            raise zoning.base.Cancelled('Cancellation requested')
        value.prepare_kings_row_runtime = Mock(side_effect=work)
        with self.assertRaises(zoning.base.Cancelled):
            self.baseline_tick(value)
        self.assertIs(value.ctx.check, original_check)
        self.assertFalse(value.pending['python_preparation_completed'])
        value.ctx.start.assert_not_called()
        value._authorize_station.assert_not_called()

    def test_unused_python_time_cannot_extend_native_or_hard_total_cap(self):
        for python_seconds, expected_deadline in ((10, 475), (400, 820)):
            with self.subTest(python_seconds=python_seconds):
                value = self.instance()
                self.accept(value)
                self.prepare(value, python_seconds)
                self.baseline_tick(value)
                self.assertEqual(value.pending['deadline'], expected_deadline)
                self.clock.now = expected_deadline
                value.tick_zoning()
                event = value.zoning_report['events'][-1]
                self.assertEqual(event['status'], 'failed')
                self.assertEqual(event['preparation_phase'], 'native_readiness')
                self.assertIn('native readiness timed out', event['message'])
                self.assertTrue(event['current_map_verified'])
                self.assertFalse(event['transfer_requested'])
                value._authorize_station.assert_not_called()

    def test_native_status_without_completed_tick_cannot_publish_ready(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 376)
        self.baseline_tick(value)
        self.clock.advance(274)
        value._query_poll.return_value = ('prepared_map', READY)
        value.tick_zoning()
        self.assertNotIn('ready', [row['status'] for row in value.zoning_report['events']])
        value._authorize_station.assert_not_called()
        self.assertFalse(value.maps[5]['ready'])

    def test_completed_tick_with_wrong_or_notready_endpoint_cannot_publish_ready(self):
        for text in (READY.replace(':7003', ':7001'), BASELINE):
            with self.subTest(text=text):
                value = self.instance()
                self.accept(value)
                self.prepare(value, 376)
                self.baseline_tick(value)
                self.clock.advance(274)
                value._map_progress.return_value = {'windows_pid': 55, 'tick_completed': 5}
                value._query_poll.return_value = ('prepared_map', text)
                value.tick_zoning()
                self.assertNotIn('ready', [row['status'] for row in value.zoning_report['events']])
                value._authorize_station.assert_not_called()

    def test_scheduler_restore_consuming_remaining_time_cannot_publish_ready(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 376)
        self.baseline_tick(value)
        self.clock.now = 819
        value._map_progress.return_value = {'windows_pid': 55, 'tick_completed': 5}
        value._query_poll.return_value = ('prepared_map', READY)
        self.control.restore.side_effect = lambda: self.clock.advance(2)
        value.tick_zoning()
        self.assertEqual(value.zoning_report['events'][-1]['status'], 'failed')
        self.assertNotIn('ready', [row['status'] for row in value.zoning_report['events']])
        self.assertFalse(value.maps[5]['ready'])
        value._authorize_station.assert_not_called()

    def test_protocol_completion_after_deadline_cannot_publish_ready_or_arrival(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 376)
        self.baseline_tick(value)
        self.clock.now = 819
        value._map_progress.return_value = {'windows_pid': 55, 'tick_completed': 5}
        def late_status():
            self.clock.advance(5)
            return 'prepared_map', READY
        value._query_poll.side_effect = late_status
        value.tick_zoning()
        self.assertEqual(value.zoning_report['events'][-1]['status'], 'failed')
        self.assertFalse(value.maps[5]['ready'])
        value._authorize_station.assert_not_called()
        value = self.instance()
        self.accept(value)
        value.pending.update(phase='arrival', deadline=105, transfer_requested=True)
        value._observe_arrival = Mock()
        value._query_poll.side_effect = late_status
        with self.assertRaisesRegex(ERROR, 'arrival timed out'):
            value.tick_zoning()
        value._observe_arrival.assert_not_called()
        self.assertTrue(value.zoning_report['failure']['transfer_requested'])

    def test_progress_becoming_stale_during_ready_evidence_cannot_publish_ready(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 376)
        self.baseline_tick(value)
        self.clock.advance(274)
        value._query_poll.return_value = ('prepared_map', READY)
        value._map_progress.side_effect = [
            {'windows_pid': 55, 'tick_completed': 5}, {'windows_pid': 55, 'tick_completed': 0}]
        value.tick_zoning()
        self.assertEqual(value.zoning_report['events'][-1]['status'], 'failed')
        self.assertFalse(value.maps[5]['ready'])
        value._authorize_station.assert_not_called()

    def test_deadline_while_staging_station_reply_cannot_publish_authorization(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 376)
        self.baseline_tick(value)
        value.pending['phase'] = 'ready'
        self.clock.now = 819
        record = dict(kind='station_request', session_id=SESSION, pid=55, request=1, target=5, map_id=1)
        write = zoning.base.private_write
        def slow_reply(path, payload):
            write(path, payload)
            self.clock.advance(2)
        with patch.object(zoning.base, 'private_write', side_effect=slow_reply), self.assertRaises(ERROR):
            zoning.LocalCharacterZoningServer._authorize_station(value, record)
        self.assertFalse((value.runtime / 'monorail-1-reply.txt').exists())
        self.assertFalse(value.pending.get('native_authorization_issued', False))
        self.assertFalse(value.pending['transfer_requested'])
        self.assertEqual(value.active_map_id, 1)

    def test_save_requested_while_python_blocks_prevents_native_launch(self):
        value = self.instance()
        self.accept(value)
        self.prepare(value, 376)
        original = value.prepare_kings_row_runtime.side_effect
        def work():
            result = original()
            (value.owner.args.state / 'character-logout.json').write_text('{}')
            return result
        value.prepare_kings_row_runtime.side_effect = work
        self.baseline_tick(value)
        value.ctx.start.assert_not_called()
        self.assertFalse(value.zoning_report['events'][-1]['transfer_requested'])
        value._authorize_station.assert_not_called()
        with patch.object(zoning.character.LocalCharacterReopenServer, 'character_evidence', return_value='ordinary-save'):
            self.assertEqual(value.character_evidence(), 'ordinary-save')

    def test_late_cold_request_refuses_before_work_and_preserves_save_reserves(self):
        value = self.instance(available_seconds=1140)
        deadline = value.owner.session_budget.deadline
        with self.assertRaisesRegex(ERROR, 'Not enough session time'):
            self.accept(value)
        value._query_start.assert_not_called()
        value.ctx.start.assert_not_called()
        self.assertEqual(value.epoch, 0)
        self.assertEqual(value.request_history, {})
        self.assertEqual(value.owner.session_budget.deadline, deadline)
        self.assertEqual(zoning.session_budget.CONNECTED_SECONDS, 1200)
        self.assertEqual(zoning.session_budget.NEUTRAL_RESERVE_MS, 60000)
        self.assertEqual(zoning.session_budget.SAVE_PROOF_RESERVE_MS, 180000)

    def test_atlas_cold_and_resident_bounds_and_map_epoch_caps_are_retained(self):
        value = self.instance(available_seconds=2000)
        self.accept(value, target=101)
        self.assertEqual(value.pending['preparation_budget_seconds'], 600)
        self.assertEqual(value.pending['python_preparation_budget_seconds'], 0)
        self.assertEqual(value.pending['native_ready_budget_seconds'], 600)
        value = self.instance(available_seconds=700)
        value.maps[5] = {'ready': True}
        self.accept(value)
        self.assertEqual(value.pending['preparation_budget_seconds'], 90)
        self.assertEqual(value.pending['python_preparation_budget_seconds'], 0)
        self.assertEqual(value.pending['phase'], 'map_ready')
        self.assertEqual(zoning.MAX_EPOCHS, 4)
        with self.assertRaisesRegex(ERROR, 'Duplicate or unreviewed'):
            value._spawn_map(101)
        value.ctx.start.assert_not_called()
        value = self.instance(available_seconds=2000)
        value.epoch = 4
        with self.assertRaisesRegex(ERROR, 'outside the supported route'):
            self.accept(value)
        value._query_start.assert_not_called()
        value.ctx.start.assert_not_called()
        self.assertEqual(value.epoch, 4)


if __name__ == '__main__':
    unittest.main()

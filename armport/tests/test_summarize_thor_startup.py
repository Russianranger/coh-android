import io
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SOURCE = Path(__file__).resolve().parents[2] / 'armport/scripts/summarize_thor_startup.py'
SPEC = importlib.util.spec_from_file_location('summarize_thor_startup', SOURCE)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def archive(members):
    value = io.BytesIO()
    with zipfile.ZipFile(value, 'w') as target:
        for name, payload in members.items():
            target.writestr(name, payload if isinstance(payload, (bytes, str)) else json.dumps(payload))
    return value.getvalue()


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def save(self, raw, name='report.zip'):
        path = Path(self.directory.name) / name
        path.write_bytes(raw)
        return path

    def guest(self, rows=None):
        return {'session_id': 'one', 'failures': ['save failed'], 'cleanup_complete': False,
            'character_reopen': {'committed_sql_verified': False, 'map_startup_timing': rows or [
                {'status': 'readiness_not_observed', 'destination_already_resident': False,
                 'request_to_map_ready_seconds': None},
                {'status': 'map_readiness_observed', 'destination_already_resident': True,
                 'request_to_map_ready_seconds': 1.25}]}}

    def android(self, **changes):
        session = 'a' * 32
        event = {'type': 'map_server_ready_observed', 'format': 1, 'session_id': session,
            'request_kind': 'initial_guest_service_request', 'epoch': None, 'map_id': 1,
            'destination_already_resident': False,
            'readiness_proof': 'existing_owned_completed_tick_and_DbServer_endpoint_status',
            'process_spawn_observed': True, 'native_ready_observed': True}
        timing = {'format': 1, 'clock': 'android_elapsed_realtime_milliseconds',
            'includes_system_suspend': True, 'clock_valid': True,
            'service_receipt_elapsed_realtime_ms': 1000, 'ui_action_elapsed_realtime_ms': 900,
            'map_ready_receipt_elapsed_realtime_ms': 66000, 'client_world_ready_receipt_elapsed_realtime_ms': 81000,
            'service_receipt_to_map_ready_seconds': 65.0, 'ui_action_to_map_ready_seconds': 65.1,
            'service_receipt_to_client_world_ready_seconds': 80.0, 'ui_action_to_client_world_ready_seconds': 80.1,
            'map_ready_event': event, 'movement_readiness_measured': False,
            'physical_60_second_acceptance_validated': False, 'is_success_proof': False}
        timing.update(changes)
        return {'session_id': session, 'passed': False, 'android_startup_timing': timing}

    def paired(self, android, guest=None, **members):
        guest = guest or self.guest()
        guest['session_id'] = android['session_id']
        return self.save(archive({'android-client-report.json': android,
            'guest-output/latest-report.json': guest, **members}))

    def test_android_service_boundary_is_primary_and_never_inferred_from_guest(self):
        android = self.android()
        result = subject.analyze(self.paired(android, self.guest([
            {'request_to_map_ready_seconds': 1.0, 'destination_already_resident': False}])))
        self.assertEqual(result['service_receipt_to_map_ready_seconds'], 65.0)
        self.assertEqual(result['ui_action_to_map_ready_seconds'], 65.1)
        self.assertEqual(result['ui_action_to_client_world_ready_seconds'], 80.1)
        self.assertEqual(result['supervisor_rows'][0]['request_to_map_ready_seconds'], 1.0)
        self.assertTrue(result['android_startup_timing_rows'][0]['session_attribution_verified'])
        self.assertFalse(result['android_result']['passed'])
        self.assertFalse(result['acceptance_evaluated'])
        self.assertIsNone(result['full_tap_to_ready_seconds'])
        self.assertIsNone(result['full_tap_to_movable_character_seconds'])

    def test_malformed_android_clock_is_retained_without_promoting_interval(self):
        for changes in ({'clock_valid': False}, {'clock': 'guest_monotonic_seconds'},
                {'service_receipt_elapsed_realtime_ms': 67000},
                {'service_receipt_to_map_ready_seconds': 1.0},
                {'ui_action_elapsed_realtime_ms': 1100, 'ui_action_to_map_ready_seconds': 64.9},
                {'client_world_ready_receipt_elapsed_realtime_ms': 65000,
                 'service_receipt_to_client_world_ready_seconds': 64.0,
                 'ui_action_to_client_world_ready_seconds': 64.1}):
            with self.subTest(changes=changes):
                result = subject.analyze(self.paired(self.android(**changes)))
                self.assertIsNone(result['service_receipt_to_map_ready_seconds'])
                self.assertEqual(result['android_startup_timing_rows'][0]['timing'],
                    self.android(**changes)['android_startup_timing'])
                self.assertFalse(result['android_startup_timing_rows'][0]['clock_and_ready_event_consistent'])

    def test_zoning_resident_and_foreign_events_cannot_claim_initial_boundary(self):
        for changes in ({'destination_already_resident': True}, {'epoch': 1},
                {'request_kind': 'zoning_request'}, {'session_id': 'b' * 32},
                {'native_ready_observed': False}, {'map_id': 101}):
            with self.subTest(changes=changes):
                android = self.android()
                android['android_startup_timing']['map_ready_event'].update(changes)
                result = subject.analyze(self.paired(android))
                self.assertIsNone(result['service_receipt_to_map_ready_seconds'])
                self.assertEqual(len(result['android_startup_timing_rows']), 1)

    def test_optional_ui_and_world_points_stay_null(self):
        android = self.android(ui_action_elapsed_realtime_ms=None, ui_action_to_map_ready_seconds=None,
            client_world_ready_receipt_elapsed_realtime_ms=None,
            service_receipt_to_client_world_ready_seconds=None, ui_action_to_client_world_ready_seconds=None)
        result = subject.analyze(self.paired(android))
        self.assertEqual(result['service_receipt_to_map_ready_seconds'], 65.0)
        self.assertIsNone(result['ui_action_to_map_ready_seconds'])
        self.assertIsNone(result['ui_action_to_client_world_ready_seconds'])

    def test_recovered_checkpoint_preserves_android_clock_without_session_claim(self):
        android = self.android()
        guest = self.guest()
        guest['session_id'] = android['session_id']
        result = subject.analyze(self.save(archive({
            'recovery-manifest.json': {'passed': False, 'session_attribution_verified': False},
            'android-recovery-checkpoint.json': android, 'guest-output/latest-report.json': guest})))
        self.assertTrue(result['session_identity_consistent'])
        self.assertTrue(result['android_startup_timing_rows'][0]['clock_and_ready_event_consistent'])
        self.assertFalse(result['android_startup_timing_rows'][0]['session_attribution_verified'])
        self.assertIsNone(result['service_receipt_to_map_ready_seconds'])
        self.assertEqual(result['android_startup_timing_rows'][0]['timing']['service_receipt_to_map_ready_seconds'], 65.0)

    def test_bad_optional_checkpoint_does_not_erase_complete_wrapper_clock(self):
        result = subject.analyze(self.paired(self.android(), **{'android-recovery-checkpoint.json': '{bad'}))
        self.assertEqual(result['service_receipt_to_map_ready_seconds'], 65.0)
        self.assertTrue(any('Android recovery checkpoint' in text for text in result['errors']))
        self.assertEqual(len(result['android_startup_timing_rows']), 1)

    def test_terminal_clock_survives_missing_guest_without_success(self):
        result = subject.analyze(self.save(archive({'android-client-report.json': self.android(),
            'recovery-manifest.json': {'passed': False, 'session_attribution_verified': False}})))
        self.assertEqual(len(result['android_startup_timing_rows']), 1)
        self.assertIsNone(result['service_receipt_to_map_ready_seconds'])
        self.assertTrue(result['errors'])
        self.assertFalse(result['acceptance_evaluated'])

    def test_stale_guest_identity_blocks_android_promotion(self):
        result = subject.analyze(self.paired(self.android(), **{
            'guest-report.zip': archive({'latest-report.json': self.guest()})}))
        self.assertFalse(result['session_identity_consistent'])
        self.assertIsNone(result['service_receipt_to_map_ready_seconds'])

    def test_owned_launch_memory_aliases_and_sparse_thermals_are_not_whole_server_peak(self):
        memory = {'status': 'observed_owned_linux_launch_process', 'observed': True,
            'scope': 'owned_linux_launch_process_only_at_first_native_ready',
            'peak_scope': 'kernel_VmHWM_for_this_process_lifetime_to_status_read',
            'linux_pid': 123, 'process_starttime_ticks': 400, 'kernel_vm_hwm_bytes': 2048,
            'vm_rss_bytes': 1024, 'includes_other_wine_fex_workers': False,
            'includes_dbserver_or_client': False, 'aggregate_mapserver_peak_measured': False, 'pss_measured': False}
        guest = self.guest()
        maps = {'1': {'owned_launch_memory_at_first_native_ready': memory}}
        guest['map_startup_observation'] = copy.deepcopy(maps)
        guest['character_reopen']['map_startup_observation'] = maps
        thermal = {'service_receipt': {'thermal_status': 0, 'thermal_status_is_temperature': False,
            'battery_temperature_deci_celsius': 315, 'battery_temperature_is_cpu_temperature': False},
            'map_ready_receipt': None}
        result = subject.analyze(self.paired(self.android(thermal_observations=thermal), guest))
        self.assertEqual(len(result['owned_launch_memory_rows']), 1)
        self.assertEqual(result['owned_launch_memory_rows'][0]['observation'], memory)
        self.assertEqual(result['android_thermal_observations'], thermal)
        self.assertIsNone(result['live_peak_memory_bytes'])
        self.assertIsNone(result['live_thermal_observations'])

    def test_failed_and_resident_rows_stay_distinct_without_acceptance(self):
        result = subject.analyze(self.save(archive({'latest-report.json': self.guest()})))
        self.assertEqual(len(result['supervisor_rows']), 2)
        self.assertIsNone(result['supervisor_rows'][0]['request_to_map_ready_seconds'])
        self.assertTrue(result['supervisor_rows'][1]['destination_already_resident'])
        self.assertEqual(result['guest_result']['failures'], ['save failed'])
        self.assertFalse(result['character_reopen_result']['committed_sql_verified'])
        self.assertFalse(result['acceptance_evaluated'])
        self.assertIsNone(result['full_tap_to_movable_character_seconds'])

    def test_native_midline_full_console_is_separate_and_tail_ignored(self):
        native = ('Reading data...ARMPORT_SERVER_STARTUP_V1 status=ok map_id=5 pid=48 '
            'sequence=1 phase=args_parsed elapsed_ms=7.125 phase_ms=7.125 scope=main_entry_to_checkpoint\n'
            'ARMPORT_SERVER_STARTUP_V1 status=clock_error map_id=5 pid=48 scope=main_entry_to_checkpoint\n')
        path = self.save(archive({'latest-report.json': self.guest(),
            'client-evidence/character-atlas-console.txt': native,
            'client-evidence/character-atlas-console-tail.txt': native}))
        result = subject.analyze(path)
        self.assertEqual(len(result['native_phase_rows']), 2)
        self.assertEqual(result['native_phase_rows'][0]['map_id'], 5)
        self.assertEqual(result['native_phase_rows'][0]['elapsed_ms'], 7.125)
        self.assertEqual(result['native_phase_rows'][1]['status'], 'clock_error')
        self.assertEqual(len(result['supervisor_rows']), 2)

    def test_nested_outer_identity_and_operation_proxy(self):
        guest = self.guest()
        path = self.save(archive({'android-client-report.json': {'session_id': 'one',
            'started_uptime_ms': 1000, 'character_connected_observed_uptime_ms': 3500},
            'guest-output/latest-report.json': guest,
            'guest-report.zip': archive({'latest-report.json': guest})}))
        result = subject.analyze(path)
        self.assertTrue(result['session_identity_consistent'])
        self.assertEqual(result['android_operation_to_world_observation_seconds'], 2.5)
        self.assertIsNone(result['full_tap_to_ready_seconds'])

    def test_stale_nested_identity_is_reported_without_replacing_current_clock(self):
        path = self.save(archive({'android-client-report.json': {'session_id': 'one'},
            'guest-output/latest-report.json': self.guest(),
            'guest-report.zip': archive({'latest-report.json': {'session_id': 'old'}})}))
        result = subject.analyze(path)
        self.assertFalse(result['session_identity_consistent'])
        self.assertEqual(len(result['supervisor_rows']), 2)
        self.assertTrue(any('inconsistent session' in text for text in result['errors']))

    def test_broken_nested_archive_does_not_erase_compact_failed_clock(self):
        result = subject.analyze(self.save(archive({'android-client-report.json': {'session_id': 'one'},
            'guest-output/latest-report.json': self.guest(), 'guest-report.zip': b'bad zip'})))
        self.assertEqual(len(result['supervisor_rows']), 2)
        self.assertTrue(any('Nested guest report' in text for text in result['errors']))

    def test_wrapperless_interrupted_carrier_keeps_guest_rows_unattributed(self):
        result = subject.analyze(self.save(archive({
            'recovery-manifest.json': {'status': 'interrupted_unverified',
                'passed': False, 'session_attribution_verified': False},
            'guest-output/latest-report.json': self.guest()})))
        self.assertEqual(len(result['supervisor_rows']), 2)
        self.assertFalse(result['recovery_manifest']['passed'])
        self.assertFalse(result['android_operation_session_attribution_verified'])
        self.assertTrue(result['session_identity_consistent'])

    def test_duplicate_session_and_invalid_file_are_retained(self):
        first = self.save(archive({'latest-report.json': self.guest()}))
        second = self.save(first.read_bytes(), 'copy.zip')
        broken = self.save(b'not zip', 'failed.zip')
        result = subject.summarize([first, second, broken])
        self.assertEqual(len(result['reports']), 3)
        self.assertEqual(result['reports'][1]['duplicate_session_export_of'], str(first))
        self.assertTrue(result['reports'][2]['errors'])
        self.assertFalse(result['acceptance_evaluated'])

    def test_oversized_or_duplicate_required_member_is_rejected(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as target:
            target.writestr('latest-report.json', '{}')
            target.writestr('latest-report.json', '{}')
        result = subject.analyze(self.save(raw.getvalue()))
        self.assertTrue(any('duplicate or oversized' in text for text in result['errors']))


if __name__ == '__main__':
    unittest.main()

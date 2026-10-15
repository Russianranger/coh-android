"""Replay the observed final movement between PeriodicInfo and normal logout."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import test_character_reopen_guest as reopen

server, guest, stamp, SESSION = reopen.server, reopen.guest, reopen.stamp, reopen.SESSION
FIXTURE = Path(__file__).with_name('fixtures') / 'thor-contact-save-0.12.1-20261003.log'
LOG_NAME = 'logs/dbserver/entity_2026-10-03-11-00-00.log'
READY_MS = stamp('261003 11:02:42') + 805
# The private sender receipt was not exported. This synthetic replay time is
# within the observed Android Save request/native logout interval.
SENT_MS = stamp('261003 11:06:31')
NOW_MS = stamp('261003 11:07:48') + 940
PERIODIC = [121.10, -768.0, -702.51]
TERMINAL = [112.468750, -768.0, -660.765625]
SQL_POSITION = [112.461586, -768.0, -660.7662]


def terminal(raw=None, *, path=LOG_NAME, sent_ms=SENT_MS, ready_ms=READY_MS, now_ms=NOW_MS):
    return server.native_logout_position([(path, FIXTURE.read_text() if raw is None else raw)],
        {'sent_utc_ms': sent_ms}, ready_ms, now_ms)


class LogoutPositionTests(unittest.TestCase):
    def prepare(self):
        harness = reopen.ReopenServerTests()
        self.addCleanup(harness.doCleanups)
        instance = harness.instance()
        harness.rows['ents'][0]['logincount'] = 7
        instance.capture_baseline()
        instance.auth_id = 77
        instance.creation_report.update(instance.connection_metadata(), connected_on_atlas=True,
            client_pid=44, character_id=1, auth_id=77, client_ready_observed_utc_ms=READY_MS)
        receipt = dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
                       action='quittologin', sent_utc_ms=SENT_MS)
        (instance.owner.args.state / 'character-logout.json').write_text(json.dumps(receipt))
        instance.current_logs = Mock(return_value=[(LOG_NAME, FIXTURE.read_text())])
        harness.clock.return_value = NOW_MS / 1000
        harness.position.update(zip(('posx', 'posy', 'posz'), SQL_POSITION))
        harness.rows['ents'][0]['logincount'] = 8
        return harness, instance, copy.deepcopy(harness.rows)

    def test_exact_thor_log_records_final_movement_and_terminal_position(self):
        periodic = server.native_position_records([(LOG_NAME, FIXTURE.read_text())])[-1]
        self.assertEqual(periodic['position'], PERIODIC)
        value = terminal()
        self.assertEqual(value['position'], TERMINAL)
        self.assertEqual(value['utc_ms'], stamp('261003 11:06:37'))
        self.assertEqual(value['log_timestamp'], value['logout_timer_evidence']['log_timestamp'])
        self.assertEqual(value['log_route'], 'embedded_dbserver_logserver')
        self.assertGreater(abs(PERIODIC[2] - SQL_POSITION[2]), 40)
        self.assertTrue(all(abs(a-b) < .01 for a, b in zip(TERMINAL, SQL_POSITION)))

    def test_terminal_requires_own_player_map_route_complete_line_and_normal_timer(self):
        raw = FIXTURE.read_text()
        timer_lines = [line for line in raw.splitlines() if 'Logout timer expired' in line]
        location_lines = [line for line in raw.splitlines() if 'Logout location :' in line]
        for changed in (raw.replace('THORHERO', 'OTHER'), raw.replace('COHLOCAL', 'OTHER'),
                raw.replace('City_01_01_1', 'City_02_01_1'), raw.replace('map 1 (', 'map 2 ('),
                raw.replace(timer_lines[0] + '\n', ''), raw.rstrip('\n'),
                '\n'.join(location_lines + timer_lines) + '\n',
                raw.replace('Logout timer expired', 'NetLink was closed')):
            with self.subTest(raw=changed):
                self.assertIsNone(terminal(changed))
        self.assertIsNone(terminal(path='logs/foreign/entity.log'))

    def test_terminal_requires_current_ready_request_and_existing_bounded_window(self):
        for changes in ({'sent_ms': stamp('261003 11:06:39')},
                        {'sent_ms': stamp('261003 11:04:36')},
                        {'ready_ms': stamp('261003 11:06:38')},
                        {'now_ms': stamp('261003 11:06:36')}):
            with self.subTest(changes=changes):
                self.assertIsNone(terminal(**changes))

    def test_two_routes_must_agree_and_cannot_cross_pair_timer_and_location(self):
        raw = FIXTURE.read_text()
        local = raw.replace('City_01_01_1:127.0.0.1:127.0.0.1', '0')
        value = server.native_logout_position([(LOG_NAME, raw), ('logs/mapserver/entity.log', local)],
            {'sent_utc_ms': SENT_MS}, READY_MS, NOW_MS)
        self.assertEqual(value['position'], TERMINAL)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Ambiguous'):
            server.native_logout_position([(LOG_NAME, raw), ('logs/mapserver/entity.log',
                local.replace('112.468750', '113.468750'))],
                {'sent_utc_ms': SENT_MS}, READY_MS, NOW_MS)
        timer_only = ''.join(line+'\n' for line in raw.splitlines() if 'Logout timer expired' in line)
        location_only = ''.join(line+'\n' for line in local.splitlines() if 'Logout location :' in line)
        self.assertIsNone(server.native_logout_position([(LOG_NAME, timer_only),
            ('logs/mapserver/entity.log', location_only)], {'sent_utc_ms': SENT_MS}, READY_MS, NOW_MS))

    def test_terminal_cannot_use_another_timestamp_or_fall_floor(self):
        raw = FIXTURE.read_text()
        location = next(line for line in raw.splitlines() if 'Logout location :' in line)
        self.assertIsNone(terminal(raw.replace(location, location.replace('11:06:37', '11:06:38'))))
        for coordinates in ('112.468750 -2000.000000 -660.765625',
                            '1e999 -768.000000 -660.765625',
                            '112.468750 10000.000000 -660.765625'):
            changed = raw.replace('112.468750 -768.000000 -660.765625', coordinates)
            with self.subTest(coordinates=coordinates), self.assertRaises(server.base.DiagnosticError):
                terminal(changed)

    def test_save_preserves_rows_and_compares_committed_sql_with_actual_logout(self):
        harness, instance, rows = self.prepare()
        result = instance.validate_saved_rows(rows, harness.inventory)
        self.assertEqual(result['login_count'], 8)
        self.assertEqual(result['rows']['powers'], instance.baseline_snapshot['rows']['powers'])
        self.assertEqual(result['rows']['costumeparts'], instance.baseline_snapshot['rows']['costumeparts'])
        native = instance.creation_report['saved_native_position_evidence']
        self.assertEqual(native['position'], TERMINAL)
        self.assertEqual(native['prior_native_position_evidence']['position'], PERIODIC)
        self.assertEqual(native['session_id'], SESSION)
        self.assertEqual(native['client_pid'], 44)
        self.assertFalse(instance.creation_report['recovery_requested'])
        self.assertFalse(instance.creation_report['committed_safe_position_verified'])

    def test_stale_sql_matching_periodic_and_actual_sql_mismatch_are_still_refused(self):
        for coordinates in (PERIODIC, [SQL_POSITION[0] + 2.1, -768, SQL_POSITION[2]],
                            [SQL_POSITION[0], -2000, SQL_POSITION[2]]):
            harness, instance, rows = self.prepare()
            harness.position.update(zip(('posx', 'posy', 'posz'), coordinates))
            with self.subTest(coordinates=coordinates), self.assertRaises(server.base.DiagnosticError):
                instance.validate_saved_rows(rows, harness.inventory)
            self.assertFalse(instance.creation_report['committed_native_position_verified'])

    def test_final_logout_cannot_replace_missing_fresh_native_producer_observation(self):
        for changed in ('no_periodic', 'native_unavailable', 'native_error'):
            harness, instance, rows = self.prepare()
            if changed == 'no_periodic':
                instance.current_logs.return_value = [(LOG_NAME, ''.join(line+'\n'
                    for line in FIXTURE.read_text().splitlines() if 'PeriodicInfo' not in line))]
            if changed == 'native_unavailable': instance.current_native_events = Mock(return_value=[])
            if changed == 'native_error':
                instance.current_native_events = Mock(side_effect=server.base.DiagnosticError('Wrong owned producer'))
            with self.subTest(changed=changed), self.assertRaises(server.base.DiagnosticError):
                instance.validate_saved_rows(rows, harness.inventory)
            self.assertFalse(instance.creation_report['committed_native_position_verified'])

    def test_final_logout_cannot_bypass_receipt_or_protected_row_validation(self):
        for changed in ('session', 'client_pid', 'character_id', 'powers', 'costume'):
            harness, instance, rows = self.prepare()
            if changed in ('session', 'client_pid', 'character_id'):
                path = instance.owner.args.state / 'character-logout.json'
                receipt = json.loads(path.read_text())
                receipt[{'session': 'session_id'}.get(changed, changed)] = 'f'*32 if changed == 'session' else 99
                path.write_text(json.dumps(receipt))
            if changed == 'powers': rows['powers'][0]['uniqueid'] += 1
            if changed == 'costume': rows['costumeparts'][0]['color1'] += 1
            with self.subTest(changed=changed), self.assertRaises(server.base.DiagnosticError):
                instance.validate_saved_rows(rows, harness.inventory)
            self.assertFalse(instance.creation_report['committed_native_position_verified'])

    @patch.object(server.progress, 'compare_records')
    def test_full_ordinary_save_pipeline_uses_terminal_position_and_finishes_verified(self, _compare):
        harness, instance, rows = self.prepare()
        instance.health = Mock()
        instance.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        instance.query = Mock(return_value='invalid container request\n')
        value = instance.character_evidence()
        self.assertTrue(guest.save_verified(value, SESSION))
        self.assertTrue(value['disconnected_before_sql'])
        self.assertTrue(value['requested_logout_observed'])
        self.assertTrue(value['logout_timer_observed'])
        self.assertEqual(value['table_sha256']['powers'], value['baseline']['table_sha256']['powers'])
        self.assertFalse(value['forced_stop_before_save'])
        self.assertFalse(value['recovery_requested'])


if __name__ == '__main__':
    unittest.main()

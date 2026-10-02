"""Replay Thor's real negative-height recovery without weakening save guards."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import test_character_reopen_guest as reopen_tests
from test_character_reopen_guest import (server, guest,
    LOG_NAME, READY, SESSION, position, stamp)

FIXTURE = Path(__file__).with_name('fixtures') / 'thor-ground-0.11.1-20261002.log'
METADATA = FIXTURE.with_suffix('.json')
THOR_LOG = 'logs/dbserver/entity_2026-10-02-09-00-00.log'
# The actual private delivery receipt was not exported. This replay uses a
# synthetic time within the observed Android request / native recovery window.
REPLAY_SENT_MS = stamp('261002 09:44:55')
REPLAY_NOW_MS = stamp('261002 09:46:00')
THOR_POSITION = [123.5, -768.0, -579.0]


def replay():
    text = FIXTURE.read_text()
    return server.stable_ground_evidence([(THOR_LOG, text)],
        {'sent_utc_ms': REPLAY_SENT_MS}, REPLAY_NOW_MS)


class GroundRepairTests(unittest.TestCase):
    def fixture_logs(self):
        return FIXTURE.read_text()

    def test_real_thor_records_recover_to_below_zero_authored_city_hall_spawn(self):
        records = server.native_position_records([(THOR_LOG, self.fixture_logs())])
        self.assertTrue(any(value['position'][1] == -2000 for value in records))
        proof = replay()
        self.assertTrue(proof['verified'])
        self.assertEqual(proof['position'], THOR_POSITION)
        self.assertEqual(proof['elapsed_ms'], 30000)
        self.assertFalse(proof['full_collision_geometry_verified'])

    def test_native_fallback_floor_and_clearance_are_refused(self):
        for y in (-1000000, -2001, -2000, -1999.5, -1999, 10000, 10001):
            with self.subTest(y=y):
                text = position('261002 09:44:57', f'123.5,{y},-579') \
                    + position('261002 09:45:27', f'123.5,{y},-579')
                self.assertIsNone(server.stable_ground_evidence([(THOR_LOG, text)],
                    {'sent_utc_ms': REPLAY_SENT_MS}, REPLAY_NOW_MS))

    def test_recent_fall_or_movement_cannot_be_hidden_by_good_thor_pair(self):
        for coordinates in ('123.5,-2000,-579', '123.5,-769,-579', '127,-768,-579'):
            text = self.fixture_logs() + position('261002 09:46:27', coordinates)
            with self.subTest(coordinates=coordinates):
                self.assertIsNone(server.stable_ground_evidence([(THOR_LOG, text)],
                    {'sent_utc_ms': REPLAY_SENT_MS}, stamp('261002 09:46:30')))

    def test_replay_still_requires_identity_current_route_freshness_and_command_time(self):
        logs = self.fixture_logs()
        for name, text, sent, now in (
            (THOR_LOG, logs.replace('THORHERO', 'OTHER'), REPLAY_SENT_MS, REPLAY_NOW_MS),
            (THOR_LOG, logs.replace('COHLOCAL', 'OTHER'), REPLAY_SENT_MS, REPLAY_NOW_MS),
            (THOR_LOG, logs.replace('City_01_01_1', 'City_02_01_1'), REPLAY_SENT_MS, REPLAY_NOW_MS),
            ('logs/foreign/entity.log', logs, REPLAY_SENT_MS, REPLAY_NOW_MS),
            (THOR_LOG, logs, stamp('261002 09:45:58'), REPLAY_NOW_MS),
            (THOR_LOG, logs, REPLAY_SENT_MS, stamp('261002 09:48:58')),
        ):
            with self.subTest(name=name, sent=sent, now=now):
                self.assertIsNone(server.stable_ground_evidence([(name, text)],
                    {'sent_utc_ms': sent}, now))

    def test_duplicate_routes_are_one_observation(self):
        single = position('261002 09:44:57', '123.5,-768,-579')
        local = single.replace('City_01_01_1:127.0.0.1:127.0.0.1', '0')
        self.assertIsNone(server.stable_ground_evidence(
            [(THOR_LOG, single), ('logs/mapserver/entity.log', local)],
            {'sent_utc_ms': REPLAY_SENT_MS}, REPLAY_NOW_MS))

    def server_with_below_zero_recovery(self):
        harness = reopen_tests.ReopenServerTests()
        self.addCleanup(harness.doCleanups)
        instance = harness.instance()
        instance.capture_baseline()
        instance.auth_id = 77
        instance.creation_report.update(instance.connection_metadata(), connected_on_atlas=True,
            client_pid=44, character_id=1, auth_id=77,
            client_ready_observed_utc_ms=stamp('261001 01:29:50'))
        receipt = dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
                       action='stuck', sent_utc_ms=stamp('261001 01:30:01'))
        (instance.owner.args.state/'character-relocation.json').write_text(json.dumps(receipt))
        logs = READY + position('261001 01:30:30', '123.5,-768,-579') \
            + position('261001 01:31:00', '123.5,-768,-579')
        instance.current_logs = Mock(return_value=[(LOG_NAME, logs)])
        instance.observe_connected_character()
        self.assertTrue(instance.creation_report['stable_ground_verified'])
        self.assertEqual(instance.creation_report['ground_evidence']['position'], THOR_POSITION)
        logout = dict(receipt, action='quittologin', sent_utc_ms=stamp('261001 01:31:20'))
        (instance.owner.args.state/'character-logout.json').write_text(json.dumps(logout))
        harness.clock.return_value = stamp('261001 01:31:40')/1000
        harness.position.update(posx=123.5, posy=-768, posz=-579)
        harness.rows['ents'][0]['logincount'] = 2
        return harness, instance, copy.deepcopy(harness.rows)

    def test_normal_save_accepts_recovered_negative_height_and_preserves_character(self):
        harness, instance, rows = self.server_with_below_zero_recovery()
        proof = instance.validate_saved_rows(rows, harness.inventory)
        self.assertEqual(proof['login_count'], 2)
        self.assertTrue(instance.creation_report['committed_safe_position_verified'])
        self.assertEqual(instance.creation_report['saved_position']['posy'], -768)
        self.assertEqual(proof['rows']['powers'], instance.baseline_snapshot['rows']['powers'])
        self.assertEqual(proof['rows']['costumeparts'], instance.baseline_snapshot['rows']['costumeparts'])

    def test_saved_fallback_or_mismatched_position_is_still_refused(self):
        for y in (-2000, -1999, -770.1):
            harness, instance, rows = self.server_with_below_zero_recovery()
            harness.position['posy'] = y
            with self.subTest(y=y), self.assertRaises(server.base.DiagnosticError):
                instance.validate_saved_rows(rows, harness.inventory)
            self.assertFalse(instance.creation_report.get('committed_safe_position_verified', False))

    def test_negative_height_recovery_releases_the_existing_relocated_event_once(self):
        harness, instance, rows = self.server_with_below_zero_recovery()
        diagnostic = guest.CharacterReopenDiagnostic.__new__(guest.CharacterReopenDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION)
        diagnostic.ctx = SimpleNamespace(report={'character_reopen': instance.creation_report}, event=Mock())
        diagnostic.connected_announced = True
        with patch.object(guest.creation.CharacterCreationDiagnostic, 'observe_console',
                          return_value=('', {'pid': 44}, {})):
            diagnostic.observe_console(); diagnostic.observe_console()
        diagnostic.ctx.event.assert_called_once()
        self.assertEqual(diagnostic.ctx.event.call_args.args[0], 'character_relocated')


if __name__ == '__main__':
    unittest.main()

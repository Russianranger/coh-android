"""Existing-player reopen, ordinary recovery and committed save boundaries."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_reopen_diagnostic as guest
import local_character_server as server
import client_startup_diagnostic as client
from test_character_server import fixture, SESSION
from test_character_guest import saved


def reopened(**changes):
    result = saved(character_id=1, before_character_id=1, baseline_character_id=1,
        existing_character_verified=True, reopen_verified=True, preserved_existing_identity=True,
        native_client_ready_observed=True, powers_preserved=True, costume_preserved=True,
        selected_rows_preserved=True, ordinary_stuck_observed=True, on_atlas_safe_position=True,
        stable_ground_verified=True, committed_safe_position_verified=True,
        recovery_requested=True, recovery_verified=True, committed_native_position_verified=True,
        before_login_count=1, login_count=2)
    result.update(changes)
    return result


def stamp(timestamp):
    return int(time.mktime(time.strptime(timestamp, '%y%m%d %H:%M:%S')) * 1000)


def position(timestamp, coordinates='106.45,-0.57,-114.45', *, name='THORHERO', account='COHLOCAL'):
    return timestamp + ' City_01_01_1:127.0.0.1:127.0.0.1 "' + name + ':' + account + '" 0 PeriodicInfo pos=<' \
        + coordinates + '> ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0\n'


LOG_NAME = 'logs/dbserver/entity_2026-10-01-01-00-00.log'
STUCK_MS = stamp('261001 01:30:01')
GROUND = position('261001 01:30:30') + position('261001 01:31:00')
READY = '261001 01:29:50 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 Connection:ResumeCharacter from 127.0.0.1:41001 AuthName "COHLOCAL" ExpLevel:1\n'
LOGOUT = '261001 01:31:30 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 [Disconnect:Logout timer expired] Science Class_Blaster, Level:1\n'


class ReopenProofTests(unittest.TestCase):
    def test_exact_existing_identity_current_ready_stuck_and_committed_save_required(self):
        self.assertTrue(guest.save_verified(reopened(), SESSION))
        for field in ('existing_character_verified', 'reopen_verified', 'preserved_existing_identity',
                'native_client_ready_observed', 'powers_preserved', 'costume_preserved',
                'recovery_verified', 'committed_native_position_verified',
                'selected_rows_preserved', 'ordinary_stuck_observed', 'on_atlas_safe_position',
                'stable_ground_verified', 'committed_safe_position_verified'):
            for value in (None, False, 1, 'true'):
                with self.subTest(field=field, value=value):
                    self.assertFalse(guest.save_verified(reopened(**{field: value}), SESSION))
        for field in ('character_id', 'before_character_id', 'baseline_character_id'):
            for value in (0, 2, True, '1'):
                self.assertFalse(guest.save_verified(reopened(**{field: value}), SESSION))
        for before, after in ((1, 1), (1, 3), (True, 2), (1, True), (0, 1), (2**31-1, 2**31)):
            self.assertFalse(guest.save_verified(reopened(before_login_count=before, login_count=after), SESSION))
        self.assertFalse(guest.save_verified(None, SESSION))

    def test_normal_save_needs_no_recovery_or_ground_claim(self):
        value = reopened(recovery_requested=False, recovery_verified=False,
            ordinary_stuck_observed=False, on_atlas_safe_position=False,
            stable_ground_verified=False, committed_safe_position_verified=False)
        self.assertTrue(guest.save_verified(value, SESSION))
        for field, invalid in (('recovery_requested', None), ('recovery_requested', 0),
                              ('recovery_verified', True), ('stable_ground_verified', True),
                              ('committed_native_position_verified', False)):
            with self.subTest(field=field, value=invalid):
                self.assertFalse(guest.save_verified(dict(value, **{field: invalid}), SESSION))

    def test_relocation_event_emits_once_only_for_current_connected_character(self):
        d = guest.CharacterReopenDiagnostic.__new__(guest.CharacterReopenDiagnostic)
        d.args = SimpleNamespace(session_id=SESSION)
        d.ctx = SimpleNamespace(report={'character_reopen': reopened(client_pid=44)}, event=Mock())
        d.connected_announced = True
        result = ('', {'pid': 44}, {})
        with patch.object(guest.creation.CharacterCreationDiagnostic, 'observe_console', return_value=result):
            d.observe_console(); d.observe_console()
        d.ctx.event.assert_called_once_with('character_relocated', session_id=SESSION, client_pid=44,
            character_id=1, name='THORHERO', account='COHLOCAL', map_id=1,
            recovery_requested=True, recovery_verified=True,
            ordinary_stuck_observed=True, on_atlas_safe_position=True, stable_ground_verified=True)
        d.relocated_announced = False
        for field, value in (('client_pid', 45), ('session_id', 'f'*32), ('ordinary_stuck_observed', False)):
            d.ctx.report['character_reopen'] = reopened(client_pid=44, **{field: value}) if field != 'client_pid' \
                else reopened(client_pid=value)
            with patch.object(guest.creation.CharacterCreationDiagnostic, 'observe_console', return_value=result), \
                    self.assertRaises(server.base.DiagnosticError):
                d.observe_console()


class NativeGroundTests(unittest.TestCase):
    def delivery(self):
        return {'sent_utc_ms': STUCK_MS}

    def test_physics_samples_require_current_route_identity_after_command_and_distinct_times(self):
        proof = server.stable_ground_evidence([(LOG_NAME, GROUND)], self.delivery(), stamp('261001 01:31:15'))
        self.assertTrue(proof['verified']); self.assertEqual(proof['elapsed_ms'], 30000)
        self.assertEqual(proof['position'], [106.45, -.57, -114.45])
        self.assertFalse(proof['full_collision_geometry_verified'])
        for name, raw in [(LOG_NAME, position('261001 01:30:00') + position('261001 01:30:30')),
                (LOG_NAME, position('261001 01:30:30') * 2),
                (LOG_NAME, position('261001 01:30:30') + position('261001 01:30:40')),
                (LOG_NAME, GROUND.replace('THORHERO', 'OTHER')),
                (LOG_NAME, GROUND.replace('COHLOCAL', 'OTHER')),
                (LOG_NAME, GROUND.replace('City_01_01_1', 'City_02_01_1')),
                ('logs/other/entity.log', GROUND), (LOG_NAME, GROUND.rstrip('\n'))]:
            with self.subTest(name=name, raw=raw):
                self.assertIsNone(server.stable_ground_evidence([(name, raw)], self.delivery(), stamp('261001 01:31:15')))
        self.assertIsNone(server.stable_ground_evidence([(LOG_NAME, GROUND)], self.delivery(), stamp('261001 01:34:01')))

    def test_latest_falling_or_moving_position_cannot_be_hidden_by_older_good_pair(self):
        for coordinates in ('106.45,-2000,-114.45', '106.45,-1.58,-114.45', '110,-0.57,-114.45',
                            '106.45,10001,-114.45'):
            logs = GROUND + position('261001 01:31:30', coordinates)
            with self.subTest(coordinates=coordinates):
                self.assertIsNone(server.stable_ground_evidence([(LOG_NAME, logs)], self.delivery(), stamp('261001 01:31:45')))
        with self.assertRaises(server.base.DiagnosticError):
            server.native_position_records([(LOG_NAME, position('261001 01:30:30', '1e999,0,0'))])
        with self.assertRaises(server.base.DiagnosticError):
            server.native_position_records([(LOG_NAME, GROUND + position('261001 01:31:00', '1,0,1'))])


class WorldPayloadCapTests(unittest.TestCase):
    def test_only_exact_world_archive_gets_larger_cap_and_still_requires_its_full_pin(self):
        digest = 'a' * 64
        for filename, size, accepted in [('atlas-world-supplement.zip', 200*1024**2, True),
                ('atlas-world-supplement.zip', 256*1024**2 + 1, False),
                ('unrelated.zip', 128*1024**2 + 1, False),
                ('atlas-world-supplement.zip.tmp', 200*1024**2, False)]:
            path = Mock(); path.is_file.return_value = True; path.is_symlink.return_value = False
            path.stat.return_value.st_size = size
            assets = Mock(); assets.__truediv__ = Mock(return_value=path)
            manifest = {'format': 1, 'scope': client.SCOPE,
                        'files': {filename: {'sha256': digest, 'bytes': size}}}
            with patch.object(client, 'read_json', return_value=manifest), patch.object(client, 'REQUIRED', set()), \
                    patch.object(client.base, 'file_hash', return_value=digest), patch.object(client.base, 'verify_pe32'):
                with self.subTest(filename=filename, size=size):
                    if accepted: self.assertEqual(client.verify_assets(assets), {filename: digest})
                    else:
                        with self.assertRaises(server.base.DiagnosticError): client.verify_assets(assets)


class ReopenServerTests(unittest.TestCase):
    def instance(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        state = Path(directory)
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}, event=Mock()), root=state,
                                args=SimpleNamespace(session_id=SESSION, state=state))
        d = server.LocalCharacterReopenServer(owner)
        rows, _, attributes = fixture()
        for values in rows.values():
            for row in values: row['containerid'] = 1
        inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
        d.schema = {'expected_attributes': attributes}
        d.inventory = Mock(return_value=inventory)
        d.sql = Mock(return_value='77|COHLOCAL')
        self.rows, self.inventory = rows, inventory
        self.position = {'containerid': 1, 'mapid': 1, 'staticmapid': 1,
                         'posx': 106.45, 'posy': -2000, 'posz': -114.45}
        d.sql_rows = Mock(side_effect=lambda table, fields, *_: copy.deepcopy(self.position)
            if fields == ('containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz') else copy.deepcopy(self.rows[table]))
        # Position SQL is a list, as ordinary SELECT evidence always is.
        d.sql_rows.side_effect = lambda table, fields, *_: [copy.deepcopy(self.position)] \
            if fields == ('containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz') else copy.deepcopy(self.rows[table])
        self.clock = self.enterContext(patch.object(server.time, 'time', return_value=stamp('261001 01:31:15')/1000))
        return d

    def test_missing_or_uninitialized_profile_never_initializes_or_creates_database(self):
        d = self.instance()
        with patch.object(server.LocalCharacterServer, 'initialize') as parent:
            with self.assertRaises(server.base.DiagnosticError): d.initialize()
            d.profile.mkdir()
            record = dict(server.login.PROFILE_IDENTITY, initialized=False)
            (d.profile/'profile.json').write_text(json.dumps(record))
            with self.assertRaises(server.base.DiagnosticError): d.initialize()
            parent.assert_not_called()

    def test_baseline_keeps_original_rows_identity_and_bad_saved_position_without_modifying_sql(self):
        d = self.instance(); before = copy.deepcopy(self.rows)
        d.capture_baseline()
        self.assertEqual(self.rows, before); self.assertEqual(d.baseline_snapshot['identity']['containerid'], 1)
        self.assertEqual(d.creation_report['baseline']['saved_position']['posy'], -2000)
        self.assertEqual(d.creation_report['baseline']['login_count'], 1)
        self.assertTrue(d.creation_report['existing_character_verified'])
        self.assertFalse(d.creation_report['sql_game_mutations_performed'])
        self.assertTrue(d.sql.call_args.args[0].startswith('SELECT'))
        self.assertEqual(d.sql.call_count, 1)

    def test_baseline_accepts_observed_first_creation_null_active_map_and_keeps_saved_atlas_position(self):
        d = self.instance()
        self.position.update(mapid=None, posx=106.454605, posy=.251066, posz=-114.45343)
        expected = copy.deepcopy(self.position)
        before = copy.deepcopy(self.rows)
        d.capture_baseline()
        self.assertEqual(d.creation_report['baseline']['saved_position'], expected)
        self.assertEqual(self.position, expected)
        self.assertEqual(self.rows, before)
        self.assertTrue(d.creation_report['existing_character_verified'])
        self.assertFalse(d.creation_report['sql_game_mutations_performed'])
        self.assertEqual(d.sql.call_count, 1)
        self.assertTrue(d.sql.call_args.args[0].startswith('SELECT'))
        with self.assertRaises(server.base.DiagnosticError): d.character_position()

    def test_baseline_still_rejects_other_maps_missing_static_map_bool_ids_and_invalid_positions(self):
        changes = [('mapid', value) for value in (0, 2, True, '1')]
        changes += [('staticmapid', value) for value in (None, 0, 2, True, '1')]
        changes += [('containerid', value) for value in (None, 2, True, '1')]
        changes += [('posy', value) for value in (None, True, float('nan'), float('inf'), 1000001)]
        for field, value in changes:
            d = self.instance(); self.position['mapid'] = None; self.position[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(server.base.DiagnosticError):
                d.capture_baseline()
            self.assertFalse(d.creation_report['existing_character_verified'])

    def test_save_requires_assigned_atlas_map_after_accepting_null_first_creation_baseline(self):
        d = self.instance(); self.position['mapid'] = None
        rows = self.prepare_ground_and_logout(d)
        for active_map in (None, 0, 2, True, '1'):
            self.position['mapid'] = active_map
            with self.subTest(active_map=active_map), self.assertRaises(server.base.DiagnosticError):
                d.validate_saved_rows(rows, self.inventory)
            self.assertFalse(d.creation_report.get('committed_safe_position_verified', False))
        self.position['mapid'] = 1
        self.assertEqual(d.validate_saved_rows(rows, self.inventory)['login_count'], 2)
        self.assertTrue(d.creation_report['committed_safe_position_verified'])

    def test_reopen_refuses_absent_duplicate_changed_or_additional_local_character(self):
        for change in ('absent', 'duplicate', 'id', 'name', 'account', 'extra'):
            d = self.instance(); values = copy.deepcopy(self.inventory)
            if change == 'absent': values = []
            if change == 'duplicate': values *= 2
            if change == 'id': values[0]['containerid'] = 2
            if change == 'name': values[0]['name'] = 'OTHER'
            if change == 'account': values[0]['authname'] = 'OTHER'
            if change == 'extra': values.append(dict(values[0], containerid=2, name='OTHER'))
            d.inventory.return_value = values
            with self.subTest(change=change), self.assertRaises(server.base.DiagnosticError): d.capture_baseline()
            self.assertFalse(d.creation_report['existing_character_verified'])

    def prepare_ground_and_logout(self, d):
        d.capture_baseline(); d.auth_id = 77
        d.creation_report.update(d.connection_metadata(), connected_on_atlas=True, client_pid=44,
            character_id=1, auth_id=77, client_ready_observed_utc_ms=stamp('261001 01:29:50'))
        stuck = dict(format=1, session_id=SESSION, client_pid=44, character_id=1, action='stuck', sent_utc_ms=STUCK_MS)
        (d.owner.args.state/'character-relocation.json').write_text(json.dumps(stuck))
        d.current_logs = Mock(return_value=[(LOG_NAME, READY + GROUND)])
        d.observe_connected_character()
        self.assertTrue(d.creation_report['stable_ground_verified'])
        logout = dict(stuck, action='quittologin', sent_utc_ms=stamp('261001 01:31:20'))
        (d.owner.args.state/'character-logout.json').write_text(json.dumps(logout))
        self.clock.return_value = stamp('261001 01:31:40')/1000
        self.position['posy'] = -.57
        self.rows['ents'][0]['logincount'] = 2
        return copy.deepcopy(self.rows)

    def test_normal_reopen_save_preserves_rows_and_commits_native_recovered_position(self):
        d = self.instance(); rows = self.prepare_ground_and_logout(d)
        snapshot = d.validate_saved_rows(rows, self.inventory)
        self.assertEqual(snapshot['login_count'], 2)
        self.assertTrue(d.creation_report['committed_safe_position_verified'])
        metadata = d.saved_metadata(snapshot)
        self.assertTrue(metadata['powers_preserved']); self.assertTrue(metadata['costume_preserved'])
        self.assertEqual(metadata['before_login_count'], 1)

    def prepare_normal_logout(self, d):
        d.capture_baseline(); d.auth_id = 77
        d.creation_report.update(d.connection_metadata(), connected_on_atlas=True, client_pid=44,
            character_id=1, auth_id=77, client_ready_observed_utc_ms=stamp('261001 01:29:50'))
        # One actual position is enough for ordinary save: no stable pair or
        # recovery command is manufactured. City Hall is below zero altitude.
        raw = position('261001 01:31:00', '106.45,-768,-114.45')
        d.current_logs = Mock(return_value=[(LOG_NAME, READY + raw)])
        d.observe_connected_character()
        logout = dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
                      action='quittologin', sent_utc_ms=stamp('261001 01:31:20'))
        (d.owner.args.state/'character-logout.json').write_text(json.dumps(logout))
        self.clock.return_value = stamp('261001 01:31:40')/1000
        self.position['posy'] = -768
        self.rows['ents'][0]['logincount'] = 2
        return copy.deepcopy(self.rows)

    def test_ordinary_save_without_stuck_keeps_native_position_and_existing_rows(self):
        d = self.instance(); rows = self.prepare_normal_logout(d)
        result = d.validate_saved_rows(rows, self.inventory)
        self.assertEqual(result['login_count'], 2)
        self.assertTrue(d.creation_report['committed_native_position_verified'])
        self.assertFalse(d.creation_report['recovery_requested'])
        self.assertFalse(d.creation_report['recovery_verified'])
        self.assertFalse(d.creation_report['stable_ground_verified'])
        self.assertFalse(d.creation_report.get('committed_safe_position_verified', False))
        self.assertEqual(d.creation_report['saved_position']['posy'], -768)

    def test_normal_save_rejects_missing_stale_fall_floor_mismatched_or_foreign_native_position(self):
        for failure in ('missing', 'stale', 'future', 'floor', 'mismatch', 'identity', 'powers', 'map'):
            d = self.instance(); rows = self.prepare_normal_logout(d)
            if failure == 'missing': d.current_logs.return_value = [(LOG_NAME, READY)]
            if failure == 'stale': d.current_logs.return_value = [(LOG_NAME, READY + position('261001 01:29:00'))]
            if failure == 'future': d.current_logs.return_value = [(LOG_NAME, READY + position('261001 01:31:25'))]
            if failure == 'floor': d.current_logs.return_value = [(LOG_NAME, READY + position('261001 01:31:00', '106.45,-2000,-114.45'))]
            if failure == 'mismatch': self.position['posx'] += 10
            if failure == 'identity': d.current_logs.return_value = [(LOG_NAME, READY + position('261001 01:31:00', name='OTHER'))]
            if failure == 'powers': rows['powers'][0]['uniqueid'] += 1
            if failure == 'map': self.position['mapid'] = 2
            with self.subTest(failure=failure), self.assertRaises(server.base.DiagnosticError):
                d.validate_saved_rows(rows, self.inventory)
            self.assertFalse(d.creation_report['committed_native_position_verified'])

    def test_explicit_recovery_cannot_fall_back_to_normal_save_when_unverified_or_receipt_replayed(self):
        d = self.instance(); rows = self.prepare_normal_logout(d)
        receipt = dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
                       action='stuck', sent_utc_ms=STUCK_MS)
        path = d.owner.args.state/'character-relocation.json'
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(server.base.DiagnosticError, 'requested ordinary recovery'):
            d.validate_saved_rows(rows, self.inventory)
        self.assertTrue(d.creation_report['recovery_requested'])
        self.assertFalse(d.creation_report['committed_native_position_verified'])
        receipt['session_id'] = 'f' * 32; path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(server.base.DiagnosticError, 'delivery does not match'):
            d.validate_saved_rows(rows, self.inventory)

    def test_optional_contact_export_failure_preserves_save_proof_and_never_adds_sql(self):
        d = self.instance(); rows = self.prepare_normal_logout(d)
        d.validate_saved_rows(rows, self.inventory)
        accepted = copy.deepcopy(d.creation_report)
        d.current_logs.side_effect = OSError('read failed')
        target = d.owner.args.state / 'export'; target.mkdir()
        sql_calls = d.sql.call_count
        with patch.object(server.LocalCharacterServer, 'collect'):
            d.collect(target)
        self.assertEqual(d.creation_report, accepted)
        self.assertEqual(d.sql.call_count, sql_calls)
        self.assertEqual(d.ctx.report['stationary_contact']['status'], 'unavailable')
        self.assertEqual(d.ctx.report['stationary_contact']['records'], [])
        self.assertTrue((target / 'character-reopen-before-snapshot.json').is_file())
        self.assertIn('stationary_contact_evidence.py', guest.REQUIRED)
        self.assertNotIn('stationary_contact_evidence.py', guest.creation.REQUIRED)

    @patch.object(server.progress, 'compare_records')
    def test_full_normal_logout_pipeline_without_recovery_retains_committed_identity_and_native_position(self, _compare):
        d = self.instance(); self.prepare_normal_logout(d)
        d.health = Mock()
        d.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        d.query = Mock(return_value='invalid container request\n')
        d.current_logs.return_value[0] = (LOG_NAME, d.current_logs.return_value[0][1] + LOGOUT)
        proof = d.character_evidence()
        self.assertTrue(guest.save_verified(proof, SESSION))
        self.assertTrue(proof['disconnected_before_sql'])
        self.assertFalse(proof['recovery_requested'])
        self.assertEqual(proof['table_sha256']['powers'], proof['baseline']['table_sha256']['powers'])

    @patch.object(server.progress, 'compare_records')
    def test_full_ordinary_logout_pipeline_binds_native_connection_recovery_and_saved_identity(self, _compare):
        d = self.instance(); self.prepare_ground_and_logout(d)
        d.health = Mock()
        d.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        d.query = Mock(return_value='invalid container request\n')
        d.current_logs.return_value = [(LOG_NAME, READY + GROUND + LOGOUT)]
        proof = d.character_evidence()
        self.assertTrue(guest.save_verified(proof, SESSION))
        self.assertEqual(proof['character_id'], proof['before_character_id'])
        self.assertEqual(proof['row_counts'], proof['baseline']['row_counts'])
        self.assertEqual(proof['table_sha256']['powers'], proof['baseline']['table_sha256']['powers'])
        self.assertEqual(proof['table_sha256']['costumeparts'], proof['baseline']['table_sha256']['costumeparts'])
        self.assertEqual(proof['logout_delivery']['action'], 'quittologin')
        self.assertEqual(proof['relocation_delivery']['action'], 'stuck')
        self.assertFalse(proof['forced_stop_before_save'])
        self.assertEqual(d.character_evidence(), proof)

    def test_save_rejects_changed_power_costume_class_missing_recovery_and_bad_saved_position(self):
        for failure in ('power', 'costume', 'class', 'position', 'ground', 'early_logout', 'inventory', 'count'):
            d = self.instance(); rows = self.prepare_ground_and_logout(d)
            if failure == 'power': rows['powers'][0]['uniqueid'] += 1
            if failure == 'costume': rows['costumeparts'][0]['color1'] += 1
            if failure == 'class': rows['ents'][0]['level'] += 1
            if failure == 'position': self.position['posy'] = -2000
            if failure == 'ground': d.creation_report['stable_ground_verified'] = False
            if failure == 'early_logout':
                path = d.owner.args.state/'character-logout.json'; receipt = json.loads(path.read_text())
                receipt['sent_utc_ms'] = stamp('261001 01:31:14'); path.write_text(json.dumps(receipt))
            values = self.inventory if failure != 'inventory' else []
            if failure == 'count': rows['ents'][0]['logincount'] = 1
            with self.subTest(failure=failure), self.assertRaises(server.base.DiagnosticError):
                d.validate_saved_rows(rows, values)


if __name__ == '__main__': unittest.main()

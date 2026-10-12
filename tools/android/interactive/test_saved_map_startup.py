"""Saved-location production-method regressions; native/Thor gameplay remains separate.

SQL and native launch/readiness boundaries are controlled fixtures here. Actual
production baseline, command construction, progress parsing, map routing, save
validation and failure guards execute without mutating any character rows.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_zoning as zoning
import local_character_server as server
from test_character_server import fixture, SESSION
from test_character_reopen_guest import READY, LOGOUT, LOG_NAME, position, stamp
import test_character_monorail as station


def status(map_id, ready=True):
    world = zoning.MAPS[map_id]['world']
    return f'{map_id} maps/City_Zones/{world}/{world}.txt ' + (
        f'S: 1 / 2 Ip: 127.0.0.1:{zoning.MAPS[map_id]["port"]} Mem: 100\n' if ready
        else 'NotReady 1 (Not started) Info\n')


def progress_bytes(pid=55, tid=56, sequence=2, completed=1):
    p = server.progress
    raw = p.HEADER.pack(b'COHMAP1\0', 1, p.RECORD_BYTES, pid, tid, sequence, 37,
                        completed, completed, 0, 37) + bytes(80)
    return raw + bytes(p.MAPPING_BYTES - p.RECORD_BYTES)


class SavedMapStartupTests(unittest.TestCase):
    def instance(self, map_id=5, active=None):
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-saved-map-')))
        state = root / 'state'; state.mkdir()
        ctx = SimpleNamespace(report={}, event=Mock(), stage=Mock(), passed=Mock(), check=Mock(),
                              deadline=1000, start=Mock())
        owner = SimpleNamespace(ctx=ctx, root=root, wine_env={},
            args=SimpleNamespace(session_id=SESSION, state=state, wine='/usr/bin/wine'))
        value = zoning.LocalCharacterZoningServer(owner)
        value.monorail_qualified = True
        value.runtime = root / 'atlas-runtime'; value.runtime.mkdir()
        value.sample_startup_observation = Mock()
        rows, _, attributes = fixture()
        for values in rows.values():
            for row in values: row['containerid'] = 1
        self.rows = rows
        self.inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
        self.saved_position = dict(containerid=1, mapid=active, staticmapid=map_id,
                                  posx=12.5, posy=-20.0, posz=40.25)
        value.schema = {'expected_attributes': attributes}
        value.inventory = Mock(side_effect=lambda: copy.deepcopy(self.inventory))
        value.sql = Mock(return_value='77|COHLOCAL')
        def selected(table, fields, *_):
            if fields == ('containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'):
                return [copy.deepcopy(self.saved_position)]
            return copy.deepcopy(self.rows[table])
        value.sql_rows = Mock(side_effect=selected)
        self.value = value
        return value

    def baseline(self, value):
        before = copy.deepcopy((self.rows, self.inventory, self.saved_position))
        value.capture_baseline()
        self.assertEqual((self.rows, self.inventory, self.saved_position), before)
        self.assertTrue(all(call.args[0].startswith('SELECT') for call in value.sql.call_args_list))

    def fake_launch(self, value):
        kings = value.runtime.with_name('kings-runtime'); kings.mkdir(exist_ok=True)
        value.prepare_kings_row_runtime = Mock(return_value={'runtime': kings,
            'graph': {'verified': True, 'map_id': 5}})
        process = Mock(); process.poll.return_value = None; process.pid = 500
        child = SimpleNamespace(process=process, output=bytearray(), overflow=False)
        def start(label, argv, **kwargs):
            process.args = argv
            map_id = int(argv[argv.index('-map_id') + 1])
            path = value.runtime / f'character-zoning-{map_id}-progress.bin'
            path.write_bytes(progress_bytes())
            return child
        value.ctx.start.side_effect = start
        return child, kings

    def test_kings_and_atlas_authoritative_baselines_keep_identity_rows_and_position(self):
        for map_id in (5, 1, 101):
            for assigned in (None, map_id):
                with self.subTest(map_id=map_id, mapid=assigned):
                    value = self.instance(map_id, assigned); self.baseline(value)
                    self.assertEqual(value.active_map_id, map_id)
                    self.assertEqual(value.creation_report['baseline']['saved_position'], self.saved_position)
                    self.assertEqual(value.baseline_snapshot['rows'], self.rows)
                    saved = value.zoning_report['saved_startup']
                    self.assertEqual((saved['map_id'], saved['port'], saved['world']),
                        (map_id, zoning.MAPS[map_id]['port'], zoning.MAPS[map_id]['world']))
                    self.assertFalse(saved['native_ready_verified'])
                    self.assertFalse(saved['character_world_entry_verified'])
                    event = value.ctx.event.call_args.kwargs
                    self.assertEqual(event['map_id'], map_id)
                    self.assertFalse(event['sql_game_mutations_performed'])

    def test_invalid_identity_or_saved_assignment_never_launches_or_mutates(self):
        changes = ({'staticmapid': 2}, {'staticmapid': True}, {'mapid': 1}, {'mapid': 0},
                   {'mapid': True}, {'posy': float('nan')}, {'posx': float('inf')})
        for changed in changes:
            value = self.instance(); self.saved_position.update(changed)
            before = copy.deepcopy(self.rows)
            with self.subTest(changed=changed), self.assertRaises(server.base.DiagnosticError):
                value.capture_baseline()
            self.assertEqual(self.rows, before); value.ctx.start.assert_not_called()
            self.assertFalse(value.creation_report['existing_character_verified'])
        value = self.instance(); self.inventory[0]['authname'] = 'OTHER'
        with self.assertRaises(server.base.DiagnosticError): value.capture_baseline()
        value.sql.assert_not_called(); value.ctx.start.assert_not_called()

    def test_kings_requires_authenticated_zone_package_before_map_selection(self):
        value = self.instance(); value.monorail_qualified = False
        with self.assertRaises(server.base.DiagnosticError): value.capture_baseline()
        self.assertEqual(value.active_map_id, 1)
        value.ctx.start.assert_not_called()

    def test_direct_kings_launch_uses_only_map5_runtime_port_progress_and_graph(self):
        value = self.instance(); self.baseline(value); child, kings = self.fake_launch(value)
        value.query = Mock(side_effect=[status(5, False), status(5)])
        with patch.object(zoning.time, 'monotonic', return_value=100), \
                patch.object(zoning.character.game, 'check_game_port') as port:
            value.start_map()
        port.assert_called_once_with(7003, zoning.socket.SOCK_DGRAM)
        value.prepare_kings_row_runtime.assert_called_once()
        value.ctx.start.assert_called_once()
        label, argv = value.ctx.start.call_args.args
        self.assertEqual(label, 'local-character-zoning-5')
        self.assertIn('--chdir=' + str(kings), argv)
        self.assertIn(server.base.windows_path(kings / 'MapServer.exe'), argv)
        self.assertEqual(argv[argv.index('-map_id') + 1], '5')
        self.assertEqual(argv[argv.index('-udp') + 1], '7003')
        self.assertEqual(set(value.maps), {5})
        self.assertIs(value.map_process, child)
        self.assertEqual(value.map_progress_path.name, 'character-zoning-5-progress.bin')
        self.assertTrue(value.creation_report['map_startup_guard']['passed'])
        self.assertEqual(value.creation_report['map_startup_guard']['protocol']['map_id'], 5)
        self.assertIn('before', value.creation_report['map_startup_guard'])
        self.assertTrue(value.zoning_report['saved_startup']['native_ready_verified'])
        self.assertFalse(value.zoning_report['saved_startup']['character_world_entry_verified'])
        messages = [call.kwargs.get('message', '') for call in value.ctx.event.call_args_list]
        self.assertTrue(any("King's Row" in message for message in messages))
        self.assertFalse(any('Preparing Atlas Park' in message for message in messages))

    def test_missing_or_wrong_kings_graph_fails_before_native_launch(self):
        for graph in ({}, {'verified': False, 'map_id': 5}, {'verified': True, 'map_id': 1}):
            value = self.instance(); self.baseline(value); self.fake_launch(value)
            value.prepare_kings_row_runtime.return_value['graph'] = graph
            value.query = Mock(return_value=status(5, False))
            with self.subTest(graph=graph), self.assertRaises(server.base.DiagnosticError): value.start_map()
            value.ctx.start.assert_not_called()
            self.assertEqual(self.saved_position['staticmapid'], 5)

    def test_owned_baseline_cannot_adopt_foreign_or_missing_mapserver(self):
        for baseline in (status(5), 'invalid container request\n', status(1, False)):
            value = self.instance(); self.baseline(value)
            value.query = Mock(return_value=baseline)
            with self.subTest(baseline=baseline), self.assertRaises(server.base.DiagnosticError): value.start_map()
            value.ctx.start.assert_not_called()
            self.assertEqual(value.active_map_id, 5)

    def test_wrong_native_world_or_port_does_not_become_readiness_or_world_entry(self):
        for reply in (status(5).replace('City_01_02', 'City_01_01'), status(5).replace(':7003', ':7001')):
            value = self.instance(); self.baseline(value); self.fake_launch(value)
            value.query = Mock(side_effect=[status(5, False), reply])
            with patch.object(zoning.time, 'monotonic', return_value=100), \
                    patch.object(zoning.character.game, 'check_game_port'), \
                    self.subTest(reply=reply), self.assertRaises(server.base.DiagnosticError): value.start_map()
            self.assertFalse(value.zoning_report['saved_startup']['native_ready_verified'])
            self.assertFalse(value.zoning_report['saved_startup']['character_world_entry_verified'])
            self.assertEqual(self.saved_position['staticmapid'], 5)

    def test_interrupted_and_timed_out_startup_preserve_saved_kings_location(self):
        for interrupted in (True, False):
            value = self.instance(); self.baseline(value); self.fake_launch(value)
            value.query = Mock(return_value=status(5, False))
            if interrupted: value.ctx.check.side_effect = server.base.Cancelled('interrupted')
            value.ctx.deadline = 100
            with patch.object(zoning.time, 'monotonic', return_value=100), \
                    patch.object(zoning.character.game, 'check_game_port'), \
                    self.subTest(interrupted=interrupted), self.assertRaises(server.base.DiagnosticError): value.start_map()
            self.assertEqual(self.saved_position['staticmapid'], 5)
            self.assertFalse(value.zoning_report['saved_startup']['native_ready_verified'])
            self.assertTrue(all(call.args[0].startswith('SELECT') for call in value.sql.call_args_list))

    def test_atlas_reopen_uses_only_retained_atlas_launch_and_environment(self):
        value = self.instance(1); self.baseline(value)
        environment = value.owner.wine_env
        def started(_):
            value.map_process = Mock(); value.map_progress_path = value.runtime / 'atlas-progress.bin'
            value.map_previous = None; value.map_launch_utc_ms = 1000
        with patch.object(server.LocalCharacterReopenServer, 'start_map', autospec=True, side_effect=started) as atlas:
            value.start_map()
        atlas.assert_called_once_with(value)
        self.assertIs(value.owner.wine_env, environment)
        self.assertEqual(set(value.maps), {1})
        value.ctx.start.assert_not_called()

    def test_kings_ready_and_character_connection_are_independent(self):
        value = self.instance(); self.baseline(value)
        self.assertFalse(value.connected_status(dict(loaded=True, connected=True, in_map_transfer=False,
            map_id=5, static_map_id=5, address='192.168.1.1')))
        with self.assertRaises(server.base.DiagnosticError): value.connected_status(dict(
            loaded=True, connected=True, in_map_transfer=False, map_id=1, static_map_id=1))
        self.assertFalse(value.zoning_report['saved_startup']['character_world_entry_verified'])
        self.assertTrue(value.connected_status(dict(loaded=True, connected=True, in_map_transfer=False,
            map_id=5, static_map_id=5, address='127.0.0.1')))
        metadata = value.connection_metadata()
        self.assertTrue(metadata['preserved_existing_identity'])
        self.assertTrue(value.zoning_report['saved_startup']['character_world_entry_verified'])

    def test_ordinary_kings_save_preserves_location_identity_powers_and_costume_then_reopens(self):
        value = self.instance(); self.baseline(value); value.auth_id = 77
        ready_ms, logout_ms, now_ms = map(stamp, ('261001 01:29:50', '261001 01:31:20', '261001 01:31:40'))
        value.creation_report.update(value.connection_metadata(), connected_on_atlas=True, client_pid=44,
            character_id=1, auth_id=77, client_ready_observed_utc_ms=ready_ms)
        value.ready_floor_ms = ready_ms - 999
        value.native_positions = Mock(return_value=[{'utc_ms': stamp('261001 01:31:00'),
            'position': [12.5, -20, 40.25]}])
        raw = (READY + position('261001 01:31:00', '12.5,-20,40.25') + LOGOUT).replace('City_01_01_1', 'City_01_02_1')
        value.current_logs = Mock(return_value=[(LOG_NAME, raw)])
        delivery = dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
                        action='quittologin', sent_utc_ms=logout_ms)
        (value.owner.args.state / 'character-logout.json').write_text(json.dumps(delivery))
        before = copy.deepcopy(self.rows)
        self.rows['ents'][0]['logincount'] = 2; self.saved_position['mapid'] = 5
        with patch.object(server.time, 'time', return_value=now_ms / 1000):
            snapshot = value.validate_saved_rows(copy.deepcopy(self.rows), self.inventory)
        self.assertEqual(value.creation_report['saved_position']['staticmapid'], 5)
        self.assertEqual(value.creation_report['saved_position']['posy'], -20)
        self.assertTrue(value.creation_report['committed_native_position_verified'])
        metadata = value.saved_metadata(snapshot)
        self.assertTrue(metadata['powers_preserved']); self.assertTrue(metadata['costume_preserved'])
        self.assertEqual(metadata['map_id'], 5)
        self.assertEqual(self.rows['powers'], before['powers'])
        self.assertEqual(self.rows['costumeparts'], before['costumeparts'])
        value.capture_baseline()
        self.assertEqual(value.active_map_id, 5)
        self.assertEqual(value.zoning_report['saved_startup']['saved_position'], self.saved_position)
        self.assertTrue(all(call.args[0].startswith('SELECT') for call in value.sql.call_args_list))

    def test_connected_save_cannot_use_unassigned_or_changed_destination(self):
        value = self.instance(); self.baseline(value)
        for changes in ({'mapid': None}, {'mapid': 1}, {'mapid': 5, 'staticmapid': 1}):
            self.saved_position.update(changes)
            with self.subTest(changes=changes), self.assertRaises(server.base.DiagnosticError): value.character_position()
        self.assertEqual(value.active_map_id, 5)

    def test_kings_to_atlas_native_station_request_is_reverse_route(self):
        value = station.StationTests.instance(self)
        value.active_map_id = 5; value.maps = {5: {'ready': True}}
        native = station.StationTests.native(self, map_id=5, target=1)
        value.map_native_events.return_value = [native]
        value._observe_station(station.old.NOW)
        self.assertEqual((value.pending['from_map_id'], value.pending['to_map_id']), (5, 1))
        value._query_start.assert_called_once_with(['-getstatus', '1', '1'], 'baseline')
        self.assertEqual(value.zoning_report['events'][-1]['travel_method'], 'stock_monorail')
        value.pending.update(phase='ready', ready_utc_ms=station.old.NOW,
                             departure_deadline_utc_ms=station.old.NOW + 10000)
        value._authorize_station(native)
        self.assertEqual((value.runtime / 'monorail-5-reply.txt').read_text(), zoning.monorail_events.reply(native))
        departure = station.StationTests.native(self, 'station_departure', 2,
            map_id=5, target=1, utc_ms=station.old.NOW + 50)
        value.map_native_events.return_value = [native, departure]
        value._observe_station(station.old.NOW + 100)
        self.assertEqual(value.pending['phase'], 'arrival')
        value._activate = Mock(side_effect=lambda map_id: setattr(value, 'active_map_id', map_id))
        value.map_native_events.return_value = [{'kind': 'ready', 'utc_ms': station.old.NOW + 200,
            'line_sha256': 'f' * 64, 'map_id': 1}]
        value._observe_arrival(None, station.old.NOW + 250)
        value._query_start.assert_called_with(['-getstatus', '1', '1'], 'arrival_map')
        value._observe_arrival(('arrival_map', status(1)), station.old.NOW + 300)
        value._query_start.assert_called_with(['-getstatus', '3', '1'], 'arrival_final_character')
        value._observe_arrival(('arrival_final_character',
            '1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1\n'), station.old.NOW + 400)
        self.assertEqual(value.active_map_id, 1)
        self.assertEqual(value.zoning_report['transfers'][0]['from_map_id'], 5)
        self.assertEqual(value.zoning_report['transfers'][0]['to_map_id'], 1)
        self.assertEqual(value.zoning_report['transfers'][0]['native_ready']['map_id'], 1)

    def test_cold_and_authenticated_reused_graph_keep_same_saved_kings_destination(self):
        # Cache construction/verification is separately executed by full asset
        # preflight. Here both authenticated preparation results cross the real
        # saved-map launch boundary and cannot alter the authoritative selection.
        for graph_status in ('installed_verified_graph', 'reused_verified_graph'):
            value = self.instance(); self.baseline(value); self.fake_launch(value)
            value.prepare_kings_row_runtime.return_value['graph']['status'] = graph_status
            value.query = Mock(side_effect=[status(5, False), status(5)])
            with patch.object(zoning.time, 'monotonic', return_value=100), \
                    patch.object(zoning.character.game, 'check_game_port'):
                value.start_map()
            self.assertEqual(value.active_map_id, 5)
            self.assertEqual(set(value.maps), {5})
            self.assertEqual(value.zoning_report['saved_startup']['saved_position'], self.saved_position)
            self.assertEqual(value.zoning_report['saved_startup']['native_maps_started'], [5])


if __name__ == '__main__':
    unittest.main()

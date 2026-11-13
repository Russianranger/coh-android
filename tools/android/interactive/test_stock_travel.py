"""The game's own zone travel: requested zones started with their cookie, two servers, arrival."""
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_zoning as zoning
import external_map_supervisor as supervisor
import zone_travel

SESSION = 'a' * 32
COMMAND = '.\\mapserver.exe -db 127.0.0.1 -udp -1 -map_id {map_id} -launcher -cookie {cookie} -aggrocap 17 -locale 0'


def record(map_id, cookie, sequence):
    return {'format': 1, 'sequence': sequence, 'map_id': map_id, 'cookie': cookie, 'base_map_id': 0,
            'is_static': 1, 'transient': 0, 'dont_auto_start': 0, 'preload_transient': 0, 'db_process_id': 300,
            'map_name': 'maps/City_Zones/City_01_02/City_01_02.txt', 'mission_info': '',
            'command': COMMAND.format(map_id=map_id, cookie=cookie)}


def owned(alive=True, ready=True):
    process = SimpleNamespace(process=Mock(), overflow=False)
    process.process.poll.return_value = None if alive else 1
    return {'process': process, 'progress_path': Path('/nonexistent/progress.bin'), 'ready': ready}


class StockTravelTests(unittest.TestCase):
    def instance(self, *, requested=True, layer=True):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        value = zoning.LocalCharacterZoningServer.__new__(zoning.LocalCharacterZoningServer)
        with patch.dict('os.environ', {zone_travel.ENABLE_ENVIRONMENT: '1' if requested else '0'}):
            value.stock = {'requested': zone_travel.requested(), 'enabled': False, 'starts': [], 'evictions': [],
                           'arrivals': 0, 'transfer_wait_observed': 0, 'decisions': []}
        value.stock_starts = {}
        value.manual_atlas_startup = {'external_maps': {'build_input_sha256': 'b' * 64}} if layer else {}
        value.monorail_qualified = True
        value.owner = SimpleNamespace(args=SimpleNamespace(state=Path(temporary.name), session_id=SESSION))
        value.ctx = SimpleNamespace(event=Mock(), report={})
        value.active_map_id = 1
        value.epoch = 0
        value.pending = None
        value.maps = {1: owned()}
        value.creation_report = {'client_pid': 44}
        value.zoning_report = {'events': [], 'transfers': []}
        value.map_launch_history = Mock()
        value._map_progress = Mock(return_value={'available': True, 'tick_completed': 3, 'unchanged_seconds': 0})
        value.live_progress = Mock(return_value=True)
        value.root = Path(temporary.name)
        return value

    def supervisor(self, value):
        directory = value.owner.args.state / ('requests-%d' % len(value.stock['starts']))
        directory.mkdir()
        return supervisor.ExternalMapSupervisor(directory, **value.external_maps_options())

    def publish(self, sup, map_id, cookie, sequence):
        import json
        (sup.directory / ('map-%d-%d.json' % (map_id, cookie))).write_text(
            json.dumps(record(map_id, cookie, sequence), separators=(',', ':')) + '\n')
        return '%s map_id=%d cookie=%d static=1\n' % (supervisor.MARKER, map_id, cookie)

    def test_station_queue_off_and_policy_only_with_the_layer(self):
        value = self.instance()
        self.assertTrue(value.stock_travel_active())
        self.assertFalse(value.monorail_enabled())
        options = value.external_maps_options()
        self.assertTrue(value.stock['enabled'])
        self.assertTrue(options['session_maps'](1))
        self.assertFalse(options['session_maps'](5))
        for changes in ({'requested': False}, {'layer': False}):
            other = self.instance(**changes)
            self.assertFalse(other.stock_travel_active())
            self.assertTrue(other.monorail_enabled())
            self.assertEqual(other.external_maps_options(), {'session_maps': other.EXTERNAL_SESSION_MAPS})

    def test_request_is_started_with_its_cookie_then_ready(self):
        value = self.instance()
        sup = self.supervisor(value)
        spawned = []

        def spawn(map_id, **keywords):
            spawned.append((map_id, keywords))
            value.maps[map_id] = owned(ready=False)
        value._spawn_map = spawn
        value.live_progress = Mock(return_value=False)
        console = '\n' + supervisor.ACK + '\n' + self.publish(sup, 5, 77, 1)
        sup.poll(console)
        value.serve_external_maps(sup)
        self.assertEqual(spawned, [(5, {'cookie': 77, 'port': 7003, 'options': ('-aggrocap', '17')})])
        self.assertEqual(value.maps[5]['cookie'], 77)
        self.assertIn(5, value.stock_starts)
        value.live_progress = Mock(return_value=True)
        value.serve_external_maps(sup)
        self.assertTrue(value.maps[5]['ready'])
        self.assertEqual(value.stock_starts, {})
        self.assertEqual(sup.report()['counts']['start_ready'], 1)
        self.assertTrue(value.stock['starts'][0]['ready'])

    def test_late_or_exited_start_is_stopped_and_delinked(self):
        value = self.instance()
        sup = self.supervisor(value)
        value._spawn_map = lambda map_id, **keywords: value.maps.__setitem__(map_id, owned(ready=False))
        value.live_progress = Mock(return_value=False)
        sup.poll('\n' + supervisor.ACK + '\n' + self.publish(sup, 5, 77, 1))
        value.serve_external_maps(sup)
        value.stock_starts[5]['deadline'] = time.monotonic() - 1
        process = value.maps[5]['process'].process
        value.serve_external_maps(sup)
        process.terminate.assert_called_once()
        self.assertNotIn(5, value.maps)
        entry = sup.next_delink()
        self.assertEqual((entry['map_id'], entry['reason']), (5, 'start_failed'))
        self.assertFalse(value.stock['starts'][0]['ready'])

    # ---- 0.13.69: the spare zone server -----------------------------------------------------

    OPTIONS = ('-aggrocap', '17')            # what this fixture's requests carry (record())

    def spare_instance(self, *, tree='zones', memory=8000):
        value = self.instance()
        value.owner.root = value.owner.args.state
        value.owner.wine_env = {}
        value.owner.args.wine = '/opt/wine/bin/wine'
        value.runtime = value.owner.args.state
        value.spare = None
        value.spare_next = value.spare_room_next = 0
        value.spare_report = {'format': 1, 'policy': zoning.SPARE_ZONE_POLICY, 'requested': True,
                              'layer_available': True, 'starts': [], 'waiting_reason': None}
        value.server_metrics_enabled = True
        value.stock['enabled'] = True
        value.creation_report['connected_on_atlas'] = True
        value.initial_zone = None
        value.active_since_monotonic = time.monotonic() - zoning.SPARE_SETTLE_SECONDS - 1
        value.zone_tree_prepared = {'runtime': Path('/zones')} if tree == 'zones' else None
        value.zone_tree_for = lambda map_id: {1: 'atlas', 101: 'atlas', 5: 'kings_row'}.get(map_id, tree if map_id == 7 else None)
        value.maps[1]['runtime'] = Path('/atlas')
        value.map_metrics_environment = lambda environment, runtime: dict(environment, ARMPORT_SERVER_METRICS='1')
        value.session_map_options = lambda: ['-notwostagemapxfer']
        value.install_zone_beacon_graph = Mock()
        value.mark_startup_timing = Mock()
        value.map_startup_timing = Mock(return_value=None)
        value.begin_startup_timing = Mock(return_value=None)
        value.stock_request_options = self.OPTIONS
        started = []

        def start(label, command, env):
            process = SimpleNamespace(process=Mock(), overflow=False, output=bytearray())
            process.process.poll.return_value = None
            started.append((label, command, env, process))
            return process
        value.ctx.start = start
        patches = [patch.object(zoning, 'available_memory_mib', return_value=memory),
                   patch.object(zoning.character.game, 'check_game_port'),
                   patch.object(zoning.character, 'mapserver_memory_arguments', return_value=['-nosharedmemory']),
                   patch.object(zoning.character, 'LOCAL_CLIENT_LINK_OPTIONS', return_value=[]),
                   patch.object(zoning.base, 'windows_path', side_effect=lambda path: 'Z:' + str(path))]
        for item in patches:
            item.start(); self.addCleanup(item.stop)
        return value, started

    def tick(self, value):
        value.spare_next = 0
        value.tick_spare()

    def test_a_spare_loads_beside_the_current_zone_and_takes_the_next_request(self):
        value, started = self.spare_instance()
        self.tick(value)
        self.assertEqual(len(started), 1)
        label, command, env, process = started[0]
        self.assertEqual(label, 'local-character-zoning-spare-1')
        # No zone and no cookie yet; the request's own options; the shared tree; its own files.
        self.assertEqual(command[command.index('-map_id') + 1], '0')
        self.assertNotIn('-cookie', command)
        self.assertEqual(tuple(command[-2:]), self.OPTIONS)
        self.assertIn('--chdir=/zones', command)
        assign = value.owner.args.state / 'character-zoning-spare-1-assign.txt'
        self.assertEqual(env[zoning.SPARE_FILE_ENVIRONMENT], 'Z:' + str(assign))
        self.assertEqual(env['ARMPORT_SERVER_METRICS'], '1')
        port = value.spare['port']
        self.assertEqual(port, zone_travel.LAST_PORT)          # the start policy hands out ports from the bottom
        row = value.spare_report['starts'][0]
        self.assertEqual((row['tree'], row['warm'], row['outcome'], row['beside_map_id']), ('zones', False, None, 1))
        self.tick(value)                                      # one spare only
        self.assertEqual(len(started), 1)
        process.output += b'loading sequencers...done\nARMPORT_SPARE_V1 status=waiting pid=9 placeholder_map_id=0\n'
        self.tick(value)
        self.assertTrue(value.spare['warm'] and row['warm'])
        # The game asks for a zone of that tree: the spare gets it, nothing new is started.
        sup = self.supervisor(value)
        value._spawn_map = Mock()
        value.live_progress = Mock(return_value=False)
        sup.poll('\n' + supervisor.ACK + '\n' + self.publish(sup, 7, 88, 1))
        with patch.dict(zoning.MAPS, {7: {'name': 'Zone 7', 'port': None, 'instance': 1, 'world': 'City_07',
                                          'shared_zone_tree': True}}):
            value.serve_external_maps(sup)
            value._spawn_map.assert_not_called()
            self.assertEqual(assign.read_text(), 'ARMPORT_SPARE_ASSIGN_V1 map_id=7 cookie=88\n')
            value.install_zone_beacon_graph.assert_called_once_with(7, Path('/zones'))
            self.assertIsNone(value.spare)
            owned7 = value.maps[7]
            self.assertIs(owned7['process'], process)
            self.assertEqual((owned7['cookie'], owned7['port'], owned7['stock'], owned7['ready']), (88, port, True, False))
            self.assertEqual(zoning.MAPS[7]['port'], port)
            self.assertEqual((row['outcome'], row['map_id']), ('assigned', 7))
            start = value.stock['starts'][0]
            self.assertEqual((start['port'], start['spare']['warm'], start['spare']['ordinal']), (port, True, 1))
            self.assertEqual(sup.requests[(7, 88)]['start']['port'], port)
            # Readiness, failure and the deadline are the ordinary start's from here.
            value.live_progress = Mock(return_value=True)
            value.serve_external_maps(sup)
            self.assertTrue(value.maps[7]['ready'])
            # Two zone servers now: no new spare until the zone the hero left has given way.
            self.assertEqual(len(started), 1)

    def test_no_spare_until_the_session_allows_it(self):
        cases = [(lambda v: v.spare_report.update(requested=False), None),
                 (lambda v: v.creation_report.update(connected_on_atlas=False), 'character_not_in_the_world'),
                 (lambda v: setattr(v, 'pending', {'to_map_id': 5}), 'a_zone_is_starting'),
                 (lambda v: v.stock_starts.update({5: {}}), 'a_zone_is_starting'),
                 (lambda v: (v.owner.args.state / 'character-logout.json').write_text('{}'), 'saving'),
                 (lambda v: setattr(v, 'active_since_monotonic', time.monotonic()), 'settling_in_the_zone'),
                 (lambda v: v.spare_report.update(layer_available=False), 'server_without_the_spare_layer'),
                 (lambda v: setattr(v, 'stock_request_options', None), 'request_options_unknown'),
                 (lambda v: v.spare_report.update(started=zoning.SPARE_START_LIMIT), 'start_limit'),
                 (lambda v: setattr(v, 'zone_tree_prepared', None) or setattr(v, 'active_map_id', 5)
                  or v.maps.update({5: v.maps.pop(1)}), 'no_prepared_tree')]
        for change, reason in cases:
            with self.subTest(reason=reason):
                value, started = self.spare_instance()
                change(value)
                self.tick(value)
                self.assertEqual((started, value.spare), ([], None))
                self.assertEqual(value.spare_report['waiting_reason'], reason)
        value, started = self.spare_instance(memory=zoning.SPARE_MIN_AVAILABLE_MIB - 1)
        self.tick(value)
        self.assertEqual((started, value.spare_report['waiting_reason']), ([], 'low_memory'))

    def test_a_request_the_spare_cannot_take_starts_the_ordinary_way_and_frees_the_spare(self):
        for name, change in (('another tree', lambda v: None),
                             ('other options', lambda v: v.spare.update(options=('-aggrocap', '20')))):
            with self.subTest(name):
                value, started = self.spare_instance()
                self.tick(value)
                process = started[0][3]
                change(value)
                sup = self.supervisor(value)
                spawned = []
                value._spawn_map = lambda map_id, **keywords: (spawned.append((map_id, keywords)),
                                                               value.maps.__setitem__(map_id, owned(ready=False)))
                target = 5 if name == 'another tree' else 7
                sup.poll('\n' + supervisor.ACK + '\n' + self.publish(sup, target, 3, 1))
                with patch.dict(zoning.MAPS, {7: {'name': 'Zone 7', 'port': None, 'instance': 1, 'world': 'City_07',
                                                  'shared_zone_tree': True}}):
                    value.serve_external_maps(sup)
                self.assertEqual([item[0] for item in spawned], [target])
                process.process.terminate.assert_called_once_with()
                self.assertIsNone(value.spare)
                row = value.spare_report['starts'][0]
                self.assertEqual((row['outcome'], row['reason']), ('dropped', 'request_for_another_tree'))
                self.assertFalse((value.owner.args.state / 'character-zoning-spare-1-assign.txt').exists())

    def test_a_spare_that_exits_is_dropped_and_another_may_start(self):
        value, started = self.spare_instance()
        self.tick(value)
        started[0][3].process.poll.return_value = 3           # the layer's own exit for a bad assignment
        self.tick(value)
        self.assertIsNone(value.spare)
        self.assertEqual(value.spare_report['starts'][0]['outcome'], 'dropped')
        self.assertIn('exited', value.spare_report['starts'][0]['reason'])
        self.tick(value)
        self.assertEqual([item[0] for item in started], ['local-character-zoning-spare-1', 'local-character-zoning-spare-2'])
        started[1][3].output += b'Program crash detected\n'
        self.tick(value)
        self.assertIn('crashed', value.spare_report['starts'][1]['reason'])

    def test_the_zone_the_hero_left_gives_way_to_the_spare_only_on_the_dbservers_word(self):
        value, started = self.spare_instance()
        value.maps[5] = owned()
        value.query_count = 0
        value.query = Mock(return_value='1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 5 SmapId 5\n')
        value._stock_arrival = Mock(side_effect=lambda target, sample: setattr(value, 'active_map_id', target))
        old = value.maps[5]['process'].process
        first = value.maps[1]['process'].process
        self.tick(value)                                      # the DbServer says the hero is in 5, not 1
        self.assertEqual((started, value.spare_report['waiting_reason']), ([], 'hero_zone_changed'))
        self.assertEqual(value.active_map_id, 5)              # the probe recorded that arrival
        old.terminate.assert_not_called(); first.terminate.assert_not_called()
        self.tick(value)                                      # asked at most every two minutes
        self.assertEqual(value.spare_report['waiting_reason'], 'resident_zone_still_running')
        self.assertEqual(value.query.call_count, 1)
        value.spare_room_next = 0
        value.query = Mock(return_value='garbage\n')          # no answer: nothing is stopped
        self.tick(value)
        self.assertEqual(value.spare_report['waiting_reason'], 'hero_zone_unconfirmed')
        old.terminate.assert_not_called(); first.terminate.assert_not_called()
        value.spare_room_next = 0
        value.active_map_id = 1
        value.query = Mock(return_value='1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1\n')
        self.tick(value)
        old.terminate.assert_called_once_with()
        self.assertEqual((set(value.maps), value.stock['evictions'][-1]['reason']), ({1}, 'room_for_the_spare'))
        self.assertEqual(value.spare_report['waiting_reason'], 'made_room')
        self.tick(value)
        self.assertEqual(len(started), 1)

    def test_the_atlas_tree_spare_takes_atlas_parks_other_instance_on_its_fixed_port(self):
        value, started = self.spare_instance(tree=None)
        self.tick(value)
        self.assertIn('--chdir=/atlas', started[0][1])
        self.assertEqual((value.spare['tree'], value.spare['port']), ('atlas', zone_travel.FIXED_PORTS[101]))
        sup = self.supervisor(value)
        value._spawn_map = Mock()
        value.live_progress = Mock(return_value=False)
        sup.poll('\n' + supervisor.ACK + '\n' + self.publish(sup, 101, 4, 1))
        value.serve_external_maps(sup)
        value._spawn_map.assert_not_called()
        value.install_zone_beacon_graph.assert_not_called()
        self.assertEqual(value.maps[101]['port'], zone_travel.FIXED_PORTS[101])

    def test_request_options_are_remembered_for_the_next_sessions_first_spare(self):
        value, _ = self.spare_instance()
        value.stock_request_options = None
        self.assertIsNone(value._request_options())
        value._remember_request_options(('-maxLevel', '50', '-aggrocap', '17'))
        path = value.owner.root / zoning.SPARE_OPTIONS_FILE
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        later, _ = self.spare_instance()
        later.owner.root = value.owner.root
        later.stock_request_options = None
        self.assertEqual(later._request_options(), ('-maxLevel', '50', '-aggrocap', '17'))
        for damage in ('not json', '{"format": 1, "kept": ["-ok", "; rm -rf /"]}', '{"format": 2, "kept": []}'):
            path.write_text(damage)
            fresh, _ = self.spare_instance()
            fresh.owner.root = value.owner.root
            fresh.stock_request_options = None
            self.assertIsNone(fresh._request_options(), damage)

    def test_third_zone_stops_the_idle_resident_one(self):
        value = self.instance()
        value.maps[5] = owned()
        value.maps[5]['last_occupied'] = 10
        value.zone_tree_for = lambda map_id: {1: 'atlas', 5: 'kings_row', 7: 'zones'}.get(map_id)
        value.query_count = 0
        value.query = Mock(return_value='1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1 InMapXfer\n')
        sup = self.supervisor(value)
        spawned = []
        value._spawn_map = lambda map_id, **keywords: (spawned.append(map_id),
                                                       value.maps.__setitem__(map_id, owned(ready=False)))
        old = value.maps[5]['process'].process
        sup.poll('\n' + supervisor.ACK + '\n' + self.publish(sup, 7, 5, 1))
        value.serve_external_maps(sup)
        old.terminate.assert_called_once()
        self.assertEqual(spawned, [7])
        self.assertEqual(set(value.maps), {1, 7})
        self.assertEqual(value.stock['evictions'][0]['map_id'], 5)
        value.query.assert_called_once_with(['-getstatus', '3', '1'], 'stock-occupied')

    def test_arrival_on_another_ready_zone_moves_the_session(self):
        value = self.instance()
        value.external_maps_options()
        value.maps[5] = owned()
        value._activate = Mock(side_effect=lambda map_id: setattr(value, 'active_map_id', map_id))
        sample = dict(loaded=True, connected=True, in_map_transfer=False, map_id=5, static_map_id=5,
                      address='127.0.0.1')
        value._observe_stock_move(dict(sample, in_map_transfer=True))
        self.assertEqual(value.stock['transfer_wait_observed'], 1)
        value._observe_stock_move(sample)
        self.assertEqual((value.active_map_id, value.epoch, value.stock['arrivals']), (5, 1, 1))
        leg = value.zoning_report['transfers'][-1]
        self.assertEqual((leg['from_map_id'], leg['to_map_id'], leg['travel_method']), (1, 5, 'stock_travel'))
        event = value.zoning_report['events'][-1]
        self.assertEqual((event['status'], event['travel_method'], event['current_map_id']),
                         ('arrived', 'stock_travel', 5))
        # A zone that is not ready yet, or not owned, never moves the session.
        value._observe_stock_move(dict(sample, map_id=7, static_map_id=7))
        self.assertEqual(value.active_map_id, 5)

    def test_a_third_zone_asks_where_the_hero_is_before_stopping_one(self):
        # Thor 0.13.56: the King's Row arrival was read 67 s after ResumeCharacter.
        # A third request in that window must not stop the zone the hero is on.
        value = self.instance()
        value.zone_tree_for = lambda map_id: {1: 'atlas', 5: 'kings_row', 6: 'zones'}.get(map_id)
        options = value.external_maps_options()
        value.maps[5] = owned()
        value.maps[1]['last_occupied'], value.maps[5]['last_occupied'] = 10, 0
        value._activate = Mock(side_effect=lambda map_id: setattr(value, 'active_map_id', map_id))
        value.query_count, value.stock_last_arrival_ms = 30, None
        answer = ['1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 5 SmapId 5 InMapXfer\n']
        def query(arguments, label):
            self.assertEqual((arguments, label), (['-getstatus', '3', '1'], 'stock-occupied'))
            value.query_count += 1
            if isinstance(answer[0], Exception):
                raise answer[0]
            return answer[0]
        value.query = query
        decision = options['policy'](record(6, 3, 1), {})
        self.assertEqual(decision[0], 'start', decision)
        self.assertEqual(decision[1]['evict'], [1])                  # Atlas, not King's Row where the hero is
        self.assertEqual((value.active_map_id, value.stock['arrivals'], value.stock['occupied_probes']), (5, 1, 1))
        self.assertEqual(value.zoning_report['transfers'][-1]['character_status']['source'], 'stock_occupied_probe')
        self.assertIsInstance(value.stock_last_arrival_ms, int)
        # The DbServer's answer already matches: nothing new is recorded.
        self.assertEqual(value.stock_occupied(), 5)
        self.assertEqual(value.stock['arrivals'], 1)
        # Unknown (failed probe, not an owned ready zone, budget kept for the save): delink.
        for reply, count in ((zoning.base.DiagnosticError('query failed'), 30),
                             ('1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 9 SmapId 9\n', 30),
                             ('1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 5 SmapId 5 NoConnect\n', 30),
                             ('invalid container request\n', 30),
                             (answer[0], zoning.STOCK_PROBE_QUERY_LIMIT)):
            answer[0], value.query_count = reply, count
            with self.subTest(reply=str(reply)[:40]):
                self.assertIsNone(value.stock_occupied())
                self.assertEqual(value.zone_policy.decide(record(6, 4, 2)), ('delink', 'player_zone_unknown'))
        self.assertEqual(value.active_map_id, 5)



class SharedZoneTreeTests(unittest.TestCase):
    def tearDown(self):
        for map_id in [m for m in zoning.MAPS if m not in (1, 5, 101)]:
            del zoning.MAPS[map_id]

    def test_other_static_zones_register_with_their_world_and_a_free_port(self):
        entry = zoning.register_zone(6)
        self.assertEqual((entry['name'], entry['world'], entry['instance'], entry['port']),
                         ('Steel Canyon', 'city_02_01', 1, None))
        # A zone without a reviewed display name keeps its zone_index key.
        self.assertEqual(zoning.register_zone(78)['name'], 'pvp')
        self.assertEqual((zoning.zone_name(71), zoning.zone_name(2)), ('Mercy Island', 'Zone 2'))
        self.assertTrue(zoning.same_zone(1, 101) and zoning.same_zone(101, 1) and zoning.same_zone(71, 71))
        self.assertFalse(zoning.same_zone(1, 5) or zoning.same_zone(1, 71) or zoning.same_zone(1, None))
        self.assertTrue(zoning.supported(6))
        self.assertIs(zoning.register_zone(6), entry)
        self.assertIs(zoning.register_zone(5), zoning.MAPS[5])
        with self.assertRaises(zoning.base.DiagnosticError):
            zoning.register_zone(2)
        self.assertEqual(zoning.free_zone_port({7004, 7005}), 7006)
        status = '6 maps/City_Zones/City_02_01/City_02_01.txt S: 1 / 2 Ip: 127.0.0.1:7004 Mem: 100\n'
        entry['port'] = 7004
        self.assertTrue(zoning.ready(zoning.parse_map_status(status, 6), 6))

    def test_tree_choice(self):
        helper = StockTravelTests('test_station_queue_off_and_policy_only_with_the_layer')
        value = helper.instance()
        self.addCleanup(helper.doCleanups)
        value.zone_asset_document = None
        self.assertEqual([value.zone_tree_for(m) for m in (1, 101, 5, 6)], ['atlas', 'atlas', 'kings_row', None])
        value.zone_asset_document = {'files': {}}
        self.assertEqual(value.zone_tree_for(6), 'zones')
        self.assertIsNone(value.zone_tree_for(2))
        value.monorail_qualified = False
        self.assertIsNone(value.zone_tree_for(5))


if __name__ == '__main__':
    unittest.main()

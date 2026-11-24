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

    def test_a_request_is_taken_between_inspections(self):
        """0.13.81: the session looked for zone start requests every five seconds.

        Measured "request to map ready" was always a multiple of five seconds (10.1, 15.1 s
        in CI; 20.2, 20.3, 25.3 s on the Thor): the request waited for the next inspection.
        """
        value = self.instance()
        sup = self.supervisor(value)
        value.external_maps, value.process = sup, SimpleNamespace(text=lambda: console[0])
        value.external_maps_next, value.external_maps_query, value.query_count = 0, None, 0
        value.creation_report['external_maps'] = {}
        value.tick_spare = Mock()
        spawned = []
        value._spawn_map = lambda map_id, **keywords: (spawned.append(map_id),
                                                       value.maps.__setitem__(map_id, owned(ready=False)))
        value.live_progress = Mock(return_value=False)
        console = ['\n' + supervisor.ACK + '\n']
        clock = [100.0]
        with patch('time.monotonic', lambda: clock[0]):
            # Nothing asked for: one directory listing, no console read, no ordinary tick.
            value.tick_external_maps = Mock(side_effect=AssertionError('no tick without a request'))
            self.assertFalse(sup.unseen_request())
            self.assertFalse(value.tick_travel_requests())
            del value.tick_external_maps
            clock[0] += 0.1
            console[0] += self.publish(sup, 5, 77, 1)
            self.assertTrue(sup.unseen_request())
            self.assertFalse(value.tick_travel_requests())          # at most twice a second
            self.assertEqual(spawned, [])
            clock[0] += 0.5
            value.external_maps_next = clock[0] + 4.4               # the ordinary tick had just run
            self.assertTrue(value.tick_travel_requests())           # the request does not wait for it
            self.assertEqual(spawned, [5])
            self.assertFalse(sup.unseen_request())
            value.tick_spare.assert_not_called()                    # the spare's idle work keeps its cadence
            self.assertEqual(value.creation_report['travel_request_ticks'],
                             {'format': 1, 'for_new_request': 1, 'while_starting': 0})
            # While the zone starts its readiness is looked at between inspections too, once a second.
            clock[0] += 0.5
            self.assertTrue(value.tick_travel_requests())
            self.assertIn(5, value.stock_starts)                    # limited by the tick's own second
            clock[0] += 0.6
            value.live_progress = Mock(return_value=True)
            self.assertTrue(value.tick_travel_requests())
            self.assertEqual(value.stock_starts, {})
            self.assertTrue(value.maps[5]['ready'])
            self.assertEqual(value.creation_report['travel_request_ticks']['while_starting'], 2)
            clock[0] += 0.6
            self.assertFalse(value.tick_travel_requests())          # nothing waiting any more
            value.tick_spare.assert_not_called()
            # The five-second inspection still runs the spare's work.
            clock[0] += 5
            value.tick_external_maps()
            value.tick_spare.assert_called_once()
        # Without the game's own zone travel there is no supervisor and nothing happens.
        other = self.instance()
        self.assertFalse(other.tick_travel_requests())
        # A stopped supervisor or an unreadable directory is never an error.
        sup.stopped = 'test'
        self.assertFalse(sup.unseen_request())
        gone = self.supervisor(self.instance())
        gone.directory.rmdir()
        self.assertFalse(gone.unseen_request())

    def test_the_session_loop_calls_the_request_check_only_while_playing(self):
        import character_creation_diagnostic as creation
        import client_interactive_diagnostic as interactive
        source = Path(interactive.__file__).read_text()
        self.assertIn('                self.between_polls()\n                time.sleep(.1)\n', source)
        self.assertEqual(interactive.PROGRESS_POLL_SECONDS, 5)
        ticks = []
        session = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
        session.local_server = SimpleNamespace(tick_travel_requests=lambda: ticks.append(1))
        session.ctx = SimpleNamespace(report={'startup_observed': True})
        session.saved_announced, session.login_announced, session.observer = False, True, object()
        session.between_polls()
        self.assertEqual(ticks, [1])
        for change in ({'saved_announced': True}, {'login_announced': False}, {'observer': None}):
            for name, changed in change.items():
                original = getattr(session, name)
                setattr(session, name, changed)
                session.between_polls()
                setattr(session, name, original)
        session.ctx.report['startup_observed'] = False
        session.between_polls()
        self.assertEqual(ticks, [1])
        session.ctx.report['startup_observed'] = True
        session.local_server = SimpleNamespace()                    # a server without the travel layer
        session.between_polls()

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

    def ahead_instance(self, order, results, **kwargs):
        """A warm spare of the shared zone tree; `results` answers install_zone_beacon_graph by map id."""
        value, started = self.spare_instance(**kwargs)
        value.zone_tree_prepared = {'runtime': Path('/zones'), 'preparation': {'beacon_graph': {}}}
        value.zone_graph_order = Mock(side_effect=lambda near: list(order))
        value._graphs_ahead_must_yield = Mock(return_value=False)
        value.ctx.check = lambda: None
        calls = []
        def install(map_id, runtime, context=None, rows=None):
            calls.append((map_id, runtime, context, rows))
            answer = results[map_id]
            if isinstance(answer, BaseException):
                raise answer
            if callable(answer):
                answer = answer(context)
            if answer is not None:
                value.zone_tree_prepared['preparation']['beacon_graph'][str(map_id)] = answer
            return answer
        value.install_zone_beacon_graph = install
        self.tick(value)
        self.tick(value)                                      # loading: nothing is done yet
        self.assertEqual(calls, [])
        started[0][3].output += b'ARMPORT_SPARE_V1 status=waiting pid=9 placeholder_map_id=0\n'
        self.tick(value)                                      # the tick that sees it warm
        self.assertEqual(calls, [])
        return value, calls

    REUSED = {'verified': True, 'status': 'reused_verified_graph', 'input_validation': 'unchanged_directory_receipt'}
    INSTALLED = {'verified': True, 'status': 'installed_verified_graph', 'input_validation': 'bounded_single_walk_inventory_and_fingerprints'}

    def test_a_warm_spare_makes_every_zones_graph_ready_ahead_one_a_tick(self):
        # Thor 0.13.79: the first visit to Cap au Diable waited 37.4 s for its graph before the hand-over.
        value, calls = self.ahead_instance([72, 71, 1, 73, 74], {72: dict(self.REUSED), 73: dict(self.REUSED), 74: dict(self.INSTALLED)})
        value.zone_tree_prepared['preparation']['beacon_graph']['71'] = {'verified': True}    # this session's own zone
        self.tick(value)
        self.assertEqual([call[0] for call in calls], [72])
        self.assertEqual(calls[0][1], Path('/zones'))
        self.assertIsInstance(calls[0][2], zoning.GraphsAheadContext)
        value.zone_graph_order.assert_called_once_with(1)                      # by distance from the hero's zone
        self.tick(value)                                      # 71 is known this session, 1 is running: 73 next
        self.assertEqual([call[0] for call in calls], [72, 73])
        self.assertIs(calls[1][3], calls[0][3])               # one pass shares the directory rows it has read
        self.tick(value)
        self.assertEqual([call[0] for call in calls], [72, 73, 74])
        self.tick(value); self.tick(value)                    # nothing left
        self.assertEqual(len(calls), 3)
        report = value.spare_report['graphs_checked_ahead']
        self.assertEqual([(row['map_id'], row['status']) for row in report],
                         [(72, 'reused_verified_graph'), (73, 'reused_verified_graph'), (74, 'installed_verified_graph')])
        self.assertTrue(all(type(row['seconds']) is float for row in report))
        self.assertEqual(value.spare_report['graphs_ahead_done'], 3)

    def test_a_full_install_ahead_is_followed_by_a_pause_and_drops_the_rows_it_made_stale(self):
        value, calls = self.ahead_instance([73, 74, 75], {73: dict(self.INSTALLED), 74: dict(self.REUSED), 75: dict(self.REUSED)})
        clock = [1000.0]
        def install(map_id, runtime, context=None, rows=None, original=value.install_zone_beacon_graph):
            if map_id == 73:
                clock[0] += 9.0                               # a first install: 9 s
            return original(map_id, runtime, context=context, rows=rows)
        value.install_zone_beacon_graph = install
        with patch.object(zoning.time, 'monotonic', side_effect=lambda: clock[0]):
            self.tick(value)
            self.assertEqual([call[0] for call in calls], [73])
            for _ in range(3):                                # 15 s of ticks: still inside the 18 s pause
                clock[0] += 5.0; self.tick(value)
            self.assertEqual([call[0] for call in calls], [73])
            clock[0] += 5.0; self.tick(value)
            self.assertEqual([call[0] for call in calls], [73, 74])
            self.assertIsNot(calls[1][3], calls[0][3])        # the install wrote into the tree: rows read again
            clock[0] += 5.0; self.tick(value)                 # a receipt check is followed by no pause
            self.assertEqual([call[0] for call in calls], [73, 74, 75])
            self.assertIs(calls[2][3], calls[1][3])

    def test_the_work_ahead_gives_way_to_a_zone_request_and_a_save_and_tries_again_later(self):
        value, calls = self.ahead_instance([73], {73: lambda context: context.check() or dict(self.INSTALLED)})
        clock = [2000.0]
        with patch.object(zoning.time, 'monotonic', side_effect=lambda: clock[0]):
            value._graphs_ahead_must_yield = Mock(side_effect=[False, True])     # asked before starting, then inside
            self.tick(value)
            self.assertEqual(len(calls), 1)
            self.assertEqual(value.spare_report['graphs_checked_ahead'], [])
            self.assertEqual(value.spare_report['graphs_ahead_stopped'], 1)
            self.assertNotIn('73', value.zone_tree_prepared['preparation']['beacon_graph'])
            value._graphs_ahead_must_yield = Mock(return_value=False)
            clock[0] += 5.0; self.tick(value)                 # inside the retry delay
            self.assertEqual(len(calls), 1)
            clock[0] += zoning.SPARE_GRAPHS_AHEAD_RETRY_SECONDS; self.tick(value)
            self.assertEqual(len(calls), 2)
            self.assertEqual(value.spare_report['graphs_checked_ahead'][0]['status'], 'installed_verified_graph')
        # A request that is already waiting: nothing is started at all.
        value, calls = self.ahead_instance([73], {73: dict(self.REUSED)})
        value._graphs_ahead_must_yield = Mock(return_value=True)
        self.tick(value); self.tick(value)
        self.assertEqual(calls, [])
        # The context asks at most every quarter second, and the session's own cancellation still wins.
        asked = Mock(return_value=False)
        session = SimpleNamespace(check=Mock(), report={'x': 1})
        context = zoning.GraphsAheadContext(session, asked)
        with patch.object(zoning.time, 'monotonic', side_effect=lambda: clock[0]):
            context.check(); context.check(); context.check()
            self.assertEqual((session.check.call_count, asked.call_count), (3, 1))
            clock[0] += zoning.SPARE_GRAPHS_AHEAD_YIELD_SECONDS
            asked.return_value = True
            with self.assertRaises(zoning.GraphsAheadStopped):
                context.check()
        self.assertEqual(context.report, {'x': 1})            # everything else is the session's context
        self.assertTrue(issubclass(zoning.GraphsAheadStopped, zoning.base.Cancelled))
        session.check.side_effect = zoning.base.Cancelled('session')
        with self.assertRaises(zoning.base.Cancelled) as raised:
            context.check()
        self.assertNotIsInstance(raised.exception, zoning.GraphsAheadStopped)

    def test_the_work_ahead_forgets_an_unverified_result_waits_for_a_starting_zone_and_never_fails_the_session(self):
        failed = {'verified': False, 'status': 'not_installed', 'error': 'Zone collision input differs'}
        value, calls = self.ahead_instance([73, 74], {73: dict(failed), 74: dict(self.REUSED)})
        value.stock_starts[5] = {}
        self.tick(value)
        self.assertEqual(calls, [])
        value.stock_starts.clear()
        clock = [3000.0]
        with patch.object(zoning.time, 'monotonic', side_effect=lambda: clock[0]):
            self.tick(value)
            self.assertEqual(value.spare_report['graphs_checked_ahead'], [{'map_id': 73, 'status': 'not_installed', 'seconds': 0.0}])
            self.assertNotIn('73', value.zone_tree_prepared['preparation']['beacon_graph'])   # the trip decides itself
            clock[0] += 5.0; self.tick(value); clock[0] += 5.0; self.tick(value)
            self.assertEqual([call[0] for call in calls], [73, 74])                          # 73 is not tried again ahead
        # A spare of another tree does nothing; an error is recorded once and ends the work.
        other, started = self.spare_instance(tree='atlas')
        other.zone_graph_order = Mock(return_value=[72]); other.install_zone_beacon_graph = Mock()
        self.tick(other)
        started[0][3].output += b'ARMPORT_SPARE_V1 status=waiting pid=9 placeholder_map_id=0\n'
        self.tick(other); self.tick(other)                    # no shared zone tree prepared
        other.zone_tree_prepared = {'runtime': Path('/zones'), 'preparation': {}}
        self.tick(other)                                      # prepared since, but this spare runs the Atlas tree
        other.install_zone_beacon_graph.assert_not_called(); other.zone_graph_order.assert_not_called()
        failing, calls = self.ahead_instance([73], {73: OSError('gone')})
        for _ in range(4):
            self.tick(failing)
        self.assertEqual(len(calls), 1)
        self.assertEqual(failing.spare_report['graphs_checked_ahead'], [{'map_id': None, 'status': 'error', 'error': 'gone'}])
        self.assertIsNotNone(failing.spare)
        listing, calls = self.ahead_instance([73], {73: dict(self.REUSED)})
        listing.zone_graph_order = Mock(side_effect=AttributeError('no assets'))
        for _ in range(3):
            self.tick(listing)
        self.assertEqual((calls, listing.zone_graph_order.call_count), ([], 1))

    def test_the_yield_probe_sees_an_untaken_zone_request_and_a_save_request(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            value, _ = self.spare_instance()
            state, requests = Path(temporary) / 'state', Path(temporary) / 'requests'
            state.mkdir(); requests.mkdir()
            value.owner = SimpleNamespace(args=SimpleNamespace(state=state))
            value.external_maps = SimpleNamespace(directory=requests, requests={(72, 5): {}})
            probe = lambda: zoning.LocalCharacterZoningServer._graphs_ahead_must_yield(value)
            self.assertFalse(probe())
            (requests / 'map-72-5.json').write_text('{}')     # taken by the session already
            (requests / 'map-73-6.json.tmp').write_text('{}') # still being written
            (requests / 'notes.txt').write_text('x')
            self.assertFalse(probe())
            (requests / 'map-73-6.json').write_text('{}')
            self.assertTrue(probe())
            value.external_maps.requests[(73, 6)] = {}
            self.assertFalse(probe())
            (state / 'character-logout.json').write_text('{}')
            self.assertTrue(probe())
            (state / 'character-logout.json').unlink()
            value.external_maps = None
            self.assertFalse(probe())
            value.owner = SimpleNamespace()                   # no state folder known: never a reason to fail
            self.assertFalse(probe())

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

    def test_a_spare_serves_a_request_that_differs_only_by_transient(self):
        # Thor 0.13.75: trips carry -transient, the zone at Enter Game has no request at all; CI
        # run 43394425425 dropped a warm spare for a request of its own tree. The server reads
        # -transient only with an idle exit timeout, which no zone server here has.
        value, started = self.spare_instance()
        self.tick(value)
        for options, expected in ((self.OPTIONS, True), (('-transient',) + self.OPTIONS, True),
                                  (self.OPTIONS + ('-transient',), True),
                                  (('-preloadtransient',) + self.OPTIONS, False),
                                  (('-aggrocap', '20'), False), ((), False)):
            with self.subTest(options=options):
                self.assertIs(value._spare_serves('zones', options), expected)
        value.spare['options'] = ('-transient',) + self.OPTIONS
        self.assertTrue(value._spare_serves('zones', self.OPTIONS))
        self.assertFalse(value._spare_serves('atlas', self.OPTIONS))
        value.spare['options'] = ('-preloadtransient',) + self.OPTIONS
        self.assertFalse(value._spare_serves('zones', ('-preloadtransient',) + self.OPTIONS))

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

    def test_the_zone_just_left_stays_with_the_owners_option_and_older_ones_give_way(self):
        # 0.13.82: current zone + the zone just left + the spare. Off by default; only with the spare.
        value, started = self.spare_instance()
        value.keep_previous_zone = True
        value.stock['keep_previous_zone'] = {'kept': 0}
        value.maps[5] = owned()
        value.query_count = 0
        value.query = Mock(return_value='1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1\n')
        self.tick(value)                                      # two zones run: nothing has to give way
        self.assertEqual(len(started), 1)
        value.query.assert_not_called()
        self.assertEqual((set(value.maps), value.stock['evictions']), ({1, 5}, []))
        # A third zone (the trip before last): only the one left longest ago is stopped.
        value.spare = None
        value.maps[7] = owned()
        value.maps[5]['last_occupied'], value.maps[7]['last_occupied'] = 10.0, 20.0
        older, newer = value.maps[5]['process'].process, value.maps[7]['process'].process
        self.tick(value)
        self.assertEqual(value.spare_report['waiting_reason'], 'made_room')
        older.terminate.assert_called_once_with(); newer.terminate.assert_not_called()
        self.assertEqual((set(value.maps), value.stock['keep_previous_zone']['kept']), ({1, 7}, 1))
        self.tick(value)
        self.assertEqual(len(started), 2)
        # The request guards allow the third server only with the option.
        with patch.dict(zoning.MAPS, {9: dict(zoning.MAPS[5])}):
            value.spare = {'process': owned()['process'], 'progress_path': Path('/x'), 'assign_path': value.root / 'a',
                           'runtime': Path('/zones'), 'port': 7099, 'launch_monotonic': 0, 'tree': 'zones'}
            value.keep_previous_zone = False
            with self.assertRaisesRegex(zoning.character.base.DiagnosticError, 'Invalid spare zone assignment'):
                value._assign_spare(9, 3)
            with self.assertRaisesRegex(zoning.character.base.DiagnosticError, 'Duplicate or unreviewed'):
                value._spawn_map(9, cookie=3, port=7005)

    def test_the_option_needs_the_spare_and_raises_the_capacity_by_one(self):
        source = (ROOT / 'android/guest/character_zoning.py').read_text()
        self.assertIn("self.keep_previous_zone = (os.environ.get(KEEP_PREVIOUS_ZONE_ENV) == '1'\n"
                      "                                   and os.environ.get(SPARE_ZONE_ENV) == '1')", source)
        self.assertIn("capacity=zone_travel.MAX_ZONE_SERVERS + (1 if getattr(self, 'keep_previous_zone', False) else 0))",
                      source)
        value = self.instance()
        value.keep_previous_zone = True
        policy = value.external_maps_options()['policy']
        self.assertEqual(policy.capacity, zone_travel.MAX_ZONE_SERVERS + 1)
        value = self.instance()
        self.assertEqual(value.external_maps_options()['policy'].capacity, zone_travel.MAX_ZONE_SERVERS)

    def test_the_zone_servers_own_console_line_says_the_hero_arrived(self):
        # 0.13.82 (patches/mapserver-single-player). Thor 0.13.81: the entity log line for the same
        # event was read 73 and 74 s after it happened, an arrival 45 s after.
        line = (b'ARMPORT_CLIENT_READY_V1 utc_ms=%d map_id=%d port=27060 name="' + zoning.character.CHARACTER.encode()
                + b'" auth="COHLOCAL"\r\n')
        console = b'Server ready.\r\n' + line % (1795495756412, 5) + b'noise\n' + line % (1795495999001, 5)
        found = zoning.console_ready(console, 5, 1795495000000, 1795496000000)
        self.assertEqual((found['utc_ms'], found['map_id'], found['port'], found['line_ordinal']),
                         (1795495999001, 5, 27060, 1))
        self.assertEqual((found['log_route'], found['source'], found['loaded_world_assets'], found['account']),
                         ('owned_zone_server_console', 'current_target_stock_CLIENT_READY_resumeCharacter_success',
                          True, 'COHLOCAL'))
        self.assertRegex(found['line_sha256'], '^[0-9a-f]{64}$')
        self.assertEqual(found['log_timestamp'], time.strftime('%y%m%d %H:%M:%S', time.localtime(1795495999)))
        entity = dict(found, log_route='embedded_dbserver_logserver')
        self.assertEqual(set(found), set(entity))
        # Older than the floor, in the future, another zone, another character or account: not this arrival.
        self.assertEqual(zoning.console_ready(console, 5, 1795495756413, 1795496000000)['utc_ms'], 1795495999001)
        self.assertIsNone(zoning.console_ready(console, 5, 1795495999002, 1795496000000))
        self.assertEqual(zoning.console_ready(console, 5, 0, 1795495800000)['utc_ms'], 1795495756412)
        self.assertIsNone(zoning.console_ready(console, 1, 0, 1795496000000))
        for other in (console.replace(b'auth="COHLOCAL"', b'auth="OTHER"'),
                      console.replace(zoning.character.CHARACTER.encode() + b'"', b'Somebody Else"'),
                      console.replace(b'ARMPORT_CLIENT_READY_V1 ', b' ARMPORT_CLIENT_READY_V1 '),
                      console.replace(b'port=27060', b'port=70000'), b''):
            self.assertIsNone(zoning.console_ready(other, 5, 0, 1795496000000))
        # The session reads the console first and the entity log only without a line.
        value = self.instance()
        value.maps[5] = dict(owned(), launch_utc_ms=1795495000000)
        value.maps[5]['process'].output = bytearray(console)
        value.current_logs = Mock(return_value=[])
        with patch.object(zoning, 'stock_ready', return_value={'utc_ms': 1, 'line_ordinal': 0}) as slow:
            self.assertEqual(value.stock_ready_now(5, 0, 1795496000000)['log_route'], 'owned_zone_server_console')
            slow.assert_not_called()
            value.maps[5]['process'].output = bytearray(b'Server ready.\n')
            self.assertEqual(value.stock_ready_now(5, 0, 1795496000000), {'utc_ms': 1, 'line_ordinal': 0})
            self.assertEqual(value.stock_ready_now(7, 0, 1795496000000), {'utc_ms': 1, 'line_ordinal': 0})
        self.assertEqual(value.zoning_report['ready_records'], {'format': 1, 'from_console': 1, 'from_entity_log': 2})
        # The binding that lets a reopened character save accepts either route and nothing else.
        binding = (ROOT / 'android/guest/local_character_server.py').read_text()
        self.assertIn("and ready.get('log_route') in ('embedded_dbserver_logserver', 'owned_zone_server_console')", binding)

    def test_a_new_resume_line_makes_the_next_inspection_due_now(self):
        # 0.13.83. Thor 0.13.82: the line was read at once but only at the next 15 s slot; the FPS
        # buttons came alive 9.4 s and 11.3 s after the hero was in the world.
        self.assertEqual(zoning.character.POLL_SECONDS, 15)
        self.assertEqual((zoning.READY_PEEK_SECONDS, zoning.READY_PEEK_LIMIT), (0.5, 256))
        line = b'ARMPORT_CLIENT_READY_V1 utc_ms=1795543898322 map_id=5 port=27060 name="X" auth="COHLOCAL"\n'
        self.assertTrue(line.startswith(zoning.CONSOLE_READY_PREFIX))
        value = self.instance()
        value.creation_report.update(connected_on_atlas=True)
        value.maps[5] = dict(owned(), launch_utc_ms=1795543000000)
        value.maps[5]['process'].output = bytearray(b'Server ready.\n')
        value.character_next = value.stock_log_next = 10 ** 9

        def look():
            value.ready_peek_next = 0                        # past the half-second throttle
            return value.ready_line_peek()

        self.assertFalse(look())
        self.assertEqual((value.character_next, value.stock_log_next), (10 ** 9, 10 ** 9))
        value.maps[5]['process'].output += line
        self.assertTrue(look())
        self.assertEqual((value.character_next, value.stock_log_next), (0, 0))
        value.character_next = value.stock_log_next = 10 ** 9
        self.assertFalse(look())                             # the same line is acted on once
        self.assertEqual(value.character_next, 10 ** 9)
        value.maps[5]['process'].output += b'noise\n' + line
        self.assertTrue(look())                              # the next resume (a trip back)
        self.assertEqual(value.zoning_report['ready_peeks'], {'format': 1, 'count': 2})
        # Within the throttle nothing is searched.
        value.maps[5]['process'].output += line
        value.ready_peek_next = time.monotonic() + 60
        self.assertFalse(value.ready_line_peek())
        # Before the first connection is established the look is repeated twice, two seconds apart.
        first = self.instance()
        first.creation_report.update(connected_on_atlas=False)
        first.maps[5] = dict(owned(), launch_utc_ms=1795543000000)
        first.maps[5]['process'].output = bytearray(line)
        first.ready_peek_next = 0
        self.assertTrue(first.ready_line_peek())
        first.ready_peek_next = 0
        self.assertFalse(first.ready_line_peek())            # not two seconds later yet
        for expected in (True, True, False):
            first.ready_peek_next, first.ready_peek_retry_at = 0, 0
            self.assertEqual(first.ready_line_peek(), expected)
        # A zone that is no longer owned is forgotten; a console without the attribute is skipped.
        del value.maps[5]
        value.maps[7] = {'process': SimpleNamespace()}
        self.assertFalse(look())
        self.assertEqual(value.ready_peek_offsets, {})

    def test_the_session_loop_runs_the_inspection_when_a_resume_line_is_new(self):
        import character_creation_diagnostic as creation
        session = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
        answers, inspections = [True, False], []
        session.local_server = SimpleNamespace(tick_travel_requests=lambda: None, ready_line_peek=lambda: answers.pop(0))
        session.ctx = SimpleNamespace(report={'startup_observed': True})
        session.saved_announced, session.login_announced, session.observer = False, True, object()
        session.observe_console = lambda: inspections.append(1)
        session.between_polls()
        session.between_polls()
        self.assertEqual(inspections, [1])
        session.login_announced = False                      # before the login nothing is looked at
        session.between_polls()
        self.assertEqual((inspections, answers), ([1], []))

    def test_an_arrival_read_from_the_console_moves_the_session_at_once(self):
        value = self.instance()
        value.stock['enabled'] = True
        value.stock.update(transfers_begun=[], arrival_source=None)
        value.stock_log_next = 0
        value.stock_last_arrival_ms = 1795495000000
        value.creation_report.update(verified=False, connected_on_atlas=True)
        value.maps[5] = dict(owned(), launch_utc_ms=1795495700000)
        now_ms = int(time.time() * 1000)
        value.maps[5]['process'].output = bytearray(
            b'ARMPORT_CLIENT_READY_V1 utc_ms=%d map_id=5 port=27060 name="' % (now_ms - 800)
            + zoning.character.CHARACTER.encode() + b'" auth="COHLOCAL"\n')
        value.current_logs = Mock(return_value=[])
        value._stock_arrival = Mock()
        record = value._poll_stock_logs()
        self.assertEqual((record['map_id'], record['log_route']), (5, 'owned_zone_server_console'))
        self.assertEqual(value.stock['arrival_source'], 'zone_console_resume_character')
        self.assertEqual(value._stock_arrival.call_args[0][0], 5)
        self.assertEqual(value._stock_arrival.call_args[0][1]['source'], 'zone_console')
        self.assertEqual(value.stock_last_arrival_ms, now_ms - 800)

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



MISSION_FILE = 'maps/Missions/Office/Office_30/Office_30_Layout_01.txt'
MISSION_NAME = MISSION_FILE.lower()


def mission_record(map_id, cookie, sequence, *, name=MISSION_FILE, info='1:2:3:L1_P_Clockwork_Mission1'):
    return dict(record(map_id, cookie, sequence), is_static=0, map_name=name, mission_info=info)


class MissionMapTests(unittest.TestCase):
    """0.13.84, test option: a mission door's map is started in the shared zone tree."""
    instance = StockTravelTests.instance
    supervisor = StockTravelTests.supervisor

    def mission_instance(self, *, enabled=True):
        value = self.instance()
        value.mission_maps = enabled
        value.missions = value.stock['mission_maps'] = {'requested': enabled, 'started': 0, 'starts': [],
                                                        'refused': [], 'ended': [], 'arrivals': 0, 'returns': 0}
        value.zone_asset_document = {'files': {}}
        value.initial_zone = None
        value.creation_report['connected_on_atlas'] = True
        value.maps = {7: owned()}
        value.active_map_id = 7
        value.zone_tree_for = lambda map_id: 'zones' if map_id in (7, 8) else None
        self.addCleanup(lambda: [zoning.MAPS.pop(key) for key in list(zoning.MAPS) if zoning.mission_map(key)])
        return value

    def publish_mission(self, sup, map_id, cookie, sequence, **fields):
        import json
        (sup.directory / ('map-%d-%d.json' % (map_id, cookie))).write_text(
            json.dumps(mission_record(map_id, cookie, sequence, **fields), separators=(',', ':')) + '\n')
        return '%s map_id=%d cookie=%d static=0\n' % (supervisor.MARKER, map_id, cookie)

    def test_a_mission_map_name_is_a_file_under_maps_missions(self):
        self.assertEqual(zoning.mission_map_name(MISSION_FILE), MISSION_NAME)
        self.assertEqual(zoning.mission_map_name(MISSION_FILE.replace('/', '\\')), MISSION_NAME)
        for name in ('maps/City_Zones/City_01_01/City_01_01.txt', 'maps/Missions/../City_Zones/a/b.txt',
                     'maps/Missions/office.txt', 'maps/Missions/Office/Office_30/a.bin', '', None, 7,
                     'maps/Missions/' + 'a/' * 9 + 'b.txt', 'maps/Missions/Of fice/a/b.txt', 'x' * 300):
            with self.subTest(name=str(name)[:40]):
                self.assertIsNone(zoning.mission_map_name(name))

    def test_without_the_option_a_mission_request_is_delinked_as_before(self):
        value = self.mission_instance(enabled=False)
        sup = self.supervisor(value)
        added = sup.poll('\n' + supervisor.ACK + '\n' + self.publish_mission(sup, 700, 9, 1))
        self.assertEqual([(e['decision'], e['reason']) for e in added], [('delink', 'not_static')])
        self.assertEqual(added[0]['mission_info'], '1:2:3:L1_P_Clockwork_Mission1')

    def test_why_a_mission_request_is_refused(self):
        value = self.mission_instance()
        value.external_maps_options()
        cases = (
            (lambda: None, mission_record(700, 9, 1, name='maps/Bases/base.txt'), 'not_a_mission_map'),
            (lambda: None, mission_record(700, 9, 1, info=''), 'no_mission_info'),
            (lambda: None, mission_record(8, 9, 1), 'map_id_is_a_zone'),
            (lambda: None, mission_record(100000, 9, 1), 'map_id_is_a_zone'),
            (lambda: value.creation_report.update(connected_on_atlas=False), mission_record(700, 9, 1),
             'character_not_in_the_world'),
            (lambda: (value.creation_report.update(connected_on_atlas=True),
                      setattr(value, 'zone_asset_document', None)), mission_record(700, 9, 1),
             'zone_assets_not_imported'),
            (lambda: (setattr(value, 'zone_asset_document', {'files': {}}),
                      value.missions.update(started=zoning.MISSION_START_LIMIT)), mission_record(700, 9, 1),
             'mission_start_limit'),
            (lambda: (value.missions.update(started=0),
                      (value.owner.args.state / 'character-logout.json').write_text('{}')), mission_record(700, 9, 1),
             'saving'),
        )
        for prepare, request, reason in cases:
            prepare()
            with self.subTest(reason=reason):
                self.assertEqual(value.zone_policy.decide(request), ('delink', reason))
        self.assertEqual([row['reason'] for row in value.missions['refused']], [case[2] for case in cases])
        (value.owner.args.state / 'character-logout.json').unlink()
        zoning.register_mission(700, MISSION_NAME)
        value.maps[700] = owned()
        value.active_map_id = 700
        self.assertEqual(value.zone_policy.decide(mission_record(701, 9, 1)), ('delink', 'already_in_a_mission'))

    def test_a_mission_request_starts_registers_and_the_hero_goes_in_and_out(self):
        value = self.mission_instance()
        sup = self.supervisor(value)
        spawned = []
        def spawn(map_id, **keywords):
            self.assertTrue(zoning.supported(map_id) and zoning.mission_map(map_id))
            spawned.append((map_id, keywords))
            value.maps[map_id] = owned(ready=False)
        value._spawn_map = spawn
        value.live_progress = Mock(return_value=False)
        sup.poll('\n' + supervisor.ACK + '\n' + self.publish_mission(sup, 700, 77, 1))
        value.serve_external_maps(sup)
        self.assertEqual(spawned, [(700, {'cookie': 77, 'port': 7004, 'options': ('-aggrocap', '17')})])
        self.assertEqual(zoning.MAPS[700], {'name': 'Mission', 'port': None, 'instance': 1,
                                            'world': 'office_30_layout_01', 'shared_zone_tree': True,
                                            'mission': True, 'map_name': MISSION_NAME})
        self.assertEqual(zoning.zone_name(700), 'Mission')
        start = value.missions['starts'][0]
        self.assertEqual((start['map_id'], start['cookie'], start['map_name'], start['from_map_id'],
                          start['mission_info']), (700, 77, MISSION_NAME, 7, '1:2:3:L1_P_Clockwork_Mission1'))
        self.assertEqual(value.missions['started'], 1)
        self.assertTrue(value.stock['starts'][0]['mission'])
        value.live_progress = Mock(return_value=True)
        value.serve_external_maps(sup)
        self.assertTrue(value.maps[700]['ready'])
        # In: the zone server's own line; the event tells the app this map is a mission.
        value._activate = Mock(side_effect=lambda map_id: setattr(value, 'active_map_id', map_id))
        value._stock_arrival(700, {'source': 'zone_console', 'map_id': 700})
        event = value.zoning_report['events'][-1]
        self.assertEqual((event['current_map_id'], event['current_map_name'], event['mission_map'],
                          event['from_map_id']), (700, 'Mission', True, 7))
        self.assertNotIn('from_mission_map', event)
        self.assertTrue(value.zoning_report['transfers'][-1]['mission'])
        self.assertEqual((value.missions['arrivals'], 'arrived_utc_ms' in start), (1, True))
        # While inside: no spare takes the place of the zone the hero came from.
        value.stock['enabled'] = True
        value.spare_report = {'started': 0}
        value._request_options = lambda: ()
        value.initial_zone_pending = lambda: False
        with patch.dict('os.environ', {zone_travel.ENABLE_ENVIRONMENT: '1'}):
            self.assertEqual(value._spare_wait_reason(time.monotonic()), 'in_a_mission')
        # Out: an ordinary arrival, marked as coming from a mission.
        value._stock_arrival(7, {'source': 'zone_console', 'map_id': 7})
        event = value.zoning_report['events'][-1]
        self.assertEqual((event['current_map_id'], event['from_map_id'], event['from_mission_map']), (7, 700, True))
        self.assertNotIn('mission_map', event)
        self.assertEqual(value.missions['returns'], 1)

    def test_a_mission_map_that_ended_is_forgotten_and_its_id_can_be_asked_for_again(self):
        value = self.mission_instance()
        value.external_maps_options()
        zoning.register_mission(700, MISSION_NAME)
        value.maps[700] = owned(alive=False)
        value.maps[700]['process'].process.returncode = 0
        value.health = zoning.LocalCharacterZoningServer.health.__get__(value)
        with patch.object(zoning.character.LocalCharacterReopenServer, 'health', lambda self: None):
            value.health()                                   # a mission map may end by itself
            value.maps[8] = owned(alive=False)
            with self.assertRaisesRegex(zoning.base.DiagnosticError, 'Ready zoning destination exited'):
                value.health()                               # a zone may not
            del value.maps[8]
        self.assertFalse(value.owns_requested_map(700))
        self.assertEqual(set(value.maps), {7})
        self.assertEqual([(row['map_id'], row['exit_code']) for row in value.missions['ended']], [(700, 0)])
        self.assertEqual(value.zone_policy.decide(mission_record(700, 10, 2))[0], 'start')
        # The occupied mission map is never forgotten here, whatever its process says.
        value.maps[700] = owned(alive=False)
        value.active_map_id = 700
        value._tick_missions()
        self.assertIn(700, value.maps)

    def test_the_dbservers_answer_names_a_mission_map_the_hero_is_in(self):
        value = self.mission_instance()
        value.external_maps_options()
        zoning.register_mission(700, MISSION_NAME)
        value.maps[700] = owned()
        value.active_map_id = 700
        value.query_count = 0
        value.query = Mock(return_value='1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 700 SmapId 7\n')
        self.assertEqual(value.stock_occupied(), 700)
        # Room for a zone asked for from inside (a hospital in another zone): the zone left gives way.
        decision, plan = value.zone_policy.decide(record(8, 3, 1))
        self.assertEqual((decision, plan['evict']), ('start', [7]))


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

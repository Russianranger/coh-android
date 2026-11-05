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

    def test_third_zone_stops_the_idle_resident_one(self):
        value = self.instance()
        value.maps[5] = owned()
        value.maps[5]['last_occupied'] = 10
        value.zone_tree_for = lambda map_id: {1: 'atlas', 5: 'kings_row', 7: 'zones'}.get(map_id)
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


if __name__ == '__main__':
    unittest.main()

"""The game's own travel: Atlas Park first, the saved zone from the DbServer's request at Enter Game.

Thor 0.13.57 (owner, 2026-11-06): THORHERO saved in King's Row; the session
prepared King's Row itself while the client started, and Android closed the app
as the client splash appeared. With the ARM64 client and stock travel the
session now always prepares Atlas Park, and King's Row (or any zone) is started
by the supervisor when the DbServer asks for it at Enter Game.
"""
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_zoning as zoning
import external_map_supervisor as supervisor
import local_character_server as server
import zone_travel
import test_saved_map_startup as saved
import test_stock_travel as stock

DYNAMIC_ENVIRONMENT = {zone_travel.ENABLE_ENVIRONMENT: '1', 'COH_CLIENT_ARCH': 'arm64'}


def connected(map_id):
    return dict(loaded=True, connected=True, in_map_transfer=False, map_id=map_id, static_map_id=map_id,
                address='127.0.0.1')


class DynamicInitialMapTests(unittest.TestCase):
    instance = saved.SavedMapStartupTests.instance
    baseline = saved.SavedMapStartupTests.baseline

    def dynamic(self, map_id=5, environment=DYNAMIC_ENVIRONMENT):
        patcher = patch.dict('os.environ', environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        value = self.instance(map_id)
        self.assertEqual(value.initial_map_preparation(), 1 if environment is DYNAMIC_ENVIRONMENT
                         and map_id != 1 else map_id)
        return value

    def test_saved_kings_row_prepares_atlas_park_and_keeps_the_saved_zone(self):
        value = self.dynamic()
        self.assertEqual((value.active_map_id, value.startup_preparation_map_id, value.creation_report['map_id']),
                         (1, 1, 1))
        startup = value.zoning_report['saved_startup']
        self.assertEqual((startup['map_id'], startup['prepared_map_id'], startup['port']), (5, 1, 7003))
        self.assertEqual(startup['dynamic_start']['policy'], zoning.DYNAMIC_INITIAL_POLICY)
        self.assertFalse(startup['dynamic_start']['activated'])
        self.assertEqual(value.zoning_report['saved_destination_map_id'], 5)
        event = value.ctx.event.call_args.kwargs
        self.assertEqual((event['map_id'], event['dynamic_start'], event['prepared_map_id']), (5, True, 1))
        self.assertFalse(event['sql_game_mutations_performed'])
        # start() repeats the baseline once the DbServer is up: same saved zone, still Atlas first.
        self.baseline(value)
        self.assertEqual(value.active_map_id, 1)
        self.saved_position['staticmapid'] = 101
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Saved destination changed'):
            value.capture_baseline()

    def test_atlas_or_the_legacy_path_without_stock_travel_or_the_arm64_client(self):
        value = self.dynamic(1)
        self.assertEqual(value.active_map_id, 1)
        self.assertNotIn('dynamic_start', value.zoning_report['saved_startup'])
        for environment in ({zone_travel.ENABLE_ENVIRONMENT: '1', 'COH_CLIENT_ARCH': 'x86'},
                            {zone_travel.ENABLE_ENVIRONMENT: '0', 'COH_CLIENT_ARCH': 'arm64'}):
            with self.subTest(environment=environment):
                value = self.dynamic(5, environment)
                self.assertEqual(value.active_map_id, 5)
                self.assertIsNone(value.dynamic_initial())
                self.assertFalse(value.ctx.event.call_args.kwargs['dynamic_start'])

    def test_a_dynamic_start_needs_the_external_maps_layer(self):
        value = self.dynamic()
        value.manual_atlas_startup = None
        with self.assertRaisesRegex(server.base.DiagnosticError, "game's own zone travel"):
            value.start_map()
        value.ctx.start.assert_not_called()

    def test_enter_game_request_starts_the_saved_zone_and_the_connection_follows_it(self):
        value = self.dynamic()
        value.manual_atlas_startup = {'external_maps': {'build_input_sha256': 'b' * 64}}
        value.maps = {1: dict(stock.owned(), launch_utc_ms=1000)}
        value._activate = Mock(wraps=lambda map_id: setattr(value, 'active_map_id', map_id)
                               or value.creation_report.update(map_id=map_id))
        directory = value.owner.args.state / 'requests'
        directory.mkdir()
        sup = supervisor.ExternalMapSupervisor(directory, **value.external_maps_options())
        launched = int(time.time() * 1000)

        def spawn(map_id, **keywords):
            value.maps[map_id] = dict(stock.owned(ready=False), launch_utc_ms=launched)
        value._spawn_map = Mock(side_effect=spawn)
        value._map_progress = Mock(return_value={'available': True})
        value.live_progress = Mock(return_value=False)
        # Enter Game: the DbServer finds King's Row not running and asks for it.
        sup.poll('\n' + supervisor.ACK + '\n' + stock.StockTravelTests.publish(None, sup, 5, 9, 1))
        value.serve_external_maps(sup)
        value._spawn_map.assert_called_once_with(5, cookie=9, port=7003, options=('-aggrocap', '17'))
        value.tick_dynamic_initial()
        dynamic = value.dynamic_initial()
        self.assertTrue(dynamic['started'])
        self.assertFalse(dynamic['activated'])
        self.assertEqual(value.active_map_id, 1)
        value.live_progress = Mock(return_value=True)
        value.serve_external_maps(sup)
        value.tick_dynamic_initial()
        self.assertEqual(value.active_map_id, 5)
        self.assertEqual(value.ready_floor_ms, launched - 999)
        self.assertTrue(dynamic['activated'])
        self.assertTrue(value.stock['starts'][0]['initial_login'])
        self.assertEqual(value.epoch, 0)                     # not a trip: no arrival event
        self.assertEqual(value.stock['arrivals'], 0)
        self.assertTrue(value.connected_status(connected(5)))
        metadata = value.connection_metadata()
        self.assertTrue(metadata['stock_travel'])
        self.assertEqual(dynamic['connected_map_id'], 5)
        self.assertTrue(value.zoning_report['saved_startup']['character_world_entry_verified'])
        value.tick_dynamic_initial()
        value._activate.assert_called_once_with(5)

    def test_a_connection_on_the_prepared_atlas_park_is_accepted(self):
        value = self.dynamic(101)
        self.assertTrue(value.connected_status(connected(1)))
        value.connection_metadata()
        self.assertEqual(value.dynamic_initial()['connected_map_id'], 1)
        self.assertFalse(value.zoning_report['saved_startup']['character_world_entry_verified'])

    def test_kings_row_proof_qualifies_after_a_dynamic_start(self):
        proof = {'session_id': saved.SESSION, 'name': 'THORHERO', 'account': 'COHLOCAL', 'character_id': 1,
                 'auth_id': 77, 'map_id': 5, 'monorail_enabled': False, 'stock_travel': True,
                 'before_character_id': 1, 'baseline_character_id': 1,
                 **{key: True for key in ('zoning_enabled', 'connected_on_atlas', 'connected_on_supported_map',
                                          'existing_character_verified', 'reopen_verified',
                                          'preserved_existing_identity', 'native_client_ready_observed')}}
        self.assertTrue(zoning.character_identity(proof, saved.SESSION))


if __name__ == '__main__':
    unittest.main()

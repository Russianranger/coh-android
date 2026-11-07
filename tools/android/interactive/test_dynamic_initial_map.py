"""The game's own travel: no zone server before Enter Game; the character's own zone only.

Thor 0.13.57 (owner, 2026-11-06): THORHERO saved in King's Row; the session
started King's Row itself while the client started, and Android's low-memory
killer closed the app. 0.13.58 then started Atlas Park first. Owner,
2026-11-07: "I want the game to load whatever zone my character is in. Under no
circumstances should characters be transported to Atlas Park unless they exist
in that zone already, especially if I have a villain or other origin
characters". With the ARM64 client and stock travel no zone is prepared before
Enter Game: the DbServer asks for the saved zone (or a new character's starting
zone) and only that zone is admitted until the character first enters it.
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
import character_creation_diagnostic as creation
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

    def tearDown(self):
        for map_id in [m for m in zoning.MAPS if m not in (1, 5, 101)]:
            del zoning.MAPS[map_id]

    def dynamic(self, map_id=5, environment=DYNAMIC_ENVIRONMENT, *, server_class=None):
        patcher = patch.dict('os.environ', environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        value = self.instance(map_id)
        prepared = value.initial_map_preparation()
        self.assertEqual(prepared, None if environment is DYNAMIC_ENVIRONMENT else map_id)
        return value

    def layer(self, value):
        value.manual_atlas_startup = {'external_maps': {'build_input_sha256': 'b' * 64}}
        directory = value.owner.args.state / ('requests-%d' % len(value.stock['starts']))
        directory.mkdir()
        return supervisor.ExternalMapSupervisor(directory, **value.external_maps_options())

    def serve(self, value, sup, map_id, cookie, sequence, *, ready=False):
        launched = int(time.time() * 1000)

        def spawn(target, **keywords):
            value.maps[target] = dict(stock.owned(ready=False), launch_utc_ms=launched,
                                      launch_monotonic=time.monotonic())
        value._spawn_map = Mock(side_effect=spawn)
        value._map_progress = Mock(return_value={'available': True})
        value.live_progress = Mock(return_value=ready)
        # The DbServer console is cumulative: one acknowledgement, then each request's marker.
        console = getattr(sup, 'test_console', '\n' + supervisor.ACK + '\n')
        sup.test_console = console + stock.StockTravelTests.publish(None, sup, map_id, cookie, sequence)
        sup.poll(sup.test_console)
        value.serve_external_maps(sup)
        return launched

    def test_a_saved_king_s_row_hero_prepares_no_zone_before_enter_game(self):
        value = self.dynamic()
        self.assertEqual((value.active_map_id, value.startup_preparation_map_id, value.creation_report['map_id']),
                         (5, None, 5))
        startup = value.zoning_report['saved_startup']
        self.assertEqual((startup['map_id'], startup['port'], startup['world']), (5, None, 'City_01_02'))
        initial = value.zoning_report['initial_zone']
        self.assertIs(startup['dynamic_start'], initial)
        self.assertEqual((initial['policy'], initial['expected_map_id'], initial['activated']),
                         (zoning.DYNAMIC_INITIAL_POLICY, 5, False))
        self.assertNotIn('prepared_map_id', initial)
        event = value.ctx.event.call_args.kwargs
        self.assertEqual((event['map_id'], event['port'], event['dynamic_start']), (5, None, True))
        self.assertNotIn('prepared_map_id', event)
        self.assertFalse(event['sql_game_mutations_performed'])
        # start() repeats the baseline once the DbServer is up: the same saved zone, still nothing prepared.
        self.baseline(value)
        self.assertEqual(value.active_map_id, 5)
        self.assertIs(value.zoning_report['initial_zone'], initial)
        self.saved_position['staticmapid'] = 101
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Saved destination changed'):
            value.capture_baseline()

    def test_an_atlas_park_hero_is_also_started_by_the_game(self):
        for map_id in (1, 101):
            with self.subTest(map_id=map_id):
                value = self.dynamic(map_id)
                self.assertEqual(value.active_map_id, map_id)
                self.assertEqual(value.dynamic_initial()['expected_map_id'], map_id)
                self.assertIsNone(value.zoning_report['saved_startup']['port'])

    def test_the_legacy_start_without_stock_travel_or_the_arm64_client(self):
        for environment in ({zone_travel.ENABLE_ENVIRONMENT: '1', 'COH_CLIENT_ARCH': 'x86'},
                            {zone_travel.ENABLE_ENVIRONMENT: '0', 'COH_CLIENT_ARCH': 'arm64'}):
            with self.subTest(environment=environment):
                value = self.dynamic(5, environment)
                self.assertEqual(value.active_map_id, 5)
                self.assertIsNone(value.dynamic_initial())
                self.assertEqual(value.zoning_report['saved_startup']['port'], 7003)
                self.assertFalse(value.ctx.event.call_args.kwargs['dynamic_start'])

    def test_start_map_starts_nothing_and_needs_the_external_maps_layer(self):
        value = self.dynamic()
        value.manual_atlas_startup = None
        with self.assertRaisesRegex(server.base.DiagnosticError, "game's own zone travel"):
            value.start_map()
        value.ctx.start.assert_not_called()
        self.layer(value)
        value.start_map()
        value.ctx.start.assert_not_called()
        value.ctx.stage.assert_called_once_with('local_atlas_startup')
        fields = value.ctx.passed.call_args.kwargs
        self.assertEqual((fields['map_ready'], fields['zone_servers_started'], fields['map_id']), (False, 0, 5))
        self.assertEqual(value.maps, {})
        self.assertIsNone(value.map_process)
        # The character list and the creator need only the DbServer.
        self.assertTrue(value.poll_initial_map_startup())
        self.assertTrue(value.client_startup_assets_allowed())
        self.assertIsNone(value.native_ready_record())

    def test_enter_game_starts_only_the_saved_zone_and_the_connection_follows_it(self):
        value = self.dynamic()
        sup = self.layer(value)
        value._activate = Mock(wraps=lambda map_id: setattr(value, 'active_map_id', map_id)
                               or value.creation_report.update(map_id=map_id))
        # Before Enter Game nothing else may start (owner: no Atlas Park unless the character is there).
        self.assertEqual(value.zone_policy.decide(stock.record(1, 3, 1)), ('delink', 'not_the_saved_zone'))
        self.assertEqual(value.zone_policy.decide(stock.record(71, 4, 2)), ('delink', 'not_the_saved_zone'))
        launched = self.serve(value, sup, 5, 9, 3)
        value._spawn_map.assert_called_once_with(5, cookie=9, port=7003, options=('-aggrocap', '17'))
        # The app hears which zone starts before its (blocking) preparation begins.
        statuses = [call.kwargs for call in value.ctx.event.call_args_list if call.args == ('character_initial_zone',)]
        self.assertEqual([(row['status'], row['map_id'], row['map_name']) for row in statuses],
                         [('starting', 5, "King's Row")])
        self.assertIn("Starting King's Row for THORHERO", statuses[0]['message'])
        self.assertEqual(value.zone_policy.decide(stock.record(6, 5, 4)), ('delink', 'initial_zone_already_starting'))
        value.tick_dynamic_initial()
        initial = value.dynamic_initial()
        self.assertTrue(initial['started'])
        self.assertFalse(initial['activated'])
        self.assertEqual(len(initial['attempts']), 1)
        value._activate.assert_not_called()
        self.assertIsNone(value.native_ready_record())
        self.assertTrue(value.initial_zone_wait_seconds() >= 0)
        value.live_progress = Mock(return_value=True)
        value.serve_external_maps(sup)
        value.tick_dynamic_initial()
        value._activate.assert_called_once_with(5)
        self.assertEqual((value.active_map_id, value.ready_floor_ms), (5, launched - 999))
        self.assertTrue(initial['activated'] and value.creation_report['map_ready'])
        self.assertEqual(initial['attempts'][-1]['outcome'], 'ready')
        self.assertTrue(value.stock['starts'][0]['initial_login'])
        self.assertEqual((value.epoch, value.stock['arrivals']), (0, 0))     # not a trip: no arrival
        self.assertTrue(value.connected_status(connected(5)))
        metadata = value.connection_metadata()
        self.assertTrue(metadata['stock_travel'])
        self.assertEqual(initial['connected_map_id'], 5)
        self.assertTrue(value.zoning_report['saved_startup']['character_world_entry_verified'])
        # Once the zone is active, the ordinary policy (current zone plus one) applies again.
        self.assertIsNone(value.admit_zone_request(1))
        value.tick_dynamic_initial()
        value._activate.assert_called_once_with(5)
        initial_row = value.initial_startup_timing
        self.assertEqual((initial_row['map_id'], initial_row['kind']), (5, 'initial_guest_service_request'))
        self.assertTrue(initial_row['initial_zone_started_by_dbserver_request'])
        self.assertIn('map_ready_observed', initial_row['points'])
        # A later trip has its own timing row; the first zone's row keeps its map.
        self.serve(value, sup, 1, 11, 9, ready=True)
        trip = value.maps[1]['startup_timing']
        self.assertEqual((trip['kind'], trip['map_id'], trip['epoch']), ('stock_travel_request', 1, 1))
        self.assertIn('map_ready_observed', trip['points'])
        self.assertEqual(initial_row['map_id'], 5)
        self.assertEqual([row['reason'] for row in initial['refused_requests']],
                         ['not_the_saved_zone', 'not_the_saved_zone', 'initial_zone_already_starting'])

    def test_a_hero_saved_in_atlas_instance_two_enters_atlas_park(self):
        value = self.dynamic(101)
        sup = self.layer(value)
        value._activate = Mock(wraps=lambda map_id: setattr(value, 'active_map_id', map_id)
                               or value.creation_report.update(map_id=map_id))
        self.assertIsNone(value.admit_zone_request(1))     # findBestMapByBaseId: Atlas instance 1
        self.serve(value, sup, 1, 2, 1, ready=True)
        value.serve_external_maps(sup)
        value.tick_dynamic_initial()
        self.assertEqual(value.active_map_id, 1)
        value.connection_metadata()
        self.assertEqual(value.dynamic_initial()['connected_map_id'], 1)

    def test_another_zone_than_the_saved_one_is_refused_even_if_it_started(self):
        value = self.dynamic()
        value.maps = {1: dict(stock.owned(ready=False), stock=True, launch_utc_ms=1, launch_monotonic=1)}
        with self.assertRaisesRegex(server.base.DiagnosticError, 'not the saved'):
            value.tick_dynamic_initial()

    def test_a_failed_start_is_recorded_and_enter_game_can_ask_again(self):
        value = self.dynamic()
        sup = self.layer(value)
        self.serve(value, sup, 5, 9, 1)
        value.tick_dynamic_initial()
        value.stock_starts[5]['deadline'] = time.monotonic() - 1
        value.serve_external_maps(sup)                     # not ready in time: stopped, delinked
        self.assertNotIn(5, value.maps)
        value.tick_dynamic_initial()
        initial = value.dynamic_initial()
        self.assertEqual(initial['attempts'][0]['outcome'], 'not_ready')
        self.assertIsNone(value.admit_zone_request(5))
        self.serve(value, sup, 5, 10, 2)
        value.tick_dynamic_initial()
        self.assertEqual(len(initial['attempts']), 2)
        self.assertNotIn('outcome', initial['attempts'][1])

    def test_king_s_row_proof_qualifies_after_a_dynamic_start(self):
        proof = {'session_id': saved.SESSION, 'name': 'THORHERO', 'account': 'COHLOCAL', 'character_id': 1,
                 'auth_id': 77, 'map_id': 5, 'monorail_enabled': False, 'stock_travel': True,
                 'before_character_id': 1, 'baseline_character_id': 1,
                 **{key: True for key in ('zoning_enabled', 'connected_on_atlas', 'connected_on_supported_map',
                                          'existing_character_verified', 'reopen_verified',
                                          'preserved_existing_identity', 'native_client_ready_observed')}}
        self.assertTrue(zoning.character_identity(proof, saved.SESSION))


class DynamicCreationTests(unittest.TestCase):
    """A new THORHERO: the starting zone the game asks for after the creator, whatever the origin."""

    def tearDown(self):
        for map_id in [m for m in zoning.MAPS if m not in (1, 5, 101)]:
            del zoning.MAPS[map_id]

    def instance(self, environment=DYNAMIC_ENVIRONMENT):
        patcher = patch.dict('os.environ', environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        helper = saved.SavedMapStartupTests('test_kings_and_atlas_authoritative_baselines_keep_identity_rows_and_position')
        with patch.object(zoning, 'LocalCharacterZoningServer', zoning.LocalCharacterZoningCreationServer):
            value = helper.instance()
        self.addCleanup(helper.doCleanups)
        value.inventory = Mock(return_value=[])
        value.sql = Mock(return_value='0')
        value.zone_asset_document = {'files': {}}
        return value

    def test_creation_reports_no_reopen_fields_and_no_zone_until_asked(self):
        value = self.instance()
        self.assertIsInstance(value, zoning.LocalCharacterZoningCreationServer)
        self.assertEqual(value.REPORT_KEY, 'character_creation')
        self.assertIs(value.ctx.report['character_creation'], value.creation_report)
        for key in zoning.LocalCharacterZoningCreationServer.REOPEN_FIELDS:
            self.assertNotIn(key, value.creation_report)
        self.assertEqual((value.active_map_id, value.creation_report['map_id']), (None, None))
        self.assertIsNone(value.initial_map_preparation())
        initial = value.dynamic_initial()
        self.assertEqual((initial['expected_map_id'], initial['map_id']), (None, None))
        value.capture_baseline()                            # the base creation baseline: an empty account
        self.assertEqual(value.creation_report['baseline_character_count'], 0)
        self.assertNotIn('saved_startup', value.zoning_report)

    def test_creation_needs_the_arm64_client(self):
        value = self.instance({zone_travel.ENABLE_ENVIRONMENT: '1', 'COH_CLIENT_ARCH': 'x86'})
        with self.assertRaisesRegex(server.base.DiagnosticError, 'ARM64 client'):
            value.initial_map_preparation()

    def test_a_villain_starts_in_mercy_island_and_nothing_else_starts_first(self):
        value = self.instance()
        value.initial_map_preparation()
        sup = DynamicInitialMapTests.layer(self, value)
        value.start_map()
        value.ctx.start.assert_not_called()
        self.assertTrue(value.poll_initial_map_startup())
        value._activate = Mock(wraps=lambda map_id: setattr(value, 'active_map_id', map_id)
                               or value.creation_report.update(map_id=map_id))
        DynamicInitialMapTests.serve(self, value, sup, 71, 1, 1)    # determineStartMapId: Mercy Island
        value._spawn_map.assert_called_once()
        self.assertEqual(value._spawn_map.call_args.args, (71,))
        self.assertEqual(value.zone_policy.decide(stock.record(1, 2, 2)), ('delink', 'initial_zone_already_starting'))
        value.tick_dynamic_initial()
        self.assertEqual(value.dynamic_initial()['map_name'], 'Mercy Island')
        value.live_progress = Mock(return_value=True)
        value.serve_external_maps(sup)
        value.tick_dynamic_initial()
        self.assertEqual((value.active_map_id, value.creation_report['map_id']), (71, 71))
        metadata = value.connection_metadata()
        self.assertEqual(metadata, {'connected_on_supported_map': True, 'zoning_enabled': True,
                                    'monorail_enabled': False, 'stock_travel': True, 'starting_zone_map_id': 71})
        proof = dict(session_id=saved.SESSION, name='THORHERO', account='COHLOCAL', character_id=1, auth_id=77,
                     map_id=71, connected_on_atlas=True, **metadata)
        self.assertTrue(zoning.creation_identity(proof, saved.SESSION))
        self.assertFalse(zoning.creation_identity(dict(proof, stock_travel=False), saved.SESSION))
        self.assertFalse(zoning.creation_identity(dict(proof, character_id=2), saved.SESSION))
        saved_proof = dict(proof, verified=True, committed_sql_verified=True, requested_logout_observed=True,
                           logout_timer_observed=True, disconnected_before_sql=True, forced_stop_before_save=False)
        self.assertTrue(zoning.creation_save_verified(saved_proof, saved.SESSION))
        self.assertEqual(value.saved_metadata(None)['map_id'], 71)

    def test_the_creation_diagnostic_is_chosen_from_the_launch_environment(self):
        on = {'COH_STOCK_TRAVEL': '1', 'COH_EXTERNAL_MAPS': '1', 'COH_CLIENT_ARCH': 'arm64'}
        self.assertTrue(creation.dynamic_creation_requested(on))
        for key, value in (('COH_STOCK_TRAVEL', '0'), ('COH_EXTERNAL_MAPS', '0'), ('COH_CLIENT_ARCH', 'x86')):
            self.assertFalse(creation.dynamic_creation_requested(dict(on, **{key: value})))
        self.assertTrue(issubclass(creation.ZoningCharacterCreationDiagnostic, creation.CharacterCreationDiagnostic))
        self.assertTrue({'character_zoning.py', 'character_zoning_scheduler.py'}
                        <= creation.ZoningCharacterCreationDiagnostic.REQUIRED)

    def test_the_starting_zone_wait_does_not_use_up_the_creator_window(self):
        diagnostic = creation.ZoningCharacterCreationDiagnostic.__new__(creation.ZoningCharacterCreationDiagnostic)
        diagnostic.ctx = SimpleNamespace(report={})
        diagnostic.local_server = SimpleNamespace(initial_zone_wait_seconds=Mock(side_effect=[0, 120.5, 240.0]))
        self.assertEqual(diagnostic.interaction_deadline(1000.0, {}), 1000.0)
        # The loop passes back the returned deadline: the extension is not added twice.
        self.assertEqual(diagnostic.interaction_deadline(1000.0, {}), 1120.5)
        self.assertEqual(diagnostic.interaction_deadline(1120.5, {}), 1240.0)
        self.assertEqual(diagnostic.ctx.report['starting_zone_wait_seconds'], 240.0)

    def test_the_wait_is_bounded(self):
        value = self.instance()
        value.initial_map_preparation()
        value.dynamic_initial()['attempts'] = [{'started_monotonic': 0.0, 'ended_monotonic': 100.0},
                                               {'started_monotonic': 200.0}]
        self.assertEqual(value.initial_zone_wait_seconds(now=260.0), 160.0)
        self.assertEqual(value.initial_zone_wait_seconds(now=10 ** 6), 2 * zone_travel.START_SECONDS)


if __name__ == '__main__':
    unittest.main()

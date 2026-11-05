"""Which requested zones the device starts, and what it stops to make room."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import zone_travel  # noqa: E402


def record(map_id, cookie=9, static=1):
    return {'map_id': map_id, 'cookie': cookie, 'is_static': static}


class Policy(unittest.TestCase):
    def setUp(self):
        self.maps = {}
        self.current = None
        self.trees = {1: 'atlas', 101: 'atlas', 5: 'kings_row', 7: 'zones', 8: 'zones'}
        self.policy = zone_travel.ZoneTravelPolicy(tree_for=self.trees.get, running=lambda: dict(self.maps),
                                                   occupied=lambda: self.current)

    def test_serves_known_trees_and_delinks_the_rest(self):
        self.maps = {1: {'ready': True, 'port': 7001}}
        self.current = 1
        self.assertEqual(self.policy(record(5), {})[0], 'start')
        self.assertEqual(self.policy(record(5), {})[1]['port'], 7003)
        self.assertEqual(self.policy(record(7), {})[1], {'tree': 'zones', 'evict': [], 'port': 7004,
                                                         'budget_seconds': zone_travel.START_SECONDS})
        self.assertEqual(self.policy(record(40), {}), ('delink', 'zone_not_served'))
        self.assertEqual(self.policy(record(5, static=0), {}), ('delink', 'not_static'))
        self.assertEqual(self.policy(record(1), {}), ('delink', 'already_running'))
        self.assertEqual([d['decision'] for d in self.policy.report()['decisions']],
                         ['start', 'start', 'start', 'delink', 'delink', 'delink'])

    def test_third_zone_stops_the_idle_one_never_the_current_or_a_starting_one(self):
        self.maps = {1: {'ready': True, 'port': 7001, 'last_occupied': 50}, 5: {'ready': True, 'port': 7003,
                                                                                'last_occupied': 90}}
        self.current = 5
        decision, plan = self.policy(record(7), {})
        self.assertEqual((decision, plan['evict'], plan['port']), ('start', [1], 7004))
        self.current = 1
        self.assertEqual(self.policy(record(7), {})[1]['evict'], [5])
        self.maps[5]['ready'] = False            # still starting: kept
        self.assertEqual(self.policy(record(7), {}), ('delink', 'capacity'))
        self.current = None
        self.assertEqual(self.policy(record(7), {}), ('delink', 'player_zone_unknown'))

    def test_ports_reuse_a_stopped_zones_port(self):
        self.maps = {1: {'ready': True, 'port': 7001}, 7: {'ready': True, 'port': 7004}}
        self.current = 1
        self.assertEqual(self.policy(record(8), {})[1], {'tree': 'zones', 'evict': [7], 'port': 7004,
                                                         'budget_seconds': zone_travel.START_SECONDS})
        self.maps = {7: {'ready': True, 'port': 7001}}  # a fixed port held by another map
        self.assertEqual(self.policy(record(1), {}), ('delink', 'no_port'))

    def test_capacity_is_validated(self):
        with self.assertRaises(ValueError):
            zone_travel.ZoneTravelPolicy(tree_for=dict.get, running=dict, occupied=lambda: None, capacity=0)



class ZoneIndex(unittest.TestCase):
    def test_index_is_the_all_map_closure(self):
        import hashlib
        import json
        import zone_index
        source = ROOT / 'docs/android-evidence/zone-assets-1.0.0-all-maps.json'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), zone_index.SOURCE_SHA256)
        maps = json.loads(source.read_text())['maps']
        self.assertEqual({row['map_id'] for row in maps}, set(zone_index.ZONES))
        union = sorted({name for row in maps for name in row['new_geometry_files']})
        self.assertEqual(list(zone_index.COLLISION_FILES), union)
        self.assertEqual(hashlib.sha256(json.dumps(union, separators=(',', ':')).encode()).hexdigest(),
                         zone_index.COLLISION_FILES_SHA256)
        for row in maps:
            key, world, complete = zone_index.ZONES[row['map_id']]
            self.assertEqual((key, world, complete), (row['key'], row['map'].split('/')[-1][:-4],
                                                      row['source_graph_complete']))
        self.assertEqual(zone_index.world(6), 'city_02_01')

    def test_session_budget_accepts_any_static_zone_only_in_stock_travel(self):
        import character_session_budget as budget
        self.assertTrue(budget.static_zone(6) and budget.static_zone(101) and budget.static_zone(626))
        self.assertFalse(budget.static_zone(2) or budget.static_zone(True) or budget.static_zone('6'))



class AppOptionAndCi(unittest.TestCase):
    def test_app_option_default_on_sets_both_guest_switches(self):
        java = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
        runtime = (java / 'ClientRuntime.java').read_text()
        self.assertIn('.getBoolean("stock-zone-travel", true)', runtime)
        self.assertIn('"COH_EXTERNAL_MAPS="+(stockTravelRequested?"1":"0"), '
                      '"COH_STOCK_TRAVEL="+(stockTravelRequested?"1":"0")', runtime)
        self.assertIn('ClientRuntime.stockTravelEnabled(this)', (java / 'ClientActivity.java').read_text())
        import external_map_supervisor
        self.assertEqual((external_map_supervisor.ENABLE_ENVIRONMENT, zone_travel.ENABLE_ENVIRONMENT),
                         ('COH_EXTERNAL_MAPS', 'COH_STOCK_TRAVEL'))

    def test_ci_input_requires_the_external_maps_dbserver(self):
        import os
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT / 'armport/app'))
        import interactive_host
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("COH_STOCK_TRAVEL: ${{ inputs.stock_travel && '1' || '' }}", workflow)
        for value, expected in (('', False), ('0', False), ('1', True)):
            with patch.dict(os.environ, {'COH_STOCK_TRAVEL': value}):
                self.assertEqual(interactive_host.stock_travel_requested(), expected)
        with patch.dict(os.environ, {'COH_STOCK_TRAVEL': 'yes'}), self.assertRaises(ValueError):
            interactive_host.stock_travel_requested()


if __name__ == '__main__':
    unittest.main()

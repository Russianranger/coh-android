"""0.13.84: the mission maps' collision leaves and how the shared zone tree takes them."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import mission_index  # noqa: E402
import zone_index  # noqa: E402

EVIDENCE = ROOT / 'docs/android-evidence/mission-asset-audit-all-20261124.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


class MissionIndex(unittest.TestCase):
    def test_the_index_is_the_audits_list(self):
        raw = EVIDENCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), mission_index.SOURCE_SHA256)
        audit = json.loads(raw)
        self.assertEqual([row['name'] for row in audit['mission_only_geometry_files']],
                         list(mission_index.COLLISION_FILES))
        self.assertEqual((audit['maps_audited'], audit['mission_map_files'], audit['maps_with_errors']), (5105, 5105, 0))
        self.assertEqual(audit['geometry_in_neither_baseline_nor_zones_supplement'], [])
        self.assertEqual(audit['geometry_not_in_retained_baseline'],
                         audit['geometry_already_among_the_zone_tree_leaves'] + len(mission_index.COLLISION_FILES))
        self.assertEqual(audit['zone_index_collision_files_sha256'], zone_index.COLLISION_FILES_SHA256)
        self.assertEqual(hashlib.sha256(canonical(list(mission_index.COLLISION_FILES))).hexdigest(),
                         mission_index.COLLISION_FILES_SHA256)

    def test_every_leaf_is_an_original_file_of_the_published_zone_pack_and_none_is_a_zone_leaf(self):
        audit = json.loads(EVIDENCE.read_bytes())
        names = mission_index.COLLISION_FILES
        self.assertEqual(len(names), 123)
        self.assertEqual(list(names), sorted(set(names)))
        self.assertFalse(set(names) & set(zone_index.COLLISION_FILES))
        for name in names:
            self.assertTrue(name.startswith('data/object_library/') and name.endswith('.geo'), name)
        # zone_asset_package.install takes one selection of at most 4096 leaves.
        self.assertLessEqual(len(names) + len(zone_index.COLLISION_FILES), 4096)
        # The audit took each file's size from the published pack's manifest (not in the repository;
        # build 45519716880 failed here when this test read that file).
        self.assertEqual(sum(row['bytes'] for row in audit['mission_only_geometry_files']), 24356646)
        self.assertEqual(audit['mission_only_geometry_bytes'], 24356646)
        manifest = ROOT / 'assets/zones-world-supplement-manifest.json'
        if manifest.is_file():
            files = json.loads(manifest.read_text())['files']
            self.assertEqual(audit['zones_supplement_files_sha256'],
                             hashlib.sha256(canonical(files)).hexdigest())
            for row in audit['mission_only_geometry_files']:
                self.assertEqual(files[row['name']]['bytes'], row['bytes'], row['name'])

    def test_the_zone_tree_takes_them_only_with_the_option_under_its_own_cache_identity(self):
        import local_character_server as server
        names, identity, count = server.zone_tree_collision(False)
        self.assertEqual((names, identity, count), (zone_index.COLLISION_FILES,
                         {'zone_collision_sha256': zone_index.COLLISION_FILES_SHA256}, 0))
        names, identity, count = server.zone_tree_collision(True)
        self.assertEqual(names, zone_index.COLLISION_FILES + mission_index.COLLISION_FILES)
        self.assertEqual(identity, {'zone_collision_sha256': zone_index.COLLISION_FILES_SHA256,
                                    'mission_collision_sha256': mission_index.COLLISION_FILES_SHA256})
        self.assertEqual((count, len(set(names))), (123, len(names)))
        source = (ROOT / 'android/guest/local_character_server.py').read_text()
        # One selection for the leaves, the cache identity and the install; nothing else names the lists.
        self.assertIn("missions = os.environ.get('COH_MISSION_MAPS') == '1'\n"
                      "        collision_names, collision_identity, mission_leaves = zone_tree_collision(missions)\n"
                      "        leaves = {name: self.zone_asset_document['files'][name] for name in collision_names}", source)
        self.assertIn("identity = dict(source_identity, map_scope='shared_static_zones_v1', **collision_identity)", source)
        self.assertIn("collision_names=collision_names)", source)
        body = source[source.index('    def _prepare_zone_runtime(self):'):source.index('    def zone_graph_order(self, near):')]
        self.assertNotIn('zone_index.COLLISION_FILES', body)

    def test_the_index_ships_with_the_guest(self):
        for name in ('armport/app/stage_app_assets.py', 'armport/app/build_thor_apk.py'):
            self.assertIn("'mission_index.py'", (ROOT / name).read_text(), name)


if __name__ == '__main__':
    unittest.main()

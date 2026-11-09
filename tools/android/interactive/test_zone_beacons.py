"""Zone graphs: reject partial native evidence, tampered packages and a mismatched shared zone tree.

Thor 0.13.63 (Mercy Island): "Beacon file not loaded for map:
maps/City_Zones/V_City_01_01/V_City_01_01.txt"; pets and NPCs could not walk to a target.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
import generate_zone_beacons as host

MAP_ID = 71
NAMES = host.zone(MAP_ID)
guest = host.manifest_validator()
LOG = (b'COH_ZONE_BEACON_MAP_V1 map=maps/city_zones/v_city_01_01/v_city_01_01.txt\n'
       b'COH_ZONE_COLLISION_LOAD_V1 missing_groups=0 missing_root_models=0\n'
       b'COH_ZONE_BEACON_FRESH_WORLD_V1 crc=0x12345678\n'
       b'COH_ZONE_BEACON_NATIVE_V1 crc=0x12345678 combat=8000 connected=7900 ground=9000 raised=1 blocks=22 paths=32\n')
DATE = struct.pack('<iII', 9, 0, 0x12345678)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def complete_package(root, inputs=None, change=None, graph=b'complete native graph fixture'):
    native = host.native_evidence(LOG, DATE, NAMES)
    if inputs is None:
        inputs = {'data/object_library/input%03d.geo' % i: pin(b'input') for i in range(100)}
        inputs['data/' + NAMES['map']] = pin(b'map')
    identity = hashlib.sha256(host.canonical(inputs)).hexdigest()
    value = {'format': 1, 'role': host.ROLE, 'map': NAMES['map'], 'map_id': MAP_ID,
             'source_commit': '0b75ade0c801735e10c5798f641948a45cc50488',
             'data_commit': 'd51533ec8e6a9cf726b9214968077a05fdcf19f3',
             'files': {NAMES['graph']: pin(graph), NAMES['date']: pin(DATE)}, 'native': native,
             'input_files': inputs, 'input_files_sha256': identity, 'runtime_graph_readback': True,
             'physical_zoning_verified': False,
             'input_profiles': {name: {'native': native, 'input_files_sha256': identity} for name in host.PROFILES},
             'zone_collision': {'archive': {}, 'manifest': {}, 'files_sha256': host.zone_index.COLLISION_FILES_SHA256,
                                'files': {name: pin(name.encode()) for name in host.zone_index.COLLISION_FILES}}}
    if change: change(value)
    raw = host.canonical(value); (root / NAMES['manifest']).write_bytes(raw)
    with zipfile.ZipFile(root / NAMES['archive'], 'w') as archive:
        for name, data in ((NAMES['graph'], graph), (NAMES['date'], DATE), (NAMES['manifest'], raw)):
            archive.writestr(name, data)
    report = {'status': 'passed', 'cleanup_complete': True, 'owned_roles': 0, 'map': NAMES['map'], 'map_id': MAP_ID,
              'native_worker_spawning_allowed': False, 'build_input': host.producer.expected(),
              'repository_commit': 'a' * 40, 'manifest': host.pin(root / NAMES['manifest']),
              'archive': host.pin(root / NAMES['archive']), 'native': value['native'],
              'profile_proofs': value['input_profiles'],
              'source_files': {name: host.pin(host.ROOT / name) for name in host.SOURCE_FILES}}
    (root / NAMES['report']).write_bytes(host.canonical(report))
    (root / NAMES['lock']).write_bytes(host.canonical({'format': 1, 'map_id': MAP_ID,
                                                       'manifest': report['manifest'], 'archive': report['archive']}))
    return value


class ZoneGraphPackageTests(unittest.TestCase):
    def test_complete_package_validates_without_android_imports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); value = complete_package(root)
            script = '''import builtins,sys
original=builtins.__import__
def portable(name,*args,**kwargs):
    if name in ('fcntl','atlas_world_assets','client_startup_diagnostic','presentation_diagnostic','diagnostic'):
        raise ModuleNotFoundError('Android-only import attempted: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=portable
sys.path.insert(0,sys.argv[1])
import generate_zone_beacons as host
host.validate_package(sys.argv[2],71,'a'*40)
print('complete portable package passed')
'''
            result = subprocess.run([sys.executable, '-c', script, str(Path(host.__file__).parent), str(root)],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('complete portable package passed', result.stdout)
            self.assertEqual(host.validate_package(root, MAP_ID, 'a' * 40), value)

    def test_validation_retains_native_input_and_tree_gates(self):
        changes = (lambda value: value['native'].update(native_pathfinder_successes=31),
                   lambda value: value['native'].update(native_collision_load_verified=False),
                   lambda value: value['native'].update(missing_root_models=1),
                   lambda value: value['input_profiles'].pop('cold_world'),
                   lambda value: value.update(source_commit='b' * 40),
                   lambda value: value.update(map_id=5),
                   lambda value: value['input_files'].pop('data/' + NAMES['map']),
                   lambda value: value['zone_collision']['files'].popitem(),
                   lambda value: value['zone_collision'].update(files_sha256='0' * 64))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for change in changes:
                complete_package(root, change=change)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    host.validate_package(root, MAP_ID, 'a' * 40)

    def test_native_witness_requires_the_map_collision_crc_readback_and_32_routes(self):
        self.assertTrue(host.native_evidence(LOG, DATE, NAMES)['native_collision_load_verified'])
        for invalid in (LOG.replace(b'paths=32', b'paths=31'), LOG.replace(b'missing_groups=0', b'missing_groups=1'),
                        LOG.replace(b'FRESH_WORLD_V1', b'NO_FRESH_WORLD'), LOG + LOG,
                        LOG.replace(b'v_city_01_01/v_city_01_01', b'city_01_02/city_01_02'),
                        LOG.replace(b'COH_ZONE_BEACON_MAP_V1', b'COH_ZONE_BEACON_MAP_V0'),
                        LOG + b'Host zone collision missing group x in y\n'):
            with self.assertRaises(ValueError):
                host.native_evidence(invalid, DATE, NAMES)
        with self.assertRaises(ValueError):
            host.native_evidence(LOG, struct.pack('<iII', 9, 0, 0x12345679), NAMES)

    def test_roles_name_the_map_and_only_proofs_verify(self):
        with unittest.mock.patch.dict(host.os.environ, {'COH_ZONE_BEACON_VERIFY_ONLY': '1', 'COH_KINGS_ROW_BEACON_VERIFY_ONLY': '1',
                                                         'COH_ATLAS_BEACON_VERIFY_ONLY': '1'}):
            generation = host.role_environment(NAMES)
            self.assertEqual(generation['COH_ZONE_BEACON_MAP'], 'maps/city_zones/v_city_01_01/v_city_01_01.txt')
            for name in ('COH_ZONE_BEACON_VERIFY_ONLY', 'COH_KINGS_ROW_BEACON_VERIFY_ONLY', 'COH_ATLAS_BEACON_VERIFY_ONLY'):
                self.assertNotIn(name, generation)
            self.assertEqual(host.role_environment(NAMES, True)['COH_ZONE_BEACON_VERIFY_ONLY'], '1')

    def test_only_defined_shared_tree_zones_are_accepted(self):
        for map_id in (1, 5, 3, 0, 9999):
            with self.subTest(map_id=map_id), self.assertRaises(ValueError):
                host.zone(map_id)
        self.assertEqual(NAMES['graph'], 'data/server/maps/city_zones/v_city_01_01/v_city_01_01.txt.v8.bcn')
        self.assertEqual(NAMES['archive'], 'zone-beacons-71.zip')

    def test_runtime_lock_refuses_modified_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest = root / NAMES['manifest']; lock = root / NAMES['lock']
            manifest.write_text('{}')
            lock.write_text(json.dumps({'format': 1, 'map_id': MAP_ID, 'manifest': host.pin(manifest), 'archive': {}}))
            manifest.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'APK-owned lock'):
                guest.read_manifest(manifest, lock, MAP_ID)

    def test_input_paths_do_not_admit_other_maps_or_traversal(self):
        self.assertTrue(guest.input_name('data/' + NAMES['map'], MAP_ID))
        for value in ('data/maps/city_zones/city_01_01/city_01_01.txt', 'data/maps/city_zones/city_01_02/city_01_02.txt',
                      'data/object_library/../../bad.geo', '/data/object_library/a.geo', 'data/object_library/a.dll'):
            self.assertFalse(guest.input_name(value, MAP_ID))

    def test_generator_patch_selects_its_map_from_the_driver(self):
        patch = (host.ROOT / host.producer.PATCH).read_text()
        self.assertIn('getenv("COH_ZONE_BEACON_MAP")', patch)
        self.assertIn('COH_ZONE_BEACON_VERIFY_ONLY', patch)
        self.assertNotIn('city_01_02', patch)
        self.assertNotIn('+           strdup("maps/', patch)
        receipt = host.producer.expected()
        self.assertEqual((receipt['build_role'], receipt['contract']['map_environment']),
                         ('host_only_zone_beacon_generator', 'COH_ZONE_BEACON_MAP'))


@unittest.skipIf(os.name == 'nt', 'The guest installer uses Android-side (POSIX) helpers')
class ZoneGraphInstallTests(unittest.TestCase):
    class Context:
        def check(self):
            pass

    def setUp(self):
        sys.path.insert(0, str(host.ROOT / 'android/guest'))
        import zone_beacon_package
        self.package = zone_beacon_package
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.runtime, self.assets = base / 'runtime', base / 'assets'
        (self.runtime / 'data/server').mkdir(parents=True); self.assets.mkdir()
        inputs = {}
        for i in range(101):
            name = 'data/object_library/zone/part%03d.geo' % i
            inputs[name] = self.write(name, b'geo %d' % i)
        inputs['data/' + NAMES['map']] = self.write('data/' + NAMES['map'], b'map')
        inputs['data/tricks/zone.txt'] = self.write('data/tricks/zone.txt', b'trick')
        self.value = complete_package(self.assets, inputs=dict(sorted(inputs.items())))

    def write(self, name, raw):
        # Installed world leaves are read-only, as the phone's tree keeps them.
        path = self.runtime / name; path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists(): path.chmod(0o644)
        path.write_bytes(raw); path.chmod(0o444)
        return pin(raw)

    def test_graph_installs_into_the_shared_zone_tree(self):
        self.assertEqual(self.package.available(self.assets), (MAP_ID,))
        result = self.package.install(self.assets, self.runtime, MAP_ID, context=self.Context(), imported_inputs_readonly=True)
        self.assertEqual((result['status'], result['installed_files'], result['map_id']), ('installed_verified_graph', 2, MAP_ID))
        self.assertEqual((self.runtime / NAMES['graph']).read_bytes(), b'complete native graph fixture')
        self.assertEqual((self.runtime / NAMES['date']).read_bytes(), DATE)
        again = self.package.install(self.assets, self.runtime, MAP_ID, context=self.Context(), imported_inputs_readonly=True)
        self.assertEqual(again['status'], 'reused_verified_graph')

    def test_a_different_tree_installs_nothing(self):
        self.write('data/object_library/zone/part007.geo', b'other geometry')
        with self.assertRaisesRegex(ValueError, 'Zone collision input differs'):
            self.package.install(self.assets, self.runtime, MAP_ID, context=self.Context(), imported_inputs_readonly=True)
        self.assertFalse((self.runtime / NAMES['graph']).exists())

    def test_an_extra_leaf_in_the_tree_is_refused(self):
        self.write('data/object_library/zone/extra.geo', b'extra')
        with self.assertRaises(ValueError):
            self.package.install(self.assets, self.runtime, MAP_ID, context=self.Context(), imported_inputs_readonly=True)
        self.assertFalse((self.runtime / NAMES['graph']).exists())

    def test_without_the_archive_no_graph_is_available(self):
        (self.assets / NAMES['archive']).unlink()
        self.assertEqual(self.package.available(self.assets), ())


@unittest.skipIf(os.name == 'nt', 'The guest server uses Android-side (POSIX) helpers')
class ZoneTreeGraphTests(unittest.TestCase):
    """The shared zone tree installs every carried graph; one that does not match is skipped, not fatal."""

    def setUp(self):
        sys.path.insert(0, str(host.ROOT / 'android/guest'))
        import local_character_server
        import zone_beacon_package
        self.server, self.package = local_character_server, zone_beacon_package
        self.owner = unittest.mock.Mock(); self.owner.owner.args.assets = Path('/assets')

    def run_install(self, install):
        with unittest.mock.patch.object(self.package, 'available', return_value=(MAP_ID,)), \
                unittest.mock.patch.object(self.package, 'install', side_effect=install):
            return self.server.LocalCharacterServer.install_zone_beacon_graphs(self.owner, Path('/tree'))

    def test_a_verified_graph_is_reported_by_map(self):
        graphs = self.run_install(lambda assets, tree, map_id, **kwargs: {'verified': True, 'map_id': map_id,
                                                                          'status': 'installed_verified_graph'})
        self.assertEqual(graphs, {'71': {'verified': True, 'map_id': 71, 'status': 'installed_verified_graph'}})

    def test_a_mismatched_graph_leaves_the_zone_without_pathing(self):
        def mismatch(*args, **kwargs):
            raise ValueError('Zone collision input differs: data/object_library/a.geo')
        graphs = self.run_install(mismatch)
        self.assertEqual(graphs['71']['status'], 'not_installed')
        self.assertFalse(graphs['71']['verified'])
        self.assertIn('Zone collision input differs', graphs['71']['error'])

    def test_cancellation_still_stops_the_session(self):
        def cancelled(*args, **kwargs):
            raise self.server.base.Cancelled('stop')
        with self.assertRaises(self.server.base.Cancelled):
            self.run_install(cancelled)

    def test_no_carried_graph_changes_nothing(self):
        with unittest.mock.patch.object(self.package, 'available', return_value=()):
            self.assertEqual(self.server.LocalCharacterServer.install_zone_beacon_graphs(self.owner, Path('/tree')), {})


if __name__ == '__main__':
    unittest.main()

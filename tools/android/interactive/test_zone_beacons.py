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

    def test_only_encounter_spawn_groups_may_load_as_empty_placeholders(self):
        # Rikti War Zone (run 42743592550): its beacons layer names an encounter group the data lacks.
        group = b'Omni/EncounterSpawns/Universal/EG_DJ_Architect_H_Universal'
        log = LOG + b'COH_ZONE_NONCOLLISION_MISSING_V1 group=' + group + b'\n'
        witness = host.native_evidence(log + b'COH_ZONE_NONCOLLISION_MISSING_V1 group=' + group + b'\r\n', DATE, NAMES)
        self.assertEqual(witness['noncollision_missing_groups'], [group.decode()])
        self.assertEqual(witness['missing_groups'], 0)
        self.assertNotIn('noncollision_missing_groups', host.native_evidence(LOG, DATE, NAMES))
        for other in (b'Omni/Buildings/Tower', b'object_library/city_zones/wall', b'Omni/EncounterSpawns/../x y'):
            with self.subTest(group=other), self.assertRaises(ValueError):
                host.native_evidence(LOG + b'COH_ZONE_NONCOLLISION_MISSING_V1 group=' + other + b'\n', DATE, NAMES)
        patch = (host.ROOT / host.producer.PATCH).read_text()
        self.assertIn('static void beaconHostMissingGroup(const char* name, const char* fname)', patch)
        self.assertIn('!strnicmp(name, "Omni/EncounterSpawns/", 21)', patch)
        self.assertEqual(patch.count('+                        beaconHostMissingGroup(groupLoad->name, fname);'), 1)
        self.assertEqual(patch.count('+                beaconHostMissingGroup(groupLoad->name, fname);'), 1)
        # Missing root geometry and references stay fatal.
        self.assertIn('FatalErrorf("Host zone collision missing root geometry %s"', patch)
        self.assertEqual(patch.count('FatalErrorf("Host zone collision missing reference %s"'), 2)

    def test_the_guest_accepts_only_encounter_placeholders(self):
        def native(value):
            return lambda manifest: (manifest['native'].update(noncollision_missing_groups=value),
                                     [p['native'].update(noncollision_missing_groups=value)
                                      for p in manifest['input_profiles'].values()])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            complete_package(root, change=native(['Omni/EncounterSpawns/Universal/EG_DJ_Architect_H_Universal']))
            guest.read_manifest(root / NAMES['manifest'], root / NAMES['lock'], MAP_ID)
            for bad in ([], ['Omni/Buildings/Tower'], ['Omni/EncounterSpawns/b', 'Omni/EncounterSpawns/a'], 'Omni/EncounterSpawns/a'):
                complete_package(root, change=native(bad))
                with self.subTest(value=bad), self.assertRaises(ValueError):
                    guest.read_manifest(root / NAMES['manifest'], root / NAMES['lock'], MAP_ID)

    def test_roles_name_the_map_and_only_proofs_verify(self):
        with unittest.mock.patch.dict(host.os.environ, {'COH_ZONE_BEACON_VERIFY_ONLY': '1', 'COH_KINGS_ROW_BEACON_VERIFY_ONLY': '1',
                                                         'COH_ATLAS_BEACON_VERIFY_ONLY': '1'}):
            generation = host.role_environment(NAMES)
            self.assertEqual(generation['COH_ZONE_BEACON_MAP'], 'maps/city_zones/v_city_01_01/v_city_01_01.txt')
            for name in ('COH_ZONE_BEACON_VERIFY_ONLY', 'COH_KINGS_ROW_BEACON_VERIFY_ONLY', 'COH_ATLAS_BEACON_VERIFY_ONLY'):
                self.assertNotIn(name, generation)
            self.assertEqual(host.role_environment(NAMES, True)['COH_ZONE_BEACON_VERIFY_ONLY'], '1')

    def test_only_defined_shared_tree_zones_are_accepted(self):
        for map_id in (1, 5, 0, 2, 9999):
            with self.subTest(map_id=map_id), self.assertRaises(ValueError):
                host.zone(map_id)
        self.assertEqual(NAMES['graph'], 'data/server/maps/city_zones/v_city_01_01/v_city_01_01.txt.v8.bcn')
        self.assertEqual(NAMES['archive'], 'zone-beacons-71.zip')

    def test_every_shared_tree_zone_has_a_graph_slot(self):
        # All zones (owner, 2026-11-09): every static zone except Atlas Park and King's Row.
        expected = {map_id: row[1] for map_id, row in host.zone_index.ZONES.items() if map_id not in (1, 5)}
        self.assertEqual(guest.WORLDS, expected)
        self.assertEqual(len(guest.WORLDS), 64)
        for map_id in (3, 14, 85, 626):
            zone = host.zone(map_id)
            world = host.zone_index.world(map_id)
            self.assertEqual(zone['map'], 'maps/city_zones/%s/%s.txt' % (world, world))
            self.assertEqual(zone['archive'], 'zone-beacons-%d.zip' % map_id)

    def test_small_and_large_zone_graphs_fit_their_bounds(self):
        def native(**change):
            return lambda value: (value['native'].update(change), [p['native'].update(change)
                                  for p in value['input_profiles'].values()])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            complete_package(root, change=native(connected_beacons=40, combat_beacons=42, ground_connections=90))
            guest.read_manifest(root / NAMES['manifest'], root / NAMES['lock'], MAP_ID)
            for bad in (dict(connected_beacons=0), dict(ground_connections=0),
                        dict(combat_beacons=guest.MAX_BEACONS + 1, connected_beacons=guest.MAX_BEACONS + 1)):
                complete_package(root, change=native(**bad))
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    guest.read_manifest(root / NAMES['manifest'], root / NAMES['lock'], MAP_ID)
            def size(limit):
                return lambda value: value['files'][NAMES['graph']].update(bytes=limit)
            complete_package(root, change=size(200 * 1024 * 1024))  # above the Atlas-sized 128 MiB bound
            guest.read_manifest(root / NAMES['manifest'], root / NAMES['lock'], MAP_ID)
            complete_package(root, change=size(guest.MAX_GRAPH + 1))
            with self.assertRaises(ValueError):
                guest.read_manifest(root / NAMES['manifest'], root / NAMES['lock'], MAP_ID)

    def test_owned_worker_count_is_bounded_and_given_to_the_native_sentry(self):
        self.assertEqual(host.worker_roles(1), ('worker',))
        self.assertEqual(host.worker_roles(3), ('worker', 'worker2', 'worker3'))
        for invalid in (0, 9, True, '3', 3.0):
            with self.subTest(workers=invalid), self.assertRaises(ValueError):
                host.worker_roles(invalid)
        self.assertEqual(host.role_environment(NAMES, workers=3)['COH_ZONE_BEACON_WORKERS'], '3')
        with unittest.mock.patch.dict(host.os.environ, {'COH_ZONE_BEACON_WORKERS': '7'}):
            self.assertNotIn('COH_ZONE_BEACON_WORKERS', host.role_environment(NAMES))
            self.assertNotIn('COH_ZONE_BEACON_WORKERS', host.role_environment(NAMES, True))
        patch = (host.ROOT / host.producer.PATCH).read_text()
        self.assertIn('getenv("COH_ZONE_BEACON_WORKERS")', patch)
        self.assertIn('-        beacon_client.cpuCount = 1; /* The orchestrator starts exactly one worker. */', patch)
        self.assertIn('+        beacon_client.cpuCount = beaconHostZoneWorkerCount();', patch)
        self.assertIn("value[0] > '8'", patch)
        self.assertEqual(host.producer.expected()['contract']['worker_environment'], 'COH_ZONE_BEACON_WORKERS')
        self.assertIn('MapServer/src/beacon/beaconClient.c', host.producer.FILES)

    def test_worker_summary_counts_each_workers_native_work(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td)
            (evidence / 'worker.log').write_bytes(b'Processing  511 legal areas\nConnecting  20: ..\nConnecting  20: .\n')
            (evidence / 'worker2.log').write_bytes(b'Processing 1110 legal areas\n')
            self.assertEqual(host.worker_summary(evidence, 2), {
                'worker': {'log_bytes': 65, 'blocks': 1, 'beacon_batches': 2},
                'worker2': {'log_bytes': 28, 'blocks': 1, 'beacon_batches': 0}})

    def test_runtime_lock_refuses_modified_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest = root / NAMES['manifest']; lock = root / NAMES['lock']
            manifest.write_text('{}')
            lock.write_text(json.dumps({'format': 1, 'map_id': MAP_ID, 'manifest': host.pin(manifest),
                                        'archive': pin(b'archive')}))
            manifest.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'APK-owned lock'):
                guest.read_manifest(manifest, lock, MAP_ID)
            for bad in ({}, {'format': 1, 'map_id': 72}, {'format': 1, 'map_id': MAP_ID, 'manifest': {}}):
                with self.subTest(lock=bad), self.assertRaisesRegex(ValueError, 'lock differs'):
                    guest.read_manifest(manifest, bad, MAP_ID)

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


class ApkZoneGraphAdmissionTests(unittest.TestCase):
    """The APK takes a graph only from its own successful generation run (stage_app_assets.zone_beacons)."""

    def setUp(self):
        sys.path.insert(0, str(host.ROOT / 'armport/app'))
        import stage_app_assets
        self.stage = stage_app_assets
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.value = complete_package(self.root)

    def run_json(self, **change):
        value = {'id': 42678203754, 'path': '.github/workflows/armport-zone-beacons.yml', 'status': 'completed',
                 'conclusion': 'success', 'head_sha': 'a' * 40}
        value.update(change)
        path = self.root / 'zone-beacons-run.json'; path.write_text(json.dumps(value))
        return path

    def test_a_successful_run_adds_exactly_its_archive_manifest_and_lock(self):
        generated, records = self.stage.zone_beacons(self.root, self.run_json())
        self.assertEqual(set(generated), {NAMES['archive'], NAMES['manifest'], NAMES['lock']})
        self.assertEqual(generated[NAMES['archive']], (self.root / NAMES['archive']).read_bytes())
        record = records[str(MAP_ID)]
        self.assertEqual((record['map'], record['run_id'], record['head_sha'], record['device_validated']),
                         (NAMES['map'], 42678203754, 'a' * 40, False))
        self.assertEqual(record['full_world_crc'], self.value['native']['full_world_crc'])
        # The generator's report stays with the run; the APK carries only what the guest installs.
        self.assertNotIn(NAMES['report'], generated)

    def test_another_workflow_commit_or_unfinished_run_is_refused(self):
        for change in ({'conclusion': 'failure'}, {'status': 'in_progress'}, {'head_sha': 'b' * 40},
                       {'path': '.github/workflows/android-kings-row-native.yml'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.stage.zone_beacons(self.root, self.run_json(**change))

    def test_a_tampered_or_incomplete_package_is_refused(self):
        run = self.run_json()
        with zipfile.ZipFile(self.root / NAMES['archive'], 'a') as archive:
            archive.writestr('data/server/extra.bcn', b'extra')
        with self.assertRaises(ValueError):
            self.stage.zone_beacons(self.root, run)
        complete_package(self.root)
        (self.root / NAMES['lock']).unlink()
        with self.assertRaisesRegex(ValueError, 'Incomplete zone graph package'):
            self.stage.zone_beacons(self.root, run)

    def test_an_artifact_without_a_defined_graph_is_refused(self):
        for key in ('archive', 'manifest', 'lock'):
            (self.root / NAMES[key]).unlink()
        with self.assertRaisesRegex(ValueError, 'holds no graph'):
            self.stage.zone_beacons(self.root, self.run_json())

    def test_graph_payloads_stay_out_of_the_bounded_client_inventory(self):
        source = (host.ROOT / 'armport/app/stage_app_assets.py').read_text()
        self.assertIn("name not in DBSERVER_PAYLOADS + zone_payloads", source)
        builder = (host.ROOT / 'armport/app/build_thor_apk.py').read_text()
        self.assertIn('added_runtime | frozenset(stage_app_assets.zone_beacons(*zone_graphs)[0])', builder)
        self.assertIn("'zone_beacon_package.py'", builder)


@unittest.skipIf(os.name == 'nt', 'The guest installer uses Android-side (POSIX) helpers')
class ZoneGraphInstallTests(unittest.TestCase):
    class Context:
        def check(self):
            pass

    def setUp(self):
        sys.path.insert(0, str(host.ROOT / 'android/guest'))
        import zone_beacon_package
        self.package = zone_beacon_package
        self.package._VERIFIED_INPUTS.clear(); self.package._LOADED_PROOFS.clear()
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.runtime, self.assets, self.objects = base / 'runtime', base / 'assets', base / 'objects'
        (self.runtime / 'data/server').mkdir(parents=True); self.assets.mkdir(); self.objects.mkdir()
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

    def install(self, source=None):
        source = source or self.package.sources(self.assets)[MAP_ID]
        return self.package.install(source, self.runtime, MAP_ID, context=self.Context(), imported_inputs_readonly=True)

    def as_navigation_pack(self, *, version='1.0.0'):
        """The APK carries only the pack descriptor; the app binds the imported objects by SHA-256."""
        files = {}
        for key in ('archive', 'manifest'):
            raw = (self.assets / NAMES[key]).read_bytes(); files['runtime/' + NAMES[key]] = pin(raw)
            (self.objects / pin(raw)['sha256']).write_bytes(raw)
        for key in ('archive', 'manifest', 'lock'):
            (self.assets / NAMES[key]).unlink()
        descriptor = {'format': 1, 'id': 'coh-navigation-maps', 'version': version, 'files': files,
                      'volumes': {'maps': sorted(files)}}
        (self.assets / 'navigation-maps-manifest.json').write_bytes(host.canonical(descriptor))
        return files

    def test_graph_installs_into_the_shared_zone_tree(self):
        self.assertEqual(self.package.available(self.assets), (MAP_ID,))
        result = self.install()
        self.assertEqual((result['status'], result['installed_files'], result['map_id'], result['origin']),
                         ('installed_verified_graph', 2, MAP_ID, 'apk'))
        self.assertEqual((self.runtime / NAMES['graph']).read_bytes(), b'complete native graph fixture')
        self.assertEqual((self.runtime / NAMES['date']).read_bytes(), DATE)
        again = self.install()
        self.assertEqual(again['status'], 'reused_verified_graph')

    def test_the_imported_navigation_pack_supplies_the_graph(self):
        files = self.as_navigation_pack()
        self.assertEqual(self.package.sources(self.assets), {})  # without the app's bind, no pack graph
        found = self.package.sources(self.assets, self.objects)
        self.assertEqual(set(found), {MAP_ID})
        self.assertEqual((found[MAP_ID]['origin'], found[MAP_ID]['version']), ('navigation_map_pack', '1.0.0'))
        self.assertEqual(found[MAP_ID]['lock']['archive'], files['runtime/' + NAMES['archive']])
        result = self.install(found[MAP_ID])
        self.assertEqual((result['status'], result['origin']), ('installed_verified_graph', 'navigation_map_pack'))
        self.assertEqual((self.runtime / NAMES['graph']).read_bytes(), b'complete native graph fixture')

    def test_a_missing_or_short_pack_object_leaves_the_zone_without_a_graph(self):
        files = self.as_navigation_pack()
        archive = self.objects / files['runtime/' + NAMES['archive']]['sha256']
        archive.write_bytes(archive.read_bytes()[:-1])
        self.assertEqual(self.package.sources(self.assets, self.objects), {})
        archive.unlink()
        self.assertEqual(self.package.sources(self.assets, self.objects), {})

    def test_a_pack_object_with_other_bytes_is_refused(self):
        files = self.as_navigation_pack()
        archive = self.objects / files['runtime/' + NAMES['archive']]['sha256']
        raw = bytearray(archive.read_bytes()); raw[-1] ^= 1; archive.write_bytes(bytes(raw))
        found = self.package.sources(self.assets, self.objects)
        with self.assertRaisesRegex(ValueError, 'archive differs'):
            self.install(found[MAP_ID])
        self.assertFalse((self.runtime / NAMES['graph']).exists())

    def test_another_descriptor_is_refused(self):
        self.as_navigation_pack()
        path = self.assets / 'navigation-maps-manifest.json'
        value = json.loads(path.read_bytes()); value['id'] = 'coh-assets'; path.write_bytes(host.canonical(value))
        with self.assertRaisesRegex(ValueError, 'descriptor differs'):
            self.package.sources(self.assets, self.objects)

    def test_a_second_zone_reuses_this_sessions_input_proofs(self):
        first = self.install()
        self.assertGreater(first['input_payload_bytes_hashed'], 0)
        for key in ('graph', 'date', 'marker'):
            target = self.runtime / NAMES[key]; target.chmod(0o644); target.unlink()
        second = self.install()
        self.assertEqual((second['status'], second['input_payload_bytes_hashed']), ('installed_verified_graph', 0))
        # A changed inode is hashed again (and refused when its bytes differ).
        for key in ('graph', 'date', 'marker'):
            target = self.runtime / NAMES[key]; target.chmod(0o644); target.unlink()
        self.write('data/object_library/zone/part007.geo', b'other geometry')
        with self.assertRaisesRegex(ValueError, 'Zone collision input differs'):
            self.install()

    def link_inputs(self):
        """The phone's shared zone tree: every read-only input is a link to the imported data
        (local_character_server.stage_map_data: destination.symlink_to(resolved))."""
        imported = Path(self.temporary.name) / 'import'
        for name in self.value['input_files']:
            path = self.runtime / name; source = imported / name
            source.parent.mkdir(parents=True, exist_ok=True)
            path.rename(source); path.symlink_to(source)
        return imported

    def forget(self, *, graph=True):
        self.package._VERIFIED_INPUTS.clear(); self.package._LOADED_PROOFS.clear()
        for key in ('graph', 'date', 'marker') if graph else ():
            target = self.runtime / NAMES[key]; target.chmod(0o644); target.unlink()

    def test_a_tree_of_per_file_links_installs_as_on_the_phone(self):
        # Thor 0.13.66: "Zone collision input is not a regular file" left Mercy Island without a graph.
        self.link_inputs()
        self.assertTrue((self.runtime / 'data' / NAMES['map']).is_symlink())
        result = self.install()
        self.assertEqual((result['status'], result['input_files_hashed']), ('installed_verified_graph', 103))
        self.assertEqual((self.runtime / NAMES['graph']).read_bytes(), b'complete native graph fixture')

    def test_a_link_to_other_bytes_is_refused(self):
        imported = self.link_inputs()
        source = imported / 'data/object_library/zone/part007.geo'
        source.chmod(0o644); source.write_bytes(b'other geometry'); source.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'Zone collision input differs'):
            self.install()
        self.assertFalse((self.runtime / NAMES['graph']).exists())

    def test_saved_proofs_spare_a_later_session_the_hashes(self):
        imported = self.link_inputs()
        proofs = Path(self.temporary.name) / 'zone-collision-input-proofs.json'
        source = self.package.sources(self.assets)[MAP_ID]
        def install():
            return self.package.install(source, self.runtime, MAP_ID, context=self.Context(),
                                        imported_inputs_readonly=True, proofs=proofs)
        first = install()
        self.assertEqual((first['status'], first['input_files_hashed']), ('installed_verified_graph', 103))
        self.assertEqual(len(json.loads(proofs.read_bytes())['proofs']), 103)
        self.forget()                                     # a later session with a new zone tree
        second = install()
        self.assertEqual((second['status'], second['input_files_hashed'], second['input_payload_bytes_hashed']),
                         ('installed_verified_graph', 0, 0))
        # A replaced input is hashed again, and refused when its bytes differ.
        self.forget()
        replaced = imported / 'data/tricks/zone.txt'
        replaced.unlink(); replaced.write_bytes(b'other'); replaced.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'Zone collision input differs'):
            install()
        # The same bytes in a new file are hashed (one file) and accepted.
        replaced.unlink(); replaced.write_bytes(b'trick'); replaced.chmod(0o444)
        third = install()
        self.assertEqual((third['status'], third['input_files_hashed']), ('installed_verified_graph', 1))

    def test_an_unusable_proof_file_only_costs_the_hashes(self):
        self.link_inputs()
        proofs = Path(self.temporary.name) / 'zone-collision-input-proofs.json'
        source = self.package.sources(self.assets)[MAP_ID]
        for raw in (b'not json', b'{"format":1,"policy":"other","proofs":{}}',
                    b'{"format":1,"policy":"resolved_input_inode_state_v1","proofs":{"1:2":["x",1,[1,2,3,4,5,6]]}}'):
            self.forget(graph=proofs.exists())
            if proofs.exists(): proofs.chmod(0o644)
            proofs.write_bytes(raw)
            result = self.package.install(source, self.runtime, MAP_ID, context=self.Context(),
                                          imported_inputs_readonly=True, proofs=proofs)
            self.assertEqual((result['status'], result['input_files_hashed']), ('installed_verified_graph', 103))

    def test_a_different_tree_installs_nothing(self):
        self.write('data/object_library/zone/part007.geo', b'other geometry')
        with self.assertRaisesRegex(ValueError, 'Zone collision input differs'):
            self.install()
        self.assertFalse((self.runtime / NAMES['graph']).exists())

    def test_an_extra_leaf_in_the_tree_is_refused(self):
        self.write('data/object_library/zone/extra.geo', b'extra')
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse((self.runtime / NAMES['graph']).exists())

    def test_without_the_archive_no_graph_is_available(self):
        (self.assets / NAMES['archive']).unlink()
        self.assertEqual(self.package.available(self.assets), ())
        self.assertEqual(self.package.sources(self.assets), {})


@unittest.skipIf(os.name == 'nt', 'The guest server uses Android-side (POSIX) helpers')
class ZoneTreeGraphTests(unittest.TestCase):
    """Each zone's graph is installed when that zone starts; one that does not match is skipped, not fatal."""

    def setUp(self):
        sys.path.insert(0, str(host.ROOT / 'android/guest'))
        import local_character_server
        import zone_beacon_package
        self.server, self.package = local_character_server, zone_beacon_package
        self.owner = unittest.mock.Mock(); self.owner.owner.args.assets = Path('/assets')
        self.owner.owner.root = Path('/state/diagnostic')
        self.owner.zone_tree_prepared = {'runtime': Path('/tree'), 'preparation': {'beacon_graph': {}}}
        self.sources = {MAP_ID: {'origin': 'navigation_map_pack'}}

    def run_install(self, install, map_id=MAP_ID, environment=None):
        environment = {'COH_NAVIGATION_MAPS': '/opt/coh-navigation'} if environment is None else environment
        with unittest.mock.patch.object(self.package, 'sources', return_value=self.sources) as sources, \
                unittest.mock.patch.object(self.package, 'install', side_effect=install), \
                unittest.mock.patch.dict(self.server.os.environ, environment, clear=False):
            if 'COH_NAVIGATION_MAPS' not in environment:
                self.server.os.environ.pop('COH_NAVIGATION_MAPS', None)
            result = self.server.LocalCharacterServer.install_zone_beacon_graph(self.owner, map_id, Path('/tree'))
            return result, sources

    def test_a_verified_graph_is_reported_by_map_once_per_session(self):
        calls = []
        def install(source, tree, map_id, **kwargs):
            calls.append(map_id)
            self.assertEqual(kwargs['proofs'], Path('/state/diagnostic/zone-collision-input-proofs.json'))
            return {'verified': True, 'map_id': map_id, 'status': 'installed_verified_graph'}
        result, sources = self.run_install(install)
        self.assertEqual((result['status'], result['navigation_map_pack']), ('installed_verified_graph', 'bound'))
        sources.assert_called_once_with(Path('/assets'), '/opt/coh-navigation')
        self.assertIs(self.owner.zone_tree_prepared['preparation']['beacon_graph']['71'], result)
        again, _ = self.run_install(install)
        self.assertIs(again, result)
        self.assertEqual(calls, [MAP_ID])

    def test_a_zone_without_a_graph_starts_as_before(self):
        result, _ = self.run_install(lambda *args, **kwargs: self.fail('no install'), map_id=72, environment={})
        self.assertEqual((result['status'], result['verified'], result['navigation_map_pack']),
                         ('no_graph', False, 'not_imported'))

    def test_a_mismatched_graph_leaves_the_zone_without_pathing(self):
        def mismatch(*args, **kwargs):
            raise ValueError('Zone collision input differs: data/object_library/a.geo')
        result, _ = self.run_install(mismatch)
        self.assertEqual((result['status'], result['verified']), ('not_installed', False))
        self.assertIn('Zone collision input differs', result['error'])

    def test_an_unexpected_pack_location_is_refused_without_stopping_the_zone(self):
        result, _ = self.run_install(lambda *args, **kwargs: self.fail('no install'),
                                     environment={'COH_NAVIGATION_MAPS': '/tmp/elsewhere'})
        self.assertEqual(result['status'], 'not_installed')
        self.assertIn('Unexpected navigation map location', result['error'])

    def test_cancellation_still_stops_the_session(self):
        def cancelled(*args, **kwargs):
            raise self.server.base.Cancelled('stop')
        with self.assertRaises(self.server.base.Cancelled):
            self.run_install(cancelled)

    def test_atlas_and_kings_row_are_not_shared_tree_zones(self):
        for map_id in (1, 5):
            result, _ = self.run_install(lambda *args, **kwargs: self.fail('no install'), map_id=map_id)
            self.assertIsNone(result)

    def test_each_shared_tree_zone_start_installs_its_graph_first(self):
        source = (host.ROOT / 'android/guest/character_zoning.py').read_text()
        self.assertIn("runtime = self.prepare_zone_runtime()['runtime']\n"
                      "                # Its navigation graph, before its MapServer loads the map (pets and NPCs path).\n"
                      "                self.install_zone_beacon_graph(map_id, runtime)", source)
        server = (host.ROOT / 'android/guest/local_character_server.py').read_text()
        self.assertNotIn('self.install_zone_beacon_graphs(target)', server)


if __name__ == '__main__':
    unittest.main()

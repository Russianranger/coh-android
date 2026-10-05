"""Exercise actual server staging across pre-visual and supplemented profiles.

The fixture supplies tiny immutable leaves and a mocked native file-copy step;
LocalCharacterServer.prepare_runtime, stage_map_data and ServerDataCache execute
their production code. These are source/layout checks, not native CRC proofs.
"""
import json
import hashlib
import os
from pathlib import Path
import unittest

import test_server_worktree_reuse as retained_fixture
import test_atlas_beacon_package as beacon_fixture


SUPPLEMENTAL_GEOMETRY = {
    'object_library/beacon_profile/building.geo': b'qualified-building-geometry',
    'object_library/beacon_profile/prop.geo': b'qualified-prop-geometry',
}


class BeaconRuntimeStagingProfileTests(unittest.TestCase):
    def setUp(self):
        self.fixture = retained_fixture.ServerWorktreeReuseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def prepare(self, sequence):
        server = self.fixture.make(sequence)
        receipt = self.fixture.prepare(server)
        self.addCleanup(self.close_if_owned, server)
        return server, receipt

    def close_if_owned(self, server):
        if server.data_cache.record is not None and server.data_cache.record['status'] == 'checked_out':
            self.fixture.close(server)

    def install_client_geometry(self, names=SUPPLEMENTAL_GEOMETRY):
        for name in names:
            path = self.fixture.data / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(SUPPLEMENTAL_GEOMETRY[name])
            path.chmod(0o444)
            os.utime(path, (1767225600, 1767225600))

    @staticmethod
    def supplemental_inventory(server):
        return {name for name in SUPPLEMENTAL_GEOMETRY
                if (server.runtime / 'data' / name).exists()}

    @staticmethod
    def refuse_fixture_generation(server):
        # Exercise the ordinary guarded fallback without changing source inputs
        # or deletion/reset semantics. The rejected generation remains present.
        marker = server.data_cache.marker
        record = json.loads(marker.read_text())
        record['status'] = 'invalid_for_profile_control'
        marker.write_text(json.dumps(record))
        return marker.parent

    def test_warm_reuse_keeps_pre_visual_geometry_and_generated_server_caches(self):
        cold, cold_receipt = self.prepare(1)
        self.assertFalse(cold_receipt['server_data_cache']['reused'])
        self.assertEqual(self.supplemental_inventory(cold), set())
        cache = cold.runtime / 'data/server/bin/preserved.bin'
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b'accepted-private-generated-cache')
        data_inode = (cold.runtime / 'data').stat().st_ino
        cold_key = cold.data_cache.key
        self.fixture.close(cold)

        self.install_client_geometry()
        warm, warm_receipt = self.prepare(2)
        self.assertTrue(warm_receipt['server_data_cache']['reused'])
        self.assertEqual(warm.data_cache.key, cold_key)
        self.assertEqual((warm.runtime / 'data').stat().st_ino, data_inode)
        self.assertEqual(self.supplemental_inventory(warm), set())
        self.assertEqual((warm.runtime / 'data/server/bin/preserved.bin').read_bytes(),
                         b'accepted-private-generated-cache')
        self.assertTrue(all((self.fixture.data / name).is_file()
                            for name in SUPPLEMENTAL_GEOMETRY))

    def test_guarded_cache_fallback_mirrors_all_already_installed_client_geometry(self):
        cold, _ = self.prepare(1)
        self.fixture.close(cold)
        self.install_client_geometry()
        rejected = self.refuse_fixture_generation(cold)

        rebuilt, receipt = self.prepare(2)
        self.assertFalse(receipt['server_data_cache']['reused'])
        self.assertIn('reuse_refused', receipt['server_data_cache'])
        self.assertEqual(self.supplemental_inventory(rebuilt), set(SUPPLEMENTAL_GEOMETRY))
        self.assertTrue(rejected.is_dir(), 'Fallback must preserve the refused generation')
        for name, raw in SUPPLEMENTAL_GEOMETRY.items():
            path = rebuilt.runtime / 'data' / name
            self.assertTrue(path.is_symlink())
            self.assertEqual(path.resolve(), (self.fixture.data / name).resolve())
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(path.stat().st_mode & 0o222, 0)

    def test_partial_source_install_is_a_real_mixed_profile_not_an_all_profile(self):
        cold, _ = self.prepare(1)
        self.fixture.close(cold)
        one = next(iter(SUPPLEMENTAL_GEOMETRY))
        self.install_client_geometry((one,))
        self.refuse_fixture_generation(cold)

        rebuilt, receipt = self.prepare(2)
        self.assertFalse(receipt['server_data_cache']['reused'])
        self.assertEqual(self.supplemental_inventory(rebuilt), {one})
        self.assertNotEqual(self.supplemental_inventory(rebuilt), set(SUPPLEMENTAL_GEOMETRY))


class BeaconQualifiedProfileInstallerTests(unittest.TestCase):
    """Use real guest staging/installation with explicitly synthetic graph proofs."""
    def setUp(self):
        self.staging = retained_fixture.ServerWorktreeReuseTests()
        self.staging.setUp()
        self.addCleanup(self.staging.doCleanups)
        self.beacon = beacon_fixture.AtlasBeaconPackageTests()
        self.beacon.setUp()
        self.addCleanup(self.beacon.doCleanups)
        for name, raw in self.beacon.inputs.items():
            self.staging.source(name.removeprefix('data/'), raw.decode())
        (self.staging.data / 'tricks').mkdir()
        self.beacon.value['stock_mapserver_sha256'] = hashlib.sha256(
            (self.staging.map_dir / 'MapServer.exe').read_bytes()).hexdigest()
        self.beacon.freeze()

    def prepare(self, sequence):
        server = self.staging.make(sequence)
        receipt = self.staging.prepare(server)
        self.addCleanup(self.close_if_owned, server)
        self.beacon.runtime = server.runtime
        return server, receipt

    def close_if_owned(self, server):
        if server.data_cache.record is not None and server.data_cache.record['status'] == 'checked_out':
            self.staging.close(server)

    def install_client_optional(self, names=None):
        selected = self.beacon.optional_inputs if names is None else names
        targets = beacon_fixture.package.actual_targets(self.staging.work, selected, beacon_fixture.Context())
        for name, path in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.beacon.optional_inputs[name])
            path.chmod(0o444)
            os.utime(path, (1767225600, 1767225600))

    def mixed_staging_directories(self):
        for relative, spelling in (
                ('object_library/test', 'Test'), ('object_library', 'Object_Library'),
                ('maps/city_zones/city_01_01', 'City_01_01'),
                ('maps/city_zones', 'City_Zones'), ('maps', 'Maps'), ('tricks', 'Tricks')):
            target = self.staging.data/relative
            target.rename(target.with_name(spelling))

    @staticmethod
    def mixed_graph_parent(server):
        (server.runtime/'data/server/Maps/City_Zones/City_01_01').mkdir(parents=True)

    def assert_private_graph_absent(self, server):
        self.assert_no_graph_installed()
        self.assertFalse((server.runtime/'data/server/Maps/City_Zones/City_01_01/city_01_01.txt.v8.bcn').exists())


    def fallback_server(self, names=None):
        cold, _ = self.prepare(1)
        self.staging.close(cold)
        self.install_client_optional(names)
        BeaconRuntimeStagingProfileTests.refuse_fixture_generation(cold)
        return self.prepare(2)[0]

    def assert_no_graph_installed(self):
        package = beacon_fixture.package
        self.assertFalse((self.beacon.runtime / package.GRAPH).exists())
        self.assertFalse((self.beacon.runtime / package.MARKER).exists())

    def test_existing_cold_cache_selects_and_reuses_only_the_qualified_none_profile(self):
        cold, _ = self.prepare(1)
        first = self.beacon.install()
        self.assertEqual(first['server_geometry_profile'], 'base_world')
        self.staging.close(cold)
        self.install_client_optional()

        warm, receipt = self.prepare(2)
        self.assertTrue(receipt['server_data_cache']['reused'])
        selected, files = beacon_fixture.package.select_profile(
            warm.runtime, self.beacon.value, beacon_fixture.Context())
        self.assertEqual(selected, 'base_world')
        self.assertEqual(files, self.beacon.value['input_files'])
        self.assertTrue(all((self.staging.data / name.removeprefix('data/')).is_file()
                            for name in self.beacon.optional_inputs))
        reused = self.beacon.install()
        self.assertEqual(reused['server_geometry_profile'], 'base_world')
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)

    def test_normal_cache_fallback_selects_only_the_qualified_complete_visual_profile(self):
        server = self.fallback_server()
        selected, files = beacon_fixture.package.select_profile(
            server.runtime, self.beacon.value, beacon_fixture.Context())
        self.assertEqual(selected, 'base_world_visual')
        self.assertEqual(files, {**self.beacon.value['input_files'],
                                 **self.beacon.value['optional_input_files']})
        installed = self.beacon.install()
        self.assertEqual(installed['server_geometry_profile'], 'base_world_visual')
        self.assertEqual(installed['input_files_checked'], len(files))
        self.assertEqual(installed['input_payload_bytes_hashed'], sum(row['bytes'] for row in files.values()))
        marker = json.loads((server.runtime / beacon_fixture.package.MARKER).read_bytes())
        self.assertEqual(marker['server_geometry_profile'], 'base_world_visual')

    def test_mixed_real_staging_profile_is_refused_without_graph_or_private_cache_changes(self):
        server = self.fallback_server((next(iter(self.beacon.optional_inputs)),))
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-refusal')
        with self.assertRaisesRegex(ValueError, 'Partial optional Atlas geometry'):
            self.beacon.install()
        self.assert_no_graph_installed()
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-refusal')

    def test_all_optional_names_with_wrong_readonly_bytes_cannot_masquerade_as_complete_profile(self):
        server = self.fallback_server()
        path = server.runtime / next(iter(self.beacon.optional_inputs))
        source = path.resolve(); source.chmod(0o600)
        source.write_bytes(b'wrong-optional-geometry'); source.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'Actual Atlas collision/group input differs'):
            self.beacon.install()
        self.assert_no_graph_installed()

    def test_unlisted_collision_geometry_refuses_even_a_complete_optional_profile(self):
        server = self.fallback_server()
        extra = server.runtime / 'data/object_library/foreign.geo'
        extra.write_bytes(b'unqualified collision input'); extra.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.beacon.install()
        self.assert_no_graph_installed()

    def test_real_mixed_case_cold_cache_and_warm_reuse_preserve_the_none_profile(self):
        self.mixed_staging_directories()
        cold, _ = self.prepare(1)
        self.mixed_graph_parent(cold)
        first = self.beacon.install()
        self.assertEqual(first['server_geometry_profile'], 'base_world')
        marker = json.loads((cold.runtime/'data/server/atlas-beacon-installed.json').read_bytes())
        self.assertEqual(marker['input_fingerprints']['data/object_library/test/g1.geo']['path'],
                         'data/Object_Library/Test/g1.geo')
        self.staging.close(cold)
        self.install_client_optional()
        warm, receipt = self.prepare(2)
        self.assertTrue(receipt['server_data_cache']['reused'])
        reused = self.beacon.install()
        self.assertEqual(reused['server_geometry_profile'], 'base_world')
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)
        self.assertFalse((warm.runtime/'data/object_library').exists())
        self.assertFalse((warm.runtime/'data/server/maps').exists())

    def test_real_mixed_case_complete_source_and_warm_cache_reuse_the_full_profile(self):
        self.mixed_staging_directories(); self.install_client_optional()
        cold, _ = self.prepare(1)
        self.mixed_graph_parent(cold)
        first = self.beacon.install()
        self.assertEqual(first['server_geometry_profile'], 'base_world_visual')
        self.staging.close(cold)
        warm, receipt = self.prepare(2)
        self.assertTrue(receipt['server_data_cache']['reused'])
        reused = self.beacon.install()
        self.assertEqual(reused['server_geometry_profile'], 'base_world_visual')
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)
        self.assertFalse((warm.runtime/'data/object_library').exists())

    def test_real_staged_case_variant_graph_refuses_without_private_cache_changes(self):
        self.mixed_staging_directories()
        server, _ = self.prepare(1)
        self.mixed_graph_parent(server)
        private = server.runtime/'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-case-refusal')
        graph = server.runtime/'data/server/Maps/City_Zones/City_01_01/CITY_01_01.TXT.v8.bcn'
        graph.write_bytes(b'existing graph must survive case refusal')
        with self.assertRaisesRegex(beacon_fixture.package.world.client.base.DiagnosticError, 'Case-conflicting world leaf'):
            self.beacon.install()
        self.assert_private_graph_absent(server)
        self.assertEqual(graph.read_bytes(), b'existing graph must survive case refusal')
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-case-refusal')
        self.assertFalse((server.runtime/'data/server/maps').exists())

    def test_swapped_raw_source_and_physical_digests_refuse_before_cache_or_graph_changes(self):
        server, _ = self.prepare(1)
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-digest-refusal')
        identity = self.beacon.value['input_identity']
        raw = identity['visual_object_geometry_sha256']
        physical = identity['optional_physical_geometry_sha256']
        self.assertNotEqual(raw, physical)
        identity['visual_object_geometry_sha256'] = physical
        identity['optional_physical_geometry_sha256'] = raw
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'different world/geometry supplement'):
            self.beacon.install()
        self.assert_no_graph_installed()
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-digest-refusal')

    def test_rich_optional_metadata_is_refused_after_complete_real_staging(self):
        server = self.fallback_server()
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-metadata-refusal')
        row = next(iter(self.beacon.value['optional_input_files'].values()))
        row['source_archive'] = 'synthetic-donor-rich-metadata'
        self.beacon.refresh_physical_profiles()
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Invalid native input/payload pin'):
            self.beacon.install()
        self.assert_no_graph_installed()
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-metadata-refusal')

    def test_cold_warm_crc_difference_is_refused_even_with_refrozen_manifest_and_archive(self):
        self.prepare(1)
        self.beacon.value['input_profiles']['base_world']['native']['full_world_crc'] = '0xdeadbeef'
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Fresh cold/warm native CRC'):
            self.beacon.install()
        self.assert_no_graph_installed()

    def test_missing_native_profile_or_incomplete_path_proof_is_refused(self):
        self.prepare(1)
        profiles = self.beacon.value['input_profiles']
        saved = profiles.pop('base_world_visual')
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Both fresh native profiles'):
            self.beacon.install()
        self.assert_no_graph_installed()
        profiles['base_world_visual'] = saved
        profiles['base_world_visual']['native']['native_pathfinder_successes'] = 31
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Fresh cold/warm native CRC'):
            self.beacon.install()
        self.assert_no_graph_installed()


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Real server preparation with mandatory original Atlas collision geometry.

Tiny immutable source leaves and complete synthetic native proof records exercise
the production guest helper, LocalCharacterServer.prepare_runtime, stage_map_data
and ServerDataCache. These tests do not claim native CRC or route validation.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

import test_server_worktree_reuse as retained_fixture
import test_atlas_beacon_package as beacon_fixture


class BeaconRequiredGeometryRuntimeTests(unittest.TestCase):
    ATLAS_GEOBIN = 'geobin/maps/city_zones/city_01_01/City_01_01'
    REQUIRED_GEOBIN = 'geobin/object_library/required/g0'
    GEOMETRY_CACHE_POLICY = 'once_required_original_atlas_private_geobin_refresh_v1'

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
        # The fixture loads the actual helper under an isolated module name.
        # Production prepare_runtime must execute that same frozen helper.
        module_patch = mock.patch.dict(sys.modules,
            {'atlas_beacon_package': beacon_fixture.package})
        module_patch.start()
        self.addCleanup(module_patch.stop)

    def prepare(self, sequence):
        server = self.staging.make(sequence)
        self.addCleanup(self.close_if_owned, server)
        try:
            receipt = self.staging.prepare(server)
        finally:
            if hasattr(server, 'runtime'):
                self.beacon.runtime = server.runtime
        return server, receipt

    def close_if_owned(self, server):
        cache = getattr(server, 'data_cache', None)
        if cache is not None and cache.record is not None and cache.record['status'] == 'checked_out':
            self.staging.close(server)

    def activate_assets(self):
        assets = self.staging.root / 'assets'
        assets.mkdir(exist_ok=True)
        shutil.copyfile(self.beacon.archive, assets / beacon_fixture.package.ARCHIVE)
        shutil.copyfile(self.beacon.manifest, assets / beacon_fixture.package.MANIFEST)
        selected_assets = self.beacon.geometry_assets()
        source, visual = selected_assets.__enter__()
        self.addCleanup(selected_assets.__exit__, None, None, None)
        for name in (visual.ARCHIVE, visual.MANIFEST):
            shutil.copyfile(source / name, assets / name)

    @property
    def required_geometry(self):
        return self.beacon.required_geometry_inputs

    def install_client_required(self, names=None):
        selected = self.required_geometry if names is None else names
        targets = beacon_fixture.package.actual_targets(
            self.staging.work, selected, beacon_fixture.Context())
        for name, path in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.required_geometry[name])
            path.chmod(0o444)
            os.utime(path, (1767225600, 1767225600))

    def seed_client_leaf(self, name, raw):
        target = self.staging.data / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(0o600)
        return target

    def stale_geometry_caches(self):
        return {
            prefix + suffix: ('old NONE cache ' + prefix + suffix).encode()
            for prefix in (self.ATLAS_GEOBIN, self.REQUIRED_GEOBIN)
            for suffix in ('.bin', '.dep', '.bounds')
        }

    def assert_required_source(self):
        self.assertEqual(len(self.required_geometry), 406)
        targets = beacon_fixture.package.actual_targets(
            self.staging.work, self.required_geometry, beacon_fixture.Context())
        for name, path in targets.items():
            self.assertTrue(path.is_file(), name)
            self.assertFalse(path.is_symlink(), name)
            self.assertEqual(path.read_bytes(), self.required_geometry[name])
            self.assertEqual(path.stat().st_mode & 0o222, 0)
            for directory in path.relative_to(self.staging.work).parents:
                self.assertFalse((self.staging.work / directory).is_symlink())

    def assert_required_staged(self, server):
        targets = beacon_fixture.package.actual_targets(
            server.runtime, self.required_geometry, beacon_fixture.Context())
        source = beacon_fixture.package.actual_targets(
            self.staging.work, self.required_geometry, beacon_fixture.Context())
        for name, path in targets.items():
            self.assertTrue(path.is_symlink(), name)
            self.assertEqual(path.resolve(), source[name].resolve())
            self.assertEqual(path.read_bytes(), self.required_geometry[name])
            self.assertEqual(path.stat().st_mode & 0o222, 0)
        # Imported base inputs retain the production per-file link closure.
        base_name = 'data/object_library/test/g1.geo'
        base = beacon_fixture.package.actual_targets(
            server.runtime, (base_name,), beacon_fixture.Context())[base_name]
        self.assertTrue(base.is_symlink())
        self.assertEqual(base.resolve(),
            (self.staging.imported / base_name.removeprefix('data/')).resolve())

    def assert_no_graph_installed(self, server=None):
        runtime = self.beacon.runtime if server is None else server.runtime
        for name in (beacon_fixture.package.GRAPH, beacon_fixture.package.MARKER):
            # Resolve parent spelling without accepting a case-variant graph leaf.
            sentinel = str(Path(name).parent / '.beacon-absence-check')
            parent = beacon_fixture.package.actual_targets(
                runtime, (sentinel,), beacon_fixture.Context())[sentinel].parent
            self.assertFalse((parent / Path(name).name).exists())

    @staticmethod
    def refuse_fixture_generation(server):
        marker = server.data_cache.marker
        record = json.loads(marker.read_text())
        record['status'] = 'invalid_for_profile_control'
        marker.write_text(json.dumps(record))
        return marker.parent

    def fallback_server(self, names=None):
        cold, _ = self.prepare(1)
        self.staging.close(cold)
        self.install_client_required(names)
        self.refuse_fixture_generation(cold)
        return self.prepare(2)[0]

    def mixed_staging_directories(self):
        for relative, spelling in (
                ('object_library/test', 'Test'), ('object_library', 'Object_Library'),
                ('maps/city_zones/city_01_01', 'City_01_01'),
                ('maps/city_zones', 'City_Zones'), ('maps', 'Maps'), ('tricks', 'Tricks')):
            target = self.staging.data / relative
            target.rename(target.with_name(spelling))

    @staticmethod
    def mixed_graph_parent(server):
        (server.runtime / 'data/server/Maps/City_Zones/City_01_01').mkdir(parents=True)

    def test_production_cold_preparation_installs_all_geometry_before_staging_and_seal(self):
        self.activate_assets()
        server = self.staging.make(1)
        self.addCleanup(self.close_if_owned, server)
        events = []
        real_stage = server.stage_map_data
        real_seal = retained_fixture.cache.ServerDataCache.seal
        real_install = beacon_fixture.package.install

        def stage(source, target, **kwargs):
            self.assert_required_source()
            events.append('stage')
            return real_stage(source, target, **kwargs)

        def seal(cache, data, stats):
            self.assert_required_source()
            self.assert_required_staged(server)
            events.append('seal')
            return real_seal(cache, data, stats)

        def install(*args, **kwargs):
            self.assertEqual(events, ['stage', 'seal'])
            events.append('graph')
            return real_install(*args, **kwargs)

        with mock.patch.object(server, 'stage_map_data', side_effect=stage), \
                mock.patch.object(retained_fixture.cache.ServerDataCache, 'seal', seal), \
                mock.patch.object(beacon_fixture.package, 'install', side_effect=install):
            receipt = self.staging.prepare(server)
        self.beacon.runtime = server.runtime
        self.assertEqual(events, ['stage', 'seal', 'graph'])
        self.assertFalse(receipt['server_data_cache']['reused'])
        self.assert_required_staged(server)
        geometry = server.creation_report['atlas_required_geometry']
        self.assertEqual(geometry['installed_files'], 406)
        self.assertFalse(geometry['full_visual_preload'])
        self.assertFalse(geometry['native_graph_qualified'])
        self.assertEqual(server.data_cache.identity['required_geometry'], geometry['identity'])
        self.assertEqual(geometry['identity'], beacon_fixture.package.validate_required_geometry(
            self.staging.work, beacon_fixture.Context()))
        graph = server.creation_report['atlas_beacon_graph']
        selected, files = beacon_fixture.package.select_profile(
            server.runtime, self.beacon.value, beacon_fixture.Context())
        self.assertEqual(selected, 'required_original_object_geometry')
        self.assertEqual(graph['server_geometry_profile'], selected)
        self.assertEqual(set(files), set(self.beacon.inputs) | set(self.required_geometry))
        self.assertEqual(graph['input_files_checked'], len(files))
        self.assertEqual(graph['input_payload_bytes_hashed'],
                         sum(row['bytes'] for row in files.values()))
        self.assertEqual(graph['status'], 'installed_verified_graph')

    def test_production_warm_preparation_preserves_geometry_graph_and_private_generated_caches(self):
        self.activate_assets()
        cold, _ = self.prepare(1)
        generated = cold.runtime / 'data/server/bin/preserved.bin'
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_bytes(b'accepted-private-generated-cache')
        generated_inode = generated.stat().st_ino
        # Generated caches belong to the successful required-geometry session.
        # The warm geometry marker must preserve client and server cache bytes.
        client_generated = self.seed_client_leaf(self.ATLAS_GEOBIN + '.bin',
                                                 b'warm-client-generated-atlas-cache')
        client_inode = client_generated.stat().st_ino
        server_generated = cold.runtime / 'data' / (self.REQUIRED_GEOBIN + '.bin')
        server_generated.parent.mkdir(parents=True, exist_ok=True)
        server_generated.write_bytes(b'warm-server-generated-required-geometry-cache')
        server_inode = server_generated.stat().st_ino
        data_inode = (cold.runtime / 'data').stat().st_ino
        cold_key = cold.data_cache.key
        graph_before = cold.creation_report['atlas_beacon_graph']
        refresh_before = cold.creation_report['atlas_required_geometry']['cache_refresh']
        self.staging.close(cold)

        warm = self.staging.make(2)
        self.addCleanup(self.close_if_owned, warm)
        with mock.patch.object(warm, 'stage_map_data',
                side_effect=AssertionError('Warm preparation must not mirror inputs')), \
                mock.patch.object(beacon_fixture.package.zipfile, 'ZipFile',
                side_effect=AssertionError('Warm preparation must not decode archives')), \
                mock.patch.object(beacon_fixture.package, 'required_geometry_cache_inventory',
                side_effect=AssertionError('Warm preparation must not scan generated caches')), \
                mock.patch.object(beacon_fixture.package.world, 'remove_cache',
                side_effect=AssertionError('Warm preparation must not remove generated caches')), \
                mock.patch.object(beacon_fixture.package.world, 'verify_target',
                side_effect=AssertionError('Warm geometry must not hash payloads')):
            receipt = self.staging.prepare(warm)
        self.beacon.runtime = warm.runtime
        self.assertTrue(receipt['server_data_cache']['reused'])
        self.assertEqual(warm.data_cache.key, cold_key)
        self.assertEqual((warm.runtime / 'data').stat().st_ino, data_inode)
        restored = warm.runtime / 'data/server/bin/preserved.bin'
        self.assertEqual(restored.read_bytes(), b'accepted-private-generated-cache')
        self.assertEqual(restored.stat().st_ino, generated_inode)
        self.assertEqual(client_generated.read_bytes(), b'warm-client-generated-atlas-cache')
        self.assertEqual(client_generated.stat().st_ino, client_inode)
        restored_geometry = warm.runtime / 'data' / (self.REQUIRED_GEOBIN + '.bin')
        self.assertEqual(restored_geometry.read_bytes(),
                         b'warm-server-generated-required-geometry-cache')
        self.assertEqual(restored_geometry.stat().st_ino, server_inode)
        self.assert_required_source()
        self.assert_required_staged(warm)
        reused = warm.creation_report['atlas_beacon_graph']
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['server_geometry_profile'], graph_before['server_geometry_profile'])
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)
        self.assertFalse(reused['archive_decoded'])
        self.assertEqual(receipt['linked_immutable_files'], 0)
        geometry = warm.creation_report['atlas_required_geometry']
        self.assertEqual(geometry['status'], 'reused_verified_required_geometry')
        self.assertEqual(geometry['selected_payload_bytes_hashed'], 0)
        self.assertFalse(geometry['archive_decoded'])
        self.assertEqual(geometry['cache_refresh'], refresh_before)
        self.assertEqual(geometry['cache_files_removed_this_prepare'], 0)
        self.assertTrue(geometry['cache_refresh_reused'])
        self.assertEqual(warm.data_cache.identity['required_geometry'], geometry['identity'])
        self.assertEqual(geometry['identity']['cache_policy'], self.GEOMETRY_CACHE_POLICY)

    def test_old_none_cache_refresh_precedes_checkout_and_seal_and_preserves_old_tree(self):
        stale = self.stale_geometry_caches()
        for name, raw in stale.items():
            self.seed_client_leaf(name, raw)
        untouched = {
            'geobin/unrelated.bin': b'unrelated-client-cache',
            'bin/client-preserved.bin': b'accepted-client-bin-sentinel',
            'server/db/client-preserved.db': b'private-client-database-sentinel',
        }
        sentinel_inodes = {}
        for name, raw in untouched.items():
            sentinel_inodes[name] = self.seed_client_leaf(name, raw).stat().st_ino
        old, _ = self.prepare(1)
        preserved = old.runtime / 'data/server/bin/preserved.bin'
        preserved.parent.mkdir(parents=True, exist_ok=True)
        preserved.write_bytes(b'old-none-private-cache')
        old_key = old.data_cache.key
        old_inode = (old.runtime / 'data').stat().st_ino
        old_cache_inodes = {
            name: (old.runtime / 'data' / name).stat().st_ino for name in stale
        }
        self.staging.close(old)
        old_marker = old.data_cache.marker.read_bytes()
        old_tree = old.data_cache.path / 'data'
        self.activate_assets()
        events = []
        server = self.staging.make(2)
        self.addCleanup(self.close_if_owned, server)
        real_checkout = retained_fixture.cache.ServerDataCache.checkout
        real_stage = server.stage_map_data
        real_seal = retained_fixture.cache.ServerDataCache.seal

        def assert_client_refresh_complete():
            self.assert_required_source()
            self.assertEqual(beacon_fixture.package.validate_required_geometry(
                self.staging.work, beacon_fixture.Context())['cache_policy'],
                self.GEOMETRY_CACHE_POLICY)
            for name in stale:
                self.assertFalse((self.staging.data / name).exists(), name)
                self.assertEqual((old_tree / name).read_bytes(), stale[name])
                self.assertEqual((old_tree / name).stat().st_ino, old_cache_inodes[name])
            for name, raw in untouched.items():
                source = self.staging.data / name
                self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(source.stat().st_ino, sentinel_inodes[name])

        def checkout(cache, target):
            assert_client_refresh_complete()
            events.append('checkout')
            return real_checkout(cache, target)

        def stage(source, target, **kwargs):
            assert_client_refresh_complete()
            events.append('stage')
            return real_stage(source, target, **kwargs)

        def seal(cache, data, stats):
            assert_client_refresh_complete()
            for name in stale:
                self.assertFalse((server.runtime / 'data' / name).exists(), name)
            events.append('seal')
            return real_seal(cache, data, stats)

        with mock.patch.object(retained_fixture.cache.ServerDataCache, 'checkout', checkout), \
                mock.patch.object(server, 'stage_map_data', side_effect=stage), \
                mock.patch.object(retained_fixture.cache.ServerDataCache, 'seal', seal):
            receipt = self.staging.prepare(server)
        self.beacon.runtime = server.runtime
        self.assertEqual(events, ['checkout', 'stage', 'seal'])
        self.assertFalse(receipt['server_data_cache']['reused'])
        self.assertNotEqual(server.data_cache.key, old_key)
        self.assertNotEqual((server.runtime / 'data').stat().st_ino, old_inode)
        self.assertEqual(old.data_cache.marker.read_bytes(), old_marker)
        self.assertEqual(old_tree.stat().st_ino, old_inode)
        self.assertEqual((old_tree / 'server/bin/preserved.bin').read_bytes(),
                         b'old-none-private-cache')
        self.assertFalse((server.runtime / 'data/server/bin/preserved.bin').exists())
        for name, raw in untouched.items():
            self.assertEqual((server.runtime / 'data' / name).read_bytes(), raw)
            self.assertEqual((old_tree / name).read_bytes(), raw)
        self.assert_required_staged(server)
        geometry = server.creation_report['atlas_required_geometry']
        self.assertEqual(server.data_cache.identity['required_geometry'], geometry['identity'])
        self.assertNotEqual(old.data_cache.identity.get('required_geometry'),
                           server.data_cache.identity['required_geometry'])
        refresh = geometry['cache_refresh']
        removed = [{
            'path': 'data/' + name,
            'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
        } for name, raw in sorted(stale.items())]
        self.assertEqual(refresh['policy'], self.GEOMETRY_CACHE_POLICY)
        self.assertTrue(refresh['performed'])
        self.assertEqual(refresh['removed_files'], len(stale))
        self.assertEqual(refresh['removed_bytes'], sum(map(len, stale.values())))
        self.assertFalse(refresh['accepted_cache_archive_modified'])
        self.assertEqual(refresh['removed_inventory_sha256'],
            hashlib.sha256(beacon_fixture.package.canonical(removed)).hexdigest())
        self.assertEqual(geometry['cache_files_removed_this_prepare'], len(stale))
        self.assertFalse(geometry['cache_refresh_reused'])
        marker = json.loads((self.staging.work / beacon_fixture.package.GEOMETRY_MARKER).read_bytes())
        self.assertEqual(marker['removed_cache_files'], removed)
        self.assertEqual(marker['cache_refresh'], refresh)
        self.assertEqual(server.creation_report['atlas_beacon_graph']['status'],
                         'installed_verified_graph')

    def test_none_runtime_inventory_is_refused_before_graph_or_private_cache_changes(self):
        server, _ = self.prepare(1)
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-none-refusal')
        with self.assertRaisesRegex(ValueError, 'Every required original Atlas geometry'):
            self.beacon.install()
        self.assert_no_graph_installed(server)
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-none-refusal')

    def test_partial_runtime_inventory_is_refused_without_graph_or_private_cache_changes(self):
        server = self.fallback_server((next(iter(self.required_geometry)),))
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-partial-refusal')
        with self.assertRaisesRegex(ValueError, 'Every required original Atlas geometry'):
            self.beacon.install()
        self.assert_no_graph_installed(server)
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-partial-refusal')

    def test_complete_runtime_with_wrong_readonly_geometry_cannot_masquerade_as_required_profile(self):
        server = self.fallback_server()
        name = next(iter(self.required_geometry))
        path = beacon_fixture.package.actual_targets(
            server.runtime, (name,), beacon_fixture.Context())[name]
        source = path.resolve()
        source.chmod(0o600)
        source.write_bytes(b'wrong-required-geometry')
        source.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'Actual Atlas collision/group input differs'):
            self.beacon.install()
        self.assert_no_graph_installed(server)

    def test_wrong_existing_client_geometry_refuses_before_server_staging(self):
        self.install_client_required()
        name = next(iter(self.required_geometry))
        path = beacon_fixture.package.actual_targets(
            self.staging.work, (name,), beacon_fixture.Context())[name]
        before = path.stat()
        path.chmod(0o600)
        path.write_bytes(b'X' * before.st_size)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        path.chmod(0o444)
        wrong_bytes = path.read_bytes()
        self.activate_assets()
        server = self.staging.make(1)
        self.addCleanup(self.close_if_owned, server)
        with mock.patch.object(server, 'stage_map_data',
                side_effect=AssertionError('Unqualified source must fail before staging')):
            with self.assertRaisesRegex((ValueError, retained_fixture.server.base.DiagnosticError),
                                        'conflicts with the reviewed payload'):
                self.staging.prepare(server)
        self.beacon.runtime = server.runtime
        self.assert_no_graph_installed(server)
        self.assertFalse(getattr(server, 'data_cache', None))
        self.assertEqual(path.read_bytes(), wrong_bytes)

    def test_linked_required_client_geometry_directory_refuses_before_staging(self):
        self.install_client_required()
        name = next(iter(self.required_geometry))
        source = beacon_fixture.package.actual_targets(
            self.staging.work, (name,), beacon_fixture.Context())[name]
        original = source.parent
        donor = self.staging.imported / 'linked-required-geometry-directory'
        original.rename(donor)
        original.symlink_to(donor, target_is_directory=True)
        before = (donor / source.name).read_bytes()
        self.activate_assets()
        server = self.staging.make(1)
        self.addCleanup(self.close_if_owned, server)
        with mock.patch.object(server, 'stage_map_data',
                side_effect=AssertionError('Linked source directory must fail before staging')):
            with self.assertRaisesRegex((ValueError, retained_fixture.server.base.DiagnosticError),
                                        '[Ll]inked|[Dd]irectory'):
                self.staging.prepare(server)
        self.assertTrue(original.is_symlink())
        self.assertEqual((donor / source.name).read_bytes(), before)
        self.assert_no_graph_installed(server)
        self.assertFalse(getattr(server, 'data_cache', None))

    def test_unlisted_collision_geometry_refuses_a_complete_required_runtime(self):
        server = self.fallback_server()
        extra = server.runtime / 'data/object_library/foreign.geo'
        extra.write_bytes(b'unqualified collision input')
        extra.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.beacon.install()
        self.assert_no_graph_installed(server)

    def test_real_mixed_case_source_cold_and_warm_cache_keep_complete_required_geometry(self):
        self.mixed_staging_directories()
        self.activate_assets()
        cold, _ = self.prepare(1)
        self.assert_required_source()
        self.assert_required_staged(cold)
        first = cold.creation_report['atlas_beacon_graph']
        marker_path = beacon_fixture.package.actual_targets(cold.runtime,
            (beacon_fixture.package.MARKER,), beacon_fixture.Context())[beacon_fixture.package.MARKER]
        marker = json.loads(marker_path.read_bytes())
        self.assertEqual(marker['input_fingerprints']['data/object_library/test/g1.geo']['path'],
                         'data/Object_Library/Test/g1.geo')
        self.staging.close(cold)

        warm = self.staging.make(2)
        self.addCleanup(self.close_if_owned, warm)
        with mock.patch.object(warm, 'stage_map_data',
                side_effect=AssertionError('Warm mixed-case cache must not mirror inputs')), \
                mock.patch.object(beacon_fixture.package.zipfile, 'ZipFile',
                side_effect=AssertionError('Warm mixed-case graph must not decode archive')):
            receipt = self.staging.prepare(warm)
        self.assertTrue(receipt['server_data_cache']['reused'])
        reused = warm.creation_report['atlas_beacon_graph']
        self.assertEqual(reused['server_geometry_profile'], first['server_geometry_profile'])
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)
        self.assertFalse((warm.runtime / 'data/object_library').exists())
        self.assert_required_staged(warm)

    def test_real_staged_case_variant_graph_refuses_without_private_cache_changes(self):
        self.mixed_staging_directories()
        self.install_client_required()
        server, _ = self.prepare(1)
        self.mixed_graph_parent(server)
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-case-refusal')
        graph = server.runtime / 'data/server/Maps/City_Zones/City_01_01/CITY_01_01.TXT.v8.bcn'
        graph.write_bytes(b'existing graph must survive case refusal')
        with self.assertRaisesRegex(beacon_fixture.package.world.client.base.DiagnosticError,
                                    'Case-conflicting world leaf'):
            self.beacon.install()
        self.assert_no_graph_installed(server)
        self.assertEqual(graph.read_bytes(), b'existing graph must survive case refusal')
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-case-refusal')
        self.assertFalse((server.runtime / 'data/server/maps').exists())

    def test_swapped_raw_source_and_physical_digests_refuse_before_private_cache_changes(self):
        server = self.fallback_server()
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-digest-refusal')
        identity = self.beacon.value['input_identity']
        raw = identity['visual_object_geometry_sha256']
        physical = identity['required_geometry_sha256']
        self.assertNotEqual(raw, physical)
        identity['visual_object_geometry_sha256'] = physical
        identity['required_geometry_sha256'] = raw
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'different world/geometry supplement'):
            self.beacon.install()
        self.assert_no_graph_installed(server)
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-digest-refusal')

    def test_rich_required_metadata_is_refused_after_complete_real_staging(self):
        server = self.fallback_server()
        private = server.runtime / 'data/server/bin/preserved.bin'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b'private-cache-must-survive-metadata-refusal')
        row = next(iter(self.beacon.value['required_geometry_files'].values()))
        row['source_archive'] = 'synthetic-donor-rich-metadata'
        self.beacon.refresh_physical_profiles()
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Invalid native input/payload pin'):
            self.beacon.install()
        self.assert_no_graph_installed(server)
        self.assertEqual(private.read_bytes(), b'private-cache-must-survive-metadata-refusal')

    def test_cold_warm_crc_difference_is_refused_even_with_refrozen_manifest_and_archive(self):
        server = self.fallback_server()
        name = beacon_fixture.package.PROFILES[0]
        self.beacon.value['input_profiles'][name]['native']['full_world_crc'] = '0xdeadbeef'
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Fresh cold/warm native CRC'):
            self.beacon.install()
        self.assert_no_graph_installed(server)

    def test_missing_native_layout_or_incomplete_path_proof_is_refused(self):
        server = self.fallback_server()
        profiles = self.beacon.value['input_profiles']
        name = beacon_fixture.package.PROFILES[1]
        saved = profiles.pop(name)
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Both fresh required-geometry native layouts'):
            self.beacon.install()
        self.assert_no_graph_installed(server)
        profiles[name] = saved
        profiles[name]['native']['native_pathfinder_successes'] = 31
        self.beacon.freeze()
        with self.assertRaisesRegex(ValueError, 'Fresh cold/warm native CRC'):
            self.beacon.install()
        self.assert_no_graph_installed(server)


if __name__ == '__main__':
    unittest.main(verbosity=2)

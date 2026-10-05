"""Bounded install/reuse checks; synthetic fixtures do not claim native graphs."""
import hashlib
import contextlib
import stat
import copy
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'android/guest'))
spec = importlib.util.spec_from_file_location('atlas_beacon_test_module', ROOT/'android/guest/atlas_beacon_package.py')
package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)


class Context:
    def check(self): pass


class AtlasBeaconPackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='coh-beacon-package-test-')
        self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        self.runtime = self.root/'runtime'; self.runtime.mkdir()
        self.inputs = {'data/'+package.MAP: b'authored test map'}
        self.inputs.update({'data/object_library/test/g%d.geo'%i: b'fixture geometry %d'%i for i in range(101)})
        self.required_geometry_inputs = {'data/object_library/required/g%d.geo'%i:
                                b'fixture required geometry %d'%i for i in range(package.REQUIRED_GEOS)}
        for name, raw in self.inputs.items():
            path = self.runtime/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); path.chmod(0o400)
        (self.runtime/'data/tricks').mkdir()
        exe = self.runtime/'MapServer.exe'; exe.write_bytes(b'fixture stock native identity')
        self.payloads = {package.GRAPH: b'unit test graph fixture body only', package.DATE: struct.pack('<iII',9,1767225600,0x10203040)}
        p = lambda raw: {'bytes': len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        self.value = {'format':3,'role':package.ROLE,'map':package.MAP,
            'source_commit':package.SOURCE_COMMIT,'data_commit':package.DATA_COMMIT,
            'stock_mapserver_sha256':p(exe.read_bytes())['sha256'],'runtime_graph_readback':True,
            'physical_npc_pathing_validated':False,'files':{n:p(v) for n,v in self.payloads.items()},
            'input_files':{n:p(v) for n,v in self.inputs.items()},
            'required_geometry_files':{n:p(v) for n,v in self.required_geometry_inputs.items()},
            'input_identity':{'asset_archive':package.BASE_ARCHIVE,
                'world_manifest':{'sha256':package.WORLD_MANIFEST_SHA256},
                'visual_geometry_sha256':package.VISUAL_GEOMETRY_SHA256,
                'visual_source_manifest':package.VISUAL_SOURCE_MANIFEST},
            'native':{'native_full_graph_readback_verified':True,'fresh_ordinary_world_crc_verified':True,
                'native_pathfinder_successes':32,'date_version':9,'connected_beacons':1900,
                'combat_beacons':2000,'ground_connections':5000,'grid_blocks':100,'full_world_crc':'0x10203040'}}
        self.value['input_files_sha256'] = hashlib.sha256(package.canonical(self.value['input_files'])).hexdigest()
        # Raw donor provenance and normalized physical pins are different
        # contracts. Only the physical digest below is synthetic fixture data.
        self.value['input_identity']['visual_object_geometry_sha256'] = package.VISUAL_OBJECT_GEOMETRY_SHA256
        self.value['input_identity']['required_geometry_sha256'] = hashlib.sha256(
            package.canonical(self.value['required_geometry_files'])).hexdigest()
        self.value['input_profiles'] = {
            name: {'native': copy.deepcopy(self.value['native']),
                   'input_files_sha256': hashlib.sha256(package.canonical({
                       **self.value['input_files'], **self.value['required_geometry_files']})).hexdigest()}
            for name in package.PROFILES}
        self.manifest = self.root/package.MANIFEST; self.archive = self.root/package.ARCHIVE
        self.freeze()
        self.add_required_inputs()

    def freeze(self):
        raw=package.canonical(self.value); self.manifest.write_bytes(raw)
        with zipfile.ZipFile(self.archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr(package.MANIFEST,raw)
            for name,data in self.payloads.items():z.writestr(name,data)
        for name,value in [('MANIFEST_SHA256',hashlib.sha256(raw).hexdigest()),
                           ('ARCHIVE_SHA256',package.pin(self.archive)['sha256']),
                           ('ARCHIVE_BYTES',self.archive.stat().st_size),
                           ('REQUIRED_GEOMETRY_SHA256',hashlib.sha256(
                               package.canonical(self.value['required_geometry_files'])).hexdigest()),
                           ('STOCK_MAPSERVER_SHA256',self.value['stock_mapserver_sha256'])]:
            patch=mock.patch.object(package,name,value);patch.start();self.addCleanup(patch.stop)

    def refresh_physical_profiles(self):
        # A refrozen fixture may have internally consistent digests while its
        # physical pin shape is invalid; read_manifest must still refuse it.
        self.value['input_files_sha256'] = hashlib.sha256(
            package.canonical(self.value['input_files'])).hexdigest()
        self.value['input_identity']['required_geometry_sha256'] = hashlib.sha256(
            package.canonical(self.value['required_geometry_files'])).hexdigest()
        for name in package.PROFILES:
            self.value['input_profiles'][name]['input_files_sha256'] = hashlib.sha256(
                package.canonical({**self.value['input_files'],
                                   **self.value['required_geometry_files']})).hexdigest()

    def install(self):
        return package.install(self.archive,self.manifest,self.runtime,context=Context(),imported_inputs_readonly=True)

    def add_required_inputs(self, names=None):
        selected = self.required_geometry_inputs if names is None else names
        for name, path in package.actual_targets(self.runtime, selected, Context()).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(self.required_geometry_inputs[name]); path.chmod(0o400)


    def remove_required_inputs(self):
        for target in package.actual_targets(self.runtime, self.required_geometry_inputs, Context()).values():
            if target.exists(): target.unlink()

    @contextlib.contextmanager
    def geometry_assets(self, extra_files=None):
        # Only the existing visual metadata validator is stubbed. The selected
        # ZIP member checks, extraction, ctime proofs and no-replace publishing
        # execute production code; this is not a native graph fixture.
        import client_visual_assets as visual
        assets = self.root/'visual-assets'; assets.mkdir(exist_ok=True)
        payloads = {**self.required_geometry_inputs, **(extra_files or {})}
        document = {'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                              for name, raw in payloads.items()}}
        (assets/visual.MANIFEST).write_bytes(package.canonical(document))
        with zipfile.ZipFile(assets/visual.ARCHIVE, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in payloads.items():
                entry = zipfile.ZipInfo(name); entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (stat.S_IFREG | 0o444) << 16
                archive.writestr(entry, raw)
        (self.runtime/'client-work.json').write_bytes(b'fixture protected client identity')
        with mock.patch.object(visual, 'package', return_value=document), \
                mock.patch.object(visual, 'FILE_COUNT', len(document['files'])), \
                mock.patch.object(visual, 'ARCHIVE_BYTES', (assets/visual.ARCHIVE).stat().st_size):
            yield assets, visual

    def test_none_and_partial_required_geometry_are_refused_before_graph_write(self):
        self.remove_required_inputs()
        for names in ({}, {next(iter(self.required_geometry_inputs))}):
            with self.subTest(present=len(names)):
                self.add_required_inputs(names)
                with self.assertRaisesRegex(ValueError, 'Every required original Atlas geometry'):
                    self.install()
                self.assert_no_graph()
                self.remove_required_inputs()

    def test_both_fresh_layouts_require_identical_complete_union_proof(self):
        for key, value in (('native_pathfinder_successes', 0), ('full_world_crc', '0x10203041')):
            with self.subTest(key=key):
                self.value['input_profiles'][package.PROFILES[0]]['native'][key] = value
                self.freeze()
                with self.assertRaisesRegex(ValueError, 'Fresh cold/warm native'):
                    self.install()
                self.assert_no_graph()
                self.value['input_profiles'][package.PROFILES[0]]['native'] = copy.deepcopy(self.value['native'])

    def test_selected_geometry_preparation_is_persistent_and_does_not_preload_ui(self):
        self.remove_required_inputs()
        with self.geometry_assets() as (assets, visual):
            first = package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(first['installed_files'], package.REQUIRED_GEOS)
            self.assertEqual(first['selected_payload_bytes_hashed'], sum(map(len, self.required_geometry_inputs.values())))
            self.assertFalse(first['full_visual_preload'])
            self.assertFalse(first['native_graph_qualified'])
            self.assertEqual(package.validate_required_geometry(self.runtime, Context()), first['identity'])
            for path in package.actual_targets(self.runtime, self.required_geometry_inputs, Context()).values():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o444)
            with mock.patch.object(package.zipfile, 'ZipFile', side_effect=AssertionError('Warm geometry must not decode ZIP')), \
                    mock.patch.object(visual, 'package', side_effect=AssertionError('Warm geometry must not parse full UI metadata')), \
                    mock.patch.object(package.world, 'verify_target', side_effect=AssertionError('Warm geometry must not hash payloads')), \
                    mock.patch.object(package, 'required_geometry_cache_inventory', side_effect=AssertionError('Warm geometry must not rescan caches')), \
                    mock.patch.object(package.world, 'remove_cache', side_effect=AssertionError('Warm geometry must preserve regenerated caches')):
                warm = package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(warm['identity'], first['identity'])
            self.assertEqual(warm['selected_payload_bytes_hashed'], 0)
            self.assertFalse(warm['archive_decoded'])
            self.assert_no_graph()

    def test_changed_required_client_leaf_cannot_be_replaced_by_source_zip(self):
        self.remove_required_inputs()
        with self.geometry_assets() as (assets, visual):
            package.ensure_required_geometry(self.runtime, assets, Context())
            target = next(iter(package.actual_targets(self.runtime, self.required_geometry_inputs, Context()).values()))
            old = target.stat()
            target.chmod(0o600); target.write_bytes(b'X' * old.st_size)
            os.utime(target, ns=(old.st_atime_ns, old.st_mtime_ns)); target.chmod(0o444)
            before = target.read_bytes()
            with self.assertRaisesRegex(package.world.client.base.DiagnosticError, 'conflicts with the reviewed payload'):
                package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(target.read_bytes(), before)
            self.assert_no_graph()

    def test_existing_verified_required_client_leaves_need_no_zip_decode(self):
        self.remove_required_inputs()
        with self.geometry_assets() as (assets, visual):
            for name, raw in self.required_geometry_inputs.items():
                path = package.actual_targets(self.runtime, (name,), Context())[name]
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); path.chmod(0o444)
                os.utime(path, (visual.client.CACHE_EPOCH, visual.client.CACHE_EPOCH))
            with mock.patch.object(package.zipfile, 'ZipFile', side_effect=AssertionError('Existing geometry must not decode ZIP')):
                first = package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(first['installed_files'], 0)
            self.assertEqual(first['selected_payload_bytes_hashed'], sum(map(len, self.required_geometry_inputs.values())))
            self.assertFalse(first['archive_decoded'])




    def cache_leaf(self, name, raw=b'private generated cache'):
        path = self.runtime / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def test_first_required_geometry_refresh_is_finite_and_generated_warm_caches_survive(self):
        self.remove_required_inputs()
        selected = [
            'data/GeoBin/Maps/City_Zones/City_01_01/City_01_01.bin',
            'data/GeoBin/Maps/City_Zones/City_01_01/City_01_01.dep',
            'data/GeoBin/Object_Library/Required/g0.bin',
            'data/GeoBin/Object_Library/Required/g0.dep',
            'data/GeoBin/Object_Library/Required/g0.bounds']
        kept = [
            'data/bin/imported-original.bin',
            'data/GeoBin/Maps/City_Zones/City_01_02/unrelated.bin',
            'data/GeoBin/Object_Library/unrelated/other.bounds',
            'data/GeoBin/Object_Library/Required/g0.other',
            'data/GeoBin/Maps/City_Zones/City_01_01/keep.texture']
        removed_pins = []
        for index, name in enumerate(selected):
            path = self.cache_leaf(name, ('stale missing-model cache %d' % index).encode())
            removed_pins.append({'path': name, **package.pin(path)})
        preserved = {name: (self.cache_leaf(name, ('preserve %s' % name).encode()).read_bytes(),
                            (self.runtime / name).stat().st_ino) for name in kept}
        with self.geometry_assets() as (assets, visual):
            first = package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(first['cache_files_removed_this_prepare'], len(selected))
            self.assertFalse(first['cache_refresh_reused'])
            saved = json.loads((self.runtime / package.GEOMETRY_MARKER).read_bytes())
            self.assertEqual(saved['removed_cache_files'], sorted(removed_pins, key=lambda row: row['path']))
            self.assertEqual(saved['cache_refresh']['policy'], package.GEOMETRY_CACHE_POLICY)
            self.assertFalse(saved['cache_refresh']['accepted_cache_archive_modified'])
            self.assertEqual(first['identity']['cache_policy'], package.GEOMETRY_CACHE_POLICY)
            for name in selected:
                self.assertFalse((self.runtime / name).exists())
            for name, (raw, inode) in preserved.items():
                self.assertEqual((self.runtime / name).read_bytes(), raw)
                self.assertEqual((self.runtime / name).stat().st_ino, inode)
            regenerated = self.cache_leaf(selected[0], b'qualified regenerated Atlas cache')
            regenerated_inode = regenerated.stat().st_ino
            marker = (self.runtime / package.GEOMETRY_MARKER).read_bytes()
            with mock.patch.object(package, 'required_geometry_cache_inventory', side_effect=AssertionError('Warm cache scan')), \
                    mock.patch.object(package.world, 'hash_regular', side_effect=AssertionError('Warm payload hash')), \
                    mock.patch.object(package.world, 'remove_cache', side_effect=AssertionError('Warm cache removal')), \
                    mock.patch.object(package.zipfile, 'ZipFile', side_effect=AssertionError('Warm ZIP decode')), \
                    mock.patch.object(visual, 'package', side_effect=AssertionError('Warm metadata parse')):
                warm = package.ensure_required_geometry(self.runtime, assets, Context())
                self.assertEqual(package.validate_required_geometry(self.runtime, Context()), first['identity'])
            self.assertTrue(warm['cache_refresh_reused'])
            self.assertEqual(warm['cache_files_removed_this_prepare'], 0)
            self.assertEqual(warm['selected_payload_bytes_hashed'], 0)
            self.assertEqual(warm['cache_refresh'], first['cache_refresh'])
            self.assertEqual(regenerated.read_bytes(), b'qualified regenerated Atlas cache')
            self.assertEqual(regenerated.stat().st_ino, regenerated_inode)
            self.assertEqual((self.runtime / package.GEOMETRY_MARKER).read_bytes(), marker)

    def test_prior_geometry_receipt_without_refresh_cannot_reuse_stale_flattened_map_cache(self):
        self.remove_required_inputs()
        with self.geometry_assets() as (assets, visual):
            package.ensure_required_geometry(self.runtime, assets, Context())
            marker = self.runtime / package.GEOMETRY_MARKER
            saved = json.loads(marker.read_bytes())
            saved.pop('cache_refresh'); saved.pop('removed_cache_files')
            saved['identity'].pop('cache_policy')
            marker.chmod(0o600); marker.write_bytes(package.canonical(saved)); marker.chmod(0o444)
            os.utime(marker, (visual.client.CACHE_EPOCH, visual.client.CACHE_EPOCH))
            stale = self.cache_leaf('data/geobin/maps/city_zones/city_01_01/City_01_01.bin',
                                    b'legacy flattened missing-geometry map')
            unrelated = self.cache_leaf('data/geobin/object_library/unrelated/other.bin', b'unrelated cache')
            with self.assertRaisesRegex(ValueError, 'cache refresh receipt'):
                package.validate_required_geometry(self.runtime, Context())
            with mock.patch.object(package.zipfile, 'ZipFile', side_effect=AssertionError('Existing geometry should not decode')):
                repaired = package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(repaired['installed_files'], 0)
            self.assertFalse(repaired['cache_refresh_reused'])
            self.assertEqual(repaired['cache_files_removed_this_prepare'], 1)
            self.assertFalse(stale.exists())
            self.assertEqual(unrelated.read_bytes(), b'unrelated cache')
            self.assertEqual(package.validate_required_geometry(self.runtime, Context()), repaired['identity'])

    def test_linked_private_cache_is_refused_before_geometry_or_refresh_receipt_writes(self):
        self.remove_required_inputs()
        linked = self.runtime / 'data/geobin/maps/city_zones/city_01_01/City_01_01.bin'
        linked.parent.mkdir(parents=True)
        outside = self.root / 'outside.bin'; outside.write_bytes(b'outside must survive')
        linked.symlink_to(outside)
        with self.geometry_assets() as (assets, visual):
            with self.assertRaisesRegex(ValueError, 'Linked required geometry private cache'):
                package.ensure_required_geometry(self.runtime, assets, Context())
        self.assertEqual(outside.read_bytes(), b'outside must survive')
        self.assertTrue(linked.is_symlink())
        self.assertFalse((self.runtime / package.GEOMETRY_MARKER).exists())
        self.assertTrue(all(not path.exists() for path in
                            package.actual_targets(self.runtime, self.required_geometry_inputs, Context()).values()))

    def test_refresh_history_cannot_claim_unrelated_imported_cache_deletion(self):
        self.remove_required_inputs()
        with self.geometry_assets() as (assets, visual):
            package.ensure_required_geometry(self.runtime, assets, Context())
            marker = self.runtime / package.GEOMETRY_MARKER
            saved = json.loads(marker.read_bytes())
            unrelated = self.cache_leaf('data/bin/imported-original.bin', b'imported immutable cache')
            removed = [{'path': 'data/bin/imported-original.bin', **package.pin(unrelated)}]
            saved['removed_cache_files'] = removed
            saved['cache_refresh'].update(removed_files=1, removed_bytes=removed[0]['bytes'],
                removed_inventory_sha256=hashlib.sha256(package.canonical(removed)).hexdigest())
            marker.chmod(0o600); marker.write_bytes(package.canonical(saved)); marker.chmod(0o444)
            os.utime(marker, (visual.client.CACHE_EPOCH, visual.client.CACHE_EPOCH))
            with self.assertRaisesRegex(ValueError, 'removed-cache pin'):
                package.validate_required_geometry(self.runtime, Context())
            repaired = package.ensure_required_geometry(self.runtime, assets, Context())
            self.assertEqual(repaired['cache_files_removed_this_prepare'], 0)
            self.assertFalse(repaired['cache_refresh_reused'])
            self.assertEqual(unrelated.read_bytes(), b'imported immutable cache')

    def test_actual_927_geo_partition_prepares_only_406_object_geometry(self):
        self.remove_required_inputs()
        # The real frozen inventory contains 521 player GEOs and 406 object
        # GEOs. UI texture additions leave that exact partition unchanged.
        extra = {'data/player_library/test/player%d.geo' % index:
                 ('fixture player geometry %d' % index).encode() for index in range(521)}
        extra['data/texture_library/ui/fixture.texture'] = b'fixture unrelated UI leaf'
        with self.geometry_assets(extra) as (assets, visual):
            result = package.ensure_required_geometry(self.runtime, assets, Context())
        self.assertEqual(result['installed_files'], 406)
        self.assertEqual(result['selected_payload_bytes_hashed'],
                         sum(map(len, self.required_geometry_inputs.values())))
        self.assertFalse((self.runtime/'data/player_library').exists())
        self.assertFalse((self.runtime/'data/texture_library').exists())
        self.assert_no_graph()

    def test_extra_object_geometry_cannot_be_silently_treated_as_common_overlap(self):
        self.remove_required_inputs()
        common = 'data/object_library/test/g1.geo'
        before = (self.runtime/common).read_bytes()
        with self.geometry_assets({common: self.inputs[common]}) as (assets, visual):
            with self.assertRaisesRegex(ValueError, 'Exact required original object geometry'):
                package.ensure_required_geometry(self.runtime, assets, Context())
        self.assertEqual((self.runtime/common).read_bytes(), before)
        self.assertFalse((self.runtime/package.GEOMETRY_MARKER).exists())
        self.assertFalse(any(path.exists() for path in package.actual_targets(
            self.runtime, self.required_geometry_inputs, Context()).values()))
        self.assert_no_graph()


    def mixed_case_directories(self):
        for relative, spelling in (
                ('data/object_library/test', 'Test'),
                ('data/object_library', 'Object_Library'),
                ('data/maps/city_zones/city_01_01', 'City_01_01'),
                ('data/maps/city_zones', 'City_Zones'),
                ('data/maps', 'Maps'), ('data/tricks', 'Tricks'), ('data', 'Data')):
            target = self.runtime/relative
            target.rename(target.with_name(spelling))
        (self.runtime/'Data/Server/Maps/City_Zones/City_01_01').mkdir(parents=True)

    def assert_no_graph(self):
        self.assertFalse((self.runtime/'Data/Server/Maps/City_Zones/City_01_01/city_01_01.txt.v8.bcn').exists())
        self.assertFalse((self.runtime/'Data/Server/atlas-beacon-installed.json').exists())
        self.assertFalse((self.runtime/package.GRAPH).exists())
        self.assertFalse((self.runtime/package.MARKER).exists())


    def test_first_install_and_warm_reuse_do_not_decode_or_hash_input_payloads_again(self):
        first=self.install();self.assertEqual(first['installed_files'],2)
        with mock.patch.object(package.zipfile,'ZipFile',side_effect=AssertionError('Warm graph must not decode archive')):
            reused=self.install()
        self.assertEqual(reused['status'],'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'],0)
        self.assertTrue(reused['fingerprint_walk'])

    def test_wrong_actual_geometry_blocks_graph_installation(self):
        path=self.runtime/'data/object_library/test/g1.geo';path.chmod(0o600);path.write_bytes(b'changed');path.chmod(0o400)
        with self.assertRaisesRegex(ValueError,'Actual Atlas collision/group input differs'):self.install()
        self.assertFalse((self.runtime/package.GRAPH).exists())

    def test_changed_readonly_input_invalidates_warm_receipt(self):
        self.install();path=self.runtime/'data/object_library/test/g1.geo'
        path.chmod(0o600);path.write_bytes(b'changed');path.chmod(0o400)
        with self.assertRaisesRegex(ValueError,'Actual Atlas collision/group input differs'):self.install()

    def test_changed_same_size_payload_with_restored_mtime_and_mode_invalidates_warm_proof(self):
        self.install();path=self.runtime/'data/object_library/test/g1.geo';before=path.stat()
        path.chmod(0o600);path.write_bytes(b'X' * before.st_size)
        os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns));path.chmod(0o400)
        after=path.stat();self.assertEqual(before.st_ino,after.st_ino)
        self.assertEqual(before.st_size,after.st_size);self.assertEqual(before.st_mtime_ns,after.st_mtime_ns)
        self.assertNotEqual(before.st_ctime_ns,after.st_ctime_ns)
        with self.assertRaisesRegex(ValueError,'Actual Atlas collision/group input differs'):self.install()

    def test_existing_different_graph_is_preserved(self):
        target=self.runtime/package.GRAPH;target.parent.mkdir(parents=True);target.write_bytes(b'old authentic input');before=target.read_bytes()
        with self.assertRaisesRegex(ValueError,'existing different beacon graph'):self.install()
        self.assertEqual(target.read_bytes(),before)

    def test_symlink_target_and_writable_inputs_are_refused(self):
        target=self.runtime/package.GRAPH;target.parent.mkdir(parents=True);target.symlink_to(self.root/'external')
        with self.assertRaisesRegex(ValueError,'Linked beacon target'):self.install()
        target.unlink();(self.runtime/'data/object_library/test/g1.geo').chmod(0o600)
        with self.assertRaisesRegex(ValueError,'immutable leaf permissions'):self.install()

    def test_bad_native_receipt_and_unrelated_graph_payload_are_refused(self):
        self.value['native']['native_pathfinder_successes']=0;self.freeze()
        with self.assertRaisesRegex(ValueError,'proofs are incomplete'):self.install()

    def test_mixed_case_directories_install_cold_and_reuse_bound_actual_paths(self):
        self.mixed_case_directories()
        first = self.install()
        self.assertEqual(first['server_geometry_profile'], package.SERVER_GEOMETRY_PROFILE)
        marker = self.runtime/'Data/Server/atlas-beacon-installed.json'
        record = json.loads(marker.read_bytes())
        self.assertTrue(record['input_fingerprints']['data/object_library/test/g1.geo']['path'].startswith(
            'Data/Object_Library/Test/'))
        self.assertEqual(record['graph_fingerprints'][package.GRAPH]['path'],
            'Data/Server/Maps/City_Zones/City_01_01/city_01_01.txt.v8.bcn')
        with mock.patch.object(package.zipfile, 'ZipFile', side_effect=AssertionError('Warm graph must not decode archive')):
            reused = self.install()
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)
        self.assertFalse((self.runtime/'data').exists())

    def test_mixed_case_directories_install_complete_required_profile_and_reuse(self):
        self.mixed_case_directories()
        self.add_required_inputs()
        first = self.install()
        self.assertEqual(first['server_geometry_profile'], package.SERVER_GEOMETRY_PROFILE)
        self.assertEqual(first['input_files_checked'], len(self.inputs) + len(self.required_geometry_inputs))
        self.assertFalse((self.runtime/'Data/object_library').exists())
        with mock.patch.object(package.zipfile, 'ZipFile', side_effect=AssertionError('Warm graph must not decode archive')):
            reused = self.install()
        self.assertEqual(reused['status'], 'reused_verified_graph')
        self.assertEqual(reused['input_payload_bytes_hashed'], 0)

    def test_original_uppercase_map_and_geometry_leaves_are_preserved_exactly(self):
        for old, new in (
                ('data/'+package.MAP, 'data/maps/city_zones/city_01_01/CITY_01_01.TXT'),
                ('data/object_library/test/g1.geo', 'data/object_library/test/G1.GEO')):
            (self.runtime/old).rename(self.runtime/new)
            self.value['input_files'][new] = self.value['input_files'].pop(old)
        self.refresh_physical_profiles(); self.freeze()
        self.mixed_case_directories()
        installed = self.install()
        self.assertEqual(installed['server_geometry_profile'], package.SERVER_GEOMETRY_PROFILE)
        self.assertTrue((self.runtime/'Data/Maps/City_Zones/City_01_01/CITY_01_01.TXT').is_file())
        self.assertTrue((self.runtime/'Data/Object_Library/Test/G1.GEO').is_file())
        self.assertFalse((self.runtime/'Data/Object_Library/Test/g1.geo').exists())

    def test_case_colliding_directories_leaves_and_different_leaf_case_are_refused(self):
        self.mixed_case_directories()
        alias = self.runtime/'Data/object_library'
        alias.mkdir()
        with self.assertRaisesRegex(package.world.client.base.DiagnosticError, 'case-conflicting world destination'):
            self.install()
        self.assert_no_graph(); alias.rmdir()
        original = self.runtime/'Data/Object_Library/Test/g1.geo'
        duplicate = original.with_name('G1.GEO')
        duplicate.write_bytes(original.read_bytes()); duplicate.chmod(0o400)
        with self.assertRaisesRegex(package.world.client.base.DiagnosticError, 'case-conflicting world destination'):
            self.install()
        self.assert_no_graph(); duplicate.unlink()
        original.rename(duplicate)
        with self.assertRaisesRegex(package.world.client.base.DiagnosticError, 'Case-conflicting world leaf'):
            self.install()
        self.assert_no_graph(); duplicate.rename(original)

    def test_unreferenced_case_colliding_directories_and_leaves_are_refused(self):
        self.mixed_case_directories()
        parent = self.runtime/'Data/Object_Library/unreferenced'
        parent.mkdir()
        first, second = parent/'Group', parent/'group'
        first.mkdir(); second.mkdir()
        with self.assertRaisesRegex(ValueError, 'Case-conflicting Atlas source inventory'):
            self.install()
        self.assert_no_graph(); first.rmdir(); second.rmdir()
        first, second = parent/'note.ini', parent/'NOTE.INI'
        first.write_bytes(b'one'); second.write_bytes(b'two')
        with self.assertRaisesRegex(ValueError, 'Case-conflicting Atlas source inventory'):
            self.install()
        self.assert_no_graph()

    def test_case_variant_existing_graph_is_preserved_without_alternate_directory(self):
        self.mixed_case_directories()
        graph = self.runtime/'Data/Server/Maps/City_Zones/City_01_01/CITY_01_01.TXT.v8.bcn'
        graph.write_bytes(b'previous case-variant graph must survive')
        before = graph.read_bytes()
        with self.assertRaisesRegex(package.world.client.base.DiagnosticError, 'Case-conflicting world leaf'):
            self.install()
        self.assertEqual(graph.read_bytes(), before)
        self.assert_no_graph()
        self.assertFalse((self.runtime/'data').exists())
        self.assertFalse((self.runtime/'Data/server').exists())

    def test_declared_casefold_duplicate_leaves_are_refused_before_installation(self):
        original = 'data/object_library/test/g1.geo'
        self.value['input_files']['data/object_library/test/G1.GEO'] = dict(self.value['input_files'][original])
        self.refresh_physical_profiles(); self.freeze()
        with self.assertRaisesRegex(ValueError, 'Atlas collision/group source identity differs'):
            self.install()
        self.assert_no_graph()

    def test_raw_donor_and_physical_digests_are_distinct_and_cannot_be_swapped(self):
        identity = self.value['input_identity']
        raw = identity['visual_object_geometry_sha256']
        physical = identity['required_geometry_sha256']
        self.assertEqual(raw, package.VISUAL_OBJECT_GEOMETRY_SHA256)
        self.assertNotEqual(raw, physical)
        identity['visual_object_geometry_sha256'] = physical
        identity['required_geometry_sha256'] = raw
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'different world/geometry supplement'):
            self.install()
        self.assertFalse((self.runtime/package.GRAPH).exists())
        self.assertFalse((self.runtime/package.MARKER).exists())

    def test_metadata_rich_records_are_refused_even_with_refrozen_physical_digests(self):
        for inventory in ('input_files', 'required_geometry_files'):
            with self.subTest(inventory=inventory):
                row = next(iter(self.value[inventory].values()))
                row['source_archive'] = 'synthetic-donor-rich-metadata'
                self.refresh_physical_profiles()
                self.freeze()
                with self.assertRaisesRegex(ValueError, 'Invalid native input/payload pin'):
                    self.install()
                self.assertFalse((self.runtime/package.GRAPH).exists())
                self.assertFalse((self.runtime/package.MARKER).exists())
                row.pop('source_archive')
                self.refresh_physical_profiles()

    def test_readonly_verified_worktree_required(self):
        with self.assertRaisesRegex(ValueError,'readonly private world'):
            package.install(self.archive,self.manifest,self.runtime,context=Context(),imported_inputs_readonly=False)


if __name__=='__main__':unittest.main()

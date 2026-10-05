"""Bounded install/reuse checks; synthetic fixtures do not claim native graphs."""
import hashlib
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
        self.optional_inputs = {'data/object_library/optional/g%d.geo'%i:
                                b'fixture optional geometry %d'%i for i in range(package.OPTIONAL_GEOS)}
        for name, raw in self.inputs.items():
            path = self.runtime/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); path.chmod(0o400)
        (self.runtime/'data/tricks').mkdir()
        exe = self.runtime/'MapServer.exe'; exe.write_bytes(b'fixture stock native identity')
        self.payloads = {package.GRAPH: b'unit test graph fixture body only', package.DATE: struct.pack('<iII',9,1767225600,0x10203040)}
        p = lambda raw: {'bytes': len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        self.value = {'format':2,'role':package.ROLE,'map':package.MAP,
            'source_commit':package.SOURCE_COMMIT,'data_commit':package.DATA_COMMIT,
            'stock_mapserver_sha256':p(exe.read_bytes())['sha256'],'runtime_graph_readback':True,
            'physical_npc_pathing_validated':False,'files':{n:p(v) for n,v in self.payloads.items()},
            'input_files':{n:p(v) for n,v in self.inputs.items()},
            'optional_input_files':{n:p(v) for n,v in self.optional_inputs.items()},
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
        self.value['input_identity']['optional_physical_geometry_sha256'] = hashlib.sha256(
            package.canonical(self.value['optional_input_files'])).hexdigest()
        self.value['input_profiles'] = {
            name: {'native': copy.deepcopy(self.value['native']),
                   'input_files_sha256': hashlib.sha256(package.canonical(selected)).hexdigest()}
            for name, selected in (
                ('base_world', self.value['input_files']),
                ('base_world_visual', {**self.value['input_files'], **self.value['optional_input_files']}))}
        self.manifest = self.root/package.MANIFEST; self.archive = self.root/package.ARCHIVE
        self.freeze()

    def freeze(self):
        raw=package.canonical(self.value); self.manifest.write_bytes(raw)
        with zipfile.ZipFile(self.archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr(package.MANIFEST,raw)
            for name,data in self.payloads.items():z.writestr(name,data)
        for name,value in [('MANIFEST_SHA256',hashlib.sha256(raw).hexdigest()),
                           ('ARCHIVE_SHA256',package.pin(self.archive)['sha256']),
                           ('ARCHIVE_BYTES',self.archive.stat().st_size),
                           ('OPTIONAL_GEOMETRY_SHA256',hashlib.sha256(
                               package.canonical(self.value['optional_input_files'])).hexdigest()),
                           ('STOCK_MAPSERVER_SHA256',self.value['stock_mapserver_sha256'])]:
            patch=mock.patch.object(package,name,value);patch.start();self.addCleanup(patch.stop)

    def refresh_physical_profiles(self):
        # A refrozen fixture may have internally consistent digests while its
        # physical pin shape is invalid; read_manifest must still refuse it.
        self.value['input_files_sha256'] = hashlib.sha256(
            package.canonical(self.value['input_files'])).hexdigest()
        self.value['input_identity']['optional_physical_geometry_sha256'] = hashlib.sha256(
            package.canonical(self.value['optional_input_files'])).hexdigest()
        for name, selected in (
                ('base_world', self.value['input_files']),
                ('base_world_visual', {**self.value['input_files'], **self.value['optional_input_files']})):
            self.value['input_profiles'][name]['input_files_sha256'] = hashlib.sha256(
                package.canonical(selected)).hexdigest()

    def install(self):
        return package.install(self.archive,self.manifest,self.runtime,context=Context(),imported_inputs_readonly=True)

    def add_optional_inputs(self, names=None):
        selected = self.optional_inputs if names is None else names
        for name, path in package.actual_targets(self.runtime, selected, Context()).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.optional_inputs[name]); path.chmod(0o400)

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
        self.assertEqual(first['server_geometry_profile'], 'base_world')
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

    def test_mixed_case_directories_install_complete_optional_profile_and_reuse(self):
        self.mixed_case_directories()
        self.add_optional_inputs()
        first = self.install()
        self.assertEqual(first['server_geometry_profile'], 'base_world_visual')
        self.assertEqual(first['input_files_checked'], len(self.inputs) + len(self.optional_inputs))
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
        self.assertEqual(installed['server_geometry_profile'], 'base_world')
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
        physical = identity['optional_physical_geometry_sha256']
        self.assertEqual(raw, package.VISUAL_OBJECT_GEOMETRY_SHA256)
        self.assertNotEqual(raw, physical)
        identity['visual_object_geometry_sha256'] = physical
        identity['optional_physical_geometry_sha256'] = raw
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'different world/geometry supplement'):
            self.install()
        self.assertFalse((self.runtime/package.GRAPH).exists())
        self.assertFalse((self.runtime/package.MARKER).exists())

    def test_metadata_rich_records_are_refused_even_with_refrozen_physical_digests(self):
        for inventory in ('input_files', 'optional_input_files'):
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

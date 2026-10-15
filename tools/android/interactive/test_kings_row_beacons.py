"""Reject partial native evidence and tampered external graph packages."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import generate_kings_row_beacons as host
guest=host.manifest_validator()


class NativeKingsProofTests(unittest.TestCase):
    def complete_package(self,root,change=None):
        graph=b'complete native graph fixture';date=struct.pack('<iII',9,0,0x12345678)
        native=host.native_evidence(
            b'COH_KINGS_ROW_COLLISION_LOAD_V1 missing_groups=0 missing_root_models=0\n'
            b'COH_KINGS_ROW_BEACON_FRESH_WORLD_V1 crc=0x12345678\n'
            b'COH_KINGS_ROW_BEACON_NATIVE_V1 crc=0x12345678 combat=8000 connected=7900 ground=9000 raised=1 blocks=22 paths=32\n',date)
        pin=lambda raw:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        inputs={'data/object_library/input%03d.geo'%i:pin(b'input') for i in range(100)}
        inputs['data/'+host.MAP]=pin(b'map')
        identity=hashlib.sha256(host.canonical(inputs)).hexdigest()
        value={'format':1,'role':'authentic_native_kings_row_beacon_graph','map':host.MAP,'map_id':5,
            'source_commit':'0b75ade0c801735e10c5798f641948a45cc50488',
            'data_commit':'d51533ec8e6a9cf726b9214968077a05fdcf19f3',
            'files':{host.GRAPH:pin(graph),host.DATE:pin(date)},'native':native,
            'input_files':inputs,'input_files_sha256':identity,'runtime_graph_readback':True,
            'physical_zoning_verified':False,'input_profiles':{name:{'native':native,
                'input_files_sha256':identity} for name in host.PROFILES}}
        if change:change(value)
        raw=host.canonical(value);(root/host.MANIFEST).write_bytes(raw)
        with zipfile.ZipFile(root/host.ARCHIVE,'w') as archive:
            for name,data in ((host.GRAPH,graph),(host.DATE,date),(host.MANIFEST,raw)):
                archive.writestr(name,data)
        report={'status':'passed','cleanup_complete':True,'owned_roles':0,
            'native_worker_spawning_allowed':False,'build_input':host.producer.expected(),
            'repository_commit':'a'*40,'manifest':host.pin(root/host.MANIFEST),
            'archive':host.pin(root/host.ARCHIVE),'native':value['native'],
            'profile_proofs':value['input_profiles'],
            'source_files':{name:host.pin(host.ROOT/name) for name in host.SOURCE_FILES}}
        (root/host.REPORT).write_bytes(host.canonical(report))
        (root/host.LOCK).write_bytes(host.canonical({'format':1,'map_id':5,
            'manifest':report['manifest'],'archive':report['archive']}))
        return value

    def test_complete_package_validates_without_fcntl_or_guest_process_imports(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);value=self.complete_package(root)
            script='''import builtins,sys
original=builtins.__import__
def portable(name,*args,**kwargs):
    if name in ('fcntl','atlas_world_assets','client_startup_diagnostic','presentation_diagnostic','diagnostic'):
        raise ModuleNotFoundError('Android-only import attempted: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=portable
sys.path.insert(0,sys.argv[1])
import generate_kings_row_beacons as host
host.validate_package(sys.argv[2],'a'*40)
print('complete portable package passed')
'''
            result=subprocess.run([sys.executable,'-c',script,str(Path(host.__file__).parent),str(root)],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('complete portable package passed',result.stdout)
            self.assertEqual(host.validate_package(root,'a'*40),value)

    def test_portable_manifest_validation_retains_native_and_input_gates(self):
        changes=(lambda value:value['native'].update(native_pathfinder_successes=31),
                 lambda value:value['native'].update(native_collision_load_verified=False),
                 lambda value:value['native'].update(missing_root_models=1),
                 lambda value:value['input_profiles'].pop('cold_world'),
                 lambda value:value.update(source_commit='b'*40),
                 lambda value:value['input_files'].pop('data/'+host.MAP))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for change in changes:
                self.complete_package(root,change)
                with self.subTest(change=change),self.assertRaises(ValueError):
                    host.validate_package(root,'a'*40)

    def test_native_witness_requires_collision_crc_readback_and_32_routes(self):
        log=(b'COH_KINGS_ROW_COLLISION_LOAD_V1 missing_groups=0 missing_root_models=0\n'
             b'COH_KINGS_ROW_BEACON_FRESH_WORLD_V1 crc=0x12345678\n'
             b'COH_KINGS_ROW_BEACON_NATIVE_V1 crc=0x12345678 combat=8000 connected=7900 ground=9000 raised=1 blocks=22 paths=32\n')
        date=struct.pack('<iII',9,0,0x12345678)
        self.assertTrue(host.native_evidence(log,date)['native_collision_load_verified'])
        for invalid in (log.replace(b'paths=32',b'paths=31'),log.replace(b'missing_groups=0',b'missing_groups=1'),
                        log.replace(b'FRESH_WORLD_V1',b'NO_FRESH_WORLD'),log+log):
            with self.assertRaises(ValueError):host.native_evidence(invalid,date)
        with self.assertRaises(ValueError):host.native_evidence(log,struct.pack('<iII',9,0,0x12345679))

    def test_inherited_verify_flag_cannot_change_generation_role(self):
        with unittest.mock.patch.dict(host.os.environ,{'COH_ATLAS_BEACON_VERIFY_ONLY':'1','COH_KINGS_ROW_BEACON_VERIFY_ONLY':'1'}):
            self.assertNotIn('COH_KINGS_ROW_BEACON_VERIFY_ONLY',host.role_environment())
            self.assertNotIn('COH_ATLAS_BEACON_VERIFY_ONLY',host.role_environment(True))
            self.assertEqual(host.role_environment(True)['COH_KINGS_ROW_BEACON_VERIFY_ONLY'],'1')

    def test_runtime_lock_refuses_modified_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest=root/guest.MANIFEST;lock=root/guest.LOCK
            manifest.write_text('{}')
            lock.write_text(json.dumps({'format':1,'map_id':5,'manifest':host.pin(manifest),'archive':{}}))
            manifest.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'APK-owned lock'):guest.read_manifest(manifest,lock)

    def test_input_paths_do_not_admit_other_maps_or_traversal(self):
        self.assertTrue(guest.input_name('data/'+host.MAP))
        for value in ('data/maps/city_zones/city_01_01/city_01_01.txt','data/object_library/../../bad.geo',
                      '/data/object_library/a.geo','data/object_library/a.dll'):
            self.assertFalse(guest.input_name(value))


import unittest.mock
if __name__=='__main__':unittest.main()

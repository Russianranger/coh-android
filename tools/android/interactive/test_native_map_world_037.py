#!/usr/bin/env python3
"""Host tests for native world gate refusal paths; no simulated native pass."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest

import prepare_native_map_world_inputs_037 as inputs
import qualify_native_map_world_037 as gate


def parse6(payload=b'\x00\x00\x00\x00',date=1800,crc=23):
    def string(value):
        value=value.encode();raw=struct.pack('<H',len(value))+value
        return raw+b'\0'*((-len(raw))%4)
    deps=struct.pack('<I',1)+string('defs/x.txt')+struct.pack('<I',date)
    return b'CrypticS'+struct.pack('<I',crc)+string('Parse6')+string('Files1')+struct.pack('<I',len(deps))+deps+struct.pack('<I',len(payload))+payload


class EvidenceRefusal(unittest.TestCase):
    def status(self,map_id=5,port=7003,fields=''):
        return f'{map_id} maps/City_Zones/City_01_02/City_01_02.txt S: 1 / 1 Ip: 127.0.0.1:{port} Mem: 512 {fields}\n'
    def console(self,map_id=5):
        world,port,count=gate.WORLDS[map_id]
        return ('COH_GAME_LOOPBACK_ONLY=1 active: IPv4 loopback binding policy\n'
                f'COH_GAME_LOOPBACK_ONLY bind verified: protocol=udp address=127.0.0.1 port={port}\n'
                f'loading map: maps/City_Zones/{world}/{world}.txt..done\nloading beacons.. done\n'
                f'Created {count} PhysX objects\nLoaded actor spore grid\nfreeing all .geo files...done\n'
                'Checking memory.. done\nServer ready. (took 30.123 seconds)\n')
    def test_selected_world_status_is_independent_of_progress(self):
        self.assertEqual(gate.ready_status(self.status(),5)['port'],7003)
        self.assertEqual(gate.ready_status(self.status(fields='NotReady 1'),5),None)
    def test_status_rejects_wrong_world_port_and_duplicate_rows(self):
        for text,map_id in [(self.status(),1),(self.status(port=7001),5),(self.status()*2,5)]:
            with self.assertRaises(ValueError):gate.ready_status(text,map_id)
    def test_status_rejects_stale_or_nonloopback_endpoint(self):
        for text in [self.status().replace('S: 1 / 1','S: 99 / 1'),self.status().replace('127.0.0.1','0.0.0.0')]:
            with self.assertRaises(ValueError):gate.ready_status(text,5)
    def test_both_world_phase_parsers_preserve_scope(self):
        for map_id in (1,5):
            value=gate.world_markers(self.console(map_id),map_id)
            self.assertFalse(value['behavioral_collision_proven'])
            self.assertEqual(value['PhysX_objects'],gate.WORLDS[map_id][2])
    def test_world_rejects_missing_phase_wrong_geometry_and_duplicate_ready(self):
        for text in [self.console().replace('loading beacons.. done\n',''),self.console().replace('2166','2311'),self.console()+'Server ready. (took 31.000 seconds)\n']:
            with self.assertRaises(ValueError):gate.world_markers(text,5)
    def test_world_rejects_wrong_loopback_destination(self):
        with self.assertRaises(ValueError):gate.world_markers(self.console().replace('port=7003','port=7001'),5)
    def progress(self,pid=123,seq=2,completed=1,started=1,flags=0):
        return struct.pack('<8s10I',b'COHMAP1\0',1,128,pid,234,seq,36,started,completed,flags,37)+b'\0'*80
    def test_progress_binds_held_pid_and_completed_tick(self):
        value=gate.map_progress(self.progress(),123)
        self.assertEqual(value['tick_completed'],1)
        self.assertIsNone(gate.map_progress(self.progress(seq=3),123))
        with self.assertRaises(ValueError):gate.map_progress(self.progress(),999)
    def test_progress_refuses_reserved_bytes_counter_inversion_and_saturation(self):
        for raw in [self.progress(completed=2),self.progress(flags=1),self.progress()[:-1]+b'x']:
            with self.assertRaises(ValueError):gate.map_progress(raw,123)
    def test_windows_provider_aliases_are_refused(self):
        for path in ['../escape','/absolute','data/a\\b','data/CON.txt','data/a.','data/a ','data/a:b','data/Nul/x','data/a?b']:
            with self.assertRaises(ValueError):inputs.safe_windows_name(path)
        self.assertEqual(inputs.safe_windows_name('data/maps/City_Zones/City_01_02.txt'),'data/maps/City_Zones/City_01_02.txt')
    def test_regular_archive_and_timestamp_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);raw=b'actual source bytes';record={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mtime_ns':1767225600000000000}
            path=root/'provider.tar.gz'
            with tarfile.open(path,'w:gz') as archive:
                member=tarfile.TarInfo('data/x.txt');member.size=len(raw);archive.addfile(member,io.BytesIO(raw))
            provider={'archive':gate.pin(path),'files':{'data/x.txt':record}}
            gate.extract_provider(path,provider,root/'owned')
            self.assertEqual((root/'owned/data/x.txt').read_bytes(),raw)
            self.assertEqual((root/'owned/data/x.txt').stat().st_mtime_ns,record['mtime_ns'])
    def test_symlink_archive_never_materializes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'provider.tar.gz'
            with tarfile.open(path,'w:gz') as archive:
                member=tarfile.TarInfo('data/x');member.type=tarfile.SYMTYPE;member.linkname='/tmp/escape';archive.addfile(member)
            provider={'archive':gate.pin(path),'files':{'data/x':{'bytes':0,'sha256':hashlib.sha256(b'').hexdigest(),'mtime_ns':0}}}
            with self.assertRaises(ValueError):gate.extract_provider(path,provider,root/'owned')
            self.assertFalse((root/'owned/data/x').exists())
    def test_cache_added_or_removed_is_not_generation_authority(self):
        with self.assertRaises(ValueError):gate.validate_generation_changes(Path('/unused'),{}, {'data/bin/x.bin':{'bytes':4,'sha256':'0'*64}}, {})
    def test_parse6_payload_and_schema_changes_fail(self):
        original=parse6()
        for changed in [parse6(payload=b'new!'),parse6(crc=99)]:
            with self.assertRaises(ValueError):gate.generation.parse6_equivalence(original,changed)
    def test_dependency_only_generation_binds_actual_source_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data/defs/x.txt';source.parent.mkdir(parents=True);source.write_text('definition')
            os.utime(source,(1800,1800));cache=root/'data/bin/x.bin';cache.parent.mkdir();cache.write_bytes(parse6())
            before_raw=parse6(date=1700)
            before={'data/bin/x.bin':{'bytes':len(before_raw),'sha256':hashlib.sha256(before_raw).hexdigest()}}
            after={'data/bin/x.bin':gate.pin(cache)}
            proof=gate.validate_generation_changes(root,before,after,{'data/bin/x.bin':before_raw})
            self.assertTrue(proof['decoded_payload_and_schema_unchanged'])
            self.assertFalse(proof['Android_cache_authority_created'])
            os.utime(source,(2400,2400))
            with self.assertRaises(ValueError):gate.validate_generation_changes(root,before,after,{'data/bin/x.bin':before_raw})
    def test_non_windows_execution_never_reports_native_success(self):
        if os.name!='nt':
            with self.assertRaises(ValueError):gate.Memory(None).sample()
    def test_bad_manifest_cannot_claim_preparation_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'x.json';path.write_text(json.dumps({'format':1,'status':'passed','shipping_allowed':True}))
            with self.assertRaises(ValueError):gate.read_manifest(path)
    def test_exact_production_error_patterns_keep_asset_failures(self):
        self.assertTrue(gate.native_failures('Errorf: fatal definition error\n'))
        self.assertTrue(gate.native_failures('MISSING ANIMATION male/test.anim\n'))
        self.assertEqual(gate.native_failures('Created 2166 PhysX objects\n'),[])
    def test_native_case_plan_covers_both_FX_variants_and_order_controls(self):
        plan=gate.phase_plan(Path('/baseline'),Path('/candidate'))
        self.assertEqual(len(plan),8)
        self.assertEqual([(v,p,r) for v,p,r,n in plan],[
            ('server_only','generation','stock'),('server_only','baseline-forward','baseline'),
            ('server_only','candidate-forward','candidate'),('server_only','candidate-reverse','candidate'),
            ('server_only','baseline-reverse','baseline'),('full','generation','stock'),
            ('full','baseline-forward','baseline'),('full','candidate-forward','candidate')])
    def test_warm_clone_excludes_stale_progress_native_logs_and_private_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'generated';source.mkdir()
            immutable=source/'data/defs/x.txt';immutable.parent.mkdir(parents=True);immutable.write_text('immutable definition')
            config=source/gate.CONFIG;config.parent.mkdir(parents=True);config.write_text('private current SQL credentials')
            native=source/'MapServer.exe';native.write_bytes(b'old observed native')
            cache=source/'data/bin/x.bin';cache.parent.mkdir(parents=True);cache.write_bytes(b'generated BIN')
            (source/'world-progress.bin').write_bytes(b'stale mapping')
            (source/'logs').mkdir();(source/'logs/map.log').write_text('old current session console')
            original_files={p.relative_to(source).as_posix():{**gate.pin(p),'mtime_ns':p.stat().st_mtime_ns//100*100}
                for p in (immutable,config,native,cache)}
            original_files['data/bin/x.bin']={'bytes':4,'sha256':hashlib.sha256(b'old!').hexdigest(),'mtime_ns':0}
            destination=root/'warm';generated={'data/bin/x.bin':gate.pin(cache)}
            proof=gate.clone_provider(source,{'files':original_files},destination,generated)
            self.assertTrue(proof['operational_members_excluded'])
            self.assertTrue(proof['generated_cache_byte_identity_checked'])
            self.assertEqual((destination/'data/bin/x.bin').read_bytes(),b'generated BIN')
            self.assertEqual((destination/'data/defs/x.txt').read_text(),'immutable definition')
            self.assertFalse((destination/'world-progress.bin').exists())
            self.assertFalse((destination/'logs').exists())
            self.assertFalse((destination/gate.CONFIG).exists())
            self.assertFalse((destination/'MapServer.exe').exists())
    def test_native_paths_enforce_UTF16_MAX_PATH_and_short_case_names(self):
        root=Path('C:/coh-world-38477608206/m10') if os.name=='nt' else Path('/tmp/coh-world-38477608206/m10')
        short=gate.native_path(root,'data/maps/City_Zones/City_01_02.txt')
        self.assertLess(len(str(short.absolute()).encode('utf-16-le'))//2,260)
        with self.assertRaises(ValueError):gate.native_path(root/'too-long-extra-case-name', 'data/'+'x'*220)
        with self.assertRaises(ValueError):gate.native_path(root,'data/'+'😀'*115)
    def test_FX_claim_requires_actual_successful_decode_and_stock_freshness(self):
        observation={'profile_rows':[{'phase':'bin_decode','input_token':'8a842dea','success':True,'elapsed_us':12}],
            'freshness_rows':[{'input_token':'ca526c44','outcome':'freshness_accepted'}]}
        value=gate.FX_consumption(observation,'full',inputs.FX_VARIANTS['full'])
        self.assertTrue(value['decoder_executed']);self.assertFalse(value['native_ID_table_observed'])
        for changed in [dict(observation,profile_rows=[]),dict(observation,freshness_rows=[]),
                        dict(observation,profile_rows=[{'phase':'bin_decode','input_token':'8a842dea','success':False}])]:
            with self.assertRaises(ValueError):gate.FX_consumption(changed,'full',inputs.FX_VARIANTS['full'])
        with self.assertRaises(ValueError):gate.FX_consumption(observation,'full',inputs.FX_VARIANTS['server_only'])
    def test_animation_claim_requires_actual_certificate_accounting(self):
        pig={'bytes':97084456,'sha256':'465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'}
        raw=('COH_ANIM_CERT_V1 schema=1 pack='+pig['sha256']+' opened=1024 certified=1024 fallback=0 crypto_failed=0 raw_bytes=900000 hash_us=50 stock_us=0 skipped_rot_keys=1000 skipped_pos_keys=1000 scanned_rot_keys=0 scanned_pos_keys=0\n').encode()
        self.assertTrue(gate.animation_consumption(raw,pig)['loaded_subset_only'])
        self.assertFalse(gate.animation_consumption(raw,pig)['whole_inventory_loaded_claimed'])
        for changed in [raw.replace(b'crypto_failed=0',b'crypto_failed=1'),raw.replace(b'certified=1024',b'certified=900'),b'']:
            with self.assertRaises(ValueError):gate.animation_consumption(changed,pig)


if __name__=='__main__':unittest.main()

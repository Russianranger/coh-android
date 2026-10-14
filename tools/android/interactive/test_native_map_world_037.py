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
from unittest.mock import patch,Mock

import prepare_native_map_world_inputs_037 as inputs
import qualify_native_map_world_037 as gate


def parse6(payload=b'\x00\x00\x00\x00',date=1800,crc=23,dependency='defs/x.txt'):
    def string(value):
        value=value.encode();raw=struct.pack('<H',len(value))+value
        return raw+b'\0'*((-len(raw))%4)
    deps=struct.pack('<I',1)+string(dependency)+struct.pack('<I',date)
    return b'CrypticS'+struct.pack('<I',crc)+string('Parse6')+string('Files1')+struct.pack('<I',len(deps))+deps+struct.pack('<I',len(payload))+payload


class EvidenceRefusal(unittest.TestCase):
    def test_windows_native_popen_owns_console_and_file_backed_handles(self):
        class Base:
            def close(self):
                for handle in self.handles:handle.close()
        owned=gate.owned_process_class(Base)
        with tempfile.TemporaryDirectory() as directory:
            logs=Path(directory);command=['MapServer.exe','-map','5'];env={'COH_GAME_LOOPBACK_ONLY':'1'}
            child=Mock();child.stdin=None
            with patch.object(gate.os,'name','nt'),patch.object(gate.subprocess,'CREATE_NEW_CONSOLE',16,create=True),patch.object(gate.subprocess,'Popen',return_value=child) as popen:
                process=owned(command,logs,logs,'map',env=env)
                popen.assert_called_once_with(command,cwd=logs,env=env,stdin=gate.subprocess.DEVNULL,
                    stdout=process.handles[0],stderr=process.handles[1],creationflags=16)
                self.assertIs(process.child,child)
                self.assertEqual([Path(h.name).name for h in process.handles],['map-stdout.log','map-stderr.log'])
                self.assertFalse(any(h.closed for h in process.handles))
            process.close()
            self.assertTrue(all(h.closed for h in process.handles))
    def test_windows_launch_failure_closes_exact_opened_handles(self):
        closed=[]
        class Base:
            def close(self):
                closed.extend(self.handles)
                for handle in self.handles:handle.close()
        with tempfile.TemporaryDirectory() as directory:
            logs=Path(directory)
            with patch.object(gate.os,'name','nt'),patch.object(gate.subprocess,'CREATE_NEW_CONSOLE',16,create=True),patch.object(gate.subprocess,'Popen',side_effect=OSError('launch failure')):
                with self.assertRaises(OSError):gate.owned_process_class(Base)(['MapServer.exe'],logs,logs,'failed')
            self.assertEqual(len(closed),2)
            self.assertTrue(all(h.closed for h in closed))
    def test_linux_native_process_uses_existing_base_constructor(self):
        class Base:
            def __init__(self,*args,**kwargs):self.forwarded=(args,kwargs)
        with patch.object(gate.os,'name','posix'),patch.object(gate.subprocess,'Popen') as popen:
            process=gate.owned_process_class(Base)(['command'],'cwd','logs','label',env={'a':'b'},interactive=True)
            self.assertEqual(process.forwarded,((['command'],'cwd','logs','label'),{'env':{'a':'b'},'interactive':True}))
            popen.assert_not_called()
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
            self.assertTrue(proof['existing_decoded_payload_and_schema_unchanged'])
            self.assertFalse(proof['Android_cache_authority_created'])
            os.utime(source,(2400,2400))
            with self.assertRaises(ValueError):gate.validate_generation_changes(root,before,after,{'data/bin/x.bin':before_raw})
    def test_exact_stock_new_geometry_BIN_binds_original_sources_and_warm_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data/object_library/x.txt';source.parent.mkdir(parents=True)
            source.write_text('immutable geometry definition');os.utime(source,(1800,1800))
            name='data/geobin/object_library/x.bin';cache=root/name;cache.parent.mkdir(parents=True)
            cache.write_bytes(parse6(dependency='object_library/x.txt'))
            original={'data/object_library/x.txt':{**gate.pin(source),'mtime_ns':source.stat().st_mtime_ns}}
            proof=gate.validate_generation_changes(root,{}, {name:gate.pin(cache)}, {},original)
            self.assertFalse(proof['Parse6_dependency_envelope_changes'][name]['original_payload_comparison_available'])
            self.assertEqual(proof['actual_dependency_sources'][name][0]['actual_source'],gate.pin(source))
            provider={'files':original};destination=root/'warm'
            gate.clone_provider(root,provider,destination,{name:gate.pin(cache)})
            self.assertEqual((destination/name).read_bytes(),cache.read_bytes())
            for authority in ({},dict(original,**{'data/object_library/x.txt':dict(original['data/object_library/x.txt'],sha256='0'*64)})):
                with self.assertRaises(ValueError):gate.validate_generation_changes(root,{}, {name:gate.pin(cache)}, {},authority)
    def test_new_geometry_BIN_outside_fixed_source_roots_is_refused(self):
        for name in ['data/geobin/player_library/x.bin','data/geobin/maps/x.tmp','data/geobin/maps/x.bounds',
                     'data/geobin/player_library/x.bounds','data/bin/unreviewed.bin','world-progress.bin']:
            self.assertFalse(gate.generated_cache_name(name))
            with tempfile.TemporaryDirectory() as directory:
                source=Path(directory)/'source';source.mkdir()
                with self.assertRaises(ValueError):gate.clone_provider(source,{'files':{}},Path(directory)/'warm',
                    {name:{'bytes':4,'sha256':'0'*64}})
    def test_new_plaque_MessageStore_uses_its_own_schema_and_original_English_closure(self):
        def table(values):
            raw=b''.join(x+b'\0' for x in values);return struct.pack('<II',len(values),len(raw))+raw
        data=(struct.pack('<I',20090521)+table([b'hello',b'help'])+table([])+struct.pack('<I',1)
              +struct.pack('<I',5)+b'HELLO'+struct.pack('<III',0,1,0))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data/texts/English/server/plaques/Atlas.ms';source.parent.mkdir(parents=True)
            source.write_text('HELLO "hello"');os.utime(source,(1800,1800))
            name='data/server/bin/plaquemsg-en.bin';cache=root/name;cache.parent.mkdir(parents=True);cache.write_bytes(data)
            original={source.relative_to(root).as_posix():{**gate.pin(source),'mtime_ns':source.stat().st_mtime_ns}}
            proof=gate.validate_generation_changes(root,{}, {name:gate.pin(cache)}, {},original)
            self.assertEqual(proof['new_MessageStore_outputs'][name]['structure']['schema_version'],20090521)
            self.assertNotIn(name,proof['Parse6_dependency_envelope_changes'])
            with self.assertRaises(ValueError):gate.validate_generation_changes(root,{}, {name:gate.pin(cache)}, {},{})
            cache.write_bytes(data+b'corruption')
            with self.assertRaises(ValueError):gate.validate_generation_changes(root,{}, {name:gate.pin(cache)}, {},original)
    def test_geometry_cache_snapshot_includes_only_fixed_native_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data/bin').mkdir(parents=True);(root/'data/server/bin').mkdir(parents=True)
            (root/'data/bin/sequencers.bin').write_bytes(b'original')
            path=root/'data/geobin/maps/City_Zones/City_01_02.bin';path.parent.mkdir(parents=True);path.write_bytes(b'geometry')
            self.assertIn(path.relative_to(root).as_posix(),gate.cache_snapshot(root))
            bad=root/'data/geobin/unknown/x.bin';bad.parent.mkdir();bad.write_bytes(b'unsupported')
            with self.assertRaises(ValueError):gate.cache_snapshot(root)
    def test_geometry_bounds_are_typed_Parse6_and_retain_exact_native_output_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data/object_library/x.txt';source.parent.mkdir(parents=True)
            source.write_text('immutable geometry');os.utime(source,(1800,1800))
            name='data/geobin/object_library/x.bounds';cache=root/name;cache.parent.mkdir(parents=True)
            cache.write_bytes(parse6(dependency='object_library/x.txt'))
            original={'data/object_library/x.txt':{**gate.pin(source),'mtime_ns':source.stat().st_mtime_ns}}
            after={name:gate.pin(cache)};proof=gate.validate_generation_changes(root,{},after,{},original)
            self.assertEqual(proof['Parse6_dependency_envelope_changes'][name]['kind'],'GroupBounds_Parse6')
            output=root/'evidence';output.mkdir();retained=gate.retain_generation_outputs(root,{},after,output)
            with tarfile.open(output/'stock-native-generated-cache-outputs.tar.gz','r:gz') as archive:
                self.assertEqual(archive.getnames(),[name]);self.assertEqual(archive.extractfile(name).read(),cache.read_bytes())
            self.assertEqual(retained['members'][name]['sha256'],after[name]['sha256'])
            warm=root/'warm';gate.clone_provider(root,{'files':original},warm,after)
            self.assertEqual(gate.cache_dates(root,after),gate.cache_dates(warm,after))
            before_dates=gate.cache_dates(warm,after);os.utime(warm/name,(2400,2400))
            self.assertEqual(gate.pin(warm/name),after[name]);self.assertNotEqual(gate.cache_dates(warm,after),before_dates)
    def test_Map_command_flushes_owned_console_without_changing_assertion_or_world_policy(self):
        for map_id in (1,5):
            command=gate.map_command('MapServer.exe',map_id)
            self.assertNotIn('-nogui',command);self.assertNotIn('-productionmode',command)
            self.assertEqual(command[command.index('-assertmode')+1],str(8192|64))
            self.assertEqual(command[command.index('-map_id')+1],str(map_id))
            self.assertEqual(command[command.index('-udp')+1],str(gate.WORLDS[map_id][1]))
            self.assertIn('-nosharedmemory',command)
    def namespace_fixture(self,root,unknown_member=False):
        names=[f'player_library/animations/test/i{i}.anim'.encode()+b'\0' for i in range(5878)]
        if unknown_member:names[-1]=b'object_library/x.txt\0'
        pool=b''.join(struct.pack('<I',len(n))+n for n in names)
        raw=(gate.animation_package.HEADER.pack(0x123,2,2,16,48,5878)
            +b'\0'*(gate.animation_package.ENTRY.size*5878)+struct.pack('<III',0x6789,5878,len(pool))+pool)
        pig=root/'piggs/server-animations.pigg';pig.parent.mkdir();pig.write_bytes(raw)
        (root/'data').mkdir();return gate.pin(pig)
    def negative_fixture(self,root):
        source=root/'data/object_library/x.rootnames';source.parent.mkdir(parents=True)
        source.write_bytes(b'original root names');os.utime(source,(1800,1800))
        original={'data/object_library/x.rootnames':{**gate.pin(source),'mtime_ns':source.stat().st_mtime_ns}}
        proof={'data/geobin/object_library/x.bin':{'after':{'dependencies':[
            {'path':'object_library/x.txt','timestamp':0},{'path':'object_library/x.rootnames','timestamp':1800}]}}}
        return proof,original
    def test_native_zero_date_is_a_scoped_absence_plus_real_original_rootnames(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);pig=self.namespace_fixture(root);proof,original=self.negative_fixture(root)
            with patch.object(gate,'ANIMATION_PIG',pig):rows,negative=gate.bind_world_dependencies(root,proof,original)
            values=rows['data/geobin/object_library/x.bin']
            self.assertEqual(values[0]['actual_source'],gate.pin(root/'data/object_library/x.rootnames'))
            self.assertEqual(values[1]['kind'],'native_same_stem_missing_text_sentinel')
            self.assertTrue(values[1]['current_native_namespace_source_absent'])
            self.assertEqual((negative['rows'],negative['unique_paths']),(1,1))
            self.assertEqual(negative['namespace']['complete_Pig_member_count'],5878)
            self.assertEqual(proof['data/geobin/object_library/x.bin']['after']['dependencies'][0]['timestamp'],0)
    def test_zero_date_never_ignores_a_present_original_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);proof,original=self.negative_fixture(root)
            original['data/OBJECT_LIBRARY/X.TXT']={'bytes':1,'sha256':'0'*64,'mtime_ns':0}
            with self.assertRaises(ValueError):gate.bind_world_dependencies(root,proof,original)
    def test_negative_dependency_checks_current_case_alias_and_links(self):
        for linked in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);pig=self.namespace_fixture(root);proof,original=self.negative_fixture(root)
                alias=root/'data/object_library/X.TXT'
                if linked:alias.symlink_to('missing-target')
                else:alias.write_bytes(b'new unapproved source')
                with patch.object(gate,'ANIMATION_PIG',pig):
                    with self.assertRaises(ValueError):gate.bind_world_dependencies(root,proof,original)
    def test_zero_date_scope_rejects_unrelated_global_map_or_nonmatching_geometry(self):
        for cache,path in [('data/bin/x.bin','object_library/x.txt'),
            ('data/geobin/maps/x.bin','maps/x.txt'),('data/geobin/object_library/x.bin','object_library/y.txt'),
            ('data/geobin/object_library/x.bounds','object_library/x.rootnames')]:
            proof={cache:{'after':{'dependencies':[{'path':path,'timestamp':0}]}}}
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):gate.bind_world_dependencies(Path(directory),proof,{})
    def test_nonzero_missing_dependency_remains_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            proof={'data/geobin/object_library/x.bin':{'after':{'dependencies':[{'path':'object_library/x.txt','timestamp':1800}]}}}
            with self.assertRaises(ValueError):gate.bind_world_dependencies(root,proof,{})
    def test_native_namespace_rejects_unknown_Pig_members_or_unpinned_archive(self):
        for unknown_member in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);pig=self.namespace_fixture(root,unknown_member=unknown_member)
                if unknown_member:
                    with patch.object(gate,'ANIMATION_PIG',pig):
                        with self.assertRaises(ValueError):gate.native_namespace(root)
                else:
                    with self.assertRaises(ValueError):gate.native_namespace(root)
    def test_native_namespace_rejects_additional_provider_controls_and_archives(self):
        for name in ('gamedatadir.txt','localdata','serverdata','tools','piggs/unknown.pigg'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);pig=self.namespace_fixture(root);path=root/name
                if name in ('localdata','serverdata','tools'):path.mkdir()
                else:path.write_text('unapproved provider')
                with patch.object(gate,'ANIMATION_PIG',pig):
                    with self.assertRaises(ValueError):gate.native_namespace(root)
    def test_native_namespace_refuses_unreadable_directory_enumeration(self):
        def failed_walk(root,*,followlinks,onerror):
            onerror(PermissionError('an inaccessible possible provider'))
            return iter(())
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate.os,'walk',side_effect=failed_walk):
                with self.assertRaisesRegex(ValueError,'absence cannot be proven'):
                    gate.native_namespace(Path(directory))
    def test_inherited_stock_refuses_unpinned_evidence_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'fake.zip';path.write_bytes(b'fake native success')
            with self.assertRaises(ValueError):gate.load_inherited_stock(path,root,{})
            self.assertFalse((root/'inherited-stock-04b').exists())
    def test_inherited_stock_refuses_changed_provider_before_any_cache_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'immutable';source.write_bytes(b'preserved')
            inherited={'facts':{'cache_before':{},'cache_dates_before':{},'provider_before':{'identity':'old'}},
                       'retention':{'members':{}}}
            with self.assertRaises(ValueError):gate.recover_stock_cache(root,{}, {},{'identity':'changed'}, {},{},inherited,root)
            self.assertEqual(source.read_bytes(),b'preserved')
    def test_failed_progress_retains_raw_held_PID_without_admitting_world(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'progress';path.write_bytes(self.progress()+b'\0'*(4096-128))
            process=Mock();process.child.pid=123;process.child.poll.return_value=None
            result=gate.progress_snapshot(path,process)
            self.assertEqual(bytes.fromhex(result['raw_record_hex']),self.progress())
            self.assertEqual(result['decoded_record']['tick_completed'],1)
            process.child.pid=999;result=gate.progress_snapshot(path,process)
            self.assertIn('decoding_failure',result);self.assertNotIn('decoded_record',result)
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

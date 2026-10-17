#!/usr/bin/env python3
"""Offline protocol/refusal controls. No live source token is ever minted here."""
import copy,hashlib,importlib.util,json,os,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('source_admission',HERE/'admit_source_snapshot.py')
admit=importlib.util.module_from_spec(spec);spec.loader.exec_module(admit)
def identity(n=10):return {'bytes':n,'sha256':'b'*64}
def documents():
    native={'binary':identity(145704),'dependencies_sha256':{'native-android/offline.c':'a'*64}}
    compiled={'artifacts':{'MapServer.exe':identity(7504384)}}
    sources={'native-android/offline.py':'c'*64};inventory={'files':4,'bytes':100,'ordered_inventory_sha256':'d'*64}
    pair={'schema':'coh-original-native-groups-pair-v1','passed':True,
        'source_run_provenance_verified':False,'cache_equivalence_verified':False,
        'source_generation_admitted':False,'actor_identity_verified':False,'world_authority':False,
        **{name:True for name in admit.public_status.PAIR}}
    report={'schema':'coh-private-original-native-groups-run-v1','passed':True,'private_character_state':True,
        'public_upload_permitted':False,'local_development_auth':True,'authserver_authenticated':False,
        'source_generation_admitted':False,'world_authority':False,'capture_stage':'COMPLETE','failure_stage':'NONE',
        'existing_character_rows_seeded':False,'new_character_created':False,'existing_character_count':1,
        'source_sha256':sources,'existing_database_dump':identity(),'compile_receipt_sha256':'e'*64,
        'original_map_binary':compiled['artifacts']['MapServer.exe'],'native_tool':native,'runtime_inventory':inventory,
        'pair':pair,**{name:True for name in admit.public_status.STATUS}}
    run={'schema':'coh-private-original-native-groups-identity-v1','nonce':'f'*64,'source_revision':'a'*40,
        'private_fresh_wine_prefix':True,'private_fresh_pg_cluster':True,'restored_existing_database_only':True,
        'source_sha256':sources,'database_dump':identity(),'compile_receipt_sha256':'e'*64,
        'native_build_receipt_sha256':'f'*64,'runtime_inventory':inventory}
    expected=('a'*40,sources,identity(),compiled,native,'e'*64,'f'*64,inventory)
    return report,run,expected
def verifier(root):
    names=sorted(admit.REQUIRED_VERIFIER_SOURCES)
    hashes={}
    for name in names:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'offline source\n')
        hashes[name]=admit.d.hash_file(path,1024)[1]
    inputs={name:identity(10+index) for index,name in enumerate(sorted(admit.INPUT_NAMES))}
    inputs['native/groups.bin']=inputs['packet.bin']
    inspection={'files':{name:dict(inputs[name],chunks=1) for name in admit.envelope.NAMES.values()}}
    executable=identity(1234);capture=identity(8000)
    counts=dict.fromkeys(admit.COUNTS,0);counts.update(files=4,definitions=8,
        named_peak_reservation_bytes=32*1024**2,named_aggregate_limit_bytes=96*1024**2)
    receipt={'schema':'coh-source-snapshot-native-verification-v1','passed':True,**dict.fromkeys(admit.VERIFIER_FALSE,False),
        'world_authority':False,'capture':capture,'executable':executable,'inputs':inputs,'source_sha256':hashes,
        'source_revision':'a'*40,'exact_native_packet_bytes_verified':True,'private_receipt':True,
        'checks':{name:True for name in admit.CHECKS},'counts':counts,
        'build':{'source_sha256':hashes,'compiler':'offline fixture only','flags':list(admit.FLAGS),
            'libraries':['crypto','z','m'],'current_committed_sources_verified':True,'mode':'release',
            'maximum_static_frame_bytes':1024,'control_digest_stack_reserve_bytes':512*1024}}
    return receipt,inspection,capture,inputs['native/groups.bin'],executable
class Controls(unittest.TestCase):
    def verify(self,value,inspection,capture,native,exe,root,expected_sources=None):
        return admit.verify_native(value,inspection,capture,native,exe,'a'*40,
                value['source_sha256'] if expected_sources is None else expected_sources,root)
    def test_pure_protocol_closure_never_mints_authority(self):
        report,run,expected=documents();result=admit.verify_documents(report,run,*expected)
        self.assertTrue(result['protocol_closure_verified'])
        self.assertFalse(result['source_generation_admitted']);self.assertFalse(result['world_authority'])
        self.assertNotIn('source_snapshot_token_sha256',result)
    def test_run_ownership_source_input_and_cleanup_refusals(self):
        baseline,run,expected=documents()
        changes=[('passed',False),('cleanup_verified',False),('owned_process_groups_absent',False),
            ('private_input_bytes_unchanged',False),('restored_private_copy_unchanged',False),
            ('source_runtime_unchanged',False),('compiled_inputs_unchanged',False),
            ('existing_character_count',True),('existing_character_count',2),('existing_character_rows_seeded',True),
            ('new_character_created',True),('source_generation_admitted',True),('world_authority',True),
            ('public_upload_permitted',True),('authserver_authenticated',True),('capture_stage','secret')]
        for key,bad in changes:
            report=copy.deepcopy(baseline);report[key]=bad
            with self.subTest(report=key,bad=bad),self.assertRaises((admit.Refused,admit.public_status.Refused)):
                admit.verify_documents(report,run,*expected)
        for key,bad in [('schema','other'),('nonce','wrong'),('source_revision','0'*40),
            ('private_fresh_wine_prefix',1),('private_fresh_pg_cluster',False),('restored_existing_database_only',False),
            ('source_sha256',{}),('database_dump',identity(11)),('compile_receipt_sha256','0'*64),
            ('native_build_receipt_sha256','0'*64),('runtime_inventory',{'files':True,'bytes':100,'ordered_inventory_sha256':'d'*64})]:
            value=copy.deepcopy(run);value[key]=bad
            with self.subTest(run=key),self.assertRaises((admit.Refused,admit.public_status.Refused)):
                admit.verify_documents(baseline,value,*expected)
    def test_whole_verifier_input_closure_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);value,inspection,capture,native,exe=verifier(root)
            result=self.verify(value,inspection,capture,native,exe,root)
            self.assertTrue(result['native_associations_verified']);self.assertFalse(result['source_generation_admitted'])
            for name in admit.INPUT_NAMES:
                changed=copy.deepcopy(value);changed['inputs'][name]=identity(999)
                with self.subTest(input=name),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
            for name in admit.CHECKS:
                changed=copy.deepcopy(value);changed['checks'][name]=1
                with self.subTest(check=name),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
            for key in ('passed','exact_native_packet_bytes_verified','private_receipt',*admit.VERIFIER_FALSE):
                changed=copy.deepcopy(value);changed[key]=int(changed[key])
                with self.subTest(flag=key),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
    def test_verifier_executable_build_and_source_ownership(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);value,inspection,capture,native,exe=verifier(root)
            for key,bad in [('capture',identity(1)),('executable',identity(1)),('source_sha256',{}),
                            ('build',{'compiler':'cc','command':['cc'],'source_sha256':{}}),
                            ('counts',{'bad':True})]:
                changed=copy.deepcopy(value);changed[key]=bad
                with self.subTest(key=key),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
            for name in list(value['source_sha256']):
                path=root/name;previous=path.read_bytes();path.write_bytes(b'drift')
                with self.subTest(source=name),self.assertRaises(admit.Refused):
                    self.verify(value,inspection,capture,native,exe,root)
                path.write_bytes(previous)
            changed=copy.deepcopy(value);changed['source_sha256']['native-android/../secret']='a'*64
            with self.assertRaises(admit.Refused):self.verify(changed,inspection,capture,native,exe,root)
            with self.assertRaises(admit.Refused):self.verify(value,inspection,capture,native,exe,root,{})
    def test_release_shape_and_every_counter_refuse_boolean_omitted_or_added_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);value,inspection,capture,native,exe=verifier(root)
            for field in admit.COUNTS:
                for bad in (True,-1,0x100000000):
                    changed=copy.deepcopy(value);changed['counts'][field]=bad
                    with self.subTest(counter=field,bad=bad),self.assertRaises(admit.Refused):
                        self.verify(changed,inspection,capture,native,exe,root)
                changed=copy.deepcopy(value);del changed['counts'][field]
                with self.subTest(omitted=field),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
            for bad in ({**value['counts'],'unreviewed':1},
                        {**value['counts'],'named_aggregate_limit_bytes':96*1024**2+1},
                        {**value['counts'],'named_peak_reservation_bytes':96*1024**2+1}):
                changed=copy.deepcopy(value);changed['counts']=bad
                with self.assertRaises(admit.Refused):self.verify(changed,inspection,capture,native,exe,root)
            for key,bad in [('mode','asan'),('flags',list(admit.FLAGS)+['-g']),
                            ('libraries',['crypto','z']),('current_committed_sources_verified',1),
                            ('maximum_static_frame_bytes',True),('maximum_static_frame_bytes',512*1024),
                            ('control_digest_stack_reserve_bytes',True)]:
                changed=copy.deepcopy(value);changed['build'][key]=bad
                with self.subTest(build=key),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
            for key,bad in [('schema','wrong'),('source_revision','0'*40)]:
                changed=copy.deepcopy(value);changed[key]=bad
                with self.subTest(field=key),self.assertRaises(admit.Refused):
                    self.verify(changed,inspection,capture,native,exe,root)
    def test_imported_helper_must_match_committed_bytes_before_and_after(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);subprocess.run(['git','init','-q',root],check=True)
            helper=root/'imported.py';helper.write_bytes(b'accepted = False\n')
            subprocess.run(['git','add','imported.py'],cwd=root,check=True)
            subprocess.run(['git','-c','user.name=offline','-c','user.email=offline@example.invalid',
                            'commit','-qm','offline source closure control'],cwd=root,check=True)
            revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            pins={'imported.py':hashlib.sha256(helper.read_bytes()).hexdigest()}
            self.assertEqual(admit.committed_source_closure(root,pins,revision),pins)
            helper.write_bytes(b'accepted = True\n')
            with self.assertRaises(admit.Refused):admit.committed_source_closure(root,pins,revision)
            changed={'imported.py':hashlib.sha256(helper.read_bytes()).hexdigest()}
            with self.assertRaises(admit.Refused):admit.committed_source_closure(root,changed,revision)
            untracked=root/'untracked.py';untracked.write_bytes(b'accept = True\n')
            with self.assertRaises(admit.Refused):admit.committed_source_closure(root,
                {'untracked.py':hashlib.sha256(untracked.read_bytes()).hexdigest()},revision)
    def test_independent_pins_and_strict_numeric_identities(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'receipt.json';path.write_text('{"offline":true}')
            digest=admit.d.hash_file(path,1024)[1]
            self.assertEqual(admit.pinned_json(path,digest,1024),{'offline':True})
            with self.assertRaises(admit.Refused):admit.pinned_json(path,'0'*64,1024)
        for value in ({'bytes':True,'sha256':'a'*64},{'bytes':0,'sha256':'a'*64},
                      {'bytes':10,'sha256':'wrong'},{'bytes':10,'sha256':'a'*64,'extra':1}):
            with self.subTest(identity=value),self.assertRaises((admit.Refused,admit.d.Refused)):admit.pin(value)
    def test_fixture_character_identity_comes_from_exact_pinned_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);backup={'fixture_identity':{'character_id':123,'auth_id':4}}
            names=('original-guest-report.json','external-observer.json','backup-request.json','backup-receipt.json')
            for name in names:(root/name).write_text(json.dumps(backup if name=='backup-receipt.json' else {}))
            (root/'fixture.pgdump').write_bytes(b'PGDMPoffline fixture only')
            (root/'account.txt').write_bytes(b'COHLOCAL\n')
            receipt={'retained_creation_evidence':{name:admit.identity(root/name,1024) for name in names},
                     'full_backup':backup}
            (root/'fixture-capture.json').write_text(json.dumps(receipt))
            digest=admit.identity(root/'fixture-capture.json',8192)['sha256']
            admitted={'database_dump_sha256':admit.identity(root/'fixture.pgdump',1024)['sha256']}
            with patch.object(admit.fixture_admission,'inspect',return_value=admitted):
                fixture,read,pins=admit.fixture_inputs(root,digest)
                self.assertEqual(read,backup);self.assertEqual(fixture,admitted)
                (root/'backup-receipt.json').write_text(json.dumps({'fixture_identity':{'character_id':456,'auth_id':4}}))
                with self.assertRaises(admit.Refused):admit.fixture_inputs(root,digest)
                (root/'backup-receipt.json').write_text(json.dumps(backup))
                (root/'fixture.pgdump').write_bytes(b'PGDMPchanged')
                with self.assertRaises(admit.Refused):admit.fixture_inputs(root,digest)
    def test_actual_host_gate_refuses_before_any_token_or_file_work(self):
        with patch.object(admit.platform,'machine',return_value='aarch64'),patch.object(admit,'pinned_json') as read:
            with self.assertRaises(admit.Refused):admit.admit(types.SimpleNamespace())
            read.assert_not_called()
    def test_cli_refusal_exposes_no_private_input_or_exception(self):
        with tempfile.TemporaryDirectory() as raw:
            output=Path(raw)/'must-not-exist.json';canary='PRIVATE_ACCOUNT_123_DBID_987_COOKIE_654'
            command=[sys.executable,str(HERE/'admit_source_snapshot.py')]
            for name in ('private-output','private-work','fixture-directory','runtime','control-fixture',
                'db-donor-apk','compile-directory','native-capture','native-build-receipt','verification',
                'verifier-executable'):command+=['--'+name,str(Path(raw)/canary)]
            command+=['--output',str(output)]
            for name in ('capture-receipt-sha256','run-identity-sha256','fixture-receipt-sha256',
                'compile-receipt-sha256','native-build-receipt-sha256','verification-sha256'):
                command+=['--'+name,'f'*64]
            environment={**os.environ,'RUNNER_ENVIRONMENT':'offline-control'}
            result=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,2);self.assertFalse(output.exists())
            self.assertNotIn(canary,result.stdout+result.stderr)
            self.assertNotIn(raw,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout),{'passed':False,'failure_code':'SOURCE_SNAPSHOT_REFUSED',
                'source_snapshot_generation_admitted':False,'world_authority':False})
            self.assertEqual(result.stderr,'')
    def test_receipt_publication_refuses_late_io_without_a_final_file(self):
        # I/O controls deliberately use a refusal-only object, never minting a
        # synthetic positive runtime source token.
        value={'schema':'offline-publication-control','passed':False}
        real_fdopen=os.fdopen
        class Stream:
            def __init__(self,stream,fail_flush,fail_close):
                self.stream=stream;self.fail_flush=fail_flush;self.fail_close=fail_close
            def write(self,value):return self.stream.write(value)
            def fileno(self):return self.stream.fileno()
            def flush(self):
                self.stream.flush()
                if self.fail_flush:raise OSError('primary-flush')
            def close(self):
                self.stream.close()
                if self.fail_close:raise OSError('secondary-close' if self.fail_flush else 'primary-close')
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);output=root/'receipt.json'
            for flush,close in ((True,False),(False,True),(True,True)):
                with self.subTest(flush=flush,close=close),patch.object(admit.os,'fdopen',
                    side_effect=lambda *a,**kw:Stream(real_fdopen(*a,**kw),flush,close)):
                    with self.assertRaisesRegex(OSError,'primary-flush' if flush else 'primary-close'):
                        admit.emit_public_receipt(output,value)
                self.assertFalse(output.exists());self.assertEqual(list(root.iterdir()),[])
            with patch.object(admit.os,'fsync',side_effect=OSError('primary-fsync')):
                with self.assertRaisesRegex(OSError,'primary-fsync'):admit.emit_public_receipt(output,value)
            self.assertFalse(output.exists());self.assertEqual(list(root.iterdir()),[])
            admit.emit_public_receipt(output,value)
            self.assertEqual(json.loads(output.read_bytes()),value)
            self.assertEqual(output.stat().st_nlink,1);self.assertEqual(output.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):admit.emit_public_receipt(output,{'passed':True})
            self.assertEqual(json.loads(output.read_bytes()),value);self.assertEqual(list(root.iterdir()),[output])
if __name__=='__main__':unittest.main(verbosity=2)

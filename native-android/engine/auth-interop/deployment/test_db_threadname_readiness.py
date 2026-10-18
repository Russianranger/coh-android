"""New-candidate admission/lifetime controls; no real service or SQL executes."""
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import hosted_db_threadname_readiness as stage

ROOT=Path(__file__).resolve().parents[4]
NEW_SHA='a'*64


class ReadinessTests(unittest.TestCase):
    def test_new_db_snapshot_uses_exact_candidate_pin_and_real_service_shape(self):
        child=mock.Mock(pid=4321);child.poll.return_value=None
        expected=Path('D:/owned/DbServer.exe')
        raw=dict(pid=4321,exists=True,name='DbServer',started_utc_ticks=639277996886036331,
                 executable_path='D:\\owned\\DbServer.exe')
        with mock.patch.object(stage.activation.prior,'capture',return_value=json.dumps(raw)),\
             mock.patch.object(stage.activation.prior,'sha',return_value=NEW_SHA):
            first=stage.activation.service_process_snapshot(child,expected,expected_binary_sha256=NEW_SHA)
            self.assertEqual(stage.activation.service_process_snapshot(child,expected,first,NEW_SHA),first)
            with self.assertRaises(ValueError):stage.activation.service_process_snapshot(child,expected,first)
            for changed in (dict(raw,pid=4322),dict(raw,name='Other'),dict(raw,started_utc_ticks=raw['started_utc_ticks']+1),dict(raw,executable_path='D:\\other\\DbServer.exe')):
                with mock.patch.object(stage.activation.prior,'capture',return_value=json.dumps(changed)),self.assertRaises(ValueError):
                    stage.activation.service_process_snapshot(child,expected,first,NEW_SHA)
        auth=dict(raw,name='AuthServer',executable_path='D:\\owned\\AuthServer.exe')
        with mock.patch.object(stage.activation.prior,'capture',return_value=json.dumps(auth)),\
             mock.patch.object(stage.activation.prior,'sha',return_value=NEW_SHA),self.assertRaisesRegex(ValueError,'candidate_binary_pin'):
            stage.activation.service_process_snapshot(child,Path('D:/owned/AuthServer.exe'),expected_binary_sha256=NEW_SHA)

    def test_candidate_pins_are_admitted_before_copy_and_rechecked(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp).resolve()/'stage';directory.mkdir();binary=directory/stage.candidate.BINARY;binary.write_bytes(b'new candidate fixture')
            pin=stage.candidate.digest(binary.read_bytes());receipt=directory/'receipt.json'
            receipt.write_text(json.dumps({'repository_commit':'b'*40,'source_file_map_sha256':'c'*64}))
            receipt_pin=stage.candidate.digest(receipt.read_bytes())
            admission={'admitted':True,'binary':{'sha256':pin},'service_executed':False}
            with mock.patch.object(stage,'admit_candidate',return_value=admission) as admit:
                scope=stage.DbCandidate(ROOT,directory,receipt_pin,pin)
                admit.assert_called_once_with(ROOT,directory,receipt_pin,pin)
                output=Path(temp)/'recovered';result=scope.recover(ROOT,output)
                self.assertEqual((output/scope.binary_name).read_bytes(),binary.read_bytes())
                self.assertFalse(result['separate_runtime_dlls_required'])
                with self.assertRaises(ValueError):scope.recover(ROOT,output)
                # Simulate replacement after byte admission, before the
                # wrapper reads origin metadata from that same receipt.
                def changed_second_read(*args):
                    receipt.write_text(json.dumps({'repository_commit':'e'*40,'source_file_map_sha256':'f'*64}))
                    return admission
                admit.side_effect=changed_second_read
                with self.assertRaisesRegex(ValueError,'pinned_file_identity'):
                    scope.recover(ROOT,Path(temp)/'mixed-origin-refused')
                self.assertFalse((Path(temp)/'mixed-origin-refused').exists())
                admit.side_effect=ValueError('new candidate byte admission refused')
                with self.assertRaises(ValueError):scope.recover(ROOT,Path(temp)/'refused')
                self.assertFalse((Path(temp)/'refused').exists())
            for receipt_pin,binary_pin in (('bad',pin),('d'*64,'bad'),('d'*64,stage.candidate.OLD_BINARY_SHA)):
                with self.assertRaises(ValueError):stage.DbCandidate(ROOT,directory,receipt_pin,binary_pin)

    def test_wrapper_admission_precedes_common_stage_and_late_change_refuses(self):
        for late in (False,True):
            with self.subTest(late=late),tempfile.TemporaryDirectory() as temp:
                output=Path(temp)/'out';events=[];scope=mock.Mock()
                scope.admission={'admitted':True};scope.verify.return_value={'admitted':not late}
                args=SimpleNamespace(source_root=ROOT,output=output,expected_commit='b'*40,db_candidate_stage=Path(temp)/'candidate',
                                     expected_db_receipt_sha256='c'*64,expected_db_binary_sha256=NEW_SHA)
                def admitted(*args):events.append('admitted');return scope
                def common(args,**kwargs):
                    self.assertIs(kwargs['db_candidate'],scope);events.append('common-owned-teardown-complete')
                    output.mkdir();return {'passed':True,'private_files_removed':True,'owned_service_cleanup_complete':True}
                with mock.patch.object(stage.activation.prior,'require_hosted'),\
                     mock.patch.object(stage,'committed_runtime_inputs',return_value={'source':'pin'}),\
                     mock.patch.object(stage,'DbCandidate',side_effect=admitted),\
                     mock.patch.object(stage.activation,'run',side_effect=common):
                    value=stage.run(args)
                self.assertEqual(events,['admitted','common-owned-teardown-complete'])
                self.assertEqual(value['passed'],not late);self.assertEqual(value['new_candidate_and_readiness_inputs_unchanged'],not late)
                self.assertTrue(value['private_files_removed']);self.assertTrue(value['owned_service_cleanup_complete'])
                self.assertEqual(json.loads((output/'receipt.json').read_text()),value)

    def test_common_stage_new_candidate_generation_profile_and_late_cleanup(self):
        @dataclass(frozen=True)
        class Prerequisite:fresh_authentication_required:bool=True
        a=stage.activation
        for late in (False,True):
            with self.subTest(late=late),tempfile.TemporaryDirectory() as temp:
                directory=Path(temp);events=[];processes=[]
                auth_stage=directory/'auth';auth_stage.mkdir();(auth_stage/a.service.candidate.BINARY).write_bytes(b'auth')
                args=SimpleNamespace(source_root=ROOT,output=directory/'out',expected_commit='b'*40,
                                     auth_candidate_stage=auth_stage,auth_success_archive=directory/'accepted-auth.zip')
                scope=mock.Mock(binary_name=stage.candidate.BINARY,binary_sha256=NEW_SHA,
                                receipt_schema=stage.DbCandidate.receipt_schema,admission={'admitted':True})
                def recover(root,out):out.mkdir();(out/scope.binary_name).write_bytes(b'new db');events.append('recover-new-db');return {'admitted':True}
                scope.recover.side_effect=recover
                class Commands:
                    def __init__(self,out):self.records=[]
                class SQL:
                    def __init__(self,records,private):self.records=records
                    def run(self,name,argv,**kwargs):events.append(name)
                    def numeric(self,name,argv,kind):return '17.0.4025.3' if kind=='version' else 30
                class Child:
                    def __init__(self,pid):self.pid=pid;self.closed=False
                    def poll(self):return 0 if self.closed else None
                class Job:
                    def __init__(self):self.handle=1
                    def assign(self,child):events.append('assign-'+str(child.pid))
                    def stop(self,child):events.append('stop-'+str(child.pid));child.closed=True;self.handle=None;return True
                def popen(argv,**kwargs):
                    child=Child(10 if not processes else 20);processes.append(child)
                    if child.pid==20:
                        config=(Path(kwargs['cwd'])/'data/server/db/servers.cfg').read_text()
                        self.assertIn('UseFakeAuth 0\n',config);self.assertIn('DefaultAccessLevel 0\n',config)
                        self.assertNotIn('Version',config);self.assertEqual(argv[-2:],['-start','0'])
                        kwargs['stdout'].write(b'SQL server 17 connected\nDbServer Ready.\n');kwargs['stdout'].flush()
                    return child
                def schema(root,out):
                    (out/'data/server/db').mkdir(parents=True);(out/'data/server/db/servers.cfg').write_text('accepted default')
                    return {'files':{},'source_commit':'s','data_commit':'d'}
                actual_sha=a.prior.sha
                def sha(path):return a.service.BINARY_SHA if path.name=='AuthServer.exe' else NEW_SHA if path.name=='DbServer.exe' else actual_sha(path)
                def snapshot(child,path,previous=None,expected_binary_sha256=None):
                    self.assertEqual(expected_binary_sha256,NEW_SHA if child.pid==20 else None)
                    if child.pid==20:events.append('new-db-generation-observer')
                    return {'pid':child.pid,'exists':True,'started_utc_ticks':639277996886036331+child.pid}
                def channel(*args):
                    if late:raise ValueError('test_new_candidate_late_registration_refusal')
                    return {'loopback_pair_verified':True}
                scalars=iter([0,1,99])
                with ExitStack() as stack:
                    for owner,name,value in ((a.prior,'require_hosted',{}),(a,'authenticated_handoff_prerequisite',Prerequisite()),
                        (a.service.candidate,'admit',{}),(a.service,'tools',(Path('LocalDB'),Path('SQLCMD'),{})),
                        (a.auth_readiness,'observe',{'healthy':True}),(a.login,'reserve_ports',([21000,21001,21002],[])),
                        (a.db_startup_diagnostic,'observe_sql',{'user_tables':0}),(a.db_startup_diagnostic,'observe_process',{'thread_count':64})):
                        stack.enter_context(mock.patch.object(owner,name,return_value=value))
                    for owner,name,value in ((a,'recover_schema',schema),(a.prior,'Commands',Commands),(a,'RedactedCommands',SQL),
                        (a.login,'OwnedJob',Job),(a.subprocess,'Popen',popen),(a.prior,'sha',sha),(a,'service_process_snapshot',snapshot),
                        (a,'owned_channel',channel)):
                        stack.enter_context(mock.patch.object(owner,name,side_effect=value))
                    stack.enter_context(mock.patch.dict(os.environ,{'RUNNER_TEMP':temp}))
                    stack.enter_context(mock.patch.object(a.prior,'capture',side_effect=lambda argv:'b'*40 if argv[-1]=='HEAD' else ''))
                    stack.enter_context(mock.patch.object(a,'recover_db',side_effect=AssertionError('old DB recovery must not run')))
                    stack.enter_context(mock.patch.object(a,'firewall',side_effect=lambda runner,name,binary,direction,add:events.append(('add-' if add else 'remove-')+direction)))
                    stack.enter_context(mock.patch.object(a.login,'inspect_listeners',side_effect=lambda pid:set() if next(p for p in processes if p.pid==pid).closed else {21000,21001,21002}))
                    stack.enter_context(mock.patch.object(a,'scalar',side_effect=lambda *args:next(scalars)))
                    stack.enter_context(mock.patch.object(a,'game_listener',return_value={'owner_pid':20}))
                    stack.enter_context(mock.patch.object(a.login,'owned_process_snapshot',side_effect=lambda pid:{'pid':30,'exists':True}))
                    modal=stack.enter_context(mock.patch.object(a.db_modal_diagnostic,'observe',side_effect=AssertionError('old-PE modal classifier must not run')))
                    value=a.run(args,db_candidate=scope)
                self.assertEqual(value['passed'],not late);self.assertEqual(value['schema'],scope.receipt_schema)
                self.assertFalse(value['client_login_attempted']);self.assertFalse(value['selected_shard_play_verified'])
                self.assertFalse(value['checksum_policy_relaxed']);self.assertFalse(value['shipping_profiles_modified'])
                self.assertFalse(value['authenticated_db_map_handoff_verified']);self.assertFalse(value['accepted_runtime_replaced'])
                for key in ('owned_service_cleanup_complete','owned_firewall_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'):
                    self.assertTrue(value[key],key)
                self.assertLess(events.index('recover-new-db'),events.index('localdb-create'))
                self.assertLess(events.index('stop-20'),events.index('stop-10'))
                self.assertGreaterEqual(events.count('new-db-generation-observer'),2)
                modal.assert_not_called()
                if late:
                    self.assertTrue(value['owned_db_startup_diagnostic']['complete'])
                    self.assertEqual(value['owned_db_modal_diagnostic']['not_run'],'modal_policy_bound_to_prior_checksum_only_pe')

    def test_new_runtime_sources_require_real_tracked_commit_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            for name in stage.RUNTIME_INPUTS:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()
            git('init','-q');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
            git('add','.');git('commit','-qm','Own readiness fixture');commit=git('rev-parse','HEAD')
            with self.assertRaises(ValueError):stage.committed_runtime_inputs(root,commit)
            with mock.patch.object(stage,'__file__',str(root/stage.RUNTIME_INPUTS[0])),\
                 mock.patch.object(stage.activation,'__file__',str(root/stage.RUNTIME_INPUTS[2])):
                self.assertEqual(len(stage.committed_runtime_inputs(root,commit)),3)
                path=root/stage.RUNTIME_INPUTS[0];raw=path.read_bytes();path.write_bytes(raw+b'\n')
                with self.assertRaises(ValueError):stage.committed_runtime_inputs(root,commit)
                path.write_bytes(raw);git('rm','--cached','-q','--',stage.RUNTIME_INPUTS[0]);git('commit','-qm','Untrack new wrapper')
                with self.assertRaises(ValueError):stage.committed_runtime_inputs(root,git('rev-parse','HEAD'))

    def test_local_refusal_precedes_artifact_admission_or_stage_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            args=SimpleNamespace(source_root=ROOT,output=Path(temp)/'out',expected_commit='b'*40)
            with mock.patch.dict(os.environ,{'RUNNER_ENVIRONMENT':'local-test'}),\
                 mock.patch.object(stage,'DbCandidate') as candidate,self.assertRaises(ValueError):stage.run(args)
            candidate.assert_not_called();self.assertFalse(args.output.exists())

    def test_raw_first_generated_metadata_view_and_mutation_refusals(self):
        # Reuse only the new composition suite's nonexecuted PE/build shell
        # constructor. No C fixture, compiler, service or old suite is run.
        import test_db_threadname_candidate as fixture
        fixture.CompositionTests.setUpClass()
        try:
            with tempfile.TemporaryDirectory() as temp:
                case=fixture.CompositionTests();directory=Path(temp)
                output,proof,original,composed=case.compile_fixture(directory)
                receipt=output/'receipt.json';binary=output/stage.candidate.BINARY
                binary_pin=stage.candidate.digest(binary.read_bytes())
                def repin(name):
                    path=output/name;proof['files'][name]={'bytes':path.stat().st_size,'sha256':stage.candidate.digest(path.read_bytes())}
                    receipt.write_text(json.dumps(proof,indent=2)+'\n')
                    return stage.candidate.digest(receipt.read_bytes())
                for name in stage.GENERATED_TEXT:
                    path=output/name;lf=path.read_bytes().replace(b'\r\n',b'\n');path.write_bytes(lf.replace(b'\n',b'\r\n'));repin(name)
                receipt_pin=stage.candidate.digest(receipt.read_bytes())
                with mock.patch.object(stage.candidate,'expected_source_map',return_value=(original,composed)):
                    snapshots={p.name:p.read_bytes() for p in output.iterdir()}
                    admitted=stage.admit_candidate(ROOT,output,receipt_pin,binary_pin)
                    self.assertEqual({p.name:p.read_bytes() for p in output.iterdir()},snapshots)
                    self.assertEqual(admitted['receipt_sha256'],receipt_pin)
                    metadata=admitted['generated_metadata_admission']
                    if os.linesep=='\n':
                        self.assertEqual(metadata['mode'],'native_generated_metadata_view')
                        self.assertEqual(set(metadata['changed_files']),stage.GENERATED_TEXT)
                        self.assertNotEqual(metadata['view_receipt_sha256'],receipt_pin)
                        self.assertTrue(metadata['temporary_view_removed'])
                    self.assertFalse(metadata['original_build_receipt_replaced'])
                    self.assertEqual(metadata['original_pe_sha256'],binary_pin)
                    for name in ('candidate-manifest.json',stage.candidate.BINARY,'source-file-map.json'):
                        path=output/name;path.write_bytes(snapshots[name]+b'changed')
                        with self.subTest(control='raw_hash',name=name),self.assertRaises(ValueError):stage.admit_candidate(ROOT,output,receipt_pin,binary_pin)
                        path.write_bytes(snapshots[name])
                    extra=output/'extra.json';extra.write_bytes(b'{}')
                    with self.assertRaises(ValueError):stage.admit_candidate(ROOT,output,receipt_pin,binary_pin)
                    extra.unlink()
                    for name,body in (('candidate-manifest.json',snapshots['candidate-manifest.json'].replace(b'Win32',b'Win64')+b'changed'),
                            ('checksum-failclosed.patch',snapshots['checksum-failclosed.patch']+b'changed'),
                            ('source-file-map.json',snapshots['source-file-map.json'].replace(b'"unchanged_after_build": true',b'"unchanged_after_build": false'))):
                        path=output/name;path.write_bytes(body);changed_pin=repin(name)
                        with self.subTest(control='rehashed_content',name=name),self.assertRaises(ValueError):stage.admit_candidate(ROOT,output,changed_pin,binary_pin)
                        path.write_bytes(snapshots[name]);repin(name)
                    for raw in (b'a\r\nb\nc\r\n',b'a\rb\n'):
                        with self.assertRaises(ValueError):stage.native_generated_text(raw)
                        path=output/'candidate-manifest.json';path.write_bytes(raw);changed_pin=repin(path.name)
                        with self.assertRaises(ValueError):stage.admit_candidate(ROOT,output,changed_pin,binary_pin)
                        path.write_bytes(snapshots[path.name]);repin(path.name)
                    binary.write_bytes(snapshots[stage.candidate.BINARY]+b'changed PE')
                    changed_pin=repin(stage.candidate.BINARY);changed_binary_pin=stage.candidate.digest(binary.read_bytes())
                    with self.assertRaises(ValueError):stage.admit_candidate(ROOT,output,changed_pin,changed_binary_pin)
        finally:fixture.CompositionTests.tearDownClass()


if __name__=='__main__':unittest.main(verbosity=2)

"""New candidate/selected-scope composition only; no compiler, SQL or network."""
from contextlib import ExitStack
from dataclasses import dataclass, FrozenInstanceError
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import hosted_db_threadname_selected_play as stage

ROOT=Path(__file__).resolve().parents[4]
NEW_SHA='a'*64
RECEIPT_SHA='c'*64


def candidate():
    value=object.__new__(stage.readiness.DbCandidate)
    value.binary_sha256=NEW_SHA;value.receipt_pin=RECEIPT_SHA
    value.admission={'receipt_sha256':RECEIPT_SHA,'admitted':True}
    return value


class CandidateSelectedTests(unittest.TestCase):
    def test_only_explicit_typed_exact_candidate_binding_is_admitted(self):
        a=stage.activation;db=candidate();token=a.DbCandidateGeneration(NEW_SHA,RECEIPT_SHA)
        scope=stage.selected.SelectedScope(Path('retained'),db_candidate_generation=token)
        self.assertIs(a.admit_selected_candidate(scope,db),token)
        with self.assertRaises(FrozenInstanceError):token.binary_sha256='d'*64
        for binary,receipt in (('bad',RECEIPT_SHA),(NEW_SHA,False),(a.DB_BINARY_SHA,RECEIPT_SHA)):
            with self.assertRaises(ValueError):a.DbCandidateGeneration(binary,receipt)
        with self.assertRaises(ValueError):stage.selected.SelectedScope(Path('retained'),db_candidate_generation={'binary_sha256':NEW_SHA})
        class Unqualified(stage.selected.SelectedScope):pass
        for scope in (stage.selected.SelectedScope(Path('retained')),Unqualified(Path('retained'),db_candidate_generation=token),
                stage.selected.SelectedScope(Path('retained'),db_candidate_generation=a.DbCandidateGeneration('d'*64,RECEIPT_SHA)),
                stage.selected.SelectedScope(Path('retained'),db_candidate_generation=a.DbCandidateGeneration(NEW_SHA,'d'*64))):
            with self.subTest(scope=type(scope).__name__),self.assertRaisesRegex(ValueError,'unqualified'):
                a.admit_selected_candidate(scope,db)
        with self.assertRaisesRegex(ValueError,'unqualified'):
            a.admit_selected_candidate(stage.selected.SelectedScope(Path('retained'),db_candidate_generation=token),SimpleNamespace(binary_sha256=NEW_SHA,admission=db.admission))

    def test_real_shaped_selected_observers_use_new_db_hash_and_refuse_reuse(self):
        a=stage.activation;s=stage.selected
        for changed in ('none','start','path','name','binary','sql'):
            with self.subTest(changed=changed):
                scope=s.SelectedScope(Path('retained'),db_candidate_generation=a.DbCandidateGeneration(NEW_SHA,RECEIPT_SHA))
                scope.binary=Path('probe');proof={'selected_probe_build':{'binary':{'sha256':'probe'}}}
                auth,db=mock.Mock(pid=10),mock.Mock(pid=20);auth.poll.return_value=db.poll.return_value=None
                images={10:Path('D:/owned/AuthServer.exe'),20:Path('D:/owned/DbServer.exe')}
                raw={pid:dict(pid=pid,exists=True,name='AuthServer' if pid==10 else 'DbServer',
                    started_utc_ticks=639277996886036331+pid,executable_path=str(path)) for pid,path in images.items()}
                starts={pid:a.admit_service_process(raw[pid],pid,images[pid]) for pid in images}
                done=False;hashes=[]
                def capture(argv):
                    pid=10 if 'Get-Process -Id 10 ' in argv[-1] else 20
                    value=dict(raw[pid])
                    if done and pid==20:
                        if changed=='start':value['started_utc_ticks']+=1
                        if changed=='path':value['executable_path']='D:/other/DbServer.exe'
                        if changed=='name':value['name']='sqlservr'
                    return json.dumps(value)
                def sha(path):
                    hashes.append(path.name)
                    return a.service.BINARY_SHA if path==images[10] else ('e'*64 if done and changed=='binary' else NEW_SHA)
                def probe(*args):
                    nonlocal done
                    done=True;return {'passed':True}
                baseline={'pid':30,'exists':True}
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(a.prior,'capture',side_effect=capture))
                    stack.enter_context(mock.patch.object(a.prior,'sha',side_effect=sha))
                    stack.enter_context(mock.patch.object(a.login,'owned_process_snapshot',side_effect=lambda pid:dict(baseline,pid=31) if done and changed=='sql' else baseline))
                    stack.enter_context(mock.patch.object(a,'owned_channel',return_value={'loopback_pair_verified':True}))
                    stack.enter_context(mock.patch.object(a,'game_listener',return_value={'owner_pid':20}))
                    stack.enter_context(mock.patch.object(a.login,'inspect_listeners',return_value={21000,21001,21002}))
                    stack.enter_context(mock.patch.object(a,'scalar',return_value=1))
                    stack.enter_context(mock.patch.object(a.login,'probe_identity',return_value={'sha256':'probe'}))
                    run=stack.enter_context(mock.patch.object(s,'run_probe',side_effect=probe))
                    args=(Path('private'),proof,[],[21000,21001,21002],auth,db,images[10],images[20],starts[10],starts[20],30,baseline)
                    if changed=='none':self.assertTrue(scope.exercise(*args))
                    else:
                        with self.assertRaises(ValueError):scope.exercise(*args)
                    run.assert_called_once()
                self.assertTrue(proof['client_login_attempted']);self.assertIn('AuthServer.exe',hashes);self.assertIn('DbServer.exe',hashes)

    def test_common_selected_candidate_transition_and_late_failure_cleanup(self):
        @dataclass(frozen=True)
        class Prerequisite:fresh_authentication_required:bool=True
        a=stage.activation;s=stage.selected
        for outcome in ('success','probe_refusal','late_generation','unbound','without_candidate'):
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory() as temp:
                directory=Path(temp).resolve();events=[];processes=[]
                auth_stage=directory/'auth';auth_stage.mkdir();(auth_stage/a.service.candidate.BINARY).write_bytes(b'auth')
                args=SimpleNamespace(source_root=ROOT,output=directory/'out',expected_commit='b'*40,
                    auth_candidate_stage=auth_stage,auth_success_archive=directory/'accepted-auth.zip')
                db=candidate();token=a.DbCandidateGeneration(NEW_SHA,RECEIPT_SHA)
                scope=s.SelectedScope(directory/'retained',db_candidate_generation=None if outcome=='unbound' else token)
                scope.binary=directory/'probe'
                def recover(root,out):out.mkdir();(out/db.binary_name).write_bytes(b'new db');events.append('recover-new-db');return db.admission
                db.recover=recover
                def prepare(root,temporary,output,runner,proof,sql,sql_runner):
                    events.append('prepare-new-selected');proof['selected_probe_build']={'binary':{'sha256':'probe'}}
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
                    def assign(self,child):pass
                    def stop(self,child):events.append('stop-'+str(child.pid));child.closed=True;self.handle=None;return True
                def popen(argv,**kwargs):
                    child=Child(10 if not processes else 20);processes.append(child)
                    if child.pid==20:
                        config=(Path(kwargs['cwd'])/'data/server/db/servers.cfg').read_text()
                        self.assertIn('UseFakeAuth 0\n',config);self.assertIn('DefaultAccessLevel 0\n',config)
                        self.assertNotIn('Version',config);self.assertEqual(argv[-2:],['-start','0'])
                        kwargs['stdout'].write(b'DbServer Ready.\n');kwargs['stdout'].flush()
                    return child
                def schema(root,out):
                    (out/'data/server/db').mkdir(parents=True);return {'files':{},'source_commit':'s','data_commit':'d'}
                actual_sha=a.prior.sha
                def sha(path):return a.service.BINARY_SHA if path.name=='AuthServer.exe' else NEW_SHA if path.name=='DbServer.exe' else actual_sha(path)
                probe_done=False
                def snapshot(child,path,previous=None,expected_binary_sha256=None):
                    self.assertEqual(expected_binary_sha256,NEW_SHA if child.pid==20 else None)
                    if child.pid==20 and probe_done and outcome=='late_generation':raise ValueError('shard_service_process_generation_changed')
                    return {'pid':child.pid,'exists':True}
                def probe(*args):
                    nonlocal probe_done
                    probe_done=True;events.append('selected-probe')
                    if outcome=='probe_refusal':raise ValueError('selected_private_probe_failed')
                    return {'passed':True,'live_grant_retained_then_wiped':True,'db_login_attempted':False}
                def scalar(sql,query,temporary):
                    if '.sys.tables' in query:return 99
                    if 'user_data' in query:return 1
                    return int(len(processes)==2)
                with ExitStack() as stack:
                    for owner,name,value in ((a.prior,'require_hosted',{}),(a,'authenticated_handoff_prerequisite',Prerequisite()),
                        (a.service.candidate,'admit',{}),(a.service,'tools',(Path('LocalDB'),Path('SQLCMD'),{})),
                        (a.auth_readiness,'observe',{'healthy':True}),(a.login,'reserve_ports',([21000,21001,21002],[])),
                        (a.db_startup_diagnostic,'observe_sql',{}),(a.db_startup_diagnostic,'observe_process',{}),
                        (a,'owned_channel',{'loopback_pair_verified':True}),(a,'game_listener',{'owner_pid':20}),
                        (a.login,'owned_process_snapshot',{'pid':30,'exists':True}),(a.login,'probe_identity',{'sha256':'probe'})):
                        stack.enter_context(mock.patch.object(owner,name,return_value=value))
                    for owner,name,value in ((a,'recover_schema',schema),(a.prior,'Commands',Commands),(a,'RedactedCommands',SQL),
                        (a.login,'OwnedJob',Job),(a.subprocess,'Popen',popen),(a.prior,'sha',sha),(a,'service_process_snapshot',snapshot),
                        (a,'scalar',scalar),(s,'run_probe',probe),(scope,'prepare',prepare)):
                        stack.enter_context(mock.patch.object(owner,name,side_effect=value))
                    stack.enter_context(mock.patch.dict(os.environ,{'RUNNER_TEMP':str(directory)}))
                    stack.enter_context(mock.patch.object(a.prior,'capture',side_effect=lambda argv:'b'*40 if argv[-1]=='HEAD' else ''))
                    old=stack.enter_context(mock.patch.object(a,'recover_db',side_effect=AssertionError('old DB recovery forbidden')))
                    stack.enter_context(mock.patch.object(a,'firewall',side_effect=lambda runner,name,binary,direction,add:events.append(('add-' if add else 'remove-')+direction)))
                    stack.enter_context(mock.patch.object(a.login,'inspect_listeners',side_effect=lambda pid:set() if next(p for p in processes if p.pid==pid).closed else {21000,21001,21002}))
                    modal=stack.enter_context(mock.patch.object(a.db_modal_diagnostic,'observe',side_effect=AssertionError('old PE policy forbidden')))
                    value=a.run(args,selected_scope=scope,db_candidate=None if outcome=='without_candidate' else db)
                old.assert_not_called();modal.assert_not_called()
                self.assertEqual(value['passed'],outcome=='success')
                self.assertEqual(value['selected_shard_play_verified'],outcome=='success')
                for key in ('owned_service_cleanup_complete','owned_firewall_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'):
                    self.assertTrue(value[key],key)
                for key in ('auth_only_login_repeated','authenticated_db_map_handoff_verified','checksum_policy_relaxed','nondevelopment_version_admitted','checksum_reference_installed','shipping_profiles_modified'):
                    self.assertFalse(value[key],key)
                if outcome in ('unbound','without_candidate'):
                    self.assertFalse(processes);self.assertNotIn('localdb-create',events);self.assertNotIn('prepare-new-selected',events)
                else:
                    self.assertEqual(value['schema'],'coh-owned-mssql-db-threadname-selected-shard-play-v1')
                    self.assertEqual(value['selected_db_candidate_generation'],{'binary_sha256':NEW_SHA,'build_receipt_sha256':RECEIPT_SHA})
                    self.assertTrue(value['client_login_attempted']);self.assertFalse(value['accepted_runtime_replaced'])
                    self.assertLess(events.index('prepare-new-selected'),events.index('selected-probe'))
                    self.assertLess(events.index('stop-20'),events.index('stop-10'))

    def test_wrapper_admits_before_scope_and_rechecks_after_owned_teardown(self):
        for changed in ('none','candidate','source'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as temp:
                output=Path(temp)/'out';events=[];db=candidate()
                db.verify=lambda:dict(db.admission,changed=True) if changed=='candidate' else db.admission
                args=SimpleNamespace(source_root=ROOT,output=output,expected_commit='b'*40,
                    db_candidate_stage=Path(temp)/'stage',expected_db_receipt_sha256=RECEIPT_SHA,expected_db_binary_sha256=NEW_SHA,
                    retained_intact_stage=Path(temp)/'retained',send_cap=7)
                def admitted(*args):events.append('admitted');return db
                def common(args,selected_scope,db_candidate):
                    self.assertIs(db_candidate,db);self.assertEqual(selected_scope.send_cap,7)
                    stage.activation.admit_selected_candidate(selected_scope,db)
                    events.append('owned-teardown-complete');output.mkdir();return {'passed':True,'private_files_removed':True}
                with mock.patch.object(stage.activation.prior,'require_hosted'),\
                     mock.patch.object(stage,'committed_inputs',side_effect=[{'source':'first'},{'source':'changed' if changed=='source' else 'first'}]),\
                     mock.patch.object(stage.readiness,'DbCandidate',side_effect=admitted) as constructor,\
                     mock.patch.object(stage.activation,'admit_selected_candidate',return_value=stage.activation.DbCandidateGeneration(NEW_SHA,RECEIPT_SHA)),\
                     mock.patch.object(stage.activation,'run',side_effect=common):
                    value=stage.run(args)
                constructor.assert_called_once();self.assertEqual(events,['admitted','owned-teardown-complete'])
                self.assertEqual(value['passed'],changed=='none');self.assertEqual(value['selected_candidate_and_source_inputs_unchanged'],changed=='none')
                self.assertTrue(value['private_files_removed']);self.assertEqual(json.loads((output/'receipt.json').read_text()),value)

    def test_seven_runtime_inputs_require_exact_tracked_checkout_ownership(self):
        names=stage.readiness.RUNTIME_INPUTS+stage.OWN_INPUTS
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()
            git('init','-q');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
            git('add','.');git('commit','-qm','Own selected fixture');commit=git('rev-parse','HEAD')
            with self.assertRaises(ValueError):stage.committed_inputs(root,commit)
            with mock.patch.object(stage,'__file__',str(root/stage.OWN_INPUTS[0])),\
                 mock.patch.object(stage.selected,'__file__',str(root/stage.OWN_INPUTS[2])),\
                 mock.patch.object(stage.readiness,'__file__',str(root/stage.readiness.RUNTIME_INPUTS[0])),\
                 mock.patch.object(stage.activation,'__file__',str(root/stage.readiness.RUNTIME_INPUTS[2])):
                self.assertEqual(len(stage.committed_inputs(root,commit)),7)
                for name in names:
                    path=root/name;raw=path.read_bytes();path.write_bytes(raw+b'\n')
                    with self.subTest(name=name),self.assertRaises(ValueError):stage.committed_inputs(root,commit)
                    path.write_bytes(raw)
                git('rm','--cached','-q','--',stage.OWN_INPUTS[0]);git('commit','-qm','Untrack selected wrapper')
                with self.assertRaises(ValueError):stage.committed_inputs(root,git('rev-parse','HEAD'))

    def test_local_refusal_precedes_new_source_or_candidate_admission(self):
        with tempfile.TemporaryDirectory() as temp:
            args=SimpleNamespace(source_root=ROOT,output=Path(temp)/'out',expected_commit='b'*40)
            with mock.patch.dict(os.environ,{'RUNNER_ENVIRONMENT':'local-test'}),\
                 mock.patch.object(stage,'committed_inputs') as source,\
                 mock.patch.object(stage.readiness,'DbCandidate') as db,self.assertRaises(ValueError):stage.run(args)
            source.assert_not_called();db.assert_not_called();self.assertFalse(args.output.exists())


if __name__=='__main__':unittest.main(verbosity=2)

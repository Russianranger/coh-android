"""New driver source-admission controls only; no compiler, registry or network."""
import copy
import ast
from contextlib import ExitStack
import json
from pathlib import Path
import re
import tempfile
import subprocess
import struct
from types import SimpleNamespace
import unittest
from unittest import mock

import hosted_auth_db_development as stage

ROOT=Path(__file__).resolve().parents[4]


def resume_positive():
    value={name:True for name in stage.RESUME_FLAGS}
    return dict(value,schema='coh-owned-suspended-primary-thread-v1',snapshot_passes=2,
        snapshot_entries_examined=2,secondary_close_failures=0,failure='NONE')


def new_job():
    def initialize(job):job.handle=123;job.kernel=mock.Mock()
    with mock.patch.object(stage.login.OwnedJob,'__init__',initialize):return stage.DevelopmentJob()


def positive(preflight=False):
    value={k:0 for k in stage.INTEGER_BOUNDS|{k:1 for k in stage.ONE_FLAGS|stage.ZERO_FLAGS}}
    value.update({k:True for k in stage.TRUE_FLAGS});value.update({k:False for k in stage.FALSE_FLAGS})
    value.update(schema='coh-auth-db-development-'+('platform-preflight' if preflight else 'list-probe')+'-v1',
        probe_stage=10 if preflight else 9,udp_cleanup_complete=1,elapsed_ms=500)
    if not preflight:
        value.update({k:1 for k in stage.ONE_FLAGS})
        value.update(phase=3,auth_phase=7,db_phase=4,auth_final_phase=8,db_final_phase=11,
            slots=12,base_slots=12,auth_frames=4,db_login_requests=1,db_player_lists=1,udp_created=1,udp_closed=1)
    return value


def synthetic_pe():
    raw=bytearray(4096);raw[:2]=b'MZ';struct.pack_into('<I',raw,60,128);raw[128:132]=b'PE\0\0'
    struct.pack_into('<HH',raw,132,0x8664,1);struct.pack_into('<H',raw,148,240)
    op=152;struct.pack_into('<H',raw,op,0x20b);struct.pack_into('<I',raw,op+56,0x3000)
    struct.pack_into('<H',raw,op+68,3);struct.pack_into('<I',raw,op+108,16)
    struct.pack_into('<II',raw,op+120,0x1000,60)
    struct.pack_into('<IIII',raw,op+240+8,0x1000,0x1000,0xe00,0x200)
    def at(rva):return 0x200+rva-0x1000
    for i,name in enumerate(('kernel32.dll','ws2_32.dll')):
        struct.pack_into('<IIIII',raw,at(0x1000+i*20),0x1100+i*32,0,0,0x1200+i*32,0x1100+i*32)
        struct.pack_into('<QQ',raw,at(0x1100+i*32),0x1300+i*32,0)
        raw[at(0x1200+i*32):at(0x1200+i*32)+len(name)+1]=name.encode()+b'\0'
        raw[at(0x1300+i*32):at(0x1300+i*32)+7]=b'\0\0Test\0'
    return raw


class DevelopmentDriverSourceTests(unittest.TestCase):
    def test_typed_new_candidate_scope_refuses_aliases_mutual_use_and_stale_generation(self):
        generation=stage.activation.DbCandidateGeneration('a'*64,'b'*64)
        candidate=stage.readiness.DbCandidate.__new__(stage.readiness.DbCandidate)
        candidate.binary_sha256='a'*64;candidate.admission={'receipt_sha256':'b'*64}
        owner=stage.DevelopmentScope(Path('unused'),generation,provisional_development_policy=True)
        self.assertEqual(stage.activation.admit_development_candidate(owner,candidate),generation)
        for scope,db in ((SimpleNamespace(db_candidate_generation=generation),candidate),(owner,None),
                (stage.selected.SelectedScope(Path('unused'),1024),candidate)):
            with self.assertRaises(ValueError):stage.activation.admit_development_candidate(scope,db)
        for pin in ('binary_sha256','receipt_sha256'):
            if pin=='binary_sha256':candidate.binary_sha256='c'*64
            else:candidate.admission[pin]='c'*64
            with self.assertRaises(ValueError):stage.activation.admit_development_candidate(owner,candidate)
            candidate.binary_sha256='a'*64;candidate.admission={'receipt_sha256':'b'*64}
        with self.assertRaisesRegex(ValueError,'mutually_exclusive'):
            stage.activation.run(None,selected_scope=object(),development_scope=owner,db_candidate=candidate)
        for policy in (False,None,1,'true'):
            with self.assertRaises(ValueError):stage.DevelopmentScope(Path('unused'),generation,provisional_development_policy=policy)
        with self.assertRaises(ValueError):stage.activation.admit_selected_candidate(owner,candidate)

    def test_private_child_wipes_constructor_and_late_failure_paths_preserving_primary(self):
        for mode in ('job','popen','assign','timeout','native','native_and_stop','stop','close','success'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name,ExitStack() as stack:
                buffers=[];sink={};events=[]
                primary=(subprocess.TimeoutExpired('PRIVATE_CANARY',37) if mode=='timeout' else OSError('PRIVATE_CANARY'))
                real_bytearray=bytearray
                def buffer(value):
                    value=real_bytearray(value);buffers.append(value);return value
                stack.enter_context(mock.patch.object(stage,'bytearray',side_effect=buffer,create=True))
                job=mock.Mock(handle=123,empty_before_close=True)
                job.assignment_verified=False
                job.launch_state='CREATED_SUSPENDED'
                job.kernel.CloseHandle.return_value=True
                def close_unassigned():job.handle=None;return True
                job.close_unassigned.side_effect=close_unassigned
                child=mock.Mock(stdin=mock.Mock(),returncode=0 if mode in ('success','stop','close') else 1)
                child.poll.return_value=None if mode=='timeout' else child.returncode
                def assign(actual):
                    if mode=='assign':job.launch_state='ASSIGNMENT_REFUSED';raise primary
                    job.assignment_verified=True;job.launch_state='RESUMED'
                job.assign.side_effect=assign
                def stop(actual):
                    events.append('stop');self.assertIs(actual,child)
                    self.assertTrue(buffers and not any(buffers[0]))
                    if mode in ('stop','timeout','native_and_stop'):raise OSError('LATE_PRIVATE_CANARY')
                    if mode=='close':job.kernel.CloseHandle.side_effect=OSError('LATE_PRIVATE_CANARY');return True
                    job.handle=None;return job.assignment_verified
                job.stop.side_effect=stop
                def popen(argv,**kwargs):
                    if mode=='popen':raise primary
                    def communicate(input,timeout):
                        self.assertIs(input,buffers[0])
                        if mode=='timeout':raise primary
                        value=positive();value['passed']=child.returncode==0
                        kwargs['stdout'].write(json.dumps(value).encode());kwargs['stdout'].flush()
                    child.communicate.side_effect=communicate;return child
                job.popen.side_effect=popen
                stack.enter_context(mock.patch.object(stage,'DevelopmentJob',side_effect=primary if mode=='job' else lambda:job))
                stack.enter_context(mock.patch.object(stage.subprocess,'Popen',side_effect=popen))
                if mode=='success':self.assertTrue(stage.private_probe(Path('unused'),23000,Path(name),failure_observation=sink)['passed'])
                else:
                    with self.assertRaises((ValueError,OSError,subprocess.TimeoutExpired)) as error:
                        stage.private_probe(Path('unused'),23000,Path(name),failure_observation=sink)
                    if mode in ('job','popen','assign','timeout'):self.assertIs(error.exception,primary)
                    if mode=='native_and_stop':self.assertEqual(str(error.exception),'development_private_probe_refused')
                self.assertEqual(len(buffers),1);self.assertFalse(any(buffers[0]))
                self.assertNotIn('PRIVATE_CANARY',json.dumps(sink))
                if mode not in ('job','popen'):child.stdin.close.assert_called_once()
                if mode=='popen':
                    job.close_unassigned.assert_called_once()
                    self.assertTrue(sink['owned_child_job_empty_before_close'])
                if mode in ('job','assign','stop','close','timeout','native_and_stop'):self.assertFalse(sink['owned_child_cleanup_complete'])

    def test_development_jobs_require_observed_empty_descendants_before_handle_close(self):
        for mode in ('complete','deadline','query','terminate','close','root_wait'):
            with self.subTest(mode=mode):
                job=new_job();job.kernel.TerminateJobObject.return_value=mode!='terminate'
                job.kernel.CloseHandle.return_value=mode!='close'
                events=[]
                def members():
                    events.append('query')
                    if mode=='query':raise OSError('PRIVATE_CANARY')
                    return [123] if mode=='deadline' or events.count('query')==1 else []
                job.process_ids=members
                def close(handle):events.append('close');return mode!='close'
                job.kernel.CloseHandle.side_effect=close
                child=mock.Mock();child.poll.return_value=0
                child._handle=0x100000123
                with mock.patch.object(stage.subprocess,'Popen',return_value=child),mock.patch.object(stage,'_resume_primary',return_value=resume_positive()):
                    self.assertIs(job.popen(['probe']),child);job.assign(child)
                if mode=='root_wait':child.wait.side_effect=[subprocess.TimeoutExpired('unused',5),None]
                with mock.patch.object(stage.time,'monotonic',side_effect=[0,1,16]),mock.patch.object(stage.time,'sleep'):
                    if mode in ('query','root_wait'):
                        with self.assertRaises((ValueError,OSError,subprocess.TimeoutExpired)):job.stop(child)
                    else:self.assertEqual(job.stop(child),mode=='complete')
                self.assertEqual(events[-1],'close')
                self.assertEqual(job.empty_before_close,mode in ('complete','terminate','close','root_wait'))
                self.assertEqual(job.handle,123 if mode=='close' else None)
        for mode in ('empty','nonempty','query','close','query_and_close'):
            with self.subTest(pending_mode=mode):
                job=new_job();job.kernel.CloseHandle.return_value=mode!='close'
                primary=OSError('PRIVATE_CANARY')
                job.process_ids=mock.Mock(side_effect=primary if mode in ('query','query_and_close') else None,
                    return_value=[123] if mode=='nonempty' else [])
                if mode=='query_and_close':job.kernel.CloseHandle.side_effect=OSError('LATE_PRIVATE_CANARY')
                if mode in ('query','query_and_close'):
                    with self.assertRaises(OSError) as error:job.close_unassigned()
                    self.assertIs(error.exception,primary)
                else:self.assertEqual(job.close_unassigned(),mode=='empty')
                job.kernel.CloseHandle.assert_called_once_with(123)

    def test_job_assignment_success_is_one_shot_child_bound_and_required_after_root_exit(self):
        for mode in ('assigned','refused','assignment_exception','wrong_child','reassignment'):
            with self.subTest(mode=mode):
                job=new_job();job.kernel.AssignProcessToJobObject.return_value=mode!='refused'
                job.kernel.TerminateJobObject.return_value=True;job.kernel.CloseHandle.return_value=True
                if mode=='assignment_exception':job.kernel.AssignProcessToJobObject.side_effect=OSError('PRIVATE_CANARY')
                child=mock.Mock(_handle=0x100000123,pid=123);child.poll.return_value=0
                with mock.patch.object(stage.subprocess,'Popen',return_value=child),mock.patch.object(stage,'_resume_primary',return_value=resume_positive()):
                    self.assertIs(job.popen(['probe']),child)
                    if mode in ('refused','assignment_exception'):
                        with self.assertRaises((ValueError,OSError)):job.assign(child)
                    else:job.assign(child)
                if mode=='reassignment':
                    with self.assertRaisesRegex(ValueError,'consumed'):job.assign(child)
                other=mock.Mock(_handle=0x100000123,pid=123);other.poll.return_value=0
                job.process_ids=mock.Mock(return_value=[])
                actual=other if mode=='wrong_child' else child
                self.assertEqual(job.stop(actual),mode in ('assigned','reassignment'))
                if mode=='wrong_child':other.wait.assert_not_called();other.kill.assert_not_called()
                if mode in ('refused','assignment_exception'):self.assertFalse(job.scope_closed_verified)
                self.assertTrue(job.empty_before_close);self.assertIsNone(job.handle)
                self.assertEqual(job.assignment_verified,mode not in ('refused','assignment_exception'))

    def test_suspended_launch_before_assignment_and_resume_is_one_use_on_every_refusal(self):
        for mode in ('success','spawn','assign','assign_and_terminate','resume_refused','resume_exception','resume_close'):
            with self.subTest(mode=mode):
                job=new_job();events=[];child=mock.Mock(_handle=0x100000123,pid=123);child.poll.return_value=0
                primary=OSError('PRIVATE_CANARY')
                def popen(*args,**kwargs):
                    events.append('spawn');self.assertEqual(kwargs['creationflags'],4)
                    if mode=='spawn':raise primary
                    return child
                def assign(*args):
                    events.append('assign')
                    if mode.startswith('assign'):return False
                    return True
                def resume(actual):
                    events.append('resume');self.assertIs(actual,child);self.assertEqual(events,['spawn','assign','resume'])
                    if mode=='resume_exception':raise primary
                    value=resume_positive()
                    if mode=='resume_refused':value.update(passed=False,failure='PROCESS_IDENTITY')
                    if mode=='resume_close':value.update(passed=False,cleanup_verified=False,failure='HANDLE_CLOSE')
                    return value
                job.kernel.AssignProcessToJobObject.side_effect=assign;job.process_ids=mock.Mock(return_value=[])
                with mock.patch.object(stage.subprocess,'Popen',side_effect=popen),mock.patch.object(stage,'_resume_primary',side_effect=resume) as resumer:
                    if mode=='spawn':
                        with self.assertRaises(OSError) as error:job.popen(['probe'])
                        self.assertIs(error.exception,primary)
                        self.assertTrue(job.close_unassigned());self.assertTrue(job.scope_closed_verified)
                    else:
                        self.assertIs(job.popen(['probe']),child)
                        if mode=='success':job.assign(child)
                        else:
                            with self.assertRaises((ValueError,OSError)):job.assign(child)
                        self.assertEqual(resumer.call_count,0 if mode.startswith('assign') else 1)
                        with self.assertRaises(ValueError):job.assign(child)
                        with self.assertRaises(ValueError):job.popen(['probe'])
                        self.assertEqual(resumer.call_count,0 if mode.startswith('assign') else 1)
                        # Both query and terminate failures still reap a known
                        # direct child that never entered the job.
                        if mode=='assign':job.process_ids.side_effect=primary
                        if mode=='assign_and_terminate':job.kernel.TerminateJobObject.side_effect=primary
                        if mode.startswith('assign'):
                            with self.assertRaises(OSError) as error:job.stop(child)
                            self.assertIs(error.exception,primary);child.kill.assert_called_once();child.wait.assert_called_once()
                        else:self.assertTrue(job.stop(child))
                    self.assertFalse(any('PRIVATE_CANARY' in str(value) for value in stage.job_projection(job).values()))
        # Every direct driver Popen is centralized; service launches select it
        # only for the new typed scope, leaving accepted paths on Popen.
        tree=ast.parse((stage.HERE/'hosted_auth_db_development.py').read_bytes())
        direct=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and isinstance(node.func.value,ast.Name) and node.func.value.id=='subprocess' and node.func.attr=='Popen']
        self.assertEqual(len(direct),1)
        self.assertTrue(any(keyword.arg=='creationflags' and ast.literal_eval(keyword.value)==4 for keyword in direct[0].keywords))
        activation=(stage.HERE/'hosted_db_shard_activation.py').read_text()
        self.assertIn('auth_launch=subprocess.Popen if development_scope is None else job.popen',activation)
        self.assertIn('db_launch=subprocess.Popen if development_scope is None else db_job.popen',activation)

    def test_resume_projection_refuses_extra_identity_types_and_incomplete_cleanup(self):
        source=ast.parse((stage.HERE/'windows_suspended_thread.py').read_bytes())
        declared={node.targets[0].id:node.value for node in source.body if isinstance(node,ast.Assign)
            and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)}
        self.assertEqual(ast.literal_eval(declared['TRUE_FIELDS'].args[0]),stage.RESUME_FLAGS)
        self.assertEqual(ast.literal_eval(declared['_FAILURES'].args[0])|{'NONE'},stage.RESUME_FAILURES)
        self.assertEqual(stage.selected.prior.sha(stage.HERE/'windows_suspended_thread.py'),stage.SUSPENDED_HELPER_SHA)
        original=resume_positive();self.assertEqual(stage.admit_resume(original),original)
        self.assertEqual(stage.resume_projection(original),original)
        for key,value in original.items():
            changed=dict(original);changed[key]=1 if type(value) is bool else True if type(value) is int else 'PRIVATE_CANARY'
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit_resume(changed)
            self.assertNotIn('PRIVATE_CANARY',json.dumps(stage.resume_projection(changed)))
        for key in ('pid','tid','path','creation_ticks'):
            with self.assertRaises(ValueError):stage.admit_resume(dict(original,**{key:'PRIVATE_CANARY'}))
            self.assertEqual(stage.resume_projection(dict(original,**{key:'PRIVATE_CANARY'}))['failure'],'PROJECTION_REFUSED')
        for code in stage.RESUME_FAILURES-{'NONE'}:
            value=dict(original,passed=False,failure=code);self.assertEqual(stage.resume_projection(value)['failure'],code)
            with self.assertRaises(ValueError):stage.admit_resume(value)

    def test_private_fallback_retains_failed_handle_and_primary_stop_exception(self):
        for mode in ('stop_and_close','false_close','pending_query_and_close'):
            with self.subTest(mode=mode):
                job=new_job();primary=OSError('PRIVATE_CANARY');late=OSError('LATE_PRIVATE_CANARY')
                child=mock.Mock(_handle=0x100000123,pid=123);child.poll.return_value=0
                if mode!='pending_query_and_close':
                    with mock.patch.object(stage.subprocess,'Popen',return_value=child),mock.patch.object(stage,'_resume_primary',return_value=resume_positive()):
                        self.assertIs(job.popen(['probe']),child);job.assign(child)
                job.empty_before_close=mode=='false_close'
                if mode=='false_close':
                    job.stop=mock.Mock(return_value=True);job.kernel.CloseHandle.return_value=False
                    self.assertFalse(stage.finish_private_job(job,child))
                else:
                    job.process_ids=mock.Mock(side_effect=primary);job.kernel.CloseHandle.side_effect=late
                    with self.assertRaises(OSError) as error:
                        stage.finish_private_job(job,None if mode=='pending_query_and_close' else child)
                    self.assertIs(error.exception,primary)
                self.assertEqual(job.handle,123);self.assertFalse(job.scope_closed_verified)
                self.assertFalse(stage.job_projection(job)['scope_closed_verified'])

    def test_registry_requires_new_job_completion_and_attempts_late_cleanup_after_common_failure(self):
        for mode in ('success','late_common','job_unobserved','native_unobserved','registry_refused','source_changed'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name,ExitStack() as stack:
                root=Path(name);args=SimpleNamespace(source_root=root,output=root/'output',expected_commit='a'*40,
                    allow_provisional_development_policy=True,retained_intact_stage=root/'crypto',
                    db_candidate_stage=root/'db',expected_db_receipt_sha256='b'*64,expected_db_binary_sha256='a'*64)
                registry=mock.Mock();registry.cleanup.return_value={'cleanup_verified':mode!='registry_refused'}
                scope=mock.Mock(registry=registry,_native_attempted=mode=='native_unobserved',native_observation={},
                    build_observation={},build_metadata={},preflight_observation={},preflight={},_service_jobs=[])
                scope.service_jobs_stopped.return_value=mode!='job_unobserved'
                db=mock.Mock(binary_sha256='a'*64,receipt_pin='b'*64,admission={});db.verify.return_value={}
                calls=[]
                def inputs(*unused):calls.append(1);return {'fixed':'c'*64} if mode!='source_changed' or len(calls)<3 else {'fixed':'d'*64}
                for target,name_,replacement in ((stage.selected.prior,'require_hosted',{}),(stage,'DevelopmentScope',scope),
                        (stage.readiness,'DbCandidate',db),(stage.activation,'admit_development_candidate',None)):
                    stack.enter_context(mock.patch.object(target,name_,return_value=replacement))
                stack.enter_context(mock.patch.object(stage,'committed_inputs',side_effect=inputs))
                stack.enter_context(mock.patch.dict(stage.os.environ,{'RUNNER_TEMP':str(root)}))
                receipt=dict(passed=True,owned_service_cleanup_complete=True)
                stack.enter_context(mock.patch.object(stage.activation,'run',side_effect=OSError('PRIVATE_CANARY') if mode=='late_common' else None,return_value=receipt))
                value=stage.run(args)
                self.assertEqual(value['passed'],mode=='success')
                self.assertEqual(registry.cleanup.call_args.kwargs['services_stopped'],mode not in ('late_common','job_unobserved','native_unobserved'))
                self.assertTrue(value['private_probe_build_removed']);self.assertNotIn('PRIVATE_CANARY',json.dumps(value))

    def test_source_ownership_refuses_untracked_modified_symlink_and_wrong_exact_pin(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);file=root/'source.py';file.write_bytes(b'owned bytes\n')
            subprocess.run(['git','init','-q',str(root)],check=True)
            with self.assertRaises(ValueError):stage._committed_file(root,'source.py')
            subprocess.run(['git','-C',str(root),'add','source.py'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=source-control','-c','user.email=source-control@example.invalid',
                'commit','-qm','owned input'],check=True)
            self.assertEqual(stage._committed_file(root,'source.py'),b'owned bytes\n')
            with self.assertRaises(ValueError):stage._committed_file(root,'source.py','a'*64)
            file.write_bytes(b'changed bytes\n')
            with self.assertRaises(ValueError):stage._committed_file(root,'source.py')
            file.unlink();target=root/'outside.py';target.write_bytes(b'owned bytes\n');file.symlink_to(target)
            with self.assertRaises(ValueError):stage._committed_file(root,'source.py')

    def test_transitive_local_python_graph_refuses_modified_untracked_and_wrong_executed_helper(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);base=root/(stage.PREFIX+'deployment');base.mkdir(parents=True)
            (base/'graph_main.py').write_text('import graph_child\nimport os\n')
            (base/'graph_child.py').write_text('from graph_leaf import value\n')
            (base/'graph_leaf.py').write_text('value=1\n')
            subprocess.run(['git','init','-q',str(root)],check=True)
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=source-control','-c','user.email=source-control@example.invalid',
                'commit','-qm','owned graph'],check=True)
            start=stage.PREFIX+'deployment/graph_main.py'
            expected=stage.deployment_import_inputs(root,[start]);self.assertEqual(len(expected),3)
            (base/'graph_leaf.py').write_text('value=2\n')
            with self.assertRaises(ValueError):stage.deployment_import_inputs(root,[start])
            (base/'graph_leaf.py').write_text('value=1\n');(base/'os.py').write_text('value=0\n')
            with self.assertRaises(ValueError):stage.deployment_import_inputs(root,[start])
            (base/'os.py').unlink()
            with mock.patch.dict(stage.sys.modules,{'graph_leaf':SimpleNamespace(__file__=str(root/'elsewhere/graph_leaf.py'))}):
                with self.assertRaisesRegex(ValueError,'executed_dependency'):stage.deployment_import_inputs(root,[start])
            self.assertEqual(stage.deployment_import_inputs(root,[start]),expected)

    def test_scope_observes_generation_and_exact_private_profile_even_after_primary_failure(self):
        generation=stage.activation.DbCandidateGeneration('a'*64,'b'*64)
        for mode in ('success','native','native_and_after','profile'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name,ExitStack() as stack:
                temporary=Path(name);auth=temporary/'auth/AuthServer.exe';db=temporary/'db/DbServer.exe'
                auth.parent.mkdir();(auth.parent/'etc').mkdir();(auth.parent/'etc/config.txt').write_text('auth\n')
                (db.parent/'data/server/db').mkdir(parents=True)
                config=db.parent/'data/server/db/servers.cfg';config.write_text('ClientProject owned_nonce\n')
                scope=stage.DevelopmentScope(temporary,generation,provisional_development_policy=True)
                scope._prepared=True;scope.registry=SimpleNamespace(client_project='owned_nonce')
                scope.binary=temporary/'new.exe';scope.build_metadata={'binary':{'fixed':True}}
                proof={'runtime_config_sha256':{'auth':stage.selected.prior.sha(auth.parent/'etc/config.txt'),
                    'db':stage.selected.prior.sha(config)}}
                if mode=='profile':config.write_text('ClientProject replaced_nonce\n')
                primary=OSError('PRIVATE_CANARY');snapshots=[]
                def snapshot(child,path,previous,**kwargs):
                    snapshots.append(path.name)
                    if mode=='native_and_after' and len(snapshots)>2:raise ValueError('after_observer_refused')
                    return {'fixed':path.name}
                for target,name_,replacement in ((stage.activation,'service_process_snapshot',snapshot),
                        (stage.login,'owned_process_snapshot',lambda pid:{'sql':True}),
                        (stage.activation,'owned_channel',lambda *args:{'owned':True}),
                        (stage.activation,'game_listener',lambda *args:{'owned':True}),
                        (stage.login,'inspect_listeners',lambda pid:{23000,23001,23002}),
                        (stage.activation,'scalar',lambda *args:1),
                        (stage.selected,'require_group_membership',lambda *args:None),
                        (stage,'probe_identity',lambda *args:{'fixed':True})):
                    stack.enter_context(mock.patch.object(target,name_,side_effect=replacement))
                probe=stack.enter_context(mock.patch.object(stage,'private_probe',side_effect=primary if mode in ('native','native_and_after') else None,return_value=positive()))
                if mode=='success':self.assertTrue(scope.exercise(temporary,proof,[],[23000,23001,23002],
                    SimpleNamespace(pid=10),SimpleNamespace(pid=11),auth,db,{}, {},12,{'sql':True}))
                else:
                    with self.assertRaises((ValueError,OSError)) as error:
                        scope.exercise(temporary,proof,[],[23000,23001,23002],SimpleNamespace(pid=10),SimpleNamespace(pid=11),auth,db,{}, {},12,{'sql':True})
                    if mode in ('native','native_and_after'):self.assertIs(error.exception,primary)
                self.assertEqual(probe.call_count,0 if mode=='profile' else 1)
                if mode!='profile':self.assertIn('development_runtime_after_probe_verified',proof)
                with self.assertRaisesRegex(ValueError,'attempt_consumed'):
                    scope.exercise(None,None,None,None,None,None,None,None,None,None,None,None)

    def test_x64_import_admission_refuses_unowned_dlls_delay_tables_and_ambiguous_ranges(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'probe.exe';original=synthetic_pe();path.write_bytes(original)
            admitted=stage.probe_identity(path)
            self.assertEqual(admitted['platform_imports'],['kernel32.dll','ws2_32.dll'])
            self.assertFalse(admitted['platform_loader_or_export_resolution_claimed'])
            mutations=[]
            bad=bytearray(original);bad[0x400:0x400+13]=b'zlibdll.dll\0\0';mutations.append(bad)
            bad=bytearray(original);struct.pack_into('<II',bad,152+112+13*8,0x1400,32);mutations.append(bad)
            bad=bytearray(original);struct.pack_into('<I',bad,152+120,0xfffffffe);mutations.append(bad)
            bad=bytearray(original);struct.pack_into('<I',bad,152+124,20);mutations.append(bad)
            bad=bytearray(original);struct.pack_into('<I',bad,0x200+12,0x1210);mutations.append(bad)
            bad=bytearray(original);struct.pack_into('<Q',bad,0x300,0x100000000);mutations.append(bad)
            bad=bytearray(original);struct.pack_into('<H',bad,134,2);bad[432:472]=bad[392:432];mutations.append(bad)
            for index,raw in enumerate(mutations):
                with self.subTest(index=index),self.assertRaises(ValueError):path.write_bytes(raw);stage.probe_identity(path)

    def test_native_keyset_and_enums_are_bound_to_exact_producer_owner_and_core(self):
        source=(stage.HERE/'windows/db_development_probe.c').read_text()
        emitted=set(re.findall(r'\\"([a-z_]+)\\":',source))
        self.assertEqual(emitted,stage.NATIVE_KEYS)
        owner=(stage.HERE/'windows/auth_db_development_owner.h').read_text()
        for c_name,prefix,expected in (('CohAuthDbDevelopmentPhase','COH_AUTH_DB_DEV_',stage.PHASES),
                ('CohAuthDbDevelopmentFailure','COH_AUTH_DB_DEV_FAILURE_',stage.FAILURES)):
            body=re.search(r'typedef enum \{([^}]+)\} '+c_name,owner).group(1)
            self.assertEqual(tuple(n.strip().removeprefix(prefix) for n in body.split(',')),expected)
        for preflight in (False,True):self.assertEqual(stage.admit_probe(positive(preflight),preflight),positive(preflight))
        with self.assertRaises(ValueError):stage.admit_probe(positive(True),False)
        with self.assertRaises(ValueError):stage.admit_probe(positive(False),True)

    def test_exact_types_full_completion_and_unclosed_authority_flags_are_enforced(self):
        original=positive()
        for key,value in original.items():
            bad=dict(original);bad[key]=not value if type(value) is bool else True if type(value) is int else 'other'
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit_probe(bad)
        for key in ('uid','cookie','account','password','raw_body','path','connect_id'):
            with self.assertRaises(ValueError):stage.admit_probe(dict(original,**{key:'PRIVATE_CANARY'}))
        for key,value in (('db_final_phase',9),('db_login_requests',2),('db_player_lists',2),('slots',0),
                ('base_slots',900001),('bonus_slots',900001),('udp_active',1),('udp_close_failures',1),
                ('udp_cleanup_failures',1),('db_unsupported',1),('db_queue_updates',1),('db_handoffs',1)):
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit_probe(dict(original,**{key:value}))
        for key in stage.ZERO_FLAGS|stage.FALSE_FLAGS:
            with self.assertRaises(ValueError):stage.native_shape(dict(original,**{key:True if key in stage.FALSE_FLAGS else 1}))
        preflight=positive(True)
        for key in ('begun','grant_consumed','db_login_requests','udp_created','udp_closed','slots'):
            with self.assertRaises(ValueError):stage.admit_probe(dict(preflight,**{key:1}),True)

    def test_failure_projection_refuses_private_malformed_live_and_unbounded_values(self):
        value=positive();value['passed']=False;value['phase']=4;value['status']=6;value['failure']=6
        def observe(raw,code=1):
            with tempfile.TemporaryFile() as output:
                output.write(raw);output.flush();return stage.observation(mock.Mock(poll=mock.Mock(return_value=code)),output)
        result=observe(json.dumps(value).encode())
        self.assertEqual((result['json_state'],result['phase'],result['status']),('VALID','FAILED','IO'))
        for key in ('base_slots','bonus_slots'):
            result=observe(json.dumps(dict(value,**{key:900001})).encode())
            self.assertEqual(result['json_state'],'VALID');self.assertNotIn('900001',json.dumps(result))
        bad=[b'',b'{PRIVATE_CANARY',b'x'*8193,json.dumps(dict(value,cookie='PRIVATE_CANARY')).encode(),
            json.dumps(value).replace('"phase": 4','"phase": 4, "phase": 4').encode(),
            json.dumps(value).replace('"elapsed_ms": 500','"elapsed_ms": NaN').encode(),
            json.dumps(dict(value,phase=900001)).encode(),json.dumps(dict(value,db_login_requests=900001)).encode()]
        for raw in bad:
            result=observe(raw);self.assertIn(result['json_state'],('REFUSED','OVERSIZE'))
            self.assertNotIn('PRIVATE_CANARY',json.dumps(result));self.assertEqual(result['phase'],'UNAVAILABLE')
        for code,state in ((None,'RUNNING'),(True,'OTHER_EXIT'),(3,'OTHER_EXIT')):
            result=observe(json.dumps(value).encode(),code);self.assertEqual(result['child_state'],state)
            self.assertNotEqual(result['json_state'],'VALID')

    def test_exact_recovered_zlib_existing_patch_and_new_probe_project_closure(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);zlib=root/'zlib'
            admitted=stage.recover_zlib(ROOT,zlib)
            self.assertTrue(admitted['existing_patch_applied_to_private_copy'])
            self.assertFalse(admitted['compiler_executed'])
            expected=stage.verify_zlib(ROOT,zlib)
            for path,change in ((zlib/'adler32.c',b'changed'),(zlib/'CMakeLists.txt',b'changed'),(zlib/'extra.c',b'extra')):
                saved=path.read_bytes() if path.exists() else None;path.write_bytes(change)
                with self.assertRaises(ValueError):stage.verify_zlib(ROOT,zlib)
                if saved is None:path.unlink()
                else:path.write_bytes(saved)
            self.assertEqual(stage.verify_zlib(ROOT,zlib),expected)
            sources=stage.prepare_project(ROOT,root/'project',root/'crypto',zlib)
            text=(root/'project/CMakeLists.txt').read_text()
            self.assertEqual(len(sources),16);self.assertEqual(len(set(sources)),16)
            self.assertIn('ZLIB::ZLIB',text);self.assertIn('MultiThreaded',text)
            self.assertIn('db_development_probe.c',text);self.assertNotIn('test_db_',text)
            self.assertNotIn('add_subdirectory("'+str(ROOT/'upstream/ouroboros'),text)
            with self.assertRaises(ValueError):stage.recover_zlib(ROOT,zlib)


if __name__=='__main__':unittest.main()

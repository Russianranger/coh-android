from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import hosted_db_shard_activation as stage

ROOT=Path(__file__).resolve().parents[4]


class DbShardActivationTests(unittest.TestCase):
    def test_actual_accepted_schema_and_compiled_db_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            db=stage.recover_db(ROOT,root/'db')
            schema=stage.recover_schema(ROOT,root/'schema')
            self.assertEqual(db['binary']['sha256'],stage.DB_BINARY_SHA)
            self.assertEqual(set(db['platform_imports']),stage.PLATFORM_DLLS)
            self.assertFalse(db['separate_runtime_dlls_required'])
            self.assertEqual(len(schema['files']),62)
            self.assertEqual(stage.prior.sha(root/'schema/schema-manifest.json'),stage.SCHEMA_SHA)
            for name,digest in (
                ('vars.attribute','26c5f2bba77ab66ef7619c995f343633dc1748297dc9963605734ef3aa1053bb'),
                ('badgestats.attribute','ec57e497c6c044269d8d7e207b0869400ceeb18a03b94bda1a9d00a9d99cced2'),
                ('pophelp.attribute','34195086d3223c717dca5e1cd00bc35a947a05d5fe31b2408a863e85aea617a1')):
                self.assertEqual(stage.prior.sha(root/'schema/data/server/db/templates'/name),digest)

    def test_owned_original_profiles_and_channel(self):
        instance='cohauth-ci-'+'a'*24
        auth=stage.auth_configuration(instance,[21000,21001,21002],Path('C:/owned/logs'))
        for text in ('UserData = true;','supportReconnect = true;','DBHasClientPorts = true;',
                     'allowUnknownServers = false;','gameServerSpecifiesId = false;',
                     'useQueue = false;','sendQueueLevel = false;','Encrypt = true;'):
            self.assertIn(text,auth)
        db=stage.db_configuration(instance,'cohdb_ci_'+'b'*24,21000,'coh-ci-'+'c'*24)
        self.assertIn('UseFakeAuth 0\n',db)
        self.assertIn('DefaultAccessLevel 0\n',db)
        self.assertNotIn('Ouroboros.exe',db)
        self.assertNotIn('Version',db)
        rows=[dict(pid=10,local='127.0.0.1',remote='127.0.0.1',lp=21000,rp=32000),
              dict(pid=20,local='127.0.0.1',remote='127.0.0.1',lp=32000,rp=21000)]
        self.assertTrue(stage.admit_channel(rows,10,20,21000)['loopback_pair_verified'])
        for index,key,value in ((0,'pid',20),(1,'rp',21001),(0,'remote','192.0.2.1'),
                                (1,'lp',32001),(0,'lp',True)):
            bad=[dict(row) for row in rows];bad[index][key]=value
            with self.assertRaises(ValueError):stage.admit_channel(bad,10,20,21000)
        for bad in ([],rows[:1],rows+rows):
            with self.assertRaises(ValueError):stage.admit_channel(bad,10,20,21000)
        with self.assertRaises(ValueError):stage.db_configuration('external','cohdb_ci_'+'b'*24,21000,'coh-ci-'+'c'*24)

    def test_local_refusal_and_owned_firewall_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'not-created'
            args=type('Args',(),dict(source_root=ROOT,output=output,expected_commit='a'*40))()
            # Explicitly model an unhosted call even when this regression suite
            # itself runs on the authorized hosted Windows service runner.
            with mock.patch.dict(os.environ,RUNNER_ENVIRONMENT='local-test'), \
                 self.assertRaisesRegex(ValueError,'fresh_github_hosted_windows_required'):
                stage.run(args)
            self.assertFalse(output.exists())
        runner=mock.Mock()
        for suffix,direction in (('in','Inbound'),('out','Outbound')):
            stage.firewall(runner,'coh-shard-'+'a'*24+'-db-'+suffix,Path('C:/owned/DbServer.exe'),direction,True)
            text=runner.run.call_args.args[1][-1]
            self.assertIn('-Protocol Any',text)
            self.assertIn('-Direction '+direction,text)
            self.assertIn('0.0.0.0-126.255.255.255',text)
            self.assertIn("Get-NetFirewallProfile",text)
            stage.firewall(runner,'coh-shard-'+'a'*24+'-db-'+suffix,Path('C:/owned/DbServer.exe'),direction,False)
            self.assertIn('Remove-NetFirewallRule',runner.run.call_args.args[1][-1])
        with self.assertRaises(ValueError):stage.firewall(runner,'unowned',Path('C:/owned/DbServer.exe'),'Inbound',True)

    def test_real_shaped_service_process_generation_and_path(self):
        for name,binary in (('AuthServer',stage.service.BINARY_SHA),('DbServer',stage.DB_BINARY_SHA)):
            expected=Path('D:/a/_temp/owned/'+name+'.exe')
            raw=dict(pid=4321,exists=True,name=name,started_utc_ticks=639277996886036331,
                     executable_path='D:\\a\\_temp\\owned\\'+name+'.exe')
            child=mock.Mock(pid=4321);child.poll.return_value=None
            with mock.patch.object(stage.prior,'capture',return_value=json.dumps(raw)) as command, \
                 mock.patch.object(stage.prior,'sha',return_value=binary):
                first=stage.service_process_snapshot(child,expected)
                self.assertIn('Get-Process -Id 4321',command.call_args.args[0][-1])
                self.assertIn('$p.Path',command.call_args.args[0][-1])
                self.assertEqual(stage.service_process_snapshot(child,expected,first),first)
                self.assertEqual(first['name'],name.lower())
                self.assertNotIn('executable_path',first)
                self.assertNotIn('D:',json.dumps(first))
            for key,value in (('name','sqlservr'),('name','OtherServer'),('pid',4322),
                    ('pid',True),('exists',False),('started_utc_ticks',True),
                    ('executable_path','D:\\a\\_temp\\other\\'+name+'.exe')):
                changed=dict(raw);changed[key]=value
                with self.subTest(name=name,key=key,value=value),self.assertRaises(ValueError):
                    stage.admit_service_process(changed,4321,expected,first)
            reused=dict(raw);reused['started_utc_ticks']+=1
            with self.assertRaisesRegex(ValueError,'generation_changed'):
                stage.admit_service_process(reused,4321,expected,first)
            child.poll.side_effect=[None,0]
            with mock.patch.object(stage.prior,'capture',return_value=json.dumps(raw)), \
                 mock.patch.object(stage.prior,'sha',return_value=binary), \
                 self.assertRaisesRegex(ValueError,'process_or_binary_changed'):
                stage.service_process_snapshot(child,expected)
            child.poll.side_effect=None;child.poll.return_value=None
            with mock.patch.object(stage.prior,'capture',return_value=json.dumps(raw)), \
                 mock.patch.object(stage.prior,'sha',return_value='0'*64), \
                 self.assertRaisesRegex(ValueError,'process_or_binary_changed'):
                stage.service_process_snapshot(child,expected)
        for path in ('relative/AuthServer.exe','C:AuthServer.exe','\\\\server\\share\\AuthServer.exe','C:/owned/Other.exe'):
            with self.assertRaises(ValueError):stage.service_image_path(path)

    def test_stream_close_failure_does_not_stop_other_teardown(self):
        broken,healthy=mock.Mock(),mock.Mock()
        broken.close.side_effect=OSError('private detail never exported')
        self.assertFalse(stage.close_streams([broken,healthy]))
        healthy.close.assert_called_once()

    def test_service_stage_success_and_late_failure_owned_cleanup(self):
        @dataclass(frozen=True)
        class Prerequisite:
            fresh_authentication_required:bool=True
        for failure in (None,'before_db','after_db','diagnostic','close_stream','selected_success','selected_refusal'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                base=Path(temp);events=[];processes=[]
                candidate=base/'candidate';candidate.mkdir();(candidate/stage.service.candidate.BINARY).write_bytes(b'auth')
                args=type('Args',(),dict(source_root=ROOT,output=base/'output',expected_commit='a'*40,
                     auth_candidate_stage=candidate,auth_success_archive=base/'unused.zip'))()
                class Commands:
                    def __init__(self,output):self.records=[]
                class SQL:
                    def __init__(self,records,private):self.records=records
                    def run(self,name,argv,**kwargs):events.append(name);return 0
                    def numeric(self,name,argv,kind):return '17.0.4025.3' if kind=='version' else 30
                class Child:
                    def __init__(self,pid):self.pid=pid;self.closed=False
                    def poll(self):return 0 if self.closed else None
                class Job:
                    def __init__(self):self.handle=1
                    def assign(self,child):events.append('assign-'+str(child.pid))
                    def stop(self,child):events.append('stop-'+str(child.pid));child.closed=True;self.handle=None;return True
                def popen(argv,**kwargs):
                    child=Child(10 if len(processes)==0 else 20);processes.append(child)
                    if child.pid==20:kwargs['stdout'].write(b'AuthServer Git Commit Hash: source\nSQL server 17 connected\nDbServer Ready.\n');kwargs['stdout'].flush()
                    return child
                def recover_schema(root,out):
                    (out/'data/server/db').mkdir(parents=True)
                    (out/'data/server/db/servers.cfg').write_text('accepted default')
                    return dict(files={},source_commit='s',data_commit='d')
                def recover_db(root,out):out.mkdir();(out/stage.db_build.BINARY).write_bytes(b'db');return {}
                actual_sha=stage.prior.sha
                def sha(path):
                    if path.name=='AuthServer.exe':return stage.service.BINARY_SHA
                    if path.name=='DbServer.exe':return stage.DB_BINARY_SHA
                    return actual_sha(path)
                values=iter([1 if failure=='before_db' else 0,1,99])
                def capture(argv):return 'a'*40 if argv[-1]=='HEAD' else ''
                def channel(*args):
                    if failure in ('after_db','diagnostic'):raise ValueError('test_after_db')
                    return {'loopback_pair_verified':True}
                def firewall(runner,name,binary,direction,add):events.append(('add-' if add else 'remove-')+name)
                def service_snapshot(child,path,previous=None):
                    # Pass real-shaped service identity through the production
                    # admission; the SQL-only helper below rejects these PIDs.
                    name='AuthServer' if child.pid==10 else 'DbServer'
                    expected='D:/a/_temp/owned/'+name+'.exe'
                    raw=dict(pid=child.pid,exists=True,name=name,
                        started_utc_ticks=639277996886036331+child.pid,executable_path=expected)
                    return stage.admit_service_process(raw,child.pid,expected,previous)
                def sql_snapshot(pid):
                    if pid!=30:raise AssertionError('SQL observer used for a service process')
                    return dict(pid=30,exists=True,name='sqlservr',started_utc_ticks=639277996886036330)
                original_close=stage.close_streams
                def close_streams(handles):
                    complete=original_close(handles)
                    return complete and failure!='close_stream'
                scope=None
                if failure in ('selected_success','selected_refusal'):
                    scope=mock.Mock()
                    def prepare(*values):
                        self.assertFalse(processes);events.append('selected-prepare')
                    def exercise(*values):
                        self.assertEqual(len(processes),2);events.append('selected-exercise')
                        values[1]['client_login_attempted']=True
                        return failure=='selected_success'
                    scope.prepare.side_effect=prepare;scope.exercise.side_effect=exercise
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(os.environ,RUNNER_TEMP=temp))
                    stack.enter_context(mock.patch.object(stage.prior,'require_hosted',return_value={}))
                    stack.enter_context(mock.patch.object(stage,'authenticated_handoff_prerequisite',return_value=Prerequisite()))
                    stack.enter_context(mock.patch.object(stage.service.candidate,'admit',return_value={}))
                    stack.enter_context(mock.patch.object(stage,'recover_schema',side_effect=recover_schema))
                    stack.enter_context(mock.patch.object(stage,'recover_db',side_effect=recover_db))
                    stack.enter_context(mock.patch.object(stage.service,'tools',return_value=(Path('LocalDB'),Path('SQLCMD'),{})))
                    stack.enter_context(mock.patch.object(stage.prior,'Commands',Commands))
                    stack.enter_context(mock.patch.object(stage,'RedactedCommands',SQL))
                    stack.enter_context(mock.patch.object(stage.prior,'capture',side_effect=capture))
                    stack.enter_context(mock.patch.object(stage.prior,'sha',side_effect=sha))
                    stack.enter_context(mock.patch.object(stage.auth_readiness,'observe',return_value={'healthy':True}))
                    stack.enter_context(mock.patch.object(stage.login,'reserve_ports',return_value=([21000,21001,21002],[])))
                    stack.enter_context(mock.patch.object(stage,'firewall',side_effect=firewall))
                    stack.enter_context(mock.patch.object(stage.login,'OwnedJob',Job))
                    stack.enter_context(mock.patch.object(stage.subprocess,'Popen',side_effect=popen))
                    stack.enter_context(mock.patch.object(stage.login,'inspect_listeners',side_effect=lambda pid:set() if next(p for p in processes if p.pid==pid).closed else {21000,21001,21002}))
                    stack.enter_context(mock.patch.object(stage,'scalar',side_effect=lambda *args,**kwargs:next(values)))
                    stack.enter_context(mock.patch.object(stage,'owned_channel',side_effect=channel))
                    stack.enter_context(mock.patch.object(stage,'game_listener',return_value={'owner_pid':20}))
                    stack.enter_context(mock.patch.object(stage,'service_process_snapshot',side_effect=service_snapshot))
                    observer=stack.enter_context(mock.patch.object(stage.db_startup_diagnostic,'observe_sql',return_value={'user_tables':0}))
                    if failure=='diagnostic':observer.side_effect=OSError('private SQL details never exported')
                    stack.enter_context(mock.patch.object(stage.db_startup_diagnostic,'observe_process',return_value={'thread_count':64}))
                    stack.enter_context(mock.patch.object(stage.login,'owned_process_snapshot',side_effect=sql_snapshot))
                    stack.enter_context(mock.patch.object(stage,'close_streams',side_effect=close_streams))
                    proof=stage.run(args,scope)
                self.assertEqual(proof['passed'],failure in (None,'selected_success'))
                for key in ('owned_service_cleanup_complete','owned_firewall_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'):
                    self.assertEqual(proof[key],not(failure=='close_stream' and key=='owned_service_cleanup_complete'),key)
                self.assertEqual(proof['client_login_attempted'],scope is not None)
                self.assertEqual(proof['selected_shard_play_verified'],failure=='selected_success')
                if scope is not None:
                    scope.prepare.assert_called_once();scope.exercise.assert_called_once()
                    self.assertLess(events.index('selected-prepare'),events.index('assign-10'))
                    self.assertLess(events.index('selected-exercise'),events.index('stop-20'))
                self.assertFalse(proof['authenticated_db_map_handoff_verified'])
                self.assertFalse(proof['checksum_policy_relaxed'])
                if failure in ('after_db','diagnostic'):
                    diagnostic=proof['owned_db_startup_diagnostic']
                    self.assertEqual(diagnostic['complete'],failure=='after_db')
                    self.assertFalse(diagnostic['raw_console_or_sql_exported'])
                    self.assertNotIn('private SQL details',json.dumps(proof))
                self.assertEqual(len([e for e in events if e.startswith('add-coh-shard-')]),4)
                self.assertEqual(len([e for e in events if e.startswith('remove-coh-shard-')]),4)
                self.assertEqual(events[-4:],['drop-owned-game-db','localdb-drop-owned-schema','localdb-stop-owned-instance','localdb-delete-owned-instance'])
                self.assertEqual([e for e in events if e.startswith('stop-')],['stop-10'] if failure=='before_db' else ['stop-20','stop-10'])


if __name__=='__main__':unittest.main()

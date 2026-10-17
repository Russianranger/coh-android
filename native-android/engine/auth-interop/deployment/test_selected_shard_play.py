from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import hosted_selected_shard_play as stage

ROOT=Path(__file__).resolve().parents[4]


class SelectedShardPlayTests(unittest.TestCase):
    def test_probe_owner_selection_grant_wipe_and_failure_cleanup(self):
        source=stage.HERE/'windows/test_shard_play_probe.c'
        scenarios=('success','allocation-failure','begin-failure','login-failure','play-failure',
            'wrong-endpoint','down-shard','wrong-port','wrong-id','empty-shards','extra-shards',
            'choose-failure','zero-cookie','zero-uid','wrong-uid','wrong-play-shard')
        with tempfile.TemporaryDirectory() as name:
            for mode,flags in (('release',['-O2']),('asan_ubsan',['-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])):
                binary=Path(name)/mode
                subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(ROOT/'native-android/include'),*flags,source,'-o',binary],check=True,capture_output=True)
                for scenario in scenarios:
                    result=subprocess.run([binary,scenario,'23000','1024'],input=b'test-account\ntest-password\n',capture_output=True,timeout=10,
                        env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
                    self.assertEqual(result.returncode,0 if scenario=='success' else 1,(mode,scenario,result.stderr.decode()))
                    proof=json.loads(result.stdout)
                    self.assertTrue(proof['local_sensitive_buffers_wiped'])
                    self.assertNotIn('test-account',result.stdout.decode())
                    self.assertNotIn('test-password',result.stdout.decode())
                    self.assertFalse(proof['db_login_attempted'])
                    if scenario=='success':stage.admit_probe(proof,1024)
                    else:
                        self.assertFalse(proof['passed'])
                        with self.assertRaises(ValueError):stage.admit_probe(proof,1024)

    def test_probe_receipt_rejects_wrong_types_scope_and_export_fields(self):
        proof=dict(schema='coh-selected-shard-play-probe-v1',passed=True,state=7,protocol=191021,
            shards=1,received_frames=4,sent_bytes=200,elapsed_ms=10,send_cap=1024,
            selected_shard_verified=True,live_grant_retained_then_wiped=True,
            local_sensitive_buffers_wiped=True,authorization_invalid_after_close=True,
            socket_cleanup_complete=True,password_retained_after_close=False,
            db_login_attempted=False,authenticated_db_map_handoff_verified=False,
            checksum_policy_relaxed=False,nondevelopment_version_admitted=False,
            real_server_provenance_verified_by_probe=False)
        self.assertEqual(stage.admit_probe(proof,1024),proof)
        for key,value in list(proof.items()):
            bad=dict(proof);bad[key]=not value if type(value) is bool else (True if type(value) is int else 'other')
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit_probe(bad,1024)
        for key in ('cookie','uid','packet_body','account','password'):
            bad=dict(proof);bad[key]='never accepted'
            with self.assertRaises(ValueError):stage.admit_probe(bad,1024)

    def test_fixture_and_new_build_are_narrow(self):
        sql=stage.account_sql()
        self.assertIn('INSERT INTO dbo.user_account',sql)
        self.assertIn(',900001,1,0,0,0,0,0,0,',sql)
        self.assertIn('INSERT dbo.user_data',sql)
        self.assertNotIn('auth-only server table must remain empty',sql)
        for column,size in (('user_data',16),('user_data_new',112),('user_game_data',16),('user_game_data_new',112)):
            self.assertIn(column+' IS NOT NULL',stage.USERDATA_QUERY)
            self.assertIn('DATALENGTH('+column+')='+str(size),stage.USERDATA_QUERY)
        with tempfile.TemporaryDirectory() as name:
            project=Path(name)/'project'
            sources=stage.prepare_project(ROOT,project,Path(name)/'retained')
            cmake=(project/'CMakeLists.txt').read_text()
            self.assertIn('libcrypto.lib',cmake)
            self.assertIn('set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)',cmake)
            self.assertNotIn('add_subdirectory',cmake)
            self.assertNotIn('fixture_constants',cmake)
            self.assertNotIn('coh_db',cmake)
            self.assertEqual(sources[0].name,'shard_play_probe.c')
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaisesRegex(ValueError,'manifest_identity'):stage.admit_crypto(Path(name),ROOT)

    def test_owned_generation_and_userdata_are_checked_around_new_scope(self):
        scope=stage.SelectedScope(Path('unused'));scope.binary=Path('probe')
        proof={'selected_probe_build':{'binary':{'sha256':'expected'}}}
        auth,db=mock.Mock(pid=10),mock.Mock(pid=20)
        baseline={'pid':30,'exists':True}
        args=(Path('private'),proof,[],[21000,21001,21002],auth,db,Path('AuthServer.exe'),Path('DbServer.exe'),{'pid':10},{'pid':20},30,baseline)
        with ExitStack() as stack:
            snapshots=stack.enter_context(mock.patch.object(stage.activation,'service_process_snapshot',return_value={'exists':True}))
            sql=stack.enter_context(mock.patch.object(stage.login,'owned_process_snapshot',return_value=baseline))
            channel=stack.enter_context(mock.patch.object(stage.activation,'owned_channel',return_value={'loopback_pair_verified':True}))
            stack.enter_context(mock.patch.object(stage.activation,'game_listener',return_value={'owner_pid':20}))
            stack.enter_context(mock.patch.object(stage.login,'inspect_listeners',return_value={21000,21001,21002}))
            scalar=stack.enter_context(mock.patch.object(stage.activation,'scalar',return_value=1))
            stack.enter_context(mock.patch.object(stage.login,'probe_identity',return_value={'sha256':'expected'}))
            probe=stack.enter_context(mock.patch.object(stage,'run_probe',return_value={'passed':True}))
            self.assertTrue(scope.exercise(*args))
            self.assertEqual(snapshots.call_count,4);self.assertEqual(channel.call_count,2)
            self.assertEqual(sql.call_count,2)
            self.assertTrue(proof['client_login_attempted'])
            probe.reset_mock();scalar.side_effect=[1,0]
            with self.assertRaisesRegex(ValueError,'userdata_not_complete'):scope.exercise(*args)
            probe.assert_not_called()
            scalar.side_effect=None;sql.return_value={'pid':30,'exists':True,'reused':True}
            with self.assertRaisesRegex(ValueError,'runtime_unavailable'):scope.exercise(*args)
            probe.assert_not_called()
            sql.return_value=baseline;scalar.return_value=1
            probe.side_effect=lambda *args:sql.configure_mock(return_value={'pid':31,'exists':True}) or {'passed':True}
            with self.assertRaisesRegex(ValueError,'runtime_unavailable'):scope.exercise(*args)

    def test_probe_pipe_job_failure_paths_are_closed_and_private_input_wiped(self):
        for failure in ('assign','communicate','stop','stop_false','none'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as name:
                child=mock.Mock(stdin=mock.Mock(),returncode=0)
                job=mock.Mock(handle=123)
                if failure=='assign':job.assign.side_effect=OSError('private assignment detail')
                if failure=='stop':job.stop.side_effect=OSError('private stop detail')
                elif failure=='stop_false':job.stop.return_value=False
                else:
                    def stop(process):job.handle=None;return True
                    job.stop.side_effect=stop
                retained=[]
                def popen(argv,**kwargs):
                    self.assertEqual(argv,['probe','23000','1024'])
                    def communicate(input,timeout):
                        retained.append(input)
                        if failure=='communicate':raise subprocess.TimeoutExpired('private',25)
                        kwargs['stdout'].write(b'{"passed":true}');kwargs['stdout'].flush()
                    child.communicate.side_effect=communicate
                    return child
                with mock.patch.object(stage.login,'OwnedJob',return_value=job), \
                     mock.patch.object(stage.subprocess,'Popen',side_effect=popen), \
                     mock.patch.object(stage,'admit_probe',return_value={'passed':True}):
                    if failure=='none':self.assertEqual(stage.run_probe(Path('probe'),23000,1024,Path(name)),{'passed':True})
                    else:
                        with self.assertRaises((OSError,subprocess.TimeoutExpired,ValueError)):
                            stage.run_probe(Path('probe'),23000,1024,Path(name))
                child.stdin.close.assert_called_once();job.stop.assert_called_once_with(child)
                if failure in ('stop','stop_false'):job.kernel.CloseHandle.assert_called_once_with(123)
                for value in retained:self.assertTrue(all(v==0 for v in value))

    def test_new_scope_must_belong_to_current_committed_source(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            def git(*args):
                subprocess.run(['git','-C',root,*args],check=True,capture_output=True)
            git('init');git('config','user.name','Test Owner');git('config','user.email','test@example.invalid')
            git('commit','--allow-empty','-m','Initial source')
            for relative in ('deployment/hosted_selected_shard_play.py','deployment/windows/shard_play_probe.c'):
                path=root/'native-android/engine/auth-interop'/relative
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'committed source\n')
            with self.assertRaisesRegex(ValueError,'not_owned_by_head'):stage.admit_scope_sources(root)
            git('add','native-android');git('commit','-m','Own new scope')
            self.assertEqual(len(stage.admit_scope_sources(root)),2)
            path.write_bytes(b'modified source\n')
            with self.assertRaisesRegex(ValueError,'not_owned_by_head'):stage.admit_scope_sources(root)


if __name__=='__main__':unittest.main()

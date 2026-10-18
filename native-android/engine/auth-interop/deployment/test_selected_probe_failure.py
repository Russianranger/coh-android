"""New failure observations only; no original service, compiler or network."""
from contextlib import ExitStack
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

import hosted_selected_shard_play as stage

CANARY='PRIVATE-ACCOUNT-COOKIE-UID-PACKET-PATH-CANARY'


def native(passed=False):
    return dict(schema='coh-selected-shard-play-probe-v1',passed=passed,
        state=7 if passed else 6,protocol=191021,shards=1,received_frames=4 if passed else 3,
        sent_bytes=200,elapsed_ms=20000,send_cap=1024,selected_shard_verified=True,
        live_grant_retained_then_wiped=passed,local_sensitive_buffers_wiped=True,
        authorization_invalid_after_close=True,socket_cleanup_complete=True,
        password_retained_after_close=False,db_login_attempted=False,
        authenticated_db_map_handoff_verified=False,checksum_policy_relaxed=False,
        nondevelopment_version_admitted=False,real_server_provenance_verified_by_probe=False)


class FailureObservationTests(unittest.TestCase):
    def observe(self,value,code=1):
        raw=value if type(value) is bytes else json.dumps(value).encode()
        with tempfile.TemporaryFile() as output:
            output.write(raw);output.flush()
            return stage.probe_observation(mock.Mock(poll=mock.Mock(return_value=code)),output,1024)

    def test_fixed_state_enum_and_failure_projection_are_source_bound(self):
        header=(stage.HERE.parents[1]/'login/coh_login.h').read_text()
        body=re.search(r'typedef enum \{([^}]+)\} CohLoginState;',header).group(1)
        self.assertEqual(tuple(name.strip().removeprefix('COH_LOGIN_') for name in body.split(',')),stage.PROBE_STATES)
        for number,name in enumerate(stage.PROBE_STATES):
            value=native();value['state']=number
            observed=self.observe(value)
            self.assertEqual(observed['json_state'],'VALID');self.assertEqual(observed['probe_state'],name)
            self.assertEqual(observed['child_state'],'EXIT_ONE');self.assertFalse(observed['probe_passed'])
            self.assertTrue(observed['local_sensitive_buffers_wiped']);self.assertFalse(observed['raw_private_output_exported'])
        value=native();value['protocol']=0xffffffff
        observed=self.observe(value);self.assertEqual(observed['protocol_class'],'OTHER')
        self.assertNotIn('4294967295',json.dumps(observed));self.assertNotIn('protocol',observed)

    def test_malformed_extra_duplicate_types_bounds_and_live_child_are_refused_privately(self):
        original=native();bad=[b'',b'{'+CANARY.encode(),b'x'*8193,
            json.dumps(original).replace('"state": 6','"state": 6, "state": 7').encode(),
            json.dumps(original).replace('"elapsed_ms": 20000','"elapsed_ms": NaN').encode()]
        for key,value in (('cookie',CANARY),('uid',CANARY),('account',CANARY),('path',CANARY),('packet_body',CANARY),
                ('state',14),('state',True),('state',-1),('protocol',True),('protocol',0x100000000),
                ('shards',33),('received_frames',65),('sent_bytes',4097),('elapsed_ms',30001),('send_cap',7),
                ('local_sensitive_buffers_wiped',1),('db_login_attempted',True),('passed',True)):
            bad.append(dict(original,**{key:value}))
        missing=dict(original);del missing['state'];bad.append(missing)
        for value in bad:
            result=self.observe(value)
            self.assertIn(result['json_state'],('REFUSED','OVERSIZE'))
            self.assertEqual(result['probe_state'],'UNAVAILABLE');self.assertNotIn(CANARY,json.dumps(result))
        for code,state in ((None,'RUNNING'),(-15,'OTHER_EXIT'),(3,'OTHER_EXIT'),(True,'OTHER_EXIT')):
            result=self.observe(original,code);self.assertEqual(result['child_state'],state)
            self.assertNotEqual(result['json_state'],'VALID')
        self.assertEqual(self.observe(b'x'*8193)['stdout_bytes_bounded'],8193)
        for value in (['not a sink'],{'account':CANARY}):
            with self.assertRaisesRegex(ValueError,'observation_sink'):
                stage.run_probe(Path('unused'),23000,1024,Path('unused'),value)

    def test_actual_owned_child_projection_is_latched_before_stop_even_on_late_cleanup_error(self):
        for failure in ('native','oversize','malformed','timeout','assign','stop','stop_false','popen','job'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                observation={};credentials=[];events=[]
                child=mock.Mock(stdin=mock.Mock(),returncode=1)
                child.poll.return_value=None if failure in ('timeout','assign') else 1
                job=mock.Mock(handle=123)
                if failure=='assign':job.assign.side_effect=OSError(CANARY)
                def stop(actual):
                    self.assertIs(actual,child);events.append('stop')
                    self.assertIn('json_state',observation)
                    if failure in ('native','stop','stop_false'):
                        self.assertEqual(observation['probe_state'],'WAIT_PLAY')
                        self.assertEqual(observation['json_state'],'VALID')
                    if failure=='stop':raise OSError(CANARY)
                    if failure=='stop_false':return False
                    job.handle=None;return True
                job.stop.side_effect=stop
                def popen(argv,**kwargs):
                    if failure=='popen':raise OSError(CANARY)
                    def communicate(input,timeout):
                        credentials.append(input)
                        if failure=='timeout':raise subprocess.TimeoutExpired(CANARY,25)
                        body=b'x'*8193 if failure=='oversize' else b'{'+CANARY.encode() if failure=='malformed' else json.dumps(native()).encode()
                        kwargs['stdout'].write(body);kwargs['stdout'].flush()
                    child.communicate.side_effect=communicate
                    return child
                with mock.patch.object(stage.login,'OwnedJob',side_effect=OSError(CANARY) if failure=='job' else lambda:job),\
                     mock.patch.object(stage.subprocess,'Popen',side_effect=popen):
                    with self.assertRaises((ValueError,OSError,subprocess.TimeoutExpired)):
                        stage.run_probe(Path('probe'),23000,1024,Path(temp),observation)
                self.assertNotIn(CANARY,json.dumps(observation));self.assertTrue(all(not any(value) for value in credentials))
                self.assertEqual(observation['owned_probe_cleanup_complete'],failure not in ('stop','stop_false','job'))
                if failure not in ('popen','job'):
                    self.assertEqual(events,['stop']);child.stdin.close.assert_called_once()
                if failure in ('stop','stop_false'):job.kernel.CloseHandle.assert_called_once_with(123)

    def test_primary_probe_exception_survives_stop_and_handle_close_exceptions(self):
        for failure in ('native_stop','timeout_stop','timeout_stop_close','parse_stop_close'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                observation={};child=mock.Mock(stdin=mock.Mock(),returncode=1)
                child.poll.return_value=1;job=mock.Mock(handle=123)
                job.stop.side_effect=OSError(CANARY)
                if failure.endswith('close'):job.kernel.CloseHandle.side_effect=OSError(CANARY)
                primary=subprocess.TimeoutExpired(CANARY,25) if failure.startswith('timeout') else ValueError('selected_native_probe_scope')
                def popen(argv,**kwargs):
                    def communicate(input,timeout):
                        if failure.startswith('timeout'):raise primary
                        kwargs['stdout'].write(json.dumps(native()).encode());kwargs['stdout'].flush()
                    child.communicate.side_effect=communicate
                    if failure.startswith('parse'):child.returncode=0
                    return child
                with mock.patch.object(stage.login,'OwnedJob',return_value=job),\
                     mock.patch.object(stage.subprocess,'Popen',side_effect=popen),\
                     mock.patch.object(stage,'admit_probe',side_effect=primary):
                    with self.assertRaises((ValueError,subprocess.TimeoutExpired)) as caught:
                        stage.run_probe(Path('probe'),23000,1024,Path(temp),observation)
                if failure.startswith(('timeout','parse')):self.assertIs(caught.exception,primary)
                else:self.assertEqual(str(caught.exception),'selected_private_probe_failed')
                self.assertFalse(observation['owned_probe_cleanup_complete'])
                self.assertEqual(observation['owned_probe_cleanup_outcome'],'EXCEPTION')
                self.assertNotIn(CANARY,json.dumps(observation));child.stdin.close.assert_called_once()

    def test_success_validation_is_unchanged_and_does_not_publish_failure_field(self):
        with tempfile.TemporaryDirectory() as temp:
            observation={};child=mock.Mock(stdin=mock.Mock(),returncode=0);child.poll.return_value=0
            job=mock.Mock(handle=123)
            def stop(child):job.handle=None;return True
            job.stop.side_effect=stop
            def popen(argv,**kwargs):
                child.communicate.side_effect=lambda **ignored:kwargs['stdout'].write(json.dumps(native(True)).encode())
                return child
            with mock.patch.object(stage.login,'OwnedJob',return_value=job),mock.patch.object(stage.subprocess,'Popen',side_effect=popen):
                self.assertEqual(stage.run_probe(Path('probe'),23000,1024,Path(temp),observation),native(True))
            self.assertEqual(observation['json_state'],'VALID');self.assertEqual(observation['child_state'],'EXIT_ZERO')
            self.assertTrue(observation['probe_passed']);self.assertTrue(observation['owned_probe_cleanup_complete'])

    def test_postprobe_runtime_check_runs_on_all_outcomes_and_preserves_first_failure(self):
        for failure in ('none','native','timeout','observer','native_and_observer'):
            with self.subTest(failure=failure):
                scope=stage.SelectedScope(Path('retained'));scope.binary=Path('probe')
                proof={'selected_probe_build':{'binary':{'sha256':'probe'}}};events=[]
                auth,db=mock.Mock(pid=10),mock.Mock(pid=20);baseline={'pid':30,'exists':True}
                def channel(*args):
                    events.append('observe')
                    if events.count('observe')==2 and failure in ('observer','native_and_observer'):raise ValueError(CANARY)
                    return {'loopback_pair_verified':True}
                def probe(binary,port,cap,temporary,observation):
                    events.append('probe')
                    native_failed=failure in ('native','native_and_observer','timeout')
                    observation.update(self.observe(native(not native_failed),None if failure=='timeout' else 1 if native_failed else 0))
                    if failure in ('native','native_and_observer'):raise ValueError('selected_private_probe_failed')
                    if failure=='timeout':raise subprocess.TimeoutExpired(CANARY,25)
                    return native(True)
                with ExitStack() as stack:
                    for owner,name,value in ((stage.activation,'service_process_snapshot',{'exists':True}),
                        (stage.login,'owned_process_snapshot',baseline),(stage.activation,'game_listener',{'owner_pid':20}),
                        (stage.login,'inspect_listeners',{21000,21001,21002}),(stage.activation,'scalar',1),
                        (stage.login,'probe_identity',{'sha256':'probe'})):
                        stack.enter_context(mock.patch.object(owner,name,return_value=value))
                    stack.enter_context(mock.patch.object(stage.activation,'owned_channel',side_effect=channel))
                    stack.enter_context(mock.patch.object(stage,'run_probe',side_effect=probe))
                    args=(Path('private'),proof,[],[21000,21001,21002],auth,db,Path('AuthServer.exe'),Path('DbServer.exe'),{}, {},30,baseline)
                    if failure=='none':self.assertTrue(scope.exercise(*args))
                    elif failure=='timeout':
                        with self.assertRaises(subprocess.TimeoutExpired):scope.exercise(*args)
                    else:
                        with self.assertRaisesRegex(ValueError,'selected_private_probe_failed' if failure.startswith('native') else CANARY):scope.exercise(*args)
                self.assertEqual(events,['observe','probe','observe'])
                self.assertEqual(proof['selected_runtime_after_probe_verified'],failure not in ('observer','native_and_observer'))
                if failure=='none':self.assertNotIn('selected_probe_failure_observation',proof)
                else:self.assertIn('selected_probe_failure_observation',proof)
                if failure in ('observer','native_and_observer'):
                    self.assertEqual(proof['selected_runtime_after_probe_failure'],'OWNED_RUNTIME_OBSERVER_REFUSED')
                if failure=='observer':
                    self.assertTrue(proof['selected_probe_failure_observation']['probe_passed'])
                    self.assertEqual(proof['selected_probe_failure_observation']['json_state'],'VALID')
                self.assertNotIn(CANARY,json.dumps(proof))


if __name__=='__main__':unittest.main(verbosity=2)

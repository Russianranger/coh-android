from contextlib import ExitStack
"""Isolated orchestration boundaries; no Windows, SQL, service or crypto executed."""
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import hosted_candidate_login as stage
import sql_readiness_diagnostic
from test_auth_login_stage import fixture

ROOT = Path(__file__).resolve().parents[4]


class CandidateLoginTests(unittest.TestCase):
    def child(self):
        return SimpleNamespace(pid=44, poll=lambda: None, kill=Mock(), wait=Mock())

    def test_eight_normal_and_partial_send_cases_are_admitted(self):
        proof = {'probe_results': {}, 'positive_modes_verified': []}
        def result(command, **kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps(fixture(command[-1])).encode())
        with patch.object(stage.login, 'inspect_listeners', return_value={21000,21001,21002}), \
             patch.object(stage.login, 'private_logs_bounded'), patch.object(stage.subprocess, 'run', side_effect=result) as run:
            stage.exercise({'normal':Path('normal.exe'),'capped':Path('capped.exe')}, self.child(), [21000,21001,21002], Path('private'), proof)
        self.assertEqual(run.call_count, 8)
        self.assertEqual(proof['positive_modes_verified'], ['normal','capped'])
        self.assertTrue(proof['account_normal_and_capped_sends_verified'])
        self.assertEqual(set(proof['probe_results']['capped']), set(stage.login.CASES))

    def test_probe_wrong_exit_extra_private_fields_and_missing_cleanup_refused(self):
        variants = [(1, fixture('valid'))]
        for field, value in [('password_retained_after_close',True),('passed',False),('raw_log','secret')]:
            changed=fixture('valid');changed[field]=value;variants.append((0,changed))
        for exitcode, value in variants:
            proof = {'probe_results': {}, 'positive_modes_verified': []}
            with patch.object(stage.login,'inspect_listeners',return_value={1,2,3}), \
                 patch.object(stage.login,'private_logs_bounded'), \
                 patch.object(stage.subprocess,'run',return_value=SimpleNamespace(returncode=exitcode,stdout=json.dumps(value).encode())):
                with self.assertRaises(ValueError):
                    stage.exercise({'normal':Path('normal.exe'),'capped':Path('capped.exe')},self.child(),[1,2,3],Path('private'),proof)
            self.assertNotIn('secret',json.dumps(proof))
            self.assertFalse(proof.get('account_normal_and_capped_sends_verified',False))

    def test_lost_listener_prevents_probe(self):
        with patch.object(stage.login,'inspect_listeners',return_value=set()), patch.object(stage.subprocess,'run') as run:
            with self.assertRaises(ValueError):
                stage.exercise({},self.child(),[1,2,3],Path('private'),{'probe_results':{}})
            run.assert_not_called()

    def test_job_member_diagnostic_failure_still_stops_job(self):
        job=Mock();job.process_ids.side_effect=ValueError('diagnostic');job.stop.return_value=True
        proof={}
        with patch.object(stage.login,'inspect_listeners',return_value=set()):
            self.assertFalse(stage.stop_owned(self.child(),job,99,proof))
        job.stop.assert_called_once()
        self.assertTrue(proof['owned_authserver_job_stop_complete'])
        self.assertTrue(proof['owned_authserver_listeners_absent'])

    def test_job_stop_failure_still_kills_and_closes_owned_handle(self):
        job=Mock();job.process_ids.return_value=[44];job.stop.side_effect=RuntimeError();job.handle=123
        child=self.child()
        with patch.object(stage.login,'inspect_listeners',return_value=set()):
            self.assertFalse(stage.stop_owned(child,job,99,{}))
        child.kill.assert_called_once();job.kernel.CloseHandle.assert_called_once_with(123)

    def test_readiness_failure_before_popen_preserves_sql_and_private_cleanup(self):
        for memory in (256,1024):
            with self.subTest(sql_memory_limit_mb=memory), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);output=root/'output'
                args=SimpleNamespace(source_root=ROOT,output=output,expected_commit='0'*40,
                    candidate_stage=root/'candidate',reuse_odbc_stage=root/'odbc',reuse_probe_stage=root/'probe',
                    intact_stage=root/'intact',intact_receipt_sha256=stage.INTACT_RECEIPT_SHA,intact_binary_sha256=stage.INTACT_BINARY_SHA,sql_memory_limit_mb=memory)
                class Commands:
                    def __init__(self,target,private_directory=None): self.output=output;self.records=target if isinstance(target,list) else []
                    def numeric(self,name,command,kind,**kwargs): return '17.0.4025.3' if kind=='version' else 99
                    def run(self,name,command,**kwargs):
                        self.records.append({'name':name})
                        text='17.0.4025.3' if name=='localdb-version' else '99' if name=='localdb-owned-process-id' else ''
                        (self.output/(name+'.log')).write_text(text)
                        if name=='archive-original-source':
                            path=next(str(x).split('=',1)[1]for x in command if str(x).startswith('--output='))
                            with tarfile.open(path,'w'): pass
                cleanup=Mock(return_value=True);firewall=Mock();popen=Mock()
                patches=[
                    patch.dict(stage.os.environ,{'RUNNER_TEMP':temporary}),
                    patch.object(stage.prior,'require_hosted',return_value={'original_source_tree':stage.prior.ORIGINAL_TREE}),
                    patch.object(stage.candidate,'admit',return_value={}),
                    patch.object(stage.login,'admit_odbc_receipt',return_value={}),
                    patch.object(stage.login,'admit_probe_reuse',return_value={}),
                    patch.object(stage,'admit_intact',return_value={}),
                    patch.object(stage,'tools',return_value=(Path('sql-localdb'),Path('sqlcmd'),{})),
                    patch.object(stage.login,'qualify_listener_projection',return_value={}),
                    patch.object(stage.prior,'Commands',Commands),
                    patch.object(sql_readiness_diagnostic,'RedactedCommands',Commands),
                    patch.object(stage.prior,'capture',return_value=''),
                    patch.object(stage.login.profile,'audit',return_value={}),
                    patch.object(stage.login,'private_command'),
                    patch.object(stage.login,'owned_process_snapshot',return_value={'exists':True}),
                    patch.object(stage.auth_readiness,'observe',return_value={'healthy':False}),
                    patch.object(stage.prior,'cleanup_owned_instance',cleanup),
                    patch.object(stage.login,'firewall_rule',firewall),
                    patch.object(stage.subprocess,'Popen',popen),
                ]
                with ExitStack() as contexts:
                    for patcher in patches:contexts.enter_context(patcher)
                    proof=stage.run(args)
                popen.assert_not_called();firewall.assert_not_called();cleanup.assert_called_once()
                self.assertEqual(proof['failure'],'candidate_x86_sql_not_ready')
                self.assertFalse(proof['passed']);self.assertFalse(proof['candidate_started'])
                self.assertTrue(proof['owned_localdb_cleanup_complete']);self.assertTrue(proof['private_files_removed'])

    def test_exact_intact_reviewed_pins_required(self):
        with self.assertRaisesRegex(ValueError,'intact_reviewed_hashes_required'):
            stage.admit_intact(Path('unused'),'0'*64,stage.INTACT_BINARY_SHA,ROOT)

    def test_exception_redaction(self):
        self.assertEqual(stage.safe_failure(ValueError('packet bytes or private rows')), 'ValueError')
        self.assertEqual(stage.safe_failure(ValueError('known_symbolic_failure')), 'known_symbolic_failure')
        self.assertEqual(stage.safe_failure(subprocess.TimeoutExpired(['private-command'],25)), 'TimeoutExpired')


if __name__ == '__main__':
    unittest.main()

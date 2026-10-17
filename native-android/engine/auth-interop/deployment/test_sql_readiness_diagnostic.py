"""Readiness diagnostic admission/redaction controls; no Windows or service."""
import copy
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import sql_readiness_diagnostic as stage
from test_auth_readiness import fixture

INSTANCE='cohauth-ci-'+'a'*24
PIPE=r'np:\\.\pipe\LOCALDB#ABC123\tsql\query'


class DiagnosticTests(unittest.TestCase):
    def test_exact_owned_local_pipe_only(self):
        self.assertEqual(stage.pipe_from_info('Private runner user\nInstance pipe name: '+PIPE+'\n'),PIPE)
        for value in ('',PIPE+'\n'+PIPE,r'np:\\remote\pipe\LOCALDB#ABC\tsql\query',r'np:\\.\pipe\other\tsql\query'):
            with self.assertRaises(ValueError):stage.pipe_from_info(value)

    def test_variants_keep_security_query_and_three_connections(self):
        original=stage.auth_readiness.script(INSTANCE)
        for architecture in (32,64):
            for database in ('master','cohauth'):
                for endpoint in ('(localdb)\\'+INSTANCE,PIPE):
                    result=stage.observer_script(INSTANCE,endpoint,architecture,database)
                    self.assertIn('Trusted_Connection=Yes;Encrypt=No;',result)
                    self.assertIn('$i -lt 3',result)
                    self.assertIn("SERVERPROPERTY('ProcessID')",result)
                    expected=original.replace('Server=(localdb)\\'+INSTANCE+';Database=cohauth;', 'Server='+endpoint+';Database='+database+';').replace('[IntPtr]::Size -ne 4','[IntPtr]::Size -ne '+str(architecture//8))
                    self.assertEqual(result,expected)
        for args in [('invalid',PIPE,32,'master'),(INSTANCE,'remote',32,'master'),(INSTANCE,PIPE,16,'master'),(INSTANCE,PIPE,32,'private')]:
            with self.assertRaises(ValueError):stage.observer_script(*args)

    def test_log_redaction_numeric_bounds_and_utf16(self):
        text='private account and connection string\nError: 17803, Severity: 20, State: 17.\nSQL Server is terminating\ninsufficient system memory'
        for encoding in ('utf-8','utf-16-le'):
            result=stage.classify_errorlog(text.encode(encoding))
            self.assertTrue(result['termination_marker']);self.assertTrue(result['insufficient_memory_marker'])
            self.assertEqual(result['numeric_errors'],[{'number':17803,'severity':20,'state':17}])
            self.assertFalse(result['content_exported']);self.assertNotIn('private',json.dumps(result))
        with self.assertRaises(ValueError):stage.classify_errorlog(b'x'*(2*1024*1024+1))
        self.assertEqual(len(stage.classify_errorlog(('Error: 233, Severity: 20, State: 0.\n'*100).encode())['numeric_errors']),64)

    def test_architecture_observer_and_no_exception_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('SysWOW64','System32'):
                path=root/name/'WindowsPowerShell/v1.0/powershell.exe';path.parent.mkdir(parents=True);path.write_bytes(b'fixture')
            for architecture in (32,64):
                value=fixture();value['pointer_bytes']=architecture//8
                with patch.dict(stage.os.environ,{'WINDIR':temp}), patch.object(stage.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(value).encode())) as run:
                    proof=stage.observe(INSTANCE,PIPE,architecture,'cohauth',123)
                    self.assertTrue(proof['healthy']);self.assertEqual(proof['observation']['pointer_bytes'],architecture//8)
                    self.assertEqual(run.call_args.kwargs['timeout'],50)
                value['pointer_bytes']=16
                with patch.dict(stage.os.environ,{'WINDIR':temp}),patch.object(stage.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(value).encode())):
                    with self.assertRaises(ValueError):stage.observe(INSTANCE,PIPE,architecture,'cohauth',123)

    def test_private_commands_suppress_failures_and_cleanup_still_finishes(self):
        with tempfile.TemporaryDirectory() as temp:
            records=[];private=stage.RedactedCommands(records,Path(temp))
            command=[sys.executable,'-c',"import sys;print('private user');print('private driver',file=sys.stderr);sys.exit(1)"]
            with self.assertRaises(ValueError):private.run('localdb-memory-bound',command,timeout=5)
            self.assertNotIn('private user',json.dumps(records));self.assertEqual(list(Path(temp).iterdir()),[])
            responses=[SimpleNamespace(returncode=1),SimpleNamespace(returncode=0),SimpleNamespace(returncode=0)]
            with patch.object(stage.subprocess,'run',side_effect=responses) as run:
                self.assertFalse(stage.prior.cleanup_owned_instance(private,Path('sqlcmd'),Path('localdb'),INSTANCE))
                self.assertEqual(run.call_count,3)
                for call in run.call_args_list:
                    self.assertEqual(call.kwargs['stdout'],stage.subprocess.DEVNULL)
                    self.assertEqual(call.kwargs['stderr'],stage.subprocess.DEVNULL)

    def test_private_numeric_query_refuses_text_and_oversized_output(self):
        with tempfile.TemporaryDirectory() as temp:
            records=[];private=stage.RedactedCommands(records,Path(temp))
            self.assertEqual(private.numeric('localdb-pid',[sys.executable,'-c',"print('123')"],'pid',5),123)
            self.assertEqual(private.numeric('localdb-version',[sys.executable,'-c',"print('17.0.4025.3')"],'version',5),'17.0.4025.3')
            for text in ('private user/driver text', '0', '4294967296', 'x'*9000):
                with self.assertRaises(ValueError):private.numeric('localdb-pid',[sys.executable,'-c','print('+repr(text)+')'],'pid',5)
            self.assertEqual(list(Path(temp).iterdir()),[])
            self.assertNotIn('private user',json.dumps(records));self.assertNotIn('x'*100,json.dumps(records))

    def test_final_source_observation_failure_preserves_redacted_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);args=SimpleNamespace(memory_limit_mb=256,source_root=root,output=root/'out',expected_commit='0'*40)
            with patch.dict(stage.os.environ,{'RUNNER_TEMP':temp}), \
                 patch.object(stage.prior,'require_hosted',return_value={}), \
                 patch.object(stage.service,'tools',side_effect=ValueError('setup_refused')), \
                 patch.object(stage.prior,'capture',side_effect=RuntimeError('private source user')):
                proof=stage.run(args)
            self.assertFalse(proof['passed']);self.assertFalse(proof['source_inputs_unchanged'])
            self.assertTrue(proof['source_status_observation_failed']);self.assertTrue((args.output/'receipt.json').is_file())
            self.assertNotIn('private source user',(args.output/'receipt.json').read_text())

    def test_overall_deadline_stops_new_children_but_cleanup_can_run(self):
        with tempfile.TemporaryDirectory() as temp:
            private=stage.RedactedCommands([],Path(temp),deadline=0)
            with patch.object(stage.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'sql_diagnostic_experiment_deadline'):
                    private.run('memory',[],timeout=1)
                run.assert_not_called()
                private.deadline=None;run.return_value=SimpleNamespace(returncode=0)
                private.run('cleanup',[],timeout=1);run.assert_called_once()

    def test_no_service_entrypoint_and_memory_choices(self):
        text=Path(stage.__file__).read_text()
        self.assertIn('process=subprocess.Popen(list(map(str,command)),stdout=stream,stderr=subprocess.DEVNULL)',text)
        self.assertNotIn('service.run(',text)
        self.assertNotIn('AuthServer.exe',text)
        with self.assertRaisesRegex(ValueError,'diagnostic_memory_policy'):
            stage.run(SimpleNamespace(memory_limit_mb='256;arbitrary'))


if __name__=='__main__':unittest.main()

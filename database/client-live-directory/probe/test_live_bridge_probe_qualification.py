"""Actual host ownership/failure controls and synthetic strict receipt guards.

These are not native Windows controls, runtime or provider authority.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import qualify_live_bridge_probe_windows as qualifier
import parse_live_bridge_probe as parser
from test_live_bridge_probe_parser import packet,row


def good_record():
    raw=packet(row())
    parsed=parser.parse(raw)
    return {'held_native_pid':12,'returncode':0,'execution_error':None,'stdout':
            'COH_NT_PROBE_RESULT pid=12 mode=1 complete=1 rows=1 batches=1 input_cleanup_failed=0 bytes='+str(len(raw))+'\n',
            'stderr':'','packet':{'bytes':len(raw),'sha256':'controlled'},'parsed':parsed,
            'process_cleanup':{'held_pid':12,'returncode':0,'closed_exact_owned_child':True,'forced_termination':False}}


class QualificationControls(unittest.TestCase):
    def test_console_mode_pid_counts_cleanup_and_bytes_bind_exact_current_packet(self):
        qualifier.genuine_result(good_record(),1,True)
        original=good_record()
        for old,new in (('pid=12','pid=13'),('mode=1','mode=2'),('rows=1','rows=2'),
                        ('batches=1','batches=2'),('input_cleanup_failed=0','input_cleanup_failed=1'),
                        ('bytes=','unknown_bytes=')):
            value=copy.deepcopy(original);value['stdout']=value['stdout'].replace(old,new)
            with self.assertRaises(ValueError):
                qualifier.genuine_result(value,1,True)
        value=copy.deepcopy(original);value['stdout']*=2
        with self.assertRaises(ValueError):
            qualifier.genuine_result(value,1,True)

    def test_held_pid_forced_termination_execution_error_or_unclosed_streams_cannot_pass(self):
        for target,field,value in (('outer','held_native_pid',13),('outer','execution_error','timeout'),
                                   ('cleanup','closed_exact_owned_child',False),('cleanup','forced_termination',True),
                                   ('cleanup','returncode',1),('cleanup','held_pid',13)):
            record=good_record()
            (record if target=='outer' else record['process_cleanup'])[field]=value
            with self.assertRaises(ValueError):
                qualifier.genuine_result(record,1,True)

    def test_timeout_retains_partial_stdout_stderr_and_reaps_exact_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            value=qualifier.execute(sys.executable,('-u','-c',
                'import sys,time;print("partial native output",flush=True);print("partial stderr",file=sys.stderr,flush=True);time.sleep(30)'),
                Path(temporary)/'absent.bin',timeout=0.3)
            self.assertIn('partial native output',value['stdout'])
            self.assertIn('partial stderr',value['stderr'])
            self.assertIsNotNone(value['execution_error'])
            self.assertTrue(value['termination_requested_after_timeout'])
            self.assertTrue(value['process_cleanup']['closed_exact_owned_child'])
            self.assertEqual(value['process_cleanup']['held_pid'],value['held_native_pid'])
            self.assertIsNotNone(value['returncode'])
            with self.assertRaises(ProcessLookupError):
                os.kill(value['held_native_pid'],0)

    def test_partial_packet_parse_failure_preserves_raw_pin_and_child_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            packet_path=Path(temporary)/'partial.bin'
            packet_path.write_bytes(b'partial-native-evidence')
            value=qualifier.execute(sys.executable,('-c','print("partial console")'),packet_path)
            self.assertEqual(value['packet'],qualifier.pin(packet_path))
            self.assertIsNotNone(value['packet_parse_error'])
            self.assertIsNone(value['parsed'])
            self.assertTrue(value['process_cleanup']['closed_exact_owned_child'])

    def test_workflow_relative_output_is_absolute_and_failed_assertion_has_durable_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous=Path.cwd()
            os.chdir(temporary)
            try:
                binary=Path('probe.exe');binary.write_bytes(b'controlled fake source only')
                seen=[]
                def failed(binary,args,output):
                    seen.extend(map(Path,args[1:]))
                    return {'stdout':'available current failure','stderr':'failure stderr',
                            'returncode':1,'parsed':None,'packet':None,'held_native_pid':123,
                            'execution_error':None,'process_cleanup':{'closed_exact_owned_child':True}}
                with patch.object(qualifier,'require_windows'),patch.object(qualifier,'execute',side_effect=failed):
                    with self.assertRaises(ValueError):
                        qualifier.qualify(binary,Path('out/windows-probe'),'a'*40)
                self.assertTrue(all(path.is_absolute() for path in seen))
                value=json.loads(Path('out/windows-probe/windows-controls.json').read_text())
                self.assertEqual(value['status'],'failed')
                self.assertEqual(value['repository_commit'],'a'*40)
                self.assertEqual(value['probe_source'],qualifier.source_pins())
                self.assertEqual(value['cases']['actual_stock_multibuffer']['stdout'],'available current failure')
                self.assertIn('Current held native PID',value['failure'])
                self.assertFalse(value['Game_executed'])
            finally:
                os.chdir(previous)

    def test_failed_start_has_no_fabricated_owned_pid_or_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            value=qualifier.execute(Path(temporary)/'absent',(),Path(temporary)/'absent.bin')
            self.assertIsNone(value['held_native_pid'])
            self.assertIsNone(value['process_cleanup'])
            self.assertIsNotNone(value['execution_error'])

    def test_sharing_readiness_failure_reaps_child_and_finalizes_partial_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            calls=[]
            def fixture_execute(binary,args,output):
                calls.append(args)
                Path(output).write_bytes(b'controlled packet evidence')
                return {'stdout':'controlled source-only fixture','stderr':'','execution_error':None,
                        'returncode':0 if len(calls)==1 else 65,
                        'process_cleanup':{'closed_exact_owned_child':True},
                        'parsed':{'batches':[{},{}],'rows':[{'name':f'fixture_{n:03d}_'+('x'*70)+'.fx'} for n in range(200)]}}
            output=Path(temporary)/'sdk'
            # Python is deliberately not the SDK probe; its wrong readiness must
            # fail. The test exercises real exact-child reaping and finalization.
            with patch.object(qualifier,'require_windows'),patch.object(qualifier,'execute',side_effect=fixture_execute),\
                 patch.object(qualifier,'genuine_result'):
                with self.assertRaises(ValueError):
                    qualifier.qualify(sys.executable,output,'b'*40)
            report=json.loads((output/'windows-controls.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertEqual(report['fresh_native_control_groups'],2)
            held=report['cases']['native_share_refusal_and_owned_release']['held']
            self.assertIsNotNone(held['execution_error'])
            self.assertTrue(held['readiness_observer_stopped'])
            self.assertTrue(held['process_cleanup']['closed_exact_owned_child'])
            self.assertEqual(held['held_native_pid'],held['process_cleanup']['held_pid'])
            self.assertIn("can't open file",held['stderr'])


if __name__=='__main__':
    unittest.main()

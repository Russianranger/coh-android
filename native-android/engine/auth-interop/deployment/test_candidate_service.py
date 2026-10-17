"""Candidate admission and orchestration fixtures; no service/crypto execution."""
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
import zipfile

import candidate_service as candidate
import hosted_auth_login as login
from test_auth_login_stage import fixture

ROOT = Path(__file__).resolve().parents[4]


class CandidateServiceTests(unittest.TestCase):
    def test_explicit_candidate_cli_requires_all_exact_reuse_inputs(self):
        base=['hosted_auth_login.py','--source-root','.', '--expected-commit','0'*40,'--output','new',
              '--reuse-auth-stage','original','--reuse-odbc-stage','odbc']
        options=['--receive-candidate-stage','candidate','--candidate-receipt-sha256','1'*64,
                 '--candidate-binary-sha256','2'*64,'--reuse-intact-stage','intact','--reuse-probe-stage','fragmented']
        with patch.object(sys,'argv',base+options), patch.object(login.prior,'require_hosted',side_effect=RuntimeError('hosted_boundary')) as boundary:
            with self.assertRaisesRegex(RuntimeError,'hosted_boundary'):login.main()
            boundary.assert_called_once()
        for removed in ('--receive-candidate-stage','--candidate-receipt-sha256','--candidate-binary-sha256','--reuse-intact-stage','--reuse-probe-stage'):
            bad=options.copy();at=bad.index(removed);del bad[at:at+2]
            with patch.object(sys,'argv',base+bad), patch.object(login.prior,'require_hosted') as boundary:
                with self.assertRaises(ValueError,msg=removed):login.main()
                boundary.assert_not_called()
        for extra in (['--openssl-archive','openssl.tar.gz'],['--intact-baseline']):
            with patch.object(sys,'argv',base+options+extra), patch.object(login.prior,'require_hosted') as boundary:
                with self.assertRaises(ValueError):login.main()
                boundary.assert_not_called()

    def test_all_eight_cases_require_owned_service_and_exact_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);proof={};checks=[];commands=[]
            class Runner:
                def run(self,name,command,**kwargs):
                    commands.append((name,command));(directory/(name+'.log')).write_text(json.dumps(fixture(command[-1])))
            with patch.object(login,'private_logs_bounded'):
                candidate.run_probes(proof,Runner(),{'fragmented_7':Path('seven.exe'),'normal_1024':Path('normal.exe')},21001,directory,directory,lambda:checks.append(1))
            self.assertEqual(len(commands),8);self.assertEqual(len(checks),16)
            self.assertEqual(proof['encrypted_login_schedules'],{'fragmented_7':True,'normal_1024':True})
            self.assertTrue(proof['fragmented_and_normal_suite_complete']);self.assertFalse(proof['general_tcp_segmentation_accepted'])
            for schedule in ('fragmented_7','normal_1024'):
                self.assertEqual(set(proof['candidate_schedule_results'][schedule]),set(login.CASES))

    def test_later_failure_retains_real_positive_but_never_complete_suite(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);proof={}
            class Runner:
                def run(self,name,command,**kwargs):
                    result=fixture(command[-1])
                    if command[-1]=='wrong-password':result['failure_reason']=2
                    (directory/(name+'.log')).write_text(json.dumps(result))
            with patch.object(login,'private_logs_bounded'), self.assertRaises(ValueError):
                candidate.run_probes(proof,Runner(),{'fragmented_7':Path('seven.exe'),'normal_1024':Path('normal.exe')},21001,directory,directory,lambda:None)
            self.assertTrue(proof['encrypted_account_login_verified'])
            self.assertFalse(proof.get('fragmented_and_normal_suite_complete',False))
            self.assertEqual(proof['encrypted_login_schedules'],{'fragmented_7':True})

    def test_owned_listener_loss_stops_probe_before_execution(self):
        def refused():raise ValueError('not_owned')
        with patch.object(login,'private_logs_bounded'), self.assertRaises(ValueError):
            candidate.run_probes({},None,{'fragmented_7':Path('seven.exe'),'normal_1024':Path('normal.exe')},21001,Path('/tmp'),Path('/tmp'),refused)

    def test_readiness_preserves_numeric_failure_and_rejects_repeats(self):
        proof={};bad={'healthy':False,'observation':{'errors':[{'sqlstate':'08001','native_error':53}]}}
        with patch.object(candidate.auth_readiness,'observe',return_value=bad), self.assertRaises(ValueError):
            candidate.observe_sql(proof,'before_authserver','cohauth-ci-'+'a'*24,100)
        self.assertEqual(proof['independent_x86_odbc_readiness']['before_authserver'],bad)
        with self.assertRaises(ValueError):candidate.observe_sql(proof,'before_authserver','cohauth-ci-'+'a'*24,100)
        with patch.object(candidate.auth_readiness,'observe',side_effect=RuntimeError('private driver data')), self.assertRaises(ValueError):
            candidate.observe_sql(proof,'during_readiness','cohauth-ci-'+'a'*24,100)
        self.assertNotIn('private driver data',json.dumps(proof))

    @unittest.skipUnless(os.environ.get('COH_INTACT_REUSE_ZIP'),'Exact historical artifact not supplied')
    def test_actual_intact_artifact_and_every_mutation(self):
        pins=json.loads((candidate.HERE/'intact-build-reuse-pins.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            with zipfile.ZipFile(os.environ['COH_INTACT_REUSE_ZIP']) as archive:
                for name in pins['files']:
                    path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(name))
            result=candidate.admit_intact(directory,ROOT)
            self.assertFalse(result['prior_login_inherited']);self.assertFalse(result['crypto_rebuilt'])
            for name in pins['files']:
                path=directory/name;data=path.read_bytes();path.write_bytes(data+b'x')
                with self.assertRaises(ValueError,msg=name):candidate.admit_intact(directory,ROOT)
                path.write_bytes(data)

    @unittest.skipUnless(os.environ.get('COH_CANDIDATE_BUILD_ZIP'),'Exact compiled candidate artifact not supplied')
    def test_actual_candidate_copy_admission_and_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);stage=directory/'stage';stage.mkdir()
            with zipfile.ZipFile(os.environ['COH_CANDIDATE_BUILD_ZIP']) as archive:archive.extractall(stage)
            destination=directory/'AuthServer.exe'
            receipt='25ee2415a280e7b3800808824d95d05b862acca9d4d4879f5fccb5605d6a2451'
            binary='9cd262dd862d14bf2d696de65cb70f155f25473503d7fd0968de9969e0ac8003'
            result=candidate.copy_candidate(stage,receipt,binary,destination)
            self.assertEqual(result['binary']['sha256'],binary)
            with self.assertRaises(ValueError):candidate.copy_candidate(stage,receipt,'0'*64,destination)


if __name__=='__main__':unittest.main()

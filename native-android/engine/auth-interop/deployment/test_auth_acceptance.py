"""Actual completed auth prerequisite plus mutation refusals; no service run."""
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import verify_auth_acceptance as stage

ROOT=Path(__file__).resolve().parents[4]
ARCHIVE=Path('/tmp/auth-38996587760.zip')
# The committed copy makes these controls runnable in fresh source-only CI.
RETAINED=ROOT/'native-android/engine/auth-interop/evidence/auth-success-38996587760/artifact.zip'


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.archive=RETAINED if RETAINED.exists() else ARCHIVE
        self.receipt=json.loads(zipfile.ZipFile(self.archive).read('receipt.json'))

    def test_exact_real_receipt_and_source_binary_chain(self):
        proof=stage.verify(ROOT,self.archive)
        self.assertEqual(proof['actual_normal_and_capped_cases'],8)
        self.assertTrue(proof['complete_owned_cleanup'])
        self.assertFalse(proof['authenticated_db_map_handoff_verified'])
        self.assertFalse(proof['new_service_execution'])

    def test_every_case_and_source_cleanup_scope_mutation_refused(self):
        for mode in ('normal','capped'):
            for case in stage.login.CASES:
                value=copy.deepcopy(self.receipt);value['probe_results'][mode][case]['passed']=False
                with self.assertRaises(ValueError):stage.admit_receipt(value)
                value=copy.deepcopy(self.receipt);value['probe_results'][mode][case]['protocol']-=1
                with self.assertRaises(ValueError):stage.admit_receipt(value)
        for flag in ('owned_authserver_job_stop_complete','owned_authserver_listeners_absent','owned_authserver_cleanup_complete','owned_firewall_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged','no_binary_rebuilt'):
            value=copy.deepcopy(self.receipt);value[flag]=False
            with self.assertRaises(ValueError,msg=flag):stage.admit_receipt(value)
        for flag in ('authenticated_db_map_handoff_verified','shipping_server_modified','general_tcp_segmentation_accepted','receiver_segmentation_controlled'):
            value=copy.deepcopy(self.receipt);value[flag]=True
            with self.assertRaises(ValueError,msg=flag):stage.admit_receipt(value)

    def test_missing_modes_wrong_negatives_or_binary_pins_refused(self):
        for mode in ('normal','capped'):
            for case in stage.login.CASES:
                value=copy.deepcopy(self.receipt);del value['probe_results'][mode][case]
                with self.assertRaises(ValueError):stage.admit_receipt(value)
            for case in ('wrong-password','missing-account'):
                value=copy.deepcopy(self.receipt);value['probe_results'][mode][case]['failure_reason']=99
                with self.assertRaises(ValueError):stage.admit_receipt(value)
        for group,key in (('candidate_admission','binary'),('normal_probe_admission','binary'),('capped_probe_admission','native_probe')):
            value=copy.deepcopy(self.receipt);value[group][key]['sha256']='0'*64
            with self.assertRaises(ValueError):stage.admit_receipt(value)
        value=copy.deepcopy(self.receipt);value['repository_commit']='0'*40
        with self.assertRaises(ValueError):stage.admit_receipt(value)

    def test_changed_generation_or_fresh_sql_connection_refused(self):
        value=copy.deepcopy(self.receipt);value['owned_sql_after_auth_stop']['started_utc_ticks']+=1
        with self.assertRaises(ValueError):stage.admit_receipt(value)
        value=copy.deepcopy(self.receipt);value['x86_readiness_before_start']['observation']['opened_connections']=2
        with self.assertRaises(ValueError):stage.admit_receipt(value)
        value=copy.deepcopy(self.receipt);next(r for r in value['commands'] if r['name']=='localdb-drop-owned-schema')['returncode']=1
        with self.assertRaises(ValueError):stage.admit_receipt(value)
        with tempfile.TemporaryDirectory() as temp:
            changed=Path(temp)/'artifact.zip';changed.write_bytes(self.archive.read_bytes()+b'x')
            with self.assertRaises(ValueError):stage.verify(ROOT,changed)

    def test_immutable_prerequisite_requires_fresh_auth_and_no_dbid(self):
        prerequisite=stage.authenticated_handoff_prerequisite(ROOT,self.archive)
        self.assertTrue(prerequisite.fresh_authentication_required)
        self.assertFalse(prerequisite.historical_session_reusable)
        self.assertIsNone(prerequisite.selected_character_dbid)
        self.assertFalse(prerequisite.authenticated_db_map_handoff_verified)
        self.assertIsInstance(prerequisite.source_pins,tuple)
        with self.assertRaises(FrozenInstanceError):prerequisite.authenticated_db_map_handoff_verified=True


if __name__=='__main__':unittest.main()

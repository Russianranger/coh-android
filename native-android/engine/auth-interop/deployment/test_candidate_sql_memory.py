"""Actual prerequisite receipt admission; no live SQL or AuthServer execution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import candidate_sql_memory as stage

RECEIPT=stage.HERE.parent/'evidence/sql-readiness-1024-38995104446/receipt.json'


class MemoryProfileTests(unittest.TestCase):
    def test_actual_all_sixteen_and_seed_cleanup_are_admitted(self):
        result=stage.select(1024)
        self.assertEqual(result['healthy_transport_observations'],16)
        self.assertTrue(result['fresh_x86_readiness_still_required'])
        self.assertFalse(result['prior_authentication_inherited'])

    def test_default256_does_not_inherit_or_read1024(self):
        with patch.object(stage,'admit_receipt') as admit:
            self.assertEqual(stage.select(256)['sql_memory_limit_mb'],256)
            admit.assert_not_called()
        for value in (True,False,None,'1024',0,512,2048):
            with self.assertRaises(ValueError):stage.select(value)

    def assert_rejected(self,value):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'receipt.json';path.write_text(json.dumps(value))
            # Re-pin the mutated fixture to exercise semantic admission as well
            # as the independently tested immutable real receipt hash boundary.
            with patch.object(stage,'RECEIPT_SHA',hashlib.sha256(path.read_bytes()).hexdigest()):
                with self.assertRaises(ValueError):stage.admit_receipt(path)

    def test_receipt_identity_and_top_level_scope_refused(self):
        value=json.loads(RECEIPT.read_text())
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'receipt.json';path.write_bytes(RECEIPT.read_bytes()+b' ')
            with self.assertRaises(ValueError):stage.admit_receipt(path)
        for key,altered in [('passed',False),('experiment_completed',False),('memory_limit_mb',256),
                ('authserver_started',True),('encrypted_account_login_verified',True),
                ('owned_localdb_cleanup_complete',False),('private_files_removed',False),
                ('source_inputs_unchanged',False),('localdb_version','16.0'),('service_guard_disabled',True)]:
            changed=copy.deepcopy(value);changed[key]=altered;self.assert_rejected(changed)

    def test_every_transport_must_match_actual_process_and_three_connections(self):
        value=json.loads(RECEIPT.read_text())
        for phase in range(4):
            for transport in range(4):
                changed=copy.deepcopy(value);changed['observations'][phase]['transports'][transport]['healthy']=False;self.assert_rejected(changed)
                changed=copy.deepcopy(value);changed['observations'][phase]['transports'][transport]['observation']['opened_connections']=2;self.assert_rejected(changed)
                changed=copy.deepcopy(value);changed['observations'][phase]['transports'][transport]['observation']['sql_process_id']+=1;self.assert_rejected(changed)
        changed=copy.deepcopy(value);changed['observations'][0]['transports'][0]['architecture_bits']=64;self.assert_rejected(changed)
        changed=copy.deepcopy(value);changed['observations'].pop();self.assert_rejected(changed)

    def test_memory_errors_seed_cleanup_and_generation_refused(self):
        value=json.loads(RECEIPT.read_text())
        for phase in range(4):
            changed=copy.deepcopy(value);changed['observations'][phase]['sql_errorlog']['insufficient_memory_marker']=True;self.assert_rejected(changed)
            changed=copy.deepcopy(value);changed['observations'][phase]['process_after']['started_utc_ticks']+=1;self.assert_rejected(changed)
        for name in ('original-schema-private','public-seed-private-credential','public-seed-private-account','localdb-drop-owned-schema','localdb-stop-owned-instance','localdb-delete-owned-instance'):
            changed=copy.deepcopy(value)
            next(r for r in changed['commands'] if r['name']==name)['returncode']=1
            self.assert_rejected(changed)


if __name__=='__main__':unittest.main()

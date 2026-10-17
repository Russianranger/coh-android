#!/usr/bin/env python3
"""Privacy controls for fixed public status extraction; no server capture."""
import copy,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
import sys
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('groups_public_summary',HERE/'summarize_groups_capture.py')
summary=importlib.util.module_from_spec(spec);spec.loader.exec_module(summary)
SECRET='CANARY-account-packet-log-exception-7d6bc70a'
def receipt():
    pair={'schema':'coh-original-native-groups-pair-v1','passed':True,
          'source_run_provenance_verified':False,'cache_equivalence_verified':False,
          'source_generation_admitted':False,'actor_identity_verified':False,'world_authority':False,
          **{key:True for key in summary.PAIR}}
    return {'schema':'coh-private-original-native-groups-run-v1','passed':True,'private_character_state':True,
            'public_upload_permitted':False,'local_development_auth':True,'authserver_authenticated':False,
            'source_generation_admitted':False,'world_authority':False,'pair':pair,
            'capture_stage':'COMPLETE','failure_stage':'NONE',
            **{name:True for name in summary.STATUS}}
class Controls(unittest.TestCase):
    def test_passed_exact_allowlist(self):
        result=summary.summarize(receipt());self.assertTrue(result['passed'])
        self.assertEqual(set(result),set(summary.empty('NONE')))
        self.assertEqual(result['failure_code'],'NONE');self.assertFalse(result['world_authority'])
    def test_every_status_is_strict_bool(self):
        for key in (*summary.STATUS,'passed','private_character_state','public_upload_permitted',
                    'local_development_auth','authserver_authenticated','source_generation_admitted','world_authority'):
            value=receipt();value[key]=int(value[key])
            with self.subTest(key=key),self.assertRaises(summary.Refused):summary.summarize(value)
        for key in summary.STATUS:
            value=receipt();value.pop(key)
            with self.subTest(missing=key),self.assertRaises(summary.Refused):summary.summarize(value)
        for key in summary.PAIR:
            value=receipt();value['pair'][key]=1
            with self.subTest(pair=key),self.assertRaises(summary.Refused):summary.summarize(value)
    def test_wrong_schema_or_authority_refused(self):
        for key,item in [('schema',SECRET),('source_generation_admitted',True),('world_authority',True),
                         ('public_upload_permitted',True),('authserver_authenticated',True)]:
            value=receipt();value[key]=item
            with self.subTest(key=key),self.assertRaises(summary.Refused):summary.summarize(value)
        for key in ('actor_identity_verified','world_authority','source_generation_admitted','source_run_provenance_verified'):
            value=receipt();value['pair'][key]=True
            with self.subTest(pair=key),self.assertRaises(summary.Refused):summary.summarize(value)
    def test_private_canaries_never_serialized(self):
        value=receipt()
        for name in ('failure_code','failure_type','account','dump','source_sha256','run_identity_sha256',
                     'native_tool','private_path','source_envelope','native_packet','raw_log','exception'):
            value[name]={'raw':SECRET,'nested':[SECRET]}
            value['pair'][name]={'raw':SECRET}
        result=summary.summarize(value);self.assertNotIn(SECRET,json.dumps(result))
        value['passed']=False;value['failure_code']=SECRET;value['failure_stage']='PAIR_VERIFY';value['capture_stage']='CLEANUP'
        result=summary.summarize(value);self.assertEqual(result['failure_code'],'SOURCE_CAPTURE_NOT_ACCEPTED')
        self.assertNotIn(SECRET,json.dumps(result))
    def test_failed_partial_receipt(self):
        value=receipt();value['passed']=False;value['capture_stage']='CLEANUP';value['failure_stage']='WINE_BOOT'
        for name in summary.STATUS:value.pop(name)
        value.pop('pair');result=summary.summarize(value)
        self.assertFalse(result['passed']);self.assertFalse(result['runtime_executed'])
        self.assertEqual(result['failure_code'],'SOURCE_CAPTURE_NOT_ACCEPTED')
    def test_fixed_stage_names_only(self):
        from groups_capture_stages import advance,CAPTURE_STAGES
        value=receipt();value['passed']=False
        for stage in CAPTURE_STAGES[:-1]:
            advance(value,stage);value['failure_stage']=stage
            self.assertEqual(summary.summarize(value)['failure_stage'],stage)
        for name in ('capture_stage','failure_stage'):
            broken=receipt();broken[name]=SECRET
            with self.subTest(field=name),self.assertRaises(summary.Refused):summary.summarize(broken)
        with self.assertRaises(ValueError):advance(value,SECRET)
    def test_absent_malformed_and_exception_fixed_failures(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);private=root/'private';private.mkdir(mode=0o700)
            with patch.object(summary,'committed_helper',return_value=('a'*40,'b'*64)):
                result=summary.emit(private,root/'absent.json');self.assertEqual(result['failure_code'],'PRIVATE_RECEIPT_ABSENT')
                receipt_path=private/'capture-receipt.json';receipt_path.write_text('{'+SECRET);receipt_path.chmod(0o600)
                result=summary.emit(private,root/'malformed.json');self.assertEqual(result['failure_code'],'PRIVATE_RECEIPT_INVALID')
                self.assertNotIn(SECRET,(root/'malformed.json').read_text())
                with patch.object(summary,'private_receipt',side_effect=OSError(SECRET)):
                    result=summary.emit(private,root/'exception.json')
                self.assertNotIn(SECRET,(root/'exception.json').read_text())
                receipt_path.write_text(json.dumps(receipt()))
                result=summary.emit(private,root/'passed.json');self.assertTrue(result['passed'])
                with self.assertRaises(summary.Refused):summary.emit(private,root/'passed.json')
    def test_links_shared_mode_and_duplicate_keys_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'capture-receipt.json';path.write_text(json.dumps(receipt()));path.chmod(0o600)
            self.assertTrue(summary.private_receipt(root)['passed'])
            path.chmod(0o644)
            with self.assertRaises(summary.Refused):summary.private_receipt(root)
            path.chmod(0o600);path.write_text('{"schema":"one","schema":"two"}')
            with self.assertRaises(summary.Refused):summary.private_receipt(root)
            path.unlink();other=root/'other';other.write_text(json.dumps(receipt()));other.chmod(0o600);path.symlink_to(other)
            with self.assertRaises(summary.Refused):summary.private_receipt(root)
if __name__=='__main__':unittest.main(verbosity=2)

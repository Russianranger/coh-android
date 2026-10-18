"""New source-composition admission controls only. No C/compiler/old suite/runtime."""
import ast
import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import hosted_auth_db_development as stage

ROOT=Path(__file__).resolve().parents[4]
RUN_RECORDS={}


def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL)


def commit(root):
    git(root,'add','.');git(root,'-c','user.name=Admission control','-c','user.email=control@invalid',
        'commit','-qm','controlled source fixture')
    return git(root,'rev-parse','HEAD').decode().strip()


def write(root,name,body):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)


class AccountControlsAdmissionTests(unittest.TestCase):
    def test_exact_new_c99_proof_and_all36_inputs_require_current_owned_bytes(self):
        inputs=stage.account_controls_inputs(ROOT);self.assertEqual(len(inputs),38)
        raw=gzip.decompress((ROOT/(stage.ACCOUNT_BASE+'.json.gz')).read_bytes());proof=json.loads(raw)
        self.assertEqual(set(proof['modes']),{'release','asan','ubsan'})
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);git(root,'init','-q')
            for path in inputs:write(root,path,(ROOT/path).read_bytes())
            commit(root);self.assertEqual(stage.account_controls_inputs(root),inputs)
            for path in (*stage.ACCOUNT_CURRENT_CORE,'native-android/engine/dbclient/coh_db_account_controls.c',
                    'native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c',
                    stage.ACCOUNT_BASE+'.json.gz',stage.ACCOUNT_BASE+'-binding.json'):
                original=(root/path).read_bytes();(root/path).write_bytes(original+b'\nCHANGED_CONTROL')
                with self.subTest(path=path),self.assertRaises(ValueError):stage.account_controls_inputs(root)
                (root/path).write_bytes(original)
            p=stage.ACCOUNT_BASE+'.json.gz';saved=(root/p).read_bytes();(root/p).unlink();commit(root)
            with self.assertRaises(ValueError):stage.account_controls_inputs(root)
            write(root,p,saved)
            # Matching untracked bytes do not satisfy current HEAD ownership.
            with self.assertRaises(ValueError):stage.account_controls_inputs(root)
        with mock.patch.object(stage.gzip,'decompress',return_value=b'{}'),self.assertRaisesRegex(ValueError,'proof_identity'):
            stage.account_controls_inputs(ROOT)
        RUN_RECORDS['c99_source_qualification_reused']={'gzip_sha256':stage.ACCOUNT_GZIP_SHA,
            'source_inputs':36,'modes':{name:{k:row[k] for k in ('checks','parser_cases','session_transactions')}
                for name,row in proof['modes'].items()},'qualifier_reexecuted':False}

    def test_only_two_exact_old_core_pins_may_resolve_to_frozen_new_source(self):
        current=stage.account_controls_inputs(ROOT)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);git(root,'init','-q')
            for path in stage.ACCOUNT_OLD_CORE:
                write(root,path,git(ROOT,'show',stage.ACCOUNT_HISTORICAL_REVISION+':'+path))
            historical=commit(root)
            for path in stage.ACCOUNT_CURRENT_CORE:write(root,path,(ROOT/path).read_bytes())
            commit(root)
            with mock.patch.object(stage,'ACCOUNT_HISTORICAL_REVISION',historical):
                for path,old in stage.ACCOUNT_OLD_CORE.items():
                    self.assertEqual(stage.qualified_prior_input(root,path,old,current),(ROOT/path).read_bytes())
                    with self.assertRaises(ValueError):stage.qualified_prior_input(root,path,'0'*64,current)
                    with self.assertRaises(ValueError):stage.qualified_prior_input(root,path,old,dict(current,**{path:'0'*64}))
                    with mock.patch.object(stage,'ACCOUNT_HISTORICAL_REVISION','0'*40),self.assertRaises(ValueError):
                        stage.qualified_prior_input(root,path,old,current)
                path='native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c'
                write(root,path,(ROOT/path).read_bytes());commit(root)
                with self.assertRaises(ValueError):stage.qualified_prior_input(root,path,'0'*64,current)
                expected=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                self.assertEqual(stage.qualified_prior_input(root,path,expected,current),(ROOT/path).read_bytes())
            # A present historical revision with different source is also refused.
            with mock.patch.object(stage,'ACCOUNT_HISTORICAL_REVISION',git(root,'rev-parse','HEAD').decode().strip()),self.assertRaises(ValueError):
                path=next(iter(stage.ACCOUNT_OLD_CORE));stage.qualified_prior_input(root,path,stage.ACCOUNT_OLD_CORE[path],current)

    def test_current_whole_driver_map_and17tu_composition_are_explicit(self):
        commit_sha=git(ROOT,'rev-parse','HEAD').decode().strip();pins=stage.committed_inputs(ROOT,commit_sha)
        for name,expected in stage.ACCOUNT_CURRENT_CORE.items():self.assertEqual(pins[name],expected)
        for name,expected in stage.received_prefix.SOURCE_PINS.items():self.assertEqual(pins[name],expected)
        for name,expected in stage.account_controls_inputs(ROOT).items():self.assertEqual(pins[name],expected)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);sources=stage.prepare_project(ROOT,root/'project',root/'crypto',root/'zlib')
            self.assertEqual(len(sources),17);self.assertEqual(len(set(sources)),17)
            self.assertEqual(sources.count(ROOT/'native-android/engine/dbclient/coh_db_account_controls.c'),1)
            self.assertIn(stage.HERE/'windows/wrapped_db_received_prefix.c',sources)
            self.assertNotIn(ROOT/'native-android/engine/dbclient/coh_db_session.c',sources)
            self.assertFalse(any('test_' in p.name for p in sources))
            text=(root/'project/CMakeLists.txt').read_text()
            self.assertIn('MultiThreaded',text);self.assertIn('ZLIB::ZLIB',text)
        RUN_RECORDS['current_source_map_count']=len(pins)
        RUN_RECORDS['project_translation_units']=17

    def test_original_positive_policy_child_lifetime_and_historical_proofs_remain_exact(self):
        old=git(ROOT,'show',stage.ACCOUNT_HISTORICAL_REVISION+':'+stage.PREFIX+'deployment/hosted_auth_db_development.py')
        current=Path(stage.__file__).read_bytes()
        def definitions(raw):return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(raw).body
            if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
        before,after=definitions(old),definitions(current)
        unchanged=('private_json','native_shape','admit_probe','observation','private_probe','finish_private_job',
            'DevelopmentJob','DevelopmentScope','PrivateBuildCommands','probe_identity','build_probe')
        for name in unchanged:self.assertEqual(before[name],after[name],name)
        for path in ('windows/db_development_probe.c','windows/wrapped_db_received_prefix.c',
                'windows/db_development_received_probe.c','windows/auth_db_development_owner.c',
                'windows/auth_db_development_owner.h','qualification/db-received-prefix-20261018/host.json'):
            path=stage.PREFIX+'deployment/'+path
            self.assertEqual((ROOT/path).read_bytes(),git(ROOT,'show',stage.ACCOUNT_HISTORICAL_REVISION+':'+path))
        summary=stage.account_controls_summary()
        self.assertFalse(summary['unknown_command_policy_relaxed']);self.assertFalse(summary['owner_success_predicate_changed'])
        self.assertFalse(summary['old_qualifiers_reexecuted']);self.assertFalse(summary['actual_account_control_bodies_inferred'])
        RUN_RECORDS['unchanged_production_definitions']=list(unchanged)
        RUN_RECORDS['historical_proofs_current_files_unchanged']=True


if __name__=='__main__':unittest.main()

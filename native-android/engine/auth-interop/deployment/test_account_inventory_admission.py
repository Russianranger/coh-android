"""Only new C36-to-C50 composition admission controls; no compiled suite/runtime."""
import ast
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
    git(root,'add','.');git(root,'-c','user.name=Inventory admission','-c','user.email=control@invalid',
        'commit','-qm','controlled inventory source fixture')
    return git(root,'rev-parse','HEAD').decode().strip()


def write(root,path,body):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)


class InventoryAdmissionTests(unittest.TestCase):
    def test_current_c50_proof_and_every_current_input_reject_source_and_proof_drift(self):
        inputs=stage.account_inventory_inputs(ROOT);self.assertEqual(len(inputs),52)
        proof=json.loads(gzip.decompress((ROOT/(stage.INVENTORY_BASE+'.json.gz')).read_bytes()))
        with tempfile.TemporaryDirectory() as name:
            root=Path(name).resolve();git(root,'init','-q')
            for path in inputs:write(root,path,(ROOT/path).read_bytes())
            commit(root);self.assertEqual(stage.account_inventory_inputs(root),inputs)
            for path in (*stage.INVENTORY_CURRENT_DELTA,'native-android/engine/dbclient/coh_db_account_inventory.h',
                    'native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c',
                    stage.INVENTORY_BASE+'.json.gz',stage.INVENTORY_BASE+'-binding.json'):
                raw=(root/path).read_bytes();(root/path).write_bytes(raw+b'\nALTERED_CONTROL')
                with self.subTest(path=path),self.assertRaises(ValueError):stage.account_inventory_inputs(root)
                (root/path).write_bytes(raw)
            path=stage.INVENTORY_BASE+'.json.gz';saved=(root/path).read_bytes();(root/path).unlink();commit(root)
            with self.assertRaises(ValueError):stage.account_inventory_inputs(root)
            write(root,path,saved)
            with self.assertRaises(ValueError):stage.account_inventory_inputs(root)
        with mock.patch.object(stage.gzip,'decompress',return_value=b'{}'),self.assertRaisesRegex(ValueError,'proof_identity'):
            stage.account_inventory_inputs(ROOT)
        RUN_RECORDS['c50_qualification']={'source_inputs':50,'gzip_sha256':stage.INVENTORY_GZIP_SHA,
            'mode_counts':{name:{k:r[k] for k in ('checks','inventory_parser_cases','session_transactions')}
                for name,r in proof['modes'].items()},'qualifier_reexecuted':False}

    def test_c36_predecessor_has_only_three_exact_historical_changes_and_other_inputs_stay_current(self):
        current=stage.account_inventory_inputs(ROOT)
        predecessor=stage.account_controls_inputs(ROOT,inventory=current)
        old=json.loads(gzip.decompress((ROOT/(stage.ACCOUNT_BASE+'.json.gz')).read_bytes()))['source_sha256']
        changed={name for name,sha in old.items() if predecessor[name]!=sha}
        self.assertEqual(changed,set(stage.INVENTORY_PREVIOUS_DELTA));self.assertEqual(len(changed),3)
        for path in set(old)-changed:self.assertEqual(predecessor[path],old[path])
        with tempfile.TemporaryDirectory() as name:
            root=Path(name).resolve();git(root,'init','-q')
            for path in changed:write(root,path,git(ROOT,'show',stage.INVENTORY_HISTORICAL_REVISION+':'+path))
            previous=commit(root)
            for path in changed:write(root,path,(ROOT/path).read_bytes())
            commit(root)
            with mock.patch.object(stage,'INVENTORY_HISTORICAL_REVISION',previous):
                for path in changed:
                    expected=stage.INVENTORY_PREVIOUS_DELTA[path]
                    self.assertEqual(stage.qualified_account_previous_input(root,path,expected,current),(ROOT/path).read_bytes())
                    with self.assertRaises(ValueError):stage.qualified_account_previous_input(root,path,'0'*64,current)
                    with self.assertRaises(ValueError):stage.qualified_account_previous_input(root,path,expected,dict(current,**{path:'0'*64}))
                    with mock.patch.object(stage,'INVENTORY_HISTORICAL_REVISION','0'*40),self.assertRaises(ValueError):
                        stage.qualified_account_previous_input(root,path,expected,current)
                path='native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c'
                write(root,path,(ROOT/path).read_bytes());commit(root)
                with self.assertRaises(ValueError):stage.qualified_account_previous_input(root,path,'0'*64,current)
                sha=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                self.assertEqual(stage.qualified_account_previous_input(root,path,sha,current),(ROOT/path).read_bytes())
            with mock.patch.object(stage,'INVENTORY_HISTORICAL_REVISION',git(root,'rev-parse','HEAD').decode().strip()),self.assertRaises(ValueError):
                path=next(iter(changed));stage.qualified_account_previous_input(root,path,stage.INVENTORY_PREVIOUS_DELTA[path],current)
        RUN_RECORDS['c36_predecessor_changes']=sorted(changed)
        RUN_RECORDS['other_c36_current_inputs_strict']=len(old)-len(changed)

    def test_whole_current_map_same17tu_and_original_policy_lifetime_and_history_roles(self):
        head=git(ROOT,'rev-parse','HEAD').decode().strip();pins=stage.committed_inputs(ROOT,head)
        for path,sha in stage.account_inventory_inputs(ROOT).items():self.assertEqual(pins[path],sha)
        for path,sha in stage.received_prefix.SOURCE_PINS.items():self.assertEqual(pins[path],sha)
        self.assertEqual(len(stage.ACCOUNT_OLD_CORE),2)
        self.assertEqual(pins[stage.ACCOUNT_TOOL],stage.ACCOUNT_TOOL_NEW_SHA)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name).resolve();sources=stage.prepare_project(ROOT,root/'project',root/'crypto',root/'zlib')
            self.assertEqual(len(sources),17);self.assertEqual(len(set(sources)),17)
            self.assertEqual(sources.count(ROOT/'native-android/engine/dbclient/coh_db_account_controls.c'),1)
            self.assertFalse(any('inventory.c' in p.name for p in sources))
        previous=git(ROOT,'show',stage.INVENTORY_HISTORICAL_REVISION+':'+stage.PREFIX+'deployment/hosted_auth_db_development.py')
        def definitions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body
            if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        before,after=definitions(previous),definitions(Path(stage.__file__).read_bytes())
        unchanged=('private_json','native_shape','admit_probe','observation','private_probe','finish_private_job',
            'DevelopmentJob','DevelopmentScope','PrivateBuildCommands','probe_identity','build_probe','prepare_project',
            'qualified_prior_input','account_controls_tool_inputs','dependency_only_ast')
        for name in unchanged:self.assertEqual(before[name],after[name],name)
        for path in (stage.ACCOUNT_BASE+'.json.gz',stage.ACCOUNT_BASE+'-binding.json'):
            self.assertEqual((ROOT/path).read_bytes(),git(ROOT,'show',stage.INVENTORY_HISTORICAL_REVISION+':'+path))
        summary=stage.account_controls_summary()
        self.assertIn('historical C36',summary['source_proof_role']);self.assertFalse(summary['actual_account_control_bodies_inferred'])
        # The final summary survives replacement of the initial value by activation.
        source=Path(stage.__file__).read_text();self.assertLess(source.index("value['account_controls_source_qualification']=account_controls_summary()"),
            source.index("(output/'receipt.json').write_text"))
        RUN_RECORDS.update(current_source_inputs=len(pins),project_translation_units=17,
            unchanged_production_definitions=list(unchanged),old_c36_qualifier_reexecuted=False,
            old_deployment_suites_reexecuted=False)


if __name__=='__main__':unittest.main()

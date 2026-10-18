"""One new composed qualifier-dependency transition control; no prior suite."""
import hashlib
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
    git(root,'add','.');git(root,'-c','user.name=Dependency control','-c','user.email=control@invalid',
        'commit','-qm','controlled dependency fixture')
    return git(root,'rev-parse','HEAD').decode().strip()


class AccountControlsToolAdmissionTests(unittest.TestCase):
    def test_exact_tool_dependency_transition_current_map_and_semantic_refusals(self):
        old=git(ROOT,'show',stage.ACCOUNT_HISTORICAL_REVISION+':'+stage.ACCOUNT_TOOL)
        current=(ROOT/stage.ACCOUNT_TOOL).read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),stage.ACCOUNT_TOOL_OLD_SHA)
        self.assertEqual(hashlib.sha256(current).hexdigest(),stage.ACCOUNT_TOOL_NEW_SHA)
        expected=stage.account_controls_tool_inputs(ROOT)
        self.assertEqual(expected,{stage.ACCOUNT_TOOL:stage.ACCOUNT_TOOL_NEW_SHA,
            stage.ACCOUNT_TOOL_REVIEW:stage.ACCOUNT_TOOL_REVIEW_SHA})
        stage.dependency_only_ast(old,current)
        for changed in (old,current+b'\nUNRELATED_POLICY_CHANGE = True\n',
                current.replace(stage.ACCOUNT_DEPENDENCY.encode(),b'engine/dbclient/other.c'),
                current.replace(stage.ACCOUNT_DEPENDENCY.encode(),
                    (stage.ACCOUNT_DEPENDENCY+"', '"+stage.ACCOUNT_DEPENDENCY).encode()),b'not valid python!!!'):
            with self.assertRaises(ValueError):stage.dependency_only_ast(old,changed)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name).resolve();git(root,'init','-q')
            for path,data in ((stage.ACCOUNT_TOOL,old),(stage.ACCOUNT_TOOL_REVIEW,(ROOT/stage.ACCOUNT_TOOL_REVIEW).read_bytes())):
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            previous=commit(root);(root/stage.ACCOUNT_TOOL).write_bytes(current);commit(root)
            with mock.patch.object(stage,'ACCOUNT_HISTORICAL_REVISION',previous):
                self.assertEqual(stage.account_controls_tool_inputs(root),expected)
                self.assertEqual(stage.qualified_prior_input(root,stage.ACCOUNT_TOOL,stage.ACCOUNT_TOOL_OLD_SHA,expected),current)
                for wanted,account in (('0'*64,expected),(stage.ACCOUNT_TOOL_OLD_SHA,
                        dict(expected,**{stage.ACCOUNT_TOOL:'0'*64}))):
                    with self.assertRaises(ValueError):stage.qualified_prior_input(root,stage.ACCOUNT_TOOL,wanted,account)
                for path in (stage.ACCOUNT_TOOL,stage.ACCOUNT_TOOL_REVIEW):
                    original=(root/path).read_bytes();(root/path).write_bytes(original+b'\nUNEXPECTED')
                    with self.assertRaises(ValueError):stage.account_controls_tool_inputs(root)
                    (root/path).write_bytes(original)
                with mock.patch.object(stage,'ACCOUNT_HISTORICAL_REVISION','0'*40),self.assertRaises(ValueError):
                    stage.account_controls_tool_inputs(root)
        head=git(ROOT,'rev-parse','HEAD').decode().strip();pins=stage.committed_inputs(ROOT,head)
        self.assertEqual(pins[stage.ACCOUNT_TOOL],stage.ACCOUNT_TOOL_NEW_SHA)
        self.assertEqual(pins[stage.ACCOUNT_TOOL_REVIEW],stage.ACCOUNT_TOOL_REVIEW_SHA)
        for path,sha in stage.ACCOUNT_CURRENT_CORE.items():self.assertEqual(pins[path],sha)
        for path,sha in (('qualification/account-controls-admission-20261018/host.json',
                'f6e8b60dfd96193a98b0ae00c9794385c27c589ebef3649d7f7d78b291aa9e5d'),
                ('qualification/db-received-prefix-20261018/host.json',
                '5635322a560af7a73901a13ae8f18f25c2be60ce5f228ab58687999a4fe29985')):
            path=stage.PREFIX+'deployment/'+path
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha)
        RUN_RECORDS.update(current_source_inputs=len(pins),qualified_tool=stage.ACCOUNT_TOOL,
            before_sha256=stage.ACCOUNT_TOOL_OLD_SHA,after_sha256=stage.ACCOUNT_TOOL_NEW_SHA,
            dependency_ast_verified=True,core_exceptions_still_exactly_two=len(stage.ACCOUNT_OLD_CORE)==2,
            old_four_method_suite_reexecuted=False,old_qualifier_executed=False)


if __name__=='__main__':unittest.main()

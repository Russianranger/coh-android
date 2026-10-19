#!/usr/bin/env python3
"""New reuse-envelope controls; synthetic compiler/PE and lifecycle doubles.

Temporary real Git checkouts and an isolated synthetic verifier exercise the
reuse envelope. No original compiler, original server or accepted suite runs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('reuse_runtime_controls', HERE / 'runtime.py')
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)
r = rt.reuse
SYNTHETIC_VERIFIER = '''import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('action')
for name in ('source-root','compile-directory','expected-source-revision','receipt-sha256'):p.add_argument('--'+name,required=True)
a=p.parse_args();d=pathlib.Path(a.compile_directory);raw=(d/'compile-only-receipt.json').read_bytes();v=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()==a.receipt_sha256 and v['source_revision']==a.expected_source_revision
b=(d/'MapServer.exe').read_bytes();assert v['artifacts']['MapServer.exe']=={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
print(json.dumps({'passed':True,'build_role':'nonshipping_same_owner_initial_send_observer','compile_only':True,'runtime_executed':False,'source_revision':a.expected_source_revision,'world_authority':False}))
'''


class Envelope(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='coh-map-reuse-controls-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.current = self.root / 'current'
        self.old = self.root / 'historical'
        self.directory = self.root / 'compile'
        self.current.mkdir(); self.directory.mkdir()
        self.git_run('init', '-q')
        self.git_run('config', 'user.email', 'synthetic@example.invalid')
        self.git_run('config', 'user.name', 'Synthetic reuse controls')
        p = self.current / r.RECIPE
        p.parent.mkdir(parents=True); p.write_text(SYNTHETIC_VERIFIER)
        (self.current / 'supplier.c').write_bytes(b'synthetic compiler supplier\n')
        (self.current / 'native.c').write_bytes(b'synthetic native before\n')
        self.git_run('add', '.'); self.git_run('commit', '-qm', 'synthetic historical compiler')
        self.old_revision = self.git_run('rev-parse', 'HEAD').decode().strip()
        self.git_run('worktree', 'add', '-q', '--detach', str(self.old), self.old_revision)
        (self.current / 'native.c').write_bytes(b'synthetic changed native\n')
        self.git_run('add', '.'); self.git_run('commit', '-qm', 'synthetic native successor')
        self.current_revision = self.git_run('rev-parse', 'HEAD').decode().strip()
        self.recipe = SimpleNamespace(__file__=str(self.current / r.RECIPE),
            checkout_closure=self.closure, relative_name=self.relative_name)
        image = b'SYNTHETIC_IMAGE_NOT_A_QUALIFIED_PE'
        (self.directory / 'MapServer.exe').write_bytes(image)
        self.receipt = {'source_revision': self.old_revision, 'build_role': r.ROLE,
            'source_closure_sha256': self.closure(self.current),
            'artifacts': {'MapServer.exe': {'bytes': len(image), 'sha256': r.sha(image)}}}
        self.write_receipt()
        self.admission = {'schema': 'coh-historical-map-artifact-recovery-v1',
            'current_execution_revision': self.current_revision, 'origin': {
                'revision': self.old_revision, 'run_id': 123, 'attempt': 1, 'artifact_id': 456,
                'zip_sha256': 'a'*64, 'receipt_sha256': self.receipt_pin},
            'zip_bytes': 100, 'members': 3, 'expanded_bytes': 200,
            'historical_successful_compile_job_verified': True,
            'same_execution_run_claimed': False, 'compiler_reexecuted': False,
            'runtime_executed': False, 'world_authority': False}
        self.write_admission()
        root_patch = patch.object(r, 'ROOT', self.current)
        root_patch.start(); self.addCleanup(root_patch.stop)

    def git_run(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.current, stderr=subprocess.DEVNULL)

    @staticmethod
    def relative_name(name):
        r.need(type(name) is str and name and not name.startswith('/') and
               all(x not in ('', '.', '..') for x in name.split('/')) and
               '\\' not in name and ':' not in name, 'CONTROL_NAME')

    def closure(self, root):
        result = {}
        for name in ('supplier.c', r.RECIPE):
            raw = r.read(root / name)
            r.need(raw == subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=root),
                   'CONTROL_CURRENT_GIT')
            result[name] = r.sha(raw)
        return result

    def write_receipt(self):
        (self.directory / r.RECEIPT).write_bytes(r.encoded(self.receipt))
        self.receipt_pin = r.sha(r.read(self.directory / r.RECEIPT))

    def write_admission(self):
        self.admission_path = self.directory.with_name(self.directory.name + '-recovery.json')
        self.admission_path.write_bytes(r.encoded(self.admission))
        self.admission_pin = r.sha(r.read(self.admission_path))

    def verify(self, **changes):
        args = dict(recipe=self.recipe, directory=self.directory, current_root=self.current,
            current_revision=self.current_revision, historical_root=self.old,
            historical_revision=self.old_revision, receipt_pin=self.receipt_pin,
            admission_pin=self.admission_pin)
        args.update(changes)
        return r.verify(**args)

    def test_real_git_native_successor_and_isolated_synthetic_verifier(self):
        before = r.read(self.directory / r.RECEIPT)
        actual, proof = self.verify()
        self.assertEqual(actual, self.receipt)
        self.assertEqual(actual['source_revision'], self.old_revision)
        self.assertNotEqual(actual['source_revision'], self.current_revision)
        self.assertEqual(proof['current_execution_revision'], self.current_revision)
        self.assertEqual(proof['compile_artifact_origin']['artifact_id'], 456)
        self.assertFalse(proof['world_authority'])
        self.assertEqual(before, r.read(self.directory / r.RECEIPT))

    def test_current_committed_compiler_change_refused(self):
        (self.current / 'supplier.c').write_bytes(b'changed compiler\n')
        self.git_run('add', '.'); self.git_run('commit', '-qm', 'changed compiler')
        self.current_revision = self.git_run('rev-parse', 'HEAD').decode().strip()
        self.admission['current_execution_revision'] = self.current_revision; self.write_admission()
        with self.assertRaisesRegex(ValueError, 'CURRENT_COMPILER_SUPPLIERS'): self.verify()

    def test_current_uncommitted_compiler_change_refused(self):
        (self.current / 'supplier.c').write_bytes(b'changed compiler\n')
        with self.assertRaisesRegex(ValueError, 'CONTROL_CURRENT_GIT'): self.verify()

    def test_current_wrong_revision_refused(self):
        with self.assertRaisesRegex(ValueError, 'CHECKOUT_REVISION'):
            self.verify(current_revision='f'*40)

    def test_historical_dirty_tree_refused(self):
        (self.old / 'native.c').write_bytes(b'dirty historical\n')
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_DIRTY'): self.verify()

    def test_same_checkout_refused(self):
        with self.assertRaisesRegex(ValueError, 'DISTINCT_OWN_CHECKOUTS'):
            self.verify(historical_root=self.current)

    def test_wrong_receipt_hash_refused(self):
        with self.assertRaisesRegex(ValueError, 'RECEIPT_HASH'): self.verify(receipt_pin='f'*64)

    def test_rewritten_receipt_revision_refused(self):
        self.receipt['source_revision'] = self.current_revision; self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'COMPILE_ORIGIN'): self.verify()

    def test_source_closure_added_or_removed_supplier_refused(self):
        for name in ('supplier.c', 'extra.c'):
            with self.subTest(name=name):
                original = deepcopy(self.receipt)
                if name in self.receipt['source_closure_sha256']:
                    del self.receipt['source_closure_sha256'][name]
                else: self.receipt['source_closure_sha256'][name] = 'f'*64
                self.write_receipt()
                self.admission['origin']['receipt_sha256'] = self.receipt_pin; self.write_admission()
                with self.assertRaisesRegex(ValueError, 'CURRENT_COMPILER_SUPPLIERS'): self.verify()
                self.receipt = original

    def test_synthetic_binary_change_refused_by_historical_verifier(self):
        (self.directory / 'MapServer.exe').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_VERIFIER'): self.verify()

    def test_late_receipt_mutation_refused(self):
        def mutate(*_): (self.directory / r.RECEIPT).write_bytes(b'changed')
        with patch.object(r, 'historical_verify', mutate):
            with self.assertRaisesRegex(ValueError, 'RECEIPT_CHANGED'): self.verify()

    def test_late_current_supplier_change_refused(self):
        original = self.recipe.checkout_closure
        count = 0
        def changing(root):
            nonlocal count
            count += 1
            result = original(root)
            return result if count == 1 else {**result, 'extra': 'f'*64}
        self.recipe.checkout_closure = changing
        with self.assertRaisesRegex(ValueError, 'CURRENT_SUPPLIERS_CHANGED'): self.verify()

    def test_historical_verifier_scope_extra_field_refused(self):
        original = r.subprocess.run
        def run(command, **kwargs):
            if command[0] == sys.executable:
                value = {'passed': True, 'build_role': r.ROLE, 'compile_only': True,
                    'runtime_executed': False, 'source_revision': self.old_revision,
                    'world_authority': False, 'private_canary': 'PRIVATE'}
                return SimpleNamespace(returncode=0, stderr=b'', stdout=r.encoded(value))
            return original(command, **kwargs)
        with patch.object(r.subprocess, 'run', run):
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_VERIFIER_SCOPE'): self.verify()

    def test_wrong_artifact_admission_pin_refused(self):
        with self.assertRaisesRegex(ValueError, 'ARTIFACT_ADMISSION_PIN'):
            self.verify(admission_pin='f'*64)

    def test_artifact_admission_origin_and_scope_mismatches_refused(self):
        for name, value in (('current_execution_revision', self.old_revision),
            ('historical_successful_compile_job_verified', False), ('same_execution_run_claimed', True),
            ('world_authority', True), ('runtime_executed', True), ('extra', 'PRIVATE')):
            with self.subTest(name=name):
                original = deepcopy(self.admission)
                self.admission[name] = value; self.write_admission()
                with self.assertRaisesRegex(ValueError, 'ARTIFACT_ADMISSION_SCOPE'): self.verify()
                self.admission = original

    def test_artifact_nested_origin_mismatches_refused(self):
        for name, value in (('revision', self.current_revision), ('receipt_sha256', 'f'*64),
                            ('extra', 'PRIVATE')):
            with self.subTest(name=name):
                original = deepcopy(self.admission)
                self.admission['origin'][name] = value; self.write_admission()
                with self.assertRaisesRegex(ValueError, 'ARTIFACT_ORIGIN'): self.verify()
                self.admission = original

    def test_artifact_admission_boolean_number_and_bad_digest_refused(self):
        for name, value in (('run_id', True), ('artifact_id', 0), ('zip_bytes', 64*1024**2+1),
            ('attempt', -1), ('zip_sha256', 'x'*64)):
            with self.subTest(name=name):
                original = deepcopy(self.admission)
                (self.admission if name == 'zip_bytes' else self.admission['origin'])[name] = value
                self.write_admission()
                with self.assertRaises(ValueError): self.verify()
                self.admission = original

    def test_artifact_admission_symlink_refused(self):
        target = self.root / 'real-admission.json'
        self.admission_path.rename(target); self.admission_path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'PATH_LINK'): self.verify()

    def test_duplicate_json_refused(self):
        with self.assertRaisesRegex(ValueError, 'JSON_DUPLICATE'): r.decode(b'{"x":1,"x":2}')


def proof():
    return {'schema': r.SCHEMA, 'historical_compile_revision': 'a'*40,
        'current_execution_revision': 'b'*40, 'compile_receipt_sha256': 'c'*64,
        'artifact_admission_sha256': 'd'*64, 'compile_artifact_origin':
            {'run_id': 123, 'attempt': 1, 'artifact_id': 456, 'zip_bytes': 100, 'zip_sha256': 'e'*64,
             'revision': 'a'*40, 'receipt_sha256': 'c'*64},
        'compiler_supplier_files': 2, 'compiler_supplier_closure_sha256': 'f'*64,
        'map_binary': {'bytes': 1, 'sha256': '0'*64},
        'unchanged_historical_verifier_executed': True,
        'historical_raw_and_Git_suppliers_verified': True,
        'current_raw_and_Git_compiler_suppliers_equal': True,
        'original_compile_receipt_preserved': True, 'compiler_reexecuted': False,
        'accepted_qualifiers_reexecuted': False, 'runtime_executed': False,
        'normal_authentication_qualified': False, 'world_authority': False}


class Wrapper(unittest.TestCase):
    def test_bridge_restores_every_replacement_after_exception_and_rejects_changed_proof(self):
        marker = lambda *a, **k: None
        original_paths = lambda *_: {'original'}
        core = SimpleNamespace(orchestration_source_paths=original_paths,
            finish_initial_observation=marker,
            retained=SimpleNamespace(emit_identity=lambda _, identity: identity))
        original_emit = core.retained.emit_identity
        original_verify = lambda *_: None
        recipe = SimpleNamespace(verify_artifact=original_verify, STAGE_RECEIPT='stage',
                                 read=lambda _: b'{}', decode=json.loads)
        args = SimpleNamespace(source_revision='b'*40, compile_receipt_sha256='c'*64,
            historical_source_root=Path('/synthetic-old'), historical_source_revision='a'*40,
            artifact_admission_sha256='d'*64, output=Path('/output'))
        actual = {'source_revision': 'a'*40}
        calls = 0
        def verify(*_):
            nonlocal calls
            calls += 1
            p = proof()
            if calls > 1: p['artifact_admission_sha256'] = '9'*64
            return actual, p
        with patch.object(rt.base.Bridge, 'install', lambda _: None), patch.object(r, 'verify', verify):
            with self.assertRaisesRegex(ValueError, 'RUNTIME_PROOF_CHANGED'):
                with rt.Bridge(args, core, None, None, None, SimpleNamespace(empty=lambda: {}),
                               recipe, None, None):
                    admitted, _ = recipe.verify_artifact(Path('/compile'), rt.ROOT, 'b'*40, 'c'*64)
                    self.assertEqual(admitted['source_revision'], 'a'*40)
                    self.assertEqual(core.orchestration_source_paths(), {'original', *rt.source_paths()})
                    identity = core.retained.emit_identity(Path('/output/run-identity.json'),
                        {'compile_receipt_sha256': 'c'*64, 'source_revision': 'b'*40})
                    self.assertEqual(identity[rt.PRIVATE], proof())
                    for name, value in (('compile_receipt_sha256', '9'*64),
                                        ('source_revision', '9'*40), (rt.PRIVATE, proof())):
                        invalid = {'compile_receipt_sha256': 'c'*64, 'source_revision': 'b'*40}
                        invalid[name] = value
                        with self.assertRaisesRegex(ValueError, 'PRESTART_IDENTITY'):
                            core.retained.emit_identity(Path('/output/run-identity.json'), invalid)
                    report = {}; core.finish_initial_observation(report)
                    self.assertEqual(report[rt.PRIVATE], proof())
                    recipe.verify_artifact(Path('/compile'), rt.ROOT, 'b'*40, 'c'*64)
        self.assertIs(recipe.verify_artifact, original_verify)
        self.assertIs(core.orchestration_source_paths, original_paths)
        self.assertIs(core.finish_initial_observation, marker)
        self.assertIs(core.retained.emit_identity, original_emit)
        self.assertFalse(rt.base.Bridge.active)

    def project(self, p, identity_proof=None):
        report = {rt.PRIVATE: p, 'compile_receipt_sha256': 'c'*64,
            'original_map_binary': {'bytes': 1, 'sha256': '0'*64},
            'source_sha256': {name: r.sha(r.read(rt.ROOT / name)) for name in rt.source_paths()},
            'private_canary': 'PRIVATE'}
        original = lambda *_: {'transaction': {'passed': True}, 'world_authority': False}
        def fake_project(*_):
            progress = SimpleNamespace(read_private=lambda *_: r.encoded({
                rt.PRIVATE: p if identity_proof is None else identity_proof}))
            return rt.base.projection(report, Path('/unused'), None, progress)
        with patch.dict(os.environ, GITHUB_SHA='b'*40), patch.object(rt.base, 'projection', original), \
             patch.object(rt.base, 'project', fake_project):
            try: return rt.project(Path('/unused'), Path('/unused-output'))
            finally: self.assertIs(rt.base.projection, original)

    def test_fixed_public_projection_and_no_private_key(self):
        value = self.project(proof())
        self.assertEqual(value[rt.PRIVATE], proof())
        self.assertNotIn('PRIVATE', json.dumps(value))

    def test_projection_identity_scope_extra_field_and_boolean_count_refusals(self):
        for name, value in (('current_execution_revision', '9'*40),
            ('compile_receipt_sha256', '9'*64), ('map_binary', {'bytes': 2, 'sha256': '0'*64}),
            ('world_authority', True), ('compiler_supplier_files', True),
            ('historical_compile_revision', 'bad'), ('extra', 'PRIVATE')):
            with self.subTest(name=name):
                p = proof(); p[name] = value
                with self.assertRaises(ValueError): self.project(p)

    def test_projection_reuse_origin_must_equal_prestart_identity(self):
        changed = proof(); changed['compile_artifact_origin']['artifact_id'] = 999
        with self.assertRaisesRegex(ValueError, 'PROJECTION_PRESTART_IDENTITY'):
            self.project(proof(), identity_proof=changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(Envelope),
        unittest.defaultTestLoader.loadTestsFromTestCase(Wrapper)]))
    value = {'schema': 'coh-server-initial-map-reuse-controls-v1', 'passed': result.wasSuccessful(),
        'test_methods': result.testsRun, 'real_temporary_Git_checkouts': True,
        'historical_verifier_and_PE_are_explicit_synthetic_doubles': True,
        'inherited_runtime_lifecycle_and_projector_are_explicit_doubles': True,
        'original_compiler_executed': False, 'original_server_executed': False,
        'accepted_qualifiers_reexecuted': False, 'world_authority': False,
        'source_sha256': {p.name: r.sha(r.read(p)) for p in
            (HERE / 'reuse.py', HERE / 'runtime.py', HERE / 'check_reuse.py')}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream: stream.write(r.encoded(value))
    print(json.dumps({'passed': value['passed'], 'test_methods': value['test_methods'],
                      'original_server_executed': False}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

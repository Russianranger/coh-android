#!/usr/bin/env python3
"""Original transaction wrapper with explicit unchanged historical Map reuse."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, filename):
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(existing.__file__).resolve() != filename:
            raise ValueError('MAP_REUSE_FOREIGN_MODULE')
        return existing
    spec = importlib.util.spec_from_file_location(name, filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reuse = load('coh_server_initial_map_reuse', HERE / 'reuse.py')
base = load('coh_server_initial_runtime_base', ROOT / 'native-android/tools/server-initial-runtime-20261018/runtime.py')
PRIVATE = 'server_initial_map_compile_reuse'


def source_paths():
    return tuple(p.relative_to(ROOT).as_posix() for p in (HERE / 'reuse.py', HERE / 'runtime.py'))


class Bridge(base.Bridge):
    def install(self):
        def verify(directory, root, revision, pin):
            reuse.need(root == ROOT and revision == self.args.source_revision
                       and pin == self.args.compile_receipt_sha256, 'RUNTIME_ARGUMENTS')
            actual, proof = reuse.verify(self.recipe, directory, root, revision,
                self.args.historical_source_root, self.args.historical_source_revision, pin,
                self.args.artifact_admission_sha256)
            if self.reuse_proof is not None:
                reuse.need(proof == self.reuse_proof, 'RUNTIME_PROOF_CHANGED')
            self.reuse_proof = proof
            # Existing consumers require the original staged receipt, not a
            # synthesized replacement. The original recipe already checked it.
            staged = self.recipe.decode(self.recipe.read(Path(directory) / self.recipe.STAGE_RECEIPT))
            return actual, staged

        self.reuse_proof = None
        self.replace(self.recipe, 'verify_artifact', verify)
        super().install()
        original_paths = self.core.orchestration_source_paths

        def paths(*args):
            return set(original_paths(*args)) | set(source_paths())

        self.replace(self.core, 'orchestration_source_paths', paths)
        original_emit = self.core.retained.emit_identity

        def emit_identity(filename, identity):
            reuse.need(filename == self.args.output / 'run-identity.json'
                and self.reuse_proof is not None
                and identity.get('compile_receipt_sha256') == self.args.compile_receipt_sha256
                and identity.get('source_revision') == self.args.source_revision
                and PRIVATE not in identity, 'PRESTART_IDENTITY')
            identity = dict(identity)
            identity[PRIVATE] = dict(self.reuse_proof)
            return original_emit(filename, identity)

        self.replace(self.core.retained, 'emit_identity', emit_identity)
        original_finish = self.core.finish_initial_observation

        def finish(report, *args):
            original_finish(report, *args)
            reuse.need(self.reuse_proof is not None, 'RUNTIME_PROOF_MISSING')
            report[PRIVATE] = dict(self.reuse_proof)

        self.replace(self.core, 'finish_initial_observation', finish)


def capture(args):
    reuse.need(args.source_revision == os.environ.get('GITHUB_SHA'), 'EXECUTION_REVISION')
    for name in ('compile_directory', 'native_capture', 'native_build_receipt', 'work', 'output',
                 'historical_source_root'):
        setattr(args, name, reuse.path(getattr(args, name)))
    core, fresh, probe, progress, _, ledger = base.context()
    recipe, receive, source = base.suppliers()
    with Bridge(args, core, fresh, probe, progress, ledger, recipe, receive, source):
        return core.capture(args)


def project(directory, output):
    # The original projector checks every executed supplier from the private
    # run's raw/Git closure. Add the explicit historical/current binding only
    # after verifying its fixed schema, fields and identity with that run.
    original = base.projection

    def projection(report, *args):
        value = original(report, *args)
        proof = report.get(PRIVATE)
        reuse.need(type(proof) is dict and proof.get('schema') == reuse.SCHEMA
            and proof.get('current_execution_revision') == os.environ.get('GITHUB_SHA')
            and proof.get('compile_receipt_sha256') == report.get('compile_receipt_sha256')
            and proof.get('map_binary') == report.get('original_map_binary'), 'PROJECTION_BINDING')
        identity = reuse.decode(args[2].read_private(Path(args[0]) / 'run-identity.json', 8*1024**2))
        reuse.need(identity.get(PRIVATE) == proof, 'PROJECTION_PRESTART_IDENTITY')
        for name in source_paths():
            reuse.need(report.get('source_sha256', {}).get(name) == reuse.sha(reuse.read(ROOT / name)),
                       'PROJECTION_EXECUTED_SOURCE')
        expected_keys = {'schema', 'historical_compile_revision', 'current_execution_revision',
            'compile_receipt_sha256', 'compiler_supplier_files', 'compiler_supplier_closure_sha256',
            'artifact_admission_sha256', 'compile_artifact_origin',
            'map_binary', 'unchanged_historical_verifier_executed',
            'historical_raw_and_Git_suppliers_verified', 'current_raw_and_Git_compiler_suppliers_equal',
            'original_compile_receipt_preserved', 'compiler_reexecuted', 'accepted_qualifiers_reexecuted',
            'runtime_executed', 'normal_authentication_qualified', 'world_authority'}
        reuse.need(set(proof) == expected_keys, 'PROJECTION_FIELDS')
        reuse.revision(proof['historical_compile_revision'])
        for name in ('compiler_supplier_closure_sha256', 'compile_receipt_sha256', 'artifact_admission_sha256'):
            reuse.need(type(proof[name]) is str and len(proof[name]) == 64
                       and all(c in '0123456789abcdef' for c in proof[name]), 'PROJECTION_DIGEST')
        origin = proof['compile_artifact_origin']
        reuse.need(type(origin) is dict and set(origin) == {'run_id', 'attempt', 'artifact_id',
            'revision', 'zip_bytes', 'zip_sha256', 'receipt_sha256'}
            and origin['revision'] == proof['historical_compile_revision']
            and origin['receipt_sha256'] == proof['compile_receipt_sha256'], 'PROJECTION_ARTIFACT_ORIGIN')
        for name, maximum in (('run_id', 2**63-1), ('attempt', 1000000),
            ('artifact_id', 2**63-1), ('zip_bytes', 64*1024**2)):
            reuse.need(type(origin[name]) is int and 0 < origin[name] <= maximum,
                       'PROJECTION_ARTIFACT_VALUE')
        reuse.need(type(origin['zip_sha256']) is str and len(origin['zip_sha256']) == 64
            and all(c in '0123456789abcdef' for c in origin['zip_sha256']), 'PROJECTION_ARTIFACT_DIGEST')
        reuse.need(type(proof['compiler_supplier_files']) is int
                   and 0 < proof['compiler_supplier_files'] <= 2048, 'PROJECTION_COUNT')
        reuse.need(all(proof[name] is True for name in ('unchanged_historical_verifier_executed',
            'historical_raw_and_Git_suppliers_verified', 'current_raw_and_Git_compiler_suppliers_equal',
            'original_compile_receipt_preserved')) and all(proof[name] is False for name in
            ('compiler_reexecuted', 'accepted_qualifiers_reexecuted', 'runtime_executed',
             'normal_authentication_qualified', 'world_authority')), 'PROJECTION_SCOPE')
        value[PRIVATE] = dict(proof)
        reuse.need(len(reuse.encoded(value)) <= base.MAX_PUBLIC_BYTES, 'PROJECTION_BOUND')
        return value

    base.projection = projection
    try:
        return base.project(directory, output)
    finally:
        base.projection = original


def main():
    parser = base.parser()
    capture_parser = parser._subparsers._group_actions[0].choices['capture']
    capture_parser.add_argument('--historical-source-root', type=Path, required=True)
    capture_parser.add_argument('--historical-source-revision', required=True)
    capture_parser.add_argument('--artifact-admission-sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == 'capture':
            value = capture(args)
            passed = value.get('passed') is True
            print(json.dumps({'schema': 'coh-server-initial-reuse-runtime-status-v1',
                'passed': passed, 'cleanup_verified': value.get('cleanup_verified') is True,
                'world_authority': False}))
            return 0 if passed else 2
        value = project(args.private_output, args.output)
        print(json.dumps({'schema': 'coh-server-initial-reuse-projection-status-v1',
            'projection_written': True, 'transaction_passed': value['transaction']['passed'],
            'world_authority': False}))
        return 0
    except Exception:
        print(json.dumps({'schema': 'coh-server-initial-reuse-runtime-status-v1', 'passed': False,
            'failure': 'ADMISSION_OR_PROJECTION_REFUSED', 'world_authority': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

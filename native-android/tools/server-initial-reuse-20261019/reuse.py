#!/usr/bin/env python3
"""Admit an unchanged historical Map compiler role for a new native receiver.

The original verifier executes unchanged in its own exact, clean checkout. Its
receipt remains historical. A separate current raw/Git supplier comparison is
required; no artifact revision or receipt field is rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RECIPE = 'native-android/tools/server-initial-observer-20261018/recipe.py'
RECEIPT = 'compile-only-receipt.json'
SCHEMA = 'coh-server-initial-map-compile-reuse-v1'
ROLE = 'nonshipping_same_owner_initial_send_observer'
MAXIMUM = 16 * 1024**2


def need(value, code):
    if not value:
        raise ValueError('MAP_REUSE_' + code)


def path(value):
    value = Path(os.path.abspath(value))
    need(not any(p.is_symlink() for p in (value, *value.parents)), 'PATH_LINK')
    return value


def read(value):
    value = path(value)
    before = value.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
         and 0 < before.st_size <= MAXIMUM, 'REGULAR_BOUND')
    raw = value.read_bytes()
    after = value.stat()
    need(len(raw) == before.st_size and
         (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
         (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'READ_CHANGED')
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('ascii')


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'JSON_DUPLICATE')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: need(False, 'JSON_FINITE'))
    need(type(value) is dict, 'JSON_OBJECT')
    return value


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, timeout=60)


def revision(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{40}', value), 'REVISION')
    return value


def checkout(root, expected, clean=False):
    need(git(root, 'rev-parse', '--show-toplevel').decode().strip() == str(root), 'CHECKOUT_ROOT')
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == expected, 'CHECKOUT_REVISION')
    if clean:
        need(git(root, 'status', '--porcelain') == b'', 'HISTORICAL_DIRTY')


def historical_verify(root, directory, expected, receipt_pin):
    """Only the historical recipe, in an isolated process, verifies old bytes."""
    result = subprocess.run([sys.executable, '-I', '-B', str(root / RECIPE),
        'verify-artifact', '--source-root', str(root), '--compile-directory', str(directory),
        '--expected-source-revision', expected, '--receipt-sha256', receipt_pin],
        cwd=root, capture_output=True, timeout=180)
    need(result.returncode == 0 and not result.stderr and len(result.stdout) <= 4096,
         'HISTORICAL_VERIFIER')
    value = decode(result.stdout)
    need(value == {'passed': True, 'build_role': ROLE, 'compile_only': True,
                   'runtime_executed': False, 'source_revision': expected,
                   'world_authority': False}, 'HISTORICAL_VERIFIER_SCOPE')


def provenance(directory, expected_revision, current_revision, receipt_pin, admission_pin):
    """Bind the prior exact API/download admission, without inventing API work."""
    filename = directory.with_name(directory.name + '-recovery.json')
    raw = read(filename)
    need(type(admission_pin) is str and re.fullmatch('[0-9a-f]{64}', admission_pin)
         and sha(raw) == admission_pin, 'ARTIFACT_ADMISSION_PIN')
    value = decode(raw)
    keys = {'schema', 'origin', 'current_execution_revision', 'zip_bytes', 'members',
        'expanded_bytes', 'historical_successful_compile_job_verified', 'same_execution_run_claimed',
        'compiler_reexecuted', 'runtime_executed', 'world_authority'}
    need(set(value) == keys and value['schema'] == 'coh-historical-map-artifact-recovery-v1'
         and value['current_execution_revision'] == current_revision
         and value['historical_successful_compile_job_verified'] is True
         and all(value[name] is False for name in ('same_execution_run_claimed',
             'compiler_reexecuted', 'runtime_executed', 'world_authority')),
         'ARTIFACT_ADMISSION_SCOPE')
    origin = value['origin']
    need(type(origin) is dict and set(origin) == {'artifact_id', 'run_id', 'revision', 'attempt',
        'zip_sha256', 'receipt_sha256'} and origin['revision'] == expected_revision
        and origin['receipt_sha256'] == receipt_pin, 'ARTIFACT_ORIGIN')
    for name, maximum in (('run_id', 2**63-1), ('attempt', 1000000), ('artifact_id', 2**63-1)):
        need(type(origin[name]) is int and 0 < origin[name] <= maximum, 'ARTIFACT_ADMISSION_VALUE')
    for name, maximum in (('zip_bytes', 64*1024**2), ('members', 128),
        ('expanded_bytes', 96*1024**2)):
        need(type(value[name]) is int and 0 < value[name] <= maximum, 'ARTIFACT_ADMISSION_VALUE')
    need(type(origin['zip_sha256']) is str and re.fullmatch('[0-9a-f]{64}', origin['zip_sha256']),
         'ARTIFACT_ADMISSION_DIGEST')
    return raw, {**origin, 'zip_bytes': value['zip_bytes']}


def verify(recipe, directory, current_root, current_revision, historical_root,
           historical_revision, receipt_pin, admission_pin):
    """Return the untouched original receipt and separately scoped reuse proof."""
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'ASSERTIONS_REQUIRED')
    current_root, historical_root, directory = map(path, (current_root, historical_root, directory))
    current_revision, historical_revision = map(revision, (current_revision, historical_revision))
    need(current_root == ROOT and historical_root != current_root, 'DISTINCT_OWN_CHECKOUTS')
    need(Path(recipe.__file__).resolve() == current_root / RECIPE, 'CURRENT_RECIPE')
    need(type(receipt_pin) is str and re.fullmatch('[0-9a-f]{64}', receipt_pin), 'RECEIPT_PIN')
    checkout(current_root, current_revision)
    checkout(historical_root, historical_revision, clean=True)
    need(subprocess.run(['git', 'merge-base', '--is-ancestor', historical_revision,
                         current_revision], cwd=current_root, timeout=60).returncode == 0,
         'COMPILE_ANCESTOR')
    raw = read(directory / RECEIPT)
    need(sha(raw) == receipt_pin, 'RECEIPT_HASH')
    receipt = decode(raw)
    need(receipt.get('source_revision') == historical_revision and receipt.get('build_role') == ROLE,
         'COMPILE_ORIGIN')
    admission_raw, origin = provenance(directory, historical_revision, current_revision, receipt_pin, admission_pin)
    closure = recipe.checkout_closure(current_root)
    need(type(closure) is dict and closure and receipt.get('source_closure_sha256') == closure,
         'CURRENT_COMPILER_SUPPLIERS')
    # Do not accept a matching receipt map alone: every historical supplier must
    # still be that committed historical file, and equal its current counterpart.
    for name, digest in closure.items():
        recipe.relative_name(name)
        need(sha(read(historical_root / name)) == digest == sha(read(current_root / name)),
             'COMPILER_SUPPLIER_BYTES')
        need(sha(git(historical_root, 'show', historical_revision + ':' + name)) == digest,
             'HISTORICAL_SUPPLIER_GIT')
    historical_verify(historical_root, directory, historical_revision, receipt_pin)
    need(read(directory / RECEIPT) == raw, 'RECEIPT_CHANGED')
    need(provenance(directory, historical_revision, current_revision, receipt_pin, admission_pin) == (admission_raw, origin),
         'ARTIFACT_ADMISSION_CHANGED')
    checkout(historical_root, historical_revision, clean=True)
    checkout(current_root, current_revision)
    need(recipe.checkout_closure(current_root) == closure, 'CURRENT_SUPPLIERS_CHANGED')
    binary = receipt.get('artifacts', {}).get('MapServer.exe')
    need(type(binary) is dict and set(binary) == {'bytes', 'sha256'}, 'BINARY_PIN')
    image = read(directory / 'MapServer.exe')
    need(binary == {'bytes': len(image), 'sha256': sha(image)}, 'BINARY_CHANGED')
    proof = {'schema': SCHEMA, 'historical_compile_revision': historical_revision,
        'current_execution_revision': current_revision, 'compile_receipt_sha256': receipt_pin,
        'artifact_admission_sha256': admission_pin, 'compile_artifact_origin': origin,
        'compiler_supplier_files': len(closure),
        'compiler_supplier_closure_sha256': sha(encoded(closure)), 'map_binary': binary,
        'unchanged_historical_verifier_executed': True,
        'historical_raw_and_Git_suppliers_verified': True,
        'current_raw_and_Git_compiler_suppliers_equal': True,
        'original_compile_receipt_preserved': True, 'compiler_reexecuted': False,
        'accepted_qualifiers_reexecuted': False, 'runtime_executed': False,
        'normal_authentication_qualified': False, 'world_authority': False}
    return receipt, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'historical-source-root', 'compile-directory'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('source-revision', 'historical-source-revision', 'receipt-sha256', 'artifact-admission-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    import importlib.util
    filename = path(args.source_root) / RECIPE
    spec = importlib.util.spec_from_file_location('coh_server_initial_map_recipe', filename)
    recipe = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = recipe
    spec.loader.exec_module(recipe)
    _, proof = verify(recipe, args.compile_directory, args.source_root, args.source_revision,
                      args.historical_source_root, args.historical_source_revision, args.receipt_sha256,
                      args.artifact_admission_sha256)
    print(encoded(proof).decode(), end='')


if __name__ == '__main__':
    main()

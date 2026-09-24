#!/usr/bin/env python3
"""Stage a separately identified, data-only DB schema generator source tree.

The immutable source and PostgreSQL patch are verified by prepare_pg_source.py.
The additional patch preserves the ordinary definition loaders and DB serializers
while bypassing binary animation binding and Mission Architect animation metadata
only for -dbtemplatesonly. This is not a reference gameplay build. Output equality
with asset-complete -templates, and gameplay/runtime compatibility, remain untested.

Source dependency review: MapServer/src/svr/svr_init.c:loadConfigFiles;
Common/seq/seqload.c:seqInitializePostLoad; Common/seq/tricks.c:setupTrick;
Common/storyarc/playerCreatedStoryarcValidate.c:playerCreatedStoryArc_GenerateData;
MapServer/src/container/containerloadsave.c:attributeNames/containerWriteTemplates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from prepare_runtime import expected_pg_receipt, pg_receipt_matches, require, sha256

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/schema-generation/0001-data-only-db-templates.patch'
RECEIPT = 'schema-generation-build-input.json'
SCHEMA_FILES = (
    'MapServer/src/cmdparse/cmdserver.h',
    'MapServer/src/svr/svr_init.c',
    'Common/seq/tricks.c',
)


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def patch_bytes(root):
    patch = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in patch.decode('utf-8').splitlines() if line.startswith('+++ b/')]
    require(len(names) == len(SCHEMA_FILES) and set(names) == set(SCHEMA_FILES),
            'Unexpected schema patch file list')
    return patch


def apply_patch(source, patch):
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(name, None)
    env['GIT_CEILING_DIRECTORIES'] = str(source.parent)
    command = ['git', '-c', 'core.autocrlf=false', 'apply']
    subprocess.run(command + ['--check', '-'], input=patch, cwd=source, env=env,
                   check=True, capture_output=True)
    subprocess.run(command + ['-'], input=patch, cwd=source, env=env,
                   check=True, capture_output=True)


def expected_schema_receipt(root=ROOT, postgresql_build_input=None):
    """Reproduce expected hashes using only patch-touched files, never upstream edits."""
    lock = json.loads((root / 'upstream-lock.json').read_text())
    pg = expected_pg_receipt(root, lock)
    if postgresql_build_input is not None:
        require(pg_receipt_matches(postgresql_build_input, pg, root),
                'PostgreSQL build receipt mismatch')
        # Preserve actual source-checkout overlay bytes (including Windows Git
        # CRLF conversion) after matching only the explicitly accepted profiles.
        pg = postgresql_build_input
    require(not set(SCHEMA_FILES).intersection(pg['patched_sha256']),
            'Schema and PostgreSQL patches overlap; explicit rebase required')
    patch = patch_bytes(root)
    original = {}
    with tempfile.TemporaryDirectory(prefix='coh-schema-receipt-') as temporary:
        staging = Path(temporary)
        for name in SCHEMA_FILES:
            source = root / lock['destination'] / name
            require(source.is_file() and not source.is_symlink(), 'Missing schema source: ' + name)
            original[name] = sha256(source)
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        apply_patch(staging, patch)
        modified = {name: sha256(staging / name) for name in SCHEMA_FILES}
    require(all(modified[name] != original[name] for name in SCHEMA_FILES),
            'Schema patch left an expected file unchanged')
    return {
        'schema_version': 1,
        'build_role': 'data_only_db_schema_generation',
        'source_commit': lock['commit'],
        'postgresql_build_input_canonical_sha256': canonical_hash(pg),
        'postgresql_build_input': pg,
        'schema_patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': original,
        'patched_sha256': modified,
        'command_flag': '-dbtemplatesonly',
        'serializer_equivalence': 'unverified',
        'runtime_validation': 'unverified',
    }


def apply_schema_overlay(source, root=ROOT):
    """Apply to a verified PG staging tree; never accept a partially changed input."""
    source = source.resolve()
    require(source != root.resolve() and (root / 'upstream').resolve() not in source.parents,
            'Schema patch may not modify the immutable snapshots')
    require(not (source / RECEIPT).exists(), 'Schema receipt already exists; use a fresh staging tree')
    pg_path = source / 'postgresql-build-input.json'
    require(pg_path.is_file() and not pg_path.is_symlink(), 'Missing PostgreSQL build receipt')
    actual_pg = json.loads(pg_path.read_text())
    expected = expected_schema_receipt(root, postgresql_build_input=actual_pg)
    inputs = dict(expected['source_sha256'])
    inputs.update(actual_pg['patched_sha256'])
    inputs.update(actual_pg['overlay_sha256'])
    for name, digest in inputs.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                'Staged source SHA-256 mismatch: ' + name)
    apply_patch(source, patch_bytes(root))
    require({name: sha256(source / name) for name in SCHEMA_FILES} == expected['patched_sha256'],
            'Applied schema patch hashes differ from expected receipt')
    (source / RECEIPT).write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def prepare(output, root=ROOT):
    output = output.resolve()
    require(not output.exists() and not output.is_symlink(), 'Output must be a new directory')
    require(output != root.resolve() and (root / 'upstream').resolve() not in output.parents,
            'Output must be outside the immutable snapshots')
    subprocess.run([sys.executable, str(root / 'tools/prepare_pg_source.py'),
                    '--output', str(output)], check=True)
    return apply_schema_overlay(output, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.output)
    print('Prepared DATA-ONLY SCHEMA source (not reference gameplay):', args.output)


if __name__ == '__main__':
    main()

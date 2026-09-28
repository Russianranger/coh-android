#!/usr/bin/env python3
"""Prepare a separately receipted Wine DbServer after the stock PostgreSQL patch."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from prepare_runtime import expected_pg_receipt, pg_receipt_matches, require, sha256
from prepare_schema_source import apply_patch, canonical_hash

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/wine-dbserver/0001-wine-odbc.patch'
OVERLAY = 'database/wine-dbserver/overlay'
RECEIPT = 'wine-dbserver-build-input.json'
WINE_FILES = ('Common/sql/sqlinclude.h', 'DBServer/CMakeLists.txt', 'DBServer/src/dbinit.c',
              'libs/UtilitiesLib/src/utils/FolderCache.c',
              'libs/UtilitiesLib/include/utilitieslib/utils/FolderCache.h')
OVERLAY_FILES = ('Common/sql/wine_odbc.c', 'Common/sql/wine_odbc.h',
                 'DBServer/src/wine_dispatch_progress.c', 'DBServer/src/wine_dispatch_progress.h',
                 'DBServer/src/wine_fixed_inputs.c', 'DBServer/src/wine_fixed_inputs.h')
WINE_COMMIT = 'b073859675060c9211fcbccfd90e4e87520dc2c2'
REQUIRED_IMPORTS = ('SQLDriverConnect', 'SQLExecDirect', 'SQLPrepare', 'SQLGetDiagRecA',
                    'SQLGetInfoW', 'SQLColumnsW', 'SQLTablesW', 'SQLForeignKeysW')
FORBIDDEN_IMPORTS = ('SQLDriverConnectA', 'SQLExecDirectA', 'SQLPrepareA', 'SQLGetInfo',
                     'SQLGetInfoA', 'SQLColumns', 'SQLColumnsA', 'SQLTables', 'SQLTablesA',
                     'SQLForeignKeys', 'SQLForeignKeysA')


def patch_bytes(root):
    value = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in value.decode('utf-8').splitlines() if line.startswith('+++ b/')]
    require(len(names) == len(WINE_FILES) and set(names) == set(WINE_FILES),
            'Unexpected Wine patch file list')
    return value


def overlay_bytes(root):
    directory = root / OVERLAY
    names = tuple(path.relative_to(directory).as_posix() for path in sorted(directory.rglob('*'))
                  if path.is_file())
    require(set(names) == set(OVERLAY_FILES), 'Unexpected Wine overlay file list')
    result = {}
    for name in names:
        path = directory / name
        require(not path.is_symlink(), 'Wine overlay must not contain linked files')
        result[name] = path.read_bytes().replace(b'\r\n', b'\n')
    return result


def dispatch_progress_metadata(contents):
    """Publish stage names from the hash-bound C enum, not a second stage list."""
    header = contents['DBServer/src/wine_dispatch_progress.h'].decode('utf-8')
    entries = re.findall(r'^    COH_DB_STAGE_([A-Z0-9_]+) = (\d+),?$', header, re.MULTILINE)
    ids = [int(number) for _, number in entries]
    require(ids == list(range(1, len(entries) + 1)) and len(set(name for name, _ in entries)) == len(entries),
            'Dispatch progress stages must have unique contiguous positive IDs')
    require(entries and entries[-1][0] == 'READY', 'Dispatch progress stage count marker changed')
    return {
        'environment_variable': 'COH_WINE_DB_PROGRESS',
        'format': 1, 'record_bytes': 128, 'mapping_bytes': 4096,
        'magic_hex': b'COHDBP1\0'.hex(), 'byte_order': 'little',
        'offsets': {'magic': 0, 'format': 8, 'record_bytes': 12, 'process_id': 16,
                    'main_thread_id': 20, 'sequence': 24, 'stage': 28,
                    'loop_count': 32, 'flags': 36, 'stage_count': 40, 'reserved': 44},
        'stages': {number: name for name, number in entries},
        'disabled_by_default': True, 'writer': 'dbserver_main_thread',
        'stage_semantics': 'operation_about_to_run',
        'sequence_semantics': 'positive_even_stable_odd_updating_no_wrap',
        'flags': {'1': 'sequence_saturated_samples_unavailable'},
        'initialization_failure': 'requested_normal_launch_exits_nonzero',
        'file_creation': 'new_absolute_drive_path_private_parent_required',
        'proves_sql_or_game_success': False,
    }


def fixed_inputs_metadata(contents):
    header = contents['DBServer/src/wine_fixed_inputs.h'].decode('utf-8')
    constants = dict(re.findall(r'^#define (COH_DB_FIXED_INPUTS_\w+) "([^"\n]+)"$', header, re.MULTILINE))
    require(set(constants) == {'COH_DB_FIXED_INPUTS_ENVIRONMENT', 'COH_DB_FIXED_INPUTS_ACK'},
            'Unexpected fixed-input mode header contract')
    return {
        'environment_variable': constants['COH_DB_FIXED_INPUTS_ENVIRONMENT'],
        'enabled_value': '1', 'disabled_by_default': True,
        'activation': 'before_first_folder_cache_create',
        'watcher_registration': 'disabled', 'notification_updates': 'disabled',
        'initial_reads': 'preserved', 'lookup_mode': 'preserved',
        'startup_acknowledgement': constants['COH_DB_FIXED_INPUTS_ACK'],
        'proves_generic_notification_fix': False,
    }


def expected_wine_receipt(root=ROOT, postgresql_build_input=None):
    lock = json.loads((root / 'upstream-lock.json').read_text())
    pg = expected_pg_receipt(root, lock)
    if postgresql_build_input is not None:
        require(pg_receipt_matches(postgresql_build_input, pg, root), 'PostgreSQL build receipt mismatch')
        pg = postgresql_build_input
    wine_patch = patch_bytes(root)
    contents = overlay_bytes(root)
    pg_patch = (root / 'patches/postgresql/0001-dbserver-postgresql.patch').read_bytes().replace(b'\r\n', b'\n')
    # CMakeLists overlaps the PG patch: reproduce PG first, then the Wine patch.
    with tempfile.TemporaryDirectory(prefix='coh-wine-dbserver-receipt-') as temporary:
        stage = Path(temporary)
        for name in set(WINE_FILES).union(pg['patched_sha256']):
            original = root / lock['destination'] / name
            require(original.is_file() and not original.is_symlink(), 'Missing immutable source: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
        apply_patch(stage, pg_patch)
        inputs = {name: sha256(stage / name) for name in WINE_FILES}
        apply_patch(stage, wine_patch)
        outputs = {name: sha256(stage / name) for name in WINE_FILES}
    require(all(outputs[name] != inputs[name] for name in WINE_FILES),
            'Wine patch left an expected file unchanged')
    return {
        'schema_version': 1, 'build_role': 'wine_dbserver', 'source_commit': lock['commit'],
        'postgresql_build_input': pg,
        'postgresql_build_input_canonical_sha256': canonical_hash(pg),
        'wine_patch_sha256': hashlib.sha256(wine_patch).hexdigest(),
        'wine_overlay_sha256': {name: hashlib.sha256(value).hexdigest()
                               for name, value in contents.items()},
        'source_sha256': inputs, 'patched_sha256': outputs,
        'compile_definitions': {'DbServer': ['COH_WINE_ODBC=1']},
        'wine_commit': WINE_COMMIT,
        'odbc_imports': {'required': list(REQUIRED_IMPORTS), 'forbidden': list(FORBIDDEN_IMPORTS)},
        'persistence_configurations': ['OFF', 'ON'],
        'fixture_startup': {'initialize_file_cache_and_log_before_sql_workers': True,
                            'assert_mode': 'stderr_and_exit', 'log_directory': 'pg-persistence-test'},
        'dispatch_progress': dispatch_progress_metadata(contents),
        'fixed_inputs': fixed_inputs_metadata(contents),
        'runtime_validation': 'unverified',
    }


def apply_wine_overlay(source, root=ROOT):
    source, root = source.resolve(), root.resolve()
    require(source not in (root, (root / 'upstream').resolve())
            and (root / 'upstream').resolve() not in source.parents,
            'Wine overlay may not modify immutable snapshots')
    require(not (source / RECEIPT).exists() and not (source / RECEIPT).is_symlink(),
            'Wine receipt already exists; use a fresh staging tree')
    pg_path = source / 'postgresql-build-input.json'
    require(pg_path.is_file() and not pg_path.is_symlink(), 'Missing PostgreSQL build receipt')
    pg = json.loads(pg_path.read_text())
    expected = expected_wine_receipt(root, pg)
    inputs = dict(pg['patched_sha256'])
    inputs.update(pg['overlay_sha256'])
    inputs.update(expected['source_sha256'])
    for name, digest in inputs.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                'Staged source SHA-256 mismatch: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents if source in parent.parents),
                'Staged source parent is linked: ' + name)
    contents = overlay_bytes(root)
    for name in contents:
        target = source / name
        require(not target.exists() and not target.is_symlink(), 'Wine overlay would overwrite source: ' + name)
        require(not any(parent.is_symlink() for parent in target.parents), 'Wine overlay parent is linked')
    apply_patch(source, patch_bytes(root))
    require({name: sha256(source / name) for name in WINE_FILES} == expected['patched_sha256'],
            'Applied Wine patch hashes differ from receipt')
    for name, value in contents.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
    (source / RECEIPT).write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def prepare(output, root=ROOT):
    require(not output.exists() and not output.is_symlink(), 'Output must be a new directory')
    output = output.resolve()
    require(output != root.resolve() and (root / 'upstream').resolve() not in output.parents,
            'Output must be outside immutable snapshots')
    subprocess.run([sys.executable, str(root / 'tools/prepare_pg_source.py'), '--output', str(output)], check=True)
    return apply_wine_overlay(output, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.output)
    print('Prepared separately identified Wine DbServer source:', args.output)


if __name__ == '__main__':
    main()

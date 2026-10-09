#!/usr/bin/env python3
"""Package one narrowly patched normal DbServer above frozen Wine/Atlas inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import package_startup_dbserver as retained

ROOT = retained.ROOT
require = retained.require
PATCH = 'patches/startup-bundle/0001-pg-cancelled-child-insert.patch'
PATCHED_FILES = ('DBServer/src/container_sql.c',)
RECEIPT = 'startup-bundle-dbserver-build-input.json'
MANIFEST = retained.MANIFEST
ROLE = 'manual_atlas_dbserver_startup_bundle'
BASE_STARTUP_EXECUTABLE = {'bytes': 1663488,
    'sha256': '539afab70c6d57aef4b2230e607e218c7a77d31de7ad10ad89f0253f5c1a09d3'}
SOURCE_FILES = (PATCH, 'tools/android/interactive/package_startup_bundle_dbserver.py',
    'tools/android/interactive/test_startup_bundle_save.py',
    'tools/android/interactive/test_startup_bundle_dbserver.py')


def patch_bytes(root=ROOT):
    raw = (root/PATCH).read_bytes().replace(b'\r\n', b'\n')
    paths = [line[6:] for line in raw.decode().splitlines() if line.startswith('+++ b/')]
    require(tuple(paths) == PATCHED_FILES, 'Startup bundle patch changed unexpected native targets')
    return raw


def save_contract():
    return {'provider': 'PostgreSQL', 'table_type': 'TT_SUBCONTAINER',
        'scope': 'cancelled_provisional_child_INSERT_only',
        'match': 'next_command_with_identical_table_pointer_and_SubId_is_DELETE',
        'retained': ['matched_DELETE', 'all_other_row_commands', 'all_column_updates',
            'DELETE_then_INSERT_order', 'SQL_Server_provider', 'parent_container_inserts',
            'FIFO_transaction_commit_before_completion', 'save_ACK_after_SQL_completion',
            'permanent_failure_rollback_and_exit_without_ACK'],
        'ignored_SQL_failures': False, 'UPSERT': False, 'schema_migration': False,
        'profile_reset': False, 'android_execution_validated': False}


def expected_receipt(root=ROOT, base_startup_build_input=None):
    base = retained.expected_receipt(root,
        base_startup_build_input.get('base_wine_build_input') if base_startup_build_input else None)
    require(base_startup_build_input is None or base_startup_build_input == base,
            'Startup bundle must retain the exact accepted manual Atlas build input')
    patch = patch_bytes(root)
    pg = base['base_wine_build_input']['postgresql_build_input']
    with tempfile.TemporaryDirectory(prefix='coh-window-save-receipt-') as temporary:
        source = Path(temporary)
        for name in pg['patched_sha256']:
            target = source/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root/'upstream/ouroboros'/name, target)
        retained.wine.apply_patch(source, (root/'patches/postgresql/0001-dbserver-postgresql.patch')
                                  .read_bytes().replace(b'\r\n', b'\n'))
        inputs = {name: retained.wine.sha256(source/name) for name in PATCHED_FILES}
        require(inputs == {name: pg['patched_sha256'][name] for name in PATCHED_FILES},
                'Startup bundle starts from unexpected PostgreSQL source')
        retained.wine.apply_patch(source, patch)
        outputs = {name: retained.wine.sha256(source/name) for name in PATCHED_FILES}
    return {'format': 1, 'build_role': ROLE, 'source_commit': base['source_commit'],
        'base_startup_build_input_canonical_sha256': retained.canonical_hash(base),
        'patch': PATCH, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': inputs, 'patched_sha256': outputs,
        'unchanged_merger_sha256': retained.wine.sha256(root/'upstream/ouroboros/DBServer/src/container_merge.c'),
        'built_target': 'DbServer', 'configuration': 'OptDebug', 'architecture': 'Win32',
        'postgresql_persistence_fixture': False, 'save_contract': save_contract(),
        'runtime_validation': 'unverified'}


def source_closure(base, layer=None):
    wine = base['base_wine_build_input']; pg = wine['postgresql_build_input']
    result = dict(pg['patched_sha256'], **pg['overlay_sha256'])
    for records in (wine['patched_sha256'], wine['wine_overlay_sha256'],
                    base['patched_sha256'], base['overlay_sha256']):
        result.update(records)
    if layer: result.update(layer['patched_sha256'])
    return result


def verify_source(source, base, layer=None):
    for name, digest in source_closure(base, layer).items():
        require(retained.wine.sha256(source/name) == digest,
                'Startup bundle source changed: '+name)
    require(retained.wine.sha256(source/'DBServer/src/container_merge.c') ==
            retained.wine.sha256(ROOT/'upstream/ouroboros/DBServer/src/container_merge.c'),
            'Startup bundle may not change the production merger')


def apply_overlay(source, root=ROOT):
    source = source.resolve()
    require(source != root.resolve() and (root/'upstream').resolve() not in source.parents,
            'Startup bundle may not modify immutable snapshots')
    require(not (source/RECEIPT).exists(), 'Startup bundle receipt already exists')
    base = json.loads((source/retained.RECEIPT).read_text(encoding='utf-8-sig'))
    layer = expected_receipt(root, base)
    verify_source(source, base)
    retained.wine.apply_patch(source, patch_bytes(root))
    verify_source(source, base, layer)
    (source/RECEIPT).write_text(json.dumps(layer, indent=2)+'\n')
    return layer


def stage(args):
    retained.stage(args)
    return apply_overlay(args.output)


def package(args):
    require(re.fullmatch(r'[a-f0-9]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists(), 'Startup bundle package output must be new')
    base = json.loads((args.source/retained.RECEIPT).read_text(encoding='utf-8-sig'))
    layer = json.loads((args.source/RECEIPT).read_text(encoding='utf-8-sig'))
    require(layer == expected_receipt(ROOT, base), 'Startup bundle source receipt differs')
    verify_source(args.source, base, layer)
    cache = retained.validate_cache(args.cache)
    original = retained.qualified_base_manifest(args.base_manifest)
    require(original['wine_build_input'] == base['base_wine_build_input'],
            'Startup bundle baseline differs from the qualified donor')
    normal = original['variants']['normal']
    binary = retained.native.record(args.binary)
    require(binary['sha256'] != normal['files']['DbServer.exe']['sha256'],
            'Startup bundle executable is unchanged from the original donor')
    require(binary['sha256'] != BASE_STARTUP_EXECUTABLE['sha256'],
            'Startup bundle executable is unchanged from the retained startup supplement')
    functions = retained.native.imported_functions(args.binary.read_bytes())
    require(set(retained.wine.REQUIRED_IMPORTS) <= set(functions) and
            not set(retained.wine.FORBIDDEN_IMPORTS).intersection(functions),
            'Startup bundle executable ODBC imports differ')
    dependencies = retained.native.dependency_report(dict(normal['files'], **{'DbServer.exe': binary}))
    require(not dependencies['unresolved'], 'Startup bundle needs unavailable donor libraries')
    manifest = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': base['source_commit'],
        'base_package_manifest_sha256': retained.BASE_PACKAGE_SHA256,
        'base_normal_executable': normal['files']['DbServer.exe'],
        'base_startup_executable': BASE_STARTUP_EXECUTABLE,
        'retained_normal_files': {name: record for name, record in normal['files'].items() if name!='DbServer.exe'},
        'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256'],
        'files': {'DbServer.exe': binary}, 'build_input': base,
        'startup_bundle_build_input': layer, 'cmake_cache': cache,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'postgresql_persistence_fixture': False,
        'odbc_imports': functions, 'dependency_report': dependencies,
        'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
        'base_package_archive_changed': False, 'android_execution_validated': False,
        'gameplay_validated': False}
    args.output.mkdir(parents=True)
    shutil.copyfile(args.binary, args.output/'DbServer.exe')
    shutil.copyfile(args.cache, args.output/'CMakeCache.txt')
    (args.output/MANIFEST).write_text(json.dumps(manifest, indent=2)+'\n')
    validate_package(args.output, args.repository_commit)
    return manifest


def validate_package(directory, commit):
    require(directory.is_dir() and not directory.is_symlink(),
            'Invalid or linked startup bundle native package directory')
    for name in ('DbServer.exe', 'CMakeCache.txt', MANIFEST):
        path = directory/name
        require(path.is_file() and not path.is_symlink(),
                'Invalid or linked startup bundle native package leaf: '+name)
    require(set(path.name for path in directory.iterdir()) == {'DbServer.exe', 'CMakeCache.txt', MANIFEST},
            'Unexpected startup bundle native package inventory')
    value = json.loads((directory/MANIFEST).read_text())
    require(value.get('format') == 1 and value.get('role') == ROLE and
            value.get('repository_commit') == commit and
            value.get('replacement_scope') == 'fresh_owned_manual_atlas_runtime_DbServer.exe_only' and
            value.get('base_package_manifest_sha256') == retained.BASE_PACKAGE_SHA256 and
            value.get('base_package_archive_changed') is False and
            value.get('android_execution_validated') is False and value.get('gameplay_validated') is False,
            'Startup bundle native package provenance differs')
    base = value.get('build_input', {})
    require(base == retained.expected_receipt(ROOT, base.get('base_wine_build_input')),
            'Startup bundle relabeled its retained manual Atlas build input')
    require(value.get('startup_bundle_build_input') == expected_receipt(ROOT, base),
            'Startup bundle native source receipt differs')
    require(value.get('configuration') == 'OptDebug' and value.get('architecture') == 'Win32' and
            value.get('postgresql_persistence_fixture') is False and
            value.get('source_commit') == base['source_commit'], 'Startup bundle native build mode differs')
    require(value.get('base_startup_executable') == BASE_STARTUP_EXECUTABLE,
            'Startup bundle relabeled the retained startup supplement')
    require(value.get('files', {}).get('DbServer.exe', {}).get('sha256') != BASE_STARTUP_EXECUTABLE['sha256'],
            'Startup bundle executable is unchanged from the retained startup supplement')
    require(value.get('files') == {'DbServer.exe': retained.native.record(directory/'DbServer.exe')},
            'Startup bundle native executable differs')
    require(value.get('cmake_cache') == retained.validate_cache(directory/'CMakeCache.txt'),
            'Startup bundle native configuration differs')
    functions = retained.native.imported_functions((directory/'DbServer.exe').read_bytes())
    require(value.get('odbc_imports') == functions and
            set(retained.wine.REQUIRED_IMPORTS) <= set(functions) and
            not set(retained.wine.FORBIDDEN_IMPORTS).intersection(functions),
            'Startup bundle ODBC import receipt differs')
    original = retained.qualified_base_manifest(ROOT/retained.ACCEPTED_BASE_MANIFEST)['variants']['normal']
    require(value.get('base_normal_executable') == original['files']['DbServer.exe'] and
            value.get('base_normal_cmake_cache_sha256') == original['cmake_cache_sha256'] and
            value.get('retained_normal_files') == {name: record for name, record in original['files'].items() if name!='DbServer.exe'},
            'Startup bundle relabeled the qualified donor executable or dependencies')
    dependencies = retained.native.dependency_report(dict(value['retained_normal_files'], **value['files']))
    require(value.get('dependency_report') == dependencies and not dependencies['unresolved'],
            'Startup bundle native donor dependency closure differs')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('stage')
    prepare.add_argument('--output', type=Path, required=True)
    prepare.add_argument('--base-manifest', type=Path, required=True)
    build = commands.add_parser('package')
    for name in ('source', 'binary', 'cache', 'base-manifest', 'output'):
        build.add_argument('--'+name, type=Path, required=True)
    build.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    value = stage(args) if args.command=='stage' else package(args)
    print(json.dumps({'output': str(args.output), 'build_role': value.get('build_role', value.get('role'))}))


if __name__=='__main__':main()

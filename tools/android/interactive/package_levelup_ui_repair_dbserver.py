#!/usr/bin/env python3
"""Package the PostgreSQL empty-child-row read repair above frozen DbServer layers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import package_startup_bundle_dbserver as retained

ROOT = retained.ROOT
require = retained.require
PATCH = 'patches/levelup-ui-repair/0001-pg-empty-row-witness.patch'
PATCHED_FILES = ('DBServer/src/container_sql.c',)
RECEIPT = 'levelup-ui-repair-dbserver-build-input.json'
MANIFEST = retained.MANIFEST
ROLE = 'manual_atlas_dbserver_levelup_ui_repair'
BASE_STARTUP_BUNDLE_EXECUTABLE = {'bytes': 1664000,
    'sha256': 'baf97a253ddccf29575801f66ef56cb7ce75f168062bb0c4ffef796b419c2029'}
SOURCE_FILES = (PATCH, 'tools/android/interactive/package_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_dbserver.py')


def patch_bytes(root=ROOT):
    raw = (root/PATCH).read_bytes().replace(b'\r\n', b'\n')
    paths = [line[6:] for line in raw.decode().splitlines() if line.startswith('+++ b/')]
    require(tuple(paths) == PATCHED_FILES, 'Level-up read patch changed unexpected native targets')
    return raw


def save_contract():
    return {'provider': 'PostgreSQL', 'table_type': 'TT_SUBCONTAINER',
        'scope': 'physical_child_row_read_witness_and_order_only',
        'match': 'row_read_appends_no_non_default_field_compared_with_its_initial_line_count',
        'effect': 'retain_FAKE_STR_IDX_row_witness_before_later_diff_merge',
        'row_order': 'ORDER_BY_SubId_on_PostgreSQL_subcontainer_single_container_select_only',
        'retained': ['non_default_column_reads', 'SQL_Server_provider', 'parent_container_read_policy',
            'all_row_and_column_commands', 'cancelled_provisional_child_INSERT_filter',
            'FIFO_transaction_commit_before_completion', 'save_ACK_after_SQL_completion',
            'permanent_failure_rollback_and_exit_without_ACK'],
        'ignored_SQL_failures': False, 'UPSERT': False, 'schema_migration': False,
        'profile_reset': False, 'android_execution_validated': False}


def expected_receipt(root=ROOT, base_startup_build_input=None, base_startup_bundle_build_input=None):
    base = retained.retained.expected_receipt(root,
        base_startup_build_input.get('base_wine_build_input') if base_startup_build_input else None)
    require(base_startup_build_input is None or base_startup_build_input == base,
            'Level-up repair must retain the exact manual Atlas build input')
    bundle = retained.expected_receipt(root, base)
    require(base_startup_bundle_build_input is None or base_startup_bundle_build_input == bundle,
            'Level-up repair must retain the exact cancelled-child save build input')
    patch = patch_bytes(root)
    with tempfile.TemporaryDirectory(prefix='coh-levelup-read-receipt-') as temporary:
        source = Path(temporary)
        pg = base['base_wine_build_input']['postgresql_build_input']
        for name in pg['patched_sha256']:
            target = source/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root/'upstream/ouroboros'/name, target)
        retained.retained.wine.apply_patch(source,
            (root/'patches/postgresql/0001-dbserver-postgresql.patch').read_bytes().replace(b'\r\n', b'\n'))
        retained.retained.wine.apply_patch(source, retained.patch_bytes(root))
        inputs = {name: retained.retained.wine.sha256(source/name) for name in PATCHED_FILES}
        require(inputs == bundle['patched_sha256'], 'Level-up repair starts from unexpected save source')
        retained.retained.wine.apply_patch(source, patch)
        outputs = {name: retained.retained.wine.sha256(source/name) for name in PATCHED_FILES}
    return {'format': 1, 'build_role': ROLE, 'source_commit': base['source_commit'],
        'base_startup_build_input_canonical_sha256': retained.retained.canonical_hash(base),
        'base_startup_bundle_build_input_canonical_sha256': retained.retained.canonical_hash(bundle),
        'patch': PATCH, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': inputs, 'patched_sha256': outputs,
        'unchanged_merger_sha256': bundle['unchanged_merger_sha256'],
        'unchanged_fifo_sha256': base['base_wine_build_input']['postgresql_build_input']['patched_sha256']['DBServer/src/sql_fifo.c'],
        'built_target': 'DbServer', 'configuration': 'OptDebug', 'architecture': 'Win32',
        'postgresql_persistence_fixture': False, 'save_contract': save_contract(),
        'runtime_validation': 'unverified'}


def source_closure(base, bundle_layer=None, layer=None):
    result = retained.source_closure(base, bundle_layer or retained.expected_receipt(ROOT, base))
    if layer: result.update(layer['patched_sha256'])
    return result


def verify_source(source, base, bundle_layer, layer=None):
    for name, digest in source_closure(base, bundle_layer, layer).items():
        require(retained.retained.wine.sha256(source/name) == digest,
                'Level-up source changed: '+name)
    require(retained.retained.wine.sha256(source/'DBServer/src/container_merge.c') ==
            bundle_layer['unchanged_merger_sha256'], 'Level-up repair changed the production merger')


def apply_overlay(source, root=ROOT):
    source = source.resolve()
    require(source != root.resolve() and (root/'upstream').resolve() not in source.parents,
            'Level-up repair may not modify immutable snapshots')
    require(not (source/RECEIPT).exists(), 'Level-up repair receipt already exists')
    base = json.loads((source/retained.retained.RECEIPT).read_text(encoding='utf-8-sig'))
    bundle = json.loads((source/retained.RECEIPT).read_text(encoding='utf-8-sig'))
    layer = expected_receipt(root, base, bundle)
    verify_source(source, base, bundle)
    retained.retained.wine.apply_patch(source, patch_bytes(root))
    verify_source(source, base, bundle, layer)
    (source/RECEIPT).write_text(json.dumps(layer, indent=2)+'\n')
    return layer


def stage(args):
    retained.stage(args)
    return apply_overlay(args.output)


def package(args):
    require(re.fullmatch(r'[a-f0-9]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists(), 'Level-up native package output must be new')
    base = json.loads((args.source/retained.retained.RECEIPT).read_text(encoding='utf-8-sig'))
    bundle = json.loads((args.source/retained.RECEIPT).read_text(encoding='utf-8-sig'))
    layer = json.loads((args.source/RECEIPT).read_text(encoding='utf-8-sig'))
    require(layer == expected_receipt(ROOT, base, bundle), 'Level-up native source receipt differs')
    verify_source(args.source, base, bundle, layer)
    cache = retained.retained.validate_cache(args.cache)
    original = retained.retained.qualified_base_manifest(args.base_manifest)
    require(original['wine_build_input'] == base['base_wine_build_input'], 'Level-up native donor differs')
    normal = original['variants']['normal']
    binary = retained.retained.native.record(args.binary)
    require(binary['sha256'] not in {normal['files']['DbServer.exe']['sha256'],
            retained.BASE_STARTUP_EXECUTABLE['sha256'], BASE_STARTUP_BUNDLE_EXECUTABLE['sha256']},
            'Level-up executable is unchanged from a retained donor')
    functions = retained.retained.native.imported_functions(args.binary.read_bytes())
    require(set(retained.retained.wine.REQUIRED_IMPORTS) <= set(functions) and
            not set(retained.retained.wine.FORBIDDEN_IMPORTS).intersection(functions),
            'Level-up executable ODBC imports differ')
    dependencies = retained.retained.native.dependency_report(dict(normal['files'], **{'DbServer.exe': binary}))
    require(not dependencies['unresolved'], 'Level-up executable needs unavailable donor libraries')
    manifest = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': base['source_commit'], 'base_package_manifest_sha256': retained.retained.BASE_PACKAGE_SHA256,
        'base_normal_executable': normal['files']['DbServer.exe'],
        'base_startup_executable': retained.BASE_STARTUP_EXECUTABLE,
        'base_startup_bundle_executable': BASE_STARTUP_BUNDLE_EXECUTABLE,
        'retained_normal_files': {name: record for name, record in normal['files'].items() if name!='DbServer.exe'},
        'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256'],
        'files': {'DbServer.exe': binary}, 'build_input': base,
        'startup_bundle_build_input': bundle, 'levelup_ui_repair_build_input': layer, 'cmake_cache': cache,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'postgresql_persistence_fixture': False,
        'odbc_imports': functions, 'dependency_report': dependencies,
        'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
        'base_package_archive_changed': False, 'android_execution_validated': False, 'gameplay_validated': False}
    args.output.mkdir(parents=True)
    shutil.copyfile(args.binary, args.output/'DbServer.exe')
    shutil.copyfile(args.cache, args.output/'CMakeCache.txt')
    (args.output/MANIFEST).write_text(json.dumps(manifest, indent=2)+'\n')
    validate_package(args.output, args.repository_commit)
    return manifest


def validate_package(directory, commit):
    require(directory.is_dir() and not directory.is_symlink(), 'Invalid or linked level-up native package directory')
    names = {'DbServer.exe', 'CMakeCache.txt', MANIFEST}
    require({path.name for path in directory.iterdir()} == names, 'Unexpected level-up native package inventory')
    for name in names:
        path = directory/name
        require(path.is_file() and not path.is_symlink(), 'Invalid or linked level-up native package leaf: '+name)
    value = json.loads((directory/MANIFEST).read_text())
    require(value.get('format') == 1 and value.get('role') == ROLE and value.get('repository_commit') == commit and
        value.get('replacement_scope') == 'fresh_owned_manual_atlas_runtime_DbServer.exe_only' and
        value.get('base_package_manifest_sha256') == retained.retained.BASE_PACKAGE_SHA256 and
        value.get('base_package_archive_changed') is False and value.get('android_execution_validated') is False and
        value.get('gameplay_validated') is False, 'Level-up native package provenance differs')
    base = value.get('build_input', {})
    require(base == retained.retained.expected_receipt(ROOT, base.get('base_wine_build_input')),
            'Level-up native package relabeled its manual Atlas ancestry')
    bundle = value.get('startup_bundle_build_input', {})
    require(bundle == retained.expected_receipt(ROOT, base), 'Level-up native package relabeled its save ancestry')
    require(value.get('levelup_ui_repair_build_input') == expected_receipt(ROOT, base, bundle),
            'Level-up native package source receipt differs')
    require(value.get('configuration') == 'OptDebug' and value.get('architecture') == 'Win32' and
        value.get('postgresql_persistence_fixture') is False and value.get('source_commit') == base['source_commit'],
        'Level-up native build mode differs')
    require(value.get('base_startup_executable') == retained.BASE_STARTUP_EXECUTABLE and
            value.get('base_startup_bundle_executable') == BASE_STARTUP_BUNDLE_EXECUTABLE,
            'Level-up native package relabeled its prior executable')
    binary = retained.retained.native.record(directory/'DbServer.exe')
    require(value.get('files') == {'DbServer.exe': binary} and binary['sha256'] not in
            {retained.BASE_STARTUP_EXECUTABLE['sha256'], BASE_STARTUP_BUNDLE_EXECUTABLE['sha256']},
            'Level-up native executable differs or is unchanged')
    require(value.get('cmake_cache') == retained.retained.validate_cache(directory/'CMakeCache.txt'),
            'Level-up native configuration differs')
    functions = retained.retained.native.imported_functions((directory/'DbServer.exe').read_bytes())
    require(value.get('odbc_imports') == functions and set(retained.retained.wine.REQUIRED_IMPORTS) <= set(functions) and
            not set(retained.retained.wine.FORBIDDEN_IMPORTS).intersection(functions), 'Level-up ODBC imports differ')
    original = retained.retained.qualified_base_manifest(ROOT/retained.retained.ACCEPTED_BASE_MANIFEST)['variants']['normal']
    require(value.get('base_normal_executable') == original['files']['DbServer.exe'] and
        value.get('base_normal_cmake_cache_sha256') == original['cmake_cache_sha256'] and
        value.get('retained_normal_files') == {name: record for name, record in original['files'].items() if name!='DbServer.exe'},
        'Level-up native package relabeled its donor executable or dependencies')
    require(binary['sha256'] != original['files']['DbServer.exe']['sha256'], 'Level-up executable is unchanged')
    dependencies = retained.retained.native.dependency_report(dict(value['retained_normal_files'], **value['files']))
    require(value.get('dependency_report') == dependencies and not dependencies['unresolved'],
            'Level-up native dependency closure differs')
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


if __name__ == '__main__': main()

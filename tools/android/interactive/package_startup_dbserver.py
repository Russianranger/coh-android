#!/usr/bin/env python3
"""Stage and package a DbServer-only supplement for explicit manual Atlas startup."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/android/dbserver'))
import prepare_wine_dbserver_source as wine
import package_dbserver as native
from prepare_schema_source import canonical_hash

require = wine.require
PATCH = 'patches/startup-dbserver/0001-manual-atlas-launcher-wait.patch'
OVERLAY = 'database/startup-dbserver/overlay'
RECEIPT = 'startup-dbserver-build-input.json'
MANIFEST = 'startup-dbserver-manifest.json'
PATCHED_FILES = ('DBServer/CMakeLists.txt', 'DBServer/src/dbinit.c')
OVERLAY_FILES = ('DBServer/src/wine_manual_atlas.c', 'DBServer/src/wine_manual_atlas.h')
BASE_PACKAGE_SHA256 = '95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6'
ACCEPTED_BASE_MANIFEST = 'docs/android-evidence/dbserver-package-36460867428.json'


def file_record(path):
    require(path.is_file() and not path.is_symlink(), 'Invalid startup DbServer file: ' + str(path))
    return {'bytes': path.stat().st_size, 'sha256': wine.sha256(path)}


def patch_bytes(root=ROOT):
    value = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    paths = [line[6:] for line in value.decode().splitlines() if line.startswith('+++ b/')]
    require(tuple(paths) == PATCHED_FILES, 'Manual Atlas patch changed unexpected native targets')
    return value


def overlay_bytes(root=ROOT):
    directory = root / OVERLAY
    paths = tuple(path.relative_to(directory).as_posix() for path in sorted(directory.rglob('*'))
                  if path.is_file())
    require(set(paths) == set(OVERLAY_FILES), 'Manual Atlas overlay inventory differs')
    return {name: (directory / name).read_bytes().replace(b'\r\n', b'\n') for name in OVERLAY_FILES}


def launcher_wait_contract(root=ROOT):
    header = overlay_bytes(root)['DBServer/src/wine_manual_atlas.h'].decode()
    constants = dict(re.findall(r'^#define (COH_DB_MANUAL_ATLAS_\w+) "([^"\n]+)"$', header, re.M))
    require(set(constants) == {'COH_DB_MANUAL_ATLAS_ENVIRONMENT', 'COH_DB_MANUAL_ATLAS_ACK'},
            'Manual Atlas native environment contract differs')
    return {'environment_variable': constants['COH_DB_MANUAL_ATLAS_ENVIRONMENT'],
        'enabled_value': '1', 'disabled_by_default': True,
        'startup_acknowledgement': constants['COH_DB_MANUAL_ATLAS_ACK'],
        'required_native_configuration': {'start_static': 0, 'fake_auth': True,
            'auth_server_present': False, 'queue_server': False, 'use_logserver': 0,
            'launcher_count': 0, 'launchers_connecting': False,
            'COH_WINE_DB_FIXED_INPUTS': '1', 'COH_WINE_DB_LOOPBACK_ONLY': '1'},
        'activation': 'after_launcher_listener_before_connection_wait',
        'skipped_operation': 'unused_launcher_connection_wait_only',
        'original_minimum_wait_seconds': 15,
        'preserved': ['launcher_listener', 'server_auto_start', 'static_map_list_initialization',
            'remaining_db_init', 'sql_fifo_finish', 'dispatch_main_loop', 'mapserver_readiness'],
        'invalid_request': 'exit_2_before_launcher_wait', 'android_execution_validated': False}


def expected_receipt(root=ROOT, base_wine_build_input=None):
    expected_wine = wine.expected_wine_receipt(root,
        base_wine_build_input.get('postgresql_build_input') if base_wine_build_input else None)
    require(base_wine_build_input is None or base_wine_build_input == expected_wine,
            'Supplement must start from the unchanged Wine DbServer build input')
    patch = patch_bytes(root)
    overlay = overlay_bytes(root)
    pg = expected_wine['postgresql_build_input']
    with tempfile.TemporaryDirectory(prefix='coh-manual-atlas-receipt-') as temporary:
        stage_root = Path(temporary)
        for name in set(wine.WINE_FILES).union(pg['patched_sha256']):
            target = stage_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / 'upstream/ouroboros' / name, target)
        wine.apply_patch(stage_root, (root / 'patches/postgresql/0001-dbserver-postgresql.patch')
                         .read_bytes().replace(b'\r\n', b'\n'))
        wine.apply_patch(stage_root, wine.patch_bytes(root))
        inputs = {name: wine.sha256(stage_root / name) for name in PATCHED_FILES}
        require(inputs == {name: expected_wine['patched_sha256'][name] for name in PATCHED_FILES},
                'Supplement starts from unexpected patched Wine source')
        wine.apply_patch(stage_root, patch)
        outputs = {name: wine.sha256(stage_root / name) for name in PATCHED_FILES}
    return {'format': 1, 'build_role': 'manual_atlas_dbserver_startup_supplement',
        'source_commit': expected_wine['source_commit'],
        'base_wine_build_input': expected_wine,
        'base_wine_build_input_canonical_sha256': canonical_hash(expected_wine),
        'patch': PATCH, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'overlay_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in overlay.items()},
        'source_sha256': inputs, 'patched_sha256': outputs,
        'built_target': 'DbServer', 'configuration': 'OptDebug', 'architecture': 'Win32',
        'postgresql_persistence_fixture': False, 'launcher_wait': launcher_wait_contract(root),
        'runtime_validation': 'unverified'}


def apply_overlay(source, root=ROOT):
    source = source.resolve()
    require(source != root.resolve() and (root / 'upstream').resolve() not in source.parents,
            'Manual Atlas overlay may not modify immutable snapshots')
    require(not (source / RECEIPT).exists(), 'Manual Atlas receipt already exists')
    base = json.loads((source / wine.RECEIPT).read_text(encoding='utf-8-sig'))
    receipt = expected_receipt(root, base)
    for name, digest in dict(base['patched_sha256'], **base['wine_overlay_sha256']).items():
        require(wine.sha256(source / name) == digest, 'Base Wine source changed: ' + name)
    contents = overlay_bytes(root)
    for name in contents:
        require(not (source / name).exists() and not (source / name).is_symlink(),
                'Manual Atlas overlay would overwrite existing source')
    wine.apply_patch(source, patch_bytes(root))
    for name, value in contents.items():
        (source / name).write_bytes(value)
    require({name: wine.sha256(source / name) for name in PATCHED_FILES} == receipt['patched_sha256'],
            'Applied manual Atlas source differs from receipt')
    (source / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def qualified_base_manifest(path):
    require(file_record(path)['sha256'] == BASE_PACKAGE_SHA256,
            'Startup supplement requires the exact accepted donor package manifest')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def align_base_profile(source, base_manifest):
    """Reproduce the donor's accepted PG overlay LF/CRLF bytes on either host."""
    base = qualified_base_manifest(base_manifest)['wine_build_input']
    require(base == wine.expected_wine_receipt(ROOT, base.get('postgresql_build_input')),
            'Qualified donor base differs from the unchanged Wine source')
    current = json.loads((source / wine.RECEIPT).read_text(encoding='utf-8-sig'))
    require(current == wine.expected_wine_receipt(ROOT, current.get('postgresql_build_input')),
            'Staged base Wine source receipt differs')
    for name, digest in base['postgresql_build_input']['overlay_sha256'].items():
        path = source / name
        require(file_record(path)['sha256'] == current['postgresql_build_input']['overlay_sha256'][name],
                'PG overlay changed before donor profile alignment: ' + name)
        value = path.read_bytes().replace(b'\r\n', b'\n')
        candidates = (value, value.replace(b'\n', b'\r\n'))
        selected = next((candidate for candidate in candidates if hashlib.sha256(candidate).hexdigest() == digest), None)
        require(selected is not None, 'Unsupported qualified PG overlay byte profile: ' + name)
        path.write_bytes(selected)
    (source / 'postgresql-build-input.json').write_text(json.dumps(base['postgresql_build_input'], indent=2) + '\n')
    (source / wine.RECEIPT).write_text(json.dumps(base, indent=2) + '\n')
    return base


def stage(args):
    wine.prepare(args.output)
    align_base_profile(args.output, args.base_manifest)
    return apply_overlay(args.output)


def validate_cache(path):
    text = path.read_text(encoding='utf-8-sig')
    require(re.search(r'^COH_PG_PERSISTENCE_TESTS:BOOL=OFF$', text, re.M),
            'Startup supplement must be a normal DbServer build')
    require(re.search(r'^CMAKE_GENERATOR_PLATFORM:INTERNAL=Win32$', text, re.M),
            'Startup supplement must target Win32')
    return file_record(path)


def package(args):
    require(re.fullmatch(r'[a-f0-9]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists(), 'Startup package output must be new')
    source = args.source
    receipt = json.loads((source / RECEIPT).read_text(encoding='utf-8-sig'))
    require(receipt == expected_receipt(ROOT, receipt.get('base_wine_build_input')),
            'Startup source receipt differs from current isolated overlay')
    base_wine = receipt['base_wine_build_input']
    pg = base_wine['postgresql_build_input']
    source_hashes = dict(pg['patched_sha256'], **pg['overlay_sha256'])
    source_hashes.update(base_wine['patched_sha256'])
    source_hashes.update(base_wine['wine_overlay_sha256'])
    source_hashes.update(receipt['patched_sha256'])
    source_hashes.update(receipt['overlay_sha256'])
    for name, digest in source_hashes.items():
        require(wine.sha256(source / name) == digest, 'Startup source changed before package: ' + name)
    cache = validate_cache(args.cache)
    base = qualified_base_manifest(args.base_manifest)
    require(base['wine_build_input'] == receipt['base_wine_build_input'],
            'Supplement base Wine receipt differs from the qualified donor')
    original = base['variants']['normal']
    binary = native.record(args.binary)
    require(binary['sha256'] != original['files']['DbServer.exe']['sha256'],
            'Startup executable is unchanged from the donor')
    functions = native.imported_functions(args.binary.read_bytes())
    require(set(wine.REQUIRED_IMPORTS) <= set(functions)
            and not set(wine.FORBIDDEN_IMPORTS).intersection(functions),
            'Startup executable ODBC import contract differs')
    closure = dict(original['files'], **{'DbServer.exe': binary})
    dependencies = native.dependency_report(closure)
    require(not dependencies['unresolved'], 'Startup executable needs unavailable donor libraries')
    manifest = {'format': 1, 'role': 'manual_atlas_dbserver_startup_supplement',
        'repository_commit': args.repository_commit, 'source_commit': receipt['source_commit'],
        'base_package_manifest_sha256': BASE_PACKAGE_SHA256,
        'base_normal_executable': original['files']['DbServer.exe'],
        'retained_normal_files': {name: record for name, record in original['files'].items()
                                  if name != 'DbServer.exe'},
        'base_normal_cmake_cache_sha256': original['cmake_cache_sha256'],
        'files': {'DbServer.exe': binary}, 'build_input': receipt, 'cmake_cache': cache,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'postgresql_persistence_fixture': False,
        'odbc_imports': functions, 'dependency_report': dependencies,
        'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
        'base_package_archive_changed': False, 'android_execution_validated': False,
        'gameplay_validated': False}
    args.output.mkdir(parents=True)
    shutil.copyfile(args.binary, args.output / 'DbServer.exe')
    shutil.copyfile(args.cache, args.output / 'CMakeCache.txt')
    (args.output / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
    validate_package(args.output, args.repository_commit)
    return manifest


def validate_package(directory, commit):
    require(set(path.name for path in directory.iterdir()) == {'DbServer.exe', 'CMakeCache.txt', MANIFEST},
            'Unexpected startup DbServer package inventory')
    value = json.loads((directory / MANIFEST).read_text())
    require(value.get('format') == 1 and value.get('role') == 'manual_atlas_dbserver_startup_supplement'
            and value.get('repository_commit') == commit
            and value.get('replacement_scope') == 'fresh_owned_manual_atlas_runtime_DbServer.exe_only'
            and value.get('base_package_archive_changed') is False
            and value.get('base_package_manifest_sha256') == BASE_PACKAGE_SHA256
            and value.get('android_execution_validated') is False and value.get('gameplay_validated') is False,
            'Startup DbServer package provenance differs')
    receipt = value.get('build_input', {})
    require(receipt == expected_receipt(ROOT, receipt.get('base_wine_build_input')),
            'Startup package source receipt differs')
    require(value.get('configuration') == 'OptDebug' and value.get('architecture') == 'Win32'
            and value.get('postgresql_persistence_fixture') is False
            and value.get('source_commit') == receipt['source_commit'], 'Startup executable build mode differs')
    require(value.get('files') == {'DbServer.exe': native.record(directory / 'DbServer.exe')},
            'Startup DbServer executable differs from receipt')
    require(value.get('cmake_cache') == validate_cache(directory / 'CMakeCache.txt'),
            'Startup DbServer configuration differs from receipt')
    functions = native.imported_functions((directory / 'DbServer.exe').read_bytes())
    require(value.get('odbc_imports') == functions and set(wine.REQUIRED_IMPORTS) <= set(functions)
            and not set(wine.FORBIDDEN_IMPORTS).intersection(functions), 'Startup ODBC import receipt differs')
    closure = dict(value.get('retained_normal_files', {}), **value['files'])
    require(value.get('dependency_report') == native.dependency_report(closure)
            and not value['dependency_report']['unresolved'], 'Startup donor dependency closure differs')
    original = qualified_base_manifest(ROOT / ACCEPTED_BASE_MANIFEST)['variants']['normal']
    require(value.get('base_normal_executable') == original['files']['DbServer.exe']
            and value.get('base_normal_cmake_cache_sha256') == original['cmake_cache_sha256']
            and value.get('retained_normal_files') == {name: record for name, record in original['files'].items()
                                                      if name != 'DbServer.exe'},
            'Startup package relabeled the qualified donor executable or libraries')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('stage')
    prepare.add_argument('--output', type=Path, required=True)
    prepare.add_argument('--base-manifest', type=Path, required=True)
    build = commands.add_parser('package')
    for name in ('source', 'binary', 'cache', 'base-manifest', 'output'):
        build.add_argument('--' + name, type=Path, required=True)
    build.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    value = stage(args) if args.command == 'stage' else package(args)
    print(json.dumps({'output': str(args.output), 'build_role': value.get('build_role', value.get('role'))}))


if __name__ == '__main__':
    main()

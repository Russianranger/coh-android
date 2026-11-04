#!/usr/bin/env python3
"""Package the on-demand zone DbServer: external map requests above the shipped layers.

Layers below this one are unchanged and checked by their own receipts:
PostgreSQL -> Wine ODBC -> manual Atlas -> cancelled-child save -> level-up
read (the device DbServer since 0.13.12). This layer adds
database/external-maps (wine_external_maps.c/.h) and
patches/external-maps/0001 (CMakeLists.txt, launchercomm.c, mapxfer.c). It is
off unless COH_WINE_DB_EXTERNAL_MAPS=1 (with manual Atlas mode and an existing
request directory); otherwise launcherCommStartProcess and the static-map
container handling behave exactly as in the level-up DbServer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
import package_levelup_ui_repair_dbserver as levelup  # noqa: E402

bundle_layer = levelup.retained            # package_startup_bundle_dbserver
manual = bundle_layer.retained             # package_startup_dbserver (manual Atlas)
wine = manual.wine                         # prepare_wine_dbserver_source
require = levelup.require

ROLE = 'manual_atlas_dbserver_external_maps'
PATCH = 'patches/external-maps/0001-external-map-requests.patch'
OVERLAY = 'database/external-maps/overlay'
PATCHED_FILES = ('DBServer/CMakeLists.txt', 'DBServer/src/launchercomm.c', 'DBServer/src/mapxfer.c')
OVERLAY_FILES = ('DBServer/src/wine_external_maps.c', 'DBServer/src/wine_external_maps.h')
RECEIPT = 'external-maps-dbserver-build-input.json'
MANIFEST = levelup.MANIFEST
# The level-up DbServer the device runs today (0.13.36 donor, built at be955678).
BASE_LEVELUP_EXECUTABLE = {'bytes': 1664512,
    'sha256': 'ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba'}
PG_PATCH = 'patches/postgresql/0001-dbserver-postgresql.patch'


def patch_bytes(root=ROOT):
    raw = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    paths = [line[6:] for line in raw.decode().splitlines() if line.startswith('+++ b/')]
    require(tuple(paths) == PATCHED_FILES, 'External map patch changed unexpected native targets')
    return raw


def overlay_bytes(root=ROOT):
    """LF bytes whatever the checkout's line endings (as the manual Atlas overlay)."""
    directory = root / OVERLAY
    names = tuple(sorted(path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()))
    require(names == tuple(sorted(OVERLAY_FILES)), 'External map overlay inventory differs')
    return {name: (directory / name).read_bytes().replace(b'\r\n', b'\n') for name in OVERLAY_FILES}


def overlay_records(root=ROOT):
    return {name: hashlib.sha256(value).hexdigest() for name, value in overlay_bytes(root).items()}


def request_contract():
    return {'environment_variable': 'COH_WINE_DB_EXTERNAL_MAPS', 'enabled_value': '1',
        'directory_variable': 'COH_WINE_DB_EXTERNAL_MAPS_DIR', 'requires_manual_atlas': True,
        'disabled_by_default': True, 'malformed_setting': 'refuse_map_starts_no_fallback',
        'acknowledgement': 'COH_WINE_DB_EXTERNAL_MAPS=1 active: map starts are published to the supervisor; no Launcher is used',
        'request_marker': 'COH_WINE_DB_EXTERNAL_MAP_REQUEST_V1', 'request_format': 1,
        'request_file': 'map-<map_id>-<cookie>.json', 'write': 'temporary_file_then_MoveFileExA_replace',
        'fields': ['format', 'sequence', 'map_id', 'cookie', 'base_map_id', 'is_static', 'transient',
                   'dont_auto_start', 'preload_transient', 'db_process_id', 'map_name', 'mission_info', 'command'],
        'overflow': 'refuse_request_never_truncate',
        'static_map_container_on_missing_launcher': 'retained_when_enabled',
        'retained': ['launcher_selection_when_disabled', 'map_start_cookie', 'cookie_checked_registration',
                     'waiting_list', 'delink_resets_container', 'manual_atlas_wait'],
        'android_execution_validated': False}


def reconstruct(root, base):
    """The three target files as the level-up DbServer source has them, plus ours applied."""
    pg = base['base_wine_build_input']['postgresql_build_input']
    with tempfile.TemporaryDirectory(prefix='coh-external-maps-receipt-') as temporary:
        source = Path(temporary)
        for name in set(wine.WINE_FILES).union(pg['patched_sha256'], PATCHED_FILES):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / 'upstream/ouroboros' / name, target)
        wine.apply_patch(source, (root / PG_PATCH).read_bytes().replace(b'\r\n', b'\n'))
        wine.apply_patch(source, wine.patch_bytes(root))
        wine.apply_patch(source, manual.patch_bytes(root))
        inputs = {name: wine.sha256(source / name) for name in PATCHED_FILES}
        wine.apply_patch(source, patch_bytes(root))
        outputs = {name: wine.sha256(source / name) for name in PATCHED_FILES}
    return inputs, outputs


def accepted_base(root=ROOT):
    """The manual Atlas receipt over the qualified Wine DbServer package (run 36460867428)."""
    wine_input = manual.qualified_base_manifest(root / manual.ACCEPTED_BASE_MANIFEST)['wine_build_input']
    return manual.expected_receipt(root, wine_input)


def expected_receipt(root=ROOT, base=None, bundle=None, layer=None):
    base = base or accepted_base(root)
    bundle = bundle or bundle_layer.expected_receipt(root, base)
    expected_levelup = levelup.expected_receipt(root, base, bundle)
    require(layer is None or layer == expected_levelup, 'External maps must retain the exact level-up build input')
    inputs, outputs = reconstruct(root, base)
    closure = levelup.source_closure(base, bundle, expected_levelup)
    require(inputs == {name: closure.get(name, wine.sha256(root / 'upstream/ouroboros' / name))
                       for name in PATCHED_FILES}, 'External maps start from unexpected DbServer source')
    patch = patch_bytes(root)
    return {'format': 1, 'build_role': ROLE, 'source_commit': base['source_commit'],
        'base_startup_build_input_canonical_sha256': manual.canonical_hash(base),
        'base_startup_bundle_build_input_canonical_sha256': manual.canonical_hash(bundle),
        'base_levelup_ui_repair_build_input_canonical_sha256': manual.canonical_hash(expected_levelup),
        'patch': PATCH, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': inputs, 'patched_sha256': outputs, 'overlay_sha256': overlay_records(root),
        'built_target': 'DbServer', 'configuration': 'OptDebug', 'architecture': 'Win32',
        'postgresql_persistence_fixture': False, 'request_contract': request_contract(),
        'runtime_validation': 'unverified'}


def receipts(source):
    def load(name):
        return json.loads((source / name).read_text(encoding='utf-8-sig'))
    return (load(manual.RECEIPT), load(bundle_layer.RECEIPT), load(levelup.RECEIPT))


def source_closure(base, bundle, layer, external=None):
    result = levelup.source_closure(base, bundle, layer)
    if external:
        result.update(external['patched_sha256'])
        result.update(external['overlay_sha256'])
    return result


def verify_source(source, base, bundle, layer, external=None):
    """Every file of the level-up closure, with this layer's three files and overlay once applied."""
    if external is None:
        levelup.verify_source(source, base, bundle, layer)
        return
    for name, digest in source_closure(base, bundle, layer, external).items():
        require(wine.sha256(source / name) == digest, 'External map source changed: ' + name)
    require(wine.sha256(source / 'DBServer/src/container_merge.c') == bundle['unchanged_merger_sha256'],
            'External maps may not change the production merger')


def apply_overlay(source, root=ROOT):
    source = source.resolve()
    require(source != root.resolve() and (root / 'upstream').resolve() not in source.parents,
            'External maps may not modify immutable snapshots')
    require(not (source / RECEIPT).exists(), 'External map receipt already exists')
    base, bundle, layer = receipts(source)
    external = expected_receipt(root, base, bundle, layer)
    verify_source(source, base, bundle, layer)
    for name, digest in external['source_sha256'].items():
        require(wine.sha256(source / name) == digest, 'External map input differs: ' + name)
    for name, value in overlay_bytes(root).items():
        target = source / name
        require(not target.exists() and not target.is_symlink(), 'External map overlay already present: ' + name)
        target.write_bytes(value)
    wine.apply_patch(source, patch_bytes(root))
    verify_source(source, base, bundle, layer, external)
    (source / RECEIPT).write_text(json.dumps(external, indent=2) + '\n')
    return external


def stage(args):
    levelup.stage(args)
    return apply_overlay(args.output)


def package(args):
    require(re.fullmatch(r'[a-f0-9]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists(), 'External map package output must be new')
    base, bundle, layer = receipts(args.source)
    external = json.loads((args.source / RECEIPT).read_text(encoding='utf-8-sig'))
    require(external == expected_receipt(ROOT, base, bundle, layer), 'External map source receipt differs')
    verify_source(args.source, base, bundle, layer, external)
    cache = manual.validate_cache(args.cache)
    original = manual.qualified_base_manifest(args.base_manifest)
    require(original['wine_build_input'] == base['base_wine_build_input'], 'External map native donor differs')
    normal = original['variants']['normal']
    binary = manual.native.record(args.binary)
    require(binary['sha256'] not in {normal['files']['DbServer.exe']['sha256'],
            bundle_layer.BASE_STARTUP_EXECUTABLE['sha256'], levelup.BASE_STARTUP_BUNDLE_EXECUTABLE['sha256'],
            BASE_LEVELUP_EXECUTABLE['sha256']}, 'External map executable is unchanged from a retained donor')
    functions = manual.native.imported_functions(args.binary.read_bytes())
    require(set(wine.REQUIRED_IMPORTS) <= set(functions) and not set(wine.FORBIDDEN_IMPORTS).intersection(functions),
            'External map executable ODBC imports differ')
    dependencies = manual.native.dependency_report(dict(normal['files'], **{'DbServer.exe': binary}))
    require(not dependencies['unresolved'], 'External map executable needs unavailable donor libraries')
    manifest = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': base['source_commit'], 'base_package_manifest_sha256': manual.BASE_PACKAGE_SHA256,
        'base_normal_executable': normal['files']['DbServer.exe'],
        'base_startup_executable': bundle_layer.BASE_STARTUP_EXECUTABLE,
        'base_startup_bundle_executable': levelup.BASE_STARTUP_BUNDLE_EXECUTABLE,
        'base_levelup_ui_repair_executable': BASE_LEVELUP_EXECUTABLE,
        'retained_normal_files': {name: record for name, record in normal['files'].items() if name != 'DbServer.exe'},
        'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256'],
        'files': {'DbServer.exe': binary}, 'build_input': base,
        'startup_bundle_build_input': bundle, 'levelup_ui_repair_build_input': layer,
        'external_maps_build_input': external, 'cmake_cache': cache,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'postgresql_persistence_fixture': False,
        'odbc_imports': functions, 'dependency_report': dependencies,
        'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
        'base_package_archive_changed': False, 'android_execution_validated': False, 'gameplay_validated': False}
    args.output.mkdir(parents=True)
    shutil.copyfile(args.binary, args.output / 'DbServer.exe')
    shutil.copyfile(args.cache, args.output / 'CMakeCache.txt')
    (args.output / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
    validate_package(args.output, args.repository_commit)
    return manifest


def validate_package(directory, commit):
    require(directory.is_dir() and not directory.is_symlink(), 'Invalid or linked external map package directory')
    names = {'DbServer.exe', 'CMakeCache.txt', MANIFEST}
    require({path.name for path in directory.iterdir()} == names, 'Unexpected external map package inventory')
    for name in names:
        path = directory / name
        require(path.is_file() and not path.is_symlink(), 'Invalid or linked external map package leaf: ' + name)
    value = json.loads((directory / MANIFEST).read_text())
    require(value.get('format') == 1 and value.get('role') == ROLE and value.get('repository_commit') == commit
            and value.get('replacement_scope') == 'fresh_owned_manual_atlas_runtime_DbServer.exe_only'
            and value.get('base_package_manifest_sha256') == manual.BASE_PACKAGE_SHA256
            and value.get('base_package_archive_changed') is False and value.get('android_execution_validated') is False
            and value.get('gameplay_validated') is False, 'External map package provenance differs')
    base = value.get('build_input', {})
    require(base == manual.expected_receipt(ROOT, base.get('base_wine_build_input')),
            'External map package relabeled its manual Atlas ancestry')
    bundle = value.get('startup_bundle_build_input', {})
    require(bundle == bundle_layer.expected_receipt(ROOT, base), 'External map package relabeled its save ancestry')
    layer = value.get('levelup_ui_repair_build_input', {})
    require(layer == levelup.expected_receipt(ROOT, base, bundle), 'External map package relabeled its read ancestry')
    require(value.get('external_maps_build_input') == expected_receipt(ROOT, base, bundle, layer),
            'External map package source receipt differs')
    require(value.get('configuration') == 'OptDebug' and value.get('architecture') == 'Win32'
            and value.get('postgresql_persistence_fixture') is False and value.get('source_commit') == base['source_commit'],
            'External map native build mode differs')
    require(value.get('base_startup_executable') == bundle_layer.BASE_STARTUP_EXECUTABLE
            and value.get('base_startup_bundle_executable') == levelup.BASE_STARTUP_BUNDLE_EXECUTABLE
            and value.get('base_levelup_ui_repair_executable') == BASE_LEVELUP_EXECUTABLE,
            'External map package relabeled its prior executable')
    binary = manual.native.record(directory / 'DbServer.exe')
    require(value.get('files') == {'DbServer.exe': binary} and binary['sha256'] not in
            {bundle_layer.BASE_STARTUP_EXECUTABLE['sha256'], levelup.BASE_STARTUP_BUNDLE_EXECUTABLE['sha256'],
             BASE_LEVELUP_EXECUTABLE['sha256']}, 'External map executable differs or is unchanged')
    require(value.get('cmake_cache') == manual.validate_cache(directory / 'CMakeCache.txt'),
            'External map native configuration differs')
    functions = manual.native.imported_functions((directory / 'DbServer.exe').read_bytes())
    require(value.get('odbc_imports') == functions and set(wine.REQUIRED_IMPORTS) <= set(functions)
            and not set(wine.FORBIDDEN_IMPORTS).intersection(functions), 'External map ODBC imports differ')
    original = manual.qualified_base_manifest(ROOT / manual.ACCEPTED_BASE_MANIFEST)['variants']['normal']
    require(value.get('base_normal_executable') == original['files']['DbServer.exe']
            and value.get('base_normal_cmake_cache_sha256') == original['cmake_cache_sha256']
            and value.get('retained_normal_files') == {name: record for name, record in original['files'].items()
                                                       if name != 'DbServer.exe'},
            'External map package relabeled its donor executable or dependencies')
    require(binary['sha256'] != original['files']['DbServer.exe']['sha256'], 'External map executable is unchanged')
    dependencies = manual.native.dependency_report(dict(value['retained_normal_files'], **value['files']))
    require(value.get('dependency_report') == dependencies and not dependencies['unresolved'],
            'External map native dependency closure differs')
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
    receipt = commands.add_parser('receipt', help='print the expected layer receipt (no build)')
    args = parser.parse_args()
    if args.command == 'receipt':
        print(json.dumps(expected_receipt(ROOT), indent=2))
        return
    value = stage(args) if args.command == 'stage' else package(args)
    print(json.dumps({'output': str(args.output), 'build_role': value.get('build_role', value.get('role'))}))


if __name__ == '__main__':
    main()

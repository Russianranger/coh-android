#!/usr/bin/env python3
"""Add one separately receipted Game-only layer after the frozen native inputs."""
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
import prepare_client_texture_source as texture
import package_responsiveness_native as baseline
from prepare_resume_client_source import apply_patch
from package_reference_runtime import file_record

PATCH = 'patches/startup-bundle-client/0001-verified-texture-root.patch'
OVERLAY = 'database/startup-bundle-client/overlay'
OVERLAY_FILE = 'Game/src/render/coh_texture_header_root.h'
FILES = ('Game/src/render/tex.c',)
RECEIPT = 'startup-bundle-client-build-input.json'
MANIFEST = 'startup-bundle-client-manifest.json'
ROLE = 'verified_root_client_startup_supplement'
require = baseline.require


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def expected_receipt(root=ROOT):
    root = Path(root)
    patch = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    require(tuple(line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')) == FILES,
            'Startup client layer changed unexpected source files')
    base = texture.expected_texture_receipt(root)
    with tempfile.TemporaryDirectory(prefix='coh-startup-client-receipt-') as temporary:
        source = Path(temporary)
        for name in texture.FILES:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / 'upstream/ouroboros' / name).read_bytes().replace(b'\r\n', b'\n'))
        apply_patch(source, (root / texture.PATCH).read_bytes().replace(b'\r\n', b'\n'))
        inputs = {name: digest(source / name) for name in FILES}
        require(inputs == {name: base['patched_sha256'][name] for name in FILES},
                'Startup client must follow the exact frozen texture source')
        apply_patch(source, patch)
        outputs = {name: digest(source / name) for name in FILES}
    return {'format': 1, 'role': ROLE, 'source_commit': base['source_commit'],
        'base_texture_build_input': base, 'patch': PATCH, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': inputs, 'patched_sha256': outputs,
        'overlay_sha256': {OVERLAY_FILE: digest(root / OVERLAY / OVERLAY_FILE)},
        'build_targets': ['Game'], 'configuration': 'OptDebug', 'architecture': 'Win32',
        'parse6_schema_changes': False, 'full_texture_asset_changes': False,
        'graphics_profile_changes': False, 'gameplay_validation_changes': False,
        'verified_root_environment': 'COH_TEXTURE_HEADER_ROOT',
        'missing_texture_reporting': {'environment_variable': 'COH_STARTUP_DIAGNOSTIC_BOUND',
            'enabled_value': '1', 'disabled_by_default': True, 'sample_limit_per_stage': 1024,
            'retained_key_limit_per_stage': 8192, 'all_validation_retained': True},
        'runtime_execution_validated': False}


def apply_overlay(source, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source != root and not source.is_relative_to(root / 'upstream'),
            'Startup client layer may not modify immutable snapshots')
    require(not (source / RECEIPT).exists() and not (source / RECEIPT).is_symlink(),
            'Startup client receipt already exists')
    frozen = baseline.source_receipts(source)
    expected = expected_receipt(root)
    require(frozen['client_texture'] == expected['base_texture_build_input'],
            'Frozen texture source receipt differs')
    for name, pin in frozen['client_texture']['patched_sha256'].items():
        require((source / name).is_file() and not (source / name).is_symlink()
                and digest(source / name) == pin, 'Frozen texture source changed: ' + name)
    for key, field in (('client_texture', 'overlay_sha256'), ('graphics_profile', 'graphics_overlay_sha256')):
        for name, pin in frozen[key].get(field, {}).items():
            require(digest(source / name) == pin, 'Frozen native overlay changed: ' + name)
    baseline.schema_pins(source)
    target = source / OVERLAY_FILE
    require(not target.exists() and not target.is_symlink(), 'Startup client overlay would overwrite source')
    for name in FILES:
        path = source / name
        path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
    apply_patch(source, (root / PATCH).read_bytes().replace(b'\r\n', b'\n'))
    target.write_bytes((root / OVERLAY / OVERLAY_FILE).read_bytes().replace(b'\r\n', b'\n'))
    require({name: digest(source / name) for name in FILES} == expected['patched_sha256'],
            'Startup client patched source differs')
    (source / RECEIPT).write_text(json.dumps(expected, indent=2) + '\n')
    return expected


def stage(args):
    baseline.stage(args)
    return apply_overlay(args.output)


def validate_source(source):
    expected = expected_receipt()
    require(baseline.read_json(source / RECEIPT) == expected, 'Startup client source receipt differs')
    frozen = baseline.source_receipts(source)
    for key, value in frozen.items():
        pins = dict(value.get('patched_sha256', {}))
        for field in ('overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
        for name, pin in pins.items():
            if name in expected['patched_sha256']: pin = expected['patched_sha256'][name]
            require(digest(source / name) == pin, 'Startup client source changed: ' + name)
    for name, pin in expected['overlay_sha256'].items():
        require(digest(source / name) == pin, 'Startup client root decoder changed')
    baseline.schema_pins(source)
    return expected, frozen


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact startup client commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh startup client package required')
    expected, frozen = validate_source(args.source)
    require(args.cache.is_file() and not args.cache.is_symlink() and 0 < args.cache.stat().st_size <= 8*1024*1024,
            'Missing, linked or oversized startup client build cache')
    cache_text = args.cache.read_text(encoding='utf-8-sig')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', cache_text, re.M) == ['OFF']
            and re.findall(r'^CMAKE_GENERATOR_PLATFORM:INTERNAL=(.*)$', cache_text, re.M) == ['Win32'],
            'Startup client requires normal Win32 build settings')
    binary = file_record(args.directory / 'CityOfHeroes.exe')
    require(binary['pe_machine'] == 0x14c, 'Startup client must be PE32')
    document = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': baseline.contract.SOURCE, 'data_commit': baseline.contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
        'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'build_input': expected, 'retained_source_inputs': frozen,
        'schema_sources_sha256': baseline.schema_pins(args.source),
        'cmake_cache': {'bytes': args.cache.stat().st_size, 'sha256': hashlib.sha256(args.cache.read_bytes()).hexdigest()},
        'files': {'CityOfHeroes.exe': binary}, 'run_url': args.run_url,
        'replacement_scope': 'CityOfHeroes.exe_only', 'retained_native_dependencies_changed': False}
    args.output.mkdir(parents=True)
    shutil.copyfile(args.directory / 'CityOfHeroes.exe', args.output / 'CityOfHeroes.exe')
    shutil.copyfile(args.cache, args.output / 'CMakeCache.txt')
    (args.output / MANIFEST).write_text(json.dumps(document, indent=2) + '\n')
    validate_package(args.output, args.repository_commit)
    return document


def validate_package(directory, commit):
    require(set(path.name for path in directory.iterdir()) == {'CityOfHeroes.exe', 'CMakeCache.txt', MANIFEST},
            'Unexpected startup client package member')
    require(all(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 64*1024*1024
                for path in directory.iterdir()), 'Linked, empty or nonregular startup client package member')
    document = baseline.read_json(directory / MANIFEST)
    require(document.get('format') == 1 and document.get('role') == ROLE
            and document.get('repository_commit') == commit
            and document.get('source_commit') == baseline.contract.SOURCE
            and document.get('data_commit') == baseline.contract.DATA
            and document.get('configuration') == 'OptDebug' and document.get('architecture') == 'Win32'
            and document.get('build_targets') == ['Game']
            and document.get('postgresql_persistence_fixture') is False
            and document.get('runtime_execution_validated') is False
            and document.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and document.get('retained_native_dependencies_changed') is False
            and document.get('build_input') == expected_receipt()
            and document.get('schema_sources_sha256') == baseline.schema_pins()
            and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+',
                             str(document.get('run_url', ''))), 'Startup client package identity differs')
    frozen = document.get('retained_source_inputs', {})
    require(set(frozen) == set(baseline.INPUTS), 'Startup client frozen source inventory differs')
    for key, value in frozen.items():
        require(value == baseline.expected_source_receipt(key, value), 'Startup client frozen source receipt differs')
    require(document.get('files') == {'CityOfHeroes.exe': file_record(directory / 'CityOfHeroes.exe')},
            'Startup client executable bytes differ')
    cache = directory / 'CMakeCache.txt'
    require(document.get('cmake_cache') == {'bytes': cache.stat().st_size,
        'sha256': hashlib.sha256(cache.read_bytes()).hexdigest()}, 'Startup client build cache differs')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('stage')
    prepare.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('package')
    for name in ('directory', 'source', 'cache', 'output'):
        create.add_argument('--' + name, type=Path, required=True)
    create.add_argument('--repository-commit', required=True)
    create.add_argument('--run-url', required=True)
    args = parser.parse_args()
    {'stage': stage, 'package': package}[args.command](args)


if __name__ == '__main__': main()

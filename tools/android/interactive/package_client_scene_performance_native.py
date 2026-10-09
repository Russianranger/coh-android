#!/usr/bin/env python3
"""Append bounded scene/frame observations to the exact accepted Game source chain."""
from __future__ import annotations
import argparse
import functools
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_startup_followup_native as base
from prepare_resume_client_source import apply_patch
from package_reference_runtime import file_record

ROLE = 'bounded_client_scene_and_frame_performance'
RECEIPT = 'client-scene-performance-build-input.json'
MANIFEST = 'client-scene-performance-native-manifest.json'
CHECKS = 'client-scene-performance-native-checks.json'
PATCHES = (
    'patches/client-scene-performance/0001-scene-loading-phase-and-preload.patch',
    'patches/client-scene-performance/0002-native-frame-timing.patch')
OVERLAYS = {
    'Game/src/cohClientSceneTiming.h': 'android/native/client-scene-performance/cohClientSceneTiming.h',
    'Game/src/cohClientFrameTiming.h': 'database/client-scene-performance/overlay/Game/src/cohClientFrameTiming.h'}
FILES = ('Game/src/game.c', 'Game/src/graphics/gfx.c', 'Game/src/clientcomm/clientcomm.c',
    'Game/src/group/groupnetrecv.c', 'Common/seq/gfxtree.c', 'Common/seq/gfxtree.h',
    'Game/src/render/thread/rt_win_init.c')
BASE_GAME = dict(base.BASE_GAME, sha256='cad33afc212113a5d116bf8fe63078034fa63c494c1a91ddadaf42cadf55fe9a', size=9449984)
COMPILER_OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
TEST_MODULES = ('test_client_scene_performance_native', 'test_client_frame_timing_native')
CONTROLS = {
    'scene_profile': {'environment_variable': 'COH_CLIENT_SCENE_PROFILE', 'enabled_value': '1',
        'disabled_by_default': True, 'record_prefix': 'COH_CLIENT_SCENE_PHASE_V1', 'bounded': True},
    'discarded_fx_preload': {'environment_variable': 'COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD',
        'enabled_value': '1', 'disabled_by_default': True, 'stock_fallback_preserved': True,
        'surviving_post_invalidation_preload_preserved': True},
    'frame_profile': {'environment_variable': 'COH_CLIENT_FRAME_TIMING', 'enabled_value': '1',
        'disabled_by_default': True, 'record_prefix': 'COH_CLIENT_FRAME_TIMING_V1',
        'aggregate_only': True, 'bounded': True}}
SOURCE_FILES = (*PATCHES, *OVERLAYS.values(),
    'tools/android/interactive/package_client_scene_performance_native.py',
    'tools/android/interactive/test_client_scene_performance_native.py',
    'tools/android/interactive/test_client_frame_timing_native.py',
    'tools/android/interactive/test_client_frame_timing_source.py',
    *('upstream/ouroboros/'+name for name in FILES))
require, digest = base.require, base.digest


@functools.lru_cache(maxsize=2)
def expected_receipt(root=ROOT):
    root = Path(root)
    require(root.resolve() == ROOT.resolve(), 'Native recipe must use the current immutable checkout')
    with tempfile.TemporaryDirectory(prefix='coh-scene-recipe-') as temporary:
        source = Path(temporary)/'accepted'
        base.stage(SimpleNamespace(output=source))
        accepted, frozen = base.validate_source(source)
        before = {name: digest(source/name) for name in FILES}
        touched = set()
        for name in PATCHES:
            patch = (root/name).read_bytes().replace(b'\r\n', b'\n')
            paths = [line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')]
            require(paths and len(paths) == len(set(paths)) and set(paths) <= set(FILES),
                'Scene/frame patch edits an unexpected native source')
            touched.update(paths)
            for path in paths:
                target = source/path; target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n'))
            apply_patch(source, patch)
        require(touched == set(FILES), 'Scene/frame patch source inventory differs')
        after = {name: digest(source/name) for name in FILES}
        require(all(before[name] != after[name] for name in FILES), 'Every declared native source must change')
        for name in reversed(PATCHES):
            base.base.reverse_patch(source, (root/name).read_bytes().replace(b'\r\n', b'\n'))
        require({name: digest(source/name) for name in FILES} == before,
            'Scene/frame reverse patches did not reproduce the complete accepted input')
    return {'format': 1, 'role': ROLE, 'source_commit': base.base.base.baseline.contract.SOURCE,
        'base_client_startup_followup_build_input': accepted,
        'patches_sha256': {name: digest(root/name) for name in PATCHES},
        'source_sha256': before, 'patched_sha256': after,
        'overlay_sha256': {name: digest(root/template) for name, template in OVERLAYS.items()},
        'reverse_patch_exact_base_verified': True, 'controls': CONTROLS,
        'build_targets': ['Game'], 'configuration': 'OptDebug', 'architecture': 'Win32',
        'cache_encoding_changed': False, 'parse6_schema_changes': False, 'source_freshness_changed': False,
        'graphics_profile_changes': False, 'renderer_changed': False, 'gameplay_validation_changes': False,
        'runtime_execution_validated': False}


def apply_overlay(source):
    source = Path(source).resolve()
    require(source != ROOT and not source.is_relative_to(ROOT/'upstream'), 'Immutable native source may not be patched')
    require(not (source/RECEIPT).exists() and not (source/RECEIPT).is_symlink(), 'Scene/frame receipt exists')
    base.validate_source(source); expected = expected_receipt()
    require({name: digest(source/name) for name in FILES} == expected['source_sha256'], 'Scene/frame accepted source differs')
    for name in FILES:
        target = source/name; target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n'))
    for name in PATCHES: apply_patch(source, (ROOT/name).read_bytes().replace(b'\r\n', b'\n'))
    for name, template in OVERLAYS.items():
        target = source/name
        require(not target.exists() and not target.is_symlink(), 'Scene/frame header would overwrite accepted source')
        target.write_bytes((ROOT/template).read_bytes().replace(b'\r\n', b'\n'))
    require({name: digest(source/name) for name in FILES} == expected['patched_sha256'], 'Scene/frame patched source differs')
    (source/RECEIPT).write_text(json.dumps(expected, indent=2)+'\n')
    return expected


def stage(args):
    base.stage(args)
    return apply_overlay(args.output)


def validate_source(source):
    source = Path(source); expected = expected_receipt(); baseline = base.base.base.baseline
    require(baseline.read_json(source/RECEIPT) == expected, 'Scene/frame source receipt differs')
    for producer in (base, base.base, base.base.base):
        require(baseline.read_json(source/producer.RECEIPT) == producer.expected_receipt(),
            'Accepted native source receipt changed: '+producer.RECEIPT)
    frozen = baseline.source_receipts(source)
    overrides = dict(base.base.base.expected_receipt()['patched_sha256'])
    overrides.update(base.base.expected_receipt()['patched_sha256'])
    overrides.update(base.expected_receipt()['patched_sha256'])
    overrides.update(expected['patched_sha256'])
    for value in frozen.values():
        pins = dict(value.get('patched_sha256', {}))
        for field in ('overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'): pins.update(value.get(field, {}))
        for name, pin in pins.items():
            require(digest(source/name) == overrides.get(name, pin), 'Retained native source changed: '+name)
    for producer in (base.base.base,):
        for name, pin in producer.expected_receipt()['overlay_sha256'].items():
            require(digest(source/name) == pin, 'Accepted native header changed: '+name)
    for name, pin in base.expected_receipt()['native_callsite_sources_sha256'].items():
        require(digest(source/name) == pin, 'Accepted cache/freshness callsite changed: '+name)
    for name, pin in baseline.schema_pins().items():
        require(digest(source/name) == overrides.get(name, pin), 'Prepared cache schema changed: '+name)
    for name, pin in expected['patched_sha256'].items(): require(digest(source/name) == pin, 'Scene/frame source changed: '+name)
    for name, pin in expected['overlay_sha256'].items(): require(digest(source/name) == pin, 'Scene/frame header changed: '+name)
    return expected, frozen


def validate_checks(checks):
    require(isinstance(checks, dict) and set(checks) == {'format', 'status', 'platform', 'architecture',
        'configuration', 'build_input', 'scene', 'frame'} and checks.get('format') == 1
        and checks.get('status') == 'passed' and checks.get('platform') == 'windows'
        and checks.get('architecture') == 'Win32' and checks.get('configuration') == 'OptDebug'
        and checks.get('build_input') == expected_receipt(), 'Current real Win32 scene/frame qualification required')
    for role, name in zip(('scene', 'frame'), TEST_MODULES):
        test = importlib.import_module(name)
        validator = getattr(test, 'validate_windows_checks', None) or test.validate_checks
        validator(checks[role])
    return checks


def combine_checks(args):
    baseline = base.base.base.baseline
    result = {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'build_input': expected_receipt(),
        'scene': baseline.read_json(args.scene_checks), 'frame': baseline.read_json(args.frame_checks)}
    validate_checks(result); require(not args.output.exists(), 'Fresh combined checks required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2)+'\n')
    return result


def validate_cmake_cache(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 8*1024**2,
        'Bounded regular native CMake cache required')
    text = path.read_text(encoding='utf-8-sig')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', text, re.M) == ['OFF']
        and re.findall(r'^CMAKE_GENERATOR_PLATFORM:INTERNAL=(.*)$', text, re.M) == ['Win32'],
        'Actual CMake cache must preserve the normal Win32 Game build')
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact native scene/frame commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh native scene/frame output required')
    expected, frozen = validate_source(args.source)
    checks = base.base.base.baseline.read_json(args.checks); validate_checks(checks)
    cache_pin = validate_cmake_cache(args.cache)
    binary = file_record(args.directory/'CityOfHeroes.exe')
    require(binary['pe_machine'] == 332 and binary != BASE_GAME and binary['imports'] == BASE_GAME['imports']
        and binary['delay_imports'] == BASE_GAME['delay_imports'], 'Native Game PE or retained imports differ')
    d = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': base.base.base.baseline.contract.SOURCE, 'data_commit': base.base.base.baseline.contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
        'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'build_input': expected, 'retained_source_inputs': frozen,
        'schema_sources_sha256': base.base.base.baseline.schema_pins(), 'base_client_executable': BASE_GAME,
        'files': {'CityOfHeroes.exe': binary}, 'replacement_scope': 'CityOfHeroes.exe_only',
        'cache_encoding_changed': False, 'retained_native_dependencies_changed': False,
        'windows_qualification': checks, 'cmake_cache': cache_pin, 'run_url': args.run_url}
    args.output.mkdir(parents=True)
    for source, name in ((args.directory/'CityOfHeroes.exe', 'CityOfHeroes.exe'), (args.cache, 'CMakeCache.txt'), (args.checks, CHECKS)):
        shutil.copyfile(source, args.output/name)
    (args.output/MANIFEST).write_text(json.dumps(d, indent=2)+'\n')
    validate_package(args.output, args.repository_commit)
    return d


def validate_package(directory, commit):
    directory = Path(directory); baseline = base.base.base.baseline
    require(set(p.name for p in directory.iterdir()) == {'CityOfHeroes.exe', 'CMakeCache.txt', MANIFEST, CHECKS}
        and all(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size <= 64*1024**2 for p in directory.iterdir()), 'Native Game-only inventory differs')
    d = baseline.read_json(directory/MANIFEST); expected = expected_receipt()
    require(d.get('format') == 1 and d.get('role') == ROLE and d.get('repository_commit') == commit
        and d.get('source_commit') == baseline.contract.SOURCE and d.get('data_commit') == baseline.contract.DATA
        and d.get('configuration') == 'OptDebug' and d.get('architecture') == 'Win32' and d.get('build_targets') == ['Game']
        and d.get('postgresql_persistence_fixture') is False and d.get('runtime_execution_validated') is False
        and d.get('cache_encoding_changed') is False and d.get('retained_native_dependencies_changed') is False
        and d.get('replacement_scope') == 'CityOfHeroes.exe_only' and d.get('build_input') == expected
        and d.get('base_client_executable') == BASE_GAME and d.get('schema_sources_sha256') == baseline.schema_pins()
        and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+', str(d.get('run_url', ''))), 'Native scene/frame producer differs')
    require(set(d.get('retained_source_inputs', {})) == set(baseline.INPUTS), 'Native inherited receipt inventory differs')
    for key, received in d['retained_source_inputs'].items():
        require(received == baseline.expected_source_receipt(key, received), 'Native inherited source receipt differs')
    record = file_record(directory/'CityOfHeroes.exe')
    require(record != BASE_GAME and record['pe_machine'] == 332 and record['imports'] == BASE_GAME['imports']
        and record['delay_imports'] == BASE_GAME['delay_imports'] and d.get('files') == {'CityOfHeroes.exe': record}, 'Native Game bytes/imports differ')
    validate_checks(d.get('windows_qualification'))
    require(d['windows_qualification'] == baseline.read_json(directory/CHECKS), 'Native actual Win32 proof differs')
    cache = directory/'CMakeCache.txt'
    require(d.get('cmake_cache') == validate_cmake_cache(cache), 'Native CMake evidence differs')
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__); commands = p.add_subparsers(dest='command', required=True)
    s = commands.add_parser('stage'); s.add_argument('--output', type=Path, required=True)
    c = commands.add_parser('combine-checks')
    for name in ('scene-checks', 'frame-checks', 'output'): c.add_argument('--'+name, type=Path, required=True)
    b = commands.add_parser('package')
    for name in ('directory', 'source', 'cache', 'output', 'checks'): b.add_argument('--'+name, type=Path, required=True)
    b.add_argument('--repository-commit', required=True); b.add_argument('--run-url', required=True)
    v = commands.add_parser('verify'); v.add_argument('--directory', type=Path, required=True); v.add_argument('--repository-commit', required=True)
    a = p.parse_args()
    result = stage(a) if a.command == 'stage' else combine_checks(a) if a.command == 'combine-checks' else package(a) if a.command == 'package' else validate_package(a.directory, a.repository_commit)
    print('Qualified native Game layer:', result.get('role', result.get('status')))


if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Append focused render-pipeline timing and repair the worker wake handshake.

Every preceding native recipe and executable history remains immutable. This
layer replaces Game only; the launcher, renderer, server and cache schema stay
bound to their independently identified accepted producers.
"""
from __future__ import annotations
import argparse
import functools
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
import package_client_renderer_attribution_native as base
from prepare_resume_client_source import apply_patch
from package_client_loading_native import reverse_patch
from package_reference_runtime import file_record

ROLE = 'bounded_client_render_pipeline'
RECEIPT = 'client-render-pipeline-build-input.json'
MANIFEST = 'client-render-pipeline-native-manifest.json'
CHECKS = 'client-render-pipeline-native-checks.json'
PATCHES = ('patches/client-render-pipeline/0001-render-worker-wake-and-focused-timing.patch',)
OVERLAYS = {'Game/src/cohClientRenderPipeline.h':
    'database/client-render-pipeline/overlay/Game/src/cohClientRenderPipeline.h'}
FILES = ('Game/src/graphics/gfx.c', 'Game/src/render/thread/rt_queue.c',
    'Game/src/render/thread/rt_queue.h', 'libs/UtilitiesLib/src/components/WorkerThread.c')
BASE_GAME = dict(base.BASE_GAME,
    sha256='adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44', size=9487872)
COMPILER_OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
CONTROLS = {
    'render_pipeline': {'environment_variable': 'COH_CLIENT_RENDER_PIPELINE',
        'enabled_value': '1', 'disabled_by_default': True,
        'record_prefix': 'COH_CLIENT_RENDER_PIPELINE_V1',
        'window_report_limit_per_thread': 120, 'command_sample_interval': 16,
        'aggregate_only': True, 'thread_cpu_window_boundaries_only': True,
        'blocking_gpu_measurement': False, 'main_scope': 'gameplay',
        'renderer_scope': 'all_states_independent'},
    'worker_wake_repair': {'asleep_published_before_event_reset': True,
        'empty_queue_recheck_preserved': True, 'producer_signals_unchanged': True,
        'unthreaded_queue_unchanged': True, 'full_queue_flush_unchanged': True}}


SOURCE_FILES = (*PATCHES, *OVERLAYS.values(),
    'tools/android/interactive/package_client_render_pipeline_native.py',
    'tools/android/interactive/test_client_render_pipeline_native.py',
    'tools/android/interactive/test_client_render_pipeline_source.py',
    *('upstream/ouroboros/'+name for name in FILES))
require, digest = base.require, base.digest
baseline = base.baseline


def typed_equal(received, expected):
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return encode(received) == encode(expected)


def normalized_patch(name):
    patch = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')]
    require(names and len(names) == len(set(names)) and set(names) <= set(FILES),
        'Render pipeline performance patch edits an unexpected native source')
    return patch, names


@functools.lru_cache(maxsize=2)
def expected_receipt(root=ROOT):
    require(Path(root).resolve() == ROOT.resolve(), 'Native recipe requires this immutable checkout')
    with tempfile.TemporaryDirectory(prefix='coh-gameplay-recipe-') as temporary:
        source = Path(temporary)/'accepted'
        base.stage(SimpleNamespace(output=source))
        accepted, frozen = base.validate_source(source)
        before = {name: digest(source/name) for name in FILES}
        touched = set()
        for name in PATCHES:
            patch, paths = normalized_patch(name)
            touched.update(paths)
            for path in paths:
                target = source/path
                target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n'))
            apply_patch(source, patch)
        require(touched == set(FILES), 'Render pipeline performance patch inventory differs')
        after = {name: digest(source/name) for name in FILES}
        require(all(before[name] != after[name] for name in FILES), 'Declared source did not change')
        for name in reversed(PATCHES):
            reverse_patch(source, normalized_patch(name)[0])
        require({name: digest(source/name) for name in FILES} == before,
            'Render pipeline reverse patches did not reproduce the complete accepted input')
    return {'format': 1, 'role': ROLE, 'source_commit': baseline.contract.SOURCE,
        'base_client_renderer_attribution_build_input': accepted,
        'patches_sha256': {name: digest(ROOT/name) for name in PATCHES},
        'source_sha256': before, 'patched_sha256': after,
        'overlay_sha256': {name: digest(ROOT/template) for name, template in OVERLAYS.items()},
        'reverse_patch_exact_base_verified': True, 'controls': CONTROLS,
        'build_targets': ['Game'], 'configuration': 'OptDebug', 'architecture': 'Win32',
        'cache_encoding_changed': False, 'parse6_schema_changes': False,
        'source_freshness_changed': False, 'graphics_profile_changes': False,
        'renderer_changed': False, 'gameplay_validation_changes': False,
        'gameplay_frame_cap_changed': False, 'native_fps_display_changed': False, 'worker_wakeup_changed': True, 'runtime_execution_validated': False}


def apply_overlay(source):
    source = Path(source).resolve()
    require(source != ROOT and not source.is_relative_to(ROOT/'upstream'),
        'Immutable native source may not be patched')
    require(not (source/RECEIPT).exists() and not (source/RECEIPT).is_symlink(),
        'Render pipeline performance receipt already exists')
    base.validate_source(source)
    expected = expected_receipt()
    require({name: digest(source/name) for name in FILES} == expected['source_sha256'],
        'Render pipeline performance accepted source differs')
    for name in OVERLAYS:
        target = source/name
        require(not target.exists() and not target.is_symlink(),
            'Render pipeline performance header would overwrite accepted source')
    for name in FILES:
        target = source/name
        target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n'))
    for name in PATCHES:
        apply_patch(source, normalized_patch(name)[0])
    for name, template in OVERLAYS.items():
        (source/name).write_bytes((ROOT/template).read_bytes().replace(b'\r\n', b'\n'))
    require({name: digest(source/name) for name in FILES} == expected['patched_sha256'],
        'Render pipeline performance applied source differs')
    (source/RECEIPT).write_text(json.dumps(expected, indent=2)+'\n')
    return expected


def stage(args):
    base.stage(args)
    return apply_overlay(args.output)


def validate_source(source):
    source = Path(source)
    expected = expected_receipt()
    require(typed_equal(baseline.read_json(source/RECEIPT), expected), 'Render pipeline source receipt differs')
    producers = (base, base.base, base.base.base, base.base.base.base, base.base.base.base.base, base.base.base.base.base.base)
    overrides = {}
    for producer in reversed(producers):
        previous = producer.expected_receipt()
        require(baseline.read_json(source/producer.RECEIPT) == previous,
            'Accepted native source receipt changed: '+producer.RECEIPT)
        overrides.update(previous['patched_sha256'])
    overrides.update(expected['patched_sha256'])
    frozen = baseline.source_receipts(source)
    for value in frozen.values():
        pins = dict(value.get('patched_sha256', {}))
        for field in ('overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
        for name, pin in pins.items():
            require(digest(source/name) == overrides.get(name, pin),
                'Retained native source changed: '+name)
    for producer in producers:
        previous = producer.expected_receipt()
        for name, pin in previous.get('overlay_sha256', {}).items():
            require(digest(source/name) == pin, 'Accepted native header changed: '+name)
        for name, pin in previous.get('native_callsite_sources_sha256', {}).items():
            require(digest(source/name) == overrides.get(name, pin),
                'Accepted cache/freshness callsite changed: '+name)
        for name, pin in previous.get('patched_sha256', {}).items():
            require(digest(source/name) == overrides.get(name, pin),
                'Accepted native source changed: '+name)
    for name, pin in baseline.schema_pins().items():
        require(digest(source/name) == overrides.get(name, pin),
            'Prepared cache schema changed: '+name)
    for field in ('patched_sha256', 'overlay_sha256'):
        for name, pin in expected[field].items():
            require(digest(source/name) == pin, 'Render pipeline performance source changed: '+name)
    return expected, frozen


def validate_checks(checks):
    require(isinstance(checks, dict) and set(checks) == {'format', 'status', 'platform',
        'architecture', 'configuration', 'build_input', 'scene', 'frame', 'gameplay', 'renderer', 'pipeline'}
        and type(checks.get('format')) is int and checks.get('format') == 1 and checks.get('status') == 'passed'
        and checks.get('platform') == 'windows' and checks.get('architecture') == 'Win32'
        and checks.get('configuration') == 'OptDebug'
        and typed_equal(checks.get('build_input'), expected_receipt()),
        'Current genuine Win32 render pipeline qualification required')
    previous = {name: value for name, value in checks.items() if name != 'pipeline'}
    previous['build_input'] = base.expected_receipt()
    base.validate_checks(previous)
    importlib.import_module('test_client_render_pipeline_native').validate_windows_checks(checks['pipeline'])
    return checks


def combine_checks(args):
    result = {'format': 1, 'status': 'passed', 'platform': 'windows',
        'architecture': 'Win32', 'configuration': 'OptDebug', 'build_input': expected_receipt(),
        'scene': baseline.read_json(args.scene_checks),
        'frame': baseline.read_json(args.frame_checks),
        'gameplay': baseline.read_json(args.gameplay_checks),
        'renderer': baseline.read_json(args.renderer_checks),
        'pipeline': baseline.read_json(args.pipeline_checks)}
    validate_checks(result)
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh combined checks required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    return result


def validate_cmake_cache(path):
    return base.validate_cmake_cache(path)


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact current native commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh native output required')
    expected, frozen = validate_source(args.source)
    checks = baseline.read_json(args.checks)
    validate_checks(checks)
    cache_pin = validate_cmake_cache(args.cache)
    binary = file_record(args.directory/'CityOfHeroes.exe')
    require(binary['pe_machine'] == 332 and binary != BASE_GAME
        and binary['imports'] == BASE_GAME['imports']
        and binary['delay_imports'] == BASE_GAME['delay_imports'],
        'Native Game PE or retained imports differ')
    manifest = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': baseline.contract.SOURCE, 'data_commit': baseline.contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
        'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'build_input': expected, 'retained_source_inputs': frozen,
        'schema_sources_sha256': baseline.schema_pins(), 'base_client_executable': BASE_GAME,
        'files': {'CityOfHeroes.exe': binary}, 'replacement_scope': 'CityOfHeroes.exe_only',
        'cache_encoding_changed': False, 'retained_native_dependencies_changed': False,
        'windows_qualification': checks, 'cmake_cache': cache_pin, 'run_url': args.run_url}
    args.output.mkdir(parents=True)
    for source, name in ((args.directory/'CityOfHeroes.exe', 'CityOfHeroes.exe'),
            (args.cache, 'CMakeCache.txt'), (args.checks, CHECKS)):
        shutil.copyfile(source, args.output/name)
    (args.output/MANIFEST).write_text(json.dumps(manifest, indent=2)+'\n')
    validate_package(args.output, args.repository_commit)
    return manifest


def validate_package(directory, commit):
    directory = Path(directory)
    require(set(path.name for path in directory.iterdir()) ==
        {'CityOfHeroes.exe', 'CMakeCache.txt', MANIFEST, CHECKS}
        and all(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 64*1024**2
            for path in directory.iterdir()), 'Native Game-only inventory differs')
    manifest = baseline.read_json(directory/MANIFEST)
    require(manifest.get('format') == 1 and manifest.get('role') == ROLE
        and manifest.get('repository_commit') == commit
        and manifest.get('source_commit') == baseline.contract.SOURCE
        and manifest.get('data_commit') == baseline.contract.DATA
        and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
        and manifest.get('build_targets') == ['Game']
        and manifest.get('postgresql_persistence_fixture') is False
        and manifest.get('runtime_execution_validated') is False
        and manifest.get('cache_encoding_changed') is False
        and manifest.get('retained_native_dependencies_changed') is False
        and manifest.get('replacement_scope') == 'CityOfHeroes.exe_only'
        and typed_equal(manifest.get('build_input'), expected_receipt())
        and manifest.get('base_client_executable') == BASE_GAME
        and manifest.get('schema_sources_sha256') == baseline.schema_pins()
        and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+',
            str(manifest.get('run_url', ''))), 'Native render pipeline producer differs')
    require(set(manifest.get('retained_source_inputs', {})) == set(baseline.INPUTS),
        'Native inherited receipt inventory differs')
    for key, received in manifest['retained_source_inputs'].items():
        require(received == baseline.expected_source_receipt(key, received),
            'Native independently recomputed inherited source receipt differs')
    record = file_record(directory/'CityOfHeroes.exe')
    require(record != BASE_GAME and record['pe_machine'] == 332
        and record['imports'] == BASE_GAME['imports']
        and record['delay_imports'] == BASE_GAME['delay_imports']
        and manifest.get('files') == {'CityOfHeroes.exe': record}, 'Native Game bytes/imports differ')
    validate_checks(manifest.get('windows_qualification'))
    require(manifest['windows_qualification'] == baseline.read_json(directory/CHECKS),
        'Native actual Win32 proof differs')
    require(manifest.get('cmake_cache') == validate_cmake_cache(directory/'CMakeCache.txt'),
        'Native actual CMake evidence differs')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('stage')
    command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('combine-checks')
    for name in ('scene-checks', 'frame-checks', 'gameplay-checks', 'renderer-checks', 'pipeline-checks', 'output'):
        command.add_argument('--'+name, type=Path, required=True)
    command = commands.add_parser('package')
    for name in ('directory', 'source', 'cache', 'output', 'checks'):
        command.add_argument('--'+name, type=Path, required=True)
    command.add_argument('--repository-commit', required=True)
    command.add_argument('--run-url', required=True)
    command = commands.add_parser('verify')
    command.add_argument('--directory', type=Path, required=True)
    command.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    result = stage(args) if args.command == 'stage' else combine_checks(args) if args.command == 'combine-checks' else package(args) if args.command == 'package' else validate_package(args.directory, args.repository_commit)
    print('Qualified native Game layer:', result.get('role', result.get('status')))


if __name__ == '__main__':
    main()

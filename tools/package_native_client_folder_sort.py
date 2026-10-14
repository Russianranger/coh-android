#!/usr/bin/env python3
"""Package one fresh Game constructor candidate without replacing native donors.

The output is a qualification-only native artifact. An actual Game runtime,
Atlas/Kings behavior and AYN Thor performance remain separate acceptance gates.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

import prepare_native_client_folder_sort_source as source
from map_startup_namespace_certificate import require
from package_reference_runtime import file_record, dependency_report

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
import package_client_render_queue_native as retained

ROLE = 'bounded_client_folder_metadata_sort'
MANIFEST = 'native-client-folder-sort-package.json'
CHECKS = 'native-client-folder-sort-windows-checks.json'
FIXTURE = 'constructor-fixture.exe'
MEMBERS = frozenset(('CityOfHeroes.exe', CHECKS, FIXTURE, source.RECEIPT, 'CMakeCache.txt'))
APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
DONOR_SOURCE = '3570430cefdb15d9b239563e85cccf4d8fe6f32e'
GAME_SHA = '5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b'
GAME_BYTES = 9499648
SCOPE = {
    'replacement_scope': 'CityOfHeroes.exe_only', 'native_game_compiled_in_current_run': True,
    'native_donor_recompiled': False, 'retained_native_dependencies_changed': False,
    'cache_schema_changed': False, 'source_freshness_changed': False, 'renderer_changed': False,
    'native_game_runtime_qualified': False, 'native_wine_executed': False,
    'physical_device_executed': False, 'publication_allowed': False,
}
MANIFEST_KEYS = frozenset(('format', 'role', 'repository_commit', 'source_commit', 'data_commit', 'run_url',
    'architecture', 'configuration', 'build_targets', 'build_input', 'retained_game_build_input',
    'historical_source_receipts', 'validated_sources_sha256', 'schema_sources_sha256', 'cmake_cache',
    'retained_public_client', 'windows_constructor_fixture', 'files', 'artifact_members', 'scope', 'qualification_scope'))


def regular(path, maximum=64 * 1024**2):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file()
            and 0 < path.stat().st_size <= maximum, 'Bounded regular native input required: ' + str(path))
    return path


def pin(path):
    path = regular(path)
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read(path):
    return json.loads(regular(path, 8 * 1024**2).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def exact(actual, expected, message):
    require(retained.typed_equal(actual, expected), message)


def identity(commit, run_url=None):
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'Exact native source commit required')
    if run_url is not None:
        require(isinstance(run_url, str) and re.fullmatch(
            r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]*', run_url),
            'Exact current Actions producer required')


def validate_fixture(value, fixture=None):
    import test_native_client_folder_sort_source as native
    require(type(value) is dict and type(value.get('format')) is int and value['format'] == 1
            and value.get('status') == 'passed'
            and value.get('role') == 'actual_extracted_folder_constructor_and_node_insert_parity'
            and type(value.get('cases')) is int and value['cases'] == 398, 'Exact current constructor C fixture required')
    exact(value.get('source'), source.expected_receipt(), 'Exact constructor fixture source differs')
    flags = {'native_windows_executed': True, 'controlled_enumeration': True,
        'portable_windows_types_are_adapters': False, 'native_game_executed': False,
        'native_wine_executed': False, 'physical_device_executed': False, 'publication_allowed': False,
        'callback_trace_exact_in_fallback': True, 'provider_metadata_and_all_links_equal': True,
        'root_per_entry_constructor_order_exact_in_every_fallback': True,
        'same_FindFirst_FindNext_FindClose_counts': True, 'enumerations_restarted': False,
        'one_temporary_batch_maximum': True, 'temporary_buffers_released_before_recursion': True}
    for name, expected in flags.items():
        require(value.get(name) is expected, 'Genuine Win32 constructor proof/scope differs: ' + name)
    for name, expected in {'observed_native_WFD_bytes': 320, 'observed_row_bytes': 324,
        'maximum_retained_batch_payload_bytes': 5308416,
        'possible_realloc_payload_overlap_bytes_before_allocator_overhead': 7962624,
        'tested_entry_limit': 16384}.items():
        require(type(value.get(name)) is int and value[name] == expected, 'Native metadata ABI/limit differs: ' + name)
    exact(value.get('tested_allocation_failures'), [1, 2], 'Native allocation failure scenarios differ')
    require(value.get('harness_sha256') == hashlib.sha256(native.harness().encode()).hexdigest(),
            'Actual extracted constructor fixture program differs')
    require(isinstance(value.get('fixture_binary_sha256'), str) and
            re.fullmatch(r'[0-9a-f]{64}', value['fixture_binary_sha256']), 'Executed fixture byte identity required')
    cases = value.get('controlled_insertion_comparison_cases')
    require(type(cases) is list and len(cases) == 3 and
            [r.get('mode') for r in cases] == ['empty', 'mixed_pig', 'previous_gdd'] and
            all(type(r) is dict and set(r) == {'mode', 'first_stock', 'first_candidate', 'last_stock', 'last_candidate'} and
                all(isinstance(r[k], str) and re.fullmatch(r'[0-9]+', r[k]) for k in r if k != 'mode') for r in cases),
            'Separate empty/PIG/previous-provider observations required')
    require(cases[2]['last_stock'] == cases[2]['last_candidate'], 'Populated-provider constructor work changed')
    if fixture is not None:
        require(pin(fixture)['sha256'] == value['fixture_binary_sha256'] and file_record(regular(fixture))['pe_machine'] == 332,
                'Executed Win32 constructor fixture bytes differ')
    return value


def donor(apk):
    exact(pin(apk), APK, 'Exact independently audited public .36 APK required')
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor APK member')
        raw = archive.read('assets/runtime/client-runtime.zip')
        outer = archive.read('assets/runtime/client-manifest.json')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) and
                all(re.fullmatch(r'[A-Za-z0-9_.-]+', n) for n in names), 'Duplicate/aliased retained native member')
        require('client-package.json' in names, 'Retained native package receipt missing')
        raw_manifest = archive.read('client-package.json')
        manifest = json.loads(raw_manifest)
        records = manifest.get('files', {})
        require(type(records) is dict and set(names) == set(records) | {'client-package.json'}
                and manifest.get('server_executables_included') is False, 'Retained native member closure differs')
        require(records['CityOfHeroes.exe']['sha256'] == GAME_SHA and records['CityOfHeroes.exe']['size'] == GAME_BYTES,
                'Retained public Game identity differs')
        actual = {}
        with tempfile.TemporaryDirectory(prefix='coh-folder-sort-donor-') as temporary:
            for name in sorted(records):
                data = archive.read(name)
                require(0 < len(data) <= 64 * 1024**2, 'Unbounded retained donor payload')
                path = Path(temporary) / name
                path.write_bytes(data)
                actual[name] = file_record(path)
        exact(actual, records, 'Retained native DLL/Game bytes or imports differ from original receipt')
        exact(dependency_report(actual), manifest['dependency_report'], 'Retained native dependency authority differs')
        return {'donor_apk': dict(APK), 'donor_source': DONOR_SOURCE, 'native_game': actual['CityOfHeroes.exe'],
            'client_runtime_zip': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
            'client_manifest': {'bytes': len(outer), 'sha256': hashlib.sha256(outer).hexdigest()},
            'client_package': {'bytes': len(raw_manifest), 'sha256': hashlib.sha256(raw_manifest).hexdigest()},
            'native_member_closure': actual, 'client_runtime_manifest': manifest,
            'native_donor_rebuilt': False, 'original_archive_or_receipts_rewritten': False}


def expected_closure(historical):
    require(type(historical) is dict and set(historical) == set(retained.baseline.INPUTS),
            'Historical source receipt inventory differs')
    pins = {}
    for key, value in historical.items():
        exact(value, retained.baseline.expected_source_receipt(key, value), 'Historical source producer differs: ' + key)
        for field in ('patched_sha256', 'overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
    producers, current = [], retained
    while hasattr(current, 'expected_receipt'):
        producers.append(current)
        if not hasattr(current, 'base'):
            break
        current = current.base
    for producer in reversed(producers):
        previous = producer.expected_receipt()
        for field in ('native_callsite_sources_sha256', 'patched_sha256', 'overlay_sha256'):
            pins.update(previous.get(field, {}))
    for name, value in retained.baseline.schema_pins().items():
        pins.setdefault(name, value)
    new = source.expected_receipt()
    require(pins.get(source.SOURCE) == new['source_sha256'][source.SOURCE], 'Retained constructor predecessor differs')
    pins.update(new['patched_sha256']); pins.update(new['overlay_sha256'])
    pins[source.NODE_SOURCE] = new['source_sha256'][source.NODE_SOURCE]
    return pins


def validate_game(path, inherited):
    path = regular(path)
    actual = file_record(path)
    previous = inherited['native_game']
    require(actual['pe_machine'] == previous['pe_machine'] == 332 and actual['sha256'] != previous['sha256'],
            'Fresh changed Win32 Game required')
    exact(actual['imports'], previous['imports'], 'Retained Game native DLL/ABI closure differs')
    exact(actual['delay_imports'], previous['delay_imports'], 'Retained Game delay imports differ')
    require(b'COH_CLIENT_FOLDER_METADATA_SORT_V1' in path.read_bytes(), 'Compiled Game lacks constructor marker')
    return actual


def validate_cache(path):
    regular(path, 8 * 1024**2)
    return retained.validate_cmake_cache(path)


def stage(args):
    retained.stage(args)
    source.stage(args.output)
    return source.validate_staged_source(args.output)


def package(args):
    identity(args.repository_commit, args.run_url)
    output = Path(args.output)
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'Fresh regular native package required')
    inputs = source.validate_staged_source(args.source)
    cmake = validate_cache(args.cache)
    inherited = donor(args.donor_apk)
    fixture = Path(args.checks).with_suffix('.exe')
    checks = validate_fixture(read(args.checks), fixture)
    binary = Path(args.directory) / 'CityOfHeroes.exe'
    require(Path(args.directory).name == 'OptDebug', 'Explicit OptDebug Game output directory required')
    actual = validate_game(binary, inherited)
    exact(inputs['validated_sources_sha256'], expected_closure(inputs['historical_source_receipts']), 'Staged source closure differs')
    output.mkdir(parents=True)
    for original, name in ((binary, 'CityOfHeroes.exe'), (args.checks, CHECKS), (fixture, FIXTURE),
                           (Path(args.source) / source.RECEIPT, source.RECEIPT), (args.cache, 'CMakeCache.txt')):
        shutil.copyfile(regular(original), output / name)
    value = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': retained.baseline.contract.SOURCE, 'data_commit': retained.baseline.contract.DATA,
        'run_url': args.run_url, 'architecture': 'Win32', 'configuration': 'OptDebug', 'build_targets': ['Game'],
        'build_input': inputs['source'], 'retained_game_build_input': inputs['retained_game_build_input'],
        'historical_source_receipts': inputs['historical_source_receipts'],
        'validated_sources_sha256': inputs['validated_sources_sha256'],
        'schema_sources_sha256': {n: inputs['validated_sources_sha256'][n] for n in retained.baseline.schema_pins()},
        'cmake_cache': cmake, 'retained_public_client': inherited, 'windows_constructor_fixture': checks,
        'files': {'CityOfHeroes.exe': actual}, 'artifact_members': {p.name: pin(p) for p in sorted(output.iterdir())},
        'scope': dict(SCOPE),
        'qualification_scope': 'Win32 constructor fixture and full Game compilation; Game runtime, both worlds and Thor remain separate gates'}
    write(output / MANIFEST, value)
    return validate_package(output, args.repository_commit, args.donor_apk)


def validate_package(directory, commit, donor_apk):
    directory = Path(directory)
    identity(commit)
    require(directory.is_dir() and not any(p.is_symlink() for p in (directory, *directory.parents)), 'Regular native artifact root required')
    require({p.name for p in directory.iterdir()} == MEMBERS | {MANIFEST}, 'Exact Game-only artifact member closure differs')
    for name in MEMBERS | {MANIFEST}:
        regular(directory / name)
    value = read(directory / MANIFEST)
    require(type(value) is dict and set(value) == MANIFEST_KEYS and type(value.get('format')) is int and value['format'] == 1
            and value.get('role') == ROLE and value.get('repository_commit') == commit,
            'Typed native artifact producer differs')
    identity(commit, value.get('run_url'))
    for name, expected in {'source_commit': retained.baseline.contract.SOURCE, 'data_commit': retained.baseline.contract.DATA,
        'architecture': 'Win32', 'configuration': 'OptDebug', 'build_targets': ['Game'], 'scope': SCOPE}.items():
        exact(value.get(name), expected, 'Native source/build/scope differs: ' + name)
    exact(value.get('build_input'), source.expected_receipt(), 'Candidate source recipe changed')
    exact(read(directory / source.RECEIPT), value['build_input'], 'Archived constructor source receipt differs')
    exact(value.get('retained_game_build_input'), retained.expected_receipt(), 'Retained Game source recipe changed')
    pins = expected_closure(value['historical_source_receipts'])
    exact(value.get('validated_sources_sha256'), pins, 'Native source closure changed')
    exact(value.get('schema_sources_sha256'), {n: pins[n] for n in retained.baseline.schema_pins()}, 'Read-only serializer schema pins changed')
    exact(value.get('artifact_members'), {n: pin(directory / n) for n in MEMBERS}, 'Native artifact bytes changed')
    checks = validate_fixture(read(directory / CHECKS), directory / FIXTURE)
    exact(value.get('windows_constructor_fixture'), checks, 'Executed native constructor fixture changed')
    inherited = donor(donor_apk)
    exact(value.get('retained_public_client'), inherited, 'Original public Game/DLL donor changed')
    actual = validate_game(directory / 'CityOfHeroes.exe', inherited)
    exact(value.get('files'), {'CityOfHeroes.exe': actual}, 'Game-only executable identity differs')
    exact(value.get('cmake_cache'), validate_cache(directory / 'CMakeCache.txt'), 'Actual CMake provenance changed')
    require(value.get('qualification_scope') == 'Win32 constructor fixture and full Game compilation; Game runtime, both worlds and Thor remain separate gates',
            'Native runtime qualification scope changed')
    return value


# Preserve the short draft API name for existing external callers.
validate = validate_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('stage'); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('package')
    for name in ('source', 'directory', 'cache', 'checks', 'donor-apk', 'output'):
        command.add_argument('--' + name, type=Path, required=True)
    command.add_argument('--repository-commit', required=True); command.add_argument('--run-url', required=True)
    command = commands.add_parser('validate')
    for name in ('directory', 'donor-apk'):
        command.add_argument('--' + name, type=Path, required=True)
    command.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    result = stage(args) if args.command == 'stage' else package(args) if args.command == 'package' else validate_package(
        args.directory, args.repository_commit, args.donor_apk)
    print(json.dumps({'status': 'nonshipping_native_stage_or_package_validated', 'role': ROLE, 'publication_allowed': False}))


if __name__ == '__main__': main()

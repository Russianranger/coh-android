#!/usr/bin/env python3
"""Build a Game-only decoder layer after the exact published startup source."""
import argparse
import hashlib
import json
import math
import importlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_startup_bundle_client as base
from prepare_resume_client_source import apply_patch
from package_reference_runtime import file_record

PATCH = 'patches/client-loading/0001-known-length-string-copy-and-profile.patch'
FILE = 'libs/UtilitiesLib/src/utils/textparser.c'
FILES = (FILE,)
ROLE = 'bounded_client_binary_loading'
RECEIPT = 'client-loading-native-build-input.json'
MANIFEST = 'client-loading-native-manifest.json'
CHECKS = 'client-loading-native-checks.json'
COMPILER_OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
SOURCE_FILES = (PATCH, 'tools/android/interactive/package_client_loading_native.py',
    'tools/android/interactive/test_client_loading_native.py')
BASE_GAME = {'sha256': 'e9f8522e07305a51f9464004ffce3f1b85fa065af04ab6892beaf47d1d095cd2',
    'size': 9446912, 'pe_machine': 332, 'imports': ['ADVAPI32.dll', 'cg.dll', 'cgGL.dll',
    'COMDLG32.dll', 'DDRAW.dll', 'DINPUT8.dll', 'DSOUND.dll', 'GDI32.dll', 'GLU32.dll',
    'IMM32.dll', 'IPHLPAPI.DLL', 'KERNEL32.dll', 'ole32.dll', 'OPENGL32.dll', 'PhysXCooking.dll',
    'PhysXLoader.dll', 'SHELL32.dll', 'USER32.dll', 'VERSION.dll', 'WINMM.dll', 'WS2_32.dll'],
    'delay_imports': []}
COPY = {'environment_variable': 'COH_CLIENT_KNOWN_STRING_COPY', 'enabled_value': '1',
    'disabled_by_default': True, 'negative_length_only': True,
    'explicit_length_secure_crt_preserved': True, 'allocation_and_free_behavior_preserved': True}
PROFILE = {'environment_variable': 'COH_CLIENT_BIN_PROFILE', 'enabled_value': '1',
    'disabled_by_default': True, 'record_prefix': 'COH_CLIENT_BIN_PROFILE_V1',
    'phases': ['open', 'freshness', 'decode'], 'thread_local_flags_and_counters': True,
    'stock_freshness_and_crc_preserved': True, 'clock': 'GetTickCount_unsigned_wrap'}
require = base.require


def digest(path): return base.digest(path)


def function(text, signature):
    begin = text.index(signature); brace = text.index('{', begin); depth = 1; end = brace+1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[begin:end]


def reverse_patch(source, patch):
    # Use the same Git implementation/configuration as the forward application.
    # GNU patch can rewrite otherwise identical LF source as CRLF on Windows.
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(name, None)
    env['GIT_CEILING_DIRECTORIES'] = str(source.parent)
    command = ['git', '-c', 'core.autocrlf=false', 'apply', '--reverse']
    subprocess.run(command + ['--check', '-'], input=patch, cwd=source, env=env,
                   check=True, capture_output=True)
    subprocess.run(command + ['-'], input=patch, cwd=source, env=env,
                   check=True, capture_output=True)


def patched_text(root=ROOT):
    root = Path(root)
    original = (root/'upstream/ouroboros'/FILE).read_bytes().replace(b'\r\n', b'\n')
    with tempfile.TemporaryDirectory(prefix='coh-client-loading-receipt-') as temporary:
        source = Path(temporary); path = source/FILE; path.parent.mkdir(parents=True); path.write_bytes(original)
        patch = (root/PATCH).read_bytes().replace(b'\r\n', b'\n')
        require(tuple(line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')) == FILES,
            'Client loading patch changed unexpected source')
        apply_patch(source, patch)
        result = path.read_bytes().decode()
        # Reverse the precise patch and compare the complete immutable input.
        reverse_patch(source, patch)
        require(path.read_bytes() == original, 'Decoder reverse patch did not reproduce exact base')
        return original.decode(), result


def expected_receipt(root=ROOT):
    root = Path(root); original, current = patched_text(root)
    # No tables, CRC computation, serialization envelope, source date comparison,
    # explicit-length handling or memory ownership policy may change.
    preserved = ('int ParseTableCRC(', 'int ParserReadBinaryTable(', 'void*    StructAllocRawDbg(',
        'void    StructFree(', 'void StructFreeString(', 'static FileScanAction DateCheckCallback(')
    function_pins = {}
    for signature in preserved:
        left, right = function(original, signature), function(current, signature)
        require(left == right, 'Client decoder changed retained native semantics: '+signature)
        function_pins[signature] = hashlib.sha256(left.encode()).hexdigest()
    return {'format': 1, 'role': ROLE, 'source_commit': base.baseline.contract.SOURCE,
        'base_startup_client_build_input': base.expected_receipt(root), 'patch': PATCH,
        'patch_sha256': digest(root/PATCH), 'source_sha256': {FILE: hashlib.sha256(original.encode()).hexdigest()},
        'patched_sha256': {FILE: hashlib.sha256(current.encode()).hexdigest()},
        'preserved_functions_sha256': function_pins, 'reverse_patch_exact_base_verified': True,
        'known_length_copy': COPY, 'bin_profile': PROFILE, 'build_targets': ['Game'],
        'configuration': 'OptDebug', 'architecture': 'Win32', 'cache_encoding_changed': False,
        'parse6_schema_changes': False, 'source_freshness_changed': False, 'graphics_profile_changes': False,
        'runtime_execution_validated': False}


def apply_overlay(source):
    source = Path(source).resolve()
    require(source != ROOT and not source.is_relative_to(ROOT/'upstream'), 'Immutable source may not be patched')
    require(not (source/RECEIPT).exists() and not (source/RECEIPT).is_symlink(), 'Loading layer receipt exists')
    base.validate_source(source)
    expected = expected_receipt()
    require(digest(source/FILE) == expected['source_sha256'][FILE], 'Loading layer base source differs')
    path = source/FILE; path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
    apply_patch(source, (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n'))
    require(digest(path) == expected['patched_sha256'][FILE], 'Loading layer output differs')
    (source/RECEIPT).write_text(json.dumps(expected, indent=2)+'\n')
    return expected


def stage(args): base.stage(args); return apply_overlay(args.output)


def validate_source(source):
    source = Path(source); expected = expected_receipt()
    require(base.baseline.read_json(source/RECEIPT) == expected, 'Loading decoder source receipt differs')
    old = base.expected_receipt()
    require(base.baseline.read_json(source/base.RECEIPT) == old, 'Frozen startup client input differs')
    frozen = base.baseline.source_receipts(source)
    for value in frozen.values():
        pins = dict(value.get('patched_sha256', {}))
        for field in ('overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
        for name, pin in pins.items():
            require(digest(source/name) == old['patched_sha256'].get(name, pin), 'Frozen client layer changed: '+name)
    for name, pin in old['overlay_sha256'].items(): require(digest(source/name) == pin, 'Frozen decoder overlay changed')
    for name, pin in base.baseline.schema_pins().items():
        require(digest(source/name) == expected['patched_sha256'].get(name, pin), 'Client parser source changed: '+name)
    return expected, frozen


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact client loading commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh client loading artifact required')
    expected, frozen = validate_source(args.source)
    checks = base.baseline.read_json(args.checks)
    validate_checks(checks)
    require(args.cache.is_file() and not args.cache.is_symlink() and 0 < args.cache.stat().st_size <= 8*1024*1024,
        'Missing client loading build cache')
    cache = args.cache.read_text(encoding='utf-8-sig')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', cache, re.M) == ['OFF']
        and re.findall(r'^CMAKE_GENERATOR_PLATFORM:INTERNAL=(.*)$', cache, re.M) == ['Win32'],
        'Client loading requires retained Win32 normal build')
    binary = file_record(args.directory/'CityOfHeroes.exe')
    require(binary['pe_machine'] == 332 and binary != BASE_GAME, 'Client loading Game derivative invalid')
    document = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': base.baseline.contract.SOURCE, 'data_commit': base.baseline.contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
        'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'build_input': expected, 'retained_source_inputs': frozen,
        'schema_sources_sha256': base.baseline.schema_pins(), 'decoder_source_sha256': expected['patched_sha256'],
        'base_client_executable': BASE_GAME, 'files': {'CityOfHeroes.exe': binary},
        'cache_encoding_changed': False, 'replacement_scope': 'CityOfHeroes.exe_only',
        'retained_native_dependencies_changed': False, 'windows_qualification': checks,
        'cmake_cache': {'bytes': args.cache.stat().st_size, 'sha256': hashlib.sha256(args.cache.read_bytes()).hexdigest()},
        'run_url': args.run_url}
    args.output.mkdir(parents=True)
    for src, name in ((args.directory/'CityOfHeroes.exe', 'CityOfHeroes.exe'),
            (args.cache, 'CMakeCache.txt'), (args.checks, CHECKS)):
        shutil.copyfile(src, args.output/name)
    (args.output/MANIFEST).write_text(json.dumps(document, indent=2)+'\n')
    validate_package(args.output, args.repository_commit)
    return document


def validate_checks(checks):
    require(isinstance(checks, dict) and checks.get('format') == 1 and checks.get('status') == 'passed'
        and checks.get('platform') == 'windows' and checks.get('architecture') == 'Win32'
        and checks.get('configuration') == 'OptDebug' and checks.get('build_input') == expected_receipt()
        and checks.get('compiler_options') == COMPILER_OPTIONS
        and checks.get('equivalence_verified') is True and checks.get('explicit_length_behavior_verified') is True
        and checks.get('thread_local_flags_verified') is True and checks.get('opt_in_and_fallback_verified') is True
        and checks.get('known_length_path_secure_crt_call_eliminated') is True
        and isinstance(checks.get('benchmarks'), list) and len(checks['benchmarks']) == 5
        and all(isinstance(x, dict) and x.get('length') in (8,48,128,512,11999)
            and type(x.get('stock_seconds')) in (int,float) and math.isfinite(x['stock_seconds']) and x['stock_seconds'] > 0
            and type(x.get('candidate_seconds')) in (int,float) and math.isfinite(x['candidate_seconds']) and x['candidate_seconds'] > 0
            for x in checks['benchmarks'])
        and re.fullmatch(r'[0-9a-f]{64}', str(checks.get('assembly_sha256','')))
        and re.fullmatch(r'[0-9a-f]{64}', str(checks.get('harness_sha256','')))
        and all(x.get('rounds') == 5 for x in checks['benchmarks'])
        and checks.get('physical_startup_savings_validated') is False,
        'Client loading requires real Win32 copy qualification')
    actual_harness = importlib.import_module('test_client_loading_native').harness()
    require(checks['harness_sha256'] == hashlib.sha256(actual_harness.encode()).hexdigest(),
        'Client loading proof did not execute the current actual native harness')
    require(sorted(x['length'] for x in checks['benchmarks']) == [8,48,128,512,11999], 'Missing copy benchmark length')
    short = [x for x in checks['benchmarks'] if x['length'] <= 512]
    require(sum(x['candidate_seconds'] for x in short) < sum(x['stock_seconds'] for x in short),
        'Known length copy did not improve the representative Win32 benchmark')
    return checks


def validate_package(directory, commit):
    directory = Path(directory)
    require(set(p.name for p in directory.iterdir()) == {'CityOfHeroes.exe', 'CMakeCache.txt', MANIFEST, CHECKS},
        'Unexpected client loading artifact member')
    require(all(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size <= 64*1024*1024
        for p in directory.iterdir()), 'Linked, empty or oversized loading artifact member')
    d = base.baseline.read_json(directory/MANIFEST)
    expected = expected_receipt()
    require(d.get('format') == 1 and d.get('role') == ROLE and d.get('repository_commit') == commit
        and d.get('source_commit') == base.baseline.contract.SOURCE and d.get('data_commit') == base.baseline.contract.DATA
        and d.get('configuration') == 'OptDebug' and d.get('architecture') == 'Win32'
        and d.get('build_targets') == ['Game'] and d.get('postgresql_persistence_fixture') is False
        and d.get('runtime_execution_validated') is False and d.get('cache_encoding_changed') is False
        and d.get('replacement_scope') == 'CityOfHeroes.exe_only' and d.get('retained_native_dependencies_changed') is False
        and d.get('build_input') == expected and d.get('decoder_source_sha256') == expected['patched_sha256']
        and d.get('schema_sources_sha256') == base.baseline.schema_pins() and d.get('base_client_executable') == BASE_GAME
        and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+', str(d.get('run_url',''))),
        'Client loading native producer contract differs')
    frozen = d.get('retained_source_inputs', {})
    require(set(frozen) == set(base.baseline.INPUTS), 'Frozen native input inventory differs')
    for key, value in frozen.items():
        require(value == base.baseline.expected_source_receipt(key, value), 'Frozen native source receipt differs')
    actual = file_record(directory/'CityOfHeroes.exe')
    require(actual['pe_machine'] == 332 and actual != BASE_GAME
        and d.get('files') == {'CityOfHeroes.exe': actual}, 'Loading Game bytes differ')
    validate_checks(d.get('windows_qualification'))
    require(d['windows_qualification'] == base.baseline.read_json(directory/CHECKS), 'Loading copy checks differ')
    cache = directory/'CMakeCache.txt'
    require(d.get('cmake_cache') == {'bytes': cache.stat().st_size,
        'sha256': hashlib.sha256(cache.read_bytes()).hexdigest()}, 'Loading native build cache differs')
    return d


def main():
    parser = argparse.ArgumentParser(description=__doc__); cmds = parser.add_subparsers(dest='command', required=True)
    s = cmds.add_parser('stage'); s.add_argument('--output', type=Path, required=True)
    p = cmds.add_parser('package')
    for name in ('directory', 'source', 'cache', 'output', 'checks'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--repository-commit', required=True); p.add_argument('--run-url', required=True)
    v = cmds.add_parser('verify'); v.add_argument('--directory', type=Path, required=True); v.add_argument('--repository-commit', required=True)
    a = parser.parse_args()
    result = {'stage': stage, 'package': package, 'verify': lambda x: validate_package(x.directory,x.repository_commit)}[a.command](a)
    print(json.dumps({'role': result['role'], 'status': 'passed'}))

if __name__ == '__main__': main()

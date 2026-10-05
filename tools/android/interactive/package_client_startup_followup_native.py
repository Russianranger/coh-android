#!/usr/bin/env python3
"""Game-only dependency lookup scheduling after the exact accepted loading layer."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_loading_native as base
from prepare_resume_client_source import apply_patch
from package_reference_runtime import file_record

PATCH = 'patches/client-startup-followup/0001-preload-power-dependency-tree.patch'
FILE = base.FILE
FILES = (FILE,)
ROLE = 'bounded_client_dependency_preload'
RECEIPT = 'client-startup-followup-build-input.json'
MANIFEST = 'client-startup-followup-native-manifest.json'
CHECKS = 'client-startup-followup-native-checks.json'
COMPILER_OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
SOURCE_FILES = (PATCH, 'tools/android/interactive/package_client_startup_followup_native.py',
    'tools/android/interactive/test_client_startup_followup_native.py',
    'upstream/ouroboros/Common/entity/load_def.c', 'upstream/ouroboros/Common/entity/powers_load.c',
    'upstream/ouroboros/Common/seq/seqload.c', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c')
BASE_GAME = dict(base.BASE_GAME, sha256='ec1a6c01b07d7c189bde743a7255c860b8dd96879225b4ffa50fd42eabbb721b', size=9443840)
PRELOAD = {'environment_variable': 'COH_CLIENT_DEPENDENCY_PRELOAD', 'enabled_value': '1',
    'disabled_by_default': True, 'requests': [{'persistfile': 'bin/powers.bin', 'directory': 'defs/powers/', 'filemask': '.powers', 'requested_tree': 'Menu'},
        {'persistfile': 'bin/sequencers.bin', 'directory': 'sequencers', 'filemask': '.txt', 'requested_tree': 'player_library/animations'}], 'scope': 'ordinary_FolderCache_metadata_only',
    'source_freshness_preserved': True, 'crc_validation_preserved': True,
    'cache_encoding_changed': False, 'full_asset_bytes_preloaded': False,
    'native_fallback_preserved': True, 'record_prefix': 'COH_CLIENT_DEPENDENCY_PRELOAD_V1'}
require = base.require
function = base.function
digest = base.digest


def patched_text(root=ROOT):
    root = Path(root)
    _, original = base.patched_text(root)
    with tempfile.TemporaryDirectory(prefix='coh-client-followup-source-') as temporary:
        source = Path(temporary); path = source/FILE; path.parent.mkdir(parents=True); path.write_bytes(original.encode())
        patch = (root/PATCH).read_bytes().replace(b'\r\n', b'\n')
        require(tuple(line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')) == FILES,
                'Dependency preload changed unexpected source')
        apply_patch(source, patch)
        current = path.read_bytes().decode()
        base.reverse_patch(source, patch)
        require(path.read_bytes() == original.encode(), 'Dependency preload reverse patch differs')
        return original, current


def expected_receipt(root=ROOT):
    root = Path(root); original, current = patched_text(root)
    preserved = ('int ParseTableCRC(', 'int ParserReadBinaryTable(', 'int ParserReadBinaryFile(',
        'char* StructAllocStringLenDbg(', 'static FileScanAction DateCheckCallback(',
        'void*    StructAllocRawDbg(', 'void    StructFree(', 'void StructFreeString(')
    pins = {}
    for signature in preserved:
        left, right = function(original, signature), function(current, signature)
        require(left == right, 'Preload changed retained native semantics: '+signature)
        pins[signature] = hashlib.sha256(left.encode()).hexdigest()
    old = function(original, 'SimpleBufHandle ParserIsPersistNewer(')
    new = function(current, 'SimpleBufHandle ParserIsPersistNewer(')
    require(new.replace('    cohClientPreloadDependencies(dir, filemask, persistfile);\n\n', '', 1) == old,
            'Preload changed an existing CRC, date, comparison or failure branch')
    callsites = {name: digest(root/'upstream/ouroboros'/name) for name in (
        'Common/entity/load_def.c', 'Common/entity/powers_load.c', 'Common/seq/seqload.c',
        'libs/UtilitiesLib/src/utils/FolderCache.c',
        'libs/UtilitiesLib/src/utils/FolderCacheNode.c', 'libs/UtilitiesLib/src/utils/file.c')}
    # Game follows the accepted PostgreSQL/events/texture/graphics chain, not
    # the separately built Wine DbServer. Its FolderCache remains stock.
    require('load_PowerDictionary(&g_PowerDictionary, "defs/powers/",' in
            (root/'upstream/ouroboros/Common/entity/load_def.c').read_text(), 'Real powers caller path changed')
    require('ParserLoadFiles(pchFilename,".powers","powers.bin",' in
            (root/'upstream/ouroboros/Common/entity/powers_load.c').read_text(), 'Real powers parser call changed')
    require('ParserLoadFiles("sequencers", ".txt", "sequencers.bin",' in
            (root/'upstream/ouroboros/Common/seq/seqload.c').read_text(), 'Real sequencer parser call changed')
    return {'format': 1, 'role': ROLE, 'source_commit': base.base.baseline.contract.SOURCE,
        'base_client_loading_build_input': base.expected_receipt(root), 'patch': PATCH,
        'patch_sha256': digest(root/PATCH), 'source_sha256': {FILE: hashlib.sha256(original.encode()).hexdigest()},
        'patched_sha256': {FILE: hashlib.sha256(current.encode()).hexdigest()},
        'preserved_functions_sha256': pins, 'reverse_patch_exact_base_verified': True,
        'freshness_body_exact_except_preload_call': True, 'native_callsite_sources_sha256': callsites,
        'dependency_preload': PRELOAD,
        'build_targets': ['Game'], 'configuration': 'OptDebug', 'architecture': 'Win32',
        'cache_encoding_changed': False, 'parse6_schema_changes': False,
        'source_freshness_changed': False, 'graphics_profile_changes': False,
        'runtime_execution_validated': False}


def apply_overlay(source):
    source = Path(source).resolve()
    require(source != ROOT and not source.is_relative_to(ROOT/'upstream'), 'Immutable source may not be patched')
    require(not (source/RECEIPT).exists() and not (source/RECEIPT).is_symlink(), 'Preload source receipt exists')
    base.validate_source(source)
    expected = expected_receipt()
    require(digest(source/FILE) == expected['source_sha256'][FILE], 'Preload base source differs')
    for name, pin in expected['native_callsite_sources_sha256'].items():
        require((source/name).is_file() and not (source/name).is_symlink() and digest(source/name) == pin,
                'Preload native dependency callsite differs: '+name)
    apply_patch(source, (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n'))
    require(digest(source/FILE) == expected['patched_sha256'][FILE], 'Preload patched source differs')
    (source/RECEIPT).write_text(json.dumps(expected, indent=2)+'\n')
    return expected


def stage(args):
    base.stage(args)
    return apply_overlay(args.output)


def validate_source(source):
    source = Path(source); expected = expected_receipt()
    require(base.base.baseline.read_json(source/RECEIPT) == expected, 'Preload source receipt differs')
    for name, pin in expected['native_callsite_sources_sha256'].items():
        require((source/name).is_file() and not (source/name).is_symlink() and digest(source/name) == pin,
                'Preload native dependency callsite differs: '+name)
    loading = base.expected_receipt()
    require(base.base.baseline.read_json(source/base.RECEIPT) == loading, 'Accepted loading source receipt differs')
    startup = base.base.expected_receipt()
    require(base.base.baseline.read_json(source/base.base.RECEIPT) == startup, 'Accepted startup source receipt differs')
    frozen = base.base.baseline.source_receipts(source)
    for value in frozen.values():
        pins = dict(value.get('patched_sha256', {}))
        for field in ('overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
        for name, pin in pins.items():
            require(digest(source/name) == expected['patched_sha256'].get(name, startup['patched_sha256'].get(name, pin)),
                    'Accepted source changed: '+name)
    for name, pin in startup['overlay_sha256'].items():
        require(digest(source/name) == pin, 'Accepted startup overlay changed')
    for name, pin in base.base.baseline.schema_pins().items():
        require(digest(source/name) == expected['patched_sha256'].get(name, pin), 'Preload parser source changed')
    return expected, frozen


def validate_checks(checks):
    expected = expected_receipt()
    require(isinstance(checks, dict) and set(checks) == {'format', 'status', 'platform', 'architecture',
        'configuration', 'compiler_options', 'build_input', 'harness_sha256', 'equivalence_verified',
        'opt_in_and_fallback_verified', 'exact_scope_verified', 'freshness_failure_branches_verified',
        'metadata_lookup_reduction_verified', 'ordinary_source_mutation_detection_verified',
        'physical_startup_savings_validated', 'individual_fallback_queries', 'candidate_tree_requests'}
        and checks.get('format') == 1 and checks.get('status') == 'passed'
        and checks.get('platform') == 'windows' and checks.get('architecture') == 'Win32'
        and checks.get('configuration') == 'OptDebug' and checks.get('compiler_options') == COMPILER_OPTIONS
        and checks.get('build_input') == expected
        and all(checks.get(k) is True for k in ('equivalence_verified', 'opt_in_and_fallback_verified',
            'exact_scope_verified', 'freshness_failure_branches_verified', 'metadata_lookup_reduction_verified',
            'ordinary_source_mutation_detection_verified'))
        and checks.get('individual_fallback_queries') == 4539 and checks.get('candidate_tree_requests') == 1
        and checks.get('physical_startup_savings_validated') is False,
        'Preload requires exact source-bound real Win32 equivalence proof')
    harness = importlib.import_module('test_client_startup_followup_native').harness()
    require(checks.get('harness_sha256') == hashlib.sha256(harness.encode()).hexdigest(), 'Preload harness identity differs')
    return checks


def package(args):
    require(re.fullmatch('[0-9a-f]{40}', args.repository_commit), 'Exact preload commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh preload package required')
    expected, frozen = validate_source(args.source)
    checks = validate_checks(base.base.baseline.read_json(args.checks))
    require(args.cache.is_file() and not args.cache.is_symlink() and 0 < args.cache.stat().st_size <= 8*1024*1024,
            'Missing preload native build cache')
    cache = args.cache.read_text(encoding='utf-8-sig')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', cache, re.M) == ['OFF']
        and re.findall(r'^CMAKE_GENERATOR_PLATFORM:INTERNAL=(.*)$', cache, re.M) == ['Win32'], 'Preload normal Win32 build required')
    binary = file_record(args.directory/'CityOfHeroes.exe')
    require(binary['pe_machine'] == 332 and binary != BASE_GAME
        and binary['imports'] == BASE_GAME['imports'] and binary['delay_imports'] == BASE_GAME['delay_imports'],
        'Preload Game derivative or native import closure invalid')
    document = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': base.base.baseline.contract.SOURCE, 'data_commit': base.base.baseline.contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
        'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'build_input': expected, 'retained_source_inputs': frozen,
        'schema_sources_sha256': base.base.baseline.schema_pins(), 'preload_source_sha256': expected['patched_sha256'],
        'base_client_executable': BASE_GAME, 'files': {'CityOfHeroes.exe': binary},
        'cache_encoding_changed': False, 'replacement_scope': 'CityOfHeroes.exe_only',
        'retained_native_dependencies_changed': False, 'windows_qualification': checks,
        'cmake_cache': {'bytes': args.cache.stat().st_size, 'sha256': hashlib.sha256(args.cache.read_bytes()).hexdigest()},
        'run_url': args.run_url}
    args.output.mkdir(parents=True)
    for src, name in ((args.directory/'CityOfHeroes.exe', 'CityOfHeroes.exe'), (args.cache, 'CMakeCache.txt'), (args.checks, CHECKS)):
        shutil.copyfile(src, args.output/name)
    (args.output/MANIFEST).write_text(json.dumps(document, indent=2)+'\n')
    validate_package(args.output, args.repository_commit)
    return document


def validate_package(directory, commit):
    directory = Path(directory)
    require(set(p.name for p in directory.iterdir()) == {'CityOfHeroes.exe', 'CMakeCache.txt', MANIFEST, CHECKS},
            'Unexpected preload native package member')
    require(all(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size <= 64*1024*1024 for p in directory.iterdir()),
            'Linked or oversized preload native package member')
    d = base.base.baseline.read_json(directory/MANIFEST); expected = expected_receipt()
    require(d.get('format') == 1 and d.get('role') == ROLE and d.get('repository_commit') == commit
        and d.get('source_commit') == base.base.baseline.contract.SOURCE and d.get('data_commit') == base.base.baseline.contract.DATA
        and d.get('configuration') == 'OptDebug' and d.get('architecture') == 'Win32'
        and d.get('build_targets') == ['Game'] and d.get('postgresql_persistence_fixture') is False
        and d.get('runtime_execution_validated') is False and d.get('cache_encoding_changed') is False
        and d.get('replacement_scope') == 'CityOfHeroes.exe_only' and d.get('retained_native_dependencies_changed') is False
        and d.get('build_input') == expected and d.get('preload_source_sha256') == expected['patched_sha256']
        and d.get('schema_sources_sha256') == base.base.baseline.schema_pins() and d.get('base_client_executable') == BASE_GAME
        and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+', str(d.get('run_url',''))),
        'Preload native producer contract differs')
    frozen = d.get('retained_source_inputs', {})
    require(set(frozen) == set(base.base.baseline.INPUTS), 'Preload frozen source inventory differs')
    for key, value in frozen.items():
        require(value == base.base.baseline.expected_source_receipt(key, value), 'Preload frozen source receipt differs')
    actual = file_record(directory/'CityOfHeroes.exe')
    require(actual['pe_machine'] == 332 and actual != BASE_GAME
        and actual['imports'] == BASE_GAME['imports'] and actual['delay_imports'] == BASE_GAME['delay_imports']
        and d.get('files') == {'CityOfHeroes.exe': actual},
            'Preload Game bytes differ')
    validate_checks(d.get('windows_qualification'))
    require(d['windows_qualification'] == base.base.baseline.read_json(directory/CHECKS), 'Preload checks differ')
    cache = directory/'CMakeCache.txt'
    require(d.get('cmake_cache') == {'bytes': cache.stat().st_size, 'sha256': hashlib.sha256(cache.read_bytes()).hexdigest()},
            'Preload build cache differs')
    return d


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    s = commands.add_parser('stage'); s.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('package')
    for name in ('directory','source','cache','output','checks'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--repository-commit', required=True); p.add_argument('--run-url', required=True)
    v = commands.add_parser('verify'); v.add_argument('--directory', type=Path, required=True); v.add_argument('--repository-commit', required=True)
    a = parser.parse_args(); result = {'stage':stage,'package':package,'verify':lambda x:validate_package(x.directory,x.repository_commit)}[a.command](a)
    print(json.dumps({'role':result['role'],'status':'passed'}))

if __name__ == '__main__': main()

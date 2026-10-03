#!/usr/bin/env python3
"""Qualify prepared server caches and update reuse without claiming Thor timings.

Native donor generation/consumption is separately evidenced by the cache package.
These regressions exercise disposable host data, the real Java tar extractor,
ordinary saving, ownership, optional recovery, contact capture, and input guards.
"""
import argparse
import ast
import contextlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path(__file__).parent
sys.path[:0] = [str(TOOLS), str(ROOT/'tools/android'), str(ROOT/'tools'),
               str(ROOT/'android/guest')]
import build_startup_caches_apk as derivative
import build_apk as base
import qualify_startup_perf as closure
import stationary_contact_evidence

# Keep the accepted contact/save/input gates and add meaningful cache/migration
# scenarios. Counts are lower bounds, not a claimed physical acceptance count.
TEST_MODULES = (
    ('test_contact_interaction_package', 11), ('test_contact_capture', 7),
    ('test_stationary_contact_evidence', 10),
    ('test_character_reopen_guest', 20), ('test_character_guest', 16),
    ('test_character_server', 24),
    ('test_session_budget_guest', 16), ('test_session_budget_java', 5),
    ('test_ground_repair', 8), ('test_acceptance', 9),
    ('test_input', 30), ('test_rfb_buffered_input', 5),
    ('test_server_worktree_reuse', 15), ('test_native_client_upgrade', 5),
    ('test_wine_refresh', 10), ('test_startup_cache_integration', 7),
    ('test_runtime_timestamps', 7),
    ('test_startup_caches_package', 17),
    ('test_server_cache_package', 10),
    ('test_server_message_cache_format', 15), ('test_stable_worktree_identity', 4),
    ('test_texture_header_index', 13),
)
PATH_SUITES = (
    ('startup_client_worktree_regressions', 'tools/android/client/test_guest.py', 27),
    ('startup_tar_extractor_regressions', 'tools/android/test_archive.py', 26),
    ('startup_native_server_cache_observer', 'tools/android/atlasgame/test_prepare_server_caches.py', 10),
    ('startup_native_server_message_sources', 'tools/android/atlasgame/test_server_message_source_contract.py', 11),
)

# These sources establish the native cache layout, dependency dates, actual TSR
# completion/exit and immediate native error reporting. They are observation
# contracts; this derivative does not rebuild MapServer from these files.
NATIVE_CACHE_CONTRACT_FILES = (
    'libs/UtilitiesLib/src/utils/textparser.c',
    'libs/UtilitiesLib/src/utils/textparserUtils.c',
    'libs/UtilitiesLib/src/utils/serialize.c',
    'libs/UtilitiesLib/src/utils/error.c',
    'libs/UtilitiesLib/src/utils/utils.c',
    'libs/UtilitiesLib/src/utils/FolderCache.c',
    'libs/UtilitiesLib/src/utils/fileutil.c',
    'libs/UtilitiesLib/src/language/MessageStore.c',
    'libs/UtilitiesLib/src/components/StringTable.c',
    'libs/UtilitiesLib/src/components/StashTable.c',
    'MapServer/src/serverError.c',
    'MapServer/src/svr/svr_init.c',
    'MapServer/src/generator/encounter.c',
    'MapServer/src/storyarc/storyarcutil.c',
)
GENERATOR_SOURCE_FILES = (
    'tools/android/atlasgame/prepare_server_caches.py',
    'tools/android/atlasgame/server_message_source_contract.py',
    'tools/android/atlasgame/prepare_device_assets.py',
    'tools/android/client/package_client_runtime.py',
    'tools/android/client/prepare_client_prerequisites.py',
    'tools/android/game/package_game_runtime.py',
    'tools/android/dbserver/prepare_device_assets.py',
    'tools/generate_runtime_data.py',
    'tools/fetch_runtime_asset_bundle.py',
    'assets/reference-inputs-receipt.json',
    'android/native/server-cache-launcher.c',
    'tools/android/interactive/qualify_runtime_timestamps.py',
    'database/client-texture-index/overlay/Game/src/render/coh_texture_header_index.h',
)


def host_python_closure(names):
    """Pin static imports across actual host-generator directories.

    Identically named flat modules can coexist in the host pipeline. Pin every
    matching repository source rather than guessing which import path wins;
    dynamic file-identity imports remain explicitly listed above.
    """
    found = set(names)
    queue = [ROOT/name for name in names if name.endswith('.py')]
    visited = set()
    directories = tuple(ROOT/name for name in (
        'tools', 'tools/android', 'tools/android/interactive',
        'tools/android/client', 'tools/android/dbserver', 'tools/android/game',
        'tools/android/atlasgame', 'android/guest'))
    while queue:
        path = queue.pop()
        if path in visited:
            continue
        visited.add(path)
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                for directory in (path.parent, *directories):
                    candidate = directory/(module.replace('.', '/')+'.py')
                    if candidate.is_file():
                        name = candidate.relative_to(ROOT).as_posix()
                        if name not in found:
                            found.add(name)
                            queue.append(candidate)
    return found


def suite_module(name, path=None):
    if path is None:
        return importlib.import_module(name)
    specification = importlib.util.spec_from_file_location(name, ROOT/path)
    derivative.require(specification is not None and specification.loader is not None,
                       'Qualification suite cannot be loaded: '+str(path))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def source_paths():
    names = set(derivative.SOURCE_FILES)
    names.update(path.relative_to(ROOT).as_posix() for path in
                 (ROOT/'.github/workflows').glob('*.yml'))
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    # TarExtractor and the installer are compiled into the derivative APK.
    # Pin every authored installer source and its actual Java host fixture.
    for directory in ('android/app/src/main/java', 'android/interactive/src/main/java',
                      'tools/android/java'):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/directory).rglob('*.java'))
    names.update(path.relative_to(ROOT).as_posix() for path in
                 (ROOT/'android/interactive/src/main/res').rglob('*') if path.is_file())
    names.add(Path(__file__).relative_to(ROOT).as_posix())
    for name, _ in TEST_MODULES:
        names.add(Path(suite_module(name).__file__).relative_to(ROOT).as_posix())
    names.update(path for _, path, _ in PATH_SUITES)
    names.update('upstream/ouroboros/'+name for name in stationary_contact_evidence.NATIVE_CONTRACT_FILES)
    names.update('upstream/i24/'+name for name in stationary_contact_evidence.DATA_CONTRACT_FILES)
    names.update('upstream/ouroboros/'+name for name in NATIVE_CACHE_CONTRACT_FILES)
    names.update(GENERATOR_SOURCE_FILES)
    native_generator = derivative.module('qualified_server_cache_generation',
        ROOT/'tools/android/atlasgame/prepare_server_caches.py')
    names.update(native_generator.GENERATOR_SOURCES)
    names.update(('docs/source-manifest.json', 'docs/data-manifest.json', 'upstream-lock.json',
        'source-target.json', 'tools/android/interactive/classify_interactive_change.py',
        'tools/android/interactive/test_classify_interactive_change.py',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json',
        'tools/android/interactive/qualify_startup_perf.py'))
    return sorted(host_python_closure(closure.local_python_closure(names)))


def regressions():
    results = {}
    suites = [(name, None, minimum) for name, minimum in TEST_MODULES]+list(PATH_SUITES)
    for name, path, minimum in suites:
        suite = unittest.defaultTestLoader.loadTestsFromModule(suite_module(name, path))
        derivative.require(suite.countTestCases() >= minimum,
                           name+' lost required focused coverage')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144,
                           name+' produced unbounded qualification output')
        derivative.require(result.wasSuccessful() and not result.skipped,
                           name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'
        time.tzset()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in derivative.HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths()}
    results = regressions()
    for name, pin in pins.items():
        base.checked_file(ROOT/name, pin)
    receipt = {
        'format': 1, 'status': 'passed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor_apk_sha256': derivative.DONOR_APK['sha256'],
        'source_files': pins, 'test_suites': results,
        'tests_run': sum(item['tests_run'] for item in results.values()),
        'checks': {name: True for name in derivative.CHECKS},
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'native_runtime_booted': False, 'dialog_semantics_validated': False,
        'native_client_or_server_recompiled': False,
        'long_prior_gameplay_milestones_repeated': False,
        'retained_payloads_verified': len(donor['payloads']),
        'authored_java_sources_verified': len(java), 'changed_java_sources': changed,
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host regressions establish identity, bounds, migration, '
            'ordinary-save/contact/input retention and real extractor behavior. The separate '
            'server-cache package must prove exact native generation and consumption. No '
            'seconds saved or five-minute Thor startup is established by these checks.',
        'preserved_state': 'Existing imports, private profile, PostgreSQL rows, credentials '
            'and generated caches are retained. Closed cache reuse requires genuine owned '
            'process cleanup. Unknown or changed inputs take the existing safe preparation path.',
    }
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh startup-cache qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified startup-cache candidate:', receipt['tests_run'],
          'focused host checks; physical startup/contact test pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__':
    main()

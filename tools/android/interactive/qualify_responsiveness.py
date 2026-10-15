#!/usr/bin/env python3
"""Focused qualification of new responsiveness code, preserving existing guards."""
import argparse
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android/game'),
               str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_responsiveness_apk as derivative
import build_apk as base
import qualify_startup_perf as prior

TEST_MODULES = (
    ('test_responsiveness_package', 10), ('test_texture_header_index', 5),
    ('test_graphics_profile', 7), ('test_client_attempt_retry', 12),
    ('test_native_client_upgrade', 5), ('test_prepare_character_events_source', 3),
    ('test_prepare_client_texture_source', 3),
    ('test_session_budget_guest', 13), ('test_session_budget_java', 5),
    ('test_character_reopen_guest', 14), ('test_ground_repair', 8),
    ('test_guest', 16), ('test_character_guest', 16), ('test_acceptance', 8),
    ('test_server_worktree_reuse', 10), ('test_character_readiness', 14),
    ('test_rfb_buffered_input', 5), ('test_input', 30), ('test_classify_interactive_change', 1),
)


def source_paths():
    names = set(derivative.SOURCE_FILES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'tools').glob('prepare*source.py'))
    names.update(path.relative_to(ROOT).as_posix() for path in base.java_sources(
        ROOT/'android/interactive/src/main', ROOT/'out/no-generated-java'))
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/interactive/src/main/res').rglob('*') if path.is_file())
    for directory in ('patches/character-events', 'patches/client-texture-index', 'patches/client-graphics',
                      'database/character-events', 'database/client-texture-index', 'database/client-graphics',
                      'patches/mapserver-progress', 'database/mapserver-progress', 'patches/game-loopback'):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/directory).rglob('*') if path.is_file())
    for module_name, _, expected_name in derivative.native_package.INPUTS.values():
        module = importlib.import_module(module_name)
        receipt = getattr(module, expected_name)()
        names.add('tools/'+module_name+'.py')
        for name in receipt.get('source_sha256', {}):
            names.add('upstream/ouroboros/'+name)
    names.update('upstream/ouroboros/'+name for name in derivative.native_package.SCHEMA_FILES)
    for module_name, _ in TEST_MODULES:
        module = importlib.import_module(module_name)
        names.add(Path(module.__file__).relative_to(ROOT).as_posix())
    names.update(('tools/android/game/test_character_events.py', 'tools/prepare_runtime.py',
        'tools/package_reference_runtime.py', 'tools/verify_source.py', 'upstream-lock.json',
        'source-target.json', 'docs/source-manifest.json',
        'tools/android/interactive/build_apk.py', 'tools/android/interactive/build_startup_perf_apk.py',
        'tools/android/interactive/qualify_startup_perf.py',
        'tools/android/interactive/build_session_window_apk.py',
        'tools/android/interactive/build_atlas_gameplay_apk.py',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json',
        '.github/workflows/android-responsiveness-native.yml',
        'docs/'+derivative.NOTES_NAME))
    return sorted(prior.local_python_closure(names))


def regressions():
    results = {}
    for name, minimum in TEST_MODULES:
        loaded = importlib.import_module(name)
        suite = unittest.defaultTestLoader.loadTestsFromModule(loaded)
        derivative.require(suite.countTestCases() >= minimum, name+' lost required regression coverage')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped focused checks')
        output = captured.getvalue()
        if output: print(output, end='')
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    # The real Windows event producer executes separately in the native job.
    events = importlib.import_module('test_character_events')
    suite = unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromTestCase(events.NativeCharacterEventObserverTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(events.NativeCharacterEventLinuxIntegrationTests)))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    derivative.require(result.wasSuccessful() and not result.skipped and result.testsRun >= 9,
                       'Independent native event observer checks failed')
    results['native_character_event_observer'] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'; time.tzset()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in derivative.HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    paths = source_paths()
    pins = {name: base.file_pin(ROOT/name) for name in paths}
    results = regressions()
    for name, pin in pins.items(): base.checked_file(ROOT/name, pin)
    # Native build receipts cannot replace prepared-cache generation history.
    policy_tests = importlib.import_module('test_session_budget_guest')
    reopen_tests = importlib.import_module('test_character_reopen_guest')
    prior.verify_policy(policy_tests, reopen_tests)
    receipt = {'format': 1, 'status': 'passed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor_apk_sha256': derivative.DONOR_APK['sha256'],
        'source_files': pins, 'test_suites': results,
        'tests_run': sum(value['tests_run'] for value in results.values()),
        'checks': {name: True for name in derivative.CHECKS},
        'policy': prior.POLICY, 'physical_gameplay_validated': False, 'native_runtime_booted': False,
        'donor': derivative.donor_link(), 'retained_payloads_verified': len(donor['payloads']),
        'authored_java_sources_verified': len(java), 'changed_java_sources': changed,
        'native_source_receipts': {key: getattr(importlib.import_module(module_name), expected_name)()
            for key, (module_name, _, expected_name) in derivative.native_package.INPUTS.items()},
        'performance_measurement': 'Host correctness, file-open reduction and immediate flush contracts; physical loading time and FPS remain unmeasured',
        'native_windows_producer_fixture': 'required by the separately completed native workflow',
        'long_prior_gameplay_milestones_repeated': False}
    derivative.validate_qualification(receipt, commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified responsiveness candidate:', receipt['tests_run'], 'focused checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()

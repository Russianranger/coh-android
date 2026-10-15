#!/usr/bin/env python3
"""Qualify the task observer/UI and retained save/input/cache guards on the host.

This receipt makes no physical gameplay or timing claim. The animation producer
must separately prove actual consumption by the unchanged stock MapServer.
"""
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
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'),
               str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_task_gate_apk as derivative
import build_apk as base
import qualify_startup_caches as closure
import stationary_contact_evidence

TEST_MODULES = (
    ('test_task_gate_package', 18), ('test_task_gate_evidence', 16),
    ('test_task_gate_native_contract', 11), ('test_task_gate_integration', 11),
    ('test_task_gate_java', 6),
    ('test_character_logout_position', 10), ('test_stationary_contact_evidence', 12),
    ('test_contact_capture', 7), ('test_character_server', 24),
    ('test_character_reopen_guest', 20), ('test_ground_repair', 8),
    ('test_character_readiness', 14), ('test_session_budget_guest', 16),
    ('test_session_budget_java', 5), ('test_input', 30),
    ('test_rfb_buffered_input', 5), ('test_server_worktree_reuse', 15),
    ('test_wine_refresh', 10), ('test_stable_worktree_identity', 4),
    ('test_server_cache_package', 10), ('test_server_message_cache_format', 15), ('test_classify_interactive_change', 2),
)
PATH_SUITES = (
    ('task_native_animation_pack_regressions', 'tools/android/atlasgame/test_server_animations.py', 13),
    ('task_retained_tar_extractor_regressions', 'tools/android/test_archive.py', 26),
)
CHECK_SUITES = {
    'task_identity_completion_and_save_guards_verified':
        ('test_task_gate_evidence', 'test_task_gate_native_contract', 'test_task_gate_integration',
         'test_character_logout_position', 'test_character_server',
         'test_character_reopen_guest'),
    'owned_command_delivery_and_capture_bounds_verified':
        ('test_task_gate_java', 'test_input', 'test_rfb_buffered_input', 'test_contact_capture'),
    'retained_contact_input_recovery_and_persistence_guards_verified':
        ('test_stationary_contact_evidence', 'test_ground_repair', 'test_session_budget_guest',
         'test_session_budget_java', 'test_character_readiness'),
    'animation_layout_fallback_and_native_proof_rejection_verified':
        ('task_native_animation_pack_regressions',),
    'retained_native_payload_and_actual_extraction_verified':
        ('test_task_gate_package', 'test_server_cache_package', 'test_server_worktree_reuse',
         'test_wine_refresh', 'test_stable_worktree_identity', 'test_classify_interactive_change',
         'task_retained_tar_extractor_regressions'),
}


def source_paths():
    names = set(derivative.SOURCE_FILES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    names.update(path.relative_to(ROOT).as_posix() for path in base.java_sources(
        ROOT/'android/interactive/src/main', ROOT/'out/no-generated-java'))
    names.update(path.relative_to(ROOT).as_posix() for path in
                 (ROOT/'android/interactive/src/main/res').rglob('*') if path.is_file())
    for module_name, _ in TEST_MODULES:
        names.add(Path(importlib.import_module(module_name).__file__).relative_to(ROOT).as_posix())
    names.update(path for _, path, _ in PATH_SUITES)
    for module_name in ('stationary_contact_evidence', 'task_gate_evidence'):
        contract = importlib.import_module(module_name)
        names.update('upstream/ouroboros/'+name for name in contract.NATIVE_CONTRACT_FILES)
        names.update('upstream/i24/'+name for name in contract.DATA_CONTRACT_FILES)
    native_contract = importlib.import_module('test_task_gate_native_contract')
    names.update('upstream/ouroboros/'+name for name in native_contract.EXTRA_NATIVE)
    names.update('upstream/i24/'+name for name in native_contract.EXTRA_DATA)
    generator = derivative.module('task_qualification_native_animation_sources',
        ROOT/'tools/android/atlasgame/prepare_server_animations.py')
    names.update(generator.GENERATOR_SOURCES)
    names.update(('docs/source-manifest.json', 'docs/data-manifest.json',
        'upstream-lock.json', 'source-target.json',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json'))
    return sorted(closure.host_python_closure(names))


def regressions():
    results = {}
    suites = [(name, None, minimum) for name, minimum in TEST_MODULES]+list(PATH_SUITES)
    for name, path, minimum in suites:
        suite = unittest.defaultTestLoader.loadTestsFromModule(closure.suite_module(name, path))
        derivative.require(suite.countTestCases() >= minimum,
                           name+' lost required focused coverage')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
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
    # A check exists only after every associated scenario actually ran, passed
    # and had no skip. The donor preflight independently extracted real payloads.
    checks = {name: all(results.get(suite, {}).get('status') == 'passed'
                       and results[suite]['skipped'] == 0
                       and results[suite]['tests_run'] > 0 for suite in suites)
              for name, suites in CHECK_SUITES.items()}
    checks['retained_native_payload_and_actual_extraction_verified'] &= (
        donor['server_payload_extraction_preflight']['status'] == 'passed')
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'native_runtime_booted': False, 'dialog_semantics_validated': False,
        'native_client_or_server_recompiled': False, 'long_prior_gameplay_milestones_repeated': False,
        'retained_payloads_verified': len(donor['payloads']), 'authored_java_sources_verified': len(java),
        'changed_java_sources': changed,
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host checks establish command/session/task bounds, SQL evidence, '
            'normal-save retention, native animation envelope/fallback and rejection of invalid native proof. '
            'Actual stock MapServer pack consumption is a separate required producer receipt. '
            'No Thor timing savings or physical task acceptance is established here.',
        'preserved_state': 'The current private profile, imported assets, PostgreSQL data and exact 93 '
            'prepared server caches remain retained. Completed physical milestones are not repeated.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh task-gate qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified task-gate candidate:', receipt['tests_run'], 'host checks; physical task/timing pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Focused optional-recovery/contact capture qualification without native boot."""
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
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'), str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_contact_interaction_apk as derivative
import build_apk as base
import qualify_startup_perf as closure
import stationary_contact_evidence

TEST_MODULES = (
    ('test_contact_interaction_package', 11), ('test_contact_capture', 7),
    ('test_stationary_contact_evidence', 10),
    ('test_character_reopen_guest', 20), ('test_character_guest', 16),
    ('test_character_server', 24),
    ('test_session_budget_guest', 16), ('test_session_budget_java', 5),
    ('test_ground_repair', 8), ('test_acceptance', 9),
    ('test_input', 30), ('test_rfb_buffered_input', 5),
)


def source_paths():
    names = set(derivative.SOURCE_FILES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    names.update(path.relative_to(ROOT).as_posix() for path in base.java_sources(
        ROOT/'android/interactive/src/main', ROOT/'out/no-generated-java'))
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/interactive/src/main/res').rglob('*') if path.is_file())
    for module_name, _ in TEST_MODULES:
        names.add(Path(importlib.import_module(module_name).__file__).relative_to(ROOT).as_posix())
    names.update('upstream/ouroboros/'+name for name in stationary_contact_evidence.NATIVE_CONTRACT_FILES)
    names.update('upstream/i24/'+name for name in stationary_contact_evidence.DATA_CONTRACT_FILES)
    names.update(('docs/source-manifest.json', 'docs/data-manifest.json', 'upstream-lock.json',
        'source-target.json', 'tools/android/interactive/classify_interactive_change.py',
        'tools/android/interactive/test_classify_interactive_change.py',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
        'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json',
        'tools/android/interactive/qualify_startup_perf.py'))
    return sorted(closure.local_python_closure(names))


def regressions():
    results = {}
    for name, minimum in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() >= minimum, name+' lost required contract coverage')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped focused checks')
        output = captured.getvalue()
        if output: print(output, end='')
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in derivative.HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths()}
    results = regressions()
    for name, pin in pins.items(): base.checked_file(ROOT/name, pin)
    receipt = {'format': 1, 'status': 'passed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor_apk_sha256': derivative.DONOR_APK['sha256'],
        'source_files': pins, 'test_suites': results, 'tests_run': sum(item['tests_run'] for item in results.values()),
        'checks': {name: True for name in derivative.CHECKS}, 'donor': derivative.donor_link(),
        'physical_gameplay_validated': False, 'native_runtime_booted': False,
        'dialog_semantics_validated': False, 'native_client_or_server_recompiled': False,
        'retained_payloads_verified': len(donor['payloads']), 'authored_java_sources_verified': len(java),
        'changed_java_sources': changed, 'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'retained_native_provenance': donor['native_responsiveness']['build_provenance'],
        'contact_evidence_scope': 'User-requested fresh views and optional identity-bound native initiation records; conversation/mission semantics require human assessment',
        'server_startup_optimization': 'deferred', 'long_prior_gameplay_milestones_repeated': False}
    derivative.validate_qualification(receipt, commit)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified optional-ground/contact candidate:', receipt['tests_run'], 'focused checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Qualify startup reuse, bounded readiness and buffered RFB input without native boot.

Retained ground/save/budget guards and the source closure are checked with focused
host regressions. Host fixture savings do not establish physical startup duration,
native FPS acceleration or the next exterior-position reopen.
"""
import argparse
import ast
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path(__file__).parent
GUEST = ROOT / 'android/guest'
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(GUEST))
# Archived native log records use the guest's TZ=UTC clock basis. Set it before
# importing test modules because they derive fixture milliseconds at import.
os.environ['TZ'] = 'UTC'
time.tzset()
import build_apk as package
import build_startup_perf_apk as derivative
import audit_atlas_beacon_inputs as beacon

TEST_MODULES = (
    ('test_session_budget_guest', 13),
    ('test_session_budget_java', 5),
    ('test_character_reopen_guest', 14),
    ('test_ground_repair', 8),
    ('test_guest', 16),
    ('test_character_guest', 16),
    ('test_acceptance', 8),
    ('test_startup_perf_package', 24),
    ('test_session_window_package', 13),
    ('test_server_worktree_reuse', 10),
    ('test_character_readiness', 14),
    ('test_rfb_buffered_input', 5),
    ('test_input', 30),
    ('test_classify_interactive_change', 1),
    ('test_atlas_beacon_inputs', 9),
)
POLICY = {
    'menu_seconds': 1200, 'connected_seconds': 1200,
    'launcher_cap_seconds': 2040, 'overall_reserve_seconds': 120,
    'recovery_age_ms': 600000, 'save_request_age_ms': 420000,
    'neutral_reserve_ms': 60000, 'save_proof_reserve_ms': 180000,
}
EXTRA_SOURCES = (
    'android/interactive/src/main/AndroidManifest.xml',
    'android/native/client-launcher.c',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'tools/android/interactive/test_guest.py',
    'tools/android/interactive/test_character_guest.py',
    'tools/android/interactive/test_acceptance.py',
    'tools/android/interactive/audit_atlas_beacon_inputs.py',
    'tools/android/interactive/test_atlas_beacon_inputs.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.11.4-testing.txt',
    'docs/android-evidence/atlas-beacon-input-preflight.json',
    'source-target.json',
    'assets/reference-inputs-receipt.json',
    'docs/android-evidence/client-test-package-review-36707839624.json',
    'upstream/i24/data/maps/city_zones/city_01_01/city_01_01_layer_beacons.txt',
)


def require(value, message):
    if not value:
        raise ValueError(message)


def local_python_closure(paths):
    """Pin static local imports, including fixture modules imported by a suite.

    Both local import directories are explicit. Standard-library modules are
    external dependencies; dynamically loaded repository files are separately
    listed by the derivative builder and EXTRA_SOURCES.
    """
    queue = [ROOT / name for name in paths if name.endswith('.py')]
    found = set(paths)
    seen = set()
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                # Repository modules use flat imports within these directories.
                for directory in (TOOLS, GUEST):
                    candidate = directory / (name.replace('.', '/') + '.py')
                    if candidate.is_file():
                        relative = candidate.relative_to(ROOT).as_posix()
                        if relative not in found:
                            found.add(relative)
                            queue.append(candidate)
                        break
    return found


def source_paths():
    names = set(derivative.SOURCE_FILES) | set(EXTRA_SOURCES)
    # Include every authored Java input (not just the one edited transport),
    # plus the exact resource input compiled by the package job.
    names.update(path.relative_to(ROOT).as_posix() for path in
                 package.java_sources(ROOT / 'android/interactive/src/main', TOOLS / 'no-generated-java'))
    names.update(path.relative_to(ROOT).as_posix() for path in
                 (ROOT / 'android/interactive/src/main/res').rglob('*') if path.is_file())
    names.update(path for path, _ in beacon.INVENTORIES)
    names.update('upstream/ouroboros/' + path for path in beacon.SOURCE_FILES)
    # The existing replay validates the authored City Hall spawn transform.
    metadata_path = ROOT / 'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json'
    names.add(json.loads(metadata_path.read_text())['map_source']['path'])
    return sorted(local_python_closure(names))


def run_regressions():
    results, modules = {}, {}
    for name, minimum in TEST_MODULES:
        module = importlib.import_module(name)
        modules[name] = module
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        require(suite.countTestCases() >= minimum,
                name + ' lost required focused regression coverage')
        java_scenarios = None
        if name == 'test_session_budget_java':
            cases = module.CASES
            require(isinstance(cases, dict) and cases
                    and all(isinstance(group, (tuple, list)) and group for group in cases.values()),
                    'Java budget harness has no independent scenario groups')
            scenarios = [scenario for group in cases.values() for scenario in group]
            methods = {method.removeprefix('test_') for method in
                       unittest.defaultTestLoader.getTestCaseNames(module.SessionBudgetJavaTests)}
            require(methods == set(cases) and len(scenarios) >= 20
                    and len(set(scenarios)) == len(scenarios)
                    and all(isinstance(scenario, str) and scenario for scenario in scenarios),
                    'Java budget coverage must execute every distinct named scenario group')
            java_scenarios = len(scenarios)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        output = captured.getvalue()
        require(len(output) <= 65536, name + ' produced unbounded host output')
        if output:
            print(output, end='')
        require(result.wasSuccessful() and not result.skipped,
                name + ' failed or skipped required regressions')
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
        if java_scenarios is not None:
            results[name]['independent_java_scenarios_run'] = java_scenarios
        if name == 'test_server_worktree_reuse':
            lines = [line.removeprefix('SERVER_DATA_HOST_METRIC ') for line in output.splitlines()
                     if line.startswith('SERVER_DATA_HOST_METRIC ')]
            require(len(lines) == 1, 'Cache suite must report its one actual cold/warm host fixture')
            metrics = json.loads(lines[0])
            require(set(metrics) == {'fixture_immutable_leaves', 'cold_seconds', 'warm_seconds',
                    'cold_symlink_creations', 'warm_symlink_creations', 'warm_immutable_directory_checks'}
                    and metrics['cold_symlink_creations'] == metrics['fixture_immutable_leaves']
                    and metrics['warm_symlink_creations'] == 0
                    and 0 <= metrics['warm_seconds'] < metrics['cold_seconds'],
                    'Cache host fixture did not establish its bounded work reduction')
            results[name]['host_fixture_metrics'] = metrics
    return results, modules


def verify_ground_replay(ground):
    metadata = json.loads(ground.METADATA.read_text())
    require(metadata['fixture']['sha256'] == package.file_pin(ground.FIXTURE)['sha256']
            and metadata['fixture']['lines_are_exact_unmodified_original_log_records'] is True
            and metadata['replay']['receipt_is_synthetic_for_parser_exercise_only'] is True
            and metadata['replay']['synthetic_sent_utc_ms'] == ground.REPLAY_SENT_MS
            and metadata['replay']['synthetic_now_utc_ms'] == ground.REPLAY_NOW_MS,
            'Exact Thor fixture or labeled synthetic receipt differs')
    recovered = ground.replay()
    require(recovered is not None and recovered['position'] == ground.THOR_POSITION
            and recovered['elapsed_ms'] == 30000
            and recovered['full_collision_geometry_verified'] is False,
            'Archived native Thor ground observations did not pass the retained observer')
    map_source = metadata['map_source']
    require(package.file_pin(ROOT / map_source['path'])['sha256'] == map_source['sha256'],
            'Authored Atlas spawn source pin differs')
    translation = [sum(step['translation'][axis] for step in map_source['translation_chain'])
                   for axis in range(3)]
    require(all(abs(a - b) < .00001 for a, b in zip(translation, ground.THOR_POSITION)),
            'Authored City Hall spawn differs from the recovered native observations')
    return {
        'position': recovered['position'], 'elapsed_ms': recovered['elapsed_ms'],
        'fixture': metadata['fixture'], 'synthetic_delivery_receipt': True,
        'physical_collision_geometry_verified': False,
        'authored_map_source': {'path': map_source['path'], **package.file_pin(ROOT / map_source['path'])},
    }


def verify_policy(module, reopen_tests):
    guest = module.policy
    expected = {
        'CONNECTED_SECONDS': POLICY['connected_seconds'],
        'LAUNCHER_BUDGET_SECONDS': POLICY['launcher_cap_seconds'],
        'OPERATION_RESERVE_SECONDS': POLICY['overall_reserve_seconds'],
        'RECOVERY_MAX_AGE_MS': POLICY['recovery_age_ms'],
        'SAVE_REQUEST_AGE_MS': POLICY['save_request_age_ms'],
        'NEUTRAL_RESERVE_MS': POLICY['neutral_reserve_ms'],
        'SAVE_PROOF_RESERVE_MS': POLICY['save_proof_reserve_ms'],
    }
    require(derivative.POLICY == POLICY
            and all(getattr(guest, name) == value for name, value in expected.items()),
            'Qualification, guest and packaging phase-budget policies differ')
    require(module.creation.INTERACTION_SECONDS == POLICY['menu_seconds']
            and module.creation.OVERALL_SECONDS == 5400
            and reopen_tests.server.RELOCATION_MAX_AGE_MS == POLICY['recovery_age_ms']
            and reopen_tests.server.LOGOUT_MAX_AGE_MS == 120000,
            'Existing menu, operation or ordinary recovery/logout evidence age bounds changed')
    launcher = (ROOT / 'android/native/client-launcher.c').read_text()
    require('*lifetime_ms=36*60*1000;' in launcher
            and POLICY['launcher_cap_seconds'] + POLICY['overall_reserve_seconds'] == 36 * 60,
            'Reserved reopen hard cap no longer fits the retained native launcher lifetime')


def verify_retained_donor(args):
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report,
        args.ground_build_report, args.avatar_build_report, args.retained_source_report)
    _, sources, changed = derivative.current_java_sources(donor, TOOLS / 'no-generated-java')
    rfb = next(iter(derivative.JAVA_CHANGES))
    derivative.validate_rfb_scope((ROOT / rfb).read_bytes(), donor['java_sources'][rfb])
    with zipfile.ZipFile(args.donor_apk) as archive:
        for name in derivative.HELPERS:
            derivative.validate_guest_scope(name, archive.read('assets/runtime/' + name),
                                            (GUEST / name).read_bytes())
        require('assets/runtime/' + derivative.GUEST_ADDITION not in archive.namelist(),
                'Startup cache module collides with the retained donor')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in derivative.HELPERS:
            package.checked_file(GUEST / Path(name).name, pin)
    return {'apk': derivative.DONOR_APK, 'published_commit': derivative.DONOR_COMMIT,
            'published_run_id': derivative.DONOR_RUN_ID,
            'lineage_receipts': {Path(path).name: package.file_pin(path) for path in (
                args.donor_build_report, args.ground_build_report, args.avatar_build_report,
                args.retained_source_report)},
            'payloads_verified': len(donor['payloads']), 'java_sources_verified': len(sources),
            'changed_java_sources': changed, 'guest_source_scope_verified': True,
            'native_payload_bytes_retained': True}


def qualify(commit, args):
    # Bind the full closure before tests, then require the same pins afterwards.
    # A test may use temporary files but cannot silently rewrite qualified input.
    sources = {name: package.file_pin(ROOT / name) for name in source_paths()}
    retained = verify_retained_donor(args)
    results, modules = run_regressions()
    verify_policy(modules['test_session_budget_guest'], modules['test_character_reopen_guest'])
    replay = verify_ground_replay(modules['test_ground_repair'])
    audit = beacon.audit_repo()
    require(audit['status'] == 'no_input' and audit['preflight_completed'] is True
            and all(audit[key] is False for key in ('native_graph_load_verified',
                'authentic_generated_graph_verified', 'loaded_world_crc_verified')),
            'Beacon preflight must remain a missing-input audit without graph/pathing acceptance')
    archived_audit = json.loads((ROOT / 'docs/android-evidence/atlas-beacon-input-preflight.json').read_text())
    require(archived_audit == audit, 'Archived beacon input preflight differs from fresh read-only audit')
    require(all(package.file_pin(ROOT / name) == pin for name, pin in sources.items()),
            'Qualified source input changed during focused regressions')
    receipt = {
        'format': 1, 'status': 'passed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor_apk_sha256': derivative.DONOR_APK['sha256'],
        'policy': POLICY, 'tests_run': sum(result['tests_run'] for result in results.values()),
        'java_budget_scenarios_run': results['test_session_budget_java']['independent_java_scenarios_run'],
        'test_suites': results, 'source_files': sources,
        'checks': {name: True for name in derivative.CHECKS},
        'archived_ground_replay': replay, 'beacon_preflight': audit,
        'physical_gameplay_validated': False,
        'native_runtime_booted': False,
        'retained_donor_validation': retained,
        'performance_claim_scope': 'Bounded host fixtures establish work reduction and exact decoder '
            'equivalence. The first updated launch prepares a new cold server-data generation; only '
            'later clean runs of that same verified generation can reuse the closed tree.',
        'limitations': 'Focused host regressions and an archived native-record parser replay only. '
            'No native or physical gameplay gate is repeated. Physical startup duration, native FPS '
            'and the next exterior-position reopen remain pending. The native launcher retains its '
            '10 FPS cap; transport read-call reduction does not establish native FPS acceleration. '
            'No generated Atlas beacon graph is supplied, installed or qualified; NPC/pathing/combat '
            'acceptance remains pending.',
    }
    derivative.validate_qualification(receipt, commit)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository-commit')
    for name in ('donor-apk', 'donor-build-report', 'ground-build-report',
                 'avatar-build-report', 'retained-source-report'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(),
            'Fresh focused qualification output required')
    receipt = qualify(package.source_commit(args.repository_commit), args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print('Focused startup/cache qualification passed:', receipt['tests_run'],
          'tests; beacon input missing; physical startup/FPS/exterior reopen pending')


if __name__ == '__main__':
    main()

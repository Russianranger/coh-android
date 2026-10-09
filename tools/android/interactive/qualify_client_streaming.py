#!/usr/bin/env python3
"""Qualify bounded client inventory and visual updates retaining the exact 0.13.8 native/DEX donor."""
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
    str(ROOT/'tools/android/dbserver'), str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_client_streaming_apk as derivative
import qualify_client_loading as prior
import qualify_startup_schedule as closure

TEST_MODULES = prior.TEST_MODULES + ('test_client_streaming_package', 'test_client_console_markers',
    'test_client_visual_candidates')
CHECK_SUITES = {
    'client_animation_mount_and_failure_guards_verified': ['test_client_animation_package', 'test_client_visual_schedule'],
    'missing_only_visual_assets_and_texture_index_binding_verified': ['test_client_visual_assets', 'test_client_visual_candidates',
        'test_client_visual_schedule', 'test_texture_header_index'],
    'bounded_texture_inventory_equivalence_and_symlink_guards_verified': ['test_texture_header_index', 'test_client_console_markers'],
    'retained_save_task_storage_profile_and_memory_guards_verified': list(prior.TEST_MODULES),
    'exact_payload_boundaries_and_actual_archive_extraction_verified': ['test_client_streaming_package',
        'test_client_visual_assets', 'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    names.update(derivative.validate_retained_native_sources(donor))
    # Asset requests and named-model/trick proofs dynamically select native/UI
    # source paths. Pin every reviewed input rather than relying on import ASTs.
    visual = derivative.read_json(ROOT/'assets/client-visual-manifest.json')
    names.update(visual['source_files'])
    return sorted(closure.source_closure(names))


def regressions():
    results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name+' has no focused scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualification_checks(results):
    registered = set(TEST_MODULES)
    derivative.require(len(registered) == len(TEST_MODULES) and set(results) == registered,
        'Client qualification requires the complete unique registered suite inventory')
    derivative.require(set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= registered for suites in CHECK_SUITES.values()),
        'Every client qualification check must reference registered required suites')
    return {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    java = derivative.current_sources(donor); visual = derivative.validate_visual_package(args.visual_directory)
    conservation = derivative.validate_visual_superset(donor, visual)
    derivative.verify_retained_world_geometry(args.donor_apk, visual)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'},
        'Formal qualification requires all three real PostgreSQL transaction fixtures')
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = qualification_checks(results)
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'retained_runtime_repository_commit': derivative.DONOR_COMMIT,
        'retained_setup_memory_repository_commit': derivative.RETAINED_SETUP_MEMORY_COMMIT,
        'retained_native_repository_commit': derivative.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_client_timing_validated': False,
        'physical_visual_assets_validated': False, 'native_runtime_booted': False,
        'long_prior_gameplay_milestones_repeated': False, 'runtime_refresh_required': True,
        'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
        'setup_memory_guards_preserved': True, 'java_or_dex_recompiled': False,
        'native_dbserver_recompiled': False, 'native_client_recompiled': False, 'native_mapserver_recompiled': False,
        'native_source_commit': donor['native_source_commit'], 'native_source_provenance': donor['native_source_provenance'],
        'native_client_compiled_in_current_run': False, 'native_client_package_reused': True,
        'visual_package': visual, 'visual_superset': conservation,
        'retained_world_lod_geometry_verified': True,
        'retained_server_cache_and_save_fix_verified': True,
        'postgresql_emission_fixture_verified': True, 'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'retained_baseline_payloads_verified': 71, 'authored_java_sources_verified': len(java),
        'changed_java_sources': [], 'retained_java_sources': 19, 'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host scenarios qualify identical texture inventory identity/security with reduced '
            'repeated filesystem work, console observation and exact append-only missing visual leaves. They do not '
            'establish physical client startup savings, first-encounter streaming improvement or complete world/NPC rendering.',
        'preserved_state': 'Immediate public 0.13.8 Game/client ZIP, 20 DLLs, all server packs and generated-cache '
            'schemas, animation bytes, exact 19 Java sources/DEX/resources, imported assets, private profile and '
            'completed tasks retain identity. Only three selected guest helpers, two visual payloads and '
            'two verification manifests change.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh client qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified client asset candidate:', receipt['tests_run'], 'host checks; physical client timing and visuals pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'visual-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()

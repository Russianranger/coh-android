#!/usr/bin/env python3
"""DRAFT outside the repository: source-attributed beacon preflight.

This does not generate a graph, modify a shipping APK, or certify device speed.
Only the two obsolete .13-to-.14 reconstruction cases use historical inputs.
All other current generator, graph, cache, and package cases execute unchanged.
"""
import argparse
import contextlib
import hashlib
import importlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ORIGINAL_COMMIT = '25f821da9e782281953412543057054abd8dd320'
ORIGINAL_ARTIFACT = {'bytes': 6137683, 'sha256': '4c42683fe1cad44f6bed1df5f0a649d36b0bc68761f91f2ad26e78d4ecc60c8a'}
ORIGINAL_SCOPE = 'append_only_original_ui_sweep_and_authentic_atlas_beacons_retaining_public_0_13_13'
HELPERS = ('android/guest/local_character_server.py', 'android/guest/native_training_save.py')
MODULES = ('test_prepare_atlas_beacon_generator_source', 'test_generate_atlas_beacons',
           'test_atlas_beacon_package', 'test_beacon_runtime_profiles', 'test_ui_beacon_package',
           'test_classify_storage_cleanup_change', 'test_server_worktree_reuse', 'test_atlas_beacon_preflight')
HISTORICAL = frozenset('test_ui_beacon_package.UiBeaconPackagingTests.' + name for name in (
    'test_actual_public_saved_character_delta_is_closed_to_reviewed_normalization_and_beacons',
    'test_required_geometry_source_proof_and_cache_key_cannot_be_changed_or_moved_after_checkout'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or linked preflight input: ' + str(path))
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            size += len(block)
            digest.update(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def qualification(archive):
    require(pin(archive) == ORIGINAL_ARTIFACT, 'Exact original .14 qualification artifact required')
    with zipfile.ZipFile(archive) as source:
        rows = source.infolist()
        require(len(rows) == 1 and rows[0].filename == 'ui-beacon-qualification.json'
                and rows[0].file_size <= 128 * 1024 * 1024, 'Original qualification archive differs')
        value = json.loads(source.read(rows[0]))
    require(value.get('format') == 1 and value.get('status') == 'passed'
            and value.get('repository_commit') == ORIGINAL_COMMIT
            and value.get('scope') == ORIGINAL_SCOPE and value.get('tests_run') == 1102,
            'Original qualification identity differs')
    require(value.get('test_suites', {}).get('test_ui_beacon_package') ==
            {'tests_run': 14, 'status': 'passed', 'skipped': 0}, 'Original package evidence differs')
    return value


def verify_helpers(directory, document):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), 'Historical source directory differs')
    for name in HELPERS:
        path = directory / name
        for parent in path.parents:
            if parent == directory:
                break
            require(not parent.is_symlink(), 'Linked historical source parent refused')
        require(pin(path) == document['source_files'][name], 'Historical source bytes differ: ' + name)


@contextlib.contextmanager
def historical_inputs(package, source, document, donor):
    # No AST rewriting, line-ending normalization, or replacement implementation.
    verify_helpers(source, document)
    require(pin(donor) == package.DONOR_APK == document['donor']['apk'], 'Exact original .13 APK required')
    with tempfile.TemporaryDirectory(prefix='coh-beacon-historical-') as temporary:
        stage = Path(temporary)
        for name in HELPERS:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(source) / name, target)
        verify_helpers(stage, document)
        target = stage / 'out/ui-beacon-donor' / package.DONOR_APK_NAME
        target.parent.mkdir(parents=True)
        # The existing test opens this verified immutable donor through its
        # ordinary fixed name; avoid a redundant 1.5 GiB copy.
        target.symlink_to(Path(donor).resolve())
        original_root = package.ROOT
        try:
            with mock.patch.object(package, 'ROOT', stage):
                yield
        finally:
            require(package.ROOT == original_root, 'Historical fixture escaped its case scope')
            verify_helpers(stage, document)
            verify_helpers(source, document)
            require(pin(donor) == package.DONOR_APK, 'Historical donor changed during cases')


def leaves(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from leaves(item)
        else:
            yield item


def execute(cases, scope):
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.TestSuite(cases))
    raw = output.getvalue()
    require(len(raw.encode()) <= 512 * 1024, 'Preflight output exceeds bound')
    print(raw, end='', flush=True)
    require(result.wasSuccessful() and not result.skipped and result.testsRun == len(cases),
            'Preflight cases failed or skipped: ' + scope)
    return {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0,
            'input_scope': scope, 'tests_executed_in_current_run': True}


def main():
    parser = argparse.ArgumentParser()
    for name in ('repository', 'historical-source', 'historical-qualification', 'donor-apk', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    root = args.repository.resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    require(head == args.repository_commit, 'Current preflight commit differs')
    subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'], cwd=root, check=True)
    sys.path[:0] = [str(root / 'tools'), str(root / 'tools/android/interactive')]
    document = qualification(args.historical_qualification)
    package = importlib.import_module('build_ui_beacon_apk')
    require(package.ROOT.resolve() == root, 'Current package validator origin differs')
    cases = [case for name in MODULES for case in leaves(
        unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))]
    historical = [case for case in cases if case.id() in HISTORICAL]
    require({case.id() for case in historical} == HISTORICAL and len(historical) == 2,
            'Exact historical reconstruction cases required')
    current = [case for case in cases if case.id() not in HISTORICAL]
    current_result = execute(current, 'current_generator_and_native_graph_contracts')
    with historical_inputs(package, args.historical_source, document, args.donor_apk):
        historical_result = execute(historical, 'current_unchanged_validators_with_exact_014_helper_inputs')
    subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'], cwd=root, check=True)
    receipt = {'format': 1, 'status': 'passed', 'repository_commit': head,
        'current': current_result, 'historical': historical_result,
        'historical_source_commit': ORIGINAL_COMMIT, 'historical_qualification': ORIGINAL_ARTIFACT,
        'historical_helper_pins': {name: document['source_files'][name] for name in HELPERS},
        'historical_case_ids': sorted(HISTORICAL), 'total_tests': len(cases),
        'excluded_cases': [], 'native_generation_proof': False,
        'shipping_assets_modified': False, 'physical_performance_gain_verified': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print('COH_ATLAS_BEACON_PREFLIGHT_TESTS ' + json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()

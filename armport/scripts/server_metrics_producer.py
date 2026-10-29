#!/usr/bin/env python3
"""Prepare exact host-tested server sources, then build two Win32 donors serially.

Only the opt-in ArmPort build jobs call this producer. It never dispatches a
workflow, changes upstream, installs a server or qualifies device execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'tools/android/interactive')]
import retained_assets
import server_package as package
import prepare_server_metrics_source as source
import map_startup_inputs as animations

VARIANTS = ('retained_progress', 'thor_certified_startup')
BASELINE_COMMIT = 'c86a57962363dbe2dc2091dadde6abdfaa2e1e1c'
BUNDLE = 'server-metrics-input.json'
MODERN_APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
MEMBER = 'assets/runtime/game-package.tar.gz'
MAX_BUNDLE = 1024 * 1024 * 1024
MAX_INPUT_FILE = 128 * 1024 * 1024
MAX_ENTRIES = 14000
require = package.require


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular producer input required: ' + str(path))
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def identity(repository_commit, run_id):
    require(re.fullmatch(r'[0-9a-f]{40}', repository_commit) and type(run_id) is int and run_id > 0,
            'Exact producer commit and Actions run required')


def baseline_root(path):
    """Historical certificate validators must keep their original source pins."""
    return package.baseline_root(path)


def fresh(path):
    original = Path(path)
    require(not original.is_symlink(), 'Linked producer output refused')
    path = original.resolve()
    require(not path.exists() and not path.is_symlink(), 'Fresh producer output required: ' + str(path))
    require(path != ROOT and ROOT / 'upstream' not in (path, *path.parents), 'Immutable producer output refused')
    path.mkdir(parents=True)
    return path


def extract_donor(apk, expected, output, variant, retained_report=None):
    """Authenticate the complete outer APK before looking at its game payload."""
    require(pin(apk) == expected, 'Exact outer donor APK differs')
    if variant == 'retained_progress':
        require(retained_report is not None and pin(retained_report) == {
            'bytes': retained_assets.REPORT_BYTES, 'sha256': retained_assets.REPORT_SHA},
            'Exact retained build report differs')
        report = package.parse_json(Path(retained_report).read_bytes())
        require(report['repository_commit'] == retained_assets.DONOR_COMMIT
                and report['sha256'] == expected['sha256'] and report['signature_verified'] is True
                and report['payload_bytes_verified'] is True, 'Retained outer donor provenance differs')
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate outer APK member')
        info = archive.getinfo(MEMBER)
        require(not info.is_dir() and not info.flag_bits & 1
                and not stat.S_ISLNK(info.external_attr >> 16) and 0 < info.file_size <= package.MAX_GAME,
                'Invalid donor game payload')
        game_archive = output / 'game-package.tar.gz'
        with archive.open(info) as src, game_archive.open('xb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
    if variant == 'retained_progress':
        require(pin(game_archive) == report['payloads'][MEMBER], 'Retained game payload differs from report')
    game, files = package.read_game_archive(game_archive)
    previous = files['game-package.json']
    _, baseline = package.validate_predecessor(previous, variant)
    # Keep original raw JSON: old native event contracts hash insertion order.
    (output / package.PREVIOUS).write_bytes(previous)
    (output / 'baseline-build-input.json').write_text(json.dumps(baseline, indent=2) + '\n')
    return {'apk': expected, 'game_archive': pin(game_archive), 'manifest': package.pin(previous),
            'mapserver': game['files']['MapServer.exe']}, baseline


def run(command, log, *, cwd=None, env=None):
    print('+ ' + ' '.join(map(str, command)), flush=True)
    with Path(log).open('w', encoding='utf-8') as output:
        process = subprocess.Popen(list(map(str, command)), cwd=cwd, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, errors='replace')
        for line in process.stdout:
            output.write(line)
            print(line, end='', flush=True)
        require(process.wait() == 0, 'Producer command failed; inspect ' + str(log))


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), 'Linked producer member')
        if path.is_file() and path.name != BUNDLE:
            result[path.relative_to(directory).as_posix()] = pin(path)
    require(0 < len(result) < MAX_ENTRIES and sum(v['bytes'] for v in result.values()) <= MAX_BUNDLE,
            'Producer input closure exceeds bound')
    return result


def stage(retained_apk, retained_report, thor_apk, animations_pigg, animation_manifest,
          output, repository_commit, run_id, upstream_root):
    identity(repository_commit, run_id)
    upstream_root = baseline_root(upstream_root)
    output = fresh(output)
    variants = {}
    # Validate genuine animation payloads before either source build is staged.
    for path, name in ((animations_pigg, 'server-animations.pigg'),
                       (animation_manifest, 'server-animation-manifest.json')):
        animations.checked(path, animations.INPUTS[name])
    inputs = output / 'animation-inputs'; inputs.mkdir()
    shutil.copyfile(animations_pigg, inputs / 'server-animations.pigg')
    shutil.copyfile(animation_manifest, inputs / 'server-animation-manifest.json')
    for variant, apk, expected, report in (
        ('retained_progress', retained_apk,
         {'bytes': retained_assets.APK_BYTES, 'sha256': retained_assets.APK_SHA}, retained_report),
        ('thor_certified_startup', thor_apk, MODERN_APK, None),
    ):
        directory = output / variant; directory.mkdir()
        donor, baseline = extract_donor(apk, expected, directory, variant, report)
        prepared = directory / 'source'
        receipt = source.prepare(prepared, variant, upstream_root, animations_pigg, animation_manifest, baseline)
        checks = directory / package.CHECKS
        run([sys.executable, ROOT / 'armport/tests/server_metrics_native.py', '--source', prepared,
             '--negative-control', upstream_root / 'upstream/ouroboros', '--upstream-root', upstream_root,
             '--report', checks],
            directory / 'source-checks.log')
        source.validate_test_report(package.parse_json(checks.read_bytes()), receipt, upstream_root)
        variants[variant] = {'donor': donor, 'source_receipt': pin(prepared / source.RECEIPT),
                             'source_checks': pin(checks)}
    manifest = {'format': 1, 'role': 'armport_server_metrics_build_input_bundle',
                'repository_commit': repository_commit, 'run_id': run_id, 'baseline_commit': BASELINE_COMMIT,
                'variants': variants,
                'files': inventory(output), 'shipping_binary_executed': False}
    (output / BUNDLE).write_text(json.dumps(manifest, indent=2) + '\n')
    verify_bundle(output, repository_commit, run_id, upstream_root)
    archive = output.with_suffix('.tar.gz')
    require(not archive.exists(), 'Producer source archive already exists')
    with tarfile.open(archive, 'w:gz') as tar:
        for name in sorted([*manifest['files'], BUNDLE]):
            tar.add(output / name, arcname=name, recursive=False)
    archive.with_suffix('.gz.sha256').write_text(pin(archive)['sha256'] + '  ' + archive.name + '\n')
    return manifest


def validate_bundle_manifest(document, repository_commit, run_id):
    identity(repository_commit, run_id)
    require(isinstance(document, dict) and set(document) == {'format', 'role', 'repository_commit',
            'run_id', 'baseline_commit', 'variants', 'files', 'shipping_binary_executed'}
            and type(document['format']) is int and document['format'] == 1
            and document['role'] == 'armport_server_metrics_build_input_bundle'
            and document['repository_commit'] == repository_commit and document['run_id'] == run_id
            and document['baseline_commit'] == BASELINE_COMMIT
            and type(document['run_id']) is int and document['shipping_binary_executed'] is False
            and set(document['variants']) == set(VARIANTS), 'Server source bundle identity differs')
    require(isinstance(document['files'], dict) and 0 < len(document['files']) < MAX_ENTRIES,
            'Server input inventory differs')
    for name, record in document['files'].items():
        safe_member(name)
        require(isinstance(record, dict) and set(record) == {'bytes', 'sha256'}
                and type(record['bytes']) is int and 0 <= record['bytes'] <= MAX_INPUT_FILE
                and re.fullmatch(r'[0-9a-f]{64}', str(record['sha256'])), 'Invalid source file pin')
    require(sum(v['bytes'] for v in document['files'].values()) <= MAX_BUNDLE, 'Input size exceeds bound')
    return document


def verify_bundle(directory, repository_commit, run_id, upstream_root):
    directory = Path(directory)
    manifest = validate_bundle_manifest(package.parse_json((directory / BUNDLE).read_bytes()),
                                        repository_commit, run_id)
    require(inventory(directory) == manifest['files'], 'Prepared bundle file identity differs')
    for variant in VARIANTS:
        path = directory / variant
        receipt = source.verify_prepared(path / 'source', upstream_root)
        previous = (path / package.PREVIOUS).read_bytes()
        game, baseline = package.validate_predecessor(previous, variant)
        require(source.canonical(receipt['baseline_receipt']) == source.canonical(baseline),
                'Source baseline differs from actual donor')
        proof = manifest['variants'][variant]
        expected_apk = MODERN_APK if variant == 'thor_certified_startup' else {
            'bytes': retained_assets.APK_BYTES, 'sha256': retained_assets.APK_SHA}
        require(proof == {'donor': {'apk': expected_apk, 'game_archive': pin(path / 'game-package.tar.gz'),
            'manifest': package.pin(previous), 'mapserver': game['files']['MapServer.exe']},
            'source_receipt': pin(path / 'source' / source.RECEIPT),
            'source_checks': pin(path / package.CHECKS)}, 'Variant input binding differs')
        _, files = package.read_game_archive(path / 'game-package.tar.gz')
        require(files['game-package.json'] == previous, 'Donor game manifest raw bytes differ')
        source.validate_test_report(package.parse_json((path / package.CHECKS).read_bytes()), receipt, upstream_root)
    for name in ('server-animations.pigg', 'server-animation-manifest.json'):
        animations.checked(directory / 'animation-inputs' / name, animations.INPUTS[name])
    return manifest


def safe_member(name):
    require(isinstance(name, str) and name, 'Invalid source archive name')
    path = PurePosixPath(name)
    reserved = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)),
                *(f'lpt{i}' for i in range(1, 10))}
    require(not path.is_absolute() and '\\' not in name and ':' not in name and '\0' not in name
            and all(p not in ('', '.', '..') and not p.endswith((' ', '.'))
                    and p.split('.')[0].casefold() not in reserved for p in name.split('/')),
            'Unsafe source archive member')
    return path


def extract(archive, output, repository_commit, run_id, upstream_root):
    identity(repository_commit, run_id)
    upstream_root = baseline_root(upstream_root)
    output = fresh(output)
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        names = [member.name for member in members]
        require(0 < len(names) <= MAX_ENTRIES and len(names) == len(set(names))
                and len({name.casefold() for name in names}) == len(names), 'Duplicate source archive member')
        require(sum(m.size for m in members) <= MAX_BUNDLE + package.MAX_JSON, 'Source archive too large')
        for member in members:
            safe_member(member.name)
            limit = package.MAX_JSON if member.name == BUNDLE else MAX_INPUT_FILE
            require(member.isfile() and 0 <= member.size <= limit, 'Nonregular or oversized source archive member')
        require(names.count(BUNDLE) == 1, 'Missing input bundle manifest')
        document = validate_bundle_manifest(package.parse_json(tar.extractfile(BUNDLE).read()),
                                            repository_commit, run_id)
        require(set(names) == set(document['files']) | {BUNDLE}, 'Source archive inventory differs')
        for member in members:
            target = output / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            if member.name != BUNDLE:
                require(pin(target) == document['files'][member.name], 'Source archive member changed')
    return verify_bundle(output, repository_commit, run_id, upstream_root)


def build(directory, output, repository_commit, run_id, upstream_root):
    require(os.name == 'nt' and shutil.which('cl'), 'Initialized genuine Windows MSVC required')
    upstream_root = baseline_root(upstream_root)
    manifest = verify_bundle(directory, repository_commit, run_id, upstream_root)
    directory, output = Path(directory).resolve(), fresh(output)
    env = dict(os.environ, CL='', _CL_='/MP1', CMAKE_BUILD_PARALLEL_LEVEL='1', MSBUILDDISABLENODEREUSE='1')
    evidence = output / 'evidence'; evidence.mkdir()
    # Existing real Windows x86 fixtures run serially, using the exact data that
    # generated the modern prepared source. The fixture binaries are retained.
    run([sys.executable, upstream_root / 'tools/test_map_startup_animation_certificate.py',
         '--animations-pigg', directory / 'animation-inputs/server-animations.pigg',
         '--animation-manifest', directory / 'animation-inputs/server-animation-manifest.json',
         '--require-windows', '--native-evidence', evidence / 'map-startup-animation-native.json'],
        evidence / 'animation-fixture.log', env=env)
    run([sys.executable, upstream_root / 'tools/test_map_startup_monorail_budget.py', '--require-windows',
         '--native-evidence', evidence / 'map-startup-monorail-native.json'],
        evidence / 'monorail-fixture.log', env=env)
    results = {}
    for variant in VARIANTS:
        inputs = directory / variant
        prepared = inputs / 'source'
        logs = evidence / variant; logs.mkdir()
        run(['cmake', '--preset', 'vs2026', '-DPATCH_EXECUTABLE=C:/Program Files/Git/usr/bin/patch.exe',
             '-DCOH_PG_PERSISTENCE_TESTS=OFF'], logs / 'configure.log', cwd=prepared, env=env)
        run(['cmake', '--build', 'out/build/vs2026', '--config', 'OptDebug', '--parallel', '1',
             '--target', 'MapServer', '--', '/nr:false', '/v:minimal'],
            logs / 'build.log', cwd=prepared, env=env)
        binary = prepared / 'out/build/vs2026/bin/OptDebug'
        artifact = output / ('server-metrics-' + variant.replace('_', '-') + '.zip')
        results[variant] = package.package(binary, prepared,
            prepared / 'out/build/vs2026/CMakeCache.txt', inputs / package.PREVIOUS,
            inputs / package.CHECKS, artifact, variant=variant, repository_commit=repository_commit,
            run_id=run_id, expected_predecessor_pin=manifest['variants'][variant]['donor']['manifest'],
            upstream_root=upstream_root)
        shutil.copyfile(binary / 'MapServer.pdb', logs / 'MapServer.pdb')
        for path in (prepared / source.RECEIPT, prepared / 'out/build/vs2026/CMakeCache.txt',
                     inputs / package.CHECKS, inputs / 'source-checks.log'):
            shutil.copyfile(path, logs / path.name)
        artifact.with_suffix('.pin.json').write_text(json.dumps(pin(artifact), indent=2) + '\n')
    record = {'format': 1, 'repository_commit': repository_commit, 'run_id': run_id,
              'baseline_commit': BASELINE_COMMIT,
              'variants_built_in_order': list(VARIANTS), 'cmake_build_parallel_level': 1,
              'msvc_appended_options': '/MP1', 'compiler_concurrency_measured': False,
              'packages': {name: value['files'] for name, value in results.items()},
              'shipping_binary_executed': False, 'physical_device_validated': False}
    (evidence / 'producer-execution.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    staging = sub.add_parser('stage')
    for name in ('retained-apk', 'retained-report', 'thor-apk', 'animations-pigg', 'animation-manifest'):
        staging.add_argument('--' + name, required=True, type=Path)
    extraction = sub.add_parser('extract')
    extraction.add_argument('--archive', required=True, type=Path)
    building = sub.add_parser('build')
    building.add_argument('--directory', required=True, type=Path)
    for action in (staging, extraction, building):
        action.add_argument('--output', required=True, type=Path)
        action.add_argument('--repository-commit', required=True)
        action.add_argument('--run-id', required=True, type=int)
        action.add_argument('--upstream-root', required=True, type=Path,
                            help='Pristine checkout of the pinned historical validator commit')
    args = vars(parser.parse_args())
    action = args.pop('command')
    result = {'stage': stage, 'extract': extract, 'build': build}[action](**args)
    print(json.dumps({'status': action + '_complete', 'run_id': result['run_id'],
                      'shipping_binary_executed': False}))


if __name__ == '__main__':
    main()

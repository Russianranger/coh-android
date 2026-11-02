#!/usr/bin/env python3
"""Run the exact modern MapServer through ARM64 app creation and zoning reopen.

Supporting test code can live at another commit. All production helpers and
native validators are imported from a separate clean candidate checkout, and
all candidate artifacts are bound to their explicit successful build/runtime.
No signing, player database, source mutation or workflow dispatch occurs here.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import sys
import time
import zipfile

import modern_runtime_donor as donor
import modern_validation as validation
import baseline_reopen


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def load_candidate(root):
    sys.path[:0] = [str(root / item) for item in
                   ('armport/app', 'armport/scripts', 'tools/android/interactive', 'android/guest')]
    interactive = importlib.import_module('interactive_host')
    stage = importlib.import_module('stage_app_assets')
    pipeline = importlib.import_module('server_pipeline')
    progress = importlib.import_module('game_map_progress')
    for module in (interactive, stage, pipeline, progress):
        validation.require(Path(module.__file__).resolve().is_relative_to(root), 'Candidate module came from another checkout')
    return interactive, stage, pipeline, progress


def source_identity():
    result = {'supporting_scripts': {}}
    directory = Path(__file__).resolve().parent
    for name in ('modern_runtime_host.py', 'modern_validation.py', 'modern_runtime_donor.py', 'baseline_reopen.py'):
        result['supporting_scripts'][name] = donor.pin(directory / name)
    try:
        result['supporting_test_commit'] = subprocess.check_output(
            ['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        result['supporting_test_commit'] = None
    return result


def runtime_manifest(assets, native):
    runtime = json.loads((assets / 'runtime-manifest.json').read_text())
    client = json.loads((assets / 'client-manifest.json').read_text())
    binding = json.loads((assets / 'armport-server-metrics-binding.json').read_text())
    runtime['armport_server_metrics_build'] = json.loads(binding['build_manifest_utf8'])
    with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
        package = json.loads(archive.read('client-package.json'))
    runtime['armport_server_native_closure'] = {key: package[key] for key in ('source_commit', 'data_commit', 'files')}
    world = json.loads((assets / 'atlas-world-supplement-manifest.json').read_text())
    runtime['armport_world_manifest'] = world
    runtime['armport_world_contract'] = dict(scope=world['scope'],
        manifest_pin=runtime['files']['atlas-world-supplement-manifest.json'],
        archive_pin=runtime['files']['atlas-world-supplement.zip'], file_count=world['file_count'],
        payload_bytes=world['payload_bytes'], files_sha256=hashlib.sha256(native.canonical(world['files'])).hexdigest())
    return runtime, client


def fetch_payloads(root, cache, apk):
    # These established source functions download and verify original asset
    # bytes only. Their preparation/native-boundary claims are not imported.
    sys.path.insert(0, str(root / 'tools/android/interactive'))
    leaf = importlib.import_module('qualify_runtime_asset_preflight')
    full = importlib.import_module('qualify_full_startup_preflight')
    payloads = leaf.ensure_assets(cache)
    full.extra_inputs(payloads)
    pack = donor.inspect_donor(apk)['asset-pack-manifest.json']
    for name, expected in pack['files'].items():
        validation.require(donor.pin(payloads / Path(name).name) == expected, 'Incomplete original asset hydration: ' + name)
    # All extracted leaves were rehashed. Remove only authenticated duplicate
    # public transport ZIPs, retaining the complete verified payload cache.
    for label, expected in {**leaf.VOLUMES, 'Audio': full.AUDIO_VOLUME}.items():
        archive = Path(cache) / ('COH-Assets-1.0.0-' + label + '.zip')
        if archive.exists():
            validation.require(donor.pin(archive) == expected, 'Transport archive changed before removal')
            archive.unlink()
    return payloads


def run_character_pair(interactive, command, work, evidence, proot, runtime, client, first, second):
    """Retain each guest's existing bound; start a fresh bound for reopen."""
    character, reopen = interactive.character, interactive.reopen
    creation_deadline = time.monotonic() + character.OVERALL_SECONDS
    created = interactive.run_session(command, work, evidence / 'creation', proot,
                                      first, runtime, client, creation_deadline)
    before = reopen.persistent_profile_identity(work)
    reopen.archive_completed_reports(work / 'state', first)
    reopen.reset_session_requests(work / 'state')
    next_command = reopen.reopen_command(command, first, second)
    validation.require('--zoning' not in next_command and '--startup-only' not in next_command,
                       'Unexpected preselected reopen route')
    next_command.append('--zoning')
    # OVERALL_SECONDS is also passed to each unmodified guest as its own
    # timeout. A slow first run cannot consume the second guest's allowance.
    reopen_deadline = time.monotonic() + character.OVERALL_SECONDS
    reopened = interactive.run_session(next_command, work, evidence / 'reopen', proot,
                                       second, runtime, client, reopen_deadline, reopening=True)
    after = reopen.persistent_profile_identity(work)
    reopen.validate_continuity(created, reopened, before, after)
    return created, reopened, {'per_session_seconds': character.OVERALL_SECONDS,
        'scope': 'independent_bounded_guest_creation_and_zoning_reopen',
        'creation_deadline_monotonic': creation_deadline,
        'reopen_deadline_monotonic': reopen_deadline}


def execute(args):
    root = validation.verify_candidate_checkout(args.candidate_root, args.candidate_commit)
    interactive, staging, pipeline, progress = load_candidate(root)
    native = pipeline.native
    baseline = native.baseline_root(args.baseline_root)
    validation.require(platform.machine().lower() in ('aarch64', 'arm64'), 'Native ARM64 runner required')
    validation.require(shutil.which('tesseract') is not None, 'Existing RFB driver requires tesseract')
    pipeline.check_build_run(json.loads(args.native_run_json.read_text()), repository_commit=args.candidate_commit,
        server_run_id=args.native_build_run_id, client_run_id=args.native_build_run_id, data_run_id=args.native_build_run_id)
    validation.verify_runtime_run(json.loads(args.candidate_runtime_json.read_text()), args.candidate_commit,
                                  args.candidate_runtime_run_id)
    build, _, members = native.read_package(args.server_archive, variant=validation.VARIANT,
        repository_commit=args.candidate_commit, run_id=args.native_build_run_id, upstream_root=baseline)
    validation.require(args.server_archive.name == pipeline.PACKAGES[validation.VARIANT], 'Exact modern server artifact name required')
    validation.require(not args.work.exists() and not args.evidence.exists(), 'Fresh private work/evidence required')
    args.work.mkdir(mode=0o700, parents=True)
    args.evidence.mkdir(parents=True)
    result = {'format': 1, 'scope': 'modern_mapserver_arm64_app_creation_and_zoning_reopen',
        'repository_commit': args.candidate_commit, 'candidate_repository_commit': args.candidate_commit,
        'native_build_run_id': args.native_build_run_id, 'candidate_runtime_run_id': args.candidate_runtime_run_id,
        'server_variant': validation.VARIANT, 'modern_server': donor.pin(args.server_archive),
        'modern_mapserver': {key: build['files']['MapServer.exe'][key] for key in ('bytes', 'sha256')},
        'modern_build_manifest_sha256': hashlib.sha256(members[native.BUILD]).hexdigest(),
        'passed': False, 'modern_runtime_executed': None, 'modern_runtime_qualified': False, 'physical_device_validated': False,
        'kings_row_runtime_validated': False, 'combat_rewards_validated': False, 'apk_built': False,
        'android_surface_validated': False, 'm4_complete': False,
        'baseline_saved_data_compatibility_validated': False, **source_identity()}
    started = time.monotonic()
    projector = None
    try:
        payloads = args.payloads or fetch_payloads(root, args.asset_cache, args.apk)
        result['donor'] = donor.prepare(args.apk, payloads, args.work / 'donor-assets')
        source = args.work / 'donor-assets/runtime'
        assets = args.work / 'modern-assets'
        result['armport_client'] = staging.stage(source, args.armport, assets, args.candidate_commit,
            server_archive=args.server_archive, server_variant=validation.VARIANT,
            server_run_id=args.native_build_run_id, upstream_root=baseline)
        validation.require(result['armport_client']['client_run_id'] == args.native_build_run_id
                and result['armport_client']['data_run_id'] == args.native_build_run_id,
                'ARM64 client/data do not belong to the exact native build')
        runtime, client = runtime_manifest(assets, native)
        validation.require(runtime['repository_commit'] == args.candidate_commit,
                           'Staging replaced candidate source identity with test source')
        task_pin = donor.pin(source / 'task-gate.json')
        validation.require(donor.pin(assets / 'task-gate.json') == task_pin == runtime['files']['task-gate.json'],
                           'Modern task gate payload changed during staging')
        # stage() has authenticated and copied the full source inventory.
        # Remove this fresh duplicate source copy; original APK and external
        # payloads remain recoverable and the actual runtime is independent.
        validation.require(source.parent == args.work / 'donor-assets' and source.is_dir() and not source.is_symlink(),
                           'Unexpected disposable staging source')
        shutil.rmtree(source)
        result['donor']['source_runtime_copies_removed_after_verified_staging'] = True
        documents = validation.contracts(assets, runtime)
        projector = validation.ModernProjector(interactive, runtime, client, documents, progress)
        interactive.legacy_report = projector.project
        character, reopen = interactive.character, interactive.reopen
        data = character.host.import_game_data(args.work / 'donor-assets/atlas',
            Path(result['donor']['reference_archive']), args.work, args.evidence)
        first, second = secrets.token_hex(16), secrets.token_hex(16)
        validation.require(first != second, 'Distinct session identities required')
        command, _ = character.make_command(args.work, assets, args.proot, first, data, 900)
        command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_ARCH=arm64')
        command.insert(command.index('/usr/bin/python3'), 'COH_CLIENT_GRAPHICS_PROFILE=standard')
        created, reopened, result['host_session_time_bounds'] = run_character_pair(
            interactive, command, args.work, args.evidence, args.proot, runtime, client, first, second)
        validation.require(set(projector.records) == {first, second}, 'Modern host lacks both admitted native sessions')
        # Recheck the same exact candidate source after execution. Supporting
        # scripts cannot accidentally cause production-source drift unnoticed.
        validation.verify_candidate_checkout(root, args.candidate_commit)
        validation.require(donor.pin(assets / 'task-gate.json') == task_pin, 'Modern runtime modified the task gate payload')
        result.update(modern_runtime_executed=True, modern_runtime_qualified=True, same_persistent_profile=True,
            same_character_id=True, creation_session_id=first, reopen_session_id=second,
            modern_sessions={'creation': projector.records[first], 'reopen': projector.records[second]},
            map_ids_executed=[1], normal_reopen_route='explicit_zoning', task_gate_payload_preserved=True)
        result['baseline_compatibility'] = baseline_reopen.run(
            interactive, command, args.work, args.evidence, args.proot, runtime, client, progress,
            projector, reopened, second, assets, args.apk, native)
        validation.verify_candidate_checkout(root, args.candidate_commit)
        validation.require(donor.pin(assets / 'task-gate.json') == task_pin, 'Baseline test modified task gate payload')
        result.update(passed=True, baseline_saved_data_compatibility_validated=True)
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        if projector is not None and projector.records:
            result['modern_runtime_executed'] = True
            result['admitted_session_ids'] = sorted(projector.records)
        elif not any((args.evidence / name).exists() for name in ('creation', 'reopen')):
            result['modern_runtime_executed'] = False
        result['guest_failures'] = {name: interactive.guest_failure_summary(args.evidence / name)
            for name in ('creation', 'reopen', 'baseline-reopen') if (args.evidence / name).exists()}
        (args.evidence / 'modern-runtime-report.json').write_bytes(encoded(result))
        print('::notice title=Modern MapServer runtime result::' + json.dumps({key: result.get(key)
            for key in ('passed', 'modern_runtime_executed', 'elapsed_seconds', 'error')}, separators=(',', ':')))
    return 0 if result['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate-root', 'baseline-root', 'apk', 'armport', 'server-archive',
                 'native-run-json', 'candidate-runtime-json', 'proot', 'work', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--candidate-commit', required=True)
    parser.add_argument('--native-build-run-id', type=int, required=True)
    parser.add_argument('--candidate-runtime-run-id', type=int, required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--payloads', type=Path)
    inputs.add_argument('--asset-cache', type=Path)
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path): setattr(args, name, value.resolve())
    try:
        return execute(args)
    except Exception as error:
        # Failure before fresh evidence creation is still explicit in CI logs.
        print(json.dumps({'passed': False, 'modern_runtime_executed': False,
                          'preflight_error': {'type': type(error).__name__, 'message': str(error)}}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

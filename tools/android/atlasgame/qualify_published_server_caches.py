#!/usr/bin/env python3
"""Read-only native qualification of the exact already-published 0.12.1 caches.

This isolated hosted run seeds the public cache bytes into fresh donor inputs.
It does not generate a donor, rebuild Android, or modify a published artifact.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('published_cache_native_observer', Path(__file__).with_name('prepare_server_caches.py'))
observer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(observer)
package = observer.package
require, pin = package.require, package.file_pin
PUBLISHED_APK = {'bytes': 625055087, 'sha256': 'fee8880a53916e4ff746d67c8a6ab22f3f0cf2ab7779198cef59035ef4d6bf29'}
PUBLISHED_CACHE_ARCHIVE = {'bytes': 29825263, 'sha256': '7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17'}
PUBLISHED_CACHE_COMMIT = '1fcabfa28f1f32a8c78de2cac496d6647fd376a9'
ARCHIVE = 'published-server-caches.zip'
REPORT = 'published-cache-qualification.json'
QUALIFICATION_SOURCES = ('tools/android/atlasgame/qualify_published_server_caches.py', *observer.GENERATOR_SOURCES)


def extract_published_caches(apk, destination):
    """Copy the exact public ZIP verbatim; never construct another cache ZIP."""
    require(pin(apk) == PUBLISHED_APK, 'Exact public 0.12.1 APK differs')
    destination = Path(destination)
    require(destination.is_dir() and not (destination / ARCHIVE).exists(), 'Fresh public cache destination required')
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate public APK member')
        raw = archive.read('assets/runtime/server-caches.zip')
        require(package.pin_bytes(raw) == PUBLISHED_CACHE_ARCHIVE, 'Public embedded server cache ZIP differs')
        external = json.loads(archive.read('assets/runtime/server-cache-manifest.json'), object_pairs_hook=package.unique_object)
    (destination / ARCHIVE).write_bytes(raw)
    manifest = package.verify_archive(destination / ARCHIVE)
    require(manifest == external and manifest['repository_commit'] == PUBLISHED_CACHE_COMMIT
            and len(manifest['files']) == 93
            and sum(item['kind'] == 'Parse6' for item in manifest['files'].values()) == 90
            and sum(item['kind'] == 'MessageStore20090521' for item in manifest['files'].values()) == 3,
            'Exact complete published cache inventory differs')
    return manifest


def seed_published_caches(archive, runtime, manifest, *, fresh_host_only):
    """Seed public bytes only into this disposable, freshly imported host tree."""
    require(fresh_host_only is True, 'Published qualification never replaces device caches')
    replacement_names = {'data/server/bin/pc_rewards.bin', 'data/server/bin/powersetconversion.bin'}
    actions = {}
    with zipfile.ZipFile(archive) as source:
        for name, record in sorted(manifest['files'].items()):
            require(package.safe_cache(name), 'Unsafe public cache path')
            raw = source.read(name)
            require(package.pin_bytes(raw) == {key: record[key] for key in ('bytes', 'sha256')}, 'Public cache changed during seed')
            target = Path(runtime) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            require(not target.is_symlink(), 'Linked public host cache refused')
            if target.exists():
                info = target.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1,
                        'Nonprivate existing host cache refused')
                if pin(target) == {key: record[key] for key in ('bytes', 'sha256')}:
                    actions[name] = 'verified_existing_exact_public_bytes'
                else:
                    require(name.casefold() in replacement_names, 'Unexpected preexisting fresh host cache differs')
                    actions[name] = 'replaced_fresh_host_client_seed_with_exact_public_bytes'
                    target.chmod(0o600)
                    target.write_bytes(raw)
            else:
                target.write_bytes(raw)
                actions[name] = 'seeded_exact_public_bytes'
            target.chmod(0o600)
            os.utime(target, ns=(package.EPOCH * 10**9, package.EPOCH * 10**9))
    return actions


def observed_prefix_server_directories(trace_paths):
    """Bind the cleanup location to Wine's actual lock FD in native tracing."""
    result = set()
    for path in sorted(trace_paths):
        for line in observer.completed_trace_lines(path):
            for name in re.findall(r'<(/[^<>]*?/server-[0-9a-f]+-[0-9a-f]+/lock)>', line):
                result.add(str(Path(name).parent))
    return sorted(result)


def verify_published_qualification(directory):
    """Recompute supplemental proof from exact public bytes and raw evidence."""
    directory = Path(directory)
    require(pin(directory / ARCHIVE) == PUBLISHED_CACHE_ARCHIVE, 'Supplemental public cache bytes differ')
    manifest = package.verify_archive(directory / ARCHIVE)
    require(manifest['repository_commit'] == PUBLISHED_CACHE_COMMIT and len(manifest['files']) == 93,
            'Supplemental public cache provenance differs')
    report = observer.read_json(directory / REPORT)
    require(report.get('format') == 1 and report.get('role') == 'published_server_cache_consumption'
            and report.get('status') == 'exact_public_server_caches_consumed'
            and package.HEX40.fullmatch(str(report.get('repository_commit', '')))
            and report.get('published_apk') == PUBLISHED_APK
            and report.get('published_cache_archive') == PUBLISHED_CACHE_ARCHIVE
            and report.get('published_cache_commit') == PUBLISHED_CACHE_COMMIT
            and report.get('donor_apk') == observer.DONOR_APK
            and report.get('donor_build_report') == observer.DONOR_REPORT
            and report.get('identity') == manifest['identity']
            and report.get('no_native_cache_generation') is True
            and report.get('published_artifacts_changed') is False
            and report.get('native_client_or_server_recompiled') is False
            and report.get('android_execution_validated') is False
            and report.get('physical_startup_timing_validated') is False
            and report.get('dialog_semantics_validated') is False,
            'Supplemental public cache identity/scope differs')
    require(report.get('source_files') == {name: pin(ROOT / name) for name in QUALIFICATION_SOURCES}, 'Supplemental source pins differ')
    require(report.get('evidence_files') == observer.evidence_pins(directory), 'Supplemental native evidence bytes differ')
    require(report.get('launcher') == pin(directory / 'evidence/server-cache-launcher.exe'), 'Supplemental launcher bytes differ')
    evidence = directory / 'evidence/consumption'
    invocation = observer.read_json(evidence / 'invocation.json')
    phase = observer.read_json(evidence / 'phase-receipt.json')
    require(invocation.get('stage') == 'consumption' and invocation.get('identity') == manifest['identity']
            and invocation.get('timezone') == 'UTC' and invocation.get('wine_debug') == '-all', 'Supplemental invocation differs')
    initialized = directory / 'evidence/prefix-initialization'
    initialization = observer.read_json(initialized / 'phase-receipt.json')
    init_cleanup = observer.read_json(initialized / 'wine-helpers-stop.json')
    require(initialization == {'context': 'owned_prefix_initialization_before_native_launch', 'wineboot_exit_code': 0, 'mapserver_launched': False}
            and type(initialization.get('wineboot_exit_code')) is int
            and init_cleanup.get('format') == 1 and type(init_cleanup.get('kill_exit_code')) is int and init_cleanup['kill_exit_code'] in (0, 1)
            and type(init_cleanup.get('wait_exit_code')) is int and init_cleanup['wait_exit_code'] == 0
            and init_cleanup.get('status') == 'prefix_server_lock_unheld'
            and init_cleanup.get('prefix') == invocation.get('wine_prefix')
            and init_cleanup.get('normal_launcher_exit_observed_first') is False
            and (initialized / 'wine-helpers-stop.log').read_bytes() == b'',
            'Owned Wine initialization was not quiescent before native tracing')
    identifiers = report['identifier_snapshots']
    require(identifiers['before'] == identifiers['after'] == manifest['identity']['identifier_files'], 'Public cache identifiers changed')
    require(type(phase.get('launcher_exit_code')) is int, 'Supplemental launcher exit code is not an integer')
    recomputed = observer.phase_receipt((evidence / 'stdout.log').read_bytes(), (evidence / 'stderr.log').read_bytes(),
                                       'consumption', invocation['session_id'], phase['launcher_exit_code'], True)
    require(all(phase.get(key) == value for key, value in recomputed.items()), 'Supplemental native completion/error proof differs')
    cleanup = observer.read_json(evidence / 'wine-helpers-stop.json')
    prefix = invocation.get('wine_prefix')
    actual_directories = observed_prefix_server_directories(evidence.glob('trace.*'))
    require(isinstance(prefix, str) and Path(prefix).is_absolute()
            and cleanup.get('format') == 1 and type(cleanup.get('kill_exit_code')) is int and cleanup['kill_exit_code'] in (0, 1)
            and type(cleanup.get('wait_exit_code')) is int and cleanup['wait_exit_code'] == 0
            and cleanup.get('normal_launcher_exit_observed_first') is True and cleanup.get('prefix') == prefix
            and cleanup.get('status') == 'prefix_server_lock_unheld'
            and init_cleanup.get('server_directory') == cleanup.get('server_directory')
            and actual_directories == [cleanup.get('server_directory')]
            and (evidence / 'wine-helpers-stop.log').read_bytes() == b'',
            'Actual traced Wine prefix lock was not proved quiescent')
    require(report['noncache_snapshots']['before'] == report['noncache_snapshots']['after'], 'Public cache consumption changed noncache data')
    files = manifest['files']
    before, after = report['cache_snapshots']['before'], report['cache_snapshots']['after']
    require(before == after and {name: {key: value[key] for key in ('bytes', 'sha256')} for name, value in before.items()}
            == {name: {key: value[key] for key in ('bytes', 'sha256')} for name, value in files.items()}
            and all(value.get('mtime_ns') == package.EPOCH * 10**9 for value in before.values()),
            'Public cache bytes or shipped dates changed')
    sources = observer.archive_source_paths(directory / ARCHIVE, files)
    require(report.get('source_paths') == sources, 'Supplemental dependency scope differs from exact public ZIP')
    trace = observer.trace_receipt(evidence.glob('trace.*'), invocation['runtime_host_path'], files, sources, manifest['identity']['identifier_files'])
    require(trace == observer.read_json(evidence / 'trace-receipt.json') and not trace['source_content_reads']
            and not trace['cache_writes'] and all(trace['cache_content_reads'].values()), 'Public caches missed, rebuilt or read definition sources')
    consumption = {**phase, 'cache_files_unchanged': True,
                   **{key: trace[key] for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')},
                   'trace_receipt_sha256': hashlib.sha256(package.canonical(trace)).hexdigest()}
    require(report.get('native_consumption') == consumption, 'Supplemental consumption claim differs from raw proof')
    require(report.get('observed_prefix_server_directories') == actual_directories, 'Supplemental actual Wine directory claim differs')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'donor-build-report', 'asset-archive', 'published-apk', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--wine', default='wine')
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    args = parser.parse_args()
    args.work, args.output = args.work.resolve(), args.output.resolve()
    require(package.HEX40.fullmatch(args.repository_commit) and 30 <= args.timeout_seconds <= 3600, 'Invalid commit/timeout')
    require(not args.work.exists() and not args.output.exists(), 'Fresh supplemental host work/output required')
    args.work.mkdir(parents=True)
    args.output.mkdir(parents=True)
    (args.output / 'evidence').mkdir()
    source_files = {name: pin(ROOT / name) for name in QUALIFICATION_SOURCES}
    manifest = extract_published_caches(args.published_apk.resolve(), args.output)
    caches, prerequisites, host, world, avatar = observer.generation_modules()
    imports, assets = observer.extract_donor(args.donor_apk.resolve(), args.donor_build_report.resolve(), args.work / 'donor', host)
    data = host.import_game_data(imports, args.asset_archive.resolve(), args.work, args.output / 'evidence')
    runtime = data.parent
    observer.extract_tar(assets / 'game-package.tar.gz', runtime, 'game-package.json')
    observer.extract_tar(assets / 'dbserver-schema.tar.gz', runtime, 'schema-manifest.json', package.compatibility_identity()['schema_manifest_sha256'])
    observer.seed_zip(assets / 'client-caches.zip', runtime, caches.verify_cache_archive(assets / 'client-caches.zip'))
    observer.seed_zip(assets / 'client-prerequisites.zip', runtime, prerequisites.verify_archive(assets / 'client-prerequisites.zip'))
    context = type('HostContext', (), {'check': lambda self: None})()
    world.install(runtime, assets, context)
    avatar.install(runtime, assets, context)
    observer.normalize_data(data)
    identity = package.build_expected_identity(data, runtime / 'MapServer.exe')
    package.verify_archive(args.output / ARCHIVE, identity)
    seed_actions = seed_published_caches(args.output / ARCHIVE, runtime, manifest, fresh_host_only=True)
    observer.write_json(args.output / 'evidence/public-cache-seed.json', seed_actions)
    observer.write_json(args.output / 'evidence/native-runtime-layout.json', observer.prepare_runtime_layout(runtime))
    launcher = args.work / 'server-cache-launcher.exe'
    with (args.output / 'evidence/launcher-build.log').open('wb') as log:
        subprocess.run(['i686-w64-mingw32-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static-libgcc',
                        str(ROOT / 'android/native/server-cache-launcher.c'), '-o', str(launcher)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    shutil.copyfile(launcher, args.output / 'evidence/server-cache-launcher.exe')
    require(not (runtime / 'piggs/texts.pigg').exists(), 'Supplemental native error observation requires development mode')
    environment = dict(os.environ, WINEARCH='win32', WINEPREFIX=str(args.work / 'wine-prefix'), WINEDEBUG='-all',
                       WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8')
    with (args.output / 'evidence/wine-initialization.log').open('wb') as log:
        subprocess.run([args.wine, 'wineboot', '--init'], env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    # Stop and prove the initialized prefix idle before strace. Otherwise an
    # already-running server outside strace could hide the actual lock FD.
    initialized = args.output / 'evidence/prefix-initialization'
    initialized.mkdir()
    observer.stop_owned_prefix(environment, initialized, normal_launcher_exit_observed_first=False)
    observer.write_json(initialized / 'phase-receipt.json', {'context': 'owned_prefix_initialization_before_native_launch',
                        'wineboot_exit_code': 0, 'mapserver_launched': False})
    identifiers = {'before': package.identifier_snapshot(data)}
    noncache = {'before': observer.data_snapshot(data)}
    files = manifest['files']
    snapshots = {'before': observer.cache_state(runtime, files)}
    sources = observer.archive_source_paths(args.output / ARCHIVE, files)
    phase = observer.run_phase(args, runtime, launcher, environment, args.output, 'consumption', identity, trace=True)
    identifiers['after'] = package.identifier_snapshot(data)
    noncache['after'] = observer.data_snapshot(data)
    snapshots['after'] = observer.cache_state(runtime, files)
    evidence = args.output / 'evidence/consumption'
    trace = observer.trace_receipt(evidence.glob('trace.*'), runtime, files, sources, identity['identifier_files'])
    observer.write_json(evidence / 'trace-receipt.json', trace)
    consumption = {**phase, 'cache_files_unchanged': snapshots['before'] == snapshots['after'],
                   **{key: trace[key] for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')},
                   'trace_receipt_sha256': hashlib.sha256(package.canonical(trace)).hexdigest()}
    report = {'format': 1, 'role': 'published_server_cache_consumption', 'status': 'exact_public_server_caches_consumed',
              'repository_commit': args.repository_commit, 'published_apk': PUBLISHED_APK, 'published_cache_archive': PUBLISHED_CACHE_ARCHIVE,
              'published_cache_commit': PUBLISHED_CACHE_COMMIT, 'donor_apk': observer.DONOR_APK, 'donor_build_report': observer.DONOR_REPORT,
              'identity': identity, 'source_files': source_files, 'evidence_files': observer.evidence_pins(args.output),
              'launcher': pin(launcher), 'native_consumption': consumption, 'identifier_snapshots': identifiers,
              'noncache_snapshots': noncache, 'cache_snapshots': snapshots, 'source_paths': sources,
              'observed_prefix_server_directories': observed_prefix_server_directories(evidence.glob('trace.*')),
              'no_native_cache_generation': True, 'published_artifacts_changed': False, 'native_client_or_server_recompiled': False,
              'android_execution_validated': False, 'physical_startup_timing_validated': False, 'dialog_semantics_validated': False}
    observer.write_json(args.output / REPORT, report)
    verify_published_qualification(args.output)
    print(json.dumps({'status': report['status'], 'files': len(files), 'public_cache': PUBLISHED_CACHE_ARCHIVE}))


if __name__ == '__main__':
    main()

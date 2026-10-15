#!/usr/bin/env python3
"""Repair 0.11.5 package extraction, reusing its exact Game/MapServer build.

The exact public 0.11.4 APK remains the preserved runtime/data donor. The
public 0.11.5 APK independently binds the reused native bytes and reproduces
the rejected archive before any new APK can be signed or published.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'android/guest'), str(ROOT/'tools')]
import build_responsiveness_apk as shared
import local_login_server as guest_login

# Load independently so historical 0.11.5 package tests retain their defaults.
CORE = shared.module('coh_reopen_repair_package_core', Path(__file__).with_name('build_responsiveness_apk.py'))
PRIOR_APK_NAME = 'COH-Atlas-Gameplay-0.11.5.apk'
PRIOR_APK = {'bytes': 595194816, 'sha256': '5ba95d45bfbe0a2cda74bb632b80d1499058f5c8b40c48d9d422a9304cdb9941'}
PRIOR_URL = 'https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.5/'+PRIOR_APK_NAME
NATIVE_RUN_ID = 37048610759
NATIVE_COMMIT = '0ddd27dfaddf9ac53a6a65548c8199bced767fbe'
VERSION_NAME, VERSION_CODE = '0.11.6', 12
APK_NAME = 'COH-Atlas-Gameplay-0.11.6.apk'
REPORT_NAME = 'reopen-repair-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.11.6-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.11.6'
WORKFLOW = '.github/workflows/android-reopen-repair.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_reopen_repair.py'
JAVA_CHANGES = CORE.JAVA_CHANGES | {'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java'}
QUALIFICATION_SCOPE = 'canonical_server_archive_and_bounded_android_extraction_repair'
CHECKS = (*CORE.CHECKS, 'real_guest_archive_extraction_verified', 'bounded_android_tar_buffer_verified')
SOURCE_FILES = CORE.SOURCE_FILES | frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_reopen_repair_apk.py',
    'tools/android/interactive/test_reopen_repair_package.py',
    'tools/android/interactive/test_process_exit_history.py',
    'tools/android/test_archive.py',
    'tools/android/java/io/github/russianranger/cohdiagnostic/ExtractRuntimeHost.java',
    'docs/'+NOTES_NAME, *JAVA_CHANGES))
for name in ('VERSION_NAME', 'VERSION_CODE', 'APK_NAME', 'REPORT_NAME', 'NOTES_NAME', 'NOTES',
             'RELEASE_TAG', 'WORKFLOW', 'QUALIFICATION_SCRIPT', 'JAVA_CHANGES',
             'QUALIFICATION_SCOPE', 'CHECKS', 'SOURCE_FILES'):
    setattr(CORE, name, globals()[name])
CORE.RELEASE_NAME = 'COH Atlas Gameplay 0.11.6 — runtime refresh and reopen package repair'
CORE.CLIENT_OR_SERVER_RECOMPILED = False
CORE.BUILD_SCOPE = ('Repair canonical server archive metadata and bounded Android tar extraction; '
    'reuse exact public 0.11.5 Game/MapServer binaries and its readiness, texture and graphics changes; '
    'retain public 0.11.4 DbServer, data, avatar, prepared caches, signer and software renderer; '
    'physical refresh/reopen validation pending')


def __getattr__(name):
    return getattr(CORE, name)


def download_prior(args):
    require = CORE.require
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh prior APK download required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(PRIOR_URL, timeout=120) as source, args.output.open('xb') as target:
        total = 0
        while chunk := source.read(1024*1024):
            total += len(chunk)
            require(total <= PRIOR_APK['bytes'], 'Oversized prior APK download')
            target.write(chunk)
    CORE.builder().checked_file(args.output, PRIOR_APK)


def reproduce_prior_archive_failure(apk):
    """Use the actual shipped guest extractor, never tarfile alone, for rejection."""
    CORE.builder().checked_file(apk, PRIOR_APK)
    with tempfile.TemporaryDirectory(prefix='coh-reopen-prior-') as temporary:
        folder = Path(temporary)
        with zipfile.ZipFile(apk) as archive:
            raw = archive.read('assets/runtime/game-package.tar.gz')
        package = folder/'game-package.tar.gz'; package.write_bytes(raw)
        with tarfile.open(package, 'r:gz') as archive:
            first = archive.getmembers()[0]
            metadata = {'name': first.name, 'mtime': first.mtime, 'mode': first.mode,
                'uid': first.uid, 'gid': first.gid, 'pax_headers': first.pax_headers}
        destination = folder/'extracted'
        try:
            guest_login.extract_regular(package, destination)
        except guest_login.base.DiagnosticError as error:
            message = str(error)
        else:
            raise ValueError('Public 0.11.5 game archive unexpectedly passes the actual guest extractor')
        CORE.require(message == 'Server payload archive metadata differs'
                     and metadata['mtime'] == 1767225600 and not any(destination.iterdir()),
                     'Public 0.11.5 rejection no longer matches the reported immediate reopen failure')
        return {'format': 1, 'status': 'reproduced', 'apk': PRIOR_APK,
            'archive': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
            'actual_guest_extractor': 'local_login_server.extract_regular',
            'error': message, 'first_member_metadata': metadata, 'extracted_files': 0}


def native_bytes(apk):
    """Read exact executable bytes while leaving strict extraction to preflight."""
    with zipfile.ZipFile(apk) as archive:
        receipt = json.loads(archive.read('assets/runtime/native-responsiveness.json'))
        CORE.native_contract.validate_receipt(receipt)
        with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client:
            city = client.read('CityOfHeroes.exe')
        with tarfile.open(fileobj=io.BytesIO(archive.read('assets/runtime/game-package.tar.gz')), mode='r:gz') as game:
            mapserver = game.extractfile('MapServer.exe').read()
    pins = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in (('CityOfHeroes.exe', city), ('MapServer.exe', mapserver))}
    for name, pin in pins.items():
        CORE.require(pin == {'bytes': receipt['files'][name]['size'], 'sha256': receipt['files'][name]['sha256']},
                     'Actual public native executable differs from its receipt')
    provenance = receipt['build_provenance']
    CORE.require(provenance['native_build_repository_commit'] == NATIVE_COMMIT
                 and provenance['run_url'] == 'https://github.com/Russianranger/coh-android/actions/runs/'+str(NATIVE_RUN_ID),
                 'Reused native build provenance differs from the exact public 0.11.5 build')
    return pins


def verify_native_reuse(prior_apk, *, current_apk=None, native_directory=None):
    CORE.builder().checked_file(prior_apk, PRIOR_APK)
    pins = native_bytes(prior_apk)
    if native_directory is not None:
        build = CORE.native_package.validate_package(native_directory, NATIVE_COMMIT)
        CORE.require(build['run_url'] == 'https://github.com/Russianranger/coh-android/actions/runs/'+str(NATIVE_RUN_ID),
                     'A different native build cannot substitute for the retained 0.11.5 build')
        for name, pin in pins.items():
            CORE.builder().checked_file(native_directory/name, pin)
    if current_apk is not None:
        CORE.require(native_bytes(current_apk) == pins, 'Repair APK changed reused Game or MapServer bytes')
    CORE.require(current_apk is not None or native_directory is not None, 'Native reuse needs actual input or output bytes')
    return {'run_id': NATIVE_RUN_ID, 'repository_commit': NATIVE_COMMIT,
            'client_or_server_recompiled_this_build': False, 'files': pins}


def verify_apk_server_archives(apk):
    return CORE.verify_apk_server_archives(apk)


def build(args):
    CORE.require(args.native_commit == NATIVE_COMMIT, 'Repair requires the already published 0.11.5 native build')
    reproduction = reproduce_prior_archive_failure(args.prior_apk)
    qualification = CORE.read_json(args.qualification)
    CORE.require(qualification.get('prior_archive_failure') == reproduction,
                 'Focused qualification did not reproduce the exact public 0.11.5 archive rejection')
    reused = verify_native_reuse(args.prior_apk, native_directory=args.native_package)
    # The shared builder now extracts all three server archives with the actual
    # guest consumer after packaging, before invoking APK signing.
    CORE.build(args)
    report_path = args.output.parent/REPORT_NAME
    report = CORE.read_json(report_path)
    consumed = verify_apk_server_archives(args.output)
    CORE.require(verify_native_reuse(args.prior_apk, current_apk=args.output) == reused,
                 'Packaged native reuse differs from verified build input')
    report['reopen_repair'] = {'prior_archive_failure': reproduction,
                             'native_build_reused': reused, 'actual_guest_archive_extraction': consumed}
    report['client_or_server_recompiled_this_build'] = False
    report_path.write_text(json.dumps(report, indent=2)+'\n')


def publish(args):
    report = CORE.read_json(args.build_report)
    expected = {'prior_archive_failure': reproduce_prior_archive_failure(args.prior_apk),
        'native_build_reused': verify_native_reuse(args.prior_apk, current_apk=args.apk),
        'actual_guest_archive_extraction': verify_apk_server_archives(args.apk)}
    CORE.require(report.get('reopen_repair') == expected and report.get('client_or_server_recompiled_this_build') is False,
                 'Publication lacks the independently verified extraction repair and exact native reuse')
    CORE.publish(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('download-donor', 'download-prior'):
        get = commands.add_parser(command); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'prior-apk', 'qualification', 'native-package', 'launcher',
                 'android-jar', 'build-tools', 'keystore', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit')
    create.add_argument('--native-commit', required=True)
    create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    release = commands.add_parser('publish')
    for name in ('apk', 'build-report', 'build-tools', 'prior-apk', 'qualification', 'donor-build-report', 'donor-apk'):
        release.add_argument('--'+name, type=Path, required=True)
    release.add_argument('--testing-notes', type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': CORE.download, 'download-prior': download_prior, 'build': build, 'publish': publish}[args.command](args)


if __name__ == '__main__': main()

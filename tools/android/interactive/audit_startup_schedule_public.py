#!/usr/bin/env python3
"""Independently audit the published 0.13.3 payloads without rebuilding it.

The frozen producer adds native manifest keys through a frozenset. JSON hashes
depend on that insertion order even when the decoded objects are equal. Adapt
only that order to the downloaded client manifest; delegate every derivative
guard to the original checker. SDK signature/version checks were performed in
CI on these exact APK bytes; this payload audit does not rerun those commands.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import zipfile

import build_startup_schedule_apk as frozen

COMMIT = 'dee916f80e9e336f374f31228535afdbe2c928ca'
PUBLIC_APK = {'bytes': 676108222, 'sha256': '2626dcabcc9d69bfd1b9ad723e9748746df77e93d565a0fb1740eeff4b516709'}
BUILD_REPORT = {'bytes': 1504652, 'sha256': 'e23644cd8d52dbd4a734c29fd3fd89364b2ff00024c6cb9a3a30721eea6df7f6'}
QUALIFICATION = {'bytes': 59119, 'sha256': 'd3f09fe50f984f7bb19c2635174d42933b3665d42a10c360ac6b2e065760bb20'}


@contextmanager
def publication_manifest_order(actual_client):
    """Preserve actual key order while leaving all values and guards intact.

    This module is a single-process command, not a concurrent build service.
    The original function is restored even when a verification fails.
    """
    frozen.require(isinstance(actual_client, dict) and isinstance(actual_client.get('files'), dict),
                   'Published client manifest files must be an object')
    allowed = frozen.HELPERS | frozen.NATIVE_ASSETS
    order = tuple(name for name in actual_client['files'] if name in allowed)
    frozen.require(set(order) == allowed, 'Published manifest is missing an authorized update')
    original = frozen.verification_manifests

    def reconstruct(donor, client, updates, commit):
        frozen.require(set(updates) == allowed, 'Manifest update boundary differs')
        ordered = {name: updates[name] for name in order}
        expected_client, expected_runtime = original(donor, client, ordered, commit)
        frozen.require(expected_client == actual_client, 'Published client manifest differs from authorized updates')
        return expected_client, expected_runtime

    frozen.verification_manifests = reconstruct
    try:
        yield
    finally:
        frozen.verification_manifests = original


def audit(args):
    base = frozen.builder()
    base.checked_file(args.apk, PUBLIC_APK)
    base.checked_file(args.build_report, BUILD_REPORT)
    base.checked_file(args.qualification, QUALIFICATION)
    donor = frozen.validate_donor(args.donor_apk, args.donor_build_report)
    java = frozen.current_sources(donor)
    qualification = frozen.validate_qualification(frozen.read_json(args.qualification), COMMIT)
    native = frozen.validate_native(args.native_directory, COMMIT, args.donor_apk)
    report = frozen.read_json(args.build_report)
    frozen.require(report.get('repository_commit') == COMMIT and report.get('apk') == frozen.APK_NAME
        and {name: report.get(name) for name in PUBLIC_APK} == PUBLIC_APK
        and report.get('version_name') == frozen.VERSION_NAME and report.get('version_code') == frozen.VERSION_CODE
        and report.get('signer_certificate_sha256') == frozen.SIGNER
        and report.get('qualification') == qualification and report.get('native_dbserver') == native
        and qualification.get('native_dbserver') == native and report.get('java_sources') == java
        and all(report.get(name) is True for name in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified')),
        'Pinned CI publication report differs')
    with zipfile.ZipFile(args.apk) as archive:
        frozen.require(archive.testzip() is None, 'Public APK ZIP CRC check failed')
        client_raw = archive.read('assets/runtime/client-manifest.json')
        client = json.loads(client_raw)
        runtime = json.loads(archive.read('assets/runtime/runtime-manifest.json'))
    client_pin = {'bytes': len(client_raw), 'sha256': hashlib.sha256(client_raw).hexdigest()}
    frozen.require(runtime['files']['client-manifest.json'] == client_pin,
                   'Runtime pin does not match actual client manifest bytes')
    with publication_manifest_order(client):
        frozen.verify_derivative(args.apk, donor, report['payloads'], COMMIT, args.native_directory)
    frozen.require(runtime == report['runtime_manifest']
        and report['runtime_manifest_sha256'] == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'],
        'Reported runtime metadata differs from public APK')
    frozen.require(frozen.verify_apk_server_archives(args.apk) == donor['server_payload_extraction_preflight'],
                   'Public APK fails actual retained guest archive extraction')
    checksum = args.apk.with_suffix('.apk.sha256')
    frozen.require(checksum.read_text() == PUBLIC_APK['sha256']+'  '+frozen.APK_NAME+'\n',
                   'Published checksum differs')
    base.checked_file(args.apk.parent/frozen.NOTES_NAME, report['testing_notes'])
    base.checked_file(frozen.NOTES, report['testing_notes'])
    return {'format': 1, 'status': 'passed', 'repository_commit': COMMIT, 'apk': PUBLIC_APK,
        'payload_digests_verified': len(report['payloads']), 'zip_crcs_verified': True,
        'retained_Android_DEX_and_resources_verified': True,
        'actual_retained_server_archive_extraction_verified': True,
        'source_qualification_and_native_supplement_verified': True,
        'runtime_matches_build_report': True, 'client_manifest_pin': client_pin,
        'native_key_serialization_order': [name for name in client['files'] if name in frozen.NATIVE_ASSETS],
        'ordering_adapter_changes_values_or_guard_set': False,
        'signature_scope': 'CI official SDK signature/version checks bound to identical downloaded public SHA-256; no local SDK rerun',
        'physical_startup_timing_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('apk', 'build-report', 'qualification', 'donor-apk', 'donor-build-report', 'native-directory'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Public 0.13.3 payload audit passed:', result['apk']['sha256'])


if __name__ == '__main__':
    main()

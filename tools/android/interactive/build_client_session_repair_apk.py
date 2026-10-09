#!/usr/bin/env python3
"""Publish the host-only .23 session repair without rebuilding the accepted Game.

Load a private .22 builder instance: only this instance receives the new helper
scope and release metadata. Historical .22 tools, their globals and tests remain
untouched. The original .21 APK and completed .22 native artifact remain the
independently authenticated immutable byte sources.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

import build_client_render_pipeline_apk as history

_base = history.module('client_session_repair_private_builder', Path(__file__).with_name('build_client_render_pipeline_apk.py'))
ROOT, require, module, shared = _base.ROOT, _base.require, _base.module, _base.shared
REPOSITORY, BRANCH, SIGNER = _base.REPOSITORY, _base.BRANCH, _base.SIGNER
retained, engine, previous = _base.retained, _base.engine, _base.previous
VERSION_NAME, VERSION_CODE = '0.13.23', 38
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.23.apk', 'client-session-repair-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.23-testing.txt'
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.23'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-session-repair.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_session_repair.py'
QUALIFICATION_SCOPE = 'owned_guest_session_budget_and_same_Game_render_pipeline_instrumentation_isolation_retaining_public_0_13_21'
NEW_HELPERS = frozenset({'client_interactive_diagnostic.py', 'character_reopen_diagnostic.py', 'character_session_budget.py'})
HELPERS = history.HELPERS | NEW_HELPERS
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS | {'client-runtime.zip', 'client-manifest.json', 'runtime-manifest.json'})
RETAINED_PAYLOAD_COUNT = 77-len(REPLACED_PAYLOADS)
CHECKS = ('owned_session_budget_and_instrumentation_isolation_verified',
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified',
    'exact_retained_Game_android_shell_and_successful_gpu_bytes_verified')
SOURCE_FILES = history.SOURCE_FILES | frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_session_repair_apk.py',
    'tools/android/interactive/test_client_session_repair_package.py',
    'tools/android/interactive/test_client_session_repair_java.py',
    'tools/android/interactive/test_session_budget_guest.py',
    'tools/android/interactive/test_client_render_pipeline_guest.py',
    'docs/COH-PERFORMANCE-0.13.23.md', 'docs/'+NOTES_NAME,
    'docs/android-evidence/session-repair-0.13.22-thor-20261009.json',
    *('android/guest/'+name for name in NEW_HELPERS)})
REVIEWED_DONOR_SOURCE_CHANGES = history.REVIEWED_DONOR_SOURCE_CHANGES | frozenset({
    *('android/guest/'+name for name in NEW_HELPERS),
    'tools/android/interactive/test_session_budget_guest.py'})
FALSE_FLAGS = history.FALSE_FLAGS + ('native_client_recompiled', 'render_pipeline_instrumentation_enabled')
TRUE_FLAGS = tuple(name for name in history.TRUE_FLAGS if name != 'native_client_recompiled') + (
    'owned_presentation_session_deadline_repair', 'render_pipeline_instrumentation_isolation',
    'accepted_Game_bytes_retained')
RETAINED_FIELDS = history.RETAINED_FIELDS
ACTUAL_NATIVE_ANCESTRY_CHECKS = history.ACTUAL_NATIVE_ANCESTRY_CHECKS

# These pins preserve the original completed native producer identity. Never
# substitute a current publication SHA into its original manifest or proof.
for _name in ('DONOR_COMMIT', 'DONOR_RUN_ID', 'DONOR_APK_NAME', 'DONOR_REPORT_NAME',
    'DONOR_APK', 'DONOR_EVIDENCE_ID', 'DONOR_EVIDENCE', 'DONOR_EVIDENCE_ARCHIVE',
    'DONOR_EVIDENCE_NAMES', 'DONOR_GAME', 'DONOR_URL', 'NATIVE_BUILD_COMMIT',
    'NATIVE_BUILD_RUN_ID', 'NATIVE_ARTIFACT_ID', 'NATIVE_ARTIFACT',
    'NATIVE_MANIFEST_PIN', 'NATIVE_GAME', 'RETAINED_NATIVE_SOURCE_FILES'):
    globals()[_name] = getattr(history, _name)
for _name in ('VERSION_NAME', 'VERSION_CODE', 'APK_NAME', 'REPORT_NAME', 'NOTES_NAME',
    'RELEASE_TAG', 'NOTES', 'WORKFLOW', 'QUALIFICATION_SCRIPT', 'QUALIFICATION_SCOPE',
    'HELPERS', 'REPLACED_PAYLOADS', 'CHECKS', 'SOURCE_FILES',
    'REVIEWED_DONOR_SOURCE_CHANGES', 'FALSE_FLAGS', 'TRUE_FLAGS'):
    setattr(_base, _name, globals()[_name])

for _name in ('builder', 'pin', 'read_json', 'read_json_value', 'donor_link',
    'donor_evidence_members', 'validate_donor_receipt', 'current_sources',
    'validate_donor', 'native_producer', 'native_build_provenance',
    'publication_provenance', 'validate_native', 'client_manifest',
    'validate_client_package_bytes', 'replace_client_archive',
    'extract_and_repair', 'verify_derivative', 'repair_android_manifest',
    'validate_existing_release', 'bounded_download', 'authenticated_artifact_download',
    'download_donor_evidence', 'download_retained_native', 'download_public'):
    globals()[_name] = getattr(_base, _name)

_original_verification_manifests = _base.verification_manifests
_original_validate_qualification = _base.validate_qualification


def session_repair_contract():
    return {'format': 1, 'changed_guest_helpers': sorted(NEW_HELPERS),
        'session_budget_clock': 'owned_guest_presentation_monotonic',
        'launcher_deadline_can_shorten_guest_budget': True,
        'native_Game_sha256': NATIVE_GAME['sha256'],
        'native_Game_changed_from_public_0_13_22': False,
        'native_build_repeated': False,
        'render_pipeline_instrumentation_enabled': False,
        'render_pipeline_disabled_reason': 'thor_0_13_22_performance_regression_isolation',
        'render_pipeline_isolation_scope': 'character_reopen_only',
        'direct_interactive_render_pipeline_instrumentation_retained': True,
        'legacy_frame_and_renderer_attribution_retained': True,
        'worker_wake_repair_retained': True,
        'physical_fps_gain_validated': False}


def verification_manifests(donor, updates, commit, native):
    client, runtime = _original_verification_manifests(donor, updates, commit, native)
    runtime['client_render_pipeline']['native_recompiled'] = False
    runtime['client_render_pipeline']['replacement_scope'] = 'retained_CityOfHeroes.exe_and_reviewed_guest_helpers'
    runtime['client_session_repair'] = {**session_repair_contract(),
        'repository_commit': commit, 'native_build_provenance': native_build_provenance(),
        'publication_provenance': publication_provenance(commit)}
    return client, runtime


def payload_boundaries(payloads, donor):
    require(len(payloads) == 77 and set(payloads) == set(donor['payloads'])
        and {n for n in payloads if payloads[n] != donor['payloads'][n]} == REPLACED_PAYLOADS,
        'Exactly ten reviewed integration payloads and sixty-seven retained .21 payloads required')


def validate_qualification(q, commit):
    _original_validate_qualification(q, commit)
    require(type(q.get('client_session_repair')) is dict
        and shared.encoded(q['client_session_repair']) == shared.encoded(session_repair_contract()),
        'Exact .23 owned session budget and unchanged Game instrumentation isolation required')
    return q

def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor)
    require(q.get('native_client_render_pipeline') == native and q.get('java_sources') == current_sources(donor)
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('retained_native_client_renderer_attribution') == donor['native_client_renderer_attribution'],
        'Qualified native/Java/retained successful GPU inputs differ')
    password = base.signing_password_spec(args.password_env); base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .23 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-session-repair-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.client_directory, native)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/n for n in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', *donor['retained_android_resources']}, 'Generated Android inventory differs')
            for name, expected in donor['retained_android_resources'].items(): require(pin(archive.read(name)) == expected, 'Retained Android resources changed')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/n, n) for n in sorted(payloads)])
            archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, native); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit, 'runtime_repository_commit': commit,
            'retained_runtime_repository_commit': DONOR_COMMIT, 'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'signer_certificate_sha256': certificate,
            'signing_key_created': False, 'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'baseline_payloads_verified': 77, 'retained_baseline_payloads_verified': RETAINED_PAYLOAD_COUNT, 'retained_dex': donor['recompiled_dex'],
            'java_sources': donor['java_sources'], 'changed_java_sources': [], 'retained_java_sources_verified': 19,
            'qualification': q, 'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_client_render_pipeline': native, 'native_build_provenance': native_build_provenance(),
            'publication_provenance': publication_provenance(commit), 'retained_native_repository_commit': NATIVE_BUILD_COMMIT,
            'client_session_repair': session_repair_contract(),
            'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True), **{name: donor[name] for name in RETAINED_FIELDS}}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified session repair APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor); report = read_json(args.build_report)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and type(report.get('client_session_repair')) is dict
        and shared.encoded(report['client_session_repair']) == shared.encoded(session_repair_contract())
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('donor') == donor_link()
        and report.get('application_id') == builder().APP_ID and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE
        and report.get('abi') == 'arm64-v8a' and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == builder().file_pin(args.qualification)
        and report.get('native_client_render_pipeline') == q.get('native_client_render_pipeline') == native
        and report.get('native_build_provenance') == q.get('native_build_provenance') == native_build_provenance()
        and report.get('publication_provenance') == q.get('publication_provenance') == publication_provenance(commit)
        and report.get('retained_native_repository_commit') == NATIVE_BUILD_COMMIT
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('retained_native_client_renderer_attribution') == donor['native_client_renderer_attribution']
        and report.get('java_sources') == q.get('java_sources') == donor['java_sources'] and report.get('changed_java_sources') == []
        and report.get('retained_java_sources_verified') == 19 and report.get('retained_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and report.get('baseline_payloads_verified') == 77 and report.get('retained_baseline_payloads_verified') == RETAINED_PAYLOAD_COUNT
        and all(report.get(name) == donor[name] for name in RETAINED_FIELDS)
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified', 'payload_bytes_verified')),
        'Exact retained .21 native continuation build receipt differs')
    builder().checked_file(args.apk, report); runtime = verify_derivative(args.apk, donor, report['payloads'], commit, native)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime continuation provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); retained.verify_signature(args.apk, args.build_tools)
    builder().run(args.build_tools/'zipalign', '-c', '4', args.apk); builder(repaired=True).verify_badging(builder().run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; builder().checked_file(notes, report['testing_notes']); builder().checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def publish_release(api, report, assets, notes):
    require(tuple(p.name for p in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets'); builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    previous.old.require_current_release_head(api, report['repository_commit'])
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.23 — session movement repair and focused rendering isolation',
        'body': notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected draft release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Release upload differs')
    previous.old.require_current_release_head(api, report['repository_commit'])
    result = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(result.get('id') == release['id'] and result.get('draft') is False and result.get('prerelease') is True and result.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return result.get('html_url')


# Route inherited operations only through this private instance. In particular,
# imports of build_client_render_pipeline_apk keep their immutable .22 scope.
for _name in ('verification_manifests', 'payload_boundaries', 'validate_qualification',
    'build', 'verify_report', 'publish_release'):
    setattr(_base, _name, globals()[_name])
publish, main = _base.publish, _base.main

if __name__ == '__main__': main()

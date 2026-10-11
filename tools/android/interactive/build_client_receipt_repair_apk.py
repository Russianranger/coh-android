#!/usr/bin/env python3
"""Publish a packaging-only .29 derivative of the authenticated public .28 APK.

Only the game-package JSON receipt ordering and its two enclosing runtime
manifests change. All native binaries, guest code, DEX, GPU and Assets 1.0.0
remain byte-identical. No asset publication or native build exists in this lane.
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
import tarfile
import tempfile
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

import build_client_assets_apk as previous

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER, retained = previous.REPOSITORY, previous.BRANCH, previous.SIGNER, previous.retained
read_json, pin, typed_equal = previous.read_json, previous.pin, previous.typed_equal
bounded_download, authenticated_artifact_download = previous.bounded_download, previous.authenticated_artifact_download
DONOR_COMMIT, DONOR_RUN_ID = '96c7f44456d711d815704d20ff93c3f095ba974d', 38152969976
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.28.apk'
DONOR_APK = {'bytes': 41195620, 'sha256': '2f0f924524e6eb19d18ec94406976676501187f99a87d170fa2fc914af2e1a8a'}
DONOR_REPORT_NAME = 'client-assets-apk-build-report.json'
DONOR_BUILD = {'bytes': 5719064, 'sha256': 'e810390fdecee7f2840a5e28181a9182cc01e9fc4684233bd0144935173e21da'}
DONOR_EVIDENCE_ID = 11708145233
DONOR_EVIDENCE = {'bytes': 1329187, 'sha256': '525a9bc0792356fad08582e66bbe8676e26ccaf9ffa8851f1be0e5a7c70ae542'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.28-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, DONOR_APK_NAME+'.sha256',
    'COH-Atlas-Gameplay-0.13.28-testing.txt', 'asset-pack-manifest.json',
    'asset-pack-build-report.json', 'kings-row-beacon-lock.json'})
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.28/'+DONOR_APK_NAME
DONOR_PUBLIC_AUDIT_ID = 11708366753
DONOR_PUBLIC_AUDIT = {'bytes': 1562, 'sha256': 'd4ccb5e8d18e001e7d08472081ef2aa24b8032e86b925f729bd4053a59ee0974'}
DONOR_PUBLIC_AUDIT_RECEIPT = {'bytes': 3313, 'sha256': 'faf9f4075c7de22059d44eed1cb3d5b65e26eaa8bb861916fb20794047792650'}
ASSET_BUILD = {'bytes': 1228, 'sha256': '4eb80545f875218a6a7b087a71823de0024a37444c877412579ce53878d6c3f7'}
VERSION_NAME, VERSION_CODE = '0.13.29', 44
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.29.apk', 'client-receipt-repair-apk-build-report.json'
NOTES_NAME, RELEASE_TAG = 'COH-Atlas-Gameplay-0.13.29-testing.txt', 'coh-atlas-gameplay-v0.13.29'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-receipt-repair.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_receipt_repair.py'
QUALIFICATION_SCOPE = 'serialized_game_receipt_order_repair_retaining_exact_028_native_guest_dex_gpu_assets'
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in (
    'game-package.tar.gz', 'client-manifest.json', 'runtime-manifest.json'))
CHECKS = ('retained_regressions_and_postgresql_verified', 'serialized_game_receipts_verified',
          'exact_028_runtime_graphics_and_assets_verified')
FALSE_FLAGS = ('native_client_recompiled', 'native_mapserver_recompiled', 'native_dbserver_recompiled',
    'java_or_dex_recompiled', 'guest_helpers_changed', 'graphics_driver_changed', 'wine_or_fex_changed',
    'world_assets_changed', 'asset_reimport_required', 'native_runtime_booted', 'save_acceptance_relaxed',
    'physical_recovery_validated', 'physical_kings_row_zoning_validated', 'physical_fps_gain_validated')
TRUE_FLAGS = ('retained_android_dex_and_resources_verified', 'all_native_member_bytes_retained',
    'external_assets_1_0_0_reused', 'serialized_game_receipts_verified', 'runtime_refresh_required')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/classify_client_receipt_repair_change.py',
    'tools/android/interactive/build_client_receipt_repair_apk.py',
    'tools/android/interactive/test_client_receipt_repair_package.py',
    'tools/android/interactive/repair_game_receipt_order.py',
    'tools/android/interactive/test_game_receipt_order.py',
    'tools/android/interactive/release-client-receipt-repair-0.13.29.json', 'docs/'+NOTES_NAME})
# The .28 public audit condition was repaired after publication. Other retained
# source changes require explicit review; native and guest sources never bypass.
REVIEWED_DONOR_SOURCE_CHANGES = frozenset({'.github/workflows/android-client-assets.yml',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py'})


def builder(*, repaired=False):
    result = previous.builder()
    if repaired:
        result.VERSION_NAME, result.VERSION_CODE, result.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return result


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK,
        'build_report': DONOR_BUILD, 'build_report_artifact_id': DONOR_EVIDENCE_ID,
        'build_report_artifact_zip': DONOR_EVIDENCE,
        'public_byte_audit_artifact_id': DONOR_PUBLIC_AUDIT_ID,
        'public_byte_audit_artifact_zip': DONOR_PUBLIC_AUDIT}


def publication_provenance(commit):
    owner = os.environ.get('GITHUB_RUN_ID')
    require(owner is None or re.fullmatch('[1-9][0-9]*', owner), 'Exact publication owner required')
    return {'format': 1, 'repository_commit': commit, 'donor_repository_commit': DONOR_COMMIT,
        'run_url': 'https://github.com/'+REPOSITORY+'/actions/runs/'+owner if owner else None,
        'native_producer_relabelled': False, 'asset_release_republished': False}


def current_sources(donor):
    base = builder()
    for name, expected in donor['java_sources'].items(): base.checked_file(ROOT/name, expected)
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py'):
            base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    for name, expected in donor['qualification']['source_files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name,
                'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: base.checked_file(ROOT/name, expected)
    for name, expected in donor['native_build_provenance']['source_files'].items():
        base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    return donor['java_sources']


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); base.checked_file(receipt, DONOR_BUILD)
    donor = read_json(receipt)
    require(donor['repository_commit'] == donor['runtime_repository_commit'] == DONOR_COMMIT
        and donor['apk'] == DONOR_APK_NAME and donor['version_name'] == '0.13.28' and donor['version_code'] == 43
        and {k: donor[k] for k in ('bytes', 'sha256')} == DONOR_APK
        and donor['signer_certificate_sha256'] == SIGNER and donor['signature_verified'] is True
        and donor['external_asset_release_tag'] == 'coh-assets-v1.0.0' and donor['asset_pack_version'] == '1.0.0'
        and donor['publication_provenance']['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(DONOR_RUN_ID),
        'Exact accepted .28 donor identity required')
    require(len(donor['payloads']) == 69, 'Exact .28 payload inventory required')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads']) | set(shell) | {'AndroidManifest.xml'},
                'Donor APK inventory differs')
        for name, expected in {**donor['payloads'], **shell}.items():
            require(pin(archive.read(name)) == expected, 'Donor APK member differs: '+name)
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        require(typed_equal(json.loads(archive.read('assets/runtime/runtime-manifest.json')), donor['runtime_manifest']),
                'Donor runtime receipt differs from authenticated bytes')
    donor['_apk_path'] = Path(apk)
    evidence = Path(receipt).parent
    base.checked_file(evidence/'asset-pack-build-report.json', ASSET_BUILD)
    for name in ('asset-pack-manifest.json', 'kings-row-beacon-lock.json'):
        base.checked_file(evidence/name, donor['payloads']['assets/runtime/'+name])
    require(read_json(evidence/'asset-pack-manifest.json') == donor['external_asset_pack'], 'Retained asset descriptor differs')
    current_sources(donor)
    return donor


def payload_boundaries(payloads, donor):
    require(len(payloads) == 69 and set(payloads) == set(donor['payloads'])
        and {name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Only game-package receipt serialization and the two enclosing manifests may change')


def verification_manifests(donor, game_pin, game_manifest_pin, commit, repair_proof):
    client = copy.deepcopy(donor['_client_verification'])
    client['files']['game-package.tar.gz'] = game_pin
    runtime = copy.deepcopy(donor['runtime_manifest'])
    runtime['files']['game-package.tar.gz'] = game_pin
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    mapped = runtime['client_bundle']['local_server']['mapserver']
    mapped.update(archive_pin=game_pin, package_manifest_sha256=game_manifest_pin['sha256'])
    runtime['client_receipt_repair'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'publication_provenance': publication_provenance(commit),
        'repair': repair_proof, **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True)}
    require(runtime['external_asset_pack'] == donor['runtime_manifest']['external_asset_pack'],
            'Existing installed asset descriptor must remain exact')
    return client, runtime


def extract_and_repair(apk, donor, destination, commit):
    import repair_game_receipt_order as repair
    destination = Path(destination); destination.mkdir(parents=True)
    base = builder()
    with zipfile.ZipFile(apk) as archive:
        for name in sorted(set(donor['payloads']) | {'classes.dex'} | set(donor['retained_android_resources'])):
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024*1024)
    for name, expected in donor['payloads'].items(): base.checked_file(destination/name, expected)
    assets = destination/'assets/runtime'
    repair_proof = repair.repair_archive(assets/'game-package.tar.gz', assets/'native-responsiveness.json')
    with tarfile.open(assets/'game-package.tar.gz', 'r:gz') as archive:
        game_manifest_pin = pin(archive.extractfile('game-package.json').read())
    client, runtime = verification_manifests(donor, base.file_pin(assets/'game-package.tar.gz'),
        game_manifest_pin, commit, repair_proof)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)):
        (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in sorted(donor['payloads'])}
    payload_boundaries(payloads, donor)
    server = retained.verify_server_archives(assets)
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz'):
        require(server['archives'][name] == donor['server_payload_extraction_preflight']['archives'][name],
                'Unchanged DbServer extraction differs')
    return runtime, payloads, {'server_archives': server, 'receipt_order': repair_proof}


def validate_qualification(q, commit, donor):
    contract = module('receipt_repair_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    contract.validate_suite_inventory()
    require(q.get('format') == 1 and q.get('status') == 'passed' and q.get('scope') == QUALIFICATION_SCOPE
        and q.get('repository_commit') == q.get('runtime_repository_commit') == commit
        and q.get('donor') == donor_link() and q.get('java_sources') == current_sources(donor)
        and q.get('retained_dex') == donor['recompiled_dex']
        and q.get('external_asset_pack') == donor['external_asset_pack']
        and q.get('native_build_provenance') == donor['native_build_provenance']
        and q.get('check_suites') == contract.CHECK_SUITES and set(q.get('checks', {})) == set(CHECKS)
        and all(q['checks'][name] is True for name in CHECKS)
        and all(q.get(name) is False for name in FALSE_FLAGS)
        and all(q.get(name) is True for name in TRUE_FLAGS), 'Exact packaging-only qualification required')
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and all(row.get('status') == 'passed'
        and row.get('skipped') == 0 and type(row.get('tests_run')) is int and row['tests_run'] > 0
        for row in suites.values()) and q.get('tests_run') == sum(row['tests_run'] for row in suites.values()),
        'Every retained and current regression suite must pass without skips')
    require(q.get('postgresql_emission_fixtures') == sorted((
        'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'))
        and q.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()),
        'All seven real PostgreSQL fixtures required')
    require(set(q.get('source_files', {})) == set(contract.source_paths(donor)), 'Exact qualified source closure required')
    for name, expected in q['source_files'].items(): builder().checked_file(ROOT/name, expected)
    require(type(q.get('package_preflight')) is dict, 'Actual serialized package preflight required')
    return q


def verify_derivative(apk, donor, payloads, commit):
    base = builder(); payload_boundaries(payloads, donor); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads) | set(shell) | {'AndroidManifest.xml'},
                'Candidate APK inventory differs')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Exact .28 DEX/resources changed: '+name)
    with tempfile.TemporaryDirectory(prefix='coh-receipt-audit-') as temporary:
        runtime, expected, preflight = extract_and_repair(donor['_apk_path'], donor, Path(temporary)/'donor', commit)
        require(payloads == expected, 'Reconstructed exact donor plus receipt-order repair differs')
    require(retained.verify_apk_server_archives(apk) == preflight['server_archives'], 'Actual APK server extraction differs')
    # Verify the shipped bytes through the unmodified real guest contract, not
    # only through the host reconstruction which produced their expected hashes.
    import repair_game_receipt_order as repair
    with tempfile.TemporaryDirectory(prefix='coh-receipt-actual-') as temporary, zipfile.ZipFile(apk) as archive:
        directory = Path(temporary)
        for name in ('game-package.tar.gz', 'native-responsiveness.json'):
            (directory/name).write_bytes(archive.read('assets/runtime/'+name))
        repair.validate_archive(directory/'game-package.tar.gz', directory/'native-responsiveness.json')
    return runtime, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source); tree = ET.parse(source)
    tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME)
    tree.getroot().set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit, donor)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .29 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-receipt-build-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit)
        require(typed_equal(preflight, q['package_preflight']), 'Qualified package preflight differs')
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', *donor['retained_android_resources']}, 'Generated Android inventory differs')
            for name, expected in donor['retained_android_resources'].items(): require(pin(archive.read(name)) == expected, 'Android resources changed')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools)
        base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(),
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True,
            'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'baseline_payloads_verified': 69, 'retained_baseline_payloads_verified': 66,
            'retained_dex': donor['recompiled_dex'], 'java_sources': donor['java_sources'], 'changed_java_sources': [],
            'retained_android_resources': donor['retained_android_resources'], 'native_build_provenance': donor['native_build_provenance'],
            'client_gpu_runtime': donor['client_gpu_runtime'], 'external_asset_release_tag': donor['external_asset_release_tag'],
            'asset_pack_version': donor['asset_pack_version'], 'external_asset_pack': donor['external_asset_pack'],
            'qualification': q, 'qualification_receipt': base.file_pin(args.qualification),
            'testing_notes': base.file_pin(args.testing_notes), 'package_preflight': preflight,
            'publication_provenance': publication_provenance(commit), 'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True)}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    return report


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit, donor); report = read_json(args.build_report)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME
        and report.get('repository_commit') == report.get('runtime_repository_commit') == commit
        and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('donor') == donor_link() and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and typed_equal(report.get('qualification'), q) and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('publication_provenance') == publication_provenance(commit)
        and report.get('retained_dex') == donor['recompiled_dex'] and report.get('java_sources') == donor['java_sources']
        and report.get('changed_java_sources') == [] and report.get('retained_android_resources') == donor['retained_android_resources']
        and report.get('native_build_provenance') == donor['native_build_provenance']
        and report.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and report.get('external_asset_release_tag') == donor['external_asset_release_tag']
        and report.get('asset_pack_version') == donor['asset_pack_version']
        and report.get('external_asset_pack') == donor['external_asset_pack']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and report.get('baseline_payloads_verified') == 69 and report.get('retained_baseline_payloads_verified') == 66
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified')), 'Exact .29 packaging-only receipt differs')
    base.checked_file(args.apk, report)
    runtime, preflight = verify_derivative(args.apk, donor, report['payloads'], commit)
    require(typed_equal(report.get('runtime_manifest'), runtime) and typed_equal(report.get('package_preflight'), preflight)
        and typed_equal(q['package_preflight'], preflight)
        and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'],
        'Actual serialized repair/provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    retained.verify_signature(args.apk, args.build_tools); retained.verify_signature(args.donor_apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME
    base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def download_donor_evidence(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor evidence directory required')
    args.output.mkdir(parents=True); target = args.output/DONOR_EVIDENCE_ARCHIVE
    authenticated_artifact_download(DONOR_EVIDENCE_ID, target, DONOR_EVIDENCE)
    with zipfile.ZipFile(target) as archive:
        require(retained.archive_inventory(archive) == DONOR_EVIDENCE_NAMES, 'Exact .28 evidence inventory required')
        for entry in archive.infolist():
            require(not entry.is_dir() and 0 < entry.file_size <= 16*1024**2, 'Bounded flat evidence required')
            (args.output/entry.filename).write_bytes(archive.read(entry))
    builder().checked_file(args.output/DONOR_REPORT_NAME, DONOR_BUILD)
    audit = args.output/'published-0.13.28-public-byte-audit.zip'
    authenticated_artifact_download(DONOR_PUBLIC_AUDIT_ID, audit, DONOR_PUBLIC_AUDIT)
    with zipfile.ZipFile(audit) as archive:
        require(retained.archive_inventory(archive) == {'client-assets-public-byte-audit.json'}, 'Exact accepted public audit required')
        target = args.output/'client-assets-public-byte-audit.json'; target.write_bytes(archive.read(target.name))
    builder().checked_file(target, DONOR_PUBLIC_AUDIT_RECEIPT)
    receipt = read_json(target)
    require(receipt['status'] == 'passed' and receipt['repository_commit'] == DONOR_COMMIT
        and receipt['publication_run_id'] == DONOR_RUN_ID and receipt['public_apk_verified'] is True
        and receipt['all_public_asset_volumes_verified'] is True, 'Accepted .28 public-byte proof differs')


_publication = module('receipt_repair_private_publication', Path(previous._publication.__file__))
for _name in ('APK_NAME', 'REPORT_NAME', 'NOTES_NAME', 'RELEASE_TAG', 'DONOR_COMMIT', 'DONOR_APK_NAME', 'DONOR_APK', 'NOTES'):
    setattr(_publication, _name, globals()[_name])
validate_existing_release, download_public = _publication.validate_existing_release, _publication.download_public


def verify_asset_release(api, directory):
    directory = Path(directory); builder().checked_file(directory/'asset-pack-build-report.json', ASSET_BUILD)
    report = read_json(directory/'asset-pack-build-report.json')
    expected = dict(report['volumes'], **report['audit_files'])
    expected['asset-pack-manifest.json'] = report['asset_manifest']
    expected['asset-pack-build-report.json'] = ASSET_BUILD
    for name, value in report['volumes'].items():
        expected[name+'.sha256'] = pin((value['sha256']+'  '+name+'\n').encode())
    release = api.request('/releases/tags/coh-assets-v1.0.0')
    require(release.get('draft') is False and release.get('tag_name') == 'coh-assets-v1.0.0', 'Retained asset release unavailable')
    assets = {row['name']: row for row in release.get('assets', [])}
    require(len(assets) == len(release.get('assets', [])) and set(assets) == set(expected)
        and all(assets[name].get('size') == value['bytes'] and assets[name].get('digest') == 'sha256:'+value['sha256']
                and assets[name].get('state') == 'uploaded' for name, value in expected.items()),
        'Published Assets 1.0.0 metadata changed; this repair must not replace assets')
    return {'release_tag': 'coh-assets-v1.0.0', 'original_public_byte_audit_artifact_id': DONOR_PUBLIC_AUDIT_ID,
            'unchanged_public_asset_metadata_verified': True, 'asset_release_republished': False}


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    client = module('receipt_repair_github', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
    verify_asset_release(client, args.donor_build_report.parent)
    try: client.request('/releases/tags/'+RELEASE_TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404: raise
    else: raise ValueError('Existing .29 release is never replaced')
    previous.previous.previous.previous.previous.require_current_release_head(client, commit)
    release = client.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': commit,
        'name': 'COH Atlas Gameplay 0.13.29 — serialized receipt compatibility repair',
        'body': notes.read_text()+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True, 'Expected new APK draft')
    for path in (args.apk, checksum, notes):
        expected = builder().file_pin(path)
        uploaded = client.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}),
                                  path, method='POST', upload=True)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name
            and uploaded.get('size') == expected['bytes'] and uploaded.get('digest') == 'sha256:'+expected['sha256'],
            'Uploaded APK release member differs')
    previous.previous.previous.previous.previous.require_current_release_head(client, commit)
    result = client.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    validate_existing_release(result)
    print('Published APK only; existing Assets 1.0.0 retained:', result['html_url'])


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    for name in ('download-donor', 'download-donor-evidence'):
        command = commands.add_parser(name); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('download-public')
    command.add_argument('--output', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    command = commands.add_parser('verify-assets'); command.add_argument('--donor-build-report', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for field in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools'):
            command.add_argument('--'+field, type=Path, required=True)
        command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        command.add_argument('--testing-notes', type=Path, default=NOTES)
        if name == 'build':
            for field in ('android-jar', 'keystore', 'output'): command.add_argument('--'+field, type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
        else:
            for field in ('apk', 'build-report'): command.add_argument('--'+field, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL, args.output, DONOR_APK)
    elif args.command == 'download-donor-evidence': download_donor_evidence(args)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'verify-assets':
        api = module('receipt_repair_asset_reader', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
        print(json.dumps(verify_asset_release(api, args.donor_build_report.parent), sort_keys=True))
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Independent exact .29 audit passed:', verify_report(args, builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()

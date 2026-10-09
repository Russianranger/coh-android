#!/usr/bin/env python3
"""Compile the reviewed .24 Android setup repair over immutable public .23.

Only reviewed Java/DEX and Android manifest version values change. All 77 runtime
payloads, both runtime verification manifests, Game/probes/GPU, assets, guest
session repairs and graphical fidelity remain byte exact to the public donor.
The private .18 shell builder preserves every historical module's own globals.
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
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import build_client_sidebar_apk as shell_history
import build_client_session_repair_apk as history

_base = history.module('setup_copy_private_shell_builder', Path(__file__).with_name('build_client_sidebar_apk.py'))
ROOT, require, module, shared = history.ROOT, history.require, history.module, history.shared
REPOSITORY, BRANCH, SIGNER = history.REPOSITORY, history.BRANCH, history.SIGNER
retained, engine = history.retained, history.engine
DONOR_COMMIT, DONOR_RUN_ID = 'ac255fee7546b28a4ae06074f385d3ad73b235ad', 37965997791
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.23.apk'
DONOR_APK = {'bytes': 1560308488, 'sha256': '101780ae658f5adeaced4f5415bb856e6a65962f43175ccb9af2284777863cb2'}
DONOR_REPORT_NAME = 'client-session-repair-apk-build-report.json'
DONOR_BUILD = {'bytes': 5569193, 'sha256': '0f61fa47a6e5c11e64773379d0b93e911a5913b7e69b07bf71f7735920dd7ccb'}
DONOR_EVIDENCE_ID = 11633732976
DONOR_EVIDENCE = {'bytes': 1293028, 'sha256': '11437d41c609e076b44748f3a34c725fb0ee7a53d6a5f13abc27a1a01396c624'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.23-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, DONOR_APK_NAME+'.sha256', 'COH-Atlas-Gameplay-0.13.23-testing.txt'})
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.23/'+DONOR_APK_NAME
DONOR_GAME = history.NATIVE_GAME
NATIVE_BUILD_COMMIT, NATIVE_BUILD_RUN_ID = history.NATIVE_BUILD_COMMIT, history.NATIVE_BUILD_RUN_ID
VERSION_NAME, VERSION_CODE = '0.13.24', 39
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.24.apk', 'setup-copy-repair-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.24-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.24'
WORKFLOW = '.github/workflows/android-setup-copy-repair.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_setup_copy_repair.py'
QUALIFICATION_SCOPE = 'android_owned_setup_copy_memory_pressure_repair_retaining_public_0_13_23_runtime'
JAVA_ROOT = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
JAVA_CHANGES = frozenset({JAVA_ROOT+'ClientRuntime.java', JAVA_ROOT+'ClientService.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java'})
JAVA_ADDITIONS, REPLACED_PAYLOADS, ADDED_PAYLOADS = frozenset(), frozenset(), frozenset()
CHECKS = ('owned_setup_copy_memory_and_recovery_verified',
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified',
    'exact_android_only_payload_native_proof_and_runtime_identity_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_setup_copy_repair_apk.py',
    'tools/android/interactive/test_setup_copy_repair_package.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_setup_service.py',
    'tools/android/test_setup_memory_guard.py',
    'tools/android/interactive/test_setup_copy_memory.py',
    'tools/android/interactive/test_setup_io_memory.py',
    'docs/COH-SETUP-COPY-0.13.24.md', 'docs/'+NOTES_NAME,
    'docs/android-evidence/setup-copy-0.13.23-thor-20261009.json', *JAVA_CHANGES})
REVIEWED_DONOR_SOURCE_CHANGES = SOURCE_FILES | frozenset({'docs/HANDOFF.md',
    'docs/COH-PERFORMANCE-0.13.23.md'})
FALSE_FLAGS = ('native_dbserver_recompiled', 'native_client_recompiled', 'native_mapserver_recompiled',
    'native_client_compiled_in_current_run', 'native_client_compiled_in_current_publication_run',
    'native_runtime_booted', 'physical_gameplay_validated', 'physical_setup_memory_validated',
    'physical_performance_validated', 'physical_fps_gain_validated', 'asset_reimport_required',
    'world_assets_changed', 'prepared_cache_archive_changed', 'graphics_driver_changed',
    'wine_or_fex_changed', 'guest_helpers_changed', 'runtime_manifest_changed', 'runtime_refresh_required',
    'mesa_driver_compiled_in_current_run', 'native_vulkan_probe_compiled_in_current_run', 'wgl_probe_compiled_in_current_run')
RETAINED_RECEIPT_FIELDS = history.RETAINED_FIELDS + ('runtime_manifest', 'runtime_manifest_sha256',
    'native_client_render_pipeline', 'native_build_provenance', 'client_session_repair')
ACTUAL_NATIVE_ANCESTRY_CHECKS = history.ACTUAL_NATIVE_ANCESTRY_CHECKS
read_json, read_json_value = history.read_json, history.read_json_value
native_build_provenance, publication_provenance = history.native_build_provenance, history.publication_provenance
native_producer, pin = history.native_producer, history.pin

for _name in ('ROOT','require','module','shared','REPOSITORY','BRANCH','SIGNER','retained',
    'DONOR_COMMIT','DONOR_RUN_ID','DONOR_APK_NAME','DONOR_APK','DONOR_BUILD','DONOR_URL','DONOR_GAME',
    'VERSION_NAME','VERSION_CODE','APK_NAME','REPORT_NAME','NOTES_NAME','NOTES','RELEASE_TAG',
    'WORKFLOW','QUALIFICATION_SCRIPT','QUALIFICATION_SCOPE','JAVA_CHANGES','JAVA_ADDITIONS',
    'REPLACED_PAYLOADS','ADDED_PAYLOADS','CHECKS','SOURCE_FILES','REVIEWED_DONOR_SOURCE_CHANGES',
    'FALSE_FLAGS','RETAINED_RECEIPT_FIELDS','read_json'):
    setattr(_base, _name, globals()[_name])
for _name in ('builder','validate_retained_sources','current_java_sources','extract_retained',
    'verify_derivative','repair_android_manifest','require_current_release_head'):
    globals()[_name] = getattr(_base,_name)


def validate_retained_sources(donor):
    for name, pin in donor['qualification']['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
            and chr(92) not in name, 'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, pin)


def current_java_sources(donor, generated):
    base = builder(); sources = retained.retained.java_sources(base, generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
        if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(set(pins) == set(donor['java_sources']) and len(pins) == 19, 'Authored Java inventory must remain exact')
    changed = {name for name in pins if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Java changes exceed the reviewed setup repair shell')
    for name, pin in donor['preserved_sources'].items(): base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py'):
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    validate_retained_sources(donor)
    return sources, pins, sorted(changed)


def verify_derivative(apk, donor, payloads, dex_pin):
    base = builder(); require(payloads == donor['payloads'], 'Android wrapper changed retained runtime payloads')
    require(dex_pin != donor['retained_dex'], 'Setup repair wrapper did not recompile Java/DEX')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(retained.archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|{'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate inventory')
        for name, pin in {'classes.dex': dex_pin, **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Recompiled DEX or retained Android resources differ')
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'], 'Runtime provenance differs')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Candidate server extraction differs')
    return donor['runtime_manifest']


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK,
        'build_report': DONOR_BUILD, 'build_report_artifact_id': DONOR_EVIDENCE_ID,
        'build_report_artifact_zip': DONOR_EVIDENCE}


def donor_evidence_members(path):
    builder().checked_file(path,DONOR_EVIDENCE)
    with zipfile.ZipFile(path) as archive:
        require(retained.archive_inventory(archive)==DONOR_EVIDENCE_NAMES,'Exact authenticated .23 evidence ZIP required')
        result={}
        for entry in archive.infolist():
            require(not entry.is_dir() and 0 < entry.file_size <= 256*1024**2,'Unsafe donor evidence member')
            result[entry.filename]=pin(archive.read(entry))
    return result


def validate_donor_receipt(path):
    expected=donor_evidence_members(path.parent/DONOR_EVIDENCE_ARCHIVE)[DONOR_REPORT_NAME]
    require(expected==DONOR_BUILD,'Authenticated raw .23 report pin differs')
    builder().checked_file(path,expected); donor=read_json(path); q=donor.get('qualification',{})
    require(donor.get('format')==1 and donor.get('repository_commit')==DONOR_COMMIT
        and donor.get('runtime_repository_commit')==DONOR_COMMIT and donor.get('apk')==DONOR_APK_NAME
        and {k:donor.get(k) for k in DONOR_APK}==DONOR_APK and donor.get('version_name')=='0.13.23'
        and donor.get('version_code')==38 and donor.get('application_id')==builder().APP_ID
        and donor.get('abi')=='arm64-v8a' and donor.get('signer_certificate_sha256')==SIGNER
        and donor.get('signing_key_created') is False and len(donor.get('payloads',{}))==77
        and len(donor.get('java_sources',{}))==19 and q.get('status')=='passed'
        and q.get('repository_commit')==DONOR_COMMIT and q.get('scope')==history.QUALIFICATION_SCOPE
        and q.get('tests_run')==1557 and len(q.get('test_suites',{}))==107
        and all(s.get('status')=='passed' and s.get('skipped')==0 for s in q['test_suites'].values())
        and all(donor.get(k) is True for k in ('signature_verified','package_badging_verified',
            'binary_manifest_version_only_verified','payload_bytes_verified'))
        and donor.get('native_build_provenance')==native_build_provenance()
        and donor.get('native_client_recompiled') is False and donor.get('java_or_dex_recompiled') is False
        and history.session_repair_contract_matches(donor.get('client_session_repair')),
        'Exact authenticated public .23 donor receipt required')
    return donor


def validate_retained_native(directory,donor):
    for name,expected in history.RETAINED_NATIVE_SOURCE_FILES.items(): builder().checked_file(ROOT/name,expected)
    builder().checked_file(Path(directory)/native_producer().MANIFEST,history.NATIVE_MANIFEST_PIN)
    builder().checked_file(Path(directory)/'CityOfHeroes.exe',DONOR_GAME)
    native=native_producer().validate_package(directory,NATIVE_BUILD_COMMIT)
    require(native==donor['native_client_render_pipeline']
        and native['run_url']==native_build_provenance()['run_url'],'Original completed native Game proof required')
    return native


def validate_donor(apk,receipt,retained_client_directory):
    base=builder(); base.checked_file(apk,DONOR_APK); donor=validate_donor_receipt(receipt)
    native=validate_retained_native(retained_client_directory,donor)
    base.verify_packaged_payloads(apk,donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell={'classes.dex':donor['retained_dex'],**donor['retained_android_resources']}
        require(retained.archive_inventory(archive)==set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},'Exact .23 APK inventory required')
        for name,expected in shell.items(): require(pin(archive.read(name))==expected,'Donor Android shell differs: '+name)
        require(archive.read('assets/runtime/runtime-manifest.json')==shared.encoded(donor['runtime_manifest']),
            'Actual frozen .23 runtime manifest encoding differs')
        with archive.open('assets/runtime/client-runtime.zip') as source,tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source,target,1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                raw=client.read('client-package.json'); package=read_json_value(raw)
                shared.native_contract.client_contract(package,donor['immutable_donor_provenance']['native_responsiveness'])
                require(package['client_render_pipeline']['manifest']==native
                    and package['client_render_pipeline']['manifest_sha256']==shared.native_contract.canonical_sha(native),
                    'Actual typed .23 Game producer differs')
                members=engine.startup.startup.client_member_pins(client)
                dlls=donor['immutable_donor_provenance']['native_responsiveness']['retained_native_files']['client']
                require(len(dlls)==20 and set(members)==set(dlls)|{'CityOfHeroes.exe','client-package.json'}
                    and members['CityOfHeroes.exe']==DONOR_GAME and all(members[n]==
                        {'bytes':v['size'],'sha256':v['sha256']} for n,v in dlls.items()),'Actual retained Game/DLL closure differs')
                donor['_native_client_manifest']=package
    require(retained.verify_apk_server_archives(apk)==donor['server_payload_extraction_preflight'],'Retained server extraction differs')
    validate_retained_sources(donor); return donor


def validate_actual_native_ancestry(donor,native):
    # Reconstruct the typed previous renderer view from its authenticated raw
    # producer history; never relabel or recompile either executable.
    ancestor=copy.deepcopy(donor['_native_client_manifest'])
    ancestor.pop('client_render_pipeline')
    ancestor['files']['CityOfHeroes.exe']=copy.deepcopy(native['base_client_executable'])
    ancestor['dependency_report']=shared.dependency_report(ancestor['files'])
    inherited=dict(donor,_native_client_manifest=ancestor)
    contract=module('setup_copy_actual_ancestry',ROOT/'tools/android/interactive/test_client_render_pipeline_contract.py')
    return contract.validate_actual_native_ancestry(inherited,native)


def validate_qualification(q,commit):
    require(q.get('format')==1 and q.get('status')=='passed' and q.get('scope')==QUALIFICATION_SCOPE
        and q.get('repository_commit')==commit and q.get('runtime_repository_commit')==DONOR_COMMIT
        and q.get('donor')==donor_link() and q.get('checks')==dict.fromkeys(CHECKS,True)
        and q.get('actual_native_ancestry_validation')==ACTUAL_NATIVE_ANCESTRY_CHECKS
        and q.get('native_build_provenance')==native_build_provenance()
        and q.get('publication_provenance')==publication_provenance(commit)
        and q.get('java_or_dex_recompiled') is True and q.get('installed_runtime_identity_preserved') is True
        and q.get('native_client_package_reused') is True and q.get('retained_native_source_and_Win32_proof_verified') is True
        and q.get('retained_java_sources_verified')==19-len(JAVA_CHANGES)
        and q.get('authored_java_sources_verified')==19 and q.get('baseline_payloads_verified')==77
        and all(q.get(k) is False for k in FALSE_FLAGS),'Exact truthful .24 Android-only qualification required')
    contract=module('setup_copy_qualification_contract',ROOT/QUALIFICATION_SCRIPT); contract.validate_suite_inventory()
    suites=q.get('test_suites',{})
    require(set(suites)==set(contract.TEST_MODULES) and q.get('check_suites')==contract.CHECK_SUITES
        and all(s.get('status')=='passed' and s.get('skipped')==0 and type(s.get('tests_run')) is int and s['tests_run']>0 for s in suites.values())
        and q.get('tests_run')==sum(s['tests_run'] for s in suites.values()),'All retained/new suites must pass without skips')
    require(SOURCE_FILES<=set(q.get('source_files',{})),'Current setup repair source closure incomplete')
    for name,expected in q['source_files'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name,'Unsafe qualified path')
        builder().checked_file(ROOT/name,expected)
    require(q.get('postgresql_emission_fixtures')==['cancelled_child_deletion_commits','delete_insert_replacement_commits','duplicate_insert_23505_rollback']
        and q.get('postgresql_levelup_fixtures')==sorted(retained.levelup_postgresql_fixtures()),'All seven real PG fixtures required')
    return q

def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.retained_client_directory)
    q = validate_qualification(read_json(args.qualification), commit)
    native = validate_retained_native(args.retained_client_directory, donor)
    require(q.get('retained_native_render_pipeline') == native, 'Qualified retained native package differs')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh setup repair APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-setup-copy-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads, preflight = extract_retained(args.donor_apk, donor, work/'donor')
        classes, generated, dex = (work/name for name in ('classes', 'generated', 'dex'))
        for folder in (classes, generated, dex): folder.mkdir()
        current_java_sources(donor, generated)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android inventory differs')
            for name, pin in donor['retained_android_resources'].items():
                raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Android resources changed beyond version')
        require({path.relative_to(generated).as_posix() for path in generated.rglob('*.java')} == {base.APP_ID.replace('.', '/')+'/R.java'}, 'Unexpected generated Java source')
        sources, java, changed = current_java_sources(donor, generated)
        require(q.get('java_sources') == java and q.get('changed_java_sources') == changed, 'Java changed after qualification')
        base.run('java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-cp', args.android_jar, '-d', classes, *sources)
        class_jar = work/'classes.jar'
        with zipfile.ZipFile(class_jar, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')): archive.write(path, path.relative_to(classes).as_posix())
        base.run('java', '-cp', args.build_tools/'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26', '--lib', args.android_jar, '--output', dex, class_jar)
        require({path.name for path in dex.iterdir()} == {'classes.dex'}, 'Unexpected DEX output')
        dex_pin = base.file_pin(dex/'classes.dex')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(dex/'classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, dex_pin); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': DONOR_COMMIT, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'retained_native_repository_commit': NATIVE_BUILD_COMMIT, 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE,
            'donor': donor_link(), 'signer_certificate_sha256': certificate, 'signing_key_created': False,
            'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': [], 'replaced_apk_payloads': [],
            'added_apk_payloads': [], 'baseline_payloads_verified': 77, 'retained_baseline_payloads_verified': 77,
            'recompiled_dex': dex_pin, 'donor_dex': donor['retained_dex'], 'java_sources': java,
            'changed_java_sources': changed, 'added_java_sources': [], 'retained_java_sources_verified': 19-len(JAVA_CHANGES), 'authored_java_sources_verified': 19,
            'native_build_provenance': native_build_provenance(), 'publication_provenance': publication_provenance(commit),
            'generated_manifest': base.file_pin(manifest), 'qualification': q,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'java_or_dex_recompiled': True, 'installed_runtime_identity_preserved': True,
            'previous_runtime_generation_retained': True, 'native_client_package_reused': True,
            'retained_native_render_pipeline': native, 'setup_memory_guards_preserved': True,
            'all_published_visual_resources_retained': True, **{key: False for key in FALSE_FLAGS},
            **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified Android-only setup repair APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.retained_client_directory)
    base, current = builder(), builder(repaired=True); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_retained_native(args.retained_client_directory, donor); report = read_json(args.build_report)
    _, java, changed = current_java_sources(donor, ROOT/'out/no-generated-java')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == DONOR_COMMIT and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('retained_native_repository_commit') == NATIVE_BUILD_COMMIT and report.get('donor') == donor_link()
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('application_id') == base.APP_ID
        and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('native_build_provenance') == native_build_provenance()
        and report.get('publication_provenance') == publication_provenance(commit)
        and report.get('qualification') == q and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('retained_native_render_pipeline') == native and q.get('retained_native_render_pipeline') == native
        and report.get('java_sources') == q.get('java_sources') == java and report.get('changed_java_sources') == q.get('changed_java_sources') == changed
        and report.get('added_java_sources') == [] and report.get('retained_java_sources_verified') == 19-len(JAVA_CHANGES)
        and report.get('authored_java_sources_verified') == 19
        and report.get('donor_dex') == donor['retained_dex'] and report.get('payloads') == donor['payloads']
        and report.get('changed_apk_payloads') == [] and report.get('replaced_apk_payloads') == [] and report.get('added_apk_payloads') == []
        and report.get('baseline_payloads_verified') == report.get('retained_baseline_payloads_verified') == 77
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'java_or_dex_recompiled', 'installed_runtime_identity_preserved', 'previous_runtime_generation_retained',
            'native_client_package_reused', 'setup_memory_guards_preserved', 'all_published_visual_resources_retained'))
        and all(report.get(key) is False for key in FALSE_FLAGS)
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Android-only setup repair build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'])
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); retained.verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    require_current_release_head(api, report['repository_commit'])
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.24 — bounded runtime setup copy',
        'body': notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        pin = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == pin['bytes']
            and uploaded.get('digest') == 'sha256:'+pin['sha256'], 'Release upload differs')
    require_current_release_head(api, report['repository_commit'])
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True
        and published.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return published.get('html_url')



def validate_existing_release(release):
    require(type(release.get('id')) is int and release['id'] > 0 and release.get('tag_name') == RELEASE_TAG
        and release.get('draft') is False and release.get('prerelease') is True
        and type(release.get('published_at')) is str and bool(release['published_at']), 'Incomplete existing release: resume original owner jobs')
    assets = release.get('assets'); base = 'https://github.com/'+REPOSITORY+'/releases/download/'+RELEASE_TAG+'/'
    require(type(assets) is list and len(assets) == 3 and {v.get('name') for v in assets} == {APK_NAME, APK_NAME+'.sha256', NOTES_NAME}, 'Incomplete release asset inventory')
    for value in assets:
        require(value.get('state') == 'uploaded' and type(value.get('size')) is int and 0 < value['size'] <= 2*1024**3
            and re.fullmatch(r'sha256:[0-9a-f]{64}', str(value.get('digest', ''))) and value.get('browser_download_url') == base+value['name'], 'Incomplete release asset metadata')
        if value['name'] == APK_NAME+'.sha256': require(value['size'] == 97, 'Incomplete checksum metadata')
        if value['name'] == NOTES_NAME: require(value['size'] <= 65536, 'Oversized testing instructions metadata')
    return True


def download_donor_evidence(args):
    require(not args.output.exists() and not args.output.is_symlink(),'Fresh donor evidence directory required')
    args.output.mkdir(parents=True)
    path=args.output/DONOR_EVIDENCE_ARCHIVE
    history.authenticated_artifact_download(DONOR_EVIDENCE_ID,path,DONOR_EVIDENCE)
    members=donor_evidence_members(path)
    with zipfile.ZipFile(path) as archive:
        for name in sorted(members):
            destination=args.output/name; destination.write_bytes(archive.read(name)); builder().checked_file(destination,members[name])
    print('Authenticated exact public .23 donor packaging artifact; no builds repeated')


def download_public(args):
    report=read_json(args.build_report)
    require(report.get('apk')==APK_NAME,'Expected .24 public APK')
    specs={APK_NAME:{k:report[k] for k in ('bytes','sha256')},
        APK_NAME+'.sha256':pin((report['sha256']+'  '+APK_NAME+'\n').encode()),NOTES_NAME:report['testing_notes']}
    for name,expected in specs.items():
        destination=args.output/name
        if destination.exists() or destination.is_symlink(): builder().checked_file(destination,expected); destination.unlink()
        history.bounded_download('https://github.com/'+REPOSITORY+'/releases/download/'+RELEASE_TAG+'/'+name,destination,expected)
    print('Actual public APK, checksum and notes authenticated')


for _name in ('donor_link','validate_donor_receipt','validate_retained_native','validate_donor',
    'validate_retained_sources','current_java_sources','verify_derivative',
    'validate_qualification','build','verify_report','publish_release'):
    setattr(_base,_name,globals()[_name])
def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('GITHUB_REF')=='refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push','workflow_dispatch'),'Publication requires continuation branch')
    commit=builder().source_commit(os.environ.get('GITHUB_SHA')); report,checksum,notes=verify_report(args,commit)
    api=module('setup_copy_github',Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published setup copy repair:',publish_release(api.GitHub(os.environ.get('GH_TOKEN')),report,
        (args.apk,checksum,notes),notes.read_text()))


def main():
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest='command',required=True)
    for name in ('download-donor','download-donor-evidence','download-retained-native'):
        command=commands.add_parser(name); command.add_argument('--output',type=Path,required=True)
    command=commands.add_parser('download-public'); command.add_argument('--output',type=Path,required=True); command.add_argument('--build-report',type=Path,required=True)
    for name in ('build','audit','publish'):
        command=commands.add_parser(name)
        for argument in ('donor-apk','donor-build-report','qualification','build-tools','retained-client-directory'):
            command.add_argument('--'+argument,type=Path,required=True)
        command.add_argument('--testing-notes',type=Path,default=NOTES); command.add_argument('--repository-commit',default=os.environ.get('GITHUB_SHA'))
        if name=='build':
            command.add_argument('--android-jar',type=Path,required=True); command.add_argument('--keystore',type=Path,required=True)
            command.add_argument('--password-env',default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); command.add_argument('--output',type=Path,required=True)
        else:
            command.add_argument('--apk',type=Path,required=True); command.add_argument('--build-report',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='download-donor': history.bounded_download(DONOR_URL,args.output,DONOR_APK)
    elif args.command=='download-donor-evidence': download_donor_evidence(args)
    elif args.command=='download-retained-native': history.download_retained_native(args)
    elif args.command=='download-public': download_public(args)
    elif args.command=='build': build(args)
    elif args.command=='publish': publish(args)
    else: print('Fresh-process setup candidate verified:',verify_report(args,builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__=='__main__': main()

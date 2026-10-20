#!/usr/bin/env python3
"""Admit only one exact signed package after every report/Android gate passes."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from package_check import BUILD_PROFILES, PACKAGE
from upgrade_emulator_check import PREVIOUS_INPUTS, SIGNER

ROOT = Path(__file__).resolve().parents[3]
APK = 'CoH-Native-Combined-0.1.12-catalog-diagnostic-arm64.apk'
TAG = 'coh-native-combined-v0.1.12-catalog-diagnostic-test'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size < 16 * 1024 * 1024,
         'missing or unbounded qualification receipt: ' + str(path))
    return json.loads(path.read_bytes())


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def admit_framework_package(framework, x86, head):
    need(x86.get('status') == 'passed' and x86.get('package') == PACKAGE and x86.get('abi') == 'x86_64'
         and x86.get('source_commit') == head and x86.get('tracked_source_clean') is True,
         'emulator package status/source/ABI differs')
    need((x86.get('version_code'), x86.get('version_name')) == BUILD_PROFILES['catalog-diagnostic']
         and x86.get('build_profile') == 'catalog-diagnostic'
         and x86.get('signer_certificate_sha256') == SIGNER,
         'emulator package version/profile/signer differs')
    identity = x86.get('apk', {})
    need(identity.get('name') == 'CoH-Native-Combined-0.1.12-catalog-diagnostic-x86_64.apk'
         and type(identity.get('bytes')) is int and 0 < identity['bytes'] <= 25 << 20
         and isinstance(identity.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', identity['sha256']),
         'emulator package byte identity invalid')
    checks = framework.get('checks', [])
    need(framework.get('status') == 'passed' and framework.get('device', {}).get('api') == '33'
         and checks and all(row.get('passed') is True for row in checks),
         'Android13 framework failed or contains failed checks')
    matches = [row for row in checks if row.get('check') == 'current launcher APK identity matches exact installed package']
    need(len(matches) == 1 and matches[0].get('installed_apk_status') == 'ready'
         and matches[0].get('installed_apk_bytes') == identity['bytes']
         and matches[0].get('installed_apk_sha256') == identity['sha256'],
         'Android13 framework installed a different or unobserved candidate package')


def main():
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'optimized release admission refused')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package-root', 'framework-root', 'fragment-root', 'upgrade-root', 'notes', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    need(os.environ['GITHUB_REPOSITORY'] == 'Russianranger/coh-android' and os.environ['GITHUB_REF'] == 'refs/heads/native-android', 'wrong publication repository/ref')
    head = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip()
    need(head == os.environ['GITHUB_SHA'], 'publication source differs')
    need(not subprocess.check_output(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=no']).strip(), 'publication source is dirty')
    package, dso = (read(args.package_root / name) for name in ('arm64-package.json', 'arm64-interop-dso.json'))
    apk = args.package_root / APK
    identity = pin(apk)
    need(package['status'] == 'passed' and package['package'] == PACKAGE and package['abi'] == 'arm64-v8a', 'package admission failed')
    need((package['version_code'], package['version_name']) == BUILD_PROFILES['catalog-diagnostic'] and package['build_profile'] == 'catalog-diagnostic', 'wrong test version')
    need(package['source_commit'] == dso['source_revision'] == head and package['tracked_source_clean'] is True, 'package/runtime source differs')
    need(package['signer_certificate_sha256'] == SIGNER, 'data-preserving signer differs')
    need({key: package['apk'][key] for key in identity} == identity == dso['apk'], 'exact ARM64 package bytes differ')
    need(dso['passed'] is True and dso['internal_core_and_static_archive_exports_hidden'] is True and dso['world_authority'] is False, 'diagnostic DSO admission failed')
    protected = read(args.package_root / 'protected-inputs.json')
    baseline = read(ROOT / 'native-android/integration/three-workstreams-20261019/recovery.json')
    need(protected['passed'] is True and protected['source_revision'] == head and protected['protected_input_sha256'] == baseline['protected_input_sha256'], 'protected runtime inputs differ')
    source = read(args.package_root / 'source-admission.json')
    framework_source = read(args.framework_root / 'source-admission.json')
    need(source == framework_source and source['passed'] is True and source['source_revision'] == head, 'framework/package source admission differs')
    for name, digest in source['reviewed_raw_and_committed_source_sha256'].items():
        path = ROOT / name
        need(path.resolve() == path and path.is_file() and not path.is_symlink(), 'unsafe source pin')
        raw = path.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == digest and subprocess.check_output(['git', '-C', ROOT, 'show', head + ':' + name]) == raw, 'current raw/committed source pin differs: ' + name)
    regression = read(args.package_root / 'report-regression/qualification.json')
    need(regression['passed'] is True and regression['source_layout_fixture_and_production_probes'] is True and regression['new_report_heap_allocations'] == 0 and regression['report_limit_bytes'] == 7168 and regression['world_authority'] is False, 'focused report regression not qualified')
    need(set(regression['modes']) == {'release', 'asan', 'ubsan'}, 'missing sanitizer qualification')
    for mode in regression['modes'].values():
        need(mode['receipt']['passed'] is True and 0 < mode['receipt']['max_report_bytes'] < 7168, 'native regression mode failed')
        rows = {row['label']: row['report'] for row in mode['reports']}
        for label, phase in [('source-layout-initial-observed', 'INITIAL_OBSERVED'), ('closed-initial-sticky', 'CLOSED')]:
            row = rows[label]
            need(row['phase'] == phase and row['initial_observed'] is True and row['cleanup_verified'] is True and row['opened_sockets'] == row['closed_sockets'], 'capture/cleanup evidence lost')
        boundary = rows['source-layout-initial-observed']['catalog_boundary']
        need(boundary is not None and boundary == rows['maximum-width-scalars']['catalog_boundary']
             and rows['maximum-width-scalars']['report_omitted_mask'] & 128,
             'essential catalog boundary lost when optional progress omitted')
        need(rows['catalog-boundary-default']['catalog_boundary'][1] == 41
             and rows['catalog-boundary-default']['catalog_boundary'] == rows['catalog-boundary-closed']['catalog_boundary'],
             'original default boundary/cleanup not qualified')
        need(rows['reward-progress-local-refusal']['catalog_boundary'] is None,
             'invalid composed source admitted a catalog boundary')
    for name, digest in regression['source_sha256'].items():
        need(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'regression compiled source pin differs: ' + name)
    phase = read(args.package_root / 'phase-regression.json')
    need(phase['status'] == 'passed' and phase['checks'] >= 85 and phase['android_execution'] is False, 'phase controls missing')
    for field, name in [('activity_sha256', 'NativeClientActivity.java'), ('state_sha256', 'HandoffState.java')]:
        need(hashlib.sha256((ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined' / name).read_bytes()).hexdigest() == phase[field], 'phase source pin differs')
    host = read(args.package_root / 'host/receipt.json')
    need(host['status'] == 'passed' and all(suite['returncode'] == 0 for suite in host['suites']), 'host qualification failed')
    framework, fragment, upgrade = (read(root / 'receipt.json') for root in (args.framework_root, args.fragment_root, args.upgrade_root))
    need(framework['status'] == 'passed' and framework['device']['api'] == '33', 'Android13 import/framework failed')
    x86 = read(args.package_root / 'x86_64-package.json')
    admit_framework_package(framework, x86, head)
    need(pin(args.package_root / x86['apk']['name']) == {key: x86['apk'][key] for key in ('bytes', 'sha256')}, 'exact emulator package bytes differ')
    need(fragment['passed'] is True and fragment['source_revision'] == head and fragment['apk'] == x86['apk'] and fragment['world_authority'] is False and fragment['package_receipt'] == x86
         and all(row.get('passed') is True for row in fragment['checks']), 'Android13 exact-package fragment/lifecycle failed')
    need(upgrade['passed'] is True and upgrade['source_revision'] == head and upgrade['candidate_apk'] == x86['apk'] and upgrade['previous']['apk_sha256'] == PREVIOUS_INPUTS['report-diagnostic']['apk_sha256']
         and upgrade['candidate_source_revision'] == head and all(row.get('passed') is True for row in upgrade['checks']), 'Android13 0.1.11 update failed')
    need(upgrade['debuggable_package_downgrade_exercised'] is True and upgrade['world_authority'] is False, 'data-preserving rollback not exercised')
    need(not args.output.exists(), 'refuse replacing publication staging')
    args.output.mkdir(parents=True)
    shutil.copyfile(apk, args.output / APK)
    for name in ('arm64-package.json', 'arm64-interop-dso.json'):
        shutil.copyfile(args.package_root / name, args.output / name)
    workflow = 'https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID']
    proof = {'schema': 'coh-catalog-diagnostic-publication-v1', 'passed': True, 'source_revision': head,
        'workflow_url': workflow, 'apk': dict(name=APK, **identity), 'version_code': 13,
        'version_name': BUILD_PROFILES['catalog-diagnostic'][1], 'package': PACKAGE,
        'signer_certificate_sha256': SIGNER, 'source_pin_count': len(source['reviewed_raw_and_committed_source_sha256']),
        'native_report_qualification': {'modes': sorted(regression['modes']), 'report_limit_bytes': 7168,
            'checks_each': regression['modes']['release']['receipt']['checks'],
            'max_report_bytes': regression['modes']['release']['receipt']['max_report_bytes'],
            'new_report_heap_allocations': 0, 'source_layout_fixture_and_production_probes': True},
        'phase_controls': phase['checks'], 'android13_framework_checks': len(framework['checks']),
        'android13_fragment_checks': len(fragment['checks']), 'android13_upgrade_checks': len(upgrade['checks']),
        'catalog_default_refusal_host_qualified': True, 'native_optional_progress_omission_preserves_boundary': True,
        'Android_positive_catalog_boundary_exercised': False,
        'previous_build_profile': 'report-diagnostic', 'same_signer_update_and_debuggable_rollback_exercised': True,
        'physical_Thor_qualified': False, 'gates_25_27_open': True, 'world_authority': False}
    (args.output / 'qualification-summary.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    (args.output / (APK + '.sha256')).write_text(identity['sha256'] + '  ' + APK + '\n')
    notes = args.notes.read_text() + '\n\nAPK SHA-256: `' + identity['sha256'] + '`.\n\nQualification: ' + workflow + '\n\nSource revision: `' + head + '`.\n'
    (args.output / 'RELEASE-NOTES.md').write_text(notes)
    print(json.dumps({'passed': True, 'apk': identity, 'workflow_url': workflow, 'tag': TAG}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Admit only one exact signed package after every report/Android gate passes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from package_check import BUILD_PROFILES, PACKAGE
from upgrade_emulator_check import PREVIOUS_INPUTS, SIGNER

ROOT = Path(__file__).resolve().parents[3]
APK = 'CoH-Native-Combined-0.1.11-report-diagnostic-arm64.apk'
TAG = 'coh-native-combined-v0.1.11-report-diagnostic-test'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size < 16 * 1024 * 1024,
         'missing or unbounded qualification receipt: ' + str(path))
    return json.loads(path.read_bytes())


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


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
    need((package['version_code'], package['version_name']) == BUILD_PROFILES['report-diagnostic'] and package['build_profile'] == 'report-diagnostic', 'wrong test version')
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
    for name, digest in regression['source_sha256'].items():
        need(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'regression compiled source pin differs: ' + name)
    phase = read(args.package_root / 'phase-regression.json')
    need(phase['status'] == 'passed' and phase['checks'] >= 40 and phase['android_execution'] is False, 'phase controls missing')
    for field, name in [('activity_sha256', 'NativeClientActivity.java'), ('state_sha256', 'HandoffState.java')]:
        need(hashlib.sha256((ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined' / name).read_bytes()).hexdigest() == phase[field], 'phase source pin differs')
    host = read(args.package_root / 'host/receipt.json')
    need(host['status'] == 'passed' and all(suite['returncode'] == 0 for suite in host['suites']), 'host qualification failed')
    framework, fragment, upgrade = (read(root / 'receipt.json') for root in (args.framework_root, args.fragment_root, args.upgrade_root))
    need(framework['status'] == 'passed' and framework['device']['api'] == '33', 'Android13 import/framework failed')
    x86 = read(args.package_root / 'x86_64-package.json')
    need(fragment['passed'] is True and fragment['source_revision'] == head and fragment['apk'] == x86['apk'] and fragment['world_authority'] is False, 'Android13 exact-package fragment/lifecycle failed')
    need(upgrade['passed'] is True and upgrade['source_revision'] == head and upgrade['candidate_apk'] == x86['apk'] and upgrade['previous']['apk_sha256'] == PREVIOUS_INPUTS['memory-diagnostic']['apk_sha256'], 'Android13 0.1.10 update failed')
    need(upgrade['debuggable_package_downgrade_exercised'] is True and upgrade['world_authority'] is False, 'data-preserving rollback not exercised')
    need(not args.output.exists(), 'refuse replacing publication staging')
    args.output.mkdir(parents=True)
    shutil.copyfile(apk, args.output / APK)
    for name in ('arm64-package.json', 'arm64-interop-dso.json'):
        shutil.copyfile(args.package_root / name, args.output / name)
    workflow = 'https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID']
    proof = {'schema': 'coh-report-diagnostic-publication-v1', 'passed': True, 'source_revision': head,
        'workflow_url': workflow, 'apk': dict(name=APK, **identity), 'version_code': 12,
        'version_name': BUILD_PROFILES['report-diagnostic'][1], 'package': PACKAGE,
        'signer_certificate_sha256': SIGNER, 'source_pin_count': len(source['reviewed_raw_and_committed_source_sha256']),
        'native_report_qualification': {'modes': sorted(regression['modes']), 'report_limit_bytes': 7168,
            'checks_each': regression['modes']['release']['receipt']['checks'],
            'max_report_bytes': regression['modes']['release']['receipt']['max_report_bytes'],
            'new_report_heap_allocations': 0, 'source_layout_fixture_and_production_probes': True},
        'phase_controls': phase['checks'], 'android13_framework_checks': len(framework['checks']),
        'android13_fragment_checks': len(fragment['checks']), 'android13_upgrade_checks': len(upgrade['checks']),
        'previous_build_profile': 'memory-diagnostic', 'same_signer_update_and_debuggable_rollback_exercised': True,
        'physical_Thor_qualified': False, 'gates_25_27_open': True, 'world_authority': False}
    (args.output / 'qualification-summary.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    (args.output / (APK + '.sha256')).write_text(identity['sha256'] + '  ' + APK + '\n')
    notes = args.notes.read_text() + '\n\nAPK SHA-256: `' + identity['sha256'] + '`.\n\nQualification: ' + workflow + '\n\nSource revision: `' + head + '`.\n'
    (args.output / 'RELEASE-NOTES.md').write_text(notes)
    print(json.dumps({'passed': True, 'apk': identity, 'workflow_url': workflow, 'tag': TAG}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Bounded Android13 package update/rollback and synthetic data preservation.

No guest process or game save parser runs. Sentinel bytes represent app-private
profile/import/save storage only; this does not qualify real game migration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import zipfile
from prepare import safe_zip
from package_check import PACKAGE, BUILD_PROFILES, check_build_identity

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_REVISION = 'd439f56ba05c3051e50c630c40afe796a9c2ec4e'
PREVIOUS_ARTIFACT = '12159047135'
PREVIOUS_RUN = '39188732819'
PREVIOUS_ARCHIVE_BYTES = 17073074
PREVIOUS_ARCHIVE_SHA = 'af0aaa0afe0d50cbedb54a7a8ea7dcda4dab3462516a71f5d49051230c9e152a'
PREVIOUS_APK = 'CoH-Native-Combined-0.1.9-gates25-27-x86_64.apk'
PREVIOUS_APK_BYTES = 13182827
PREVIOUS_APK_SHA = '17fdc39f01dd282ea2787b4f4f0fbc7e3f2c981f92ebe2cabe1c2afed782f6f4'
SIGNER = '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522'
# Historical pins remain the default. The report regression must additionally
# exercise the exact installed 0.1.10 donor, not infer that path from 0.1.9.
PREVIOUS_INPUTS = {
    'capture-diagnostic': dict(revision='f311bebfa9bdf33916fefcaaacd546282e17b534',artifact='12289656309',
        run='39474180919',archive_bytes=24919187,
        archive_sha256='db4151cd32c6140b9e116b3ee6479d1e14d4dda6a097f8a46f400887a86f9814',
        apk='CoH-Native-Combined-0.1.16-capture-diagnostic-x86_64.apk',apk_bytes=14452858,
        apk_sha256='b02a302a0754d9c40841992a83ce500d74f930fecd043c3bcd509cdc07a97109'),
    'original-fragment': dict(revision=PREVIOUS_REVISION, artifact=PREVIOUS_ARTIFACT,
        run=PREVIOUS_RUN, archive_bytes=PREVIOUS_ARCHIVE_BYTES, archive_sha256=PREVIOUS_ARCHIVE_SHA,
        apk=PREVIOUS_APK, apk_bytes=PREVIOUS_APK_BYTES, apk_sha256=PREVIOUS_APK_SHA),
    'report-diagnostic': dict(revision='042a149e6ca00d76e498fae9958bf49e5b795dd6', artifact='12234456043',
        run='39352586218', archive_bytes=18664742,
        archive_sha256='767e98dd382d0a756df4903b16632c13bf0be080f475282c6894e2e7b50e3a63',
        apk='CoH-Native-Combined-0.1.11-report-diagnostic-x86_64.apk', apk_bytes=13237943,
        apk_sha256='ccfbca1fdba7c07e974aa679c2708fafcfe6860110cdef06d4779393c9d9a82a'),
    'memory-diagnostic': dict(revision='ae5a11d0c0be5098d0aec66370dda99c055167ee', artifact='12226012507',
        run='39334606957', archive_bytes=17868604,
        archive_sha256='0d38981d31781a0e2d24adc579017e335ecb80cef547e45e5d0ee915d44ddd04',
        apk='CoH-Native-Combined-0.1.10-memory-diagnostic-x86_64.apk', apk_bytes=13233003,
        apk_sha256='4cba32800790112c22146f6f6f8f773436a816de44c3e83d1c9503b0e9ec4d49'),
    'entity-diagnostic': dict(revision='38c6446830dc6a55204a663de7477db12c6a5536', artifact='12259140776',
        run='39408855380', archive_bytes=16266666,
        archive_sha256='cea4a2c3ff82f469ec016b2ef08dee640e32f2b041e8f4d0b6862bdd3050858e',
        apk='CoH-Native-Combined-0.1.14-entity-diagnostic-x86_64.apk', apk_bytes=13257323,
        apk_sha256='a1260501d5cc6f2074eba02617fe53eb011f456ada27092620955f8d9e30de2b'),
}



def need(ok, message):
    if not ok:
        raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def previous_inputs(archive_path, output, profile='original-fragment'):
    expected = PREVIOUS_INPUTS[profile]
    need(archive_path.stat().st_size == expected['archive_bytes'], 'previous artifact byte length differs')
    need(hashlib.sha256(archive_path.read_bytes()).hexdigest() == expected['archive_sha256'], 'previous artifact SHA256 differs')
    with zipfile.ZipFile(archive_path) as archive:
        safe_zip(archive)
        need(len(archive.infolist()) <= 4096, 'previous artifact member count exceeds bound')
        need(archive.getinfo(expected['apk']).file_size == expected['apk_bytes'], 'previous APK member size differs')
        raw = archive.read(expected['apk'])
        if profile == 'entity-diagnostic':
            # 0.1.14 retained its executed x86 APK pin and an ARM64 package audit,
            # rather than an x86 package receipt. Verify those actual records;
            # return only expected installed metadata for the storage exercise.
            need(archive.getinfo('arm64-package.json').file_size <= 256 * 1024, 'previous ARM64 receipt exceeds bound')
            arm = json.loads(archive.read('arm64-package.json'))
            accepted = json.loads((ROOT / 'native-android/combined-client/diagnostics/entity-20261020/arm64-0.1.14-package.json').read_bytes())
            need(arm == accepted, 'accepted 0.1.14 package audit differs')
            need(arm['source_commit'] == expected['revision'] and arm['signer_certificate_sha256'] == SIGNER, 'accepted 0.1.14 source or signer differs')
            check_build_identity(arm['version_code'], arm['version_name'], profile)
            receipt = {'version_code': arm['version_code'], 'version_name': arm['version_name'], 'apk': pin(raw)}
        else:
            need(archive.getinfo('x86_64-package.json').file_size <= 256 * 1024, 'previous receipt exceeds bound')
            receipt = json.loads(archive.read('x86_64-package.json'))
    need(pin(raw) == {'bytes': expected['apk_bytes'], 'sha256': expected['apk_sha256']}, 'previous APK pin differs')
    if profile != 'entity-diagnostic':
        package_receipt(receipt, raw, profile, expected['revision'])
    target = output / expected['apk']
    with target.open('xb') as stream:
        stream.write(raw)
    return target, receipt


def package_receipt(receipt, raw, profile, revision):
    need(receipt['status'] == 'passed' and receipt['abi'] == 'x86_64' and receipt['package'] == PACKAGE, 'package receipt identity differs')
    check_build_identity(receipt['version_code'], receipt['version_name'], profile)
    need(receipt['source_commit'] == revision and receipt['tracked_source_clean'] is True, 'package source revision differs')
    need(receipt['signer_certificate_sha256'] == SIGNER, 'package upgrade signer differs')
    need({k: receipt['apk'][k] for k in ('bytes', 'sha256')} == pin(raw), 'package bytes differ from receipt')


def sentinels():
    """Small synthetic fixtures in representative private storage locations."""
    return {
        'files/combined-import/upgrade-profile-sentinel.pgdump': b'PGDMP\0SYNTHETIC STORAGE SENTINEL; NEVER RESTORE\n' + bytes(range(256)) * 16,
        'files/combined-import/upgrade-import-sentinel.bin': bytes((i * 13 + 7) & 255 for i in range(65536)),
        'files/combined-server/diagnostic/state/upgrade-save-sentinel.json': b'{"synthetic":true,"not_a_game_save":true,"character":"StorageFixture","level":1}\n',
        'shared_prefs/upgrade-qualification.xml': b'<?xml version="1.0" encoding="utf-8"?><map><string name="profile">synthetic-disposable</string></map>\n',
    }


class UpgradeCheck:
    def __init__(self, args):
        self.args = args
        self.proofs = []

    def adb(self, *command, check=True, timeout=60):
        result = subprocess.run([self.args.adb, '-s', self.args.serial, *map(str, command)], capture_output=True, timeout=timeout)
        if check:
            need(result.returncode == 0, 'ADB command refused: ' + str(command[:3]) + ' ' + (result.stdout + result.stderr).decode(errors='replace')[-2000:])
        return result

    def text(self, *command):
        return self.adb(*command).stdout.decode()

    def record(self, stage, **details):
        self.proofs.append({'stage': stage, 'passed': True, **details})
        (self.args.output / 'progress.json').write_text(json.dumps(self.proofs, indent=2) + '\n')

    def install(self, apk, label, replace=False, downgrade=False):
        # This package/data test runs with notifications already granted, like
        # the main framework suite. Leaving Android's permission Activity open
        # while replacing the requesting package can strand an orphan task.
        flags = ['-g'] + (['-r'] if replace else []) + (['-d'] if downgrade else [])
        result = self.adb('install', *flags, apk, timeout=120)
        need(re.search(rb'^Success\s*$', result.stdout, re.M) is not None, 'package installation did not report Success')
        (self.args.output / (label + '-install.txt')).write_bytes(result.stdout + result.stderr)

    def identity(self, apk, receipt, label):
        metadata = self.text('shell', 'dumpsys', 'package', PACKAGE)
        version = re.search(r'\bversionCode=(\d+)\b', metadata)
        name = re.search(r'\bversionName=([^\s]+)', metadata)
        uid = re.search(r'\buserId=(\d+)\b', metadata)
        need(version and name and uid, 'installed version/UID absent')
        need((version.group(1), name.group(1)) == (receipt['version_code'], receipt['version_name']), 'installed version differs')
        paths = self.text('shell', 'pm', 'path', PACKAGE).splitlines()
        need(len(paths) == 1 and paths[0].startswith('package:/data/app/') and paths[0].endswith('/base.apk'), 'installed APK path shape differs')
        raw = self.adb('exec-out', 'cat', paths[0][8:]).stdout
        need(pin(raw) == pin(apk.read_bytes()), 'actual installed APK bytes differ')
        self.record(label, version_code=version.group(1), version_name=name.group(1), installed_apk=pin(raw), uid=int(uid.group(1)))
        return uid.group(1)

    def launch_and_quiesce(self, receipt, label):
        permissions = self.text('shell', 'dumpsys', 'package', PACKAGE)
        need(re.search(r'^\s*android\.permission\.POST_NOTIFICATIONS:\s+granted=true(?:,|$)', permissions, re.M) is not None, 'test installation must grant notifications before launcher lifecycle checks')
        # Retain the pre-launch report rather than clearing persisted app data.
        # An explicit stopped process plus uptime requires a fresh report epoch.
        self.capture(label + '-before')
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        start_elapsed_ms = int(float(self.text('shell', 'cat', '/proc/uptime').split()[0]) * 1000)
        result = self.text('shell', 'am', 'start', '-W', '-n', PACKAGE + '/.MainActivity')
        (self.args.output / (label + '-am-start.txt')).write_text(result)
        need('Error:' not in result, 'launcher start refused')
        deadline = time.monotonic() + 45
        observations = {'start_elapsed_ms': start_elapsed_ms, 'read_attempts': 0, 'last_read_returncode': None, 'last_report_bytes': None, 'json_decode_failures': 0}
        while time.monotonic() < deadline:
            result = self.adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/combined-report.json', check=False)
            observations.update(read_attempts=observations['read_attempts'] + 1, last_read_returncode=result.returncode, last_report_bytes=len(result.stdout))
            (self.args.output / (label + '-report-read.stderr')).write_bytes(result.stderr[:8192])
            if result.returncode == 0:
                need(len(result.stdout) <= 128 * 1024, 'combined launcher report exceeds existing 128KiB bound')
                (self.args.output / (label + '-last-combined-report.json')).write_bytes(result.stdout)
                try:
                    report = json.loads(result.stdout)
                except json.JSONDecodeError:
                    observations['json_decode_failures'] += 1
                    report = None
                if isinstance(report, dict):
                    observations['last_observed_identity'] = {key: report.get(key) for key in ('version_code', 'version_name', 'installed_apk_status', 'updated_elapsed_ms')}
                    fresh = type(report.get('updated_elapsed_ms')) is int and report['updated_elapsed_ms'] >= start_elapsed_ms
                    if fresh and str(report.get('version_code')) == receipt['version_code'] and report.get('version_name') == receipt['version_name']:
                        if report.get('installed_apk_status') == 'ready':
                            need(report['installed_apk'] == {k: receipt['apk'][k] for k in ('bytes', 'sha256')}, 'launcher report APK identity differs')
                            server = report.get('server')
                            need(isinstance(server, dict), 'fresh launcher report server fields absent')
                            need(report.get('busy') is False and server.get('owned_process_alive') is False and server.get('ready') is False, 'guest unexpectedly started')
                            need(server.get('phase') == 'stopped' and server.get('failure_code') == '', 'idle launcher initialization failed')
                            (self.args.output / (label + '-report-observations.json')).write_text(json.dumps(observations, indent=2) + '\n')
                            self.capture(label + '-after')
                            self.assert_no_app_fault(label)
                            self.adb('shell', 'am', 'force-stop', PACKAGE)
                            self.record(label, launcher_opened=True, guest_started=False, fresh_report_epoch=True, notification_permission_granted=True)
                            return
            (self.args.output / (label + '-report-observations.json')).write_text(json.dumps(observations, indent=2) + '\n')
            time.sleep(.25)
        self.capture(label + '-timeout')
        self.assert_no_app_fault(label)
        raise ValueError('launcher did not produce the exact installed idle package identity')

    def capture(self, label):
        for name, command, limit in (
            ('combined-report.json', ('exec-out', 'run-as', PACKAGE, 'cat', 'files/combined-report.json'), 128 * 1024),
            ('activity.txt', ('shell', 'dumpsys', 'activity', 'activities'), 2 * 1024 * 1024),
            ('lastanr.txt', ('shell', 'dumpsys', 'activity', 'lastanr'), 256 * 1024),
            ('crash.txt', ('logcat', '-d', '-b', 'crash', '-t', '200'), 256 * 1024),
            ('app-logcat.txt', ('logcat', '-d', '-t', '400', '-s', 'AndroidRuntime', 'ActivityManager', 'coh-memory-observer'), 512 * 1024),
        ):
            try:
                result = self.adb(*command, check=False, timeout=15)
                (self.args.output / (label + '-' + name)).write_bytes(result.stdout[:limit])
            except Exception as failure:
                (self.args.output / (label + '-' + name + '.capture-error')).write_text(type(failure).__name__)

    def assert_no_app_fault(self, label):
        lastanr = self.text('shell', 'dumpsys', 'activity', 'lastanr')
        crashes = self.text('logcat', '-d', '-b', 'crash', '-t', '200')
        need(re.search(r'ANR in ' + re.escape(PACKAGE) + r'(?:[\s(/]|$)', lastanr) is None and PACKAGE not in crashes, 'app crash or ANR observed during ' + label)

    def seed(self):
        for index, (name, raw) in enumerate(sentinels().items()):
            need(self.adb('shell', 'run-as', PACKAGE, 'test', '-e', name, check=False).returncode != 0, 'sentinel target already exists')
            local = self.args.output / ('sentinel-' + str(index))
            local.write_bytes(raw)
            remote = '/data/local/tmp/coh-upgrade-sentinel-' + str(index)
            self.adb('push', local, remote)
            try:
                self.adb('shell', 'run-as', PACKAGE, 'mkdir', '-p', str(Path(name).parent))
                self.adb('shell', 'run-as', PACKAGE, 'cp', remote, name)
            finally:
                self.adb('shell', 'rm', '-f', remote)
        self.preserved('previous-seeded')

    def preserved(self, label):
        values = {}
        for name, raw in sentinels().items():
            observed = self.adb('exec-out', 'run-as', PACKAGE, 'cat', name).stdout
            need(observed == raw, 'synthetic private storage changed: ' + name)
            values[name] = pin(observed)
        self.record(label, sentinel_sha256=values, synthetic_storage_only=True)

    def run(self):
        need(self.text('shell', 'getprop', 'ro.boot.qemu').strip() == '1' and self.text('shell', 'getprop', 'ro.product.cpu.abi').strip() == 'x86_64' and self.text('shell', 'getprop', 'ro.build.version.sdk').strip() == '33', 'disposable Android13 x86_64 emulator required')
        need(not self.text('shell', 'pm', 'list', 'packages', '--user', '0', PACKAGE).strip(), 'refuse an emulator with an existing app')
        previous, old_receipt = previous_inputs(self.args.previous_archive, self.args.output, self.args.previous_profile)
        head = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip()
        need(not os.environ.get('GITHUB_SHA') or head == os.environ['GITHUB_SHA'], 'workflow revision differs')
        candidate = json.loads(self.args.package_receipt.read_bytes())
        candidate_revision = self.args.candidate_source_revision or head
        if candidate_revision != head:
            need(self.args.source_admission is not None and self.args.source_admission.stat().st_size <= 128 * 1024, 'exact-package source admission required')
            admission = json.loads(self.args.source_admission.read_bytes())
            need(admission['schema'] == 'coh-combined-exact-apk-requalification-v1' and admission['passed'] is True and admission['candidate_source_revision'] == candidate_revision and admission['qualification_source_revision'] == head and admission['runtime_and_build_inputs_unchanged'] is True, 'current source is not admitted for the exact candidate APK')
            need(admission['candidate_apks']['x86_64'] == pin(self.args.apk.read_bytes()), 'admitted candidate APK bytes differ')
        package_receipt(candidate, self.args.apk.read_bytes(), self.args.build_profile, candidate_revision)
        self.install(previous, 'previous')
        uid = self.identity(previous, old_receipt, 'previous-installed')
        self.launch_and_quiesce(old_receipt, 'previous-launch')
        self.seed()
        self.install(self.args.apk, 'upgrade', replace=True)
        need(self.identity(self.args.apk, candidate, 'candidate-upgraded') == uid, 'update changed private storage UID')
        self.preserved('after-package-upgrade')
        self.launch_and_quiesce(candidate, 'candidate-launch')
        self.preserved('after-candidate-launch')
        if self.args.exercise_debuggable_downgrade:
            self.install(previous, 'debuggable-rollback', replace=True, downgrade=True)
            need(self.identity(previous, old_receipt, 'previous-rolled-back') == uid, 'rollback changed private storage UID')
            self.preserved('after-package-rollback')
            self.launch_and_quiesce(old_receipt, 'previous-rollback-launch')
            self.preserved('after-rollback-launch')
            self.install(self.args.apk, 'candidate-reinstall', replace=True)
            need(self.identity(self.args.apk, candidate, 'candidate-reinstalled') == uid, 'reinstall changed private storage UID')
            self.launch_and_quiesce(candidate, 'candidate-reinstall-launch')
            self.preserved('after-candidate-reinstall')
        receipt = {'schema': 'coh-android-package-update-storage-v1', 'passed': True, 'source_revision': head,
            'previous': dict(PREVIOUS_INPUTS[self.args.previous_profile], build_profile=self.args.previous_profile),
            'candidate_apk': candidate['apk'], 'candidate_source_revision': candidate_revision,
            'source_admission_sha256': hashlib.sha256(self.args.source_admission.read_bytes()).hexdigest() if self.args.source_admission else None,
            'checks': self.proofs, 'synthetic_sentinel_bytes': sum(map(len, sentinels().values())),
            'synthetic_profile_uses_active_import_filename': False, 'initial_failed_upgrade_launch_root_cause_established': False,
            'notification_permission_pregranted_by_test_installer': True,
            'android_api': 33, 'abi': 'x86_64', 'debuggable_package_downgrade_exercised': self.args.exercise_debuggable_downgrade,
            'package_data_preservation_only': True, 'real_game_save_migration_qualified': False, 'guest_started': False,
            'physical_Thor_qualified': False, 'world_authority': False}
        (self.args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'Python assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    for name in ('apk', 'package-receipt', 'previous-archive', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--build-profile', choices=BUILD_PROFILES, default='memory-diagnostic')
    parser.add_argument('--previous-profile', choices=PREVIOUS_INPUTS, default='original-fragment')
    parser.add_argument('--exercise-debuggable-downgrade', action='store_true')
    parser.add_argument('--candidate-source-revision', help='Exact reused APK revision; requires an independent current-source admission when different from HEAD')
    parser.add_argument('--source-admission', type=Path)
    args = parser.parse_args()
    need((args.candidate_source_revision is None) == (args.source_admission is None), 'candidate revision and current-source admission must be supplied together')
    need(args.candidate_source_revision is None or re.fullmatch('[0-9a-f]{40}', args.candidate_source_revision) is not None, 'candidate revision must be an exact Git SHA')
    need(not args.output.exists(), 'fresh output required')
    args.output.mkdir(parents=True)
    driver = UpgradeCheck(args)
    try:
        driver.run()
    except Exception as failure:
        driver.capture('failure')
        (args.output / 'failure.json').write_text(json.dumps({'type': type(failure).__name__, 'message': str(failure)[:3000], 'package_data_preservation_only': True, 'real_game_save_migration_qualified': False}, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()

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
from package_check import PACKAGE, check_build_identity

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


def need(ok, message):
    if not ok:
        raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def previous_inputs(archive_path, output):
    need(archive_path.stat().st_size == PREVIOUS_ARCHIVE_BYTES, 'previous artifact byte length differs')
    need(hashlib.sha256(archive_path.read_bytes()).hexdigest() == PREVIOUS_ARCHIVE_SHA, 'previous artifact SHA256 differs')
    with zipfile.ZipFile(archive_path) as archive:
        safe_zip(archive)
        need(len(archive.infolist()) <= 4096, 'previous artifact member count exceeds bound')
        need(archive.getinfo(PREVIOUS_APK).file_size == PREVIOUS_APK_BYTES, 'previous APK member size differs')
        need(archive.getinfo('x86_64-package.json').file_size <= 256 * 1024, 'previous receipt exceeds bound')
        raw = archive.read(PREVIOUS_APK)
        receipt = json.loads(archive.read('x86_64-package.json'))
    need(pin(raw) == {'bytes': PREVIOUS_APK_BYTES, 'sha256': PREVIOUS_APK_SHA}, 'previous APK pin differs')
    package_receipt(receipt, raw, 'original-fragment', PREVIOUS_REVISION)
    target = output / PREVIOUS_APK
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
        'files/combined-import/profile.pgdump': b'PGDMP\0SYNTHETIC STORAGE SENTINEL; NEVER RESTORE\n' + bytes(range(256)) * 16,
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
        flags = (['-r'] if replace else []) + (['-d'] if downgrade else [])
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
        result = self.text('shell', 'am', 'start', '-W', '-n', PACKAGE + '/.MainActivity')
        need('Error:' not in result, 'launcher start refused')
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            result = self.adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/combined-report.json', check=False)
            if result.returncode == 0 and len(result.stdout) <= 2 * 1024 * 1024:
                try:
                    report = json.loads(result.stdout)
                    if (str(report.get('version_code')) == receipt['version_code'] and report.get('version_name') == receipt['version_name'] and report.get('installed_apk_status') == 'ready'):
                        need(report['installed_apk'] == {k: receipt['apk'][k] for k in ('bytes', 'sha256')}, 'launcher report APK identity differs')
                        need(report.get('busy') is False and report['server']['owned_process_alive'] is False and report['server']['ready'] is False, 'guest unexpectedly started')
                        self.adb('shell', 'am', 'force-stop', PACKAGE)
                        self.record(label, launcher_opened=True, guest_started=False)
                        return
                except (ValueError, KeyError, TypeError):
                    pass
            time.sleep(.25)
        raise ValueError('launcher did not produce the exact installed idle package identity')

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
        previous, old_receipt = previous_inputs(self.args.previous_archive, self.args.output)
        head = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip()
        need(not os.environ.get('GITHUB_SHA') or head == os.environ['GITHUB_SHA'], 'workflow revision differs')
        candidate = json.loads(self.args.package_receipt.read_bytes())
        package_receipt(candidate, self.args.apk.read_bytes(), 'memory-diagnostic', head)
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
            'previous': {'run_id': PREVIOUS_RUN, 'artifact_id': PREVIOUS_ARTIFACT, 'source_revision': PREVIOUS_REVISION, 'archive_bytes': PREVIOUS_ARCHIVE_BYTES, 'archive_sha256': PREVIOUS_ARCHIVE_SHA, 'apk_bytes': PREVIOUS_APK_BYTES, 'apk_sha256': PREVIOUS_APK_SHA},
            'candidate_apk': candidate['apk'], 'checks': self.proofs, 'synthetic_sentinel_bytes': sum(map(len, sentinels().values())),
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
    parser.add_argument('--exercise-debuggable-downgrade', action='store_true')
    args = parser.parse_args()
    need(not args.output.exists(), 'fresh output required')
    args.output.mkdir(parents=True)
    driver = UpgradeCheck(args)
    try:
        driver.run()
    except Exception as failure:
        (args.output / 'failure.json').write_text(json.dumps({'type': type(failure).__name__, 'message': str(failure)[:3000], 'package_data_preservation_only': True, 'real_game_save_migration_qualified': False}, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Extract only verified runtime/import assets from the retained app donor.

This does not build, sign, install or qualify an APK. The old app's complete
byte identity is fixed by its already published build evidence; only its
assets are inputs to the new ARM64 guest integration test.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

APK_BYTES = 590725465
APK_SHA = 'ee9c09a3bda8a7f68af1e481e8c85e96c14ee0ea6ab414dbcda2ca730dd73688'
REPORT_BYTES = 38185
REPORT_SHA = '587088a83e4d70e8dab88f8362367bc532b94e86412bf372750ac060728a689f'
DONOR_COMMIT = '204615c6c4a809d6b814c7174b81448cffea3f7a'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    require(path.is_file() and not path.is_symlink(), 'Regular donor file required')
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def extract(apk, build_report, output):
    require(pin(apk) == {'bytes': APK_BYTES, 'sha256': APK_SHA}, 'Retained APK bytes differ')
    require(pin(build_report) == {'bytes': REPORT_BYTES, 'sha256': REPORT_SHA}, 'Retained build report differs')
    report = json.loads(build_report.read_text())
    require(report['repository_commit'] == DONOR_COMMIT and report['sha256'] == APK_SHA
            and report['signature_verified'] is True and report['payload_bytes_verified'] is True,
            'Retained donor identity differs')
    require(not output.exists(), 'Fresh donor extraction required')
    output.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate APK member')
        selected = {name: record for name, record in report['payloads'].items() if name.startswith('assets/')}
        require(0 < len(selected) <= 128, 'Unexpected donor asset count')
        require(sum(archive.getinfo(name).file_size for name in selected) <= 2 * 1024**3,
                'Donor asset extraction exceeds bound')
        for name, expected in selected.items():
            path = PurePosixPath(name)
            require(len(path.parts) == 3 and path.parts[1] in ('runtime', 'atlas')
                    and path.name not in ('.', '..') and '\\' not in name,
                    'Unsafe donor asset path')
            member = archive.getinfo(name)
            require(not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16)
                    and member.file_size == expected['bytes'], 'Invalid donor asset member')
            target = output / path.parts[1] / path.name
            target.parent.mkdir(exist_ok=True)
            with archive.open(member) as source, target.open('xb') as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
            require(pin(target) == expected, 'Donor asset digest differs: ' + name)
    return {'run_id': 36920583713, 'artifact_id': 11192425448,
            'source_commit': DONOR_COMMIT, 'apk_sha256': APK_SHA, 'asset_count': len(selected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('apk', 'build-report', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    print(json.dumps(extract(**vars(parser.parse_args()))))


if __name__ == '__main__':
    main()

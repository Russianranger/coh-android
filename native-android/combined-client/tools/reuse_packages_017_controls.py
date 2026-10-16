#!/usr/bin/env python3
"""Independent source/ZIP/payload refusal controls for exact 0.1.7 reuse."""
from pathlib import Path
import argparse
import io
import json
import stat
import subprocess
import tempfile
from unittest.mock import patch
import zipfile
import reuse_packages_017 as reuse

checks = []


def check(name, action, rejected=False):
    try:
        action()
    except (ValueError, FileNotFoundError, KeyError, zipfile.BadZipFile):
        if not rejected:
            raise
    else:
        if rejected:
            raise AssertionError('Mutation was admitted: ' + name)
    checks.append(name)


def zip_controls():
    def inspect(entries):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, 'w') as z:
            for entry in entries:
                z.writestr(entry, b'x')
        with zipfile.ZipFile(memory) as z:
            reuse.validate_zip(z)
    check('regular ZIP admitted', lambda: inspect(['folder/file', 'second']))
    for name in ['../escape', '/absolute', 'folder\\escape', 'folder//file', 'folder/./file', 'C:/drive']:
        check('ZIP path refused: ' + name, lambda name=name: inspect([name]), True)
    for mode in [stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o600]:
        info = zipfile.ZipInfo('special');info.create_system = 3;info.external_attr = mode << 16
        check('ZIP special entry refused: ' + str(mode), lambda info=info: inspect([info]), True)
    check('ZIP file-directory alias refused', lambda: inspect(['same', 'same/']), True)
    check('ZIP parent conflict refused', lambda: inspect(['parent/file', 'parent']), True)
    check('ZIP member count refused', lambda: inspect([str(i) for i in range(129)]), True)
    class Archive:
        def __init__(self, entries):self.entries = entries
        def infolist(self):return self.entries
    info = zipfile.ZipInfo('oversize');info.file_size = (32 << 20) + 1
    check('ZIP member byte limit refused', lambda: reuse.validate_zip(Archive([info])), True)
    entries = [zipfile.ZipInfo(str(i)) for i in range(5)]
    for entry in entries:entry.file_size = 32 << 20
    check('ZIP total byte limit refused', lambda: reuse.validate_zip(Archive(entries)), True)
    duplicate = [zipfile.ZipInfo('duplicate'), zipfile.ZipInfo('duplicate')]
    check('ZIP duplicate refused', lambda: reuse.validate_zip(Archive(duplicate)), True)


def source_controls(directory):
    repo = directory / 'source';repo.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args], check=True,
            capture_output=True, text=True).stdout.strip()
    git('init', '-q');git('config', 'user.name', 'Reuse controls');git('config', 'user.email', 'reuse-controls@example.invalid')
    workflow = repo / reuse.MAIN_WORKFLOW;workflow.parent.mkdir(parents=True)
    workflow.write_text('jobs:\n  packages:\n' + reuse.OLD_CONDITION + '\n    steps: []\n')
    production = repo / 'native-android/engine/runtime.c';production.parent.mkdir(parents=True);production.write_text('int production;\n')
    driver = repo / 'native-android/combined-client/tools/emulator_check.py';driver.parent.mkdir(parents=True);driver.write_text('pass\n')
    git('add', '.');git('commit', '-qm', 'Qualified source')
    source = git('rev-parse', 'HEAD');tree = git('rev-parse', 'HEAD^{tree}')
    with patch.object(reuse, 'SOURCE', source), patch.object(reuse, 'SOURCE_TREE', tree):
        check('clean whole source closure admitted', lambda: reuse.validate_source(repo, True))
        production.write_text('int changed;\n')
        check('dirty production refused', lambda: reuse.validate_source(repo, False), True)
        production.write_text('int production;\n')
        untracked = production.with_name('unexpected.c');untracked.write_text('int unexpected;\n')
        check('untracked production refused', lambda: reuse.validate_source(repo, False), True);untracked.unlink()
        driver.write_text('pass # driver-only correction\n')
        check('dirty qualification source refused with clean flag', lambda: reuse.validate_source(repo, True), True)
        git('add', '.');git('commit', '-qm', 'Driver-only correction')
        check('committed driver-only change admitted', lambda: reuse.validate_source(repo, True))
        workflow.write_text(workflow.read_text().replace(reuse.OLD_CONDITION, reuse.NEW_CONDITION))
        git('add', '.');git('commit', '-qm', 'Exact continuation condition')
        check('exact workflow condition admitted', lambda: reuse.validate_source(repo, True))
        workflow.write_text(workflow.read_text().replace('steps: []', 'steps: [unauthorized]'))
        check('extra main workflow edit refused', lambda: reuse.validate_source(repo, False), True)
        workflow.write_text(workflow.read_text().replace('steps: [unauthorized]', 'steps: []'))
        production.write_text('int changed;\n');git('add', '.');git('commit', '-qm', 'Production mutation')
        check('committed production mutation refused', lambda: reuse.validate_source(repo, True), True)
    with patch.object(reuse, 'SOURCE', source), patch.object(reuse, 'SOURCE_TREE', '0' * 40):
        check('qualified source tree substitution refused', lambda: reuse.validate_source(repo, True), True)


def payload_controls(archive, source, directory):
    output = directory / 'packages'
    check('exact real artifact admitted without rebuilding', lambda: reuse.admit(archive, output, source))
    check('existing output preserved', lambda: reuse.admit(archive, output, source), True)
    def mutate(relative, change):
        path = output / relative;original = path.read_bytes()
        try:
            path.write_bytes(change(original));reuse.validate_payload(output, source)
        finally:
            path.write_bytes(original)
    def json_change(data, change):
        value = json.loads(data);change(value);return (json.dumps(value) + '\n').encode()
    check('APK byte mutation refused', lambda: mutate(reuse.APKS['arm64-v8a'][0], lambda b:b[:-1] + bytes([b[-1] ^ 1])), True)
    check('APK source receipt substitution refused', lambda: mutate('arm64-package.json', lambda b:json_change(b, lambda v:v.update(source_commit='0' * 40))), True)
    check('APK native ELF omission refused', lambda: mutate('arm64-package.json', lambda b:json_change(b, lambda v:v['native_libraries'].pop(next(iter(v['native_libraries']))))), True)
    check('Android UDP binary mutation refused', lambda: mutate('host/local-android/coh-local-x86_64', lambda b:b[:-1] + bytes([b[-1] ^ 1])), True)
    check('Android UI peer binary mutation refused', lambda: mutate('host/local-android/coh-local-peer-x86_64', lambda b:b[:-1] + bytes([b[-1] ^ 1])), True)
    check('Android Map binary mutation refused', lambda: mutate('host/map-android/x86_64/test_mapclient_android', lambda b:b[:-1] + bytes([b[-1] ^ 1])), True)
    check('generated GROUPS header mutation refused', lambda: mutate('host/map-android/groups-fixtures.h', lambda b:b + b'\n'), True)
    check('generated command header mutation refused', lambda: mutate('host/map-android/server-command-fixtures.h', lambda b:b + b'\n'), True)
    def source_pin(value):value['implementation_sha256'][next(iter(value['implementation_sha256']))] = '0' * 64
    check('archived source pin mutation refused', lambda: mutate('host/local-protocol.json', lambda b:json_change(b, source_pin)), True)
    check('per-ABI Map receipt mutation refused', lambda: mutate('host/map-android/x86_64/receipt.json', lambda b:json_change(b, lambda v:v.update(binary_sha256='0' * 64))), True)
    check('missing Android UI peer ABI refused', lambda: mutate('host/local-android/android-build.json', lambda b:json_change(b, lambda v:v['scripted_ui_peer_artifacts'].pop())), True)
    check('all real payloads restored and admitted', lambda: reuse.validate_payload(output, source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-reuse-017-controls-') as temp:
        directory = Path(temp);zip_controls();source_controls(directory)
        if args.archive:payload_controls(args.archive, args.source_root.resolve(), directory)
    print(json.dumps(dict(status='passed', checks=len(checks), real_artifact_checked=bool(args.archive),
        rebuilt=False, cases=checks), indent=2))


if __name__ == '__main__':
    main()

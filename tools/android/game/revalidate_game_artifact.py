#!/usr/bin/env python3
"""Replay validation of the immutable completed Atlas run; never rerun or edit it."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile

import host_game_smoke as host

RUN_ID = 36424870915
ARTIFACT_ID = 10973022843
ARCHIVE_BYTES = 8984584
ARCHIVE_SHA256 = 'a539817527900628ed3387a7384fa230fd9dcaa9964b5373780d54b2b4210ee3'
RUNTIME_COMMIT = 'f756f50b708cfd2307f460946918d1c24c36e0af'
# Independently verified accepted M2 runtime input, unchanged by this game run.
RUNTIME_LOCK_SHA256 = '025e9bf55b214be4ff4709ec917ba326648a78feae8e97cd0131b72adca4f760'
DATA_MANIFEST_SHA256 = 'b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4'
SCHEMA_MANIFEST_SHA256 = 'b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92'
RUNTIME_MANIFEST_SHA256 = 'fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203'
RUNTIME_EXECUTABLES = ('DbServer.exe', 'MapServer.exe', 'TestClientCreate.exe',
                       'TestClientResume.exe', 'TestClientBridge.exe')
# Historical pins stay independent of a later diagnostic package's donors.
RUNTIME_DONORS = {
    'reference': {'run_id': 36088012664, 'repository_commit': '775a0dd770adac045484805dbbb5f68054c7a354',
                  'manifest_sha256': 'a498eeb9c92299d44a748d08e720cd2e8aeacca0631129182a766ed00ff98952'},
    'dbserver': {'run_id': 36369485666, 'repository_commit': '1a5eea159172a4698441eb8cfed5ea5ca99fcf12',
                 'manifest_sha256': '2dee0ef37aaaab5666c868393dfdba7bcfd1520b4aa1bffe9d565632cfd9327b'},
    'resume': {'run_id': 36297542986, 'repository_commit': '5f2c561058a186de59d3f27301eea210bd4bb66d',
               'manifest_sha256': '299b908e42abd3164d85e75b96122c3a61bfb1d33055e0967ccfe3f891ab7048'},
}
BRIDGE_SOURCES = {
    'database/wine-game/TestClientBridge.c': 'ce7f07eb903c885eb2b24e8e396a86decc92579d96632dc3d69b6153752b634c',
    'database/wine-game/bridge_protocol.h': 'e75cf3827808c1c0717455915f248e37b0872e8db191b933143f3f0e6e61b36f',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(folder, limits):
    records = {}
    for path in folder.iterdir():
        host.require(path.name in limits and path.is_file() and not path.is_symlink(),
                     'Unexpected capture member')
        data = path.read_bytes()
        host.require(len(data) <= limits[path.name], 'Capture exceeds original bound')
        records[path.name] = {'bytes': len(data), 'sha256': sha(data)}
    return records


def revalidate(archive):
    host.require(archive.is_file() and not archive.is_symlink()
                 and archive.stat().st_size == ARCHIVE_BYTES and host.digest(archive) == ARCHIVE_SHA256,
                 'Original GitHub artifact identity differs')
    with zipfile.ZipFile(archive) as source, tempfile.TemporaryDirectory(prefix='coh-atlas-replay-') as temporary:
        members = source.infolist()
        names = [item.filename for item in members]
        host.require(len(names) == len(set(names)) == 37
                     and sum(item.file_size for item in members) < 80 * 1024 * 1024,
                     'Artifact inventory differs or exceeds bound')
        evidence = Path(temporary)
        for item in members:
            path = PurePosixPath(item.filename)
            host.require(not path.is_absolute() and '..' not in path.parts
                         and path.as_posix() == item.filename and '\\' not in item.filename
                         and not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
                         and not item.flag_bits & 1 and item.file_size <= 40 * 1024 * 1024,
                         'Invalid archived file')
            if path.parts[:2] == ('android', 'game-evidence'):
                target = evidence.joinpath(*path.parts[2:])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(item))

        package_raw = source.read('wine-game/game-package.json')
        data_raw = source.read('game-data/game-data-manifest.json')
        schema_raw = source.read('dbserver-schema/schema-manifest.json')
        host.require(sha(data_raw) == DATA_MANIFEST_SHA256 and sha(schema_raw) == SCHEMA_MANIFEST_SHA256,
                     'Previously accepted data or schema manifest differs')
        package, schema = json.loads(package_raw), json.loads(schema_raw)
        host.require(package['repository_commit'] == RUNTIME_COMMIT,
                     'Runtime package is from another commit')
        for role, pin in RUNTIME_DONORS.items():
            host.require(all(package['inputs'][role][key] == pin[key]
                             for key in ('run_id', 'repository_commit', 'manifest_sha256')),
                         'Runtime donor differs: ' + role)
        bridge = package['inputs']['bridge']['manifest']
        host.require(bridge == json.loads(source.read('bridge/bridge-build.json'))
                     and bridge['repository_commit'] == RUNTIME_COMMIT,
                     'Captured bridge build identity differs')
        host.require(bridge['sources_sha256_lf'] == BRIDGE_SOURCES,
                     'Reviewed format-1 bridge producer identity differs')

        expected = {'inputs': {
            'runtime_manifest_sha256': RUNTIME_MANIFEST_SHA256,
            'game_package_sha256': sha(package_raw), 'game_data_manifest_sha256': sha(data_raw),
            'schema_manifest_sha256': sha(schema_raw), 'repository_commit': RUNTIME_COMMIT,
            'source_commit': host.dbhost.SOURCE_COMMIT, 'data_commit': host.dbhost.DATA_COMMIT,
            'binary_sha256': {name: package['files'][name]['sha256'] for name in RUNTIME_EXECUTABLES}},
            'schema': host.dbhost.schema_expectations(schema), 'runtime_lock_sha256': RUNTIME_LOCK_SHA256}
        report_path = evidence / 'game-runtime-report.json'
        report = host.read_json(report_path)
        captures = inventory(evidence / 'game-captures', host.CAPTURE_LIMITS)
        services = inventory(evidence / 'game-service-captures', host.SERVICE_CAPTURE_LIMITS)
        host.validate_report(report, expected=expected)
        host.validate_capture_files(report, evidence, captures)
        host.validate_service_captures(report, evidence, services)
        game = report['game']
        sources = ('tools/android/game/revalidate_game_artifact.py', 'tools/android/game/host_game_smoke.py',
                   'tools/android/dbserver/host_dbserver_smoke.py')
        return {'format': 1, 'status': 'passed', 'kind': 'immutable_completed_runtime_evidence_revalidation',
                'runtime_run_id': RUN_ID, 'runtime_repository_commit': RUNTIME_COMMIT,
                'original_workflow_conclusion': 'failure',
                'original_host_error': 'Validator required child_exited, absent from the format-1 bridge producer',
                'correction': 'Require a verified uint32 child_exit_code, excluding STILL_ACTIVE (259); retain all identity, save, capture and cleanup checks',
                'runtime_reexecuted': False, 'runtime_evidence_modified': False,
                'artifact': {'id': ARTIFACT_ID, 'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
                'raw_report': {'bytes': report_path.stat().st_size, 'sha256': host.digest(report_path)},
                'validator_repository_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=host.ROOT, text=True).strip(),
                'validator_worktree_clean': not subprocess.check_output(['git', 'status', '--porcelain', '--', *sources], cwd=host.ROOT, text=True).strip(),
                'validator_sources_sha256': {name: host.digest(host.ROOT / name) for name in sources},
                'reviewed_bridge_sources_sha256_lf': BRIDGE_SOURCES,
                'passed_runtime_stages': [item['stage'] for item in report['stages']],
                'process_captures': len(report['processes']), 'character': game['character'],
                'first_save': game['first_save'], 'restart': game['restart'],
                'resume': game['resume'], 'second_save': game['second_save'],
                'cleanup_complete': report['cleanup_complete'], 'owned_cleanup': report['wine_process_cleanup'],
                'game_capture_files': captures, 'service_capture_files': services,
                'android_execution_validated': False, 'gameplay_validated': False,
                'scope': 'Hosted ARM64 Wine/FEX Atlas creation, live influence, committed protocol saves and same-character restart/resume; startup reliability and Android gameplay remain separate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    receipt = revalidate(args.archive)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')
    print('PASS: unchanged Atlas run 36424870915; 18 runtime stages, both saves, restart/resume and complete cleanup')


if __name__ == '__main__':
    main()

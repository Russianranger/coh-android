#!/usr/bin/env python3
"""Assemble an explicitly composite Wine game runtime from accepted immutable donors."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/android/dbserver'))
from package_reference_runtime import file_record, dependency_report, require
from package_dbserver import record
from package_resume_client import verify_resume_client_package

SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
PINS = {
    'reference': ('docs/reference-runtime-evidence/build-36088012664.json', 'build-info.json', 36088012664),
    'dbserver': ('docs/android-evidence/dbserver-package-36451873322.json', 'package-manifest.json', 36451873322),
    'resume': ('docs/postgresql-evidence/resume-testclient-build-36297542986.json', 'build-info.json', 36297542986),
}
LOOPBACK_DBSERVER_PIN = ('docs/android-evidence/dbserver-package-36460867428.json',
                       'package-manifest.json', 36460867428)
DBSERVER_PROFILES = ('accepted', 'loopback')
BRIDGE_SOURCES = ('database/wine-game/TestClientBridge.c', 'database/wine-game/bridge_protocol.h')
BRIDGE_FLAGS = '/nologo /W4 /O2 /MT /D_WIN32_WINNT=0x0601'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(root=ROOT):
    return {name: hashlib.sha256((root / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for name in BRIDGE_SOURCES}


def new_output(path):
    require(not path.exists() and not path.is_symlink(), 'Output must be a new directory')


def bridge_receipt(directory, commit):
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'Invalid repository commit')
    value = {'format': 1, 'role': 'stock_testclient_launcher_bridge', 'repository_commit': commit,
             'architecture': 'Win32', 'compiler': 'MSVC', 'flags': BRIDGE_FLAGS,
             'sources_sha256_lf': source_hashes(), 'files': {'TestClientBridge.exe': record(directory / 'TestClientBridge.exe')}}
    require(value['files']['TestClientBridge.exe']['pe_machine'] == 0x14c, 'Bridge must be PE32')
    (directory / 'bridge-build.json').write_text(json.dumps(value, indent=2) + '\n')
    return value


def verified_donor(directory, kind, *, dbserver_profile='accepted'):
    require(dbserver_profile in DBSERVER_PROFILES, 'Unknown DbServer profile')
    accepted_name, manifest_name, run_id = (LOOPBACK_DBSERVER_PIN
        if kind == 'dbserver' and dbserver_profile == 'loopback' else PINS[kind])
    manifest_path = directory / manifest_name
    require(manifest_path.is_file() and not manifest_path.is_symlink(), 'Missing donor manifest: ' + kind)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    accepted = json.loads((ROOT / accepted_name).read_text(encoding='utf-8-sig'))
    require(manifest == accepted, 'Donor differs from accepted receipt: ' + kind)
    require(manifest['source_commit'] == SOURCE, 'Donor source pin differs')
    if kind == 'dbserver':
        require(manifest['variants']['normal']['postgresql_persistence_fixture'] is False,
                'Normal DbServer fixture must be disabled')
        records = manifest['variants']['normal']['files']
        folder = directory / 'normal'
        get_record = record
    else:
        require(manifest['postgresql_persistence_fixture'] is False, 'Donor fixture must be disabled')
        records = manifest['files']
        folder = directory
        get_record = file_record
    actual_pe = {p.name for p in folder.iterdir() if p.suffix.lower() in ('.dll', '.exe')}
    expected_pe = {name for name in records if Path(name).suffix.lower() in ('.dll', '.exe')}
    require(actual_pe == expected_pe, 'Unexpected donor executable/DLL payload: ' + kind)
    for name, expected in records.items():
        path = folder / name
        require(path.is_file() and not path.is_symlink() and path.parent == folder,
                'Invalid donor payload: ' + name)
        require(get_record(path) == expected, 'Donor bytes or PE metadata differ: ' + kind + '/' + name)
    provenance = {'run_id': run_id, 'repository_commit': manifest['repository_commit'],
                  'manifest_sha256': sha(manifest_path), 'manifest': manifest}
    return manifest, folder, provenance


def choose_files(reference_dir, normal_dir):
    """Keep the proven normal Wine CrashRpt; record rather than hide DLL collisions."""
    chosen = {p.name: (p, 'reference') for p in reference_dir.iterdir() if p.suffix.lower() == '.dll'}
    chosen['MapServer.exe'] = (reference_dir / 'MapServer.exe', 'reference')
    chosen['TestClientCreate.exe'] = (reference_dir / 'TestClient.exe', 'reference')
    collisions = {}
    for p in normal_dir.iterdir():
        if p.suffix.lower() not in ('.dll', '.exe'):
            continue
        if p.name in chosen:
            old = chosen[p.name][0]
            collisions[p.name] = {'reference_sha256': sha(old), 'dbserver_sha256': sha(p),
                                  'selected': 'dbserver', 'reason': 'Preserve accepted Wine normal dependency closure'}
        chosen[p.name] = (p, 'dbserver')
    return chosen, collisions


def assemble(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Invalid repository commit')
    new_output(args.output)
    ref, ref_dir, ref_proof = verified_donor(args.reference, 'reference')
    profile = getattr(args, 'dbserver_profile', 'accepted')
    db, normal_dir, db_proof = verified_donor(args.dbserver, 'dbserver', dbserver_profile=profile)
    resume, resume_dir, resume_proof = verified_donor(args.resume, 'resume')
    resume_exe, _ = verify_resume_client_package(args.resume, resume['repository_commit'], ref)
    bridge_path = args.bridge / 'bridge-build.json'
    bridge = json.loads(bridge_path.read_text())
    require(bridge.get('format') == 1 and bridge.get('role') == 'stock_testclient_launcher_bridge', 'Wrong bridge role')
    require(bridge.get('repository_commit') == args.repository_commit and bridge.get('architecture') == 'Win32', 'Bridge commit/architecture differs')
    require(bridge.get('sources_sha256_lf') == source_hashes() and bridge.get('flags') == BRIDGE_FLAGS,
            'Bridge source or build flags differ')
    require(bridge.get('files') == {'TestClientBridge.exe': record(args.bridge / 'TestClientBridge.exe')}, 'Bridge bytes differ')
    chosen, collisions = choose_files(ref_dir, normal_dir)
    chosen['TestClientResume.exe'] = (resume_exe, 'resume')
    chosen['TestClientBridge.exe'] = (args.bridge / 'TestClientBridge.exe', 'bridge')
    require(len({name.casefold() for name in chosen}) == len(chosen), 'Case-colliding game payload')
    files = {name: record(path) for name, (path, _) in chosen.items()}
    deps = dependency_report(files)
    require(not deps['unresolved'], 'Unresolved composite imports: ' + str(deps['unresolved']))
    manifest = {'format': 1, 'role': 'wine_game_runtime', 'source_commit': SOURCE, 'data_commit': DATA,
                'repository_commit': args.repository_commit, 'client_version': 'coh-persistence-diagnostic',
                'client_version_source': 'Explicit diagnostic fallback; accepted reference has no patch version',
                'files': files, 'file_donors': {name: donor for name, (_, donor) in chosen.items()},
                'dependency_report': deps, 'dll_collisions': collisions,
                'inputs': {'reference': ref_proof, 'dbserver': db_proof, 'resume': resume_proof,
                           'bridge': {'repository_commit': args.repository_commit, 'manifest_sha256': sha(bridge_path), 'manifest': bridge}},
                'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
                'scope': 'Composite hosted qualification input; not a replacement stock reference package'}
    # Preserve the byte-level shape of accepted packages. The opt-in candidate
    # is a separate composite qualification, never a replacement acceptance.
    if profile == 'loopback':
        manifest['dbserver_profile'] = profile
    try:
        args.output.mkdir(parents=True)
        for name, (path, _) in chosen.items():
            shutil.copyfile(path, args.output / name)
            require(record(args.output / name) == files[name], 'Payload changed while copying')
        (args.output / 'game-package.json').write_text(json.dumps(manifest, indent=2) + '\n')
    except BaseException:
        shutil.rmtree(args.output, ignore_errors=True)
        raise
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    bridge = sub.add_parser('bridge-receipt')
    bridge.add_argument('--directory', type=Path, required=True)
    bridge.add_argument('--repository-commit', required=True)
    package = sub.add_parser('assemble')
    for name in ('reference', 'dbserver', 'resume', 'bridge', 'output'):
        package.add_argument('--' + name, type=Path, required=True)
    package.add_argument('--repository-commit', required=True)
    package.add_argument('--dbserver-profile', choices=DBSERVER_PROFILES, default='accepted',
                         help='Opt into separate hosted qualification of the loopback DbServer donor')
    args = ap.parse_args()
    value = bridge_receipt(args.directory, args.repository_commit) if args.command == 'bridge-receipt' else assemble(args)
    print(json.dumps({'role': value['role'], 'files': len(value['files'])}))


if __name__ == '__main__':
    main()

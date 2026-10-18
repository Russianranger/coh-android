#!/usr/bin/env python3
"""Run exact newly built local-owner UDP contract binary on Android13 emulator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import struct


def native_source_paths(root, tracked):
    paths = set()
    for name in tracked:
        if name and name.decode().startswith('native-android/') and Path(name.decode()).suffix in ('.py', '.c', '.h', '.inc'):
            path = root / name.decode()
            if not path.is_file():
                raise ValueError('tracked native source is missing: ' + name.decode())
            paths.add(path)
    return paths


def source_identity(root):
    root = root.resolve()
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args], timeout=30)
    revision = git('rev-parse', 'HEAD').decode().strip()
    tree = git('rev-parse', 'HEAD^{tree}').decode().strip()
    paths = native_source_paths(root, git('ls-files', '-z').split(b'\0'))
    for relative in ('local/source-pins.json', 'dbclient/source-pins.json', 'mapclient/source-pins.json',
                     'replication/source-pins.json', 'replication/groups-source-pins.json'):
        manifest = root / 'native-android/engine' / relative
        paths.add(manifest)
        for name in json.loads(manifest.read_bytes())['sha256_lf']:
            paths.add(root / name if name.startswith(('upstream/', 'android/'))
                      else root / 'upstream/ouroboros' / name)
    raw = {str(p.relative_to(root)): p.read_bytes() for p in paths}
    entries = git('ls-tree', '-r', '-z', 'HEAD', '--', *sorted(raw)).split(b'\0')
    objects = {}
    for entry in entries:
        if entry:
            meta, name = entry.split(b'\t', 1)
            mode, kind, oid = meta.split()
            if kind != b'blob' or mode not in (b'100644', b'100755'):
                raise ValueError('regular Git source required')
            objects[name.decode()] = oid.decode()
    if set(objects) != set(raw):
        raise ValueError('complete tracked source domain required')
    for name, data in raw.items():
        if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != objects[name]:
            raise ValueError('working source differs from Git: ' + name)
    if git('rev-parse', 'HEAD').decode().strip() != revision:
        raise ValueError('source revision changed')
    return dict(source_revision=revision, source_tree=tree,
                source_sha256={n: hashlib.sha256(b).hexdigest() for n, b in raw.items()})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root):
    proof = json.loads((root / 'host.json').read_bytes())
    if proof.get('passed') is not True or proof.get('controls_only') is not False:
        raise ValueError('full checked-source host proof required')
    identity = source_identity(Path(__file__).resolve().parents[3])
    if any(proof.get(k) != v for k, v in identity.items()):
        raise ValueError('complete current Git source/driver identity required')
    required_helpers = {'native-android/engine/dbclient/check.py', 'native-android/engine/mapclient/check.py',
                        'native-android/engine/replication/check.py', 'native-android/engine/replication/groups_oracle.py',
                        'native-android/tools/protocol_fixture/prepare.py',
                        'native-android/engine/local/run_owned_android.py'}
    helpers = proof.get('checked_helpers')
    if (type(proof.get('source_loader_controls')) is not int or proof['source_loader_controls'] != 5 or
        proof.get('project_helpers_frozen_before_first_import') is not True or
        proof.get('cached_project_bytecode_used') is not False or not isinstance(helpers, list) or
        not required_helpers.issubset(helpers) or any(p not in identity['source_sha256'] for p in helpers)):
        raise ValueError('checked helper execution provenance required')
    integrated = proof['integrated']
    checks = integrated.get('checks')
    implementation = integrated.get('implementation_sha256')
    required_implementation = {'engine/local/coh_local.c', 'engine/local/coh_local.h', 'engine/local/check.py',
                               'engine/local/test_local.c', 'engine/dbclient/coh_db_session.c', 'engine/dbclient/coh_db_account_controls.c',
                               'engine/mapclient/coh_mapclient.c', 'engine/mapclient/coh_mapclient_owned.c'}
    if (integrated.get('passed') is not True or integrated.get('sanitizers') != 'ASan+UBSan' or
        not isinstance(checks, dict) or set(checks) != {'release', 'asan', 'ubsan'} or
        checks['release'] != checks['asan'] or checks['release'] != checks['ubsan'] or
        not isinstance(implementation, dict) or not required_implementation.issubset(implementation) or
        any(identity['source_sha256'].get('native-android/' + n) != h for n, h in implementation.items())):
        raise ValueError('complete passed sanitizer and compiled-source binding required')
    expected = integrated['checks']['release']
    if type(expected.get('checks')) is not int or expected['checks'] <= 0 or type(expected.get('socket_scenarios')) is not int or expected['socket_scenarios'] <= 0:
        raise ValueError('positive native checks and UDP scenarios required')
    fixtures = integrated.get('fixture_sha256')
    if (not isinstance(fixtures, dict) or set(fixtures) != {'fixtures.h', 'groups-fixtures.h', 'server-command-fixtures.h'} or
        any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for v in fixtures.values())):
        raise ValueError('complete generated fixture map required')
    for key in ('passed', 'actual_os_udp', 'full_scripted_db_map_chain',
                'source_layout_peer', 'socket_leak_check'):
        if expected.get(key) is not True:
            raise ValueError('host contract incomplete: ' + key)
    for key in ('real_server_interoperability', 'real_authenticated_session', 'native_live_world'):
        if expected.get(key) is not False:
            raise ValueError('host scope invalid: ' + key)
    build = json.loads((root / 'android/android-build.json').read_bytes())
    rows = build['artifacts']
    if build.get('module') != 'local' or {r['abi'] for r in rows} != {'x86_64', 'arm64-v8a'} or len(rows) != 2:
        raise ValueError('both native ABI builds required')
    if rows != integrated['android']['artifacts']:
        raise ValueError('host and Android receipts disagree')
    selected = None
    for row in rows:
        name = row['file']
        if name != 'coh-local-' + row['abi'] or row.get('built') is not True or row.get('executed') is not False:
            raise ValueError('invalid native build descriptor')
        if row.get('fixture_sha256') != fixtures:
            raise ValueError('ABI fixture/source binding differs')
        path = root / 'android' / name
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < 16 * 1024 * 1024 or sha(path) != row['sha256']:
            raise ValueError('native binary identity differs')
        header = path.read_bytes()[:20]
        if header[:6] != b'\x7fELF\x02\x01' or struct.unpack('<H', header[18:20])[0] != {'x86_64': 62, 'arm64-v8a': 183}[row['abi']]:
            raise ValueError('wrong native ELF ABI')
        if row['abi'] == 'x86_64':
            selected = path
    return selected, expected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--artifacts', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--adb', type=Path)
    ap.add_argument('--serial')
    ap.add_argument('--validate-only', action='store_true')
    a = ap.parse_args()
    if a.output.exists():
        ap.error('fresh output required')
    root = a.artifacts.resolve()
    binary, expected = validate(root)
    proof = dict(passed=False, validation_only=a.validate_only, android_executed=False,
                 physical_thor_accepted=False, real_server=False, encrypted_authentication=False,
                 actor_identity=False, world_authority=False, apk_rebuilt=False,
                 host_sha256=sha(root / 'host.json'), binary_sha256=sha(binary), cleanup_verified=False)
    remote = None
    adb = None
    def run(*args):
        p = subprocess.run([*adb, *map(str, args)], capture_output=True, text=True, timeout=90)
        if p.returncode:
            raise RuntimeError('adb command failed: ' + p.stdout[-1000:] + p.stderr[-1000:])
        return p.stdout.strip()
    try:
        if not a.validate_only:
            if not a.adb or not a.serial:
                raise ValueError('explicit adb and emulator serial required')
            adb = [str(a.adb.resolve()), '-s', a.serial]
            run('wait-for-device')
            if run('shell', 'getprop', 'ro.build.version.sdk') != '33' or run('shell', 'getprop', 'ro.kernel.qemu') != '1':
                raise ValueError('Android13 emulator required')
            if 'x86_64' not in run('shell', 'getprop', 'ro.product.cpu.abilist').split(','):
                raise ValueError('x86_64 emulator required')
            remote = run('shell', 'mktemp', '-d', '/data/local/tmp/coh-owned-local.XXXXXX')
            if not re.fullmatch(r'/data/local/tmp/coh-owned-local\.[A-Za-z0-9]+', remote):
                remote = None
                raise ValueError('unexpected temporary directory')
            destination = remote + '/test'
            run('push', binary, destination)
            if run('shell', 'sha256sum', destination).split()[0] != sha(binary):
                raise ValueError('transferred binary identity differs')
            run('shell', 'chmod', '700', destination)
            actual = json.loads(run('shell', destination))
            if actual != expected:
                raise ValueError('Android and source-qualified host contract results differ')
            proof.update(android_executed=True, android_sdk=33, abi='x86_64', result=actual)
        proof['passed'] = True
    finally:
        try:
            if remote:
                run('shell', 'rm', '-r', remote)
                run('shell', 'test', '!', '-e', remote)
                proof['cleanup_verified'] = True
        except Exception:
            proof['passed'] = False
            raise
        finally:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()

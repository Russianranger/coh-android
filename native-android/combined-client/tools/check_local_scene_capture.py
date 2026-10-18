#!/usr/bin/env python3
"""Build the nonshipping owned local receive observer and test real socket cleanup.

The test peer is source-derived and scripted. It cannot qualify a real MapServer
generation, authentication or world, even though the client uses actual sockets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import subprocess
import tempfile
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NATIVE = ROOT / 'native-android'
RELATIVE = [
    'engine/local/coh_local.c', 'engine/dbclient/coh_dbclient.c',
    'engine/dbclient/coh_db_session.c', 'engine/dbclient/coh_db_account_controls.c', 'engine/mapclient/coh_mapclient.c',
    'engine/mapclient/coh_mapclient_owned.c', 'engine/replication/coh_replication.c',
    'engine/replication/coh_groups.c', 'engine/network/coh_net.c',
    'engine/network/coh_net_frame.c', 'engine/network/coh_net_zip.c',
    'engine/network/coh_net_udp.c', 'engine/auth/coh_auth.c',
    'engine/auth/coh_auth_openssl.c', 'engine/session/coh_session_crypto.c',
    'protocol/coh_protocol.c', 'src/coh_blowfish.c',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    return subprocess.run(list(map(str, command)), capture_output=True, text=True,
                          timeout=120, **kwargs)


def require(command, **kwargs):
    result = run(command, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed\n{result.stdout}\n{result.stderr}')
    return result


def source_module(path):
    # Execute the admitted current source text, never cached project bytecode.
    module = types.ModuleType(path.stem)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def test(binary, peer, work, environment):
    account = work / 'account'
    account.write_text('Fixture\n')
    account.chmod(0o600)
    peer_report = work / 'peer.json'
    process = subprocess.Popen([str(peer), '--serve', '--report', str(peer_report)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env=environment)
    try:
        with selectors.DefaultSelector() as ready:
            ready.register(process.stdout, selectors.EVENT_READ)
            if not ready.select(10):
                raise TimeoutError('scripted peer did not become ready')
            port = json.loads(process.stdout.readline())['db_port']
        output = work / 'captured'
        result = require([binary, port, 0, account, output, 5000, 5, 0, 0], env=environment)
        summary = json.loads(result.stdout)
        assert summary['passed'] is True and summary['opened_sockets'] == summary['closed_sockets'] == 2
        receipt = json.loads((output / 'capture.json').read_text())
        packet = output / 'groups.bin'
        assert receipt['actual_client_loan_verified'] and receipt['selected_dbid_owner_bound']
        assert receipt['cleanup_verified'] and receipt['packet_written_synchronously']
        assert not receipt['packet_copy_retained'] and not receipt['source_generation_admitted']
        assert not receipt['actor_identity_verified'] and not receipt['world_authority']
        assert packet.stat().st_size == receipt['bytes'] > 16384
        assert digest(packet) == receipt['packet_sha256']
        assert receipt['payload_bits'] == receipt['groups_consumed_bits'] == receipt['bytes'] * 8
        assert receipt['post_command_cursor'] == 32 and receipt['byte_aligned'] == 1
        assert receipt['selected_slot'] == 0 and receipt['selected_dbid'] == 17
        assert receipt['db_session_generation'] > 0 and receipt['db_receipt_generation'] > 0
        assert (output.stat().st_mode & 0o777) == 0o700
        assert (packet.stat().st_mode & 0o777) == 0o600
        assert ((output / 'capture.json').stat().st_mode & 0o777) == 0o600
        checks = 19
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        if process.returncode:
            raise RuntimeError('scripted peer failed: ' + stdout + stderr)
    peer_receipt = json.loads(peer_report.read_text())
    assert peer_receipt['closed_sockets'] == 2 and not peer_receipt['failed']
    checks += 1
    # Every failed run owns its directory, deletes only its own provisional files,
    # and leaves no successful binding. Existing destinations remain untouched.
    existing = work / 'existing'
    existing.mkdir()
    sentinel = existing / 'groups.bin'
    sentinel.write_bytes(b'preserve')
    result = run([binary, 1, 0, account, existing, 100, 5, 0, 0], env=environment)
    assert result.returncode == 1 and sentinel.read_bytes() == b'preserve'
    assert json.loads(result.stdout)['opened_sockets'] == 0
    checks += 2
    link = work / 'link'
    link.symlink_to(existing, target_is_directory=True)
    assert run([binary, 1, 0, account, link, 100, 5, 0, 0], env=environment).returncode == 1
    assert sentinel.read_bytes() == b'preserve'
    checks += 2
    for index, raw in enumerate((b'', b'a' * 15, b'a\0b', b'bad name', b'\n')):
        invalid = work / f'invalid-{index}'
        invalid.write_bytes(raw)
        invalid.chmod(0o600)
        destination = work / f'bad-output-{index}'
        assert run([binary, 1, 0, invalid, destination, 100, 5, 0, 0], env=environment).returncode == 2
        assert not destination.exists()
        checks += 2
    account.chmod(0o644)
    assert run([binary, 1, 0, account, work / 'public-account', 100, 5, 0, 0], env=environment).returncode == 2
    account.chmod(0o600)
    checks += 1
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as blackhole:
        blackhole.bind(('127.0.0.1', 0))
        port = blackhole.getsockname()[1]
        destination = work / 'timeout'
        result = run([binary, port, 0, account, destination, 40, 5, 0, 0], env=environment)
        refusal = json.loads(result.stdout)
        assert result.returncode == 1 and not destination.exists()
        assert refusal['opened_sockets'] == refusal['closed_sockets'] == 1
        checks += 2
        destination = work / 'cancelled'
        child = subprocess.Popen(list(map(str, [binary, port, 0, account, destination, 5000, 5, 0, 0])),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
        try:
            blackhole.settimeout(5)
            blackhole.recv(2048)
            # The first datagram may belong to the timed-out run. Wait for this
            # child's directory before signalling; this polls no server state.
            import time
            deadline = time.monotonic() + 5
            while not destination.exists() and time.monotonic() < deadline:
                time.sleep(0.001)
            child.send_signal(signal.SIGTERM)
            stdout, stderr = child.communicate(timeout=5)
            refusal = json.loads(stdout)
            assert child.returncode == 1 and not destination.exists()
            assert refusal['opened_sockets'] == refusal['closed_sockets'] == 1
            checks += 2
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
    return {'passed': True, 'checks': checks, 'scripted_peer_only': True,
            'actual_client_receive_loan': True, 'real_server_capture': False,
            'source_generation_admitted': False, 'world_authority': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('fresh output directory required')
    args.output.mkdir(parents=True)
    sources = [NATIVE / p for p in RELATIVE]
    observer = HERE / 'capture_local_scene.c'
    inputs = [observer, Path(__file__), *sources]
    tracked = require(['git', '-C', ROOT, 'ls-files', '-z', 'native-android']).stdout.split('\0')
    inputs.extend(ROOT / path for path in tracked if path and
                  Path(path).suffix in ('.py', '.h', '.c', '.inc', '.json') and
                  not any(part in ('evidence', 'qualification', 'diagnostics') for part in Path(path).parts))
    for relative in ('local/source-pins.json', 'dbclient/source-pins.json',
                     'mapclient/source-pins.json', 'replication/source-pins.json',
                     'replication/groups-source-pins.json'):
        manifest = NATIVE / 'engine' / relative
        inputs.append(manifest)
        for path in json.loads(manifest.read_text())['sha256_lf']:
            inputs.append(ROOT / path if path.startswith(('upstream/', 'android/'))
                          else ROOT / 'upstream/ouroboros' / path)
    inputs = sorted(set(inputs))
    pins = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    source_revision = require(['git', '-C', ROOT, 'rev-parse', 'HEAD']).stdout.strip()
    checkout_state = require(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=normal']).stdout
    results = {}
    modes = [('release', ['-O2'])]
    if args.sanitize:
        modes += [('address', ['-O1', '-g', '-fsanitize=address', '-no-pie']),
                  ('undefined', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
    with tempfile.TemporaryDirectory(prefix='coh-local-capture-') as temp:
        work = Path(temp)
        if args.test:
            db = source_module(NATIVE / 'engine/dbclient/check.py')
            oracle, _ = db.oracle(ROOT, work)
            db.fixtures(oracle, work)
            maps = source_module(NATIVE / 'engine/mapclient/check.py')
            maps.command_fixtures(ROOT, work)
            maps.groups_fixtures(ROOT, work)
        environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for label, options in modes:
            flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', *options,
                     '-I' + str(NATIVE / 'include'), '-I' + str(work)]
            objects = []
            for index, source in enumerate(sources):
                target = work / f'{label}-{index}.o'
                # Preserve original protocol integer/bitcast qualification flags.
                original_flags = ['-O0'] if source.name in ('coh_protocol.c', 'coh_blowfish.c') else []
                require(['cc', *flags, *original_flags, '-c', source, '-o', target])
                objects.append(target)
            binary = args.output.resolve() / ('coh-capture-local-scene' + ('' if label == 'release' else '-' + label))
            require(['cc', *flags, observer, *objects, '-lz', '-lm', '-lcrypto', '-o', binary])
            results[label] = {'binary': binary.name, 'sha256': digest(binary), 'built': True}
            if args.test:
                peer = work / ('peer-' + label)
                require(['cc', *flags, NATIVE / 'engine/local/test_ui_peer.c', *objects,
                         '-lz', '-lm', '-lcrypto', '-o', peer])
                mode_work = work / label
                mode_work.mkdir()
                results[label]['tests'] = test(binary, peer, mode_work, environment)
    assert pins == {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    assert require(['git', '-C', ROOT, 'rev-parse', 'HEAD']).stdout.strip() == source_revision
    proof = {'schema': 'coh-local-scene-capture-build-v1', 'passed': True,
             'source_revision': source_revision,
             'source_dirty_at_start': bool(checkout_state), 'source_checkout_state_at_start': checkout_state,
             'source_hashes_authoritative_for_build_bytes': True,
             'source_sha256': pins, 'modes': results,
             'android_built': False, 'android_executed': False,
             'real_server_capture': False, 'source_generation_admitted': False,
             'actor_identity_verified': False, 'world_authority': False}
    (args.output / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': results}))


if __name__ == '__main__':
    main()

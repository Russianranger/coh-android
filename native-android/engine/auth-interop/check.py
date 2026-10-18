#!/usr/bin/env python3
"""Strict deployment admission and redaction; never real-auth acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from source_oracle import qualify as source_oracle
from probe_test import qualify as probe_test

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError('Qualification command failed:\n' + result.stdout + result.stderr)
    return result.stdout

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--crypto-root', type=Path, help='Reserved for full Android probe linkage; admission suite needs no crypto')
    parser.add_argument('--android-output', type=Path)
    parser.add_argument('--probe-output', type=Path, help='Opt-in full real-module host probe build; performs no connection')
    args = parser.parse_args()
    native = args.source_root.resolve() / 'native-android'
    pins = json.loads((HERE / 'source-pins.json').read_text())
    for path, expected in pins['sha256_lf'].items():
        content = (args.source_root / path).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Auth/DB source policy changed: ' + path)
    sources = [HERE / 'coh_auth_interop.c', HERE / 'tests/test_auth_interop.c']
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-I' + str(native / 'include')]
    proof = {'schema': 'coh-auth-interop-qualification-v1', 'passed': True, 'checks': {}, 'android': {},
             'source_policy_verified': True, 'source_pins_sha256': sha(HERE / 'source-pins.json'),
             'real_account_login_verified': False, 'native_live_world': False, 'physical_thor_accepted': False,
             'scope': 'Strict encrypted deployment admission and redaction only; no network connections from tests.'}
    with tempfile.TemporaryDirectory(prefix='coh-auth-interop-') as temporary:
        temporary = Path(temporary)
        proof['original_source_oracle'] = source_oracle(args.source_root.resolve(), temporary)
        modes = [('release', ['-O2'])]
        if args.sanitize:
            modes.append(('asan_ubsan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']))
        for mode, extra in modes:
            binary = temporary / mode
            run(['cc', *flags, *extra, *sources, '-o', binary])
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
            proof['checks'][mode] = json.loads(run([binary], env=env))
        if args.probe_output:
            dependencies = ['engine/live/coh_live.c', 'engine/login/coh_login.c', 'engine/dbclient/coh_dbclient.c',
                            'engine/dbclient/coh_db_session.c', 'engine/dbclient/coh_db_account_controls.c', 'engine/mapclient/coh_mapclient.c',
                            'engine/replication/coh_replication.c', 'engine/replication/coh_groups.c',
                            'engine/network/coh_net.c', 'engine/network/coh_net_frame.c', 'engine/network/coh_net_zip.c',
                            'engine/network/coh_net_udp.c', 'engine/session/coh_session_crypto.c',
                            'engine/auth/coh_auth.c', 'engine/auth/coh_auth_openssl.c',
                            'protocol/coh_protocol.c', 'src/coh_blowfish.c']
            args.probe_output.parent.mkdir(parents=True, exist_ok=True)
            probe_flags = ['-O1'] + (['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie'] if args.sanitize else [])
            run(['cc', *flags, *probe_flags, HERE / 'coh_auth_interop.c', HERE / 'probe.c',
                 *[native / name for name in dependencies], '-lcrypto', '-lz', '-lm', '-o', args.probe_output])
            proof['probe_lifecycle'] = probe_test(args.probe_output.resolve())
            proof['host_probe'] = {'built': True, 'sha256': sha(args.probe_output), 'executed': True, 'execution_scope': 'isolated TCP no-success lifecycle only',
                                   'source_sha256': {name: sha(native / name) for name in dependencies}}
        if args.ndk:
            if not args.android_output:
                parser.error('--ndk requires --android-output')
            toolchain = args.ndk.resolve() / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
            for abi, triple in [('arm64-v8a', 'aarch64'), ('x86_64', 'x86_64')]:
                out = args.android_output.resolve() / abi
                out.mkdir(parents=True, exist_ok=True)
                binary = out / 'test_auth_interop'
                run([toolchain / (triple + '-linux-android26-clang'), *flags, '-O2', *sources, '-o', binary])
                receipt = {'passed': True, 'abi': abi, 'binary': binary.name, 'binary_sha256': sha(binary),
                           'executed': False, 'policy_only': True, 'real_account_login_verified': False,
                           'source_sha256': {str(path.relative_to(native)): sha(path) for path in sources}}
                (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
                proof['android'][abi] = receipt
    proof['source_sha256'] = {str(path.relative_to(native)): sha(path) for path in [*sources, HERE / 'coh_auth_interop.h', HERE / 'probe.c', HERE / 'check.py', HERE / 'source_oracle.py', HERE / 'probe_test.py', HERE / 'run.py']}
    proof['sanitizers'] = 'ASan+UBSan; LeakSanitizer not claimed' if args.sanitize else 'not requested'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks': proof['checks'], 'android_built': list(proof['android'])}))

if __name__ == '__main__':
    main()

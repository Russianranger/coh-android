#!/usr/bin/env python3
"""Qualify isolated source-pinned receive-offset candidate; no live login claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import receive_candidate as candidate
from source_audit import decoded, extract

HERE = Path(__file__).resolve().parent


def qualify(root, output):
    originals = candidate.sources(root)
    patched = candidate.replace_offset(originals[candidate.SOCKET])
    functions = {'CSocketServerEx::OnRead': extract(decoded(patched), 'CSocketServerEx::OnRead'),
                 'CIOSocket::Read': extract(decoded(originals[candidate.IO]), 'CIOSocket::Read')}
    fixture = (HERE / 'candidate_receive_fixture.cpp').read_text()
    code = fixture.replace('/* EXACT_ORIGINAL_FUNCTIONS */', '\n'.join(functions.values()))
    executions = {}
    with tempfile.TemporaryDirectory(prefix='coh-receive-candidate-') as temporary:
        directory = Path(temporary)
        generated = directory / 'candidate.cpp'
        generated.write_text(code)
        for mode in ('release', 'asan_ubsan'):
            binary = directory / mode
            flags = ['-O2'] if mode == 'release' else ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
            result = subprocess.run(['c++', '-std=c++17', *flags, generated, '-o', binary], capture_output=True, timeout=60)
            if result.returncode:
                raise ValueError('candidate_compile_failed:' + result.stderr.decode()[:3000])
            result = subprocess.run([binary], capture_output=True, timeout=30,
                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:
                raise ValueError('candidate_control_failed:' + result.stderr.decode()[:3000])
            value = json.loads(result.stdout)
            if not (value['passed'] and value['all_body_splits'] == 169 and value['send_caps'] == 170 and value['random_schedules'] == 100):
                raise ValueError('candidate_result_mismatch')
            executions[mode] = {'binary_sha256': candidate.digest(binary.read_bytes()), 'result': value}
        boundary_fixture = (HERE / 'boundary_receive_fixture.cpp').read_text()
        boundary_code = boundary_fixture.replace('/* EXACT_ORIGINAL_FUNCTIONS */', '\n'.join(functions.values()))
        boundary_cpp = directory / 'boundary.cpp'
        boundary_cpp.write_text(boundary_code)
        boundary_results = {}
        for mode in ('release', 'asan_ubsan'):
            binary = directory / ('boundary-' + mode)
            flags = ['-O2'] if mode == 'release' else ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
            subprocess.run(['c++', '-std=c++17', *flags, boundary_cpp, '-o', binary], check=True, capture_output=True, timeout=60)
            result = subprocess.run([binary], capture_output=True, timeout=30,
                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:
                raise ValueError('candidate_boundary_failed:' + result.stderr.decode()[:3000])
            value = json.loads(result.stdout)
            if not (value['passed'] and value['minimum_body'] == 1 and value['maximum_body'] == 4096 and value['stateful_decoder_observer']):
                raise ValueError('candidate_boundary_result_mismatch')
            boundary_results[mode] = {'binary_sha256': candidate.digest(binary.read_bytes()), 'result': value}
        # A regression control must fail against the original defective function.
        original_code = fixture.replace('/* EXACT_ORIGINAL_FUNCTIONS */', '\n'.join([
            extract(decoded(originals[candidate.SOCKET]), 'CSocketServerEx::OnRead'),
            functions['CIOSocket::Read']]))
        original_cpp, original_binary = directory / 'original.cpp', directory / 'original'
        original_cpp.write_text(original_code)
        subprocess.run(['c++', '-std=c++17', '-O2', original_cpp, '-o', original_binary], check=True, capture_output=True, timeout=60)
        regression = subprocess.run([original_binary], capture_output=True, timeout=30)
        if regression.returncode != 1 or b'check failed at' not in regression.stderr:
            raise ValueError('original_regression_not_reproduced')
        # Exact-source admission rejects changed sources and repeat application.
        for data in (b'', patched, originals[candidate.SOCKET] + b'\n', originals[candidate.SOCKET].replace(candidate.BEFORE, candidate.BEFORE + b' ')):
            try:
                candidate.replace_offset(data)
            except ValueError:
                continue
            raise ValueError('candidate_mutation_admitted')
        staged = candidate.prepare(root, directory / 'staged')
        if (directory / 'staged' / 'SocketServerEx.cpp').read_bytes() != patched:
            raise ValueError('candidate_stage_mismatch')
    proof = {'schema': 'coh-authserver-receive-candidate-qualification-v1', 'passed': True,
        'original_source_tree': candidate.ORIGINAL_TREE,
        'original_source_sha256': {path: candidate.digest(data) for path, data in originals.items()},
        'candidate_source_sha256': candidate.digest(patched),
        'candidate_manifest': staged, 'executions': executions,
        'boundary_executions': boundary_results, 'boundary_fixture_sha256': candidate.digest(boundary_fixture.encode()),
        'qualifier_sha256': candidate.digest(Path(__file__).read_bytes()),
        'fixture_sha256': candidate.digest(fixture.encode()), 'generated_oracle_sha256': candidate.digest(code.encode()),
        'source_mutation_rejections': 4, 'original_defect_regression_reproduced': True,
        'scope': 'Exact candidate OnRead and unchanged original Read, opaque byte-boundary decoder and platform fixtures. Includes arbitrary partial and coalesced delivery, incomplete input, invalid lengths, corrupt body and invalid opcode refusal. No account/password or cryptographic execution.',
        'original_service_changed': False, 'patched_authserver_windows_built': False,
        'encrypted_account_login_verified': False, 'wrong_password_service_verified': False,
        'missing_account_service_verified': False, 'general_tcp_segmentation_accepted': False,
        'leak_sanitizer_enabled': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = qualify(args.source_root.resolve(), args.output)
    print(json.dumps({'passed': proof['passed'], 'checks_per_mode': proof['executions']['release']['result']['checks'],
        'encrypted_account_login_verified': False}))

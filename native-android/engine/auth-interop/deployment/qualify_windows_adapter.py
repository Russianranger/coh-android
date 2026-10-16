#!/usr/bin/env python3
"""Host syscall-shell controls; Windows execution is a separate gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def qualify(sanitize=False):
    source = HERE / 'windows'
    inputs = [source / name for name in ('winsock_compat.h', 'winsock_compat.c', 'test_winsock_api.h', 'test_winsock_compat.c')]
    results = {}
    with tempfile.TemporaryDirectory(prefix='coh-winsock-controls-') as temporary:
        for mode in (('release', 'asan_ubsan') if sanitize else ('release',)):
            binary = Path(temporary) / mode
            flags = ['-O2'] if mode == 'release' else ['-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
            command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-DCOH_WINSOCK_TEST', *flags,
                       str(source / 'winsock_compat.c'), str(source / 'test_winsock_compat.c'), '-o', str(binary)]
            subprocess.run(command, check=True, capture_output=True, timeout=90)
            result = subprocess.run([binary], check=True, capture_output=True, timeout=30,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1'))
            value = json.loads(result.stdout)
            if value != {'passed': True, 'checks': 46, 'real_windows_execution': False, 'real_account_login_verified': False}:
                raise ValueError('adapter_control_result_mismatch')
            results[mode] = {'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'result': value}
    return {'schema': 'coh-winsock-adapter-host-v1', 'passed': True, 'executions': results,
            'inputs_sha256': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
            'real_windows_execution': False, 'real_account_login_verified': False, 'leak_sanitizer_enabled': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.sanitize)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks_per_execution': 46, 'real_windows_execution': False}))

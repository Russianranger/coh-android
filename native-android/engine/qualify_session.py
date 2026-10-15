#!/usr/bin/env python3
"""Qualify the opt-in session modules, their crypto bridge and combined ABI.

Independent suites run concurrently. No account, server endpoint, imported
assets or accepted APK is modified. Synthetic peer tests are not server proof.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ENGINE = Path(__file__).resolve().parent
NATIVE = ENGINE.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--audio-codec-root', type=Path)
    parser.add_argument('--audio-asset-root', type=Path)
    args = parser.parse_args()
    if bool(args.audio_codec_root) != bool(args.audio_asset_root):
        parser.error('Authentic audio checking requires both audio corpus directories')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = args.source_root.resolve()
    receipts = []

    def run_suite(module):
        command = [sys.executable, str(ENGINE/module/'check.py'),
                   '--source-root', str(root), '--output', str(output/(module+'.json'))]
        if args.sanitize:
            command += ['--sanitize']
        if module == 'audio':
            if args.audio_codec_root:
                command += ['--codec-root', str(args.audio_codec_root.resolve()),
                            '--asset-root', str(args.audio_asset_root.resolve())]
            else:
                # Clean runners do not possess the recovered proprietary
                # corpus. Require an explicit partial scope instead of
                # accidentally depending on another task's scratch defaults.
                command += ['--no-authentic']
        start = time.monotonic()
        with (output/(module+'.log')).open('w') as log:
            try:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300)
                return {'module': module, 'passed': result.returncode == 0,
                        'exit_code': result.returncode, 'command': command,
                        'elapsed_host_seconds': time.monotonic()-start}
            except subprocess.TimeoutExpired:
                return {'module': module, 'passed': False, 'command': command,
                        'error': 'Exceeded the 300-second module budget'}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(run_suite, module): module
                   for module in ['network', 'auth', 'replication', 'audio']}
        for future in as_completed(futures):
            try:
                item = future.result()
            except Exception as error:
                item = {'module': futures[future], 'passed': False, 'error': str(error)}
            receipts.append(item)
            print(json.dumps(item), flush=True)
    summary = {'schema': 'coh-native-session-continuation-v1',
               'passed': all(item['passed'] for item in receipts),
               'modules': sorted(receipts, key=lambda item: item['module']),
               'android_emulator_qualified': False, 'physical_thor_accepted': False,
               'actual_server_interoperability_verified': False,
               'authenticated_account': False, 'live_world_session': False,
               'accepted_apk_rebuilt': False}
    summary['authentic_audio_corpus_requested'] = bool(args.audio_codec_root)
    try:
        if summary['passed']:
            sources = [ENGINE/p for p in [
                'session/test_contract.c', 'session/coh_session_crypto.c',
                'auth/coh_auth.c', 'auth/coh_auth_openssl.c',
                'network/coh_net.c', 'network/coh_net_frame.c', 'network/coh_net_zip.c',
                'replication/coh_replication.c']]
            sources += [NATIVE/'protocol/coh_protocol.c', NATIVE/'src/coh_blowfish.c']
            command = [os.environ.get('CC', 'cc'), '-std=c11', '-O1', '-g',
                       '-Wall', '-Wextra', '-Werror', '-I'+str(NATIVE/'include'),
                       *map(str, sources), '-lcrypto', '-lz', '-lm',
                       '-o', str(output/'session-contract')]
            env = os.environ.copy()
            if args.sanitize:
                command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-fno-pie', '-no-pie']
                env.update(ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',
                           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            with (output/'session-contract-build.log').open('w') as log:
                subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=60)
            result = subprocess.run([str(output/'session-contract')], check=True,
                                    text=True, capture_output=True, env=env, timeout=60)
            contract = json.loads(result.stdout)
            (output/'session-contract.json').write_text(json.dumps(contract, indent=2)+'\n')
            summary['cross_module_contract'] = contract
            summary['passed'] = summary['passed'] and contract['passed']
            for label, extra in [('combined-host', ['--sanitize'] if args.sanitize else [])] + (
                    [('combined-arm64', ['--ndk', str(args.ndk.resolve())])] if args.ndk else []):
                command = [sys.executable, str(ENGINE/'build.py'), '--output', str(output/label), *extra]
                with (output/(label+'.log')).open('w') as log:
                    subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
                summary[label] = json.loads((output/label/'build-receipt.json').read_text())
            summary['android_arm64_built'] = bool(args.ndk)
            summary['android_crypto_provider_linked'] = False
            summary['crypto_provider_scope'] = 'OpenSSL host backend exercised; portable callback bridge built for Android without a selected crypto backend.'
    except (subprocess.SubprocessError, ValueError, OSError) as error:
        summary['passed'] = False
        summary['integration_error'] = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            (output/'integration-error.log').write_text((error.stdout or '')+(error.stderr or ''))
    summary['source_sha256'] = {
        str(path.relative_to(NATIVE)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ENGINE.rglob('*')) if path.is_file()
        and path.suffix in {'.c', '.h', '.py', '.vert', '.frag'}
    }
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({'passed': summary['passed'],
                      'android_arm64_built': summary.get('android_arm64_built', False),
                      'real_server': False, 'summary': str(output/'summary.json')}))
    raise SystemExit(0 if summary['passed'] else 1)


if __name__ == '__main__':
    main()

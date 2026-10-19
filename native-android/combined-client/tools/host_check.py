#!/usr/bin/env python3
"""Collect independent source/import/local-server contracts for one app batch."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--donor-apk', type=Path, default=PROJECT / '.inputs/COH-Atlas-Gameplay-0.13.36.apk')
    p.add_argument('--ndk', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    ndk = args.ndk
    if not ndk:
        sdk = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
        if sdk:
            ndk = Path(sdk) / 'ndk/28.2.13676358'
    if not ndk or not ndk.is_dir():
        raise ValueError('Pinned NDK28.2.13676358 is required for Android boundary binaries')
    native = args.source_root.resolve() / 'native-android'
    commands = [
        ('framework-driver-controls', [sys.executable, native / 'combined-client/tools/driver_controls.py']),
        ('installed-apk-identity', [sys.executable, native / 'combined-client/qualification/check_apk_identity.py']),
        ('lease-admission', [sys.executable, native / 'combined-client/qualification/check_lease.py']),
        ('guest-diagnostics', [sys.executable, native / 'combined-client/qualification/check_diagnostics.py']),
        ('server-memory-policy', [sys.executable, native / 'combined-client/qualification/check_server_memory.py']),
        ('phase-memory-diagnostics', [sys.executable, native / 'combined-client/qualification/check_phase_memory.py']),
        ('memory-jni', [sys.executable, native / 'combined-client/qualification/check_memory_jni.py']),
        ('viewport-policy', [sys.executable, native / 'combined-client/qualification/check_viewport.py']),
        ('imports', [sys.executable, native / 'combined-client/imports/tests/check_imports.py', '--donor-apk', args.donor_apk.resolve()]),
        ('server-runtime', [sys.executable, native / 'combined-client/runtime/check.py', '--source-root', args.source_root.resolve(), '--donor', args.donor_apk.resolve(), '--output', args.output / 'server-runtime.json']),
        ('network-protocol', [sys.executable, native / 'engine/network/check.py', '--source-root', args.source_root.resolve(), '--sanitize', '--output', args.output / 'network-protocol.json']),
        ('local-protocol', [sys.executable, native / 'engine/local/check.py', '--source-root', args.source_root.resolve(), '--sanitize', '--ndk', ndk.resolve(), '--android-output', args.output / 'local-android', '--output', args.output / 'local-protocol.json']),
        ('db-protocol', [sys.executable, native / 'engine/dbclient/check.py', '--source-root', args.source_root.resolve(), '--sanitize', '--output', args.output / 'db-protocol.json']),
        ('map-protocol', [sys.executable, native / 'engine/mapclient/check.py', '--source-root', args.source_root.resolve(), '--sanitize', '--ndk', ndk.resolve(), '--android-output', args.output / 'map-android', '--output', args.output / 'map-protocol.json']),
        ('replication', [sys.executable, native / 'engine/replication/check.py', '--source-root', args.source_root.resolve(), '--sanitize', '--output', args.output / 'replication.json']),
        ('scene-structure', [sys.executable, native / 'engine/replication/groups_check.py', '--source-root', args.source_root.resolve(), '--sanitize', '--output', args.output / 'scene-structure.json']),
    ]
    results = []
    for name, command in commands:
        command = [str(x) for x in command]
        started = time.monotonic()
        result = subprocess.run(command, cwd=args.source_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
        (args.output / (name + '.log')).write_text(result.stdout)
        item = {'name': name, 'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic()-started, 3), 'command': command}
        results.append(item)
        (args.output / 'progress.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(item), flush=True)
        if result.returncode:
            raise RuntimeError('Host check failed: ' + name + '\n' + result.stdout[-10000:])
    receipt = {'format': 1, 'status': 'passed', 'suites': results, 'scope': 'Source and deterministic host/import/scripted socket contracts; Android execution and actual guest server startup are separate evidence.', 'actual_server_interoperability_verified': False}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()

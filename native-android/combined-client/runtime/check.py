#!/usr/bin/env python3
"""Admission tests and exact donor API audit; never claims an executed server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
DONOR_SHA256 = '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'
REQUIRED_MODULES = ('diagnostic.py', 'dbserver_diagnostic.py', 'game_diagnostic.py',
    'client_startup_diagnostic.py', 'local_login_server.py', 'local_character_server.py',
    'character_zoning.py', 'game_evidence.py')


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for part in iter(lambda: source.read(1024 * 1024), b''):
            value.update(part)
    return value.hexdigest()


def run_tests(directory):
    env = dict(os.environ, COH_COMBINED_GUEST=str(directory))
    result = subprocess.run([sys.executable, str(HERE / 'test_runtime.py')], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
    print(result.stdout, end='')
    if result.returncode:
        raise SystemExit(result.returncode)
    return {'test_methods': 15, 'status': 'passed',
            'stdout_sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=HERE.parents[2])
    parser.add_argument('--donor', type=Path)
    parser.add_argument('--donor-sha256', default=DONOR_SHA256)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = args.source_root.resolve() / 'android' / 'guest'
    record = {'format': 1, 'scope': 'server_only_admission_and_retained_api_contract',
        'actual_server_executed': False, 'actual_login_verified': False,
        'native_world_entry_verified': False, 'test_character_provision_executed': False,
        'source_contract_tests': run_tests(source),
        'source_modules': {name: sha(source / name) for name in REQUIRED_MODULES}}
    if args.donor:
        actual = sha(args.donor)
        if actual != args.donor_sha256:
            raise SystemExit('Donor SHA256 differs')
        with tempfile.TemporaryDirectory(prefix='coh-combined-donor-api-') as temporary:
            folder = Path(temporary)
            with zipfile.ZipFile(args.donor) as archive:
                selected = [entry for entry in archive.infolist()
                            if entry.filename.startswith('assets/runtime/')
                            and entry.filename.endswith(('.py', '.json'))]
                if not 20 <= len(selected) <= 256:
                    raise SystemExit('Donor module inventory differs')
                for entry in selected:
                    if (Path(entry.filename).parent.as_posix() != 'assets/runtime'
                            or entry.file_size > 64 * 1024 * 1024):
                        raise SystemExit('Unsafe donor metadata path')
                    (folder / Path(entry.filename).name).write_bytes(archive.read(entry))
            record['donor'] = {'sha256': actual, 'modules': {
                name: sha(folder / name) for name in REQUIRED_MODULES},
                'contract_tests': run_tests(folder)}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'actual_server_executed': False,
                      'test_methods_per_guest': 15, 'donor_checked': args.donor is not None}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Admission tests and exact donor API audit; never claims an executed server."""
import argparse
import hashlib
import json
import os
import re
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
    summary = re.search(r'(?m)^Ran ([0-9]+) tests? in ', result.stdout)
    if summary is None:
        raise SystemExit('Host test result count is missing')
    count = int(summary[1])
    skipped = re.search(r'(?m)^OK \(skipped=([0-9]+)\)', result.stdout)
    skip_count = int(skipped[1]) if skipped else 0
    return {'test_methods': count, 'passed_methods': count - skip_count,
            'skipped_methods': skip_count, 'status': 'passed',
            'skip_reasons': re.findall(r"(?m)\.\.\. skipped '([^'\n]{1,200})'", result.stdout),
            'stdout_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
            'unix_socket_interruption_test_executed': bool(re.search(
                r'(?m)^test_real_unix_socket_interruption_then_new_session_restart .*\.\.\. ok$', result.stdout)),
            'abrupt_guest_resource_capture_test_executed': bool(re.search(
                r'(?m)^test_guest_resource_event_is_flushed_before_abrupt_guest_exit .*\.\.\. ok$', result.stdout))}


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
        'display_endpoint_policy': 'session_sha256_96bit_private_component_25bytes',
        'legacy_display_endpoints_deleted': False, 'donor_display_guard_weakened': False,
        'guest_resource_scope': 'bounded_self_RSS_and_peak_RSS_observations_only_cgroup_unknown_not_a_cause_verdict',
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
                      'test_methods_per_guest': record['source_contract_tests']['test_methods'], 'donor_checked': args.donor is not None}))


if __name__ == '__main__':
    main()

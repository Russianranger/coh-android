#!/usr/bin/env python3
"""Compare complete stock/candidate identity parsing on a preserved device log.

This is a host CPU benchmark, not a Thor startup measurement. Both paths decode
the same raw bytes every observation and verify the exact same current markers.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_startup_diagnostic as guest


def stock_values(output, marker):
    return [json.loads(line[len(marker):]) for line in output.splitlines()
            if line.startswith(marker)]


def benchmark(raw, iterations=156, rounds=5):
    text = raw.decode('utf-8', 'replace')
    markers = (guest.LAUNCH_MARKER, guest.CONSOLE_MARKER)
    expected = [stock_values(text, marker) for marker in markers]
    if [guest.console_marker_values(text, marker) for marker in markers] != expected:
        raise ValueError('Candidate current-console identities differ from stock')
    results = {'stock_seconds': [], 'candidate_seconds': []}
    for round_number in range(rounds):
        paths = [('stock_seconds', stock_values), ('candidate_seconds', guest.console_marker_values)]
        if round_number % 2:
            paths.reverse()
        for name, parser in paths:
            started = time.perf_counter()
            for _ in range(iterations):
                observed = raw.decode('utf-8', 'replace')
                if [parser(observed, marker) for marker in markers] != expected:
                    raise ValueError('Benchmark identity changed')
            results[name].append(round(time.perf_counter() - started, 6))
    return {'format': 1, 'status': 'passed', 'scope': 'host_complete_console_identity_parsing_only',
        'input': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'lines': len(text.splitlines())},
        'iterations_per_round': iterations, 'rounds': rounds, 'utf8_decode_included_in_both_paths': True,
        'current_identity_values_equal': True, 'candidate_splits_unrelated_lines': False,
        'whole_console_rescanned_each_observation': True, 'identity_cache_added': False,
        **results, 'stock_median_seconds': statistics.median(results['stock_seconds']),
        'candidate_median_seconds': statistics.median(results['candidate_seconds']),
        'physical_client_startup_savings_validated': False,
        'interpretation': 'Measures host parser CPU for repeated observations of the final console; '
            'does not apportion the device observer metric or predict Thor startup savings.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support-zip', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.support_zip) as support:
        if support.getinfo('guest-report.zip').file_size > 160 * 1024 * 1024:
            raise ValueError('Oversized guest report')
        with zipfile.ZipFile(io.BytesIO(support.read('guest-report.zip'))) as guest_zip:
            member = 'client-evidence/client-console.log'
            if guest_zip.getinfo(member).file_size > guest.CLIENT_OUTPUT_LIMIT:
                raise ValueError('Console exceeds existing capture bound')
            raw = guest_zip.read(member)
    receipt = benchmark(raw)
    receipt['support_zip'] = {'name': args.support_zip.name,
        'bytes': args.support_zip.stat().st_size,
        'sha256': hashlib.sha256(args.support_zip.read_bytes()).hexdigest()}
    receipt['source_files'] = {str(path.relative_to(ROOT)): {
        'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in (Path(__file__).resolve(), ROOT / 'android/guest/client_startup_diagnostic.py')}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in
        ('status', 'stock_median_seconds', 'candidate_median_seconds',
         'physical_client_startup_savings_validated')}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Compare the exact previous inventory algorithm against the current helper.

This Linux host fixture measures Python inventory preparation only. It neither
reads client payload headers nor runs Wine, Game, a server or an Android device.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import struct
import subprocess
import tempfile
import time
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
BASELINE = 'af7e6a52926f842044b3115ae4729809df8997a2'
HELPER = 'android/guest/texture_header_index.py'
RECORDS = 11612
IMPORTED = 11367
LOCAL = RECORDS - IMPORTED


class Context:
    def check(self):
        pass

    def event(self, *args, **kwargs):
        pass


def load_helpers():
    previous_source = subprocess.check_output(
        ['git', '-C', str(ROOT), 'show', BASELINE + ':' + HELPER])
    previous = types.ModuleType('previous_texture_inventory')
    exec(compile(previous_source, BASELINE + ':' + HELPER, 'exec'), previous.__dict__)
    spec = importlib.util.spec_from_file_location('current_texture_inventory', ROOT / HELPER)
    current = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(current)
    return {'previous': previous, 'current': current}, {
        'previous': hashlib.sha256(previous_source).hexdigest(),
        'current': hashlib.sha256((ROOT / HELPER).read_bytes()).hexdigest()}


def fixture(root):
    work, imported = root / 'work', root / 'imported'
    folder = work / 'data/texture_library/test'
    folder.mkdir(parents=True)
    imported.mkdir()
    extra = b'texture_library/test/synthetic\0'
    payload = (struct.pack('<IIIIIffB3s', 32 + len(extra), 8, 16, 32,
               0, 0.1, 0.2, 1, b'TX2') + extra + b'original')
    for index in range(RECORDS):
        name = 'leaf-%05d.texture' % index
        path = imported / name if index < IMPORTED else folder / name
        path.write_bytes(payload)
        path.chmod(0o444)
        if index < IMPORTED:
            (folder / name).symlink_to(path)
    client = {'source_data': str(imported)}
    (work / 'client-work.json').write_text(json.dumps(client))
    return work


def resolve_counts(helper, work, expected):
    original = Path.resolve
    calls, leaves = Counter(), Counter()
    def resolve(path, *args, **kwargs):
        calls['all'] += 1
        if path.suffix == '.texture':
            if args or kwargs != {'strict': True}:
                raise AssertionError('Texture leaf resolution stopped being strict')
            leaves[path] += 1
        return original(path, *args, **kwargs)
    with patch.object(Path, 'resolve', resolve):
        actual = helper.texture_inputs(work, Context())
    if actual != expected or len(leaves) != RECORDS or any(count != 1 for count in leaves.values()):
        raise AssertionError('Instrumented inventory differs or skips/repeats a strict leaf')
    return {'all_resolve_calls': calls['all'], 'strict_leaf_calls': sum(leaves.values()),
            'each_leaf_resolved_exactly_once': True}


def benchmark(rounds):
    helpers, sources = load_helpers()
    samples = {name: [] for name in helpers}
    with tempfile.TemporaryDirectory(prefix='coh-texture-inventory-') as name:
        work = fixture(Path(name))
        reference = helpers['previous'].texture_inputs(work, Context())
        comparisons = 0
        for index in range(rounds):
            order = ('previous', 'current') if index % 2 == 0 else ('current', 'previous')
            for name in order:
                started = time.perf_counter()
                result = helpers[name].texture_inputs(work, Context())
                samples[name].append(round(time.perf_counter() - started, 6))
                if result != reference:
                    raise AssertionError('Complete records, metadata hash or client receipt differ')
                comparisons += 1
        counts = {name: resolve_counts(helper, work, reference) for name, helper in helpers.items()}
        inventory_sha = reference[1]
    medians = {name: statistics.median(values) for name, values in samples.items()}
    return {'format': 1, 'scope': 'linux_host_synthetic_texture_inventory_algorithm_comparison',
        'baseline_commit': BASELINE, 'helper_path': HELPER, 'helper_source_sha256': sources,
        'benchmark_script': {'path': Path(__file__).relative_to(ROOT).as_posix(),
                             'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'host': {'system': platform.system(), 'machine': platform.machine(),
                 'python': platform.python_version()},
        'fixture': {'records': RECORDS, 'imported_readonly_symlink_leaves': IMPORTED,
                    'local_readonly_regular_leaves': LOCAL,
                    'synthetic_names_and_payloads': True, 'temporary_fixture_removed': True},
        'rounds': rounds, 'alternating_order': True, 'samples_seconds': samples,
        'median_seconds': medians,
        'median_reduction_percent': round((1 - medians['current'] / medians['previous']) * 100, 3),
        'untimed_resolution_instrumentation': counts,
        'equivalence': {'timed_full_tuple_comparisons': comparisons,
            'all_records_and_inventory_sha256_and_client_receipts_identical': True,
            'fixture_inventory_sha256': inventory_sha,
            'untimed_instrumented_full_tuple_comparisons': len(helpers)},
        'boundaries': {'all_leaf_strict_resolution_preserved': True,
            'readonly_metadata_validation_preserved': True,
            'original_header_payloads_read': False, 'native_decoder_executed': False,
            'game_executed': False, 'server_executed': False,
            'android_or_thor_executed': False, 'physical_startup_savings_validated': False,
            'cache_format_or_identity_schema_changed': False},
        'reproduce': 'python tools/android/interactive/benchmark_texture_inventory.py --rounds 5 --output '
            'docs/android-evidence/client-streaming-0.13.9-texture-benchmark.json'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 3 <= args.rounds <= 20:
        parser.error('rounds must be between 3 and 20')
    result = benchmark(args.rounds)
    encoded = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Independent host experiment; never starts a server or changes production.

Execute exact original text/crash-observation functions against bounded fake
processes. Compare repeated unchanged-output work to an append-only length
memo prototype. No device timing or production readiness claim is made.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time
import types

BASE = 'cda93d96f8696e6a0f2ec6940a0c96e5b852f281'
SOURCES = {
    'android/guest/diagnostic.py': '748975acf9b0c01b094166150112306edfc12c18656bc4b1926e00ea9460dbaf',
    'android/guest/local_character_server.py': '82915cdab3573843c32961478f4e015c27a72e180d75db177e439a081305e180',
}
MAX_OUTPUT = 2 * 1024 * 1024


def original_functions(root):
    bodies, pins = {}, {}
    for path, expected in SOURCES.items():
        raw = subprocess.run(['git', '-C', str(root), 'show', BASE + ':' + path],
            check=True, capture_output=True, timeout=30).stdout
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('SOURCE_IDENTITY')
        tree = ast.parse(raw)
        name = 'text' if path.endswith('/diagnostic.py') else 'map_crash_observation'
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
        if len(nodes) != 1:
            raise ValueError('SOURCE_METHOD_IDENTITY')
        node = nodes[0]
        environment = {'re': re, 'hashlib': hashlib}
        # Original AST node, unchanged; fake self is the only replacement.
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), path, 'exec'), environment)
        bodies[name] = environment[name]
        pins[path] = {'file_sha256': expected, 'method': name,
            'method_source_sha256': hashlib.sha256(ast.get_source_segment(raw.decode(), node).encode()).hexdigest()}
    return bodies, pins


class Original:
    def __init__(self, functions):
        self.output = bytearray()
        self.text = types.MethodType(functions['text'], self)


class AppendMemo:
    """Experiment only: source reader exclusively appends; resets unsupported.

    Cache the full result including its exact console hash/context, so a crash
    marker that gains more suffix text on a later append is always recomputed.
    This saves repeated decoding and scanning, without retaining decoded text.
    Production locking, race/lifetime and deployment qualification remain open.
    """
    def __init__(self, functions):
        self.map_process = Original(functions)
        self.original = types.MethodType(functions['map_crash_observation'], self)
        self.last_length = -1
        self.result = None

    def observe(self):
        length = len(self.map_process.output)
        if length != self.last_length:
            self.result = self.original()
            self.last_length = length
        return self.result


def equivalence(functions):
    cases = [
        [b'normal ', b'output'],
        [b'Program ', b'crash detected', b' with suffix'],
        [b'Exception caught: EXCEPTION_', b'ACCESS_VIOLATION', b' context'],
        [b'normal \xf0\x9f', b'\x8c\x8d', b' Program crash detected'],
        [b'\xff\xfe Program crash detected', b'\xf0', b'\x9f\x8c\x8d'],
        [b'x' * (MAX_OUTPUT - 24), b'Program crash detected', b'overflow not retained'],
    ]
    comparisons = 0
    for chunks in cases:
        memo = AppendMemo(functions)
        for chunk in chunks:
            if len(memo.map_process.output) + len(chunk) <= MAX_OUTPUT:
                memo.map_process.output.extend(chunk)
            for _ in range(3):
                if memo.observe() != memo.original():
                    raise ValueError('EQUIVALENCE_FAILED')
                comparisons += 1
    return {'append_boundary_cases': len(cases), 'exact_result_comparisons': comparisons,
        'utf8_replacement_and_completion_checked': True, 'split_marker_checked': True,
        'source_overflow_drop_policy_checked': True,
        'concurrent_reader_races_qualified': False, 'same_length_mutations_supported': False}


def elapsed(callback, iterations):
    begin = time.perf_counter_ns()
    for _ in range(iterations): callback()
    return (time.perf_counter_ns() - begin) / 1000000


def run(root, iterations=1000, repeats=5):
    if not (1 <= iterations <= 10000 and 1 <= repeats <= 10):
        raise ValueError('BENCHMARK_BOUND')
    functions, pins = original_functions(root)
    proof = equivalence(functions)
    measurements = []
    # 36,503 is the largest retained process output in the accepted current ZIP.
    for size in (36503, 65536, MAX_OUTPUT):
        memo = AppendMemo(functions)
        memo.map_process.output.extend(b'n' * size)
        memo.observe()
        original, candidate = [], []
        for _ in range(repeats):
            original.append(elapsed(memo.original, iterations))
            candidate.append(elapsed(memo.observe, iterations))
        measurements.append({'output_bytes': size, 'polls_per_repeat': iterations,
            'repeats': repeats, 'unchanged_no_crash_output': True,
            'original_ms': original, 'prototype_ms': candidate,
            'original_median_ms': statistics.median(original),
            'prototype_median_ms': statistics.median(candidate),
            'decoded_bytes_avoided_after_initial_observation': size * iterations})
    return {'schema': 'coh-startup-console-host-experiment-v1', 'source_commit': BASE,
        'source_methods': pins, 'host': {'python': platform.python_version(), 'machine': platform.machine()},
        'equivalence': proof, 'measurements': measurements,
        'limits': {'maximum_output_bytes': MAX_OUTPUT, 'maximum_iterations': 10000,
                   'maximum_repeats': 10, 'peak_process_rss_measured': False},
        'scope': {'synthetic_output_only': True, 'original_methods_executed': True,
            'production_modified': False, 'android_or_thor_executed': False,
            'startup_improvement_measured': False, 'deployable_candidate': False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--iterations', type=int, default=1000)
    parser.add_argument('--repeats', type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(run(args.source_root, args.iterations, args.repeats), indent=2, sort_keys=True))


if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Bounded offline analyzer benchmark; never a server/device speed claim."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

import analyze_startup_resources as analysis


def benchmark(path, repeats=5, iterations=10):
    analysis.base.need(type(repeats) is int and 1 <= repeats <= 9 and
                       type(iterations) is int and 1 <= iterations <= 100, 'BENCHMARK_BOUND')
    elapsed, peaks, pins, output_pin = [], [], None, None
    for _ in range(repeats):
        tracemalloc.start()
        try:
            started = time.perf_counter()
            for _ in range(iterations):
                documents, provenance = analysis.base.read_archive(path)
                body = json.dumps(analysis.analyze(documents, provenance), sort_keys=True, allow_nan=False).encode()
                current = {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
                analysis.base.need(pins is None or pins == provenance, 'BENCHMARK_INPUT_CHANGED')
                analysis.base.need(output_pin is None or output_pin == current, 'BENCHMARK_OUTPUT_CHANGED')
                pins, output_pin = provenance, current
                del documents, body
            elapsed.append(round((time.perf_counter() - started) * 1000 / iterations, 6))
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    return {'schema': 'coh-startup-offline-analysis-benchmark-v1', 'repeats': repeats,
        'iterations_per_repeat': iterations, 'input': pins, 'deterministic_output': output_pin,
        'elapsed_ms_per_analysis': elapsed, 'median_elapsed_ms': statistics.median(elapsed),
        'python_traced_peak_bytes_per_repeat': peaks, 'maximum_python_traced_peak_bytes': max(peaks),
        'scope': 'host_archive_read_json_analysis_and_encoding_with_tracemalloc_overhead',
        'whole_process_rss_measured': False, 'device_execution': False,
        'production_startup_speedup_measured': False, 'runtime_modified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export_zip', type=Path)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--iterations', type=int, default=10)
    args = parser.parse_args(argv)
    try:
        result = benchmark(args.export_zip, args.repeats, args.iterations)
    except analysis.base.Rejected as error:
        print(json.dumps({'error': str(error)})); return 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print(json.dumps({'error': 'INPUT_UNAVAILABLE_OR_INVALID'})); return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)); return 0


if __name__ == '__main__': sys.exit(main())

#!/usr/bin/env python3
"""Bounded retry regression against an explicit production candidate checkout.

Only this test and the candidate's NetLink/codec dependencies are compiled. The
shared NEXT build lock covers every compiler invocation; objects build serially.
No source fixtures, APKs, servers, sockets, or retained build outputs are used.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True,
                            timeout=60, **kwargs)
    if result.returncode:
        raise RuntimeError('Command failed: ' + repr(command) + '\n' +
                           result.stdout[-2000:] + result.stderr[-4000:])
    return result.stdout


def fingerprint(paths):
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-root', type=Path, required=True,
                        help='checkout containing the production coh_net_queue_retries API')
    parser.add_argument('--mode', choices=('all', 'release', 'asan', 'ubsan'), default='all')
    args = parser.parse_args()
    root = args.candidate_root.resolve(strict=True)
    native = root / 'native-android'
    network = native / 'engine/network'
    sources = [network / 'coh_net.c', network / 'coh_net_frame.c',
               network / 'coh_net_zip.c', native / 'protocol/coh_protocol.c',
               native / 'src/coh_blowfish.c', HERE / 'tests/test_retry_limit.c']
    inputs = sources + [network / 'coh_net.h', network / 'coh_net_zip_internal.h',
                        native / 'protocol/coh_protocol.h', native / 'engine/coh_contracts.h',
                        native / 'include/coh_native_core.h', native / 'src/byte_reader.h',
                        Path(__file__).resolve()]
    modes = {'release': [], 'asan': ['-fsanitize=address'],
             'ubsan': ['-fsanitize=undefined']}
    if args.mode != 'all':
        modes = {args.mode: modes[args.mode]}
    results = {}
    # All cooperating NEXT source checks use this same exclusive flock; there
    # are no child build pools or compiler calls before lock acquisition.
    with open('/tmp/coh-next-build.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before = fingerprint(inputs)
        with tempfile.TemporaryDirectory(prefix='coh-next-retry-limit-') as temporary:
            work = Path(temporary)
            for mode, sanitizer in modes.items():
                objects = []
                for index, source in enumerate(sources):
                    obj = work / f'{mode}-{index}.o'
                    optimization = '-O0' if source.name in ('coh_protocol.c', 'coh_blowfish.c') else '-O2'
                    run(['cc', '-std=c99', optimization, '-g', '-Wall', '-Wextra', '-Werror',
                         '-fno-omit-frame-pointer', '-fno-pie', *sanitizer,
                         '-I' + str(network), '-I' + str(native / 'include'),
                         '-I' + str(native / 'protocol'), '-c', source, '-o', obj])
                    objects.append(obj)
                binary = work / f'{mode}-retry-limit'
                run(['cc', '-no-pie', *sanitizer, *objects, '-lz', '-o', binary])
                environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',
                                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                results[mode] = json.loads(run([binary], env=environment))
        if fingerprint(inputs) != before:
            raise RuntimeError('Candidate/test inputs changed during the check; rerun on stable source.')
    print(json.dumps({'passed': True, 'modes': results, 'input_sha256': before,
                      'candidate_root': str(root), 'compile_jobs': 1}, sort_keys=True))


if __name__ == '__main__':
    main()

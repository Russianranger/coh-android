#!/usr/bin/env python3
"""Execute pinned receipt costs through the real parent reservation API.

This proves ordering/refusal/accounting rollback only. It neither instantiates
source owners nor qualifies a global child adapter, RSS or external retirement.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REL = Path('native-android/combined-client/diagnostics')


def require(ok, why):
    if not ok:
        raise ValueError(why)


def run(args, **kwargs):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                            timeout=90, env=dict(os.environ, GIT_NO_LAZY_FETCH='1',
                            ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                            UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), **kwargs)
    require(result.returncode == 0, result.stdout + result.stderr)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    require(not args.output.exists(), 'fresh output required')
    revision = run(['git', '-C', root, 'rev-parse', 'HEAD']).strip()
    aggregate = root / REL / 'aggregate-memory-20261017'
    paths = [HERE / 'phase_replay.c', HERE / 'qualify_phase_replay.py',
             aggregate / 'verify.py', aggregate / 'source-pins.json',
             root / 'native-android/engine/working-set/coh_working_set.c',
             root / 'native-android/engine/working-set/coh_working_set.h',
             root / 'native-android/engine/coh_contracts.h']
    frozen = {path: path.read_bytes() for path in paths}
    for path, raw in frozen.items():
        # These are text files; compare exact UTF-8 re-encoding to tracked blobs.
        require(run(['git', '-C', root, 'show', revision + ':' + str(path.relative_to(root))]).encode() == raw,
                'uncommitted qualification input ' + str(path.relative_to(root)))
    pins = json.loads(frozen[aggregate / 'source-pins.json'])
    proofs, proof_hashes = {}, {}
    for name, pin in pins['proofs'].items():
        raw = (root / pin['path']).read_bytes()
        require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
                'receipt identity ' + name)
        proof_hashes[pin['path']] = pin['sha256']
        proofs[name] = json.loads(gzip.decompress(raw) if pin['path'].endswith('.gz') else raw)
        require(proofs[name]['passed'] is True, 'receipt failed ' + name)
    spec = importlib.util.spec_from_file_location('coh_f_pinned_aggregate', aggregate / 'verify.py')
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    original, retirement = ledger.ledger(proofs), ledger.retirement_extension(proofs)
    result = proofs['sealed']['modes']['release']['result']
    costs = {'SHARED_SOURCE': result['shared_source'],
             'PRIOR_ALLOWANCE': result['dictionary_reservation_kept_for_conservative_comparison'],
             'GEO_RESERVATION': result['retired_geo_reservation'],
             'WORLD_OLD': original['world_named_retained_baseline'],
             'SEALED_OWNED': result['sealed_owned'],
             'SEAL_CALL_RESERVE': result['retirement_peak'] - original['world_named_retained_baseline'] - result['sealed_owned'],
             'DICTIONARIES': original['known_dictionary_retained'],
             'POWER_SETS': original['power_sets_retained'],
             'EXPECTED_PARENT': retirement['measured_parent_metadata_and_reserve_bytes'],
             'WORLD_RETIRED': retirement['sealed_world_comparison_baseline']}
    costs['OLD_EXCLUSIVE'] = costs['WORLD_OLD'] - costs['SHARED_SOURCE'] - costs['PRIOR_ALLOWANCE'] - costs['GEO_RESERVATION']
    costs['EXPECTED_TRANSITION'] = costs['EXPECTED_PARENT'] + result['retirement_peak'] + costs['DICTIONARIES']
    costs['EXPECTED_FINAL'] = costs['EXPECTED_PARENT'] + costs['WORLD_RETIRED'] + costs['DICTIONARIES'] + costs['POWER_SETS']
    require(all(type(v) is int and v > 0 for v in costs.values()), 'positive derived costs')
    require(costs['SEAL_CALL_RESERVE'] == 16384 and costs['EXPECTED_TRANSITION'] == 100074681
            and costs['EXPECTED_FINAL'] == 67361231, 'expected source-qualified phase costs')
    checks, stack = {}, {}
    with tempfile.TemporaryDirectory(prefix='coh-f-parent-replay-') as temporary:
        temporary = Path(temporary)
        working = temporary / 'working-set'
        working.mkdir()
        for path, raw in frozen.items():
            if path.name in ('coh_working_set.c', 'coh_working_set.h'):
                (working / path.name).write_bytes(raw)
            elif path.name in ('coh_contracts.h', 'phase_replay.c'):
                (temporary / path.name).write_bytes(raw)
        (temporary / 'costs.h').write_text(''.join('#define %s ((size_t)%su)\n' % pair for pair in costs.items()))
        for mode, flags in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address',
                '-fno-omit-frame-pointer', '-no-pie']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined',
                '-fno-sanitize-recover=all'])]:
            obj, binary = working / (mode + '.o'), temporary / mode
            common = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', *flags]
            run([*common, '-fstack-usage', '-c', working / 'coh_working_set.c', '-o', obj])
            run([*common, '-I' + str(temporary), temporary / 'phase_replay.c', obj, '-o', binary])
            checks[mode] = json.loads(run([binary]))
            frames = [int(row.split('\t')[1]) for row in obj.with_suffix('.su').read_text().splitlines()]
            require(sum(frames) <= 16384, 'parent emitted frame sum exceeds reserve')
            stack[mode] = {'maximum_parent_frame_bytes': max(frames), 'sum_parent_frames_bytes': sum(frames)}
    require(checks['release'] == checks['asan'] == checks['ubsan'], 'mode results differ')
    require(all(path.read_bytes() == raw for path, raw in frozen.items()), 'source changed')
    require(run(['git', '-C', root, 'rev-parse', 'HEAD']).strip() == revision, 'HEAD changed')
    output = {'schema': 'coh-independent-parent-phase-replay-v1', 'passed': True,
              'source_revision': revision, 'source_sha256': {str(p.relative_to(root)):
              hashlib.sha256(raw).hexdigest() for p, raw in frozen.items()},
              'receipt_sha256': proof_hashes, 'derived_billing_partitions': costs,
              'modes': checks, 'parent_stack': stack, 'synthetic_billing_keys': True,
              'source_owners_instantiated': False, 'actual_resource_retirement_observed': False,
              'module_adapters_qualified': False, 'rss_measured': False, 'android_built': False,
              'android_executed': False, 'world_authority': False, 'leak_sanitizer': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': checks}))


if __name__ == '__main__':
    main()

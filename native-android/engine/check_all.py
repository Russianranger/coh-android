#!/usr/bin/env python3
"""Run independent module suites concurrently, then their shared ABI test.

All six receipts are retained even when an independent stream fails. This
runner does not build or change an APK or contact a gameplay server.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse, hashlib, json, subprocess, sys, time

ENGINE = Path(__file__).resolve().parent
MODULES = ['assets', 'renderer', 'network', 'sequencer', 'ui', 'audio']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path, help='Full repository with immutable upstream source')
    parser.add_argument('--recovered-root', required=True, type=Path, help='Recovered corpus parent containing raw GEO and coh-next assets')
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    recovered = args.recovered_root.resolve()
    authentic = recovered/'coh-next/native-android/integration-probe/app/src/main/assets'
    codecs = recovered/'coh-next/native-android/decode/.deps'

    def run(module):
        candidates = [ENGINE/module/'check.py', ENGINE/module/'tools/check.py']
        driver = next((p for p in candidates if p.is_file()), None)
        if driver is None:
            return {'module': module, 'passed': False, 'error': 'Missing module check driver'}
        receipt = output/(module+'.json')
        command = [sys.executable, str(driver), '--output', str(receipt), '--source-root', str(args.source_root.resolve())]
        if args.sanitize: command += ['--sanitize']
        if module == 'assets': command += ['--corpus-root', str(recovered)]
        if module == 'renderer':
            command += ['--corpus', str(authentic)]
            if args.ndk: command += ['--ndk', str(args.ndk.resolve())]
        if module == 'audio': command += ['--codec-root', str(codecs), '--asset-root', str(authentic)]
        start = time.monotonic()
        with (output/(module+'.log')).open('w') as log:
            try:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300)
                return {'module': module, 'passed': result.returncode == 0, 'exit_code': result.returncode,
                        'elapsed_host_seconds': time.monotonic()-start, 'command': command,
                        'receipt': receipt.name if receipt.exists() else None,
                        'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest() if receipt.exists() else None}
            except subprocess.TimeoutExpired:
                return {'module': module, 'passed': False, 'error': 'Module suite exceeded 300 seconds', 'command': command}
    results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(run, name): name for name in MODULES}
        for future in as_completed(futures):
            try: result = future.result()
            except Exception as error: result = {'module': futures[future], 'passed': False, 'error': str(error)}
            results.append(result)
            print(json.dumps({'module': result['module'], 'passed': result['passed']}), flush=True)
    aggregate = {'schema': 'coh-native-parallel-module-check-v1', 'workers': 6,
                 'passed': all(x['passed'] for x in results), 'modules': sorted(results, key=lambda x:x['module']),
                 'android_emulator_qualified': False, 'physical_thor_qualified': False,
                 'scope': 'Host source/oracle/sanitizer suites. Host runtimes are diagnostics, not device gameplay benchmarks.'}
    if aggregate['passed']:
        command = [sys.executable, str(ENGINE/'build.py'), '--output', str(output/'combined-host'),
                   '--codec-root', str(codecs), '--audio-fixture', str(authentic/'headset.ogg')]
        if args.sanitize: command += ['--sanitize']
        with (output/'combined-host.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        aggregate['combined_host_passed'] = result.returncode == 0
        aggregate['passed'] = aggregate['passed'] and result.returncode == 0
    (output/'summary.json').write_text(json.dumps(aggregate, indent=2)+'\n')
    raise SystemExit(0 if aggregate['passed'] else 1)

if __name__ == '__main__': main()

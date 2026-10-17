#!/usr/bin/env python3
"""Admit exact bounded-frame artifacts, then reuse qualified Android13 driver.

--validate-only never starts adb and never reports Android execution. All device
execution remains fixture-only and retains the original driver's receipts/logs.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DRIVER = HERE.parent / 'continuation/run_adapter_android.py'
spec = importlib.util.spec_from_file_location('frame_android_adapter_driver', DRIVER)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
c = driver.c


def frame_result(result):
    """Require the recovered frame corpus, not a historical adapter-only build."""
    numeric = ('checks', 'ordered_batch_draws', 'ordered_batches', 'original_matrix_cases',
               'bounded_mutations', 'published_generations', 'concurrent_readers',
               'max_draws_tested', 'render_allocations', 'render_frees')
    if (type(result) is not dict or any(type(result.get(key)) is not int for key in numeric)
            or result.get('passed') is not True
            or type(result.get('checks')) is not int or result['checks'] < 32284
            or result.get('ordered_batch_draws') != 1025
            or result.get('ordered_batches') != 3
            or result.get('selective_binding') is not True
            or result.get('original_matrix_cases') != 512
            or result.get('bounded_mutations') != 5000
            or result.get('published_generations') != 2000
            or result.get('concurrent_readers') != 3
            or result.get('max_draws_tested') != 4096
            or result.get('render_allocations') != 0
            or result.get('render_frees') != 0
            or result.get('fixture_only') is not True
            or result.get('authentic_world_entry') is not False):
        raise ValueError('Recovered bounded-frame corpus/result scope absent')
    return result


def validate_runner_sources(repo, proof):
    # Bind executing Python bytes, not only native compiler inputs. Hashes are
    # supplied by check.py in qualification.json and BOTH exact ABI receipts.
    paths = (Path(__file__).resolve(), DRIVER.resolve(), Path(c.__file__).resolve())
    sources = proof.get('source_sha256', {})
    for running in paths:
        relative = running.relative_to(ROOT.resolve()).as_posix()
        expected = sources.get(relative)
        if expected is None or c.hash_value(expected) != c.digest(running):
            raise ValueError('Executing frame/delegated runner is absent or differs from artifact source')
        if c.digest(c.child(repo, relative)) != expected:
            raise ValueError('Executing runner differs from requested qualified checkout')


def validate(artifacts, repo):
    proof = c.read(c.child(artifacts, 'qualification.json'))
    expected, entries = driver.validate(artifacts, proof)
    validate_runner_sources(repo, proof)
    frame_result(expected)
    # validate() above requires identical address/undefined/native/ABI results,
    # both exact ELF hashes and fixture bytes; checkout check binds source hashes.
    driver.validate_checkout(repo, proof)
    return proof, expected, entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--adb', type=Path)
    parser.add_argument('--serial')
    args = parser.parse_args()
    if not args.validate_only and (not args.adb or not args.serial):
        parser.error('--adb and --serial required for device execution')
    result = {'schema': 'coh-bounded-frame-android-v1', 'passed': False,
              'artifact_admitted': False, 'android_executed': False,
              'emulator_qualified': False, 'native_result_validated': False,
              'fixture_only': True, 'authentic_world_entry': False,
              'physical_thor_accepted': False, 'gpu_execution': False,
              'mode': 'admission-only' if args.validate_only else 'android13-x86_64',
              'runner_sha256': c.digest(Path(__file__)),
              'delegated_runner_sha256': c.digest(DRIVER), 'errors': {}}
    try:
        proof, expected, entries = validate(args.artifacts.resolve(), args.source_root.resolve())
        result.update(artifact_admitted=True, source_revision=proof['source_revision'],
                      source_tree=proof['source_tree'], source_sha256=proof['source_sha256'],
                      expected_native_result=expected,
                      binaries_sha256={abi: value['sha256'] for abi, value in entries.items()})
        if args.validate_only:
            result['passed'] = True
        else:
            # Original driver refuses any nonempty execution evidence directory,
            # checks Android13/emulator/ABI, exact transferred binary and result,
            # source stability and owned remote cleanup before qualifying.
            receipt = args.output.parent / 'execution/receipt.json'
            command = [sys.executable, str(DRIVER), '--adb', str(args.adb),
                       '--serial', args.serial, '--artifacts', str(args.artifacts),
                       '--source-root', str(args.source_root), '--output', str(receipt)]
            completed = subprocess.run(command, timeout=480, check=False)
            observed = c.read(receipt)
            result.update(delegated_receipt=str(receipt.resolve()),
                          delegated_receipt_sha256=c.digest(receipt),
                          delegated_driver_exit_code=completed.returncode)
            # Propagate observed execution honestly even if later validation fails.
            result['android_executed'] = observed.get('android_executed') is True
            if completed.returncode or observed.get('passed') is not True:
                raise ValueError('Delegated Android execution did not qualify')
            frame_result(observed.get('result'))
            if not c.json_equal(observed['result'], expected):
                raise ValueError('Android frame result differs from admitted artifact')
            if (observed.get('android_executed') is not True
                    or observed.get('emulator_qualified') is not True
                    or observed.get('native_result_validated') is not True
                    or observed.get('temporary_files_removed') is not True):
                raise ValueError('Android execution/cleanup qualification absent')
            result.update(passed=True, emulator_qualified=True, native_result_validated=True,
                          result=observed['result'])
    except Exception as error:
        result['errors']['qualification'] = str(error)
    c.write(args.output, result)
    print(json.dumps({key: result[key] for key in ('passed', 'artifact_admitted',
                                                 'android_executed', 'emulator_qualified', 'errors')}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

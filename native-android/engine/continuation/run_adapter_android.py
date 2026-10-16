#!/usr/bin/env python3
"""Execute exact immutable-adapter contracts on Android; never a live-world test."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    'adapter_receipt_common', HERE.parent / 'scenecatalog-qualification/common.py')
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)
REQUIRED = {
    'native-android/engine/world-render-adapter/coh_world_render.c',
    'native-android/engine/world-render-adapter/coh_world_render.h',
    'native-android/engine/world-render-adapter/tests/test_world_render.c',
    'native-android/engine/world-render-adapter/check.py',
    'native-android/engine/renderer/coh_renderer.c',
    'native-android/engine/renderer/coh_renderer.h',
    'native-android/engine/renderer/coh_renderer_shaders.h',
    'native-android/engine/coh_contracts.h',
    'native-android/engine/world-render-adapter/source-pins.json',
    'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h',
}
COMMAND_OUTPUT_MAX = 1024 * 1024


class CommandFailure(RuntimeError):
    def __init__(self, log, returncode):
        super().__init__('Android command failed; retained log ' + log.name)
        self.returncode = returncode


def bounded_execute(command, log, timeout=60):
    """Keep failure logs, and bound their in-memory decode before JSON parsing.

    Commands address a hash-admitted test binary and this job's emulator. This
    is a memory read ceiling, not a hard filesystem quota or process RSS cap.
    """
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('wb') as stream:
        try:
            process = subprocess.run([str(part) for part in command], stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Android command timed out; bounded execution not accepted') from None
    with log.open('rb') as stream:
        raw = stream.read(COMMAND_OUTPUT_MAX + 1)
    if len(raw) > COMMAND_OUTPUT_MAX:
        raise ValueError('Android command output exceeds decode ceiling')
    if process.returncode:
        raise CommandFailure(log, process.returncode)
    return raw.decode('utf-8')


def validate(root, proof):
    c.mapping(proof, 'Adapter qualification')
    if (proof.get('passed') is not True or proof.get('fixture_only') is not True
            or proof.get('prerequisites_available') is not False
            or proof.get('authentic_server_interoperability') is not False
            or proof.get('physical_thor_accepted') is not False
            or proof.get('android_emulator_qualified') is not False):
        raise ValueError('Only successful fixture-only adapter evidence is admitted')
    c.reject_compile_claims(proof)
    if proof.get('source_inputs_unchanged') is not True:
        raise ValueError('Source inputs must remain unchanged throughout qualification')
    for key in ('source_revision', 'source_tree'):
        if not isinstance(proof.get(key), str) or not re.fullmatch('[a-f0-9]{40}', proof[key]):
            raise ValueError('Exact source commit and tree required')
    if proof.get('clean_worktree_before') is not True or proof.get('clean_worktree_after') is not True:
        raise ValueError('Clean qualification source required')
    sources = c.source_hashes(proof.get('source_sha256'))
    if not REQUIRED.issubset(sources):
        raise ValueError('Required adapter build sources omitted')
    expected = c.native_result(proof.get('host'))
    c.reject_compile_claims(expected)
    if expected.get('fixture_only') is not True or expected.get('authentic_world_entry') is not False:
        raise ValueError('Native fixture evidence scope differs')
    for mode in ('address', 'undefined'):
        if not c.json_equal(c.native_result(proof.get(mode)), expected):
            raise ValueError('Sanitized host results differ')
    fixtures = c.mapping(proof.get('fixtures_sha256'), 'Original matrix fixture')
    if set(fixtures) != {'original_matrix.h'}:
        raise ValueError('Exact original matrix fixture required')
    for name, sha in fixtures.items():
        if c.digest(c.child(root, name)) != c.hash_value(sha):
            raise ValueError('Original matrix fixture changed')
    builds = c.mapping(proof.get('android_builds'), 'Android builds')
    if set(builds) != set(c.ABIS):
        raise ValueError('Both ABI builds required before device execution')
    entries = {}
    for abi in c.ABIS:
        receipt_path = c.child(root, 'android/' + abi + '/build.json')
        receipt = c.read(receipt_path)
        if not c.json_equal(builds[abi], receipt):
            raise ValueError('ABI receipt differs from qualified receipt')
        if (receipt.get('passed') is not True or receipt.get('abi') != abi
                or receipt.get('api') != 26 or receipt.get('executed') is not False
                or receipt.get('source_revision') != proof['source_revision']
                or receipt.get('source_tree') != proof['source_tree']
                or not c.json_equal(receipt.get('source_sha256'), sources)
                or not c.json_equal(receipt.get('fixtures_sha256'), fixtures)
                or not c.json_equal(receipt.get('expected_native_result'), expected)):
            raise ValueError('ABI build/source/fixture scope differs')
        c.reject_compile_claims(receipt)
        name = receipt.get('binary')
        if not isinstance(name, str) or name != 'world-render-adapter-test':
            raise ValueError('Unexpected standalone executable name')
        binary = c.child(root, 'android/' + abi + '/' + name)
        if binary.stat().st_size > 128 * 1024 * 1024 or c.digest(binary) != c.hash_value(receipt.get('binary_sha256')):
            raise ValueError('Android binary identity differs')
        c.elf_identity(binary, abi)
        entries[abi] = {'binary': binary, 'sha256': receipt['binary_sha256'],
                        'build_receipt_sha256': c.digest(receipt_path)}
    return expected, entries


def validate_checkout(repo, proof):
    state = c.git_state(repo)
    tree = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD^{tree}'],
                                   text=True, timeout=30).strip()
    if (state['source_revision'] != proof['source_revision'] or tree != proof['source_tree']
            or state['source_git_status_porcelain']):
        raise ValueError('Execution checkout differs from clean qualified source/tree')
    c.verify_sources(repo, proof['source_sha256'])
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=HERE.parents[2])
    args = parser.parse_args()
    root, repo = args.artifacts.resolve(), args.source_root.resolve()
    if args.output.parent.exists() and any(args.output.parent.iterdir()):
        parser.error('Execution evidence directory must be empty')
    result = {'schema': 'coh-world-adapter-android-execution-v1', 'passed': False,
              'android_executed': False, 'emulator_qualified': False,
              'device_test_command_attempted': False,
              'device_test_command_exit_code': None,
              'native_result_validated': False,
              'fixture_only': True, 'authentic_world_entry': False,
              **{key: False for key in c.CLAIMS}, 'errors': {},
              'runner_sha256': c.digest(Path(__file__))}
    adb = [args.adb.resolve(), '-s', args.serial]
    number, remote = 0, None

    def run(command, timeout=60):
        nonlocal number
        number += 1
        return bounded_execute(command, args.output.parent / 'logs' / f'{number:03}.log', timeout).strip()

    try:
        report_path = c.child(root, 'qualification.json')
        proof = c.read(report_path)
        expected, entries = validate(root, proof)
        state = validate_checkout(repo, proof)
        result.update(source_revision=proof['source_revision'], source_tree=proof['source_tree'],
                      qualification_sha256=c.digest(report_path), source_sha256=proof['source_sha256'])
        run([*adb, 'wait-for-device'])
        prop = lambda name: run([*adb, 'shell', 'getprop', name])
        if (prop('ro.build.version.sdk') != '33' or prop('ro.kernel.qemu') != '1'
                or 'x86_64' not in prop('ro.product.cpu.abilist').split(',')):
            raise ValueError('Expected Android 13 x86_64 emulator')
        result['device_fingerprint'] = prop('ro.build.fingerprint')
        remote = run([*adb, 'shell', 'mktemp', '-d', '/data/local/tmp/coh-adapter.XXXXXX'])
        if not re.fullmatch(r'/data/local/tmp/coh-adapter\.[A-Za-z0-9]+', remote):
            remote = None
            raise ValueError('Unexpected device temporary directory')
        entry = entries['x86_64']
        destination = remote + '/adapter-test'
        run([*adb, 'push', entry['binary'], destination])
        if run([*adb, 'shell', 'sha256sum', destination]).split()[0] != entry['sha256']:
            raise ValueError('Transferred binary differs')
        run([*adb, 'shell', 'chmod', '700', destination])
        # Device-side deadline ends a hung test even if adb later disconnects.
        # The host deadline allows the device timeout to finish first.
        result.update(binary_sha256=entry['sha256'],
                      build_receipt_sha256=entry['build_receipt_sha256'],
                      device_test_command_attempted=True)
        try:
            raw = run([*adb, 'shell', 'timeout', '-s', 'KILL', '90', destination], timeout=180)
            result['device_test_command_exit_code'] = 0
        except CommandFailure as error:
            result['device_test_command_exit_code'] = error.returncode
            raise
        # A command attempt alone does not prove native execution: adb, the
        # shell or timeout may fail first. Retain that distinction on failures.
        actual = c.native_result(c.loads(raw))
        result['android_executed'] = True
        if not c.json_equal(actual, expected):
            c.write(args.output.parent / 'unexpected-result.json', actual)
            raise ValueError('Android result differs from sanitized host result')
        result.update(result=actual, native_result_validated=True)
        c.verify_sources(repo, proof['source_sha256'])
        if c.git_state(repo) != state:
            raise ValueError('Source state changed during execution')
        result['passed'] = result['emulator_qualified'] = True
    except Exception as error:
        result['errors']['execution'] = str(error)
    finally:
        if remote is not None:
            try:
                run([*adb, 'shell', 'rm', '-rf', remote])
                result['temporary_files_removed'] = True
            except Exception as error:
                result['errors']['cleanup'] = str(error)
                result['passed'] = result['emulator_qualified'] = False
    c.write(args.output, result)
    print({'passed': result['passed'], 'errors': result['errors'], 'authentic_world_entry': False})
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

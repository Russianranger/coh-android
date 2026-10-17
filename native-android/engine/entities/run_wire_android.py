#!/usr/bin/env python3
"""Execute source-bound standalone prefix/range wire contracts, never world admission."""
import argparse
import importlib.util
import hashlib
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ADAPTER_PATH = 'native-android/engine/continuation/run_adapter_android.py'
COMMON_PATH = 'native-android/engine/scenecatalog-qualification/common.py'
RUNNER_PATH = 'native-android/engine/entities/run_wire_android.py'
_spec = importlib.util.spec_from_file_location('wire_android_adapter', HERE.parent / 'continuation/run_adapter_android.py')
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)
c = adapter.c
MODULES = {
    'prefix': {'schema': 'coh-character-prefix-v1', 'stem': 'character_prefix',
               'fixture': 'prefix_fixtures.h', 'sources': 'production_source_sha256',
               'fixture_key': 'fixture_sha256', 'original': 'source_sha256_lf',
               'build_original': 'original_source_sha256_lf',
               'scope': 'whole_character_complete'},
    'ranges': {'schema': 'coh-power-range-qualification-v1', 'stem': 'power_ranges',
               'fixture': 'range_fixtures.h', 'sources': 'source_sha256',
               'fixture_key': 'fixtures_sha256', 'original': 'original_sha256_lf',
               'build_original': 'original_sha256_lf', 'scope': 'full_power_info_update'},
}


def native_result(value, module):
    """Existing wire tests emit counts and their explicit incomplete boundary."""
    scope = MODULES[module]['scope']
    c.mapping(value, 'Native wire result')
    if (set(value) != {'fixtures', 'checks', scope}
            or type(value['fixtures']) is not int or not 0 < value['fixtures'] < 1_000_000
            or type(value['checks']) is not int or not 0 < value['checks'] < 1_000_000_000
            or value[scope] is not False):
        raise ValueError('Unexpected native wire result/scope')
    return value


def required_sources(module):
    stem = MODULES[module]['stem']
    pins = 'character-prefix-source-pins.json' if module == 'prefix' else 'power-ranges-source-pins.json'
    paths = {RUNNER_PATH, ADAPTER_PATH, COMMON_PATH,
             'native-android/engine/entities/check_' + stem + '.py',
             'native-android/engine/entities/coh_' + stem + '.c',
             'native-android/engine/entities/coh_' + stem + '.h',
             'native-android/engine/entities/test_' + stem + '.c',
             'native-android/engine/entities/' + pins,
             'native-android/engine/entities/check_teammate_buffs.py',
             'native-android/engine/entities/test_run_wire_android.py',
             'native-android/engine/replication/coh_replication.c',
             'native-android/engine/replication/coh_replication.h',
             'native-android/engine/coh_contracts.h',
             'native-android/include/coh_native_core.h',
             'native-android/tools/protocol_fixture/prepare.py'}
    if module == 'ranges':
        paths.update({'native-android/engine/entities/power_ranges_oracle.c.inc',
                      'native-android/engine/entities/power_ranges_fixture.c.inc',
                      'native-android/engine/character-data/coh_character_data.h',
                      'native-android/engine/character-data/coh_character_data.c'})
    return paths, pins


def validate(root, proof, module):
    config = MODULES[module]
    c.mapping(proof, 'Wire qualification')
    if (proof.get('schema') != config['schema'] or proof.get('passed') is not True
            or proof.get('source_unchanged_before_after') is not True
            or proof.get('actor_publication') is not False
            or proof.get('acknowledgments_enabled') is not False
            or proof.get(config['scope']) is not False):
        raise ValueError('Incomplete or overclaimed standalone wire qualification')
    c.reject_compile_claims(proof)
    for key in ('dictionary_authority', 'dictionary_bindings_verified', 'full_update_complete', 'complete_full_update'):
        if key in proof and proof[key] is not False:
            raise ValueError('Standalone wire proof overclaims semantic authority')
    controls = c.mapping(proof.get('wire_runner_host_controls'), 'Wire runner host controls')
    c.reject_compile_claims(controls)
    if (controls.get('passed') is not True
            or type(controls.get('test_methods')) is not int or controls.get('test_methods') != 9
            or type(controls.get('failures')) is not int or type(controls.get('errors')) is not int
            or controls.get('failures') != 0 or controls.get('errors') != 0
            or controls.get('android_executed') is not False
            or controls.get('emulator_qualified') is not False
            or controls.get('actor_publication') is not False
            or controls.get('acknowledgments_enabled') is not False):
        raise ValueError('Wire runner negative controls missing/overclaimed')
    for key in ('source_revision', 'source_tree'):
        if not isinstance(proof.get(key), str) or not re.fullmatch('[a-f0-9]{40}', proof[key]):
            raise ValueError('Exact source commit/tree required')
    sources = c.source_hashes(proof.get(config['sources']))
    required, _ = required_sources(module)
    if not required.issubset(sources):
        raise ValueError('Required wire/runner/dependency source omitted')
    # Actual running driver/dependencies must be exactly the bytes in the build.
    for name, path in ((RUNNER_PATH, Path(__file__)),
                       (ADAPTER_PATH, Path(adapter.__file__)),
                       (COMMON_PATH, Path(c.__file__))):
        if c.digest(path) != sources[name]:
            raise ValueError('Running Android driver/dependency differs from build')
    checks = c.mapping(proof.get('checks'), 'Host checks')
    if set(checks) != {'release', 'asan', 'ubsan'}:
        raise ValueError('Release, ASan and UBSan results required')
    expected = native_result(checks['release'], module)
    for mode in ('asan', 'ubsan'):
        if not c.json_equal(native_result(checks[mode], module), expected):
            raise ValueError('Sanitized host result differs')
    fixture_sha = c.hash_value(proof.get(config['fixture_key']))
    if c.digest(c.child(root, 'android/' + config['fixture'])) != fixture_sha:
        raise ValueError('Original generated fixture changed')
    original = c.source_hashes(proof.get(config['original']))
    builds = c.mapping(proof.get('android'), 'Android builds')
    if set(builds) != set(c.ABIS) or proof.get('android_built') != list(c.ABIS):
        raise ValueError('Both ABI builds required')
    entries = {}
    for abi in c.ABIS:
        receipt_path = c.child(root, 'android/' + abi + '/receipt.json')
        receipt = c.read(receipt_path)
        if not c.json_equal(receipt, builds[abi]):
            raise ValueError('Per-ABI receipt differs')
        c.reject_compile_claims(receipt)
        if (receipt.get('built') is not True or receipt.get('executed') is not False
                or receipt.get('abi') != abi or type(receipt.get('api_level')) is not int or receipt.get('api_level') != 26
                or receipt.get('source_revision') != proof['source_revision']
                or receipt.get('source_tree') != proof['source_tree']
                or not c.json_equal(receipt.get('source_sha256'), sources)
                or not c.json_equal(receipt.get(config['build_original']), original)
                or receipt.get('fixtures_sha256') != fixture_sha
                or not c.json_equal(receipt.get('expected_native_result'), expected)
                or receipt.get('actor_publication') is not False
                or receipt.get('acknowledgments_enabled') is not False
                or receipt.get(config['scope']) is not False):
            raise ValueError('ABI build/source/fixture/scope identity differs')
        name = 'coh_' + config['stem'] + '_test'
        if receipt.get('binary') != name:
            raise ValueError('Unexpected standalone executable')
        binary = c.child(root, 'android/' + abi + '/' + name)
        if binary.stat().st_size > 128 * 1024 * 1024 or c.digest(binary) != c.hash_value(receipt.get('binary_sha256')):
            raise ValueError('Android executable bytes differ')
        c.elf_identity(binary, abi)
        entries[abi] = {'binary': binary, 'sha256': receipt['binary_sha256'],
                        'build_receipt_sha256': c.digest(receipt_path)}
    return expected, entries


def validate_checkout(repo, proof, module):
    config = MODULES[module]
    state = c.git_state(repo)
    tree = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD^{tree}'], text=True, timeout=30).strip()
    if (state['source_revision'] != proof['source_revision'] or tree != proof['source_tree']
            or state['source_git_status_porcelain']):
        raise ValueError('Checkout differs from clean qualified source/tree')
    c.verify_sources(repo, proof[config['sources']])
    _, pins_name = required_sources(module)
    original = proof[config['original']]
    if not c.json_equal(c.read(c.child(repo, 'native-android/engine/entities/' + pins_name)), original):
        raise ValueError('Original source pins differ')
    for name, digest in original.items():
        # Sparse source checkout is supported without assuming missing files
        # never existed. Original normalized source identity is bound to Git.
        name = c.relative_name(name)
        path = repo / 'upstream/ouroboros' / name
        raw = c.child(repo, 'upstream/ouroboros/' + name).read_bytes() if path.is_file() else subprocess.check_output(
            ['git', '-C', str(repo), 'show', 'HEAD:upstream/ouroboros/' + name], timeout=30)
        if hashlib.sha256(raw.decode().replace('\r\n', '\n').encode()).hexdigest() != digest:
            raise ValueError('Original source bytes differ')
    return state


def main(argv=None, executor=adapter.bounded_execute):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', choices=MODULES, required=True)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=HERE.parents[2])
    args = parser.parse_args(argv)
    root, repo = args.artifacts.resolve(), args.source_root.resolve()
    if args.output.parent.exists() and any(args.output.parent.iterdir()):
        parser.error('Execution evidence directory must be empty')
    result = {'schema': 'coh-wire-android-execution-v1', 'module': args.module,
              'passed': False, 'serial': args.serial, 'android_executed': False, 'emulator_qualified': False,
              'device_test_command_attempted': False, 'device_test_command_exit_code': None,
              'native_result_validated': False, 'native_match': False,
              'temporary_files_removed': False, 'fixture_only': True,
              'authentic_world_entry': False, 'actor_publication': False,
              'acknowledgments_enabled': False, MODULES[args.module]['scope']: False,
              **{key: False for key in c.CLAIMS},
              'errors': {}, 'runner_sha256': c.digest(Path(__file__))}
    adb = [args.adb.resolve(), '-s', args.serial]
    number, remote = 0, None

    def run(command, timeout=60):
        nonlocal number
        number += 1
        return executor(command, args.output.parent / 'logs' / f'{number:03}.log', timeout).strip()

    try:
        report_path = c.child(root, 'qualification.json')
        proof = c.read(report_path)
        expected, entries = validate(root, proof, args.module)
        state = validate_checkout(repo, proof, args.module)
        sources = proof[MODULES[args.module]['sources']]
        result.update(source_revision=proof['source_revision'], source_tree=proof['source_tree'],
                      qualification_sha256=c.digest(report_path), source_sha256=sources)
        run([*adb, 'wait-for-device'])
        prop = lambda name: run([*adb, 'shell', 'getprop', name])
        device = {key: prop(key) for key in ('ro.build.version.sdk', 'ro.kernel.qemu',
                                            'ro.product.cpu.abilist', 'ro.build.fingerprint')}
        result['device_properties'] = device
        if (device['ro.build.version.sdk'] != '33' or device['ro.kernel.qemu'] != '1'
                or 'x86_64' not in device['ro.product.cpu.abilist'].split(',')
                or not device['ro.build.fingerprint']):
            raise ValueError('Expected Android 13 x86_64 emulator')
        remote = run([*adb, 'shell', 'mktemp', '-d', '/data/local/tmp/coh-wire.XXXXXX'])
        if not re.fullmatch(r'/data/local/tmp/coh-wire\.[A-Za-z0-9]+', remote):
            remote = None
            raise ValueError('Unexpected owned device directory')
        entry = entries['x86_64']
        destination = remote + '/wire-test'
        run([*adb, 'push', entry['binary'], destination])
        remote_hash = run([*adb, 'shell', 'sha256sum', destination]).split()
        if not remote_hash or remote_hash[0] != entry['sha256']:
            raise ValueError('Transferred executable differs')
        run([*adb, 'shell', 'chmod', '700', destination])
        result.update(binary_sha256=entry['sha256'], build_receipt_sha256=entry['build_receipt_sha256'],
                      device_test_command_attempted=True)
        try:
            raw = run([*adb, 'shell', 'timeout', '-s', 'KILL', '90', destination], timeout=180)
            result['device_test_command_exit_code'] = 0
        except adapter.CommandFailure as error:
            result['device_test_command_exit_code'] = error.returncode
            raise
        actual = native_result(c.loads(raw), args.module)
        result['android_executed'] = True
        if not c.json_equal(actual, expected):
            c.write(args.output.parent / 'unexpected-result.json', actual)
            raise ValueError('Android native result differs from sanitized host result')
        result.update(result=actual, native_match=True, native_result_validated=True)
        validate(root, proof, args.module)
        if c.digest(report_path) != result['qualification_sha256']:
            raise ValueError('Qualification receipt changed during execution')
        c.verify_sources(repo, sources)
        if c.git_state(repo) != state:
            raise ValueError('Source state changed during execution')
        result['passed'] = result['emulator_qualified'] = True
    except Exception as error:
        result['errors']['execution'] = str(error)
    finally:
        if remote is not None:
            try:
                run([*adb, 'shell', 'rm', '-rf', remote])
                run([*adb, 'shell', 'test', '!', '-e', remote])
                result['temporary_files_removed'] = True
            except Exception as error:
                result['errors']['cleanup'] = str(error)
                result['passed'] = result['emulator_qualified'] = False
    c.write(args.output, result)
    print({'passed': result['passed'], 'errors': result['errors'], 'authentic_world_entry': False})
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

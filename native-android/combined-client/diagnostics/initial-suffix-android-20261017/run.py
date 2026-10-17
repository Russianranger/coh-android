#!/usr/bin/env python3
"""Admit and execute standalone suffix controls on explicit Android13 emulator."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import struct
import uuid
from prepare import HERE, ROOT, SUFFIX, load_suffix, sha


def helper():
    path = ROOT / 'native-android/engine/entities/run_character_android.py'
    spec = importlib.util.spec_from_file_location('coh_raw_android', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admit(artifacts):
    common = helper()
    read = lambda name: common.read(common.child(artifacts, name))
    package = read('package.json')
    if package.get('schema') != 'coh-initial-suffix-android-package-v1' or package.get('passed') is not True:
        raise ValueError('package scope')
    if any(package.get(k) is not False for k in ('actor_publication', 'acknowledgments_enabled', 'android_executed', 'physical_thor')):
        raise ValueError('package authority')
    sources = package.get('source_sha256', {})
    for path in [HERE / 'prepare.py', Path(__file__), ROOT / 'native-android/engine/entities/run_character_android.py']:
        if sources.get(path.relative_to(ROOT).as_posix()) != sha(path):
            raise ValueError('executing driver identity')
    host = read('host.json')
    if sha(common.child(artifacts, 'host.json')) != package.get('host_sha256'):
        raise ValueError('host binding')
    if host.get('schema') != 'coh-initial-global-suffix-diagnostic-v1' or host.get('passed') is not True:
        raise ValueError('host scope')
    for key in ('whole_initial_update_complete', 'actor_publication', 'acknowledgments_enabled', 'dependency_stack_and_sanitizer_closure'):
        if host.get(key) is not False:
            raise ValueError('host authority or dependency scope')
    core, providers = host.get('source_sha256', {}), host.get('provider_sha256', {})
    if not core or not providers or set(core) & set(providers):
        raise ValueError('source ownership')
    for name, digest in {**core, **providers}.items():
        if sources.get(name) != digest:
            raise ValueError('host source binding')
    for name, digest in sources.items():
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or sha(common.child(ROOT, name)) != digest:
            raise ValueError('current source identity')
    module = load_suffix()
    required = {SUFFIX / name for name in ('check.py', 'fixture_builder.py', 'CONTRACT.md', 'source-order-pins.json', 'test_suffix.c')}
    for directory, names in module.SOURCES.items():
        required.update(SUFFIX.parent / directory / name for name in names)
        for pattern in ('*.h', '*.py', '*.inc', '*.json'):
            required.update((SUFFIX.parent / directory).glob(pattern))
    required.update([ROOT / 'native-android/include/coh_native_core.h',
                     ROOT / 'native-android/tools/protocol_fixture/prepare.py'])
    if not {p.relative_to(ROOT).as_posix() for p in required}.issubset(core):
        raise ValueError('incomplete compiled source closure')
    provider_names = {
        'character-outer-20261017': ['qualify_outer.py', 'independent.py', 'source-pins.json', 'host-proof.json', 'group4_oracle.py', 'group56_oracle.py', 'group56_independent.py', 'group56-source-pins.json'],
        'allents-tail-20261017': ['inventory_oracle.py', 'update_oracle.py', 'update-source-pins.json', 'active_invention_oracle.py', 'active-invention-source-pins.json', 'member_oracle.py', 'team_oracle.py', 'team-source-pins.json', 'superstats_oracle.py', 'superstats-source-pins.json', 'attribute_monitor_oracle.py', 'attribute-monitor-source-pins.json', 'dynamic_wire_oracle.py', 'dynamic-wire-source-pins.json', 'sky_oracle.py', 'sky-source-pins.json'],
    }
    required_providers = {'native-android/combined-client/diagnostics/' + directory + '/' + name
                          for directory, names in provider_names.items() for name in names}
    if set(providers) != required_providers:
        raise ValueError('incomplete original provider closure')
    expected = host.get('checks', {}).get('release')
    if not isinstance(expected, dict) or expected.get('passed') is not True or expected.get('checks') != 9991:
        raise ValueError('native control count')
    for key in ('whole_initial_update_complete', 'actor_publication', 'ack_permitted'):
        if expected.get(key) is not False:
            raise ValueError('native authority')
    if any(host.get('checks', {}).get(mode) != expected for mode in ('asan', 'ubsan')):
        raise ValueError('host sanitizer results')
    if host.get('source_revision') != package.get('source_revision'):
        raise ValueError('source generation')
    if host.get('fixtures_sha256') != package.get('fixture_sha256') or sha(common.child(artifacts, 'fixtures.h')) != package['fixture_sha256']:
        raise ValueError('fixture binding')
    if set(package.get('builds', {})) != {'arm64-v8a', 'x86_64'}:
        raise ValueError('both ABI builds required')
    binaries = {}
    for abi, machine in [('arm64-v8a', 183), ('x86_64', 62)]:
        build = read(abi + '/build.json')
        binary = common.child(artifacts, abi + '/coh_initial_suffix_test')
        if binary.stat().st_size > 32 * 1024**2:
            raise ValueError('binary size limit')
        with binary.open('rb') as stream:
            header = stream.read(64)
        if build != package['builds'][abi] or build.get('built') is not True or build.get('executed') is not False or build.get('abi') != abi or build.get('api') != 26:
            raise ValueError('ABI build binding')
        if len(header) != 64 or header[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', header, 18)[0] != machine or sha(binary) != build.get('binary_sha256') or build.get('fixture_sha256') != package['fixture_sha256']:
            raise ValueError('ABI binary identity')
        if build.get('external_dependency_stack_and_sanitizer_closure') is not False or build.get('linked_android_platform_zlib') is not True:
            raise ValueError('dependency scope')
        if build.get('machine') != machine or not isinstance(build.get('compiler_sha256'), str) or not re.fullmatch('[0-9a-f]{64}', build['compiler_sha256']):
            raise ValueError('compiler or machine identity')
        binaries[abi] = binary
    return expected, binaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--adb', type=Path)
    parser.add_argument('--serial')
    args = parser.parse_args()
    if not args.validate_only and (not args.adb or not args.serial):
        parser.error('explicit adb and serial required')
    if args.output.parent.exists() and any(args.output.parent.iterdir()):
        raise ValueError('fresh evidence directory required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(schema='coh-initial-suffix-android-execution-v1', passed=False,
                  artifact_admitted=False, native_execution_attempted=False,
                  android_executed=False, temporary_files_removed=False,
                  actor_publication=False, acknowledgments_enabled=False,
                  whole_initial_update_complete=False, live_server=False,
                  gpu_execution=False, physical_thor=False,
                  loaded_zlib_mapping_verified=False,
                  external_dependency_stack_and_sanitizer_closure=False)
    common = helper()
    remote = '/data/local/tmp/coh-suffix-' + uuid.uuid4().hex
    owned = False
    commands = 0

    def adb(*arguments):
        nonlocal commands
        commands += 1
        return common.command([args.adb, '-s', args.serial, *arguments],
                              args.output.parent / (str(commands) + '.log'), 180)

    try:
        expected, binaries = admit(args.artifacts.resolve())
        result['artifact_admitted'] = True
        if not args.validate_only:
            if not re.fullmatch('emulator-[0-9]+', args.serial):
                raise ValueError('explicit emulator required')
            if [adb('shell', 'getprop', name) for name in ('ro.build.version.sdk', 'ro.product.cpu.abi', 'ro.kernel.qemu')] != ['33', 'x86_64', '1']:
                raise ValueError('Android13 x86_64 emulator required')
            owned = True
            adb('shell', 'mkdir', remote)
            binary = binaries['x86_64']
            target = remote + '/' + binary.name
            adb('push', binary, target)
            if adb('shell', 'sha256sum', target).split()[0] != sha(binary):
                raise ValueError('transferred binary differs')
            adb('shell', 'chmod', '700', target)
            zlib_before = adb('shell', 'sha256sum', '/system/lib64/libz.so').split()[0]
            if not re.fullmatch('[0-9a-f]{64}', zlib_before):
                raise ValueError('platform zlib file identity')
            result['native_execution_attempted'] = True
            observed = json.loads(adb('shell', 'timeout', '-s', 'KILL', '90', target))
            result['android_executed'] = True
            result['observed'] = observed
            if observed != expected:
                raise ValueError('native result differs')
            zlib_after = adb('shell', 'sha256sum', '/system/lib64/libz.so').split()[0]
            if zlib_before != zlib_after:
                raise ValueError('platform zlib file changed')
            result['observed_platform_zlib_file'] = dict(path='/system/lib64/libz.so', before_sha256=zlib_before, after_sha256=zlib_after, loaded_mapping_verified=False)
            admit(args.artifacts.resolve())
            adb('shell', 'rm', '-rf', remote)
            adb('shell', 'test', '!', '-e', remote)
            owned = False
            result['temporary_files_removed'] = True
        result['passed'] = True
    except Exception as error:
        result['error'] = str(error)
    finally:
        if owned:
            try:
                adb('shell', 'rm', '-rf', remote)
                adb('shell', 'test', '!', '-e', remote)
                result['temporary_files_removed'] = True
            except Exception:
                result['cleanup_error'] = 'owned remote cleanup failed'
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build or execute the new socket boundary; never install/rebuild an APK."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

NATIVE = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_socket_report(result):
    # The C driver's zero exit status precedes this check. Its report exposes
    # explicit invariants rather than a generic 'passed' field. Fixed counts
    # bind the intended scenarios; both ABIs execute the same deterministic
    # test source whose identity is recorded by build mode.
    expected = {'checks': 1194, 'negative_cases': 61, 'socket_scenarios': 22,
                'actual_os_udp': True, 'socket_leak_check': True,
                'live_server_interoperability': False}
    return (isinstance(result, dict) and set(result) == set(expected)
            and all(type(result[key]) is type(value) and result[key] == value
                    for key, value in expected.items()))


def socket_report_controls():
    """Bind the updated deterministic driver without relaxing report types."""
    expected = {'checks': 1194, 'negative_cases': 61, 'socket_scenarios': 22,
                'actual_os_udp': True, 'socket_leak_check': True,
                'live_server_interoperability': False}
    controls = 1
    assert valid_socket_report(expected)
    invalid = [None, [], 1194, {}, dict(expected, extra=True),
               dict(expected, checks=886, negative_cases=49, socket_scenarios=16)]
    for key in expected:
        missing = dict(expected)
        del missing[key]
        invalid.append(missing)
        for value in [None, str(expected[key]), 0.0, [], {},
                      not expected[key] if type(expected[key]) is bool else True,
                      int(expected[key]) if type(expected[key]) is bool else expected[key]+1]:
            invalid.append(dict(expected, **{key: value}))
    for result in invalid:
        assert not valid_socket_report(result), repr(result)
        controls += 1
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    controls = socket_report_controls()
    if args.self_test:
        if args.execute or args.ndk:
            parser.error('--self-test is independent of build and execution')
        proof = {'schema': 'coh-native-socket-report-controls-v1',
                 'passed': True, 'controls': controls}
        (output/'validator-controls.json').write_text(json.dumps(proof, indent=2)+'\n')
        print(json.dumps(proof))
        return
    if args.execute:
        receipt = json.loads((output/'boundary-build.json').read_text())
        binary = output/'coh-net-udp-x86_64'
        if sha(binary) != receipt['binaries']['x86_64']['sha256']:
            raise RuntimeError('Native boundary executable identity differs')
        def adb(*command):
            return subprocess.check_output(['adb', *command], text=True, timeout=60).strip()
        if adb('shell', 'getprop', 'ro.product.cpu.abi') != 'x86_64':
            raise RuntimeError('This boundary binary requires the x86_64 emulator')
        target = '/data/local/tmp/coh-native-net-boundary'
        try:
            adb('push', str(binary), target)
            adb('shell', 'chmod', '700', target)
            raw = adb('shell', 'timeout', '30', target)
            (output/'android-udp-stdout.txt').write_text(raw+'\n')
            result = json.loads(raw)
            if not valid_socket_report(result):
                raise RuntimeError('Android socket boundary failed')
            proof = {'schema': 'coh-native-android-socket-boundary-v1',
                     'passed': True, 'android_api': adb('shell', 'getprop', 'ro.build.version.sdk'),
                     'validator_controls': controls,
                     'abi': 'x86_64', 'binary_sha256': sha(binary), 'native': result,
                     'scope': 'New native UDP owner/lifecycle on Android shell; synthetic peer, no APK, real shard, account login or world session.',
                     'arm64_executed': False, 'physical_thor_accepted': False,
                     'actual_server_interoperability_verified': False}
            (output/'android-udp-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
            print(json.dumps(proof))
        finally:
            try:
                adb('shell', 'rm', '-f', target)
            except subprocess.SubprocessError:
                pass
        return
    if not args.ndk:
        parser.error('Build mode requires --ndk')
    tools = args.ndk.resolve()/'toolchains/llvm/prebuilt/linux-x86_64/bin'
    sources = [NATIVE/p for p in [
        'engine/network/coh_net.c', 'engine/network/coh_net_frame.c',
        'engine/network/coh_net_zip.c', 'engine/network/coh_net_udp.c',
        'engine/network/tests/test_udp.c', 'protocol/coh_protocol.c', 'src/coh_blowfish.c']]
    proof = {'schema': 'coh-native-android-socket-boundary-build-v1',
             'validator_controls': controls,
             'binaries': {}, 'source_sha256': {str(p.relative_to(NATIVE)): sha(p) for p in sources},
             'android_executed': False}
    for abi, target in [('arm64', 'aarch64'), ('x86_64', 'x86_64')]:
        binary = output/('coh-net-udp-'+abi)
        command = [str(tools/(target+'-linux-android26-clang')), '-std=c11', '-O2',
                   '-Wall', '-Wextra', '-Werror', '-I'+str(NATIVE/'include'),
                   '-I'+str(NATIVE/'engine/network'), *map(str, sources), '-lz', '-lm',
                   '-Wl,--no-undefined', '-o', str(binary)]
        subprocess.run(command, check=True, timeout=60)
        elf = subprocess.check_output([str(tools/'llvm-readelf'), '-h', str(binary)], text=True)
        expected = 'AArch64' if abi == 'arm64' else 'X86-64'
        if expected not in elf or 'ELF64' not in elf:
            raise RuntimeError('Wrong executable architecture')
        proof['binaries'][abi] = {'sha256': sha(binary), 'bytes': binary.stat().st_size,
                                  'command': command, 'elf': elf}
    proof['passed'] = True
    (output/'boundary-build.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps({'passed': True, 'android_executed': False}))


if __name__ == '__main__':
    main()

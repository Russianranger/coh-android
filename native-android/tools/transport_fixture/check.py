#!/usr/bin/env python3
"""Real UDP transport and lifecycle checks under ASan/UBSan on Linux LP64.

The exact source is built for the good run. Three separately built negative
controls alter a guard in a temporary copy and must fail the same real socket
driver. No mutation is written to the repository or shipped to Android.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalized(path):
    return path.read_text().replace('\r\n', '\n')


def verify_original():
    pins = json.loads((HERE / 'source-pins.json').read_text())
    spec = importlib.util.spec_from_file_location('packet_source_extract', ROOT / 'tools/protocol_fixture/prepare.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sources = {}
    for filename, pin in pins['sources'].items():
        text = normalized(REPO / pin['path'])
        if digest(text.encode()) != pin['sha256_lf']:
            raise ValueError('Original source hash differs: ' + filename)
        sources[filename] = text
    for name, pin in pins['functions'].items():
        if digest(module.extract(sources[pin['file']], name).encode()) != pin['sha256_lf']:
            raise ValueError('Original function hash differs: ' + name)
    return pins


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pins = verify_original()
    original = ROOT / 'transport/coh_transport.c'
    driver = HERE / 'driver.c'
    source_paths = [original, ROOT / 'transport/coh_transport.h', driver,
                    HERE / 'backend_driver.c', HERE / 'late_cancel_driver.c',
                    ROOT / 'protocol/coh_protocol.c', ROOT / 'protocol/coh_protocol.h',
                    ROOT / 'protocol/protocol_goldens.h', ROOT / 'src/coh_blowfish.c']
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    prefix = ['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
              '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread']
    include = ['-I' + str(ROOT / directory) for directory in ['include', 'protocol', 'transport']]
    tail = [str(ROOT / 'protocol/coh_protocol.c'), str(ROOT / 'src/coh_blowfish.c'), str(driver)]
    with tempfile.TemporaryDirectory(prefix='coh-transport-host-') as temporary:
        temporary = Path(temporary)
        binary = temporary / 'transport-host'
        wraps = ['-Wl,--wrap=poll', '-Wl,--wrap=__poll_chk']
        subprocess.run(prefix + include + [str(original)] + tail + wraps + ['-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, env=env, text=True,
                                capture_output=True, timeout=20)
        proof = json.loads(result.stdout)
        backend_binary = temporary / 'backend-host'
        subprocess.run(prefix + include + tail[:-1] + [str(HERE / 'backend_driver.c'),
                       '-o', str(backend_binary)], check=True)
        result = subprocess.run([str(backend_binary)], check=True, env=env,
                                text=True, capture_output=True, timeout=5)
        proof['injected_backend'] = json.loads(result.stdout)
        # Inject a parity error after an actual accepted datagram arrived,
        # then change the UI epoch at cleanup. The later cancellation cannot
        # turn that independent failure into an expected lifecycle abort.
        text = original.read_text()
        parity_anchor = 'if (received.wire_bytes != n || memcmp(received.wire, g->wire, n))'
        if text.count(parity_anchor) != 1:
            raise ValueError('Late-cancel parity seam differs')
        fault_text = text.replace(parity_anchor, parity_anchor[:-1] + ' || received.wire_bytes > 0)')
        fault_text = fault_text.replace('done:\n    loop_close', 'done:\n    coh_transport_cancel();\n    loop_close', 1)
        fault_source = temporary / 'parity-then-late-cancel.c'
        fault_source.write_text(fault_text)
        late_tail = tail[:-1] + [str(HERE / 'late_cancel_driver.c')]
        fault_binary = temporary / 'late-cancel-host'
        subprocess.run(prefix + include + [str(fault_source)] + late_tail + ['-o', str(fault_binary)], check=True)
        result = subprocess.run([str(fault_binary)], check=True, env=env, text=True,
                                capture_output=True, timeout=5)
        proof['parity_then_late_cancel'] = json.loads(result.stdout)
        classify_anchor = 'if (proof.session_failure) { proof.passed = 0; proof.expected_cancel = 0; }'
        unsafe_text = fault_text.replace(classify_anchor, classify_anchor +
            '\n    if (cancelled(loop.epoch)) { proof.session_failure = 0; proof.expected_cancel = 1; proof.cancelled = 1; }', 1)
        unsafe_source = temporary / 'unsafe-late-cancel.c'; unsafe_source.write_text(unsafe_text)
        unsafe_binary = temporary / 'unsafe-late-cancel'
        subprocess.run(prefix + include + [str(unsafe_source)] + late_tail + ['-o', str(unsafe_binary)], check=True)
        result = subprocess.run([str(unsafe_binary)], env=env, text=True, capture_output=True, timeout=5)
        if result.returncode != 1 or 'late-cancel driver failed:' not in result.stderr:
            raise RuntimeError('Late-cancel failure waiver negative control was not caught')
        controls = {}
        mutations = {
            'endpoint_guard_removed': ('source.sin_port != expected->sin_port', '0'),
            'cancel_epoch_ignored': ('epoch != lifecycle_epoch', '((void)epoch, 0)'),
            'failure_output_overwritten': ('Received local;\n    memset(&local',
                                          'memset(out, 0, sizeof(*out));\n    Received local;\n    memset(&local'),
        }
        for name, (before, after) in mutations.items():
            if text.count(before) != 1:
                raise ValueError('Negative control anchor is not unique: ' + name)
            mutated = temporary / (name + '.c')
            mutated.write_text(text.replace(before, after))
            executable = temporary / name
            subprocess.run(prefix + include + [str(mutated)] + tail + wraps + ['-o', str(executable)], check=True)
            result = subprocess.run([str(executable)], env=env, text=True,
                                    capture_output=True, timeout=20)
            # A sanitizer crash is not evidence that the intended semantic
            # assertion caught the regression. Require the driver's message.
            caught = result.returncode == 1 and 'transport driver failed at line ' in result.stderr
            if not caught:
                raise RuntimeError('Negative control was not caught: ' + name + '\n' + result.stderr)
            controls[name] = {'caught': True, 'returncode': result.returncode,
                              'assertion': result.stderr.strip()}
        controls['later_cancel_waives_independent_failure'] = {'caught': True,
            'returncode': 1, 'assertion': 'late-cancel driver rejected an independent parity error incorrectly waived by a later UI cancellation'}
        proof.update(schema='coh-native-udp-host-proof-v1',
                     scope='Linux LP64 real IPv4 loopback UDP; accepted NetLink v0 wire subset; no server connection, login or reliable delivery',
                     sanitizers=['AddressSanitizer', 'UndefinedBehaviorSanitizer'],
                     leak_sanitizer=False, original_source_revision=pins['source_revision'],
                     source_pins_verified=True, negative_controls=controls,
                     source_sha256={str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in source_paths})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2) + '\n')
        print(json.dumps(proof))


if __name__ == '__main__':
    main()

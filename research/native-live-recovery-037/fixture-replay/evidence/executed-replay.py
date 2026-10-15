#!/usr/bin/env python3
"""Replay recovered dormant host controls without rebuilding native artifacts.

This authenticates the retained CI report, sources, helper and command logs before
deriving a separate host-only receipt. The failed original job remains failed.
The original, byte-exact JNI test module authenticates that scoped receipt again.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[3]
OPERATION = REPO / 'research/native-live-client-operation-037'
FIXTURE = REPO / 'research/native-live-client-fixture-037'
PINS = {
    'operation_manifest': {'bytes': 11204, 'sha256': '2d5d81ad1c1d986391c150dc4320c4907a87c7e904935979448446416b8089f5'},
    'fixture_manifest': {'bytes': 2181, 'sha256': '1cbabe98ea01da98dee74cf554f2230a6c712a24bc533fb8d382020f8fd3ead3'},
    'original_ci_receipt': {'bytes': 17822, 'sha256': '9d28449756c06b539d906cf1cc1729233eebe6a63901e9eca80615c57845270f'},
    'original_ci_host_helper': {'bytes': 35664, 'sha256': 'cec249a49fa8758b4caf2f074c133fb687f5d53e1c580ab1aa8031b822d653a8'},
}


def pin(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def checked(path, expected):
    if pin(path) != {'bytes': expected['bytes'], 'sha256': expected['sha256']}:
        raise ValueError('Authentication failed: ' + str(path))


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def source_map():
    checked(OPERATION / 'SOURCE_PINS.json', PINS['operation_manifest'])
    checked(FIXTURE / 'source-pins.json', PINS['fixture_manifest'])
    sources = {}
    for item in json.loads((OPERATION / 'SOURCE_PINS.json').read_text())['files']:
        path = OPERATION / item['stageRelativePath']
        checked(path, item)
        if item['stageRelativePath'].startswith(('android/', 'tools/')):
            sources[item['stageRelativePath']] = path
    for relative, expected in json.loads((FIXTURE / 'source-pins.json').read_text())['files'].items():
        path = FIXTURE / relative
        checked(path, expected)
        if relative.startswith('source/'):
            sources[relative[len('source/'):]] = path
    if len(sources) != 13:
        raise ValueError('Unexpected recovered installed-layout source count')
    return sources


def authenticate_ci(artifact_root):
    out = artifact_root / 'out/native-live-directory-037'
    receipt = out / 'qualification.json'
    checked(receipt, PINS['original_ci_receipt'])
    original = json.loads(receipt.read_text())
    if original['status'] != 'failed' or original['failure'] != {
            'message': 'JNI dependency boundary changed', 'type': 'ValueError'}:
        raise ValueError('Original overall job outcome differs')
    if original['host_JNI'] is not True or original['host_JNI_fixture'] != {
            'schema': 'coh-live-host-JNI-fixture-v1', 'controls_passed': 28,
            'failures': 0, 'shipping_admission': False,
            'android_vm_or_game_qualified': False}:
        raise ValueError('Original host execution evidence differs')
    for relative, expected in original['source_files'].items():
        checked(artifact_root / 'tools/native_live_directory' / relative, expected)
        if relative in ('coh_live_directory_core.c', 'coh_live_directory_core.h',
                        'coh_live_directory_jni.c', 'NativeLiveDirectory.java'):
            checked(REPO / 'tools/native_live_directory' / relative, expected)
    for relative, expected in original['artifacts'].items():
        checked(out / relative, expected)
    checked(out / 'libcoh_live_directory-host.so', PINS['original_ci_host_helper'])
    commands = original['commands']
    if len(commands) != 12 or any(c['exit_code'] != 0 for c in commands):
        raise ValueError('Original command completion evidence differs')
    for command in commands:
        for stream in ('stdout', 'stderr'):
            checked(out / (command['label'] + '.' + stream), command[stream])
    host_commands = {c['label']: c for c in commands}
    for label in ('compile-host-JNI', 'compile-Java-facade-fixture', 'execute-host-JNI'):
        if label not in host_commands:
            raise ValueError('Missing host compile/execute evidence')
    execute = host_commands['execute-host-JNI']['command']
    if execute[:2] != ['java', '-Xcheck:jni'] or execute[-2] != 'io.github.russianranger.cohclientinteractive.NativeLiveDirectoryFixture':
        raise ValueError('Host JNI execution command changed')
    output = json.loads((out / 'execute-host-JNI.stdout').read_text())
    if output != original['host_JNI_fixture'] or (out / 'execute-host-JNI.stderr').read_bytes():
        raise ValueError('Host JNI raw output differs')
    return out, original


def run_suite(layout, module, expected, receipt, output):
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.pathsep.join(str(layout / p) for p in ('tools/android/interactive', 'android/guest'))
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['COH_LIVE_TEST_JNI_RECEIPT'] = str(receipt)
    command = [sys.executable, '-W', 'error::ResourceWarning', '-m', 'unittest', module, '-v']
    start = time.monotonic()
    result = subprocess.run(command, cwd=layout, env=environment, text=True,
                            capture_output=True, timeout=120)
    wall = time.monotonic() - start
    (output / (module + '.stdout')).write_text(result.stdout)
    (output / (module + '.stderr')).write_text(result.stderr)
    count = re.search(r'Ran (\d+) tests? in ', result.stderr)
    passed = result.returncode == 0 and count is not None and int(count[1]) == expected and result.stderr.rstrip().endswith('OK')
    value = {'module': module, 'expected_cases': expected, 'cases_run': int(count[1]) if count else None,
             'status': 'passed' if passed else 'failed', 'exit_code': result.returncode,
             'wall_seconds': round(wall, 6), 'command': command,
             'stdout': pin(output / (module + '.stdout')), 'stderr': pin(output / (module + '.stderr'))}
    print(json.dumps(value), flush=True)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', required=True, type=Path,
                        help='Extracted original artifact 11878700818 with out/ and tools/')
    parser.add_argument('--layout', required=True, type=Path, help='New isolated directory, never an active runtime tree')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'evidence')
    args = parser.parse_args()
    layout, output = args.layout.resolve(), args.output.resolve()
    if layout.exists():
        raise ValueError('Choose a fresh isolated layout; this runner never replaces existing paths')
    sources = source_map()
    out, original = authenticate_ci(args.artifact_root.resolve())
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / 'qualification.json', output / 'original-ci-qualification.failed.json')
    for relative, source in sources.items():
        target = layout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    installed = {relative: pin(layout / relative) for relative in sorted(sources)}
    json_write(output / 'installed-source-pins.json', installed)
    host_scope = {
        'schema': 'coh-recovered-derived-host-only-qualification-v1',
        'status': 'host-only-passed', 'host_JNI': True,
        'scope': 'Derived only from authenticated original host source/compile/execute evidence; original job remains failed',
        'original_ci_report': PINS['original_ci_receipt'], 'original_ci_status': original['status'],
        'original_ci_failure': original['failure'],
        'original_artifact_id': 11878700818, 'original_run_id': 38531585318,
        'source_files': original['source_files'],
        'artifacts': {'libcoh_live_directory-host.so': PINS['original_ci_host_helper']},
        'host_JNI_fixture': original['host_JNI_fixture'],
        'host_commands': [c for c in original['commands'] if c['label'] in (
            'compile-host-JNI', 'compile-Java-facade-fixture', 'execute-host-JNI')],
        'Android_OS_Wine_FEX_PRoot_parity': False, 'registered_Game_consumer': False,
        'physical_Thor_performance': False, 'shipping_admission': False,
    }
    json_write(output / 'derived-host-only-qualification.json', host_scope)
    with tempfile.TemporaryDirectory(prefix='coh-recovered-host-JNI-') as temporary:
        temporary = Path(temporary)
        receipt = temporary / 'qualification.json'
        json_write(receipt, host_scope)
        shutil.copyfile(out / 'libcoh_live_directory-host.so', temporary / 'libcoh_live_directory-host.so')
        suites = [run_suite(layout, module, cases, receipt, output) for module, cases in (
            ('test_client_live_directory_fixture', 75),
            ('test_client_live_directory_control', 36),
            ('test_client_live_directory_operation_jni', 5))]
        checked(temporary / 'libcoh_live_directory-host.so', PINS['original_ci_host_helper'])
    for relative, expected in installed.items():
        checked(layout / relative, expected)
    source_map()
    authenticate_ci(args.artifact_root.resolve())
    result = {
        'schema': 'coh-recovered-fixture-guest-host-JNI-replay-v1',
        'finished_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'passed' if all(s['status'] == 'passed' for s in suites) else 'failed',
        'runner': pin(Path(__file__)), 'sources': pin(output / 'installed-source-pins.json'),
        'isolated_layout': str(layout), 'suites': suites,
        'overlapping_historical_controls_not_added': True,
        'native_compile_performed': False, 'historical_test_bytes_modified': False,
        'actual_host_JNI_kernel_TCP': suites[2]['status'] == 'passed',
        'fixture_process_JNI_fstat_and_NT_evidence': 'typed host mocks and synthetic packets',
        'original_job_status': 'failed', 'original_report': pin(output / 'original-ci-qualification.failed.json'),
        'derived_host_scope_receipt': pin(output / 'derived-host-only-qualification.json'),
        'actual_Android': False, 'actual_Wine_FEX_PRoot': False, 'native_Game': False,
        'runtime_activation': False, 'APK_qualification': False, 'physical_Thor_performance': False,
    }
    json_write(output / 'replay-qualification.json', result)
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

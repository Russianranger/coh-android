#!/usr/bin/env python3
"""Build/admit an isolated Win32 receive-offset candidate; never start a service."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import tarfile
import tempfile

import hosted_auth_stage as prior
import receive_candidate

SCHEMA = 'coh-hosted-authserver-receive-build-v1'
BINARY = 'AuthServer-receive-candidate.exe'
POLICY = {'generator': 'Visual Studio 18 2026', 'architecture': 'Win32',
          'configuration': 'OptDebug', 'target': 'AuthServer', 'parallel': '2',
          'mapserver': False, 'beaconserver': False, 'service_execution': False}


def stage_source(original, destination):
    """Change only the externally archived SocketServerEx.cpp; pin both IO inputs."""
    socket = destination / 'AuthServer/src/SocketServerEx.cpp'
    io = destination / 'AuthServer/src/IOSocket.cpp'
    for path, file in ((receive_candidate.SOCKET, socket), (receive_candidate.IO, io)):
        if file.is_symlink() or not file.is_file() or file.read_bytes() != original[path]:
            raise ValueError('receive_archive_source_mismatch')
    socket.write_bytes(receive_candidate.replace_offset(original[receive_candidate.SOCKET]))
    return {'SocketServerEx.cpp': prior.sha(socket), 'IOSocket.cpp': prior.sha(io)}


def commands(source, build, patch):
    return [
        ['cmake', '-S', source, '-B', build, '-G', POLICY['generator'], '-A', POLICY['architecture'],
         '-DCOX_BUILD_MAPSERVER=OFF', '-DCOX_BUILD_BEACONSERVER=OFF', '-DPATCH_EXECUTABLE=' + str(patch)],
        ['cmake', '--build', build, '--config', POLICY['configuration'], '--parallel', POLICY['parallel'], '--target', POLICY['target']]]


def validate_corpus(proof):
    expected = {
        'executions': {'passed': True, 'checks': 5139, 'all_body_splits': 169,
                       'send_caps': 170, 'random_schedules': 100, 'coalesced_frames': 3,
                       'cryptography_executed': False, 'live_service_executed': False},
        'boundary_executions': {'passed': True, 'checks': 206, 'boundary_schedules': 134,
                       'minimum_body': 1, 'maximum_body': 4096, 'stateful_decoder_observer': True,
                       'cryptography_executed': False, 'live_service_executed': False}}
    for group, result in expected.items():
        executions = proof.get(group)
        if not isinstance(executions, dict) or set(executions) != {'release', 'asan_ubsan'}:
            raise ValueError('receive_host_execution_modes')
        for mode in ('release', 'asan_ubsan'):
            record = executions[mode]
            if (not isinstance(record, dict) or set(record) != {'binary_sha256', 'result'}
                    or not isinstance(record['binary_sha256'], str)
                    or not re.fullmatch(r'[0-9a-f]{64}', record['binary_sha256'])):
                raise ValueError('receive_host_execution_identity')
            # Canonical JSON equality also rejects bool/int substitutions.
            if json.dumps(record['result'], sort_keys=True) != json.dumps(result, sort_keys=True):
                raise ValueError('receive_host_execution_corpus')
    if (type(proof.get('source_mutation_rejections')) is not int or proof['source_mutation_rejections'] != 4
            or proof.get('original_defect_regression_reproduced') is not True
            or proof.get('general_tcp_segmentation_accepted') is not False
            or proof.get('leak_sanitizer_enabled') is not False):
        raise ValueError('receive_host_corpus_scope')


def admit(directory, receipt_sha256, binary_sha256):
    """Require caller-pinned receipt AND binary; never inherit live-login success."""
    directory = directory.resolve()
    receipt = directory / 'receipt.json'
    if receipt.is_symlink() or receipt.stat().st_size > 1024 * 1024 or prior.sha(receipt) != receipt_sha256:
        raise ValueError('receive_build_receipt_identity')
    proof = json.loads(receipt.read_text())
    if (proof.get('schema') != SCHEMA or proof.get('passed') is not True or proof.get('build_policy') != POLICY
            or proof.get('original_source_tree') != prior.ORIGINAL_TREE
            or proof.get('source_inputs_unchanged') is not True
            or proof.get('candidate_sources_unchanged_after_build') is not True
            or proof.get('service_executed') is not False
            or proof.get('encrypted_account_login_verified') is not False):
        raise ValueError('receive_build_receipt_scope')
    files = proof.get('files')
    expected_files = {BINARY, 'candidate-manifest.json', 'receive-offset.patch', 'SocketServerEx.cpp',
                      'IOSocket.cpp', 'candidate-host-qualification.json', 'candidate-CMakeCache.txt',
                      'configure-receive-candidate.log', 'build-receive-candidate.log', 'archive-original-source.log'}
    if not isinstance(files, dict) or set(files) != expected_files:
        raise ValueError('receive_build_file_set')
    for name, identity in files.items():
        path = directory / name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size > prior.LOG_LIMIT
                or identity != {'bytes': path.stat().st_size, 'sha256': prior.sha(path)}):
            raise ValueError('receive_build_file_identity')
    binary = directory / BINARY
    value = prior.pe_identity(binary, 2)
    if value['sha256'] != binary_sha256 or proof.get('candidate_binary') != value:
        raise ValueError('receive_build_binary_identity')
    manifest = json.loads((directory / 'candidate-manifest.json').read_text())
    candidate_source = (directory / 'SocketServerEx.cpp').read_bytes()
    original = candidate_source.replace(receive_candidate.AFTER, receive_candidate.BEFORE)
    if (receive_candidate.replace_offset(original) != candidate_source
            or manifest.get('candidate_source_sha256') != prior.sha(directory / 'SocketServerEx.cpp')
            or manifest.get('original_source_sha256') != receive_candidate.SOURCE_SHA256
            or prior.sha(directory / 'IOSocket.cpp') != receive_candidate.SOURCE_SHA256[receive_candidate.IO]):
        raise ValueError('receive_build_candidate_source')
    qualification = json.loads((directory / 'candidate-host-qualification.json').read_text())
    validate_corpus(qualification)
    if (qualification.get('passed') is not True or qualification.get('candidate_source_sha256') != manifest['candidate_source_sha256']
            or qualification.get('encrypted_account_login_verified') is not False):
        raise ValueError('receive_build_host_qualification')
    return {'admitted': True, 'receipt_sha256': receipt_sha256, 'binary': value,
            'scope': 'Caller-pinned nonshipping candidate Windows compilation; service/login not executed.',
            'encrypted_account_login_verified': False, 'general_tcp_segmentation_accepted': False}


def admit_host_qualification(path, expected_sha256, root):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024 or prior.sha(path) != expected_sha256:
        raise ValueError('receive_host_receipt_identity')
    proof = json.loads(path.read_text())
    here = root / 'native-android/engine/auth-interop/deployment'
    if (proof.get('schema') != 'coh-authserver-receive-candidate-qualification-v1'
            or proof.get('passed') is not True or proof.get('original_source_tree') != prior.ORIGINAL_TREE
            or proof.get('original_source_sha256') != receive_candidate.SOURCE_SHA256
            or proof.get('original_defect_regression_reproduced') is not True
            or proof.get('encrypted_account_login_verified') is not False
            or proof.get('fixture_sha256') != prior.sha(here / 'candidate_receive_fixture.cpp')
            or proof.get('boundary_fixture_sha256') != prior.sha(here / 'boundary_receive_fixture.cpp')
            or proof.get('qualifier_sha256') != prior.sha(here / 'qualify_receive_candidate.py')):
        raise ValueError('receive_host_receipt_scope')
    expected_candidate = receive_candidate.digest(receive_candidate.replace_offset(receive_candidate.sources(root)[receive_candidate.SOCKET]))
    if proof.get('candidate_source_sha256') != expected_candidate:
        raise ValueError('receive_host_candidate_identity')
    validate_corpus(proof)
    return proof


def build(args):
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = prior.require_hosted(root, output, args.expected_commit)
    originals = receive_candidate.sources(root)
    output.mkdir(parents=True)
    proof = dict(identity, schema=SCHEMA, passed=False, build_policy=POLICY, commands=[],
                 service_executed=False, encrypted_account_login_verified=False,
                 authenticated_db_map_handoff_verified=False, general_tcp_segmentation_accepted=False)
    runner = prior.Commands(output)
    try:
        patch = Path(os.environ['ProgramFiles']) / 'Git/usr/bin/patch.exe'
        if not patch.is_file():
            raise ValueError('qualified_patch_tool_unavailable')
        with tempfile.TemporaryDirectory(prefix='coh-receive-build-', dir=os.environ['RUNNER_TEMP']) as temporary:
            temporary = Path(temporary)
            # Reuse exact Linux release/sanitizer evidence; no unsupported GCC flags on MSVC.
            admit_host_qualification(args.host_qualification, args.expected_host_qualification_sha256, root)
            shutil.copy2(args.host_qualification, output / 'candidate-host-qualification.json')
            staged = temporary / 'candidate'
            manifest = receive_candidate.prepare(root, staged)
            for name in ('SocketServerEx.cpp', 'IOSocket.cpp', 'receive-offset.patch', 'candidate-manifest.json'):
                shutil.copy2(staged / name, output / name)
            archive = temporary / 'original-source.tar'
            runner.run('archive-original-source', ['git', '-C', root, 'archive', '--format=tar', '--output=' + str(archive), args.expected_commit, 'upstream/ouroboros'])
            proof['source_archive_sha256'] = prior.sha(archive)
            with tarfile.open(archive) as tar:
                tar.extractall(temporary / 'source', filter='data')
            source, build_directory = temporary / 'source/upstream/ouroboros', temporary / 'build'
            proof['candidate_sources'] = stage_source(originals, source)
            configure, compile_command = commands(source, build_directory, patch)
            runner.run('configure-receive-candidate', configure, timeout=900)
            runner.run('build-receive-candidate', compile_command, timeout=1500)
            binary = build_directory / 'bin/OptDebug/AuthServer.exe'
            proof['candidate_binary'] = prior.pe_identity(binary, 2)
            shutil.copy2(binary, output / BINARY)
            shutil.copy2(build_directory / 'CMakeCache.txt', output / 'candidate-CMakeCache.txt')
            proof['candidate_sources_unchanged_after_build'] = proof['candidate_sources'] == {
                'SocketServerEx.cpp': prior.sha(source / 'AuthServer/src/SocketServerEx.cpp'),
                'IOSocket.cpp': prior.sha(source / 'AuthServer/src/IOSocket.cpp')}
            proof['passed'] = proof['candidate_sources_unchanged_after_build'] and prior.sha(output / BINARY) == proof['candidate_binary']['sha256']
    except Exception as error:
        proof['failure'] = str(error) if isinstance(error, ValueError) else type(error).__name__
    finally:
        proof['commands'] = runner.records
        try:
            proof['source_inputs_unchanged'] = not prior.capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android/engine/auth-interop'])
        except Exception:
            proof['source_inputs_unchanged'] = False
        proof['passed'] = proof['passed'] and proof['source_inputs_unchanged']
        proof['files'] = {path.name: {'bytes': path.stat().st_size, 'sha256': prior.sha(path)}
                          for path in output.iterdir() if path.is_file() and path.name != 'receipt.json'}
        (output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    compile_parser = sub.add_parser('build')
    compile_parser.add_argument('--source-root', type=Path, required=True)
    compile_parser.add_argument('--expected-commit', required=True)
    compile_parser.add_argument('--output', type=Path, required=True)
    compile_parser.add_argument('--host-qualification', type=Path, required=True)
    compile_parser.add_argument('--expected-host-qualification-sha256', required=True)
    admission = sub.add_parser('admit')
    admission.add_argument('--stage', type=Path, required=True)
    admission.add_argument('--expected-receipt-sha256', required=True)
    admission.add_argument('--expected-binary-sha256', required=True)
    args = parser.parse_args()
    result = build(args) if args.operation == 'build' else admit(args.stage, args.expected_receipt_sha256, args.expected_binary_sha256)
    print(json.dumps(result if args.operation == 'admit' else {'passed': result['passed'], 'failure': result.get('failure'), 'encrypted_account_login_verified': False}))
    raise SystemExit(0 if result.get('passed', result.get('admitted', False)) else 1)

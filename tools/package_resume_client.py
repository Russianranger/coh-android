#!/usr/bin/env python3
"""Package a separately identified resume-only diagnostic TestClient.

The artifact supplies only the new executable and its build receipts. It does
not replace or redistribute the accepted reference runtime. Its imports must
resolve against that runtime before the diagnostic executable can be staged.
"""
import argparse
import json
from pathlib import Path
import re
import shutil

from package_reference_runtime import dependency_report, file_record, require
from prepare_resume_client_source import RECEIPT, expected_resume_receipt
from prepare_runtime import input_files

ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = 'TestClient.exe'
SYMBOL = 'TestClient.pdb'
BUILD_ROLE = 'resume_only_diagnostic_testclient'
STATUS = 'diagnostic_build_packaged_runtime_unverified'
PACKAGE_FILES = frozenset((EXECUTABLE, RECEIPT, 'build-info.json'))


def verify_receipt(receipt, root):
    require(isinstance(receipt, dict) and
            isinstance(receipt.get('postgresql_build_input'), dict),
            'Missing resume-client PostgreSQL build receipt')
    expected = expected_resume_receipt(
        root=root, postgresql_build_input=receipt['postgresql_build_input'])
    require(receipt == expected,
            'Resume-client build receipt differs from pinned source, patch or PostgreSQL inputs')
    return expected


def package(binary_directory, build_input, cmake_cache, output,
            repository_commit, run_url='', root=ROOT):
    require(re.fullmatch(r'[a-f0-9]{40}', repository_commit), 'Invalid repository commit')
    require(not output.exists() and not output.is_symlink(), 'Output must be a new directory')
    receipt_record = file_record(build_input)
    receipt = json.loads(build_input.read_text(encoding='utf-8'))
    verify_receipt(receipt, root)
    require(re.search(r'^COH_PG_PERSISTENCE_TESTS:BOOL=OFF$', cmake_cache.read_text(), re.MULTILINE),
            'Resume-client build must have persistence fixture mode OFF')
    executable_record = file_record(binary_directory / EXECUTABLE)
    symbol_record = file_record(binary_directory / SYMBOL)
    manifest = {
        'schema_version': 1,
        'build_role': BUILD_ROLE,
        'status': STATUS,
        'source_commit': receipt['source_commit'],
        'repository_commit': repository_commit,
        'configuration': 'OptDebug',
        'architecture': 'Win32',
        'run_url': run_url,
        'postgresql_persistence_fixture': False,
        'resume_client_build_input': receipt,
        'files': {EXECUTABLE: executable_record, RECEIPT: receipt_record},
        'symbols': {SYMBOL: symbol_record},
        'dependency_validation': 'deferred_until_accepted_reference_runtime',
    }
    # No DLLs are copied from this build. Import metadata is recorded above;
    # final dependency resolution needs the separately accepted runtime.
    try:
        for directory, inputs in (
                (output / 'runtime', {EXECUTABLE: binary_directory / EXECUTABLE,
                                      RECEIPT: build_input}),
                (output / 'symbols', {SYMBOL: binary_directory / SYMBOL})):
            directory.mkdir(parents=True)
            for name, source in inputs.items():
                shutil.copy2(source, directory / name)
                expected = manifest['symbols' if name == SYMBOL else 'files'][name]
                require(file_record(directory / name) == expected,
                        'Build input changed while packaging: ' + name)
            (directory / 'build-info.json').write_text(
                json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    except BaseException:
        if output.exists():
            shutil.rmtree(output)
        raise
    return manifest


def verify_resume_client_package(package_directory, expected_repository_commit,
                                 accepted_runtime_manifest, root=ROOT):
    """Verify provenance, Win32 bytes and imports before a private runtime copy.

    ``accepted_runtime_manifest`` must come from the existing reference-runtime
    byte/provenance validation. This function never modifies that runtime.
    """
    require(re.fullmatch(r'[a-f0-9]{40}', expected_repository_commit),
            'Invalid expected repository commit')
    files = dict(input_files(package_directory))
    require(set(files) == PACKAGE_FILES,
            'Resume-client package must contain only the executable and two flat receipts')
    manifest = json.loads(files['build-info.json'].read_text(encoding='utf-8'))
    require(isinstance(manifest, dict) and manifest.get('schema_version') == 1,
            'Unsupported resume-client manifest schema')
    require(manifest.get('build_role') == BUILD_ROLE and manifest.get('status') == STATUS,
            'Expected separately identified resume-only diagnostic build')
    require(manifest.get('repository_commit') == expected_repository_commit,
            'Resume-client repository commit mismatch')
    require(manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32',
            'Expected OptDebug / Win32 resume client')
    require(manifest.get('postgresql_persistence_fixture') is False,
            'Resume-client build must have persistence fixture mode OFF')
    receipt = manifest.get('resume_client_build_input')
    verify_receipt(receipt, root)
    require(manifest.get('source_commit') == receipt['source_commit'],
            'Resume-client source commit mismatch')
    require(isinstance(accepted_runtime_manifest, dict) and
            accepted_runtime_manifest.get('source_commit') == receipt['source_commit'],
            'Accepted runtime source commit mismatch')
    require(receipt['postgresql_build_input'] ==
            accepted_runtime_manifest.get('postgresql_build_input'),
            'Resume-client and accepted runtime PostgreSQL receipts differ')
    records = manifest.get('files')
    require(isinstance(records, dict) and set(records) == {EXECUTABLE, RECEIPT},
            'Unexpected resume-client packaged-file records')
    for name in (EXECUTABLE, RECEIPT):
        require(records[name] == file_record(files[name]),
                'Resume-client file size/SHA-256 or PE metadata mismatch: ' + name)
    require(json.loads(files[RECEIPT].read_text(encoding='utf-8')) == receipt,
            'Packaged and embedded resume-client receipts differ')
    runtime_records = accepted_runtime_manifest.get('files')
    require(isinstance(runtime_records, dict) and runtime_records,
            'Missing accepted runtime file records')
    # Replacement in this in-memory import inventory does not change any bytes
    # or metadata in the accepted package. Check the complete dependency graph.
    dependencies = dependency_report({**runtime_records, EXECUTABLE: records[EXECUTABLE]})
    require(not dependencies['unresolved'],
            'Resume-client imports unresolved against accepted runtime: ' +
            '; '.join(dependencies['unresolved']))
    return files[EXECUTABLE], manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary-directory', type=Path, required=True)
    parser.add_argument('--build-input', type=Path, required=True)
    parser.add_argument('--cmake-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--run-url', default='')
    args = parser.parse_args()
    manifest = package(args.binary_directory, args.build_input, args.cmake_cache,
                       args.output, args.repository_commit, args.run_url)
    print(json.dumps({'status': manifest['status'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()

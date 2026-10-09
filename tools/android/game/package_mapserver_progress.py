#!/usr/bin/env python3
"""Package a separately receipted MapServer progress executable and symbols."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from package_reference_runtime import dependency_report, file_record, require
from prepare_runtime import input_files
from prepare_mapserver_progress_source import expected_progress_receipt, RECEIPT

BUILD_ROLE = 'mapserver_progress'
PROFILE = 'dispatch_progress_v1'
STATUS = 'diagnostic_build_packaged_runtime_unverified'
DATA_COMMIT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
PACKAGE_FILES = frozenset(('MapServer.exe', RECEIPT, 'build-info.json'))
ACCEPTED_REFERENCE = 'docs/reference-runtime-evidence/build-36088012664.json'
HEX64 = re.compile(r'[0-9a-f]{64}')


def read_json(path):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 8 * 1024 * 1024,
            'Missing or oversized MapServer progress receipt: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify_receipt(receipt, root=ROOT):
    require(isinstance(receipt, dict) and isinstance(receipt.get('game_build_input'), dict),
            'Missing MapServer progress creation source receipt')
    expected = expected_progress_receipt(root, receipt['game_build_input'])
    require(receipt == expected, 'MapServer progress source receipt differs from pinned source or overlay')
    return expected


def verify_mapserver_progress_manifest(manifest, expected_repository_commit, accepted_runtime_manifest, root=ROOT):
    """Verify source, format and import provenance before selecting candidate bytes."""
    require(re.fullmatch(r'[0-9a-f]{40}', expected_repository_commit), 'Invalid expected repository commit')
    require(isinstance(manifest, dict) and manifest.get('schema_version') == 1
            and manifest.get('build_role') == BUILD_ROLE and manifest.get('status') == STATUS,
            'Expected separately identified MapServer progress candidate')
    require(manifest.get('repository_commit') == expected_repository_commit,
            'MapServer progress repository commit mismatch')
    require(manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('runtime_execution_validated') is False
            and manifest.get('build_targets') == ['MapServer']
            and HEX64.fullmatch(str(manifest.get('cmake_cache_sha256', ''))),
            'MapServer progress must be unverified MapServer-only OptDebug / Win32 with fixture mode OFF')
    receipt = verify_receipt(manifest.get('build_input'), root)
    require(isinstance(accepted_runtime_manifest, dict)
            and isinstance(accepted_runtime_manifest.get('files'), dict) and accepted_runtime_manifest['files'],
            'Missing accepted reference runtime manifest')
    require(manifest.get('source_commit') == receipt['source_commit'] == accepted_runtime_manifest.get('source_commit')
            and manifest.get('data_commit') == DATA_COMMIT, 'MapServer progress source/data commit mismatch')
    require(receipt['game_build_input']['postgresql_build_input'] == accepted_runtime_manifest.get('postgresql_build_input'),
            'MapServer progress and accepted runtime PostgreSQL receipts differ')
    require(manifest.get('progress_contract') == receipt['progress_contract'],
            'MapServer progress contract differs from source receipt')
    records = manifest.get('files')
    require(isinstance(records, dict) and set(records) == PACKAGE_FILES - {'build-info.json'},
            'Unexpected MapServer progress file records')
    total = 0
    for name, info in records.items():
        require(isinstance(info, dict) and type(info.get('size')) is int and 0 < info['size'] <= 512 * 1024 * 1024
                and HEX64.fullmatch(str(info.get('sha256', ''))), 'Invalid MapServer progress file record: ' + name)
        total += info['size']
        if name == 'MapServer.exe':
            require(info.get('pe_machine') == 0x14c
                    and all(isinstance(info.get(key), list) and all(isinstance(item, str) for item in info[key])
                            for key in ('imports', 'delay_imports')), 'MapServer progress executable must be PE32')
        else:
            require(set(info) == {'size', 'sha256'} and info['size'] <= 8 * 1024 * 1024,
                    'Invalid MapServer progress source receipt record')
    require(total <= 512 * 1024 * 1024, 'MapServer progress payload exceeds its bound')
    # The embedded source receipt has an exact independently checked file record.
    encoded = json.dumps(receipt, indent=2) + '\n'
    require(any(records[RECEIPT] == {'size': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                for value in (encoded.encode(), encoded.replace('\n', '\r\n').encode())),
            'MapServer progress embedded source receipt bytes differ')
    symbols = manifest.get('symbols')
    require(isinstance(symbols, dict) and set(symbols) == {'MapServer.pdb'}
            and isinstance(symbols['MapServer.pdb'], dict)
            and set(symbols['MapServer.pdb']) == {'size', 'sha256'}
            and type(symbols['MapServer.pdb'].get('size')) is int
            and 0 < symbols['MapServer.pdb']['size'] <= 512 * 1024 * 1024
            and HEX64.fullmatch(str(symbols['MapServer.pdb'].get('sha256', ''))),
            'Missing MapServer progress symbol receipt')
    dependencies = dependency_report({**accepted_runtime_manifest['files'], 'MapServer.exe': records['MapServer.exe']})
    require(not dependencies['unresolved'],
            'MapServer progress imports unresolved against accepted runtime: ' + '; '.join(dependencies['unresolved']))
    require(manifest.get('dependency_report') == dependencies
            and manifest.get('dependency_validation') == 'accepted_reference_runtime',
            'MapServer progress dependency report differs')
    return manifest


def verify_mapserver_progress_package(directory, expected_repository_commit, accepted_runtime_manifest, root=ROOT):
    paths = dict(input_files(directory))
    require(set(paths) == PACKAGE_FILES, 'MapServer progress package must contain only MapServer and flat receipts')
    manifest = read_json(paths['build-info.json'])
    verify_mapserver_progress_manifest(manifest, expected_repository_commit, accepted_runtime_manifest, root)
    for name, info in manifest['files'].items():
        require(file_record(paths[name]) == info, 'MapServer progress file size/SHA-256 or PE metadata mismatch: ' + name)
    require(read_json(paths[RECEIPT]) == manifest['build_input'],
            'Packaged and embedded MapServer progress source receipts differ')
    return paths['MapServer.exe'], manifest


def package(args, accepted_runtime_manifest=None, root=ROOT):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists() and not args.output.is_symlink(), 'Output must be a new directory')
    if accepted_runtime_manifest is None:
        accepted_runtime_manifest = read_json(args.reference / 'build-info.json')
        require(accepted_runtime_manifest == read_json(root / ACCEPTED_REFERENCE),
                'Dependency donor differs from accepted reference receipt')
    receipt = verify_receipt(read_json(args.build_input), root)
    require(args.cache.is_file() and not args.cache.is_symlink(), 'Missing MapServer CMake cache')
    values = re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$',
                        args.cache.read_text(encoding='utf-8-sig'), re.MULTILINE)
    require(values == ['OFF'], 'MapServer progress build must have persistence fixture mode OFF')
    sources = {'MapServer.exe': args.directory / 'MapServer.exe', RECEIPT: args.build_input}
    symbols = {'MapServer.pdb': args.directory / 'MapServer.pdb'}
    records = {name: file_record(path) for name, path in sources.items()}
    manifest = {'schema_version': 1, 'build_role': BUILD_ROLE, 'status': STATUS,
                'source_commit': receipt['source_commit'], 'data_commit': DATA_COMMIT,
                'repository_commit': args.repository_commit, 'configuration': 'OptDebug', 'architecture': 'Win32',
                'run_url': args.run_url, 'postgresql_persistence_fixture': False,
                'runtime_execution_validated': False, 'build_targets': ['MapServer'],
                'build_input': receipt, 'progress_contract': receipt['progress_contract'],
                'cmake_cache_sha256': hashlib.sha256(args.cache.read_bytes()).hexdigest(),
                'files': records, 'symbols': {name: file_record(path) for name, path in symbols.items()},
                'dependency_validation': 'accepted_reference_runtime',
                'dependency_report': dependency_report({**accepted_runtime_manifest['files'],
                                                       'MapServer.exe': records['MapServer.exe']}),
                'scope': 'Separate MapServer progress diagnostic; accepted binaries and receipts remain unchanged'}
    verify_mapserver_progress_manifest(manifest, args.repository_commit, accepted_runtime_manifest, root)
    try:
        for folder, inputs, expected in ((args.output / 'runtime', sources, records),
                                        (args.output / 'symbols', symbols, manifest['symbols'])):
            folder.mkdir(parents=True)
            for name, source in inputs.items():
                shutil.copy2(source, folder / name)
                require(file_record(folder / name) == expected[name], 'Build input changed while packaging: ' + name)
            (folder / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        verify_mapserver_progress_package(args.output / 'runtime', args.repository_commit, accepted_runtime_manifest, root)
    except BaseException:
        shutil.rmtree(args.output, ignore_errors=True)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'build-input', 'cache', 'reference', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--run-url', default='')
    args = parser.parse_args()
    manifest = package(args)
    print(json.dumps({'status': manifest['status'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()

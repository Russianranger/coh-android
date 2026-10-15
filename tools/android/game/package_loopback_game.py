#!/usr/bin/env python3
"""Package isolated loopback MapServer/create/resume candidates, never acceptance.

Only executables and source receipts enter the runtime donor. DLLs remain owned
by the accepted reference runtime, against which the full import graph is checked.
"""
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
from prepare_game_loopback_source import expected_game_receipt

BUILD_ROLE = 'loopback_game_diagnostic'
STATUS = 'diagnostic_build_packaged_runtime_unverified'
EXECUTABLES = ('MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe')
RECEIPTS = {'creation': 'game-create-build-input.json', 'resume': 'game-resume-build-input.json'}
PACKAGE_FILES = frozenset((*EXECUTABLES, *RECEIPTS.values(), 'build-info.json'))
SYMBOLS = tuple(str(Path(name).with_suffix('.pdb')) for name in EXECUTABLES)
ACCEPTED_REFERENCE = 'docs/reference-runtime-evidence/build-36088012664.json'
HEX64 = re.compile(r'[0-9a-f]{64}')


def read_json(path):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 8 * 1024 * 1024,
            'Missing or oversized loopback build receipt: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify_receipt(receipt, variant, root=ROOT):
    require(isinstance(receipt, dict) and isinstance(receipt.get('postgresql_build_input'), dict),
            'Missing loopback PostgreSQL source receipt')
    expected = expected_game_receipt(root=root, postgresql_build_input=receipt['postgresql_build_input'],
                                     variant=variant)
    require(receipt == expected,
            'Loopback game source receipt differs from pinned source, variant or overlay: ' + variant)
    return expected


def verify_loopback_game_manifest(manifest, expected_repository_commit, accepted_runtime_manifest, root=ROOT):
    """Verify embedded provenance and imports before selecting any candidate bytes.

    The caller must independently validate the accepted reference manifest and
    any copied executable bytes. This helper also serves the hosted verifier,
    where the separate donor files are represented by the embedded manifest.
    """
    require(re.fullmatch(r'[0-9a-f]{40}', expected_repository_commit), 'Invalid expected repository commit')
    require(isinstance(manifest, dict) and manifest.get('schema_version') == 1
            and manifest.get('build_role') == BUILD_ROLE and manifest.get('status') == STATUS,
            'Expected separately identified loopback game candidate')
    require(manifest.get('repository_commit') == expected_repository_commit,
            'Loopback game repository commit mismatch')
    require(manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('runtime_execution_validated') is False,
            'Loopback game must be unverified OptDebug / Win32 with fixture mode OFF')
    variants = manifest.get('variants')
    require(isinstance(variants, dict) and set(variants) == set(RECEIPTS), 'Loopback game build variants differ')
    require(isinstance(accepted_runtime_manifest, dict)
            and isinstance(accepted_runtime_manifest.get('files'), dict)
            and accepted_runtime_manifest['files'], 'Missing accepted reference runtime manifest')
    for variant, value in variants.items():
        require(isinstance(value, dict) and value.get('postgresql_persistence_fixture') is False
                and HEX64.fullmatch(str(value.get('cmake_cache_sha256', ''))),
                'Missing fixture-OFF build-cache evidence: ' + variant)
        receipt = verify_receipt(value.get('build_input'), variant, root)
        require(manifest.get('source_commit') == receipt['source_commit'] == accepted_runtime_manifest.get('source_commit'),
                'Loopback game source commit mismatch')
        require(receipt['postgresql_build_input'] == accepted_runtime_manifest.get('postgresql_build_input'),
                'Loopback game and accepted runtime PostgreSQL receipts differ')
    records = manifest.get('files')
    require(isinstance(records, dict) and set(records) == PACKAGE_FILES - {'build-info.json'},
            'Unexpected loopback game file records')
    total = 0
    for name, info in records.items():
        require(isinstance(info, dict) and type(info.get('size')) is int and 0 < info['size'] <= 512 * 1024 * 1024
                and HEX64.fullmatch(str(info.get('sha256', ''))), 'Invalid loopback game file record: ' + name)
        total += info['size']
        if name in EXECUTABLES:
            require(info.get('pe_machine') == 0x14c
                    and all(isinstance(info.get(key), list) and all(isinstance(item, str) for item in info[key])
                            for key in ('imports', 'delay_imports')), 'Loopback executable must be PE32: ' + name)
        else:
            require(set(info) == {'size', 'sha256'} and info['size'] <= 8 * 1024 * 1024,
                    'Invalid loopback source receipt record: ' + name)
    require(total <= 512 * 1024 * 1024, 'Loopback game payload exceeds its bound')
    dependencies = dependency_report({**accepted_runtime_manifest['files'],
                                     **{name: records[name] for name in EXECUTABLES}})
    require(not dependencies['unresolved'],
            'Loopback game imports unresolved against accepted runtime: ' + '; '.join(dependencies['unresolved']))
    require(manifest.get('dependency_report') == dependencies, 'Loopback game dependency report differs')
    require(manifest.get('dependency_validation') == 'accepted_reference_runtime',
            'Missing accepted reference dependency validation')
    return manifest


def verify_loopback_game_package(directory, expected_repository_commit, accepted_runtime_manifest, root=ROOT):
    paths = dict(input_files(directory))
    require(set(paths) == PACKAGE_FILES, 'Loopback game package must contain only three executables and flat receipts')
    manifest = read_json(paths['build-info.json'])
    verify_loopback_game_manifest(manifest, expected_repository_commit, accepted_runtime_manifest, root)
    for name, info in manifest['files'].items():
        require(file_record(paths[name]) == info, 'Loopback game file size/SHA-256 or PE metadata mismatch: ' + name)
    for variant, name in RECEIPTS.items():
        require(read_json(paths[name]) == manifest['variants'][variant]['build_input'],
                'Packaged and embedded loopback game source receipts differ: ' + variant)
    return {name: paths[name] for name in EXECUTABLES}, manifest


def package(args, accepted_runtime_manifest=None, root=ROOT):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Invalid repository commit')
    require(not args.output.exists() and not args.output.is_symlink(), 'Output must be a new directory')
    if accepted_runtime_manifest is None:
        accepted_runtime_manifest = read_json(args.reference / 'build-info.json')
        require(accepted_runtime_manifest == read_json(root / ACCEPTED_REFERENCE),
                'Dependency donor differs from accepted reference receipt')
    sources, variants = {}, {}
    for variant, prefix in (('creation', 'create'), ('resume', 'resume')):
        build_input = getattr(args, prefix + '_build_input')
        receipt = verify_receipt(read_json(build_input), variant, root)
        cache = getattr(args, prefix + '_cache')
        require(cache.is_file() and not cache.is_symlink(), 'Missing CMake cache: ' + variant)
        text = cache.read_text(encoding='utf-8-sig')
        values = re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', text, re.MULTILINE)
        require(values == ['OFF'], 'Loopback game build must have persistence fixture mode OFF: ' + variant)
        variants[variant] = {'build_input': receipt, 'postgresql_persistence_fixture': False,
                             'cmake_cache_sha256': hashlib.sha256(cache.read_bytes()).hexdigest()}
        sources[RECEIPTS[variant]] = build_input
    sources.update({'MapServer.exe': args.create_directory / 'MapServer.exe',
                    'TestClientCreate.exe': args.create_directory / 'TestClient.exe',
                    'TestClientResume.exe': args.resume_directory / 'TestClient.exe'})
    symbols = {str(Path(name).with_suffix('.pdb')): path.with_suffix('.pdb')
               for name, path in sources.items() if name in EXECUTABLES}
    records = {name: file_record(path) for name, path in sources.items()}
    manifest = {'schema_version': 1, 'build_role': BUILD_ROLE, 'status': STATUS,
                'source_commit': variants['creation']['build_input']['source_commit'],
                'repository_commit': args.repository_commit, 'configuration': 'OptDebug', 'architecture': 'Win32',
                'run_url': args.run_url, 'postgresql_persistence_fixture': False,
                'runtime_execution_validated': False, 'variants': variants, 'files': records,
                'symbols': {name: file_record(path) for name, path in symbols.items()},
                'dependency_validation': 'accepted_reference_runtime',
                'dependency_report': dependency_report({**accepted_runtime_manifest['files'],
                                                       **{name: records[name] for name in EXECUTABLES}}),
                'scope': 'Separate loopback-only hosted qualification candidate; accepted donors remain unchanged'}
    verify_loopback_game_manifest(manifest, args.repository_commit, accepted_runtime_manifest, root)
    try:
        for folder, inputs, expected in ((args.output / 'runtime', sources, records),
                                        (args.output / 'symbols', symbols, manifest['symbols'])):
            folder.mkdir(parents=True)
            for name, source in inputs.items():
                shutil.copy2(source, folder / name)
                require(file_record(folder / name) == expected[name], 'Build input changed while packaging: ' + name)
            (folder / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        verify_loopback_game_package(args.output / 'runtime', args.repository_commit, accepted_runtime_manifest, root)
    except BaseException:
        shutil.rmtree(args.output, ignore_errors=True)
        raise
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('create-directory', 'resume-directory', 'create-build-input', 'resume-build-input',
                 'create-cache', 'resume-cache', 'reference', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--repository-commit', required=True)
    ap.add_argument('--run-url', default='')
    args = ap.parse_args()
    manifest = package(args)
    print(json.dumps({'status': manifest['status'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()

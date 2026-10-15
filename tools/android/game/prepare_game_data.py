#!/usr/bin/env python3
"""Stage the complete reviewed game data for a private Wine runtime.

Uses the existing immutable-source runtime assembler without binaries. The
accepted generated schemas remain a separate input and are not overlaid here.
Only data/ and an exact file inventory are published; the guest creates its own
tools/ marker, credentials and generated caches in a private runtime copy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_runtime as runtime
import runtime_asset_bundle as assets

SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
ASSET_MANIFEST_SHA256 = 'cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f'
ASSET_ARCHIVE_SHA256 = '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07'
ASSET_ARCHIVE_BYTES = 615541018
ASSET_COUNT = 16721
ASSET_BYTES = 985644857
DATA_COUNT = 173011
DATA_BYTES = 2977730517
MAX_FILES = 250000
MAX_BYTES = 4 * 1024**3
MAX_MANIFEST = 64 * 1024**2
MANIFEST = 'game-data-manifest.json'
FORBIDDEN_SUFFIXES = frozenset(('.exe', '.dll', '.pdb', '.pigg', '.bin', '.bounds'))
require = runtime.require


def regular_bytes(path, limit):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
            'Missing, linked or oversized input: ' + str(path))
    return path.read_bytes()


def reviewed_assets(directory, manifest, receipt, root=ROOT):
    """Recheck every extracted asset against the external reviewed trust anchor."""
    manifest_bytes = regular_bytes(manifest, assets.MAX_MANIFEST)
    require(hashlib.sha256(manifest_bytes).hexdigest() == ASSET_MANIFEST_SHA256,
            'Reviewed asset manifest hash differs')
    document = assets.decode_manifest(manifest_bytes)
    require(manifest_bytes == assets.canonical(document), 'Reviewed asset manifest is not canonical')
    records = assets.validate_manifest(document, assets.provenance(root))
    accepted = assets.decode_manifest(regular_bytes(receipt, 64 * 1024))
    for key, value in {'source_commit': SOURCE, 'text_data_commit': DATA,
                       'archive_sha256': ASSET_ARCHIVE_SHA256,
                       'archive_bytes': ASSET_ARCHIVE_BYTES,
                       'manifest_sha256': ASSET_MANIFEST_SHA256,
                       'asset_count': ASSET_COUNT, 'asset_bytes': ASSET_BYTES}.items():
        require(accepted.get(key) == value, 'Reviewed asset receipt differs: ' + key)
    require(document['source_commit'] == SOURCE and document['text_data_commit'] == DATA
            and len(records) == ASSET_COUNT and sum(r['size'] for r in records) == ASSET_BYTES,
            'Reviewed asset provenance/count/bytes differ')
    expected = {record['path']: record for record in records}
    actual = {}
    for name, path in runtime.input_files(Path(directory)):
        require(name in expected, 'Unlisted extracted asset: ' + name)
        record = expected[name]
        require(path.stat().st_size == record['size'] and runtime.sha256(path) == record['sha256'],
                'Extracted asset size/hash differs: ' + name)
        with path.open('rb') as stream:
            require(stream.read(8) != b'CrypticS', 'Serialized cache disguised as an asset')
        actual[name] = path
    require(set(actual) == set(expected), 'Missing extracted assets')
    return records


def expected_data(root, asset_records):
    """Bind copied text back to immutable receipts, including source cfg priority."""
    expected = {}
    for filename, commit, data_only in (('content-lock.json', DATA, True),
                                         ('upstream-lock.json', SOURCE, False)):
        lock = json.loads(regular_bytes(root / filename, 64 * 1024))
        require(lock['commit'] == commit, 'Immutable source/data pin differs')
        path = runtime.safe_relative(lock['manifest'])
        manifest = json.loads(regular_bytes(root / path, MAX_MANIFEST))
        require(manifest['commit'] == commit, 'Immutable manifest pin differs')
        for record in manifest['entries']:
            name = record['path']
            if data_only:
                if not name.startswith('data/') or runtime.excluded_reason(name[5:]):
                    continue
            elif not (name.startswith('data/server/db/') and Path(name).suffix.casefold() == '.cfg'):
                continue
            runtime.safe_relative(name)
            key = name.casefold()
            require(not data_only or key not in expected, 'Ambiguous immutable data path')
            expected[key] = {'bytes': record['size'], 'sha256': record['sha256']}
    # The existing assembler preserves authoritative text at any asset collision.
    for record in asset_records:
        expected.setdefault(('data/' + record['path']).casefold(),
                            {'bytes': record['size'], 'sha256': record['sha256']})
    require(len(expected) == DATA_COUNT and sum(r['bytes'] for r in expected.values()) == DATA_BYTES,
            'Reviewed full-data assembly count/bytes differ')
    return expected


def checked_inventory(directory, expected):
    files, seen, total = {}, set(), 0
    for name, path in runtime.input_files(directory / 'data'):
        name = 'data/' + name
        key = name.casefold()
        require(key not in seen and key in expected, 'Unexpected or ambiguous staged data: ' + name)
        require(Path(name).suffix.casefold() not in FORBIDDEN_SUFFIXES
                and runtime.excluded_reason(name[5:]) is None, 'Executable or generated cache in game data')
        size = path.stat().st_size
        total += size
        require(len(files) < MAX_FILES and total <= MAX_BYTES, 'Game data exceeds inventory bounds')
        record = {'bytes': size, 'sha256': runtime.sha256(path)}
        require(record == expected[key], 'Staged data differs from reviewed input: ' + name)
        seen.add(key)
        files[name] = record
    require(seen == set(expected) and len(files) == DATA_COUNT and total == DATA_BYTES,
            'Staged game-data inventory is incomplete')
    return dict(sorted(files.items())), total


def prepare(asset_data, output, *, asset_manifest=None, asset_receipt=None, root=ROOT):
    root, asset_data, output = Path(root), Path(asset_data), Path(output)
    assets.safe_new(output, root)
    require(asset_data.resolve() not in output.resolve().parents, 'Output cannot be inside asset inputs')
    for parent in asset_data.parents:
        require(not parent.is_symlink(), 'Linked asset input ancestor')
    records = reviewed_assets(asset_data,
        Path(asset_manifest) if asset_manifest else root / 'assets/reference-inputs-manifest.json',
        Path(asset_receipt) if asset_receipt else root / 'assets/reference-inputs-receipt.json', root)
    expected = expected_data(root, records)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-game-data-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'runtime'
        assembled = runtime.stage(staging, asset_data=(asset_data,), binaries=None, root=root)
        require(assembled['source_commit'] == SOURCE and assembled['data_commit'] == DATA
                and assembled['executables_supplied'] is False
                and len(assembled['binary_asset_files']) == ASSET_COUNT,
                'Unexpected runtime assembly provenance')
        require({p.name for p in staging.iterdir()} == {'data', 'tools', 'runtime-inputs.json'},
                'Unexpected full-runtime assembly contents')
        files, total = checked_inventory(staging, expected)
        document = {'format': 1, 'scope': 'reviewed_game_data',
                    'source_commit': SOURCE, 'data_commit': DATA, 'files': files,
                    'file_count': len(files), 'total_bytes': total,
                    'asset_manifest_sha256': ASSET_MANIFEST_SHA256,
                    'asset_archive_sha256': ASSET_ARCHIVE_SHA256,
                    'android_execution_validated': False, 'gameplay_validated': False}
        encoded = assets.canonical(document)
        require(len(encoded) <= MAX_MANIFEST, 'Game data manifest exceeds size bound')
        # Reserve the new destination only after all large payload checks pass.
        output.mkdir(exist_ok=False)
        try:
            (staging / 'data').rename(output / 'data')
            with (output / MANIFEST).open('xb') as stream:
                stream.write(encoded)
        except BaseException:
            shutil.rmtree(output)
            raise
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset-data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--asset-manifest', type=Path)
    parser.add_argument('--asset-receipt', type=Path)
    args = parser.parse_args()
    result = prepare(args.asset_data, args.output, asset_manifest=args.asset_manifest,
                     asset_receipt=args.asset_receipt)
    print(json.dumps({'output': str(args.output), 'file_count': result['file_count'],
                      'total_bytes': result['total_bytes']}))


if __name__ == '__main__':
    main()

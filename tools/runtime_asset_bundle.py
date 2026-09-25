#!/usr/bin/env python3
"""Build/stage the seven reviewed base-asset donors without copying caches or text.

The external manifest is the trust anchor: keep it with the reviewed code. A ZIP
and its own embedded manifest alone do not establish trusted provenance. Passing
these checks establishes byte identity, not gameplay or serializer compatibility.

Builds default to DEFLATE level 6 with fixed entry order/timestamps. Compressed
archive bytes can vary between zlib versions; the receipt identifies the exact
archive bytes. --compression stored retains the uncompressed transport option.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
import tempfile
import zipfile
import zlib

from inspect_piggs import inspect

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
TEXT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
DONORS = ('fonts.pigg', 'player.pigg', 'geom.pigg', 'geomBC.pigg',
          'stage1a.pigg', 'stage1b.pigg', 'stage1f.pigg')
SUFFIXES = frozenset(('.geo', '.texture', '.anim', '.ttf', '.ttc'))
MANIFEST_NAME = 'asset-manifest.json'
MAX_ENTRIES = 20000
MAX_TOTAL = 1024 ** 3
MAX_ENTRY = 512 * 1024 ** 2
MAX_MANIFEST = 16 * 1024 ** 2
MAX_ARCHIVE = MAX_TOTAL + MAX_MANIFEST + 32 * 1024 ** 2
INCOMPLETE = '.inspection-incomplete'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(document):
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('utf-8')


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def decode_manifest(data):
    require(len(data) <= MAX_MANIFEST, 'Manifest size limit exceeded')
    return json.loads(data, object_pairs_hook=no_duplicate_keys)


def safe_asset(name):
    require(isinstance(name, str) and name and len(name.encode('utf-8')) <= 1024 and name == name.lower(),
            'Asset paths must be nonempty canonical lowercase')
    require(all(ord(c) >= 32 and ord(c) != 127 and c not in '<>:"\\|?*' for c in name),
            'Unsafe asset path: ' + name)
    parts = name.split('/')
    require(all(p not in ('', '.', '..') and not p.endswith((' ', '.')) for p in parts),
            'Unsafe asset path: ' + name)
    require(not any(re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])', p.split('.')[0], re.I)
                    for p in parts), 'Reserved Windows path: ' + name)
    require(not any(p in ('.git', 'bin', 'geobin', '_devonly', 'markerfiles') for p in parts),
            'Generated/development asset path: ' + name)
    require(PurePosixPath(name).suffix in SUFFIXES, 'Not a selected binary asset: ' + name)
    return PurePosixPath(name)


def safe_new(path, root=ROOT):
    require(not path.exists() and not path.is_symlink(), 'Output already exists: ' + str(path))
    resolved, immutable = path.resolve(), (root / 'upstream').resolve()
    require(resolved != immutable and immutable not in resolved.parents and resolved != root.resolve(),
            'Output must be outside immutable snapshots and repository root')
    for ancestor in path.parents:
        require(not ancestor.is_symlink(), 'Output parent is a symlink: ' + str(ancestor))


def provenance(root=ROOT):
    lock = json.loads((root / 'upstream-lock.json').read_text())
    content = json.loads((root / 'content-lock.json').read_text())
    require(lock['commit'] == SOURCE and content['commit'] == TEXT and content['source_pair'] == SOURCE,
            'Source/text pins changed; review and regenerate asset bundle policy')
    records = []
    for filename, key in (('base-assets-assessment.json', 'new_archives'),
                          ('base-geometry-assessment.json', 'archive'),
                          ('stage1-assets-assessment.json', 'new_archives')):
        doc = json.loads((root / 'docs' / filename).read_text())
        require(doc['source_commit'] == SOURCE and doc['text_data_commit'] == TEXT,
                'Asset assessment pins differ')
        records.extend(doc[key] if isinstance(doc[key], list) else [doc[key]])
    found = {r['archive']: r for r in records if r['archive'] in DONORS}
    require(set(found) == set(DONORS), 'Missing reviewed donor provenance')
    summary = json.loads((root / 'docs/runtime-assembly-assessment.json').read_text())
    require(summary['source_commit'] == SOURCE and summary['text_data_commit'] == TEXT,
            'Assembly assessment pins differ')
    return {'source_commit': SOURCE, 'text_data_commit': TEXT,
            'donors': [{'archive': name, 'bytes': found[name]['bytes'], 'sha256': found[name]['sha256']}
                       for name in DONORS],
            'asset_count': summary['base_binary_asset_files'],
            'asset_bytes': summary['base_binary_asset_bytes'],
            'extensions': summary['base_binary_extensions']}


def validate_manifest(doc, expected):
    require(isinstance(doc, dict) and doc.get('schema_version') == 1 and
            doc.get('status') == 'reviewed_base_assets_byte_checked_runtime_unvalidated',
            'Unsupported or incomplete asset manifest')
    for key in ('source_commit', 'text_data_commit', 'donors', 'asset_count', 'asset_bytes', 'extensions'):
        require(doc.get(key) == expected[key], 'Manifest differs from reviewed ' + key)
    records = doc.get('files')
    require(isinstance(records, list) and 0 < len(records) <= MAX_ENTRIES and
            len(records) == doc['asset_count'], 'Manifest entry count mismatch or limit exceeded')
    require([r.get('path') for r in records if isinstance(r, dict)] ==
            sorted(r.get('path') for r in records if isinstance(r, dict)), 'Manifest is not sorted')
    seen, directories, total, extensions = set(), set(), 0, Counter()
    for record in records:
        require(isinstance(record, dict) and set(record) == {'path', 'size', 'sha256', 'donor'},
                'Invalid asset record')
        path = safe_asset(record['path'])
        key = str(path).casefold()
        require(key not in seen and key not in directories, 'Duplicate/case-colliding asset path')
        seen.add(key)
        for parent in path.parents:
            if str(parent) != '.':
                require(str(parent).casefold() not in seen, 'Asset file/directory collision')
                directories.add(str(parent).casefold())
        require(type(record['size']) is int and 0 < record['size'] <= MAX_ENTRY,
                'Asset entry size limit exceeded')
        require(isinstance(record['sha256'], str) and re.fullmatch('[0-9a-f]{64}', record['sha256']),
                'Invalid asset SHA256')
        require(record['donor'] in {d['archive'] for d in expected['donors']}, 'Unknown asset donor')
        total += record['size']
        require(total <= MAX_TOTAL, 'Asset total byte limit exceeded')
        extensions[path.suffix] += 1
    require(total == doc['asset_bytes'] and dict(extensions) == doc['extensions'],
            'Manifest byte/extension totals mismatch')
    return records


def compression_type(compression):
    require(compression in ('deflate', 'stored'), 'Unsupported bundle compression')
    return zipfile.ZIP_DEFLATED if compression == 'deflate' else zipfile.ZIP_STORED


def compression_receipt(compression):
    compression_type(compression)
    return {'zip_compression': compression,
            'deflate_level': 6 if compression == 'deflate' else None,
            'zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION if compression == 'deflate' else None,
            'archive_byte_reproducibility': ('fixed metadata/order; DEFLATE bytes may vary by zlib version'
                                             if compression == 'deflate' else 'fixed metadata/order; uncompressed payloads')}


def zip_info(name, compression='stored'):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = compression_type(compression)
    # ZipInfo's public compress_level property was added after Python 3.12.
    # The supported older runtimes expose the same value as _compresslevel.
    if hasattr(info, 'compress_level'):
        info.compress_level = 6 if compression == 'deflate' else None
    else:
        info._compresslevel = 6 if compression == 'deflate' else None
    return info


def write_bundle(archive, assets, manifest_bytes, records, compression='deflate'):
    """Fix metadata/order; DEFLATE bytes are reproducible for the same zlib."""
    compression_type(compression)
    with zipfile.ZipFile(archive, 'x', allowZip64=True) as bundle:
        bundle.writestr(zip_info(MANIFEST_NAME, compression), manifest_bytes)
        for record in records:
            path = assets / safe_asset(record['path'])
            require(not path.is_symlink() and path.is_file(), 'Nonregular staged asset')
            require(path.stat().st_size == record['size'] and sha256(path) == record['sha256'],
                    'Staged asset changed: ' + record['path'])
            with path.open('rb') as source, bundle.open(zip_info('assets/' + record['path'], compression), 'w') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)


def build(directory, archive, manifest, receipt, root=ROOT, compression='deflate'):
    compression_type(compression)
    expected = provenance(root)
    outputs = (archive, manifest, receipt)
    require(len({p.resolve() for p in outputs}) == len(outputs), 'Outputs must have distinct paths')
    require(directory.is_dir() and not directory.is_symlink(), 'Donor input must be a real directory')
    for output in outputs:
        safe_new(output, root)
        require(directory.resolve() not in output.resolve().parents, 'Output must be outside donor input')
    # Validate the complete donor set before extracting any data.
    for donor in expected['donors']:
        path = directory / donor['archive']
        require(path.is_file() and not path.is_symlink(), 'Missing/nonregular donor: ' + donor['archive'])
        require(path.stat().st_size == donor['bytes'] and sha256(path) == donor['sha256'],
                'Reviewed donor size/SHA256 mismatch: ' + donor['archive'])
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='asset-bundle-', dir=archive.parent) as temporary:
        temporary = Path(temporary)
        assets = temporary / 'assets'
        assets.mkdir()
        (assets / INCOMPLETE).write_text('Do not use incomplete asset inspection.\n')
        records, staged, budget = [], set(), [MAX_TOTAL + 256 * 1024 ** 2]
        for donor in expected['donors']:
            report = inspect(directory / donor['archive'], None, MAX_ENTRY, budget, assets, staged)
            require(report['sha256'] == donor['sha256'] and report['bytes'] == donor['bytes'],
                    'Donor changed during inspection: ' + donor['archive'])
            for entry in report['entries']:
                if entry['category'] == 'candidate_binary_asset':
                    path = entry['path'].lower()
                    safe_asset(path)
                    require(not entry.get('serialized_header'), 'Serialized cache disguised as binary asset')
                    records.append({'path': path, 'size': entry['size'], 'sha256': entry['sha256'],
                                    'donor': donor['archive']})
            print('Verified ' + donor['archive'], flush=True)
        doc = dict(expected, schema_version=1,
                   status='reviewed_base_assets_byte_checked_runtime_unvalidated',
                   files=sorted(records, key=lambda record: record['path']))
        validate_manifest(doc, expected)
        manifest_bytes = canonical(doc)
        (assets / INCOMPLETE).unlink()
        candidate = temporary / 'bundle.zip'
        write_bundle(candidate, assets, manifest_bytes, doc['files'], compression)
        result = {'schema_version': 1, 'source_commit': SOURCE, 'text_data_commit': TEXT,
                  'archive_sha256': sha256(candidate), 'archive_bytes': candidate.stat().st_size,
                  'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
                  'asset_count': doc['asset_count'], 'asset_bytes': doc['asset_bytes'],
                  'runtime_compatibility': 'unvalidated', **compression_receipt(compression)}
        # Publish receipt last; failed builds never leave an apparently complete receipt.
        with archive.open('xb') as target, candidate.open('rb') as source:
            shutil.copyfileobj(source, target, 1024 * 1024)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open('xb') as target:
            target.write(manifest_bytes)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with receipt.open('xb') as target:
            target.write(canonical(result))
    return result


def bounded_zip_directory(archive):
    """Check the small EOCD before zipfile allocates central-directory records.

    This transport format needs neither multi-disk ZIP, ZIP64 nor ZIP comments.
    Reject those variants instead of trusting potentially unbounded metadata.
    """
    size = archive.stat().st_size
    require(size >= 22, 'Truncated ZIP directory')
    with archive.open('rb') as source:
        source.seek(-22, os.SEEK_END)
        signature, disk, start_disk, disk_count, count, directory_size, offset, comment = struct.unpack(
            '<4s4H2LH', source.read(22))
    require(signature == b'PK\x05\x06' and disk == start_disk == comment == 0 and
            disk_count == count and 0 < count <= MAX_ENTRIES + 1,
            'Unsupported or oversized ZIP directory')
    require(directory_size <= 32 * 1024 ** 2 and offset + directory_size == size - 22,
            'ZIP directory bounds/size mismatch')
    # ZipFile parses until directory_size is exhausted; it does not use the
    # EOCD count as an allocation bound. Count actual fixed headers first, with
    # only a 46-byte buffer, so a forged low EOCD count cannot allocate hundreds
    # of thousands of ZipInfo objects before stage() checks len(infolist()).
    central_header = struct.Struct('<4s6H3L5H2L')
    consumed, actual_count = 0, 0
    with archive.open('rb') as source:
        source.seek(offset)
        while consumed < directory_size:
            require(directory_size - consumed >= central_header.size,
                    'Truncated ZIP central directory header')
            data = source.read(central_header.size)
            require(len(data) == central_header.size, 'Truncated ZIP central directory header')
            fields = central_header.unpack(data)
            require(fields[0] == b'PK\x01\x02' and fields[13] == 0 and
                    all(fields[index] != 0xffffffff for index in (8, 9, 16)),
                    'Unsupported ZIP central directory record')
            actual_count += 1
            require(actual_count <= count and actual_count <= MAX_ENTRIES + 1,
                    'ZIP central directory count exceeds declared count or limit')
            variable_size = sum(fields[index] for index in (10, 11, 12))
            consumed += central_header.size
            require(variable_size <= directory_size - consumed,
                    'ZIP central directory variable fields exceed bounds')
            source.seek(variable_size, os.SEEK_CUR)
            consumed += variable_size
    require(actual_count == count, 'ZIP central directory count differs from EOCD')


def stage(archive, manifest, output, *, expected=None, root=ROOT):
    expected = provenance(root) if expected is None else expected
    safe_new(output, root)
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size <= MAX_ARCHIVE,
            'Input must be a bounded regular ZIP')
    require(manifest.is_file() and not manifest.is_symlink() and manifest.stat().st_size <= MAX_MANIFEST,
            'External manifest must be a bounded regular file')
    manifest_bytes = manifest.read_bytes()
    records = validate_manifest(decode_manifest(manifest_bytes), expected)
    require(manifest_bytes == canonical(decode_manifest(manifest_bytes)), 'Manifest must use canonical JSON')
    selected = {'assets/' + r['path']: r for r in records}
    bounded_zip_directory(archive)
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        require(len(infos) == len(records) + 1 and len(infos) <= MAX_ENTRIES + 1,
                'ZIP entry count mismatch or limit exceeded')
        names, total = set(), 0
        for info in infos:
            require(info.filename not in names, 'Duplicate ZIP path')
            names.add(info.filename)
            require(info.filename == MANIFEST_NAME or info.filename in selected, 'Unlisted/unsafe ZIP path')
            mode = (info.external_attr >> 16) & 0xffff
            require(stat.S_IFMT(mode) == stat.S_IFREG and not info.is_dir(), 'ZIP entry is not a regular file')
            require(not info.flag_bits & 1 and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    'Encrypted/unsupported ZIP compression')
            wanted = len(manifest_bytes) if info.filename == MANIFEST_NAME else selected[info.filename]['size']
            require(info.file_size == wanted and info.file_size <= MAX_ENTRY, 'ZIP entry size mismatch/limit')
            total += info.file_size
        require(total <= MAX_TOTAL + MAX_MANIFEST, 'ZIP total byte limit exceeded')
        require(names == set(selected) | {MANIFEST_NAME}, 'Missing/unlisted ZIP entries')
        require(bundle.read(MANIFEST_NAME) == manifest_bytes, 'Embedded/external manifest mismatch')
        output.mkdir(parents=True)
        marker = output / INCOMPLETE
        marker.write_text('Do not use incomplete asset bundle extraction.\n')
        # Every metadata/path check completes before touching the output. A later
        # payload/CRC failure keeps the marker, also recognized by prepare_runtime.
        for record in records:
            target = output / safe_asset(record['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            digest, size, prefix = hashlib.sha256(), 0, b''
            with bundle.open('assets/' + record['path']) as source, target.open('xb') as destination:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    size += len(block)
                    require(size <= record['size'], 'Inflated asset exceeds declared size')
                    if not prefix:
                        prefix = block[:8]
                    digest.update(block)
                    destination.write(block)
            require(prefix != b'CrypticS', 'Serialized cache disguised as binary asset')
            require(size == record['size'] and digest.hexdigest() == record['sha256'],
                    'Asset size/SHA256 mismatch: ' + record['path'])
        marker.unlink()
        require(not marker.exists(), 'Incomplete marker could not be removed')
    return {'asset_count': len(records), 'asset_bytes': sum(r['size'] for r in records),
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'runtime_compatibility': 'unvalidated'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('build', help='Verify reviewed original PIGGs and build a ZIP with fixed metadata/order')
    make.add_argument('--directory', type=Path, required=True)
    make.add_argument('--archive', type=Path, required=True)
    make.add_argument('--manifest', type=Path, required=True)
    make.add_argument('--receipt', type=Path, required=True)
    make.add_argument('--compression', choices=('deflate', 'stored'), default='deflate',
                      help='Default: deflate level 6; archive bytes may vary by zlib version, receipt records exact hash')
    unpack = commands.add_parser('stage', help='Verify ZIP against reviewed external manifest and extract assets')
    unpack.add_argument('--archive', type=Path, required=True)
    unpack.add_argument('--manifest', type=Path, required=True)
    unpack.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        result = build(args.directory, args.archive, args.manifest, args.receipt, compression=args.compression)
    else:
        result = stage(args.archive, args.manifest, args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print('Asset bundle failed: ' + str(error), file=sys.stderr)
        sys.exit(1)

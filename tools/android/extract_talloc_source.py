#!/usr/bin/env python3
"""Recover pinned talloc source from the accepted runtime's source artifact."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile

import build_proot
from dbserver.host_dbserver_smoke import ACCEPTED_RUNTIME_COMMIT, ACCEPTED_RUNTIME_MANIFEST


ACCEPTED_RUNTIME_RUN = 36364550345
MEMBER_NAME = 'sources/talloc-2.4.3.tar.gz'
MAX_METADATA_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_TAR_BYTES = 32 * 1024 * 1024
MAX_MEMBERS = 64


def require(condition, message):
    if not condition:
        raise ValueError(message)


def record(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def bounded_regular_file(path, limit):
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    require(not path.is_symlink(), 'Source input must not be a symlink')
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), 'Source input must be a regular file')
        require(0 < info.st_size <= limit, 'Source input exceeds its size bound or is empty')
        data = stream.read(limit + 1)
        require(len(data) == info.st_size, 'Source input changed or exceeds its size bound')
    return data


def verify_record(data, expected, label):
    require(isinstance(expected, dict) and type(expected.get('bytes')) is int
            and record(data) == {key: expected.get(key) for key in ('bytes', 'sha256')},
            label + ' size/SHA-256 mismatch')


def extract_source(assets, bundle, output):
    require(not output.exists() and not output.is_symlink(), 'Output must be fresh')
    manifest_data = bounded_regular_file(assets / 'runtime-manifest.json', MAX_METADATA_BYTES)
    require(record(manifest_data)['sha256'] == ACCEPTED_RUNTIME_MANIFEST,
            'Requires the exact accepted 0.1.5 runtime manifest')
    manifest = json.loads(manifest_data)
    require(manifest.get('format') == 1 and manifest.get('repository_commit') == ACCEPTED_RUNTIME_COMMIT,
            'Accepted runtime identity differs')
    build_data = bounded_regular_file(assets / 'proot-build.json', MAX_METADATA_BYTES)
    verify_record(build_data, manifest.get('files', {}).get('proot-build.json'), 'PRoot build receipt')
    build = json.loads(build_data)
    require(build.get('schema_version') == 1 and build.get('target') == 'android-arm64'
            and build.get('source_commit') == build_proot.PROOT_COMMIT
            and build.get('source_tree') == build_proot.PROOT_TREE
            and build.get('talloc_version') == '2.4.3', 'Accepted source recipe identity differs')
    source_receipt = build.get('corresponding_sources', {})
    require(source_receipt.get('file') == 'proot-corresponding-sources.tar.gz',
            'Corresponding-source bundle identity differs')
    bundle_data = bounded_regular_file(bundle, MAX_SOURCE_BYTES)
    verify_record(bundle_data, source_receipt, 'Corresponding-source bundle')
    with gzip.GzipFile(fileobj=io.BytesIO(bundle_data)) as stream:
        tar_data = stream.read(MAX_TAR_BYTES + 1)
    require(len(tar_data) <= MAX_TAR_BYTES, 'Expanded source bundle exceeds its size bound')
    source = None
    with tarfile.open(fileobj=io.BytesIO(tar_data), mode='r:') as archive:
        for count, member in enumerate(archive, 1):
            require(count <= MAX_MEMBERS, 'Source bundle has too many members')
            if member.name != MEMBER_NAME:
                continue
            require(source is None, 'Duplicate talloc source member')
            require(member.isfile() and not member.issparse(), 'Talloc source must be a regular member')
            require(0 < member.size <= MAX_SOURCE_BYTES, 'Talloc source exceeds its size bound')
            with archive.extractfile(member) as stream:
                source = stream.read(MAX_SOURCE_BYTES + 1)
            require(len(source) == member.size, 'Talloc source member is truncated')
    require(source is not None, 'Exact talloc source member is missing')
    verify_record(source, build.get('sources', {}).get('talloc-2.4.3.tar.gz'), 'Talloc source')
    require(record(source)['sha256'] == build_proot.TALLOC_SHA256, 'Talloc source differs from build recipe SHA-256')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.' + output.name + '.', dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        # Link publication is atomic and refuses an existing file or symlink.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'format': 1, 'accepted_runtime_run_id': ACCEPTED_RUNTIME_RUN,
            'runtime_manifest_sha256': record(manifest_data)['sha256'],
            'proot_build_receipt': record(build_data), 'corresponding_sources': record(bundle_data),
            'member': dict(record(source), name=MEMBER_NAME), 'output': str(output),
            'build_recipe_unchanged': True, 'runtime_execution_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extract_source(args.assets, args.bundle, args.output), indent=2))


if __name__ == '__main__':
    main()

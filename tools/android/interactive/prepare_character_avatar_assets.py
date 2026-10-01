#!/usr/bin/env python3
"""Verify the small pinned default-male supplement independently of base assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = 'character-avatar-defaults.zip'
MANIFEST = 'character-avatar-defaults-manifest.json'
ARCHIVE_PIN = {'bytes': 1842488, 'sha256': '03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29'}
MANIFEST_PIN = {'bytes': 28554, 'sha256': '2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7'}
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
SCOPE = 'default_male_avatar_supplement'
FILE_COUNT, PAYLOAD_BYTES = 21, 2980122


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or linked avatar input: ' + path.name)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def bundle_contract():
    return {'scope': SCOPE, 'archive': ARCHIVE, 'archive_pin': dict(ARCHIVE_PIN),
            'manifest_file': MANIFEST, 'manifest_pin': dict(MANIFEST_PIN),
            'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES,
            'installation': 'private_client_worktree_missing_files_only',
            'imported_assets_modified': False, 'prepared_caches_modified': False,
            'runtime_visual_validated': False, 'gameplay_validated': False}


def verify(archive, manifest, *, root=ROOT):
    archive, manifest = Path(archive), Path(manifest)
    require(pin(manifest) == MANIFEST_PIN, 'Avatar manifest differs from reviewed metadata')
    require(pin(archive) == ARCHIVE_PIN, 'Avatar archive differs from reviewed payload bytes')
    document = json.loads(manifest.read_text())
    require(document.get('format') == 1 and document.get('scope') == SCOPE
            and document.get('source_commit') == SOURCE and document.get('data_commit') == DATA,
            'Avatar baseline identity differs')
    require(document.get('archive') == {'filename': ARCHIVE, **ARCHIVE_PIN}
            and document.get('file_count') == FILE_COUNT and document.get('payload_bytes') == PAYLOAD_BYTES
            and document.get('runtime_visual_validated') is False and document.get('gameplay_validated') is False,
            'Avatar package scope or inventory size differs')
    provenance = document.get('provenance', {})
    require(provenance.get('source_archives_fully_downloaded') is False
            and provenance.get('source_archive_sha256_verified') is False,
            'Selected ranges must not claim complete source archive verification')
    files = document.get('files', {})
    require(isinstance(files, dict) and len(files) == FILE_COUNT
            and sum(value['bytes'] for value in files.values()) == PAYLOAD_BYTES
            and set(files) == set(provenance.get('entries', {})), 'Avatar file inventory differs')
    accepted = json.loads((Path(root)/'assets/reference-inputs-manifest.json').read_text())
    base_names = {'data/' + record['path'].casefold() for record in accepted['files']}
    require(not base_names.intersection(files), 'Avatar supplement would replace an accepted imported asset')
    with zipfile.ZipFile(archive) as payload:
        names = payload.namelist()
        require(len(names) == len(set(names)) == FILE_COUNT and set(names) == set(files),
                'Avatar ZIP member set differs')
        for name, expected in files.items():
            path = PurePosixPath(name)
            require(name == name.lower() and path.as_posix() == name and '..' not in path.parts
                    and '\\' not in name and ':' not in name
                    and (name.startswith('data/player_library/') and path.suffix == '.geo'
                         or name.startswith('data/texture_library/') and path.suffix == '.texture'),
                    'Unsafe avatar path')
            entry = payload.getinfo(name)
            require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_ISREG(entry.external_attr >> 16)
                    and entry.file_size == expected['bytes'] and 0 < entry.file_size <= PAYLOAD_BYTES,
                    'Invalid avatar ZIP entry')
            raw = payload.read(entry)
            require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'],
                    'Avatar payload hash differs: ' + name)
            donor = provenance['entries'][name]
            require(hashlib.md5(raw).hexdigest() == donor['md5_table']
                    and donor['integrity'] == 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed',
                    'Avatar payload differs from selected PIGG entry')
    return document


def prepare(output, *, root=ROOT):
    output = Path(output)
    require(output.is_dir() and not output.is_symlink(), 'Avatar output must be a regular directory')
    source = Path(root)/'assets'
    verify(source/ARCHIVE, source/MANIFEST, root=root)
    for name in (ARCHIVE, MANIFEST):
        require(not (output/name).exists() and not (output/name).is_symlink(), 'Avatar output already exists')
    for name in (ARCHIVE, MANIFEST):
        shutil.copyfile(source/name, output/name)
    verify(output/ARCHIVE, output/MANIFEST, root=root)
    return bundle_contract()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(ROOT/'assets'/ARCHIVE, ROOT/'assets'/MANIFEST)
        print(json.dumps(bundle_contract(), indent=2))
    elif args.output:
        print(json.dumps(prepare(args.output), indent=2))
    else:
        parser.error('Select --verify or --output')

#!/usr/bin/env python3
"""Draft modern CI donor hydration. No native process, database or APK signing.

Authenticates the exact .36 donor and all Assets 1.0.0 leaves before copying.
The resulting runtime can be passed to existing stage_app_assets.stage() with
server_variant='thor_certified_startup'; it is not runtime qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
from zipfile import ZipFile

DONOR = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
IMPORTS = {'atlas-import.properties', 'atlas-text.zip', 'atlas-text-index.tsv', 'atlas-assets-index.tsv'}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular donor/payload required: ' + path.name)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def inspect_donor(apk):
    require(pin(apk) == DONOR, 'Exact .36 donor APK required')
    with ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK member')
        docs = {name: json.loads(archive.read('assets/runtime/' + name))
                for name in ('runtime-manifest.json', 'client-manifest.json', 'asset-pack-manifest.json')}
        runtime, client, pack = [docs[name] for name in docs]
        require(runtime['format'] == client['format'] == pack['format'] == 1
                and pack['id'] == 'coh-assets' and pack['version'] == '1.0.0', 'Donor manifest identity differs')
        require(len(runtime['files']) == 89 and len(client['files']) == 81 and len(pack['files']) == 23,
                'Modern donor inventory differs')
        require(all(runtime['files'][name] == expected for name, expected in client['files'].items()),
                'Inner/outer donor inventory differs')
        external = {name.split('/', 1)[1] for name in pack['files'] if name.startswith('runtime/')}
        missing = {name for name in runtime['files'] if 'assets/runtime/' + name not in names}
        require(missing == external and len(missing) == 19, 'External runtime closure differs')
        for name, expected in runtime['files'].items():
            if name in external:
                require(pack['files']['runtime/' + name] == expected, 'External pin differs: ' + name)
                continue
            member = archive.getinfo('assets/runtime/' + name)
            require(not member.is_dir() and not member.flag_bits & 1
                    and not stat.S_ISLNK(member.external_attr >> 16), 'Unsafe runtime member')
            require(raw_pin(archive.read(member)) == expected, 'Packaged donor pin differs: ' + name)
        require('assets/atlas/atlas-import.properties' in names, 'Missing original importer contract')
    return docs


def prepare(apk, payloads, output):
    docs = inspect_donor(apk)
    runtime, client, pack = [docs[name] for name in docs]
    payloads, output = Path(payloads), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Fresh output required')
    # Validate every external leaf before publishing any staged input.
    for name, expected in pack['files'].items():
        require(pin(payloads / Path(name).name) == expected, 'External payload differs: ' + name)
    output.mkdir(parents=True)
    runtime_dir, imports = output / 'runtime', output / 'atlas'
    runtime_dir.mkdir(); imports.mkdir()
    with ZipFile(apk) as archive:
        for name, expected in runtime['files'].items():
            target = runtime_dir / name
            member = 'assets/runtime/' + name
            if member in archive.namelist():
                with archive.open(member) as source, target.open('xb') as destination:
                    shutil.copyfileobj(source, destination, 1024 * 1024)
            else:
                shutil.copyfile(payloads / name, target)
            require(pin(target) == expected, 'Staged runtime pin differs: ' + name)
        # The self manifest is authenticated by the complete donor APK hash.
        (runtime_dir / 'runtime-manifest.json').write_bytes(archive.read('assets/runtime/runtime-manifest.json'))
        for name in IMPORTS:
            target = imports / name
            if name == 'atlas-import.properties':
                target.write_bytes(archive.read('assets/atlas/' + name))
            else:
                shutil.copyfile(payloads / name, target)
    return {'donor': DONOR, 'runtime_files': len(runtime['files']), 'client_files': len(client['files']),
            'external_files': len(pack['files']), 'runtime': str(runtime_dir), 'imports': str(imports),
            'reference_archive': str(payloads / 'atlas-assets.zip'),
            'native_runtime_executed': False, 'database_accessed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--payloads', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    require((args.payloads is None) == (args.output is None), 'Payloads and output are required together')
    if args.output:
        print(json.dumps(prepare(args.apk, args.payloads, args.output), indent=2))
    else:
        docs = inspect_donor(args.apk)
        print(json.dumps({'exact_donor_verified': True,
                          'runtime_files': len(docs['runtime-manifest.json']['files']),
                          'external_files': len(docs['asset-pack-manifest.json']['files']),
                          'native_runtime_executed': False}, indent=2))


if __name__ == '__main__':
    main()

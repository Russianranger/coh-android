#!/usr/bin/env python3
"""Stage a new runtime directory from pinned text data and optional external inputs.

Does not execute game programs, install a database, or modify imported snapshots.
Extract PIGGs into a separate directory first; supply its data root as --asset-data.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = ('client.ps1', 'db.ps1', 'map.ps1', 'templates.ps1',
             'create-bins.ps1', 'start-local.ps1')


def copy_file(source, destination):
    if Path(source).is_symlink():
        raise ValueError('Symlinks are not allowed in runtime inputs: ' + str(source))
    return shutil.copy2(source, destination)


def ignore_generated(directory, names):
    ignored = []
    for name in names:
        if (Path(directory) / name).is_symlink():
            raise ValueError('Symlinks are not allowed in runtime inputs')
        lower = name.lower()
        if lower in ('.git', 'bin', 'geobin', '_devonly') or lower.endswith(('.bin', '.bin.meta', '.bounds')):
            ignored.append(name)
    return ignored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Must not already exist')
    parser.add_argument('--asset-data', type=Path, help='Already extracted binary asset data directory')
    parser.add_argument('--binaries', type=Path, help='Exact source build outputs, including build-info.txt')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Output already exists; use a new directory to preserve existing data')
    if ROOT / 'upstream' in output.parents:
        parser.error('Output must be outside the immutable upstream snapshots')
    for directory in (args.asset_data, args.binaries):
        if directory and not directory.is_dir():
            parser.error('Input is not a directory: ' + str(directory))
        if directory and (output == directory.resolve() or directory.resolve() in output.parents):
            parser.error('Output must not be inside an input directory')
    source_lock = json.loads((ROOT / 'upstream-lock.json').read_text())
    data_lock = json.loads((ROOT / 'content-lock.json').read_text())
    for lock in ('upstream-lock.json', 'content-lock.json'):
        subprocess.run([sys.executable, str(ROOT / 'tools/verify_source.py'), '--lock', lock], check=True)
    binary_files = []
    if args.binaries:
        build_info = args.binaries / 'build-info.txt'
        if not build_info.is_file() or ('Commit: ' + source_lock['commit']) not in {
                line.strip() for line in build_info.read_text().splitlines()}:
            parser.error('Binaries must include build-info.txt identifying the exact locked source commit')
        for name in ('CityOfHeroes.exe', 'MapServer.exe', 'DbServer.exe', 'pig.exe'):
            if not (args.binaries / name).is_file():
                parser.error('Missing build output: ' + name)
        binary_files = [p for p in args.binaries.iterdir() if p.suffix.lower() in ('.exe', '.dll')]
        binary_files.append(build_info)
    output.mkdir(parents=True)
    if args.asset_data:
        shutil.copytree(args.asset_data, output / 'data', ignore=ignore_generated,
                        copy_function=copy_file)
    # Restore authoritative text after extraction, without resetting any Git tree.
    shutil.copytree(ROOT / data_lock['destination'] / 'data', output / 'data',
                    dirs_exist_ok=True, copy_function=copy_file)
    config = output / 'data/server/db'
    config.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / source_lock['destination'] / 'data/server/db').glob('*.cfg'):
        copy_file(path, config / path.name)
    (output / 'tools').mkdir()
    for name in LAUNCHERS:
        text = (ROOT / data_lock['destination'] / 'tools' / name).read_text()
        (output / 'tools' / name).write_text(text.replace('Game.exe', 'CityOfHeroes.exe'), encoding='utf-8')
    hashes = {}
    for path in binary_files:
        copy_file(path, output / path.name)
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'status': 'staged_not_gameplay_validated',
                'source_commit': source_lock['commit'], 'data_commit': data_lock['commit'],
                'binary_assets_supplied': bool(args.asset_data),
                'binary_asset_compatibility': 'unverified',
                'executables_supplied': bool(args.binaries), 'build_file_sha256': hashes,
                'templates_and_bins_generated': False, 'database_installed': False,
                'launcher_changes': 'Game.exe -> CityOfHeroes.exe; source-pinned DB configs'}
    (output / 'runtime-inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Staged ' + str(output) + '; assets, DLL completeness, database and gameplay still require validation.')


if __name__ == '__main__':
    main()

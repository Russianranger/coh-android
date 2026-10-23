#!/usr/bin/env python3
"""Add the ARM64 option to extracted app assets; never builds/signs an APK."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

import armport_client_package as package

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': package.digest(path)}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def stage(source, armport, output, repository_commit):
    package.require(re.fullmatch('[0-9a-f]{40}', repository_commit), 'Exact repository commit required')
    package.require(not output.exists(), 'Fresh app asset output required')
    runtime = json.loads((source / 'runtime-manifest.json').read_text())
    client = json.loads((source / 'client-manifest.json').read_text())
    package.require(runtime.get('format') == client.get('format') == 1
                    and client.get('scope') == 'actual_client_startup_guest', 'Existing client manifest required')
    for name, expected in runtime['files'].items():
        package.require(re.fullmatch('[A-Za-z0-9_.-]+', name) and name not in ('.', '..'), 'Unsafe app payload')
        path = source / name
        package.require(path.is_file() and not path.is_symlink()
                        and pin(path) == expected, 'Donor app payload differs: ' + name)
    package.require(all(runtime['files'].get(name) == expected for name, expected in client['files'].items()),
                    'Inner/outer app inventories disagree')
    with tempfile.TemporaryDirectory(prefix='armport-package-check-') as temporary:
        document = package.unpack(armport, Path(temporary) / 'client')
    replacements = {'armport-client.zip': armport,
                    'armport_client_package.py': Path(__file__).with_name('armport_client_package.py'),
                    'armport_interactive.py': Path(__file__).with_name('armport_interactive.py'),
                    'client_stdio.py': Path(__file__).with_name('client_stdio.py'),
                    'character_creation_diagnostic.py': ROOT / 'android/guest/character_creation_diagnostic.py'}
    output.mkdir(parents=True)
    # Ordinary copies keep the retained donor independent of future edits.
    for name in runtime['files']:
        if name not in replacements and name != 'client-manifest.json':
            shutil.copyfile(source / name, output / name)
    for name, path in replacements.items():
        shutil.copyfile(path, output / name)
        record = pin(output / name)
        runtime['files'][name] = client['files'][name] = record
    package.require(len(client['files']) <= 96, 'Existing client inventory bound exceeded')
    (output / 'client-manifest.json').write_bytes(encoded(client))
    runtime['files']['client-manifest.json'] = pin(output / 'client-manifest.json')
    runtime['repository_commit'] = repository_commit
    runtime['armport_client'] = {'archive_sha256': package.digest(armport),
        'executable_sha256': document['files']['CityOfHeroes.exe']['sha256'],
        'client_run_id': document['client_run_id'], 'data_run_id': document['data_run_id'],
        'machine': 'ARM64', 'default_architecture': 'x86'}
    (output / 'runtime-manifest.json').write_bytes(encoded(runtime))
    return runtime['armport_client']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'armport', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    print(json.dumps(stage(**vars(parser.parse_args()))))


if __name__ == '__main__':
    main()

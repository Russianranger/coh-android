#!/usr/bin/env python3
"""Create offline ZIP format fixtures from the three pinned neighborhood bodies.

The generated directories and headers are test data, never original archive
evidence. Android instead opens the complete archives admitted by its importer.
This helper has no acquisition path and does not modify its verified inputs.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import tempfile
import zipfile

NATIVE = Path(__file__).resolve().parents[2]
SCOPE = ('Generated ZIP format fixtures with authentic pinned neighborhood bodies; '
         'not original ZIP directory/header or whole-archive SHA qualification')


def source_inputs():
    path = NATIVE / 'combined-client/tools/prepare_neighborhood.py'
    spec = importlib.util.spec_from_file_location('runtime_zip_source_pins', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.INPUTS) == 3
    return module.INPUTS


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(cache, output):
    cache, output = Path(cache), Path(output)
    bodies = []
    for name, alias, size, digest, origin in source_inputs():
        path = cache / alias
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise ValueError('Pinned neighborhood input missing or wrong size: ' + alias)
        raw = path.read_bytes()
        if len(raw) != size or sha(raw) != digest:
            raise ValueError('Pinned neighborhood input SHA differs: ' + alias)
        bodies.append((name, size, digest, origin, raw))
    if output.is_symlink() or output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Fixture output must be a new or empty directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {'scope': SCOPE, 'original_archive_sha256_verified': False,
              'network_requests': 0, 'input_payload_bytes': sum(row[1] for row in bodies),
              'archives': []}
    # Validate all bodies before writing. Publish the descriptor last, so a
    # consumer cannot mistake a partial preparation for a complete fixture set.
    with tempfile.TemporaryDirectory(prefix='coh-zip-format-', dir=output.parent) as temporary:
        stage = Path(temporary)
        for origin in ('atlas', 'client'):
            name = origin + '.sparse.zip'
            path = stage / name
            members = {}
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
                for member, size, digest, selected, raw in bodies:
                    if selected != origin:
                        continue
                    entry = zipfile.ZipInfo(member, (1980, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFREG | 0o444) << 16
                    archive.writestr(entry, raw)
                    stored = archive.getinfo(member)
                    members[member] = {'data_offset': stored.header_offset + 30 + len(member.encode('utf-8')),
                                       'bytes': size, 'stored_bytes': size, 'sha256': digest}
            raw = path.read_bytes()
            if len(raw) > 1 << 20:
                raise ValueError('Generated fixture exceeds the existing range bound')
            for member, pin in members.items():
                offset = pin['data_offset']
                if sha(raw[offset:offset + pin['bytes']]) != pin['sha256']:
                    raise ValueError('Generated fixture member framing differs: ' + member)
            result['archives'].append({'origin': 'generated_zip_format_fixture_with_authentic_' + origin + '_bodies',
                                       'file': name, 'bytes': len(raw), 'members': members,
                                       'ranges': [{'offset': 0, 'bytes': len(raw), 'sha256': sha(raw)}]})
        (stage / 'original-archive-ranges.json').write_text(json.dumps(result, indent=2) + '\n')
        output.mkdir(exist_ok=True)
        for name in ('atlas.sparse.zip', 'client.sparse.zip', 'original-archive-ranges.json'):
            os.replace(stage / name, output / name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.cache, args.output)
    print(json.dumps({'scope': SCOPE, 'input_payload_bytes': result['input_payload_bytes'],
                      'fixture_bytes': sum(row['bytes'] for row in result['archives']),
                      'original_archive_sha256_verified': False, 'network_requests': 0}))


if __name__ == '__main__':
    main()

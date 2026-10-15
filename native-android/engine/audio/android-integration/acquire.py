#!/usr/bin/env python3
"""Acquire two authentic sound assets with existing bounded release ZIP reader."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('bounded_release_acquire', NATIVE / 'tools/animation_fixture/acquire.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pin = json.loads((NATIVE / 'tools/audio_fixture/pins.json').read_text())
    reader = module.HTTPRange(pin['outer_asset_url'], pin['outer_expected_bytes'], 8 << 20)
    records = []
    a.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(reader) as outer:
        manifest = outer.read(pin['manifest_member'])
        if len(manifest) != pin['manifest_bytes'] or sha(manifest) != pin['manifest_sha256']:
            raise ValueError('Release manifest identity differs')
        manifest = json.loads(manifest)
        sub = module.subzip(reader, outer.getinfo(pin['inner_member']))
        if sub.size != pin['inner_expected_bytes']:
            raise ValueError('Inner ZIP identity differs')
        with zipfile.ZipFile(sub) as archive:
            for name, local in [('data/sound/ogg/music/atlasplaza.ogg', 'atlasplaza.ogg'),
                                ('data/sound/ogg/city/steam1_loop.ogg', 'steam1.ogg')]:
                entry = archive.getinfo(name)
                expected = manifest['files'][name]
                if entry.flag_bits & 1 or not 0 < entry.file_size <= 8 << 20 or entry.file_size != expected['bytes']:
                    raise ValueError('Unsafe sound entry')
                data = archive.read(entry)
                if len(data) != expected['bytes'] or sha(data) != expected['sha256']:
                    raise ValueError('Sound SHA256 differs')
                (a.output / local).write_bytes(data)
                records.append({'path': name, 'file_name': local, 'bytes': len(data), 'sha256': sha(data),
                                'compressed': entry.compress_size, 'offset': entry.header_offset,
                                'crc32': f'{entry.CRC:08x}', 'method': entry.compress_type})
    receipt = {'schema': 'coh-native-audio-stream-corpus-v1', 'passed': True, 'data_commit': manifest['data_commit'],
               'outer_url': pin['outer_asset_url'], 'outer_expected_bytes': pin['outer_expected_bytes'],
               'inner_member': pin['inner_member'], 'inner_expected_bytes': pin['inner_expected_bytes'],
               'manifest_sha256': pin['manifest_sha256'], 'records': records,
               'http_range_bytes': reader.total, 'ranges': reader.requests, 'etag_stable': True,
               'full_archive_hash_verified': False,
               'integrity_scope': 'Pinned manifest SHA + each selected file size/SHA + ZIP CRC; full 848MB archive not downloaded'}
    (a.output / 'corpus.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()

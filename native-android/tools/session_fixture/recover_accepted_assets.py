#!/usr/bin/env python3
"""Recover exact accepted runtime inputs from the pinned gates16–18 APK.

No source acquisition or qualification is repeated. Only whole-APK SHA256 and
the original embedded asset identities are accepted. Output is a local fixture
cache; the qualified package and its receipts remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

APK_SHA256 = 'eb763d8c6e5354da06a336e8fe09a244a893755e82ef708ea1d2139dc17b8634'
APK_BYTES = 2139651
RUNTIME = {'world.bin', 'character.bin', 'rig.bin', 'morph.bin', 'locomotion.bin'}


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.apk.read_bytes()
    if identity(raw) != {'bytes': APK_BYTES, 'sha256': APK_SHA256}:
        raise ValueError('Accepted APK identity differs')
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.apk) as apk:
        if apk.testzip() is not None:
            raise ValueError('Accepted APK ZIP integrity differs')
        manifest = json.loads(apk.read('assets/asset-manifest.json'))
        metadata = json.loads(apk.read('assets/session-fixture.json'))
        if set(manifest['assets']) != RUNTIME or metadata['gates'] != [16, 17, 18]:
            raise ValueError('Accepted asset closure differs')
        recovered = {}
        for name, pin in metadata['assets'].items():
            if Path(name).name != name:
                raise ValueError('Unsafe accepted member name')
            data = apk.read('assets/' + name)
            if identity(data) != {k: pin[k] for k in ('bytes', 'sha256')}:
                raise ValueError('Accepted asset identity differs: ' + name)
            (args.output / name).write_bytes(data)
            recovered[name] = identity(data)
        for name in ('asset-manifest.json', 'session-fixture.json'):
            (args.output / name).write_bytes(apk.read('assets/' + name))
    receipt = {'schema': 1, 'passed': True, 'accepted_apk': identity(raw),
               'runtime_source_commit': 'e88a02b284de16ed6f7caf1e6b689f2e85d0b6e8',
               'recovered_assets': recovered, 'qualification_repeated': False}
    (args.output / 'accepted-assets-recovery.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'recovered_assets': len(recovered)}))


if __name__ == '__main__':
    main()

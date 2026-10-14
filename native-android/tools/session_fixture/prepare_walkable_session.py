#!/usr/bin/env python3
"""Combine preserved accepted assets with new authored walkable/directional inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

RUNTIME = {'world.bin', 'character.bin', 'rig.bin', 'morph.bin', 'locomotion.bin', 'walkable.bin'}


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked_metadata(directory, name):
    metadata = json.loads((directory / name).read_text())
    if not metadata.get('passed') and metadata.get('status') != 'prepared':
        raise ValueError('Unqualified preparation: ' + name)
    for filename, pin in metadata['assets'].items():
        if Path(filename).name != filename or identity(directory / filename) != {k: pin[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Fixture identity differs: ' + filename)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-assets', type=Path, required=True)
    parser.add_argument('--walkable-assets', type=Path, required=True)
    parser.add_argument('--locomotion-assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-output', type=Path, required=True)
    args = parser.parse_args()
    accepted = checked_metadata(args.accepted_assets, 'session-fixture.json')
    walkable = checked_metadata(args.walkable_assets, 'walkable-fixture.json')
    locomotion = checked_metadata(args.locomotion_assets, 'directional-fixture.json')
    if accepted['gates'] != [16, 17, 18]:
        raise ValueError('Accepted baseline gates differ')
    args.output.mkdir(parents=True, exist_ok=True)
    args.evidence_output.mkdir(parents=True, exist_ok=True)
    # Retire only the generated legacy metadata whose binary is replaced here.
    (args.output / 'locomotion-fixture.json').unlink(missing_ok=True)
    mapping = {}
    # Preserve all accepted character/world inputs and comparisons byte-for-byte.
    for name in accepted['assets']:
        if name in ('locomotion.bin', 'locomotion-fixture.json'):
            continue
        shutil.copyfile(args.accepted_assets / name, args.output / name)
        mapping[name] = {'source_fixture': 'accepted-gates16-18', **identity(args.output / name)}
    for directory, label, metadata in [(args.walkable_assets, 'walkable', walkable),
                                       (args.locomotion_assets, 'directional', locomotion)]:
        for name in sorted(set(metadata['assets']) | {label + '-fixture.json'}):
            if name in mapping or Path(name).name != name:
                raise ValueError('Conflicting or unsafe fixture name: ' + name)
            shutil.copyfile(directory / name, args.output / name)
            mapping[name] = {'source_fixture': label, **identity(args.output / name)}
    if not RUNTIME <= mapping.keys():
        raise ValueError('Missing new runtime asset closure')
    manifest = {'schema': 1, 'assets': {name: identity(args.output / name) for name in sorted(RUNTIME)}}
    (args.output / 'asset-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = {'schema': 1, 'gates': [19, 20, 21], 'passed': True,
               'kind': 'accepted actor/benchmark plus authored ground, source collision and directional raw keys',
               'runtime_assets': sorted(RUNTIME),
               'assets': {name: identity(args.output / name) for name in sorted(mapping)},
               'source_mapping': mapping, 'character_parts': 11, 'world_parts': 2,
               'reference_data_drive_rendering': False, 'runtime_motion_scripted_by_fixture': False,
               'full_original_client': False, 'full_atlas_loaded': False,
               'server_interoperability_verified': False,
               'physical_gates19_21_accepted': False}
    (args.output / 'session-fixture.json').write_text(json.dumps(receipt, indent=2) + '\n')
    for name in ('session-fixture.json', 'asset-manifest.json'):
        shutil.copyfile(args.output / name, args.evidence_output / name)
    print(json.dumps({'passed': True, 'runtime_assets': manifest['assets']}))


if __name__ == '__main__':
    main()

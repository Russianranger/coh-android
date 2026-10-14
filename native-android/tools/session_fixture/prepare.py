#!/usr/bin/env python3
"""Combine accepted character/world fixtures with the new locomotion fixture.

This only packages pinned authored inputs. It does not bake actor placement,
movement, camera matrices, poses, palettes, or a scripted gameplay sequence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


RUNTIME_ASSETS = {'world.bin', 'character.bin', 'rig.bin', 'morph.bin', 'locomotion.bin'}


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_metadata(directory, filename):
    raw = (directory / filename).read_bytes()
    if not 0 < len(raw) <= 512 << 10:
        raise ValueError('Metadata exceeds the Android loader bound: ' + filename)
    metadata = json.loads(raw)
    for name, pin in metadata['assets'].items():
        if Path(name).name != name:
            raise ValueError('Unsafe fixture filename: ' + name)
        if identity(directory / name) != {k: pin[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Fixture identity differs: ' + filename + '/' + name)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--character-assets', type=Path, required=True)
    parser.add_argument('--world-assets', type=Path, required=True)
    parser.add_argument('--locomotion-assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-output', type=Path, required=True)
    args = parser.parse_args()
    character = read_metadata(args.character_assets, 'character-fixture.json')
    world = read_metadata(args.world_assets, 'world-fixture.json')
    locomotion = read_metadata(args.locomotion_assets, 'locomotion-fixture.json')
    if character['scene']['part_count'] != 11 or world['scene']['part_count'] != 2:
        raise ValueError('Accepted authored character/world closure differs')
    if not world['source_trick_resolution_qualified']:
        raise ValueError('Original world material declarations were not qualified')
    args.output.mkdir(parents=True, exist_ok=True)
    args.evidence_output.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for directory, label, metadata in [(args.character_assets, 'character', character),
                                       (args.world_assets, 'world', world),
                                       (args.locomotion_assets, 'locomotion', locomotion)]:
        # An accepted integration APK also carries audio assets. Reuse only the
        # source closure declared by the character/world/locomotion metadata.
        names = set(metadata['assets']) | {label + '-fixture.json'}
        for source in sorted(directory / name for name in names):
            name = 'world-material-reference.bin' if label == 'world' and source.name == 'material-reference.bin' else source.name
            if name in mapping or name in {'session-fixture.json', 'asset-manifest.json'}:
                raise ValueError('Conflicting fixture asset: ' + name)
            mapping[name] = {'source_fixture': label, 'source_name': source.name, **identity(source)}
            shutil.copyfile(source, args.output / name)
    # The world metadata follows its renamed comparison-only material asset.
    world['assets']['world-material-reference.bin'] = world['assets'].pop('material-reference.bin')
    (args.output / 'world-fixture.json').write_text(json.dumps(world, indent=2) + '\n')
    mapping['world-fixture.json'].update(identity(args.output / 'world-fixture.json'))
    if not RUNTIME_ASSETS <= mapping.keys():
        raise ValueError('Missing native runtime assets: ' + str(RUNTIME_ASSETS - mapping.keys()))
    manifest = {'schema': 1, 'assets': {name: identity(args.output / name) for name in sorted(RUNTIME_ASSETS)}}
    (args.output / 'asset-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = {'schema': 1, 'gates': [16, 17, 18], 'passed': True,
               'kind': 'combined authored runtime assets; references retained as evidence only',
               'runtime_assets': sorted(RUNTIME_ASSETS),
               'assets': {name: identity(args.output / name) for name in sorted(mapping)},
               'source_mapping': mapping,
               'character_parts': 11, 'world_parts': 2,
               'reference_data_drive_rendering': False,
               'runtime_motion_scripted_by_fixture': False,
               'full_original_client': False, 'full_atlas_loaded': False,
               'server_interoperability_verified': False}
    (args.output / 'session-fixture.json').write_text(json.dumps(receipt, indent=2) + '\n')
    for name in ('session-fixture.json', 'asset-manifest.json'):
        shutil.copyfile(args.output / name, args.evidence_output / name)
    print(json.dumps({'passed': True, 'runtime_assets': manifest['assets'], 'packaged_files': len(mapping) + 2}))


if __name__ == '__main__':
    main()

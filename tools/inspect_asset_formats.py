#!/usr/bin/env python3
"""Check staged animation/texture structures against a verified PIGG inventory.

Run inspect_piggs.py first. This tool rechecks staged sizes and SHA-256 hashes,
then performs offline format checks. It does not run the game or prove runtime
compatibility. Keep the three format-checker modules together in tools/.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

from animation_format import animation_header, animation_dependency_report
from texture_format import texture_header


def inspect_formats(inventory, assets):
    if inventory.get('status') != 'archive_integrity_verified_runtime_compatibility_unverified':
        raise ValueError('Expected a completed inspect_piggs.py inventory')
    root = assets.resolve(strict=True)
    records = []
    for archive in inventory['archives']:
        for entry in archive['entries']:
            name = entry['path']
            suffix = PurePosixPath(name).suffix.lower()
            if suffix not in ('.anim', '.texture'):
                continue
            parts = name.replace('\\', '/').lower().split('/')
            if any(p in ('', '.', '..') for p in parts) or ':' in name:
                raise ValueError('Unsafe inventory path: ' + name)
            path = root.joinpath(*parts)
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                raise ValueError('Asset must be a regular file inside staging: ' + name)
            size = path.stat().st_size
            if size != entry['size'] or size > 512 * 1024**2:
                raise ValueError('Staged asset size mismatch or over limit: ' + name)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Staged asset SHA-256 mismatch: ' + name)
            result = (animation_header if suffix == '.anim' else texture_header)(data)
            records.append({'archive': archive['archive'], 'path': name,
                            'sha256': entry['sha256'], **result})
    counts = Counter(x['validation_status'] for x in records)
    animations = [x for x in records if x['path'].lower().endswith('.anim')]
    animation_names = {(x.get('name') or '').replace('\\', '/').casefold()
                       for x in animations}
    dependencies = animation_dependency_report(animations)
    dependencies['scope'] = 'base_anim_name references within the inspected set only'
    dependencies['male_thumbsup_present'] = 'male/thumbsup' in animation_names
    dependencies['name_path_mismatches'] = [x['path'] for x in animations
        if x['path'].replace('\\', '/').casefold() !=
        'player_library/animations/' +
        (x.get('name') or '').replace('\\', '/').casefold() + '.anim']
    startup_names = {'white', 'grey', 'black', 'invisible', 'dummy_bump',
                     'dummy_dynamic_cubemap_face0', 'buildinglightpattern'}
    startup_textures = {name: [x['path'] for x in records
                              if x['path'].lower().endswith('.texture') and
                              PurePosixPath(x['path']).stem.casefold() == name]
                        for name in sorted(startup_names)}
    return {
        'status': 'offline_format_checks_complete_runtime_unverified',
        'source_commit': '0b75ade0c801735e10c5798f641948a45cc50488',
        'staged_hashes_verified': len(records),
        'validation_status_counts': dict(counts),
        'animation_dependencies': dependencies,
        'startup_texture_paths': startup_textures,
        'archives': [{k: v for k, v in a.items() if k != 'entries'}
                     for a in inventory['archives']],
        'entries': records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New JSON report')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Output already exists')
    report = inspect_formats(json.loads(args.inventory.read_text()), args.assets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('entries', 'archives', 'animation_dependencies', 'startup_texture_paths')}))
    return int(any(x['validation_status'] != 'structural_checks_passed' for x in report['entries']))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Format inspection failed: ' + str(error), file=sys.stderr)
        sys.exit(1)

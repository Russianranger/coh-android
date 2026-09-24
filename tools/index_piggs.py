#!/usr/bin/env python3
"""Quick read-only PIGG v2 inventory, using only Python's standard library.

Reads archive tables and names, never payloads. Output is NOT an integrity check.
Designed to identify which large client archives contain missing asset types
before uploading them. Directory paths in the report are relative to the root.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

MAX_METADATA_BYTES = 64 * 1024**2
STARTUP_TEXTURES = {'white', 'grey', 'invisible', 'black', 'dummy_bump',
                    'dummy_dynamic_cubemap_face0', 'buildinglightpattern'}


def read_exact(stream, count):
    if count < 0 or count > MAX_METADATA_BYTES:
        raise ValueError('Archive metadata exceeds inspection limit')
    data = stream.read(count)
    if len(data) != count:
        raise ValueError('Truncated archive table')
    return data


def index_archive(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Input must be a regular file')
    with path.open('rb') as stream:
        magic, creator, reader, header_size, entry_size, count = struct.unpack(
            '<IHHHHI', read_exact(stream, 16))
        if (magic, creator, header_size, entry_size) != (0x123, 2, 16, 48) or reader > 2:
            raise ValueError('Unsupported archive format')
        if count * entry_size > MAX_METADATA_BYTES:
            raise ValueError('Archive entry count exceeds inspection limit')
        stream.seek(count * entry_size, 1)
        flag, names_count, names_size = struct.unpack('<III', read_exact(stream, 12))
        if flag != 0x6789 or names_count != count or count > names_size // 4:
            raise ValueError('Invalid filename table')
        data = read_exact(stream, names_size)
    names, pos = [], 0
    for _ in range(count):
        if pos + 4 > len(data):
            raise ValueError('Truncated filename length')
        size, = struct.unpack_from('<I', data, pos)
        pos += 4
        raw = data[pos:pos + size]
        if len(raw) != size or not raw.endswith(b'\0') or b'\0' in raw[:-1]:
            raise ValueError('Invalid filename')
        name = raw[:-1].decode('utf-8').replace('\\', '/')
        if (not name or ':' in name or any(p in ('', '.', '..') for p in name.split('/'))
                or any(ord(c) < 32 for c in name)):
            raise ValueError('Unsafe archive filename')
        names.append(name)
        pos += size
    if pos != len(data) or len({n.lower() for n in names}) != len(names):
        raise ValueError('Trailing filename data or case-colliding names')
    animations = sorted(n for n in names if n.lower().endswith('.anim'))
    startup_textures = sorted(n for n in names if n.lower().endswith('.texture')
                              and Path(n).stem.lower() in STARTUP_TEXTURES)
    return {'bytes': path.stat().st_size, 'entry_count': count,
            'integrity_checked': False, 'payloads_read': False,
            'extensions': dict(sorted(Counter(Path(n).suffix.lower() for n in names).items())),
            'animation_count': len(animations), 'animation_samples': animations[:12],
            'startup_texture_paths': startup_textures,
            'has_male_thumbsup_animation': 'player_library/animations/male/thumbsup.anim' in {n.lower() for n in names},
            'sample_entries': names[:8]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path,
                        help='Client root; recursively scans .pigg files, skipping symlinks')
    parser.add_argument('--output', required=True, type=Path, help='New JSON file to upload')
    args = parser.parse_args()
    if args.directory.is_symlink() or not args.directory.is_dir():
        parser.error('Client directory is unavailable or is a symlink')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; choose a new filename')
    root = args.directory.resolve()
    archives = []
    # os.walk explicitly avoids following directory symlinks across Python versions.
    import os
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = sorted(f for f in folders if not (Path(directory) / f).is_symlink())
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.suffix.lower() != '.pigg' or path.is_symlink():
                continue
            entry = {'archive': path.relative_to(root).as_posix()}
            try:
                entry.update(index_archive(path))
            except (OSError, ValueError, struct.error) as error:
                entry['index_error'] = str(error)
            archives.append(entry)
    result = {'status': 'index_only_not_integrity_verified', 'archives': archives,
              'archive_count': len(archives),
              'archives_with_animations': [a['archive'] for a in archives if a.get('animation_count', 0)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    failures = sum('index_error' in a for a in archives)
    print(f'Indexed {len(archives)} archives; {failures} errors. Payloads were not verified.')
    print(f'Upload {args.output}')
    return 1 if failures or not archives else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

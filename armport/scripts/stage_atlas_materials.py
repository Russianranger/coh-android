#!/usr/bin/env python3
"""Stage only the 27 reviewed Atlas material additions as a separate layer."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

from stage_atlas_supplement import digest, require
from stage_reviewed_files import stage_archive

ROOT = Path(__file__).resolve().parents[2]


def reviewed_world():
    # Reuse the existing pin/range verifier; do not define a new donor source.
    sys.path.insert(0, str(ROOT))
    from tools.android.interactive import prepare_atlas_world_assets
    return prepare_atlas_world_assets


def selection():
    world = reviewed_world()
    document = world.read_manifest(ROOT / 'assets' / world.MANIFEST)
    names = world.material_extension_files(document)
    return document, {name: document['files'][name] for name in sorted(names)}


def verify(output, selected):
    require(output.is_dir() and not any(p.is_symlink() for p in (output, *output.parents)),
            'Missing or linked Atlas material layer')
    actual = {}
    for path in output.rglob('*'):
        require(not path.is_symlink(), 'Linked Atlas material member')
        if path.is_dir():
            continue
        require(path.is_file(), 'Non-regular Atlas material member')
        name = 'data/' + path.relative_to(output).as_posix()
        require(name in selected, 'Unexpected Atlas material member: ' + name)
        actual[name] = dict(bytes=path.stat().st_size, sha256=digest(path))
    require(actual == selected, 'Atlas material inventory or digest differs')
    return dict(files=len(selected), payload_bytes=sum(p['bytes'] for p in selected.values()),
                manifest_sha256=reviewed_world().MANIFEST_PIN['sha256'],
                scope='reviewed_27_atlas_material_additions', runtime_validated=False)


def stage(archive, document, selected, output):
    require(not output.exists() and not output.is_symlink(), 'Atlas material output already exists')
    require(not any(p.is_symlink() for p in output.parents), 'Linked Atlas material output parent')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.atlas-materials-', dir=output.parent) as temp:
        data = Path(temp) / 'data'
        data.mkdir()
        stage_archive(archive, document, selected, data)
        verify(data, selected)
        data.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--base-archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    document, selected = selection()
    if not args.verify_only:
        require(args.archive is not None, 'An exact reviewed material archive is required')
        if args.base_archive is not None:
            args.archive.parent.mkdir(parents=True, exist_ok=True)
            result = reviewed_world().materialize(archive=args.archive, base_archive=args.base_archive)
            print('::notice title=ArmPort reviewed material reconstruction::' + json.dumps(result))
        stage(args.archive, document, selected, args.output)
    print('::notice title=ArmPort reviewed Atlas materials::' + json.dumps(verify(args.output, selected)))


if __name__ == '__main__':
    main()

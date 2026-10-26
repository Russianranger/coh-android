#!/usr/bin/env python3
"""Recover and stage the previously reviewed 0.10 Atlas data, without an APK build."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

APK_SHA = 'ee9c09a3bda8a7f68af1e481e8c85e96c14ee0ea6ab414dbcda2ca730dd73688'
ARCHIVE_SHA = '499d50fe7bb399465dcd30d046dec99551dd5f98181947e98f9d5d99a3880c60'
MANIFEST_SHA = '2566bed7c2948b53ac169e090086613da571ec45008d72a6eb00e092acc2d203'
PINS = {'atlas-world-supplement.zip': (203438405, ARCHIVE_SHA),
        'atlas-world-supplement-manifest.json': (None, MANIFEST_SHA)}
REVIEWED_MANIFEST = Path(__file__).resolve().parents[2] / 'assets/atlas-world-supplement-manifest.json'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), 'Regular input required')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def recover(apk, output):
    require(apk.stat().st_size == 590725465 and digest(apk) == APK_SHA, 'Retained APK identity differs')
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK members')
        for name, (size, sha) in PINS.items():
            matches = [n for n in names if n in ('assets/runtime/' + name, 'assets/atlas/' + name)]
            require(len(matches) == 1, 'Missing/ambiguous retained Atlas asset: ' + name)
            member = archive.getinfo(matches[0])
            require(member.file_size <= (size or 16 * 1024 * 1024)
                    and not stat.S_ISLNK(member.external_attr >> 16), 'Invalid retained member')
            target = output / name
            with archive.open(member) as source, target.open('xb') as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
            require((size is None or target.stat().st_size == size) and digest(target) == sha,
                    'Retained Atlas asset identity differs')


def unpack(archive_path, document, output):
    files = document['files']
    require(len(files) == document['file_count']
            and sum(p['bytes'] for p in files.values()) == document['payload_bytes'], 'Manifest totals differ')
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        require(len(members) == len(files) and {m.filename for m in members} == set(files),
                'Atlas archive inventory differs')
        for member in members:
            name = PurePosixPath(member.filename)
            require(name.as_posix() == member.filename and not name.is_absolute()
                    and name.parts[0] == 'data' and len(name.parts) > 2
                    and all(p not in ('', '.', '..') for p in name.parts)
                    and '\\' not in member.filename and ':' not in member.filename
                    and name.suffix in ('.geo', '.texture')
                    and not stat.S_ISLNK(member.external_attr >> 16), 'Unsafe Atlas member')
            pin = files[member.filename]
            require(0 < member.file_size == pin['bytes'] <= 128 * 1024 * 1024, 'Atlas member size differs')
            data = archive.read(member)
            require(hashlib.sha256(data).hexdigest() == pin['sha256'], 'Atlas member digest differs')
            target = output.joinpath(*name.parts[1:])
            require(not any(p.is_symlink() for p in (target, *target.parents)), 'Linked Atlas output')
            if target.exists():
                require(digest(target) == pin['sha256'], 'Atlas would replace different existing data')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as destination:
                    destination.write(data)
    return dict(files=len(files), payload_bytes=document['payload_bytes'], archive_sha256=ARCHIVE_SHA)


def verify_reviewed_subset(document, reviewed):
    for name, pin in document['files'].items():
        entry = reviewed['files'].get(name)
        require(entry is not None and entry['sha256'] == pin['sha256']
                and entry['bytes'] == pin['bytes'], 'Pinned file differs from repository manifest: ' + name)


def verify_inputs(source, reviewed_manifest=None):
    for name, (size, sha) in PINS.items():
        path = source / name
        require((size is None or path.stat().st_size == size) and digest(path) == sha,
                'Atlas input identity differs: ' + name)
    document = json.loads((source / 'atlas-world-supplement-manifest.json').read_text())
    require(document['file_count'] == 2877 and document['payload_bytes'] == 309655940,
            'Unexpected retained Atlas scope')
    reviewed_manifest = reviewed_manifest or REVIEWED_MANIFEST
    verify_reviewed_subset(document, json.loads(reviewed_manifest.read_text()))
    return document


def stage(source, output, reviewed_manifest=None):
    document = verify_inputs(source, reviewed_manifest)
    result = unpack(source / 'atlas-world-supplement.zip', document, output)
    result['repository_manifest_sha256'] = digest(reviewed_manifest or REVIEWED_MANIFEST)
    result['reviewed_subset_files'] = len(document['files'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    recover_args = sub.add_parser('recover')
    recover_args.add_argument('--apk', type=Path, required=True)
    stage_args = sub.add_parser('stage')
    stage_args.add_argument('--source', type=Path, required=True)
    for child in (recover_args, stage_args):
        child.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = recover(args.apk, args.output) if args.action == 'recover' else stage(args.source, args.output)
    print('::notice title=ArmPort reviewed Atlas supplement::' + json.dumps(result or {'recovered': True}))


if __name__ == '__main__':
    main()

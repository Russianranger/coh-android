#!/usr/bin/env python3
"""Stage only exact, unambiguous files selected from existing reviewed archives."""
import argparse
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from reviewed_asset_coverage import load_manifest, sha, coverage
from stage_atlas_supplement import digest, require

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'armport/evidence/m3-reviewed-file-selection.json'
EVIDENCE = ROOT / 'armport/evidence/m3-dispatch-errors-40105902494.json'


def checked_plan():
    plan = json.loads(PLAN.read_text())
    require(plan == coverage(json.loads(EVIDENCE.read_text()), ROOT / 'assets'),
            'Reviewed selection differs from current manifests/evidence')
    require(not any(plan['ambiguous'].values()), 'Ambiguous texture source; no automatic selection')
    return plan


def stage_archive(archive_path, document, selected, output):
    pin = document['archive']
    require(archive_path.stat().st_size == pin['bytes'] and digest(archive_path) == pin['sha256'],
            'Reviewed archive identity differs')
    for name, pin in selected.items():
        require(document['files'].get(name) == pin, 'Selection differs from reviewed per-file pin')
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        require(len(members) == len(document['files'])
                and {m.filename for m in members} == set(document['files']), 'Archive inventory differs')
        for name, pin in selected.items():
            member = archive.getinfo(name)
            parts = PurePosixPath(name).parts
            require(name.startswith('data/') and '..' not in parts and '\\' not in name and ':' not in name
                    and not stat.S_ISLNK(member.external_attr >> 16)
                    and member.file_size == pin['bytes'] <= 128 * 1024 * 1024, 'Unsafe selected member')
            data = archive.read(member)
            require(sha(data) == pin['sha256'], 'Selected member digest differs: ' + name)
            target = output.joinpath(*parts[1:])
            require(not any(p.is_symlink() for p in (target, *target.parents)), 'Linked selected output')
            if target.exists():
                require(digest(target) == pin['sha256'], 'Selected file collision differs: ' + name)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(data)


def verify(output, plan):
    expected = {name.removeprefix('data/'): pin for files in plan['selected'].values() for name, pin in files.items()}
    actual = {p.relative_to(output).as_posix(): p for p in output.rglob('*') if not p.is_dir()}
    require(actual.keys() == expected.keys(), 'Selected staging inventory differs')
    for name, pin in expected.items():
        require(actual[name].stat().st_size == pin['bytes'] and digest(actual[name]) == pin['sha256'],
                'Selected staged file differs: ' + name)
    return dict(selected_files=len(expected), payload_bytes=sum(p['bytes'] for p in expected.values()),
                plan_sha256=digest(PLAN), new_source_fetched=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--visual', type=Path)
    parser.add_argument('--zones', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    plan = checked_plan()
    if not args.verify_only:
        require(args.visual is not None and args.zones is not None, 'Both reviewed archives are required')
        sources = {'client-visual': args.visual, 'zones-world-supplement': args.zones,
                   'character-avatar-defaults': ROOT / 'assets/character-avatar-defaults.zip'}
        for source, path in sources.items():
            document, _ = load_manifest(ROOT / 'assets' / (source + '-manifest.json'))
            stage_archive(path, document, plan['selected'][source], args.output)
    print('::notice title=ArmPort selected reviewed files::' + json.dumps(verify(args.output, plan)))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Prepare 0.3 using exact accepted actor assets and new authentic map inputs.

Only generated asset filenames owned by these native fixture tools can be
replaced or retired. Unknown output entries abort preparation. The accepted APK,
its old assets and evidence are never modified or rebuilt by this tool.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

NATIVE = Path(__file__).resolve().parents[2]
ACCEPTED_ARCHIVE = {'bytes': 7291533,
                    'sha256': '662b679f33854c704b831a061ba03a5d142b8f987686f783293f51ef84503151'}
ACCEPTED_APK = {'bytes': 2344055,
                'sha256': '2d59e2b39af99facc6f3ac26b310aeba85802542efabb1e71d90e2d33a00de92'}
ACCEPTED_RUNTIME = {
    'world.bin': {'bytes': 102176, 'sha256': '7289eb3a4478648dcefce682121ccd0448aee6a21a7c4977ffd6415dd11ece6f'},
    'character.bin': {'bytes': 4261100, 'sha256': '59dae233f6a6b980f134be71b1ef6d7d112fca46f49b01468f932787fbe33ea7'},
    'rig.bin': {'bytes': 11642, 'sha256': '2b1e862dc61744d51d568f05f54ee1a0ce723ba7529c55adb7e373d2c42b8dd5'},
    'morph.bin': {'bytes': 3028, 'sha256': 'ceba092c4e80fa9945cecb08fc438e28e69786253c4638512549baf7af021e02'},
    'locomotion.bin': {'bytes': 147103, 'sha256': '8c42bd6c72223ec0d32519143fe90fa23f9528006ed914659ae44f78592b63d7'},
}
RUNTIME = set(ACCEPTED_RUNTIME) | {'walkable.bin', 'map.bin'}
METADATA = {'asset-manifest.json', 'session-fixture.json', 'map-fixture.json', 'walkable-fixture.json'}
# Explicit historical generated closure; arbitrary files are never removed.
LEGACY_GENERATED = {
    'character-fixture.json', 'character-reference.bin', 'directional-fixture.json',
    'locomotion-fixture.json', 'material-reference.bin', 'world-fixture.json',
    'world-material-reference.bin', 'world-reference.bin',
}


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked_accepted_assets(path):
    if path.stat().st_size != ACCEPTED_APK['bytes'] or identity(path.read_bytes()) != ACCEPTED_APK:
        raise ValueError('Accepted 0.2.0 APK identity differs')
    with zipfile.ZipFile(path) as apk:
        names = apk.namelist()
        if len(names) != len(set(names)) or apk.testzip() is not None:
            raise ValueError('Accepted APK has duplicate members or invalid ZIP data')
        manifest = json.loads(apk.read('assets/asset-manifest.json'))
        fixture = json.loads(apk.read('assets/session-fixture.json'))
        if manifest['schema'] != 1 or set(manifest['assets']) != set(ACCEPTED_RUNTIME) | {'walkable.bin'}:
            raise ValueError('Accepted six-file runtime closure differs')
        if fixture['passed'] is not True or fixture['gates'] != [19, 20, 21]:
            raise ValueError('Accepted 0.2 fixture metadata differs')
        recovered = {}
        for name, pin in ACCEPTED_RUNTIME.items():
            raw = apk.read('assets/' + name)
            if identity(raw) != pin or manifest['assets'][name] != pin or fixture['assets'][name] != pin:
                raise ValueError('Accepted source asset identity differs: ' + name)
            recovered[name] = raw
        prior = {name: apk.read('assets/' + name)
                 for name in ('asset-manifest.json', 'session-fixture.json', 'world-fixture.json',
                              'character-fixture.json', 'directional-fixture.json', 'walkable-fixture.json',
                              'world-reference.bin', 'world-material-reference.bin')}
        for name, data in prior.items():
            if name in fixture['assets'] and identity(data) != fixture['assets'][name]:
                raise ValueError('Accepted provenance identity differs: ' + name)
    return recovered, prior


def prepare(accepted_apk, source_root, corpus, output, evidence):
    recovered, prior = checked_accepted_assets(accepted_apk)
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    allowed = RUNTIME | METADATA | LEGACY_GENERATED
    for path in output.iterdir():
        if not path.is_file() or path.is_symlink() or path.name not in allowed:
            raise ValueError('Refusing to alter unknown generated-assets output entry: ' + str(path))
    spec = importlib.util.spec_from_file_location('source_map_batch_prepare', NATIVE / 'tools/map_fixture/prepare.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with tempfile.TemporaryDirectory(prefix='coh-world-prepare-', dir=output.parent) as temporary:
        staging = Path(temporary)
        prepared = staging / 'map'
        map_receipt = builder.prepare(source_root.resolve(), [p.resolve() for p in corpus], prepared)
        if map_receipt['passed'] is not True or map_receipt['expanded_walkable']['passed'] is not True:
            raise ValueError('New source map or collision preparation did not pass')
        for name, raw in recovered.items():
            (staging / name).write_bytes(raw)
        for name in ('map.bin', 'walkable.bin', 'map-fixture.json', 'walkable-fixture.json'):
            shutil.copyfile(prepared / name, staging / name)
        runtime = {name: identity((staging / name).read_bytes()) for name in sorted(RUNTIME)}
        if runtime['map.bin'] != {k: map_receipt['bundle'][k] for k in ('bytes', 'sha256')}:
            raise ValueError('New source-map bundle differs from preparation receipt')
        if runtime['walkable.bin'] != map_receipt['expanded_walkable']['assets']['walkable.bin']:
            raise ValueError('Expanded source collision differs from preparation receipt')
        manifest = {'schema': 1, 'assets': runtime}
        (staging / 'asset-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        closure = RUNTIME | {'map-fixture.json', 'walkable-fixture.json'}
        fixture = {'schema': 1, 'gates': [22, 23, 24], 'passed': True,
                   'kind': 'Preserved accepted actor plus original GEO/TEXTURE source bundle and authentic bounded Atlas placements',
                   'runtime_assets': sorted(RUNTIME),
                   'assets': {name: identity((staging / name).read_bytes()) for name in sorted(closure)},
                   'accepted_apk': ACCEPTED_APK,
                   'accepted_runtime_source_commit': '8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d',
                   'accepted_runtime_assets_preserved': ACCEPTED_RUNTIME,
                   'catalog': map_receipt['catalog'], 'radius_queries': map_receipt['radius_queries'],
                   'reference_data_drive_rendering': False, 'runtime_motion_scripted_by_fixture': False,
                   'accepted_qualification_repeated': False, 'new_map_collision_expanded': True,
                   'full_original_client': False, 'full_atlas_loaded': False,
                   'server_interoperability_verified': False, 'physical_gates22_24_accepted': False}
        (staging / 'session-fixture.json').write_text(json.dumps(fixture, indent=2) + '\n')
        expected = RUNTIME | METADATA
        for path in list(output.iterdir()):
            if path.name not in expected:
                path.unlink()  # Verified explicit historical generator-owned name.
        for name in sorted(expected):
            shutil.copyfile(staging / name, output / name)
    for name in sorted(METADATA):
        shutil.copyfile(output / name, evidence / name)
    old_evidence = evidence / 'accepted-0.2-provenance'
    old_evidence.mkdir(exist_ok=True)
    for name, raw in {**prior, 'world.bin': recovered['world.bin']}.items():
        (old_evidence / name).write_bytes(raw)
    receipt = {'schema': 1, 'passed': True, 'accepted_apk': ACCEPTED_APK,
               'accepted_runtime_assets_reused': ACCEPTED_RUNTIME,
               'accepted_qualification_repeated': False, 'identical_apk_rebuilt': False,
               'new_runtime_assets': {name: runtime[name] for name in ('map.bin', 'walkable.bin')},
               'packaged_runtime_count': len(RUNTIME), 'packaged_total_assets': len(expected),
               'source_map_catalog': map_receipt['catalog'],
               'android_execution_qualified': False, 'physical_qualified': False}
    (evidence / 'accepted-assets-recovery.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    accepted = parser.add_mutually_exclusive_group(required=True)
    accepted.add_argument('--accepted-apk', type=Path)
    accepted.add_argument('--accepted-archive', type=Path, help='Exact original 0.2 source/build artifact ZIP; extract only its pinned ARM64 APK')
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-output', type=Path, required=True)
    args = parser.parse_args()
    if args.accepted_apk:
        receipt = prepare(args.accepted_apk, args.source_root, args.corpus, args.output, args.evidence_output)
    else:
        archive = args.accepted_archive
        if archive.stat().st_size != ACCEPTED_ARCHIVE['bytes'] or identity(archive.read_bytes()) != ACCEPTED_ARCHIVE:
            raise ValueError('Accepted original artifact ZIP identity differs')
        with tempfile.TemporaryDirectory(prefix='coh-accepted-world-') as temporary:
            path = Path(temporary) / 'accepted.apk'
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                if len(names) != len(set(names)) or bundle.testzip() is not None:
                    raise ValueError('Accepted artifact ZIP integrity or unique-member check failed')
                member = 'CoH-Native-Session-Client-0.2.0-arm64.apk'
                if bundle.getinfo(member).file_size != ACCEPTED_APK['bytes']:
                    raise ValueError('Accepted artifact APK member size differs')
                path.write_bytes(bundle.read(member))
            receipt = prepare(path, args.source_root, args.corpus, args.output, args.evidence_output)
        receipt['accepted_archive'] = ACCEPTED_ARCHIVE
        (args.evidence_output / 'accepted-assets-recovery.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()

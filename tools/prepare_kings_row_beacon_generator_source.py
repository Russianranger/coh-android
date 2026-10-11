#!/usr/bin/env python3
"""Stage a separate host-only Kings Row beacon producer; never ship its EXE.

Retain the frozen Atlas containment and genuine beacon algorithms. The small
second overlay selects map 5 and refuses missing native world members/models,
which would otherwise silently create a graph for incomplete collision input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import prepare_atlas_beacon_generator_source as atlas
from prepare_resume_client_source import apply_patch, canonical_hash

ROOT = Path(__file__).resolve().parents[1]
MAP = 'maps/city_zones/city_01_02/city_01_02.txt'
PATCH = 'patches/kings-row-beacons/0001-host-only-kings-row-generator.patch'
RECEIPT = 'kings-row-beacon-generator-build-input.json'
FILES = ('MapServer/src/beacon/beaconClientServer.c', 'MapServer/src/beacon/beaconServer.c',
         'Common/group/groupfileload.c')
RETAINED = tuple(name for name in atlas.RETAINED if name not in FILES)


def expected(root=ROOT):
    root = Path(root)
    base = atlas.expected(root)
    patch = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = tuple(line[6:].decode('ascii') for line in patch.splitlines() if line.startswith(b'+++ b/'))
    atlas.progress.require(names == FILES, 'Kings Row host-only patch scope differs')
    with tempfile.TemporaryDirectory(prefix='coh-kings-source-') as temporary:
        stage = Path(temporary)
        for name in set(FILES).union(atlas.FILES):
            target = stage / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / 'upstream/ouroboros' / name, target)
        apply_patch(stage, (root / atlas.PATCH).read_bytes().replace(b'\r\n', b'\n'))
        inputs = {name: atlas.progress.sha256(stage / name) for name in FILES}
        apply_patch(stage, patch)
        outputs = {name: atlas.progress.sha256(stage / name) for name in FILES}
    contract = dict(base['contract'], map=MAP, map_id=5,
                    missing_group_or_root_geometry='fatal_before_acceptance',
                    fresh_process_input_profiles=['cold_world', 'reopened_world'])
    return {'format': 1, 'build_role': 'host_only_kings_row_beacon_generator',
            'source_commit': base['source_commit'], 'base': base,
            'patch_sha256': hashlib.sha256(patch).hexdigest(),
            'source_sha256': inputs, 'patched_sha256': outputs,
            'retained_algorithm_sha256': {name: atlas.progress.sha256(root/'upstream/ouroboros'/name)
                                         for name in RETAINED},
            'contract': contract, 'build_targets': ['MapServer'],
            'runtime_validation': 'pending_generation'}


def prepare(output, root=ROOT):
    output, root = Path(output), Path(root)
    receipt = expected(root)
    atlas.prepare(output, root)
    atlas.progress.require(json.loads((output/atlas.RECEIPT).read_text()) == receipt['base'],
                           'Frozen Atlas producer base changed')
    for name, digest in receipt['source_sha256'].items():
        atlas.progress.require(atlas.progress.sha256(output/name) == digest, 'Host source differs: '+name)
    apply_patch(output, (root/PATCH).read_bytes().replace(b'\r\n', b'\n'))
    for name, digest in {**receipt['patched_sha256'], **receipt['retained_algorithm_sha256']}.items():
        atlas.progress.require(atlas.progress.sha256(output/name) == digest, 'Host source result differs: '+name)
    (output/RECEIPT).write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    value = prepare(parser.parse_args().output)
    print(json.dumps({'status': 'staged', 'role': value['build_role'], 'canonical_sha256': canonical_hash(value)}))

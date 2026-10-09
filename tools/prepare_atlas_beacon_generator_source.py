#!/usr/bin/env python3
"""Stage a host-only, single-map producer using the active native beacon roles.

The produced executable is never a gameplay donor. It only contains Beacon
master/server/client roles, rejects ordinary/production startup, cannot install
itself or start workers, and verifies the freshly reloaded Atlas graph before
the owned server can complete. Geometry generation and connection algorithms
are retained exactly; the old compiled-out combat processor remains disabled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import prepare_mapserver_progress_source as progress
from prepare_resume_client_source import apply_patch, canonical_hash

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/atlas-beacons/0001-host-only-atlas-generator.patch'
RECEIPT = 'atlas-beacon-generator-build-input.json'
FILES = (
    'MapServer/src/beacon/beaconClientServer.c',
    'MapServer/src/beacon/beaconServer.c',
    'MapServer/src/beacon/beaconClient.c',
)
RETAINED = (
    'MapServer/src/beacon/beaconGenerate.c',
    'MapServer/src/beacon/beaconConnection.c',
    'MapServer/src/beacon/beaconFile.c',
    'MapServer/src/beacon/beaconPath.c',
    'Common/group/groupfileload.c', 'Common/gridcoll/gridcoll.c',
)
MAP = 'maps/city_zones/city_01_01/city_01_01.txt'


def expected(root=ROOT):
    root = Path(root)
    patch = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = tuple(line[6:].decode('ascii') for line in patch.splitlines()
                  if line.startswith(b'+++ b/'))
    progress.require(names == FILES, 'Host beacon patch scope changed')
    with tempfile.TemporaryDirectory(prefix='coh-beacon-source-') as temporary:
        stage = Path(temporary)
        for name in FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / 'upstream/ouroboros' / name, target)
        inputs = {name: progress.sha256(stage / name) for name in FILES}
        apply_patch(stage, patch)
        outputs = {name: progress.sha256(stage / name) for name in FILES}
    return {
        'format': 1, 'build_role': 'host_only_atlas_beacon_generator',
        'source_commit': json.loads((root / 'source-target.json').read_text())['source_commit'],
        'base': progress.expected_progress_receipt(root),
        'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': inputs, 'patched_sha256': outputs,
        'retained_algorithm_sha256': {name: progress.sha256(root / 'upstream/ouroboros' / name)
                                      for name in RETAINED},
        'contract': {'map': MAP, 'roles': ['master', 'server', 'sentry', 'worker'],
                     'worker_count': 1, 'address': '127.0.0.1',
                     'ordinary_gameplay_startup_allowed': False,
                     'production_mode_allowed': False, 'installation_allowed': False,
                     'native_worker_spawning_allowed': False,
                     'map_list_count': 1, 'single_pass': True,
                     'native_full_graph_readback': True,
                     'fresh_ordinary_world_crc_match_required': True,
                     'native_pathfinder_successes_required': 32,
                     'fresh_process_input_profiles': ['base_world', 'base_world_visual'],
                     'profile_verification_network_start_allowed': False,
                     'shippable_gameplay_binary': False},
        'build_targets': ['MapServer'], 'runtime_validation': 'pending_generation',
    }


def prepare(output, root=ROOT):
    output, root = Path(output), Path(root)
    receipt = expected(root)
    progress.prepare(output, root)
    progress.require(json.loads((output / progress.RECEIPT).read_text()) == receipt['base'],
                     'Staged MapServer base changed')
    for name, digest in receipt['source_sha256'].items():
        progress.require(progress.sha256(output / name) == digest,
                         'Generator source differs: ' + name)
    apply_patch(output, (root / PATCH).read_bytes().replace(b'\r\n', b'\n'))
    for name, digest in {**receipt['patched_sha256'],
                         **receipt['retained_algorithm_sha256']}.items():
        progress.require(progress.sha256(output / name) == digest,
                         'Generator patch/retained algorithm changed: ' + name)
    (output / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.output)
    print(json.dumps({'status': 'staged', 'role': result['build_role'],
                      'canonical_sha256': canonical_hash(result)}))


if __name__ == '__main__':
    main()

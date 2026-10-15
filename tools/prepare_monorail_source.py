#!/usr/bin/env python3
"""Stage the finite native station bridge after the retained character events."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import prepare_character_events_source as events
from prepare_resume_client_source import apply_patch, canonical_hash
from prepare_runtime import require, sha256
ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/monorail/0001-monorail.patch'
OVERLAY = 'database/monorail/overlay'
RECEIPT = 'monorail-build-input.json'
FILES = (*events.EVENTS_FILES, 'MapServer/src/door.c')
OVERLAY_FILES = ('MapServer/src/svr/wine_monorail.c', 'MapServer/src/svr/wine_monorail.h')
COLLISION_FILES = ('MapServer/src/beacon/beaconGenerate.c', 'MapServer/src/beacon/beaconConnection.c',
    'MapServer/src/beacon/beaconFile.c', 'MapServer/src/beacon/beaconPath.c',
    'Common/group/groupfileload.c', 'Common/gridcoll/gridcoll.c')
CONTRACT = {'format': 1, 'environment_variable': 'COH_WINE_MONORAIL_SESSION',
    'reply_environment_variable': 'COH_WINE_MONORAIL_REPLY',
    'native_event_prefix': 'COH_ZONING_EVENT_V1', 'reply_prefix': 'COH_MONORAIL_REPLY_V1',
    'disabled_by_default': True, 'station_maps': [1, 5], 'event_maps': [1, 5, 101],
    'station_line': 'ParagonCityMonorail', 'spawn': 'LinkFrom_Monorail_ParagonCity',
    'transport': 'owned_flushed_console_and_private_atomic_reply',
    'game_and_dbserver_rebuild_required': False,
    'stock_door_validation_repeated_after_readiness': True,
    'station_preparation_timeout_seconds': 600, 'physical_validation': False}

def patch_bytes(root=ROOT):
    value=(Path(root)/PATCH).read_bytes().replace(b'\r\n',b'\n')
    names=[line[6:] for line in value.decode().splitlines() if line.startswith('+++ b/')]
    require(len(names)==len(FILES) and set(names)==set(FILES),'Unexpected monorail patch files')
    return value

def overlay_bytes(root=ROOT):
    directory=Path(root)/OVERLAY
    paths=list(directory.rglob('*'))
    require(not any(p.is_symlink() for p in paths),'Linked monorail overlay')
    require({p.relative_to(directory).as_posix() for p in paths if p.is_file()}==set(OVERLAY_FILES),'Monorail overlay file set differs')
    return {n:(directory/n).read_bytes().replace(b'\r\n',b'\n') for n in OVERLAY_FILES}

def expected_receipt(root=ROOT, events_build_input=None):
    root=Path(root)
    base=events.expected_events_receipt(root,None if events_build_input is None else events_build_input.get('progress_build_input'))
    require(events_build_input is None or events_build_input==base,'Monorail character-event prerequisite differs')
    with tempfile.TemporaryDirectory(prefix='coh-monorail-input-') as tmp:
        source=Path(tmp)
        for name in set(FILES).union(events.progress.game.GAME_FILES):
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/'upstream/ouroboros'/name,path)
        for patch in (events.progress.game.patch_bytes(root),events.progress.patch_bytes(root),events.patch_bytes(root)):
            apply_patch(source,patch)
        inputs={n:sha256(source/n) for n in FILES}
        apply_patch(source,patch_bytes(root))
        outputs={n:sha256(source/n) for n in FILES}
    return {'schema_version':1,'build_role':'monorail','source_commit':base['source_commit'],
        'events_build_input':base,'events_build_input_canonical_sha256':canonical_hash(base),
        'patch_sha256':hashlib.sha256(patch_bytes(root)).hexdigest(),
        'overlay_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in overlay_bytes(root).items()},
        'source_sha256':inputs,'patched_sha256':outputs,'contract':CONTRACT,
        'retained_collision_sources':{n:sha256(root/'upstream/ouroboros'/n) for n in COLLISION_FILES},
        'build_targets':['MapServer'],'runtime_validation':'unverified'}

def apply_monorail_overlay(source,root=ROOT):
    source,root=Path(source).resolve(),Path(root).resolve()
    require(source != root and root/'upstream' not in (source,*source.parents),'Immutable upstream staging refused')
    receipt=source/RECEIPT
    require(not receipt.exists() and not receipt.is_symlink(),'Monorail overlay already staged')
    previous=source/events.RECEIPT
    require(previous.is_file() and not previous.is_symlink(),'Missing character events prerequisite')
    expected=expected_receipt(root,json.loads(previous.read_text()))
    for name,digest in expected['source_sha256'].items():
        path=source/name
        require(path.is_file() and not path.is_symlink() and sha256(path)==digest,'Monorail source identity differs: '+name)
    for name,data in overlay_bytes(root).items():
        path=source/name
        require(not path.exists() and not path.is_symlink(),'Monorail overlay target exists')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    apply_patch(source,patch_bytes(root))
    require({n:sha256(source/n) for n in FILES}==expected['patched_sha256'],'Monorail applied source differs')
    require({n:sha256(source/n) for n in COLLISION_FILES}==expected['retained_collision_sources'],
        'Monorail changed native collision/beacon algorithms')
    receipt.write_text(json.dumps(expected,indent=2)+'\n')
    return expected

def prepare(output,root=ROOT):
    events.prepare(output,root)
    return apply_monorail_overlay(output,root)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    prepare(parser.parse_args().output)

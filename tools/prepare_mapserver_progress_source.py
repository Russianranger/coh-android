#!/usr/bin/env python3
"""Stage an opt-in MapServer progress overlay after creation loopback source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import prepare_game_loopback_source as game
from prepare_runtime import require, sha256
from prepare_resume_client_source import apply_patch, canonical_hash

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/mapserver-progress/0001-mapserver-progress.patch'
OVERLAY = 'database/mapserver-progress/overlay'
RECEIPT = 'mapserver-progress-build-input.json'
PROGRESS_FILES = ('MapServer/CMakeLists.txt', 'MapServer/src/svr/svr_init.c',
                  'MapServer/src/svr/svr_tick.c')
OVERLAY_FILES = ('MapServer/src/svr/wine_map_progress.c', 'MapServer/src/svr/wine_map_progress.h')


def patch_bytes(root=ROOT):
    value = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in value.decode().splitlines() if line.startswith('+++ b/')]
    require(len(names) == len(PROGRESS_FILES) and set(names) == set(PROGRESS_FILES),
            'Unexpected MapServer progress patch file list')
    return value


def overlay_bytes(root=ROOT):
    directory = root / OVERLAY
    paths = tuple(directory.rglob('*'))
    require(not any(path.is_symlink() for path in paths), 'MapServer progress overlay contains linked paths')
    names = {path.relative_to(directory).as_posix() for path in paths if path.is_file()}
    require(names == set(OVERLAY_FILES), 'Unexpected MapServer progress overlay file list')
    return {name: (directory / name).read_bytes().replace(b'\r\n', b'\n') for name in sorted(names)}


def progress_metadata(contents):
    header = contents[OVERLAY_FILES[1]].decode('utf-8')
    constants = dict(re.findall(r'^#define (COH_MAP_PROGRESS_\w+) (.+)$', header, re.MULTILINE))
    require(constants == {'COH_MAP_PROGRESS_ENVIRONMENT': '"COH_WINE_MAP_PROGRESS"',
                          'COH_MAP_PROGRESS_FORMAT': '1', 'COH_MAP_PROGRESS_RECORD_BYTES': '128',
                          'COH_MAP_PROGRESS_MAPPING_BYTES': '4096', 'COH_MAP_PROGRESS_FLAG_SATURATED': '1'},
            'Unexpected MapServer progress header constants')
    entries = re.findall(r'^    COH_MAP_STAGE_([A-Z0-9_]+) = (\d+),?$', header, re.MULTILINE)
    require(entries and [int(number) for _, number in entries] == list(range(1, len(entries) + 1))
            and len({name for name, _ in entries}) == len(entries)
            and entries[-1][0] == 'SLEEP_DONE', 'MapServer progress stages differ')
    stages = {number: name for name, number in entries}
    require(stages.get('24') == 'TICK_BEGIN' and stages.get('34') == 'TICK_DONE',
            'MapServer progress tick counter stages differ')
    return {
        'environment_variable': 'COH_WINE_MAP_PROGRESS', 'format': 1,
        'record_bytes': 128, 'mapping_bytes': 4096, 'magic_hex': b'COHMAP1\0'.hex(),
        'byte_order': 'little',
        'offsets': {'magic': 0, 'format': 8, 'record_bytes': 12, 'process_id': 16,
                    'main_thread_id': 20, 'sequence': 24, 'stage': 28,
                    'tick_started': 32, 'tick_completed': 36, 'flags': 40,
                    'stage_count': 44, 'reserved': 48},
        'reserved_bytes': 80, 'stages': stages,
        'disabled_by_default': True, 'writer': 'mapserver_main_thread',
        'stage_semantics': 'operation_about_to_run_unless_DONE_or_ED',
        'sequence_semantics': 'positive_even_stable_odd_updating_no_wrap',
        'tick_started_stage': 24, 'tick_completed_stage': 34,
        'counter_semantics': 'monotonic_no_wrap_completed_not_greater_than_started',
        'flags': {'1': 'sequence_or_counter_saturated_samples_unavailable'},
        'initialization_failure': 'requested_launch_exits_nonzero',
        'file_creation': 'new_absolute_drive_path_private_parent_required',
        'proves_readiness_or_game_success': False,
    }


def expected_progress_receipt(root=ROOT, game_build_input=None):
    root = Path(root)
    if game_build_input is not None:
        require(isinstance(game_build_input, dict)
                and isinstance(game_build_input.get('postgresql_build_input'), dict),
                'Missing creation loopback source receipt')
    expected_game = game.expected_game_receipt(root, None if game_build_input is None
                                               else game_build_input['postgresql_build_input'], 'creation')
    require(game_build_input is None or game_build_input == expected_game,
            'Creation loopback source receipt mismatch')
    pg = expected_game['postgresql_build_input']
    require(not set(PROGRESS_FILES).intersection(pg['patched_sha256']),
            'MapServer progress and PostgreSQL patches overlap; explicit rebase required')
    contents, patch = overlay_bytes(root), patch_bytes(root)
    with tempfile.TemporaryDirectory(prefix='coh-map-progress-receipt-') as temporary:
        stage = Path(temporary)
        for name in set(PROGRESS_FILES).union(game.GAME_FILES):
            original = root / 'upstream/ouroboros' / name
            require(original.is_file() and not original.is_symlink(), 'Missing immutable source: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
        apply_patch(stage, game.patch_bytes(root))
        inputs = {name: sha256(stage / name) for name in PROGRESS_FILES}
        apply_patch(stage, patch)
        outputs = {name: sha256(stage / name) for name in PROGRESS_FILES}
    require(all(inputs[name] != outputs[name] for name in PROGRESS_FILES),
            'MapServer progress patch left a file unchanged')
    return {'schema_version': 1, 'build_role': 'mapserver_progress',
            'source_commit': expected_game['source_commit'], 'game_build_input': expected_game,
            'game_build_input_canonical_sha256': canonical_hash(expected_game),
            'progress_patch_sha256': hashlib.sha256(patch).hexdigest(),
            'progress_overlay_sha256': {name: hashlib.sha256(value).hexdigest()
                                       for name, value in contents.items()},
            'source_sha256': inputs, 'patched_sha256': outputs,
            'progress_contract': progress_metadata(contents),
            'build_targets': ['MapServer'], 'runtime_validation': 'unverified'}


def apply_progress_overlay(source, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source not in (root, root / 'upstream') and root / 'upstream' not in source.parents,
            'MapServer progress overlay may not modify immutable snapshots')
    receipt_path = source / RECEIPT
    require(not receipt_path.exists() and not receipt_path.is_symlink(),
            'MapServer progress receipt already exists; use a fresh staging tree')
    game_path = source / game.RECEIPT
    require(game_path.is_file() and not game_path.is_symlink(), 'Missing creation loopback source receipt')
    expected = expected_progress_receipt(root, json.loads(game_path.read_text()))
    base = expected['game_build_input']
    pg = base['postgresql_build_input']
    pg_path = source / 'postgresql-build-input.json'
    require(pg_path.is_file() and not pg_path.is_symlink() and json.loads(pg_path.read_text()) == pg,
            'PostgreSQL source receipt differs from loopback source')
    require(not (source / game.resume.RECEIPT).exists() and not (source / game.resume.RECEIPT).is_symlink(),
            'MapServer progress requires creation source without a resume overlay')
    inputs = {**pg['patched_sha256'], **pg['overlay_sha256'], **base['patched_sha256'],
              **expected['source_sha256']}
    for name, digest in inputs.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                'Staged source SHA-256 mismatch: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents), 'Staged source parent is linked: ' + name)
    contents = overlay_bytes(root)
    for name in contents:
        path = source / name
        require(not path.exists() and not path.is_symlink(), 'MapServer progress overlay would overwrite source: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents), 'MapServer progress overlay parent is linked')
    apply_patch(source, patch_bytes(root))
    require({name: sha256(source / name) for name in PROGRESS_FILES} == expected['patched_sha256'],
            'Applied MapServer progress patch hashes differ from receipt')
    for name, value in contents.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    receipt_path.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def prepare(output, root=ROOT):
    game.prepare(output, root, variant='creation')
    return apply_progress_overlay(output, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.output)
    print('Prepared separately identified MapServer progress source:', args.output)


if __name__ == '__main__':
    main()

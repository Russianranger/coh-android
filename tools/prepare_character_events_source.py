#!/usr/bin/env python3
"""Stage immediate character events after the unchanged MapServer progress overlay."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

import prepare_mapserver_progress_source as progress
from prepare_runtime import require, sha256
from prepare_resume_client_source import apply_patch, canonical_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'android/guest'))
import native_character_events as events

PATCH = 'patches/character-events/0001-character-events.patch'
OVERLAY = 'database/character-events/overlay'
RECEIPT = 'character-events-build-input.json'
EVENTS_FILES = progress.PROGRESS_FILES
OVERLAY_FILES = ('MapServer/src/svr/wine_character_events.c',
                 'MapServer/src/svr/wine_character_events.h')


def patch_bytes(root=ROOT):
    value = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in value.decode().splitlines() if line.startswith('+++ b/')]
    require(len(names) == len(EVENTS_FILES) and set(names) == set(EVENTS_FILES),
            'Unexpected character event patch file list')
    return value


def overlay_bytes(root=ROOT):
    directory = root / OVERLAY
    paths = tuple(directory.rglob('*'))
    require(not any(path.is_symlink() for path in paths), 'Character event overlay contains linked paths')
    names = {path.relative_to(directory).as_posix() for path in paths if path.is_file()}
    require(names == set(OVERLAY_FILES), 'Unexpected character event overlay file list')
    return {name: (directory / name).read_bytes().replace(b'\r\n', b'\n') for name in sorted(names)}


def expected_events_receipt(root=ROOT, progress_build_input=None):
    root = Path(root)
    require(progress_build_input is None or isinstance(progress_build_input, dict),
            'Missing character event progress source receipt')
    expected_progress = progress.expected_progress_receipt(root,
        None if progress_build_input is None else progress_build_input.get('game_build_input'))
    require(progress_build_input is None or progress_build_input == expected_progress,
            'Character event progress source receipt mismatch')
    contents, patch = overlay_bytes(root), patch_bytes(root)
    header = contents[OVERLAY_FILES[1]].decode()
    require(re.findall(r'^#define (COH_CHARACTER_EVENTS_\w+) (.+)$', header, re.MULTILINE) == [
                ('COH_CHARACTER_EVENTS_ENVIRONMENT', '"' + events.ENVIRONMENT + '"'),
                ('COH_CHARACTER_EVENTS_FORMAT', '1')],
            'Character event native format or environment differs')
    with tempfile.TemporaryDirectory(prefix='coh-character-events-receipt-') as temporary:
        stage = Path(temporary)
        for name in set(EVENTS_FILES).union(progress.game.GAME_FILES):
            original = root / 'upstream/ouroboros' / name
            require(original.is_file() and not original.is_symlink(), 'Missing immutable source: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
        apply_patch(stage, progress.game.patch_bytes(root))
        apply_patch(stage, progress.patch_bytes(root))
        inputs = {name: sha256(stage / name) for name in EVENTS_FILES}
        require(inputs == expected_progress['patched_sha256'], 'Character event source base differs')
        apply_patch(stage, patch)
        outputs = {name: sha256(stage / name) for name in EVENTS_FILES}
    require(all(inputs[name] != outputs[name] for name in EVENTS_FILES),
            'Character event patch left a file unchanged')
    return {'schema_version': 1, 'build_role': 'character_events',
        'source_commit': expected_progress['source_commit'],
        'progress_build_input': expected_progress,
        'progress_build_input_canonical_sha256': canonical_hash(expected_progress),
        'events_patch_sha256': hashlib.sha256(patch).hexdigest(),
        'events_overlay_sha256': {name: hashlib.sha256(value).hexdigest()
                                 for name, value in contents.items()},
        'source_sha256': inputs, 'patched_sha256': outputs,
        'progress_contract': expected_progress['progress_contract'],
        'events_contract': dict(events.CONTRACT),
        'build_targets': ['MapServer'], 'runtime_validation': 'unverified'}


def apply_events_overlay(source, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source not in (root, root / 'upstream') and root / 'upstream' not in source.parents,
            'Character event overlay may not modify immutable snapshots')
    receipt_path = source / RECEIPT
    require(not receipt_path.exists() and not receipt_path.is_symlink(),
            'Character event receipt already exists; use fresh source')
    base_path = source / progress.RECEIPT
    require(base_path.is_file() and not base_path.is_symlink(), 'Missing MapServer progress source receipt')
    expected = expected_events_receipt(root, json.loads(base_path.read_text()))
    native = expected['progress_build_input']
    game = native['game_build_input']
    pg = game['postgresql_build_input']
    for name, value in ((progress.game.RECEIPT, game), ('postgresql-build-input.json', pg)):
        path = source / name
        require(path.is_file() and not path.is_symlink() and json.loads(path.read_text()) == value,
                'Character event source prerequisite receipts differ')
    inputs = {**pg['patched_sha256'], **pg['overlay_sha256'], **game['patched_sha256'],
              **native['progress_overlay_sha256'], **expected['source_sha256']}
    for name, digest in inputs.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                'Staged character event source SHA-256 mismatch: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents), 'Character event source parent is linked')
    contents = overlay_bytes(root)
    for name in contents:
        path = source / name
        require(not path.exists() and not path.is_symlink(), 'Character event overlay would overwrite source: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents), 'Character event overlay parent is linked')
    apply_patch(source, patch_bytes(root))
    require({name: sha256(source / name) for name in EVENTS_FILES} == expected['patched_sha256'],
            'Applied character event hashes differ from receipt')
    for name, value in contents.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    receipt_path.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def prepare(output, root=ROOT):
    progress.prepare(output, root)
    return apply_events_overlay(output, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.output)
    print('Prepared immediate native character event source:', args.output)


if __name__ == '__main__':
    main()

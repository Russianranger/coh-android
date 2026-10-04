#!/usr/bin/env python3
"""Apply a separately identified reversible Android client graphics overlay.

Call after the separately receipted native event/texture overlays. This patch
touches only gfxSettings.c; it never modifies the immutable upstream snapshot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from prepare_runtime import require, sha256
from prepare_resume_client_source import apply_patch

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/client-graphics/0001-reversible-performance-profile.patch'
OVERLAY = 'database/client-graphics/overlay'
RECEIPT = 'client-graphics-build-input.json'
GRAPHICS_FILES = ('Game/src/graphics/gfxSettings.c',)
OVERLAY_FILES = ('Game/src/graphics/cohAndroidGraphicsProfile.h',)


def patch_bytes(root=ROOT):
    value = (Path(root) / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in value.decode().splitlines() if line.startswith('+++ b/')]
    require(names == list(GRAPHICS_FILES), 'Unexpected client graphics patch file list')
    return value


def overlay_bytes(root=ROOT):
    directory = Path(root) / OVERLAY
    paths = tuple(directory.rglob('*'))
    require(not directory.is_symlink() and not any(path.is_symlink() for path in paths),
            'Client graphics overlay contains linked paths')
    names = {path.relative_to(directory).as_posix() for path in paths if path.is_file()}
    require(names == set(OVERLAY_FILES), 'Unexpected client graphics overlay file list')
    return {name: (directory / name).read_bytes().replace(b'\r\n', b'\n') for name in sorted(names)}


def expected_graphics_receipt(root=ROOT):
    root = Path(root)
    lock = json.loads((root / 'upstream-lock.json').read_text())
    patch, contents = patch_bytes(root), overlay_bytes(root)
    with tempfile.TemporaryDirectory(prefix='coh-client-graphics-receipt-') as temporary:
        stage = Path(temporary)
        for name in GRAPHICS_FILES:
            original = root / 'upstream/ouroboros' / name
            require(original.is_file() and not original.is_symlink(), 'Missing immutable source: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
        inputs = {name: sha256(stage / name) for name in GRAPHICS_FILES}
        apply_patch(stage, patch)
        outputs = {name: sha256(stage / name) for name in GRAPHICS_FILES}
    require(all(inputs[name] != outputs[name] for name in GRAPHICS_FILES),
            'Client graphics patch left a file unchanged')
    return {'schema_version': 1, 'build_role': 'client_graphics_profile',
            'source_commit': lock['commit'], 'graphics_patch_sha256': hashlib.sha256(patch).hexdigest(),
            'graphics_overlay_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in contents.items()},
            'source_sha256': inputs, 'patched_sha256': outputs,
            'graphics_contract': {'environment_variable': 'COH_CLIENT_GRAPHICS_PROFILE',
                                  'enabled_value': 'performance', 'default_native_profile': 'standard',
                                  'scope': 'Game_graphics_only', 'world_render_scale': 0.75,
                                  'ui_resolution': [800, 600], 'native_preset': 'gfxGetMinAdvancedSettings',
                                  'preserve_saved_preferences': 'capture_before_first_apply_restore_on_save',
                                  'renderer': 'unchanged', 'device_fps_gain_measured': False},
            'build_targets': ['Game'], 'runtime_validation': 'unverified'}


def apply_graphics_overlay(source, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source not in (root, root / 'upstream') and root / 'upstream' not in source.parents,
            'Client graphics overlay may not modify immutable snapshots')
    receipt_path = source / RECEIPT
    require(not receipt_path.exists() and not receipt_path.is_symlink(),
            'Client graphics receipt already exists; use a fresh staging tree')
    expected = expected_graphics_receipt(root)
    for name, digest in expected['source_sha256'].items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                'Staged client graphics source SHA-256 mismatch: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents), 'Staged client graphics source parent is linked')
    contents = overlay_bytes(root)
    for name in contents:
        path = source / name
        require(not path.exists() and not path.is_symlink(), 'Client graphics overlay would overwrite source: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents), 'Client graphics overlay parent is linked')
    apply_patch(source, patch_bytes(root))
    require({name: sha256(source / name) for name in GRAPHICS_FILES} == expected['patched_sha256'],
            'Applied client graphics patch hashes differ from receipt')
    for name, value in contents.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    receipt_path.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    apply_graphics_overlay(args.source)
    print('Applied separately identified client graphics overlay:', args.source)


if __name__ == '__main__':
    main()

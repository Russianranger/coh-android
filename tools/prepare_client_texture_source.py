"""Apply the opt-in header index only to fresh verified staged native sources."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
from prepare_resume_client_source import apply_patch

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/client-texture-index/0001-index-texture-headers.patch'
OVERLAY = 'database/client-texture-index/overlay'
RECEIPT = 'client-texture-build-input.json'
FILES = ('Game/src/render/tex.c', 'Game/src/render/tex.h', 'Common/gameComm/NPC.c',
         'Common/gameData/costume_data.c', 'Common/seq/tricks.c')
OVERLAY_FILE = 'Game/src/render/coh_texture_header_index.h'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_texture_receipt(root=ROOT):
    root = Path(root)
    patch = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')]
    if len(names) != len(FILES) or set(names) != set(FILES):
        raise ValueError('Texture patch inventory differs')
    inputs = {name: digest(root / 'upstream/ouroboros' / name) for name in FILES}
    with tempfile.TemporaryDirectory(prefix='coh-texture-source-') as temporary:
        staged = Path(temporary)
        for name in FILES:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / 'upstream/ouroboros' / name, target)
        apply_patch(staged, patch)
        outputs = {name: digest(staged / name) for name in FILES}
    return {'format': 1, 'role': 'opt_in_client_texture_header_index',
        'source_commit': json.loads((root / 'upstream-lock.json').read_text())['commit'],
        'patch_sha256': hashlib.sha256(patch).hexdigest(), 'source_sha256': inputs,
        'patched_sha256': outputs, 'overlay_sha256': {OVERLAY_FILE: digest(root / OVERLAY / OVERLAY_FILE)},
        'texture_header_struct_bytes': 32, 'parse6_schema_changes': False,
        'full_texture_asset_changes': False, 'fallback': 'ordinary_native_file_reads',
        'runtime_performance_validated': False}


def apply_texture_overlay(source, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    if source == root or source.is_relative_to(root / 'upstream') or (source / RECEIPT).exists():
        raise ValueError('Fresh staged source outside snapshots required')
    receipt = expected_texture_receipt(root)
    for name, sha in receipt['source_sha256'].items():
        if (source / name).is_symlink() or digest(source / name) != sha:
            raise ValueError('Texture source closure differs: ' + name)
    apply_patch(source, (root / PATCH).read_bytes().replace(b'\r\n', b'\n'))
    target = source / OVERLAY_FILE
    if target.exists():
        raise ValueError('Texture overlay would overwrite a source file')
    target.write_bytes((root / OVERLAY / OVERLAY_FILE).read_bytes())
    if any(digest(source / name) != sha for name, sha in receipt['patched_sha256'].items()):
        raise ValueError('Patched texture source closure differs')
    (source / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt

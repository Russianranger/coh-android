#!/usr/bin/env python3
"""Install the pinned default male avatar supplement into one private worktree."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile

import client_startup_diagnostic as client

require = client.require
MANIFEST = 'character-avatar-defaults-manifest.json'
ARCHIVE = 'character-avatar-defaults.zip'
MANIFEST_SHA256 = '2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7'
ARCHIVE_SHA256 = '03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29'
ARCHIVE_BYTES, PAYLOAD_BYTES = 1842488, 2980122
ALLOWED = frozenset({
    'data/player_library/male_boot.geo',
    'data/player_library/male_glove.geo',
    'data/player_library/male_hair.geo',
    'data/player_library/male_pants.geo',
    'data/player_library/male_shirt.geo',
    'data/player_library/v_male_head.geo',
    'data/texture_library/players/avatar/male/chest/leather/chest_leather_03.texture',
    'data/texture_library/players/avatar/male/chest/leather/chest_leather_03_mask.texture',
    'data/texture_library/players/avatar/male/chest/tights/chest_tights.texture',
    'data/texture_library/players/avatar/male/hips/leather/hips_leather_03.texture',
    'data/texture_library/players/avatar/male/hips/leather/hips_leather_03_mask.texture',
    'data/texture_library/players/avatar/male/hips/tights/hips_tights.texture',
    'data/texture_library/players/avatar/super_shared/boots/boot_leather_03.texture',
    'data/texture_library/players/avatar/super_shared/boots/boot_leather_03_mask.texture',
    'data/texture_library/players/avatar/super_shared/boots/boot_smooth_01.texture',
    'data/texture_library/players/avatar/super_shared/gloves/glove_leather_03.texture',
    'data/texture_library/players/avatar/super_shared/gloves/glove_leather_03_mask.texture',
    'data/texture_library/players/avatar/super_shared/gloves/glove_smooth_01.texture',
    'data/texture_library/players/avatar/super_shared/hair/hair_style_01a.texture',
    'data/texture_library/players/avatar/super_shared/hair/hair_style_01b.texture',
    'data/texture_library/v_players/avatar/super_shared/patterns/face/face_v_asym_eyes_01.texture',
})


def read_regular(path, limit, *, installed=False):
    """Read bounded owned bytes without following links or accepting hard links."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_uid == os.geteuid() and 0 < before.st_size <= limit,
                'Invalid avatar supplement file: ' + path.name)
        if installed:
            require(stat.S_IMODE(before.st_mode) == 0o444 and int(before.st_mtime) == client.CACHE_EPOCH,
                    'Avatar supplement permissions or timestamp differ: ' + path.name)
        with os.fdopen(fd, 'rb', closefd=False) as source:
            raw = source.read(limit + 1)
        after = os.fstat(fd)
        require(len(raw) == before.st_size and (after.st_size, after.st_mtime_ns, after.st_nlink)
                == (before.st_size, before.st_mtime_ns, 1), 'Avatar supplement changed while reading')
        return raw
    finally:
        os.close(fd)


def package(assets):
    manifest_raw = read_regular(assets / MANIFEST, 128 * 1024)
    require(hashlib.sha256(manifest_raw).hexdigest() == MANIFEST_SHA256,
            'Avatar supplement manifest differs from the reviewed pin')
    manifest = json.loads(manifest_raw)
    require(manifest.get('format') == 1 and manifest.get('scope') == 'default_male_avatar_supplement'
            and manifest.get('source_commit') == client.SOURCE and manifest.get('data_commit') == client.DATA
            and manifest.get('file_count') == len(ALLOWED) and manifest.get('payload_bytes') == PAYLOAD_BYTES
            and set(manifest.get('files', {})) == ALLOWED
            and manifest.get('archive') == {'filename': ARCHIVE, 'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
            'Avatar supplement provenance or allowlist differs')
    raw = read_regular(assets / ARCHIVE, ARCHIVE_BYTES)
    require(len(raw) == ARCHIVE_BYTES and hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256,
            'Avatar supplement archive differs from the reviewed pin')
    payloads = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(len(entries) == len(ALLOWED) and {item.filename for item in entries} == ALLOWED,
                'Avatar supplement ZIP inventory differs')
        for entry in entries:
            pin = manifest['files'][entry.filename]
            require(not entry.is_dir() and not entry.flag_bits & 1
                    and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
                    and entry.file_size == pin['bytes'] and 0 < entry.file_size <= PAYLOAD_BYTES,
                    'Invalid avatar supplement ZIP member')
            content = archive.read(entry)
            require(len(content) == pin['bytes'] and hashlib.sha256(content).hexdigest() == pin['sha256'],
                    'Avatar supplement payload differs: ' + entry.filename)
            payloads[entry.filename] = content
    require(sum(map(len, payloads.values())) == PAYLOAD_BYTES, 'Avatar supplement payload bound differs')
    return manifest, payloads


def real_directory(path):
    require(path.is_absolute() and '..' not in path.parts, 'Expected an absolute private avatar directory')
    for current in [*reversed(path.parents), path]:
        info = current.lstat()
        require(stat.S_ISDIR(info.st_mode), 'Linked or non-directory avatar destination refused')


def verify_target(path, pin):
    try:
        raw = read_regular(path, pin['bytes'], installed=True)
    except FileNotFoundError:
        return False
    require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
            'Existing avatar supplement conflicts with the reviewed payload: ' + path.name)
    return True


def install(worktree, assets, context):
    """Add missing assets only; reuse requires every installed byte to reverify."""
    real_directory(worktree)
    real_directory(worktree / 'data')
    manifest, payloads = package(assets)
    directories, verified = {}, {}
    # Preflight every destination before writing any payload. Case aliases
    # are conflicts because Wine can resolve names without regard to case.
    for name in sorted(ALLOWED):
        context.check()
        target = worktree
        for part in Path(name).parts:
            if target.exists() or target.is_symlink():
                real_directory(target)
                if target not in directories:
                    names = {}
                    for item in target.iterdir():
                        names.setdefault(item.name.casefold(), []).append(item.name)
                    directories[target] = names
                matches = directories[target].get(part.casefold(), [])
                require(not matches or matches == [part], 'Case-conflicting avatar destination refused')
            target /= part
        verified[name] = verify_target(target, manifest['files'][name])
    installed = 0
    for name in sorted(ALLOWED):
        context.check()
        target = worktree / name
        if verified[name]:
            continue
        parent = worktree
        for part in Path(name).parts[:-1]:
            parent /= part
            parent.mkdir(mode=0o700, exist_ok=True)
            real_directory(parent)
        descriptor, temporary = tempfile.mkstemp(prefix='.avatar-pending-', dir=target.parent)
        temporary = Path(temporary)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(payloads[name]); output.flush(); os.fsync(output.fileno())
            os.chmod(temporary, 0o444)
            os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
            # link is atomic and refuses an existing target, unlike replace.
            os.link(temporary, target, follow_symlinks=False)
        finally:
            temporary.unlink(missing_ok=True)
        require(verify_target(target, manifest['files'][name]), 'Avatar supplement publication failed')
        installed += 1
    return {'format': 1, 'scope': manifest['scope'], 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'file_count': len(ALLOWED), 'payload_bytes': PAYLOAD_BYTES,
        'installed_files': installed, 'reused_files': len(ALLOWED) - installed,
        'worktree': worktree.name, 'files': manifest['files'], 'normalized_mtime_epoch': client.CACHE_EPOCH,
        'imported_files_modified': False, 'worktree_identity_modified': False, 'cache_files_modified': False,
        'runtime_visual_validated': False, 'visual_scope': manifest['visual_scope']}

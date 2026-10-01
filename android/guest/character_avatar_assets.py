#!/usr/bin/env python3
"""Install the pinned default male avatar supplement into one private worktree."""
import hashlib
import errno
import io
import json
import os
import re
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


LEGACY_LINK = re.compile(r'\.(?:proot\.)?l2s\.\.avatar-pending-[a-z0-9_]{8}0001')


def legacy_parent(value, worktree, relative_parent):
    """Validate an old embedded path; never follow or open that path."""
    old = Path(value)
    require(old.is_absolute() and '..' not in old.parts and str(old) == value,
            'Invalid legacy avatar link')
    suffix = relative_parent.parts
    require(tuple(old.parent.parts[-len(suffix):]) == suffix,
            'Legacy avatar link directory differs')
    previous = old.parent.parents[len(suffix)-1].name
    require(re.fullmatch(r'client-work-[0-9a-f]{24}', previous) is not None
            and previous != worktree.name, 'Legacy avatar link is not from a moved worktree')
    return old


def legacy_target(target, worktree, pin):
    """Recognize only the stale two-link layout of the old avatar publisher."""
    value = os.readlink(target)
    old = legacy_parent(value, worktree, target.parent.relative_to(worktree))
    require(LEGACY_LINK.fullmatch(old.name) is not None, 'Unrecognized legacy avatar link')
    intermediate = target.parent / old.name
    final_value = os.readlink(intermediate)
    require(final_value == value + '.0001', 'Legacy avatar backing chain differs')
    backing = target.parent / (old.name + '.0001')
    require(verify_target(backing, pin), 'Missing legacy avatar backing file')
    return (value, intermediate, final_value, backing)


def legacy_orphans(worktree, verified, repairs, manifest):
    """Preflight pinned leftovers, including a cancelled cleanup after replacement."""
    result = []
    parents = { (worktree / name).parent for name in ALLOWED }
    for parent in sorted(parents):
        if not parent.exists():
            continue
        candidates = list(parent.iterdir())
        backing_names = [path for path in candidates if path.name.endswith('.0001')
                         and LEGACY_LINK.fullmatch(path.name[:-5])]
        names = [name for name in ALLOWED if (worktree / name).parent == parent]
        require(len(backing_names) <= len(names), 'Too many legacy avatar backing files')
        for backing in backing_names:
            raw = read_regular(backing, PAYLOAD_BYTES, installed=True)
            matching = [name for name in names if manifest['files'][name] == {
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}]
            require(len(matching) == 1, 'Unrecognized legacy avatar backing bytes')
            name = matching[0]
            intermediate = parent / backing.name[:-5]
            if name in repairs:
                require(repairs[name][1] == intermediate and repairs[name][3] == backing,
                        'Ambiguous legacy avatar backing chain')
            else:
                require(verified[name], 'Orphan avatar backing has no verified destination')
                # Directory entry type is physical, unlike PRoot's virtual stat.
                with os.scandir(parent) as entries:
                    linked = next(item.is_symlink() for item in entries if item.name == Path(name).name)
                require(not linked, 'Orphan avatar destination is linked')
                if os.path.lexists(intermediate):
                    old_final = legacy_parent(os.readlink(intermediate), worktree, parent.relative_to(worktree))
                    require(old_final.name == backing.name, 'Orphan avatar backing chain differs')
            result.append((name, intermediate, backing))
    return result


def install(worktree, assets, context):
    """Add missing assets or repair verified stale legacy leaves in the private tree."""
    real_directory(worktree)
    real_directory(worktree / 'data')
    manifest, payloads = package(assets)
    directories, verified, repairs = {}, {}, {}
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
        try:
            verified[name] = verify_target(target, manifest['files'][name])
        except OSError as error:
            if error.errno != errno.ELOOP:
                raise
            repairs[name] = legacy_target(target, worktree, manifest['files'][name])
            verified[name] = False
    leftovers = legacy_orphans(worktree, verified, repairs, manifest)
    installed = 0
    repaired = 0
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
            if name in repairs:
                value, intermediate, final_value, backing = repairs[name]
                require(os.readlink(target) == value and os.readlink(intermediate) == final_value
                        and verify_target(backing, manifest['files'][name]),
                        'Legacy avatar chain changed before replacement')
                # Only this verified stale leaf is replaced. rename does not
                # follow it; fresh/missing files still use RENAME_NOREPLACE.
                os.replace(temporary, target)
                repaired += 1
            else:
                client.publish_new_regular_file(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        require(verify_target(target, manifest['files'][name]), 'Avatar supplement publication failed')
        installed += 1
    # Remove only preflighted pinned backing files after every logical leaf
    # is verified. A retry can finish this cleanup after an interrupted repair.
    removed = 0
    for name, intermediate, backing in leftovers:
        context.check()
        require(verify_target(worktree / name, manifest['files'][name])
                and verify_target(backing, manifest['files'][name]), 'Avatar repair cleanup differs')
        if os.path.lexists(intermediate):
            intermediate.unlink()
            removed += 1
        backing.unlink()
        removed += 1
    return {'format': 1, 'scope': manifest['scope'], 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'file_count': len(ALLOWED), 'payload_bytes': PAYLOAD_BYTES,
        'installed_files': installed - repaired, 'reused_files': len(ALLOWED) - installed + repaired,
        'legacy_repaired_files': repaired, 'legacy_backing_files_removed': removed,
        'worktree': worktree.name, 'files': manifest['files'], 'normalized_mtime_epoch': client.CACHE_EPOCH,
        'imported_files_modified': False, 'worktree_identity_modified': False, 'cache_files_modified': False,
        'runtime_visual_validated': False, 'visual_scope': manifest['visual_scope']}

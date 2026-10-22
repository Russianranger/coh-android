#!/usr/bin/env python3
"""Print the 32-bit file layout of .anim files (ArmPort check for patch 0033).

SkeletonAnimTrack on disk (596 bytes): headerSize, name[256], baseAnimName[256],
max_hip_displacement, length, bone_tracks (offset), bone_track_count,
rotation_compression_type, position_compression_type, skeletonHeirarchy
(offset), backupAnimTrack, loadstate, lasttimeused, fileAge, spare_room[9].
BoneAnimTrack on disk (20 bytes): rot_idx, pos_idx (offsets), 4 x U16 counts,
id, flags, pad. SkeletonHeirarchy: heirarchy_root + 100 x (child, next, id).

  inspect_anim.py <data dir> [name substring ...]
"""
import os
import struct
import sys

HDR = struct.Struct('<i256s256sffIiiiIIifi36x')
BONE = struct.Struct('<IIHHHHbbH')
HIER_SIZE = 4 + 100 * 12


def describe(path):
    raw = open(path, 'rb').read()
    if len(raw) < HDR.size:
        return f'{path}: {len(raw)} bytes (too short)'
    (header_size, name, base, hip, length, bone_off, bone_count, rot, pos, hier,
     backup, loadstate, last, age) = HDR.unpack_from(raw)
    cstr = lambda b: b.split(b'\0', 1)[0].decode('latin-1')
    issues = []
    if bone_off + bone_count * BONE.size > len(raw):
        issues.append('bone tracks past end of file')
    if bone_off + bone_count * BONE.size > header_size:
        issues.append('bone tracks past headerSize')
    if hier:
        if hier >= len(raw):
            issues.append('hierarchy past end of file')
        elif hier + HIER_SIZE > header_size:
            issues.append(f'hierarchy extends {hier + HIER_SIZE - header_size} bytes past headerSize')
    bad_keys = 0
    for i in range(min(bone_count, max(0, (len(raw) - bone_off) // BONE.size))):
        r, p = BONE.unpack_from(raw, bone_off + i * BONE.size)[:2]
        if r > len(raw) or p > len(raw):
            bad_keys += 1
    if bad_keys:
        issues.append(f'{bad_keys} bone tracks with key offsets past end')
    return (f'{os.path.basename(path)}: {len(raw)} bytes, headerSize {header_size}, name {cstr(name)!r}, '
            f'base {cstr(base)!r}, bones {bone_count} @ {bone_off}, hierarchy @ {hier}'
            + (f'; {", ".join(issues)}' if issues else '; ok'))


def main():
    root, picks = sys.argv[1], [s.lower() for s in sys.argv[2:]]
    files = []
    for d, _, names in os.walk(root, followlinks=True):
        files += [os.path.join(d, n) for n in names if n.lower().endswith('.anim')]
    files.sort()
    chosen = [f for f in files if any(p in f.lower() for p in picks)] if picks else files[:10]
    lines = [describe(f) for f in chosen[:40]]
    bad = [describe(f) for f in files]
    bad = [l for l in bad if not l.endswith('; ok')]
    print('\n'.join(lines))
    print(f'{len(files)} .anim files; {len(bad)} with layout issues')
    print('\n'.join(bad[:20]))


if __name__ == '__main__':
    main()

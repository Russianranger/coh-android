"""Bounded offline inspection of the legacy Win32 City of Heroes .anim format.

Source: upstream/ouroboros/Common/seq/{animtrack.h,animtrack.c,
animtrackanimate.c,bones.h} and Utilities/GetAnimation2/src/outputanim.c
at the project's immutable source pin 0b75ade0c801735e10c5798f641948a45cc50488.
The file is a 32-bit little-endian native struct dump, with file-relative
offsets instead of pointers. It has no format magic or version. This module
does not run the engine, decode/interpolate compressed quaternions, or certify
runtime compatibility. Never cast these disk records to native ARM64 structs.
"""

from collections import Counter
import math
import struct

HEADER_BYTES = 596
BONE_BYTES = 20
BONE_ID_COUNT = 99
BONES_ON_DISK = 100
_BONE = struct.Struct('<IIHHHHbBH')
_ROTATIONS = {1: ('uncompressed', 16), 2: ('compressed_5_bytes', 5),
              4: ('compressed_8_bytes', 8), 128: ('compressed_nonlinear', 5)}
_POSITIONS = {8: ('uncompressed', 12), 16: ('compressed_6_bytes', 6)}


def animation_header(data):
    """Return header facts plus bounded structural/key-data checks.

    Historical arrays shorter than today's BONES_ON_DISK are reported, and
    only their reachable hierarchy is validated. Passing is evidence of the
    checks listed here, not proof of source or runtime compatibility.
    """
    result = {
        'format': 'coh_win32_animation',
        'validation_status': 'structural_checks_failed',
        'runtime_compatibility': 'unverified',
        'validation_scope': '32-bit disk layout, bounds, key flags/counts, '
                            'loader numeric predicates, reachable hierarchy',
        'file_bytes': len(data), 'errors': [], 'warnings': [],
    }
    errors, warnings = result['errors'], result['warnings']
    if len(data) < HEADER_BYTES:
        errors.append('truncated 596-byte Win32 animation header')
        return result

    def string_field(start, label):
        raw = data[start:start + 256]
        if b'\0' not in raw:
            errors.append(label + ' is not NUL-terminated in 256 bytes')
            return None
        try:
            value = raw.split(b'\0', 1)[0].decode('ascii')
        except UnicodeDecodeError:
            errors.append(label + ' contains non-ASCII bytes')
            return None
        normalized = value.replace('\\', '/')
        if not normalized or normalized.startswith('/') or ':' in normalized or any(
                p in ('', '.', '..') for p in normalized.split('/')):
            errors.append(label + ' is not a safe relative animation name')
        return value

    result['name'] = string_field(4, 'name')
    result['base_anim_name'] = string_field(260, 'baseAnimName')
    header_size, = struct.unpack_from('<i', data)
    hip, length, bone_offset, bone_count, rot_type, pos_type, hierarchy = (
        struct.unpack_from('<ffIiiiI', data, 516))
    result.update(header_size=header_size, bone_tracks_offset=bone_offset,
                  bone_track_count=bone_count, hierarchy_offset=hierarchy,
                  hierarchy_capacity=0, hierarchy_reachable_count=0,
                  max_hip_displacement=hip, length_frames=length,
                  rotation_compression_type=rot_type,
                  position_compression_type=pos_type)
    if not math.isfinite(hip) or not math.isfinite(length) or length < 0:
        errors.append('invalid animation length or hip displacement')
    if not HEADER_BYTES <= header_size <= len(data):
        errors.append('headerSize lies outside file')
    if not 1 <= bone_count <= BONE_ID_COUNT:
        errors.append('bone count outside supported BoneId range')
    if not HEADER_BYTES <= bone_offset <= header_size:
        errors.append('bone table offset lies outside header area')
    if bone_offset + bone_count * BONE_BYTES != header_size:
        errors.append('bone table does not end at headerSize')
    if errors:
        return result

    reachable = set()
    if hierarchy:
        hierarchy_bytes = bone_offset - hierarchy
        if hierarchy != HEADER_BYTES or hierarchy_bytes < 16 or (
                hierarchy_bytes - 4) % 12:
            errors.append('invalid skeleton hierarchy location/length')
        else:
            capacity = (hierarchy_bytes - 4) // 12
            result['hierarchy_capacity'] = capacity
            if capacity > BONES_ON_DISK:
                errors.append('hierarchy array exceeds current on-disk capacity')
            else:
                if capacity < BONES_ON_DISK:
                    warnings.append(
                        f'legacy hierarchy has {capacity} slots; current C struct '
                        'has 100. Reachable links are checked; higher index reads '
                        'and engine compatibility remain unverified')
                root, = struct.unpack_from('<i', data, hierarchy)
                stack = [root]
                if root == -1:
                    errors.append('skeleton hierarchy has no root')
                while stack:
                    index = stack.pop()
                    if index == -1:
                        continue
                    if not 0 <= index < min(capacity, BONE_ID_COUNT):
                        errors.append('reachable hierarchy link is out of bounds')
                        break
                    if index in reachable:
                        errors.append('hierarchy cycle or repeated reachable bone')
                        break
                    reachable.add(index)
                    child, next_bone, bone_id = struct.unpack_from(
                        '<iii', data, hierarchy + 4 + 12 * index)
                    if bone_id != index:
                        errors.append('reachable hierarchy bone ID differs from index')
                        break
                    stack.extend((child, next_bone))
                result['hierarchy_reachable_count'] = len(reachable)
    elif bone_offset != HEADER_BYTES:
        errors.append('unexpected space before bone table without hierarchy')

    rotations, positions = Counter(), Counter()
    rotation_keys = position_keys = 0
    bone_ids = set()
    for index in range(bone_count):
        ro, po, rf, pf, rc, pc, bone_id, flags, pad = _BONE.unpack_from(
            data, bone_offset + index * BONE_BYTES)
        prefix = f'bone[{index}]: '
        if not 0 <= bone_id < BONE_ID_COUNT or bone_id in bone_ids:
            errors.append(prefix + 'invalid or duplicate BoneId')
        bone_ids.add(bone_id)
        if 0 in (rf, pf, rc, pc) or rc > rf or pc > pf:
            errors.append(prefix + 'invalid full/frame key counts')
        if flags & 0x60:
            errors.append(prefix + 'delta-coded flags unsupported by inspected loader')
        rotation = _ROTATIONS.get(flags & 0x87)
        position = _POSITIONS.get(flags & 0x18)
        if rotation is None or position is None:
            errors.append(prefix + 'missing or ambiguous rotation/position encoding')
            continue
        if pad:
            warnings.append(prefix + 'nonzero explicit padding')
        rotation_name, rotation_size = rotation
        position_name, position_size = position
        rotations[rotation_name] += 1
        positions[position_name] += 1
        rotation_keys += rf
        position_keys += pf
        if not header_size <= ro <= len(data) - rf * rotation_size:
            errors.append(prefix + 'rotation key payload lies outside data area')
            continue
        if not header_size <= po <= len(data) - pf * position_size:
            errors.append(prefix + 'position key payload lies outside data area')
            continue
        if rotation_size == 5:
            # animDebugCheckBoneTrackOnLoad: top two bits must be zero.
            if any(data[ro + 5 * j] >= 64 for j in range(rf)):
                errors.append(prefix + '5-byte rotation top byte is >=64')
        elif rotation_size == 16:
            for j in range(rf):
                q = struct.unpack_from('<4f', data, ro + 16 * j)
                if not all(math.isfinite(v) for v in q) or not any(q):
                    errors.append(prefix + 'nonfinite or zero uncompressed quaternion')
                    break
        if position_size == 12:
            for j in range(pf):
                xyz = struct.unpack_from('<3f', data, po + 12 * j)
                # Match the existing loader predicate, including its one-sided bound.
                if not all(math.isfinite(v) and v < 2000000 for v in xyz):
                    errors.append(prefix + 'uncompressed position fails loader predicate')
                    break
    if hierarchy and not errors and not bone_ids.issubset(reachable):
        errors.append('local bone tracks are absent from reachable skeleton hierarchy')
    result.update(rotation_formats=dict(rotations), position_formats=dict(positions),
                  rotation_key_count=rotation_keys, position_key_count=position_keys)
    if not errors:
        result['validation_status'] = 'structural_checks_passed'
    return result


def animation_dependency_report(headers):
    """Check baseAnimName links between validated headers, case-insensitively.

    Self-references are valid terminal base skeletons only when a hierarchy is
    stored locally. Other cycles and missing references are reported separately.
    """
    by_name = {}
    duplicates, invalid = [], []
    norm = lambda s: s.replace('\\', '/').casefold()
    for header in headers:
        if header.get('validation_status') != 'structural_checks_passed':
            invalid.append(header.get('name'))
            continue
        name = norm(header['name'])
        if name in by_name:
            duplicates.append(name)
        by_name[name] = header
    missing, cycles, no_hierarchy, roots = set(), set(), set(), set()
    for origin in by_name:
        cursor, visited = origin, []
        while cursor in by_name:
            if cursor in visited:
                cycles.add(tuple(sorted(visited[visited.index(cursor):])))
                break
            visited.append(cursor)
            header = by_name[cursor]
            target = norm(header['base_anim_name'])
            if target == cursor:
                if header.get('hierarchy_offset'):
                    roots.add(cursor)
                else:
                    no_hierarchy.add(cursor)
                break
            cursor = target
        else:
            missing.add(cursor)
    return {
        'runtime_compatibility': 'unverified',
        'validated_track_count': len(by_name),
        'invalid_header_names': invalid,
        'duplicate_casefolded_names': sorted(set(duplicates)),
        'missing_base_names': sorted(missing),
        'nonterminal_cycles': [list(x) for x in sorted(cycles)],
        'terminal_bases_without_hierarchy': sorted(no_hierarchy),
        'terminal_base_count': len(roots),
        'terminal_base_names': sorted(roots),
    }

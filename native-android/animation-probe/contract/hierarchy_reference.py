#!/usr/bin/env python3
"""Independent CoH hierarchy/socket/skin arithmetic for Phase 7.

Local quaternion/position samples come from the retained original-function host
oracle, never the portable Android sampler. This module independently composes
the hierarchy and evaluates the source socket palette using Python binary64.
Serialized comparison data is float32. It does not execute Cg or capture the
original Windows client's runtime state.
"""
from __future__ import annotations

import math
import struct
import hashlib
import json


def finite(values, count):
    result = tuple(float(x) for x in values)
    if len(result) != count or not all(math.isfinite(x) for x in result):
        raise ValueError("wrong-sized or non-finite vector")
    return result


def f32(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("non-finite scalar")
    return struct.unpack("<f", struct.pack("<f", value))[0]


IDENTITY = ((1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0))
CHECKPOINT_FRAMES = (1.0, 1.5, 5.25, 12.5, 24.5, 25.0)


def local_matrix(rotation, position):
    """Source quatToMat columns transposed into three affine upload rows.

    Preserve raw base quaternions; no extra normalization is applied here.
    In this source convention a positive Z quaternion rotates X toward -Y.
    """
    x, y, z, w = finite(rotation, 4)
    px, py, pz = finite(position, 3)
    tx, ty, tz = 2.0*x, 2.0*y, 2.0*z
    xx, xy, xz = tx*x, ty*x, tz*x
    yy, yz, zz = ty*y, tz*y, tz*z
    wx, wy, wz = tx*w, ty*w, tz*w
    return ((1.0-(yy+zz), xy+wz, xz-wy, px),
            (xy-wz, 1.0-(xx+zz), yz+wx, py),
            (xz+wy, yz-wx, 1.0-(xx+yy), pz))


def compose(parent, local):
    """Affine parent * local; rows act on column position vectors."""
    parent = tuple(finite(row, 4) for row in parent)
    local = tuple(finite(row, 4) for row in local)
    if len(parent) != 3 or len(local) != 3:
        raise ValueError("affine matrix needs three rows")
    return tuple(tuple(sum(parent[r][k] * local[k][c] for k in range(3))
                       + (parent[r][3] if c == 3 else 0.0)
                       for c in range(4)) for r in range(3))


def transform(matrix, point, position=True):
    point = finite(point, 3)
    return tuple(sum(row[k]*point[k] for k in range(3))
                 + (row[3] if position else 0.0) for row in matrix)


def with_translation(matrix, translation):
    translation = finite(translation, 3)
    return tuple((*matrix[i][:3], translation[i]) for i in range(3))


def _locals(items):
    result = {}
    for item in items:
        bone = int(item["id"])
        if bone in result:
            raise ValueError("duplicate local bone id")
        result[bone] = {"rotation": finite(item["rotation"], 4),
                        "position": finite(item["position"], 3)}
    return result


def sample_hierarchy(hierarchy, base_local, local, palette_ids=(9, 5, 7),
                     socket_id=72, root_transform=IDENTITY):
    """Independent local -> world -> btt/bpt -> socket palette evaluation.

    `local` is already adjusted by source animDelta and base fallback rules.
    `base_local` contains first keys from the sequencer's base skeleton.
    All hierarchy records are validated, including bones outside the mesh's
    seven-bone ancestor closure. Bone scale and actor morphing are unit/zero.
    """
    parents = {}
    for item in hierarchy:
        bone, parent = int(item["id"]), int(item["parent"])
        if bone in parents or bone < 0 or parent == bone:
            raise ValueError("invalid or duplicate hierarchy bone")
        parents[bone] = parent
    base, sampled = _locals(base_local), _locals(local)
    if set(base) != set(parents) or set(sampled) != set(parents):
        raise ValueError("local channels must cover the entire base hierarchy")
    palette_ids = tuple(int(i) for i in palette_ids)
    if (not palette_ids or len(palette_ids) > 15
            or len(set(palette_ids)) != len(palette_ids)
            or socket_id not in parents or any(i not in parents for i in palette_ids)):
        raise ValueError("invalid palette/socket mapping")
    for parent in parents.values():
        if parent != -1 and parent not in parents:
            raise ValueError("unreachable hierarchy parent")
    world, btt, active = {}, {}, set()

    def visit(bone):
        if bone in world:
            return
        if bone in active:
            raise ValueError("hierarchy cycle")
        active.add(bone)
        parent = parents[bone]
        if parent == -1:
            parent_world = root_transform
            # The outer sequencer node has no valid bone id. Its root btt slots
            # start zero; animExtractBoneTranslations also explicitly zeros0.
            btt[bone] = (0.0, 0.0, 0.0)
        else:
            visit(parent)
            parent_world = world[parent]
            btt[bone] = ((0.0, 0.0, 0.0) if bone == 0 else
                         tuple(btt[parent][i] + base[bone]["position"][i]
                               for i in range(3)))
        world[bone] = compose(parent_world,
                              local_matrix(sampled[bone]["rotation"],
                                           sampled[bone]["position"]))
        active.remove(bone)

    for bone in parents:
        visit(bone)
    bpt = {bone: with_translation(world[bone],
                                 transform(world[bone], tuple(-x for x in btt[bone])))
           for bone in parents}
    palette = [with_translation(bpt[bone], transform(bpt[bone], btt[socket_id]))
               for bone in palette_ids]
    # An independently rearranged identity catches accidental double/missing
    # inverse-bind or socket translation during generator changes.
    for bone, matrix in zip(palette_ids, palette):
        direct = transform(world[bone], tuple(btt[socket_id][i]-btt[bone][i]
                                              for i in range(3)))
        if max(abs(matrix[r][3]-direct[r]) for r in range(3)) > 1e-10:
            raise AssertionError("socket palette identity failed")
    return {"bone_ids": list(parents), "local": sampled, "btt": btt,
            "world": world, "bpt": bpt, "palette": palette,
            "palette_ids": list(palette_ids), "socket_id": socket_id,
            "socket_world": world[socket_id]}


def mesh_vertices(raw):
    """Read already-qualified COHMESH1 records without the native parser."""
    if len(raw) < 64:
        raise ValueError("mesh header truncated")
    header = struct.unpack_from("<8s14I", raw)
    magic, version, size, count, indices, bones, stride, vo, io, bo, total, *zero = header
    if (magic != b"COHMESH1" or version != 1 or size != 64 or stride != 48
            or not 0 < count <= 100000 or not 0 < bones <= 15 or any(zero)
            or vo != 64 or io != vo+count*48 or bo != io+indices*4
            or total != bo+bones*4 or total != len(raw)):
        raise ValueError("mesh envelope differs")
    records = [struct.unpack_from("<10f2I", raw, vo+i*48) for i in range(count)]
    ids = struct.unpack_from("<"+"I"*bones, raw, bo)
    for record in records:
        finite(record[:10], 10)
        if any(i >= bones for i in record[10:]) or not 0.0 <= record[9] <= 1.0:
            raise ValueError("invalid skin slot/weight")
    return records, list(ids)


def skin_vertices(vertices, palette):
    """Source GPU lerp then normalize; excludes fixed CPU deform's normal rule."""
    output = []
    for record in vertices:
        matrices = [palette[i] for i in record[10:12]]
        p = [transform(m, record[:3]) for m in matrices]
        n = [transform(m, record[3:6], False) for m in matrices]
        weight_y = record[9]
        position = tuple(a+(b-a)*weight_y for a, b in zip(*p))
        normal = tuple(a+(b-a)*weight_y for a, b in zip(*n))
        length = math.sqrt(sum(v*v for v in normal))
        if length <= 1e-12:
            raise ValueError("collapsed blended normal")
        output.append((*position, *(v/length for v in normal)))
    return output


def cycle_frame(frame, timestep, first=1.0, last=25.0, scale=1.0):
    """Source seqCycleFrame rule, deliberately not modulo/fmod looping."""
    frame, timestep, first, last, scale = finite((frame, timestep, first, last, scale), 5)
    if first >= last or frame < first or frame > last or timestep < 0 or scale < 0:
        raise ValueError("invalid bounded clock input")
    advanced = f32(f32(frame)+f32(f32(scale)*f32(timestep)))
    if advanced > last:
        advanced = f32(advanced-f32(last-first))
        if advanced > last:
            advanced = f32(first)
    return advanced


def _packed(values):
    values = tuple(f32(v) for v in values)
    return struct.pack("<"+"f"*len(values), *values)


def _matrix_values(matrix):
    return (value for row in matrix for value in row)


def generate(original_samples, mesh_raw):
    """Build the frozen COHAGL01 native reference and its diagnostic metadata.

    original_samples schema:
      hierarchy: [{id, parent}, ...] (all 60 reachable base nodes)
      base_local: [{id, rotation:[x,y,z,w], position:[x,y,z]}, ...]
      samples: [{frame, local:[{id, rotation, position}, ...]}, ...]
    Samples are original-host local channels after animDelta/base fallback.
    Neither the portable native rig parser nor its sampler is executed here.
    """
    self_check()
    if original_samples.get("socket_id") != 72 or original_samples.get("palette_ids") != [9, 5, 7]:
        raise ValueError("original local oracle must retain the source socket/palette identities")
    clock = original_samples["clock"]
    if (clock.get("first_frame"), clock.get("last_frame"),
            clock.get("ticks_per_second"), clock.get("effective_rate")) != (1, 25, 30, 1):
        raise ValueError("original local oracle clock differs from bounded source contract")
    hierarchy = sorted(original_samples["hierarchy"], key=lambda v: int(v["id"]))
    bone_ids = [int(v["id"]) for v in hierarchy]
    if len(bone_ids) != 60 or len(set(bone_ids)) != 60:
        raise ValueError("fixture must retain all 60 base hierarchy nodes")
    wanted = set(bone_ids)
    base_local = [v for v in original_samples["base_local"] if int(v["id"]) in wanted]
    vertices, palette_ids = mesh_vertices(mesh_raw)
    if len(vertices) != 116 or palette_ids != [9, 5, 7]:
        raise ValueError("reference must use the pinned real sleeves mesh")
    samples = {f32(v["frame"]): v for v in original_samples["samples"]}
    if not all(frame in samples for frame in CHECKPOINT_FRAMES):
        raise ValueError("original-host oracle lacks required checkpoint")
    shared = struct.pack("<60I", *bone_ids)
    shared += struct.pack("<60i", *(int(v["parent"]) for v in hierarchy))
    shared += struct.pack("<3I", *palette_ids)
    bodies, metadata, all_geometry, shared_btt = [], [], [], None
    for index, frame in enumerate(CHECKPOINT_FRAMES):
        local = [v for v in samples[frame]["local"] if int(v["id"]) in wanted]
        stage = sample_hierarchy(hierarchy, base_local, local, palette_ids, 72)
        btt = _packed(v for bone in bone_ids for v in stage["btt"][bone])
        if shared_btt is None:
            shared_btt = btt
        elif btt != shared_btt:
            raise AssertionError("base btt changed during reference generation")
        # Float32 palettes are what the renderer actually uploads. Evaluate
        # hardware skin from those values so the golden's input is unambiguous.
        palette_raw = _packed(v for matrix in stage["palette"] for v in _matrix_values(matrix))
        palette_values = struct.unpack("<36f", palette_raw)
        serialized_palette = [tuple(tuple(palette_values[b*12+r*4:b*12+r*4+4])
                                    for r in range(3)) for b in range(3)]
        geometry = skin_vertices(vertices, serialized_palette)
        all_geometry.extend(geometry)
        local_raw = _packed(v for bone in bone_ids
                            for channel in ("rotation", "position")
                            for v in stage["local"][bone][channel])
        world_raw = _packed(v for bone in bone_ids for v in _matrix_values(stage["world"][bone]))
        bpt_raw = _packed(v for bone in bone_ids for v in _matrix_values(stage["bpt"][bone]))
        geometry_raw = _packed(v for vertex in geometry for v in vertex)
        body = _packed([frame])+local_raw+world_raw+bpt_raw+palette_raw+geometry_raw
        if len(body) != 10372:
            raise AssertionError("frozen reference case stride changed")
        bodies.append(body)
        metadata.append({"index": index, "frame": frame,
                         "source_locals_sha256": hashlib.sha256(local_raw).hexdigest(),
                         "palette_sha256": hashlib.sha256(palette_raw).hexdigest(),
                         "skin_geometry_sha256": hashlib.sha256(geometry_raw).hexdigest(),
                         "socket_world_rows": stage["socket_world"],
                         "skin_bounds": {"minimum": [min(v[c] for v in geometry) for c in range(3)],
                                         "maximum": [max(v[c] for v in geometry) for c in range(3)]}})
    shared += shared_btt
    # All offsets are absolute except the five per-case stage offsets.
    header = bytearray(128)
    struct.pack_into("<8s", header, 0, b"COHAGL01")
    fields = {8:1, 12:128, 16:6, 20:60, 24:3, 28:116,
              32:128, 36:368, 40:608, 44:620, 48:1340,
              52:10372, 56:63572, 60:72, 64:0,
              68:4, 72:1684, 76:4564, 80:7444, 84:7588}
    for offset, value in fields.items():
        struct.pack_into("<I", header, offset, value)
    struct.pack_into("<3f", header, 88, 30.0, 1.0, 25.0)
    raw = bytes(header)+shared+b"".join(bodies)
    if len(raw) != 63572:
        raise AssertionError("frozen reference envelope changed")
    result = {"format": "COHAGL01", "header_bytes": 128,
              "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
              "sample_count": 6, "bone_count": 60, "palette_count": 3,
              "vertex_count": 116, "bone_ids": bone_ids,
              "parents": [int(v["parent"]) for v in hierarchy],
              "palette_global_ids": palette_ids, "socket_global_id": 72,
              "checkpoint_frames": list(CHECKPOINT_FRAMES), "cases": metadata,
              "global_skin_bounds": {
                  "minimum": [min(v[c] for v in all_geometry) for c in range(3)],
                  "maximum": [max(v[c] for v in all_geometry) for c in range(3)]},
              "scope": "unit bone/actor scale, identity outer transform, one real clip",
              "local_oracle": "retained original-function host sampler",
              "original_local_rig_sha256": original_samples.get("rig_sha256"),
              "original_local_source_commit": original_samples.get("source_commit"),
              "original_local_semantic_json_sha256": hashlib.sha256(
                  json.dumps(original_samples, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest(),
              "hierarchy_oracle": "independent Python binary64 arithmetic",
              "palette_skin_inputs": "float32 serialization of independent palette",
              "portable_sampler_executed_by_generator": False,
              "original_runtime_capture": False, "original_cg_execution": False}
    return raw, result


def self_check():
    """Hand-derived nonidentity cases detect sign/order/offset mistakes."""
    half = math.sqrt(0.5)
    r = local_matrix((0, 0, half, half), (1, 2, 3))
    assert max(abs(a-b) for a, b in zip(transform(r, (1, 0, 0)), (1, 1, 3))) < 1e-12
    hierarchy = [{"id": 0, "parent": -1}, {"id": 7, "parent": 0},
                 {"id": 72, "parent": 0}]
    base = [{"id": i, "rotation": [0, 0, 0, 1], "position": p}
            for i, p in ((0, [10, 0, 0]), (7, [2, 0, 0]), (72, [0, 3, 0]))]
    sampled = [{"id": 0, "rotation": [0, 0, half, half], "position": [1, 2, 3]},
               base[1], base[2]]
    stage = sample_hierarchy(hierarchy, base, sampled, [7], 72)
    assert stage["btt"][0] == (0, 0, 0)
    assert stage["btt"][7] == (2, 0, 0)
    assert max(abs(a-b) for a, b in zip(stage["world"][7][0], (0, 1, 0, 1))) < 1e-12
    assert max(abs(stage["palette"][0][i][3]-v)
               for i, v in enumerate((4, 2, 3))) < 1e-12
    # Raw base quaternion preservation matters; adding normalization here is a
    # source behavior change even when most base tracks happen to be near-unit.
    assert local_matrix((0, 0, .5, .5), (0, 0, 0))[0][0] == .5
    vertex = (1, 0, 0, 1, 0, 0, 0, 0, .5, .5, 0, 1)
    skinned = skin_vertices([vertex], [IDENTITY, r])[0]
    assert max(abs(a-b) for a, b in zip(skinned[:3], (1, .5, 1.5))) < 1e-12
    assert abs(skinned[3]-half) < 1e-12 and abs(skinned[4]+half) < 1e-12
    assert cycle_frame(25, 0) == 25
    assert cycle_frame(25, .25) == 1.25
    assert cycle_frame(1, 49) == 1  # one subtraction, then source reset
    try:
        sample_hierarchy([{"id": 0, "parent": 7}, {"id": 7, "parent": 0}],
                         base[:2], sampled[:2], [7], 0)
    except ValueError:
        pass
    else:
        raise AssertionError("cyclic hierarchy accepted")
    return {"status": "passed", "kind": "independent hierarchy/socket boundaries",
            "portable_sampler_executed": False, "original_runtime_capture": False}


if __name__ == "__main__":
    print(json.dumps(self_check(), indent=2))

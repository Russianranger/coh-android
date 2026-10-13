#!/usr/bin/env python3
"""Independent complete-character hierarchy, socket and skin reference.

Inputs are real canonical meshes and local rows produced by unchanged original
actor/animation scalar functions. This module never invokes the Android/native
character sampler. Python binary64 composes the hierarchy; emitted matrices and
geometry are float32. No original Win32 rendering or Cg execution is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

PREVIOUS = Path(__file__).resolve().parents[2] / "animation-probe/contract/hierarchy_reference.py"
_spec = importlib.util.spec_from_file_location("coh_phase7_reference", PREVIOUS)
_phase7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_phase7)
finite = _phase7.finite
f32 = _phase7.f32
compose = _phase7.compose
transform = _phase7.transform
with_translation = _phase7.with_translation
mesh_vertices = _phase7.mesh_vertices
skin_vertices = _phase7.skin_vertices
IDENTITY = _phase7.IDENTITY
FRAMES = _phase7.CHECKPOINT_FRAMES


def matrix_rows(value):
    """Accept explicit rows or twelve scalar source upload rows."""
    if len(value) == 12 and not isinstance(value[0], (list, tuple)):
        value = [value[r * 4:r * 4 + 4] for r in range(3)]
    if len(value) != 3:
        raise ValueError("affine matrix must have three rows")
    return tuple(finite(row, 4) for row in value)


def node_scaled(world, scale):
    """Original node->mat * diag(node->bonescale), without child propagation."""
    scale = finite(scale, 3)
    if any(v <= 0 or v > 10 for v in scale):
        raise ValueError("bone scale is outside the bounded source contract")
    return tuple(tuple(row[c] * scale[c] if c < 3 else row[c]
                       for c in range(4)) for row in matrix_rows(world))


def sample_hierarchy(hierarchy, base_local, local, bone_scales, actor_root):
    """Compose original local rows; keep render bone scale out of traversal."""
    parents = {}
    for item in hierarchy:
        bone, parent = int(item["id"]), int(item["parent"])
        if bone in parents or not 0 <= bone < 99 or parent == bone:
            raise ValueError("duplicate, cyclic or invalid bone")
        parents[bone] = parent
    wanted = set(parents)
    base = {int(item["id"]): item for item in base_local}
    sampled = {int(item["id"]): item for item in local}
    scales = {int(item["id"]): finite(item["scale"], 3)
              for item in bone_scales}
    if (len(base) != len(base_local) or len(sampled) != len(local)
            or len(scales) != len(bone_scales)
            or set(base) != wanted or set(sampled) != wanted
            or not wanted.issubset(scales)):
        raise ValueError("local/base/scale records do not uniquely cover hierarchy")
    if any(parent != -1 and parent not in wanted for parent in parents.values()):
        raise ValueError("hierarchy references an absent parent")
    root = matrix_rows(actor_root)
    world, btt, active = {}, {}, set()

    def visit(bone):
        if bone in world:
            return
        if bone in active:
            raise ValueError("hierarchy cycle")
        active.add(bone)
        parent = parents[bone]
        if parent == -1:
            parent_world = root
            btt[bone] = (0.0, 0.0, 0.0)
        else:
            visit(parent)
            parent_world = world[parent]
            position = finite(base[bone]["position"], 3)
            btt[bone] = ((0.0, 0.0, 0.0) if bone == 0 else
                         tuple(btt[parent][c] + position[c] for c in range(3)))
        # The actor oracle has already applied original pre/post limb scaling
        # to the local rows and has preserved original morph-before-delta order.
        world[bone] = compose(parent_world, matrix_rows(sampled[bone]["local_rows"]))
        active.remove(bone)

    for bone in parents:
        visit(bone)
    scaled = {bone: node_scaled(world[bone], scales[bone]) for bone in parents}
    bpt = {bone: with_translation(scaled[bone],
                                  transform(scaled[bone], tuple(-v for v in btt[bone])))
           for bone in parents}
    return {"parents": parents, "local": sampled, "btt": btt,
            "world": world, "scaled_world": scaled, "bpt": bpt,
            "bone_scales": scales, "actor_root": root}


def socket_palette(stage, socket, palette_ids):
    if socket not in stage["parents"] or any(b not in stage["parents"] for b in palette_ids):
        raise ValueError("part socket/palette is absent from the actual hierarchy")
    # Preserve the source's two separate point transforms: inverse bind, then
    # source socket offset. Do not simplify their native float32 evaluation.
    return [with_translation(stage["bpt"][bone],
                              transform(stage["bpt"][bone], stage["btt"][socket]))
            for bone in palette_ids]


def packed(values):
    values = tuple(f32(v) for v in values)
    return struct.pack("<" + "f" * len(values), *values)


def matrix_values(matrix):
    return [value for row in matrix_rows(matrix) for value in row]


def serialized_palette(palette):
    raw = packed(v for matrix in palette for v in matrix_values(matrix))
    values = struct.unpack("<" + "f" * (len(raw) // 4), raw)
    return raw, [matrix_rows(values[i * 12:i * 12 + 12])
                 for i in range(len(palette))]


def generate(original_samples, mesh_raws, bindings=None):
    """Return frozen COHCHR01 bytes and complete comparison metadata."""
    self_check()
    if bindings is None:
        bindings = json.loads(Path(__file__).with_name("binding.json").read_text())
    parts = bindings["parts"]
    if len(parts) != 11 or len(mesh_raws) != len(parts):
        raise ValueError("all eleven original visible draws must be present")
    hierarchy = sorted(original_samples["hierarchy"], key=lambda v: int(v["id"]))
    ids = [int(v["id"]) for v in hierarchy]
    if len(ids) != 60 or len(set(ids)) != 60:
        raise ValueError("reference must validate all sixty actual hierarchy nodes")
    wanted = set(ids)
    base = [v for v in original_samples["base_local"] if int(v["id"]) in wanted]
    morph = original_samples["morphology"]
    scales = morph["bone_scales"]
    root = morph["actor_root_rows"]
    cases = {f32(item["frame"]): item for item in original_samples["samples"]}
    if not all(frame in cases for frame in FRAMES):
        raise ValueError("original actor oracle lacks a required checkpoint")
    meshes = []
    for part, raw in zip(parts, mesh_raws):
        vertices, palette_ids = mesh_vertices(raw)
        if (palette_ids != part["palette_global_ids"]
                or len(vertices) != part["vertex_count"]):
            raise ValueError("real part palette/vertex identity differs from binding")
        meshes.append((vertices, palette_ids))
    if sum(len(v) for v, _ in meshes) != 2626 or sum(len(p) for _, p in meshes) != 45:
        raise ValueError("frozen whole-character counts changed")
    draw_records, vertex_first, palette_first = [], 0, 0
    for index, (part, (vertices, palette_ids)) in enumerate(zip(parts, meshes)):
        draw_records.append({"index": index, "part": part["part"],
                             "socket_global_id": part["socket_global_id"],
                             "palette_global_ids": palette_ids,
                             "vertex_count": len(vertices), "vertex_first": vertex_first,
                             "palette_first": palette_first,
                             "palette_case_offset": 7444 + palette_first * 48,
                             "geometry_case_offset": 9604 + vertex_first * 24})
        vertex_first += len(vertices)
        palette_first += len(palette_ids)
    bodies, case_metadata, btt_raw, scales_raw, all_geometry = [], [], None, None, []
    for index, frame in enumerate(FRAMES):
        local = [v for v in cases[frame]["local"] if int(v["id"]) in wanted]
        stage = sample_hierarchy(hierarchy, base, local, scales, root)
        current_btt = packed(v for bone in ids for v in stage["btt"][bone])
        current_scales = packed(v for bone in ids for v in stage["bone_scales"][bone])
        if btt_raw is None:
            btt_raw, scales_raw = current_btt, current_scales
        elif btt_raw != current_btt or scales_raw != current_scales:
            raise AssertionError("fixed source bind/morph data changed between samples")
        local_raw = packed(v for bone in ids for name in ("rotation", "position")
                           for v in finite(stage["local"][bone][name], 4 if name == "rotation" else 3))
        world_raw = packed(v for bone in ids for v in matrix_values(stage["world"][bone]))
        scaled_raw = packed(v for bone in ids for v in matrix_values(stage["scaled_world"][bone]))
        palette_chunks, geometry_chunks, draw_bounds = [], [], []
        for draw, (vertices, palette_ids) in zip(draw_records, meshes):
            palette = socket_palette(stage, draw["socket_global_id"], palette_ids)
            palette_raw, upload = serialized_palette(palette)
            geometry = skin_vertices(vertices, upload)
            all_geometry.extend(geometry)
            palette_chunks.append(palette_raw)
            geometry_chunks.append(packed(v for vertex in geometry for v in vertex))
            draw_bounds.append({"part": draw["part"], "palette_sha256": hashlib.sha256(palette_raw).hexdigest(),
                                "minimum": [min(v[c] for v in geometry) for c in range(3)],
                                "maximum": [max(v[c] for v in geometry) for c in range(3)]})
        body = packed([frame]) + local_raw + world_raw + scaled_raw + b"".join(palette_chunks) + b"".join(geometry_chunks)
        if len(body) != 72628:
            raise AssertionError("frozen character reference case stride changed")
        bodies.append(body)
        case_metadata.append({"index": index, "frame": frame, "draws": draw_bounds,
                              "local_sha256": hashlib.sha256(local_raw).hexdigest(),
                              "world_sha256": hashlib.sha256(world_raw).hexdigest(),
                              "scaled_world_sha256": hashlib.sha256(scaled_raw).hexdigest()})
    shared = struct.pack("<60I", *ids)
    shared += struct.pack("<60i", *(int(v["parent"]) for v in hierarchy))
    shared += btt_raw + scales_raw + packed(matrix_values(root))
    for draw in draw_records:
        shared += struct.pack("<8I", draw["socket_global_id"], len(draw["palette_global_ids"]),
                              draw["vertex_count"], draw["vertex_first"], draw["palette_first"],
                              draw["palette_case_offset"], draw["geometry_case_offset"], 0)
    if len(shared) != 2320:
        raise AssertionError("frozen character shared envelope changed")
    header = bytearray(128)
    header[:8] = b"COHCHR01"
    fields = {8: 1, 12: 128, 16: 6, 20: 60, 24: 11, 28: 2626,
              32: 128, 36: 368, 40: 608, 44: 1328, 48: 2048,
              52: 2096, 56: 2448, 60: 72628, 64: 438216,
              68: 4, 72: 1684, 76: 4564, 80: 7444, 84: 9604,
              88: 45, 92: 32}
    for offset, value in fields.items():
        struct.pack_into("<I", header, offset, value)
    struct.pack_into("<3f", header, 96, 30.0, 1.0, 25.0)
    raw = bytes(header) + shared + b"".join(bodies)
    if len(raw) != 438216:
        raise AssertionError("frozen whole-character reference size changed")
    metadata = {"format": "COHCHR01", "version": 1, "header_bytes": 128,
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "sample_count": 6, "bone_count": 60, "draw_count": 11,
                "vertex_count": 2626, "palette_matrix_count": 45,
                "frame_samples": list(FRAMES), "bone_ids": ids,
                "offsets": {"ids": 128, "parents": 368, "btt": 608,
                            "bone_scales": 1328, "actor_root": 2048, "draws": 2096,
                            "cases": 2448, "case_stride": 72628, "local": 4,
                            "world": 1684, "scaled_world": 4564, "palettes": 7444,
                            "geometry": 9604, "draw_stride": 32},
                "draws": draw_records, "cases": case_metadata,
                "actor_bounds": {"minimum": [min(v[c] for v in all_geometry) for c in range(3)],
                                 "maximum": [max(v[c] for v in all_geometry) for c in range(3)]},
                "local_sample_oracle": "unchanged original scalar functions with original source morph ordering",
                "hierarchy_oracle": "independent Python binary64 composition; float32 upload matrices",
                "portable_native_sampler_called_by_generator": False,
                "node_bone_scale_propagates_to_children": False,
                "original_windows_runtime_capture": False, "original_cg_execution": False}
    return raw, metadata


def self_check():
    """Analytic checks target nonpropagating render scale and source sockets."""
    hierarchy = [{"id": 0, "parent": -1}, {"id": 1, "parent": 0}, {"id": 2, "parent": 1}]
    base = [{"id": i, "position": [float(i), 0, 0]} for i in range(3)]
    local = [{"id": i, "rotation": [0, 0, 0, 1], "position": [float(i), 0, 0],
              "local_rows": ((1, 0, 0, float(i)), (0, 1, 0, 0), (0, 0, 1, 0))}
             for i in range(3)]
    scales = [{"id": 0, "scale": [2, 3, 4]}, {"id": 1, "scale": [5, 6, 7]},
              {"id": 2, "scale": [1, 1, 1]}]
    stage = sample_hierarchy(hierarchy, base, local, scales, IDENTITY)
    if stage["world"][2][0][3] != 3 or stage["world"][2][0][0] != 1:
        raise AssertionError("render bone scale leaked into a child hierarchy")
    palette = socket_palette(stage, 2, [1])[0]
    # world1.translation=1, scaleX=5, btt1=1, socketbtt2=3:
    # inverse bind gives 1-5=-4, then socket adds 15 =>11.
    if palette[0][0] != 5 or palette[0][3] != 11:
        raise AssertionError("inverse-bind/socket transform order differs")
    if abs(math.sqrt(sum(v * v for v in skin_vertices([(1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0)], [palette])[0][3:])) - 1) > 1e-12:
        raise AssertionError("skinned normal was not normalized")
    try:
        sample_hierarchy([{"id": 0, "parent": 1}, {"id": 1, "parent": 0}],
                         base[:2], local[:2], scales[:2], IDENTITY)
    except ValueError:
        pass
    else:
        raise AssertionError("cyclic hierarchy accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-samples", type=Path, required=True)
    parser.add_argument("--meshes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    raw, metadata = generate(json.loads(args.original_samples.read_text()),
                             [(args.meshes / f"mesh{i}.bin").read_bytes() for i in range(11)])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"generated": True, "bytes": len(raw), "sha256": metadata["sha256"],
                      "draws": 11, "vertices": 2626, "cases": 6}))


if __name__ == "__main__":
    main()

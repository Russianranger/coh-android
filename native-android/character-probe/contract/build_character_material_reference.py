#!/usr/bin/env python3
"""Independent scalar references for every resolved Phase 8 costume draw.

COHCMAT8 has a 64-byte <8s14I> header, six cases per scene part, and a
128-byte <26f6I> record followed by 64*64*4 expected RGBA8 pixels. The first
26 floats have the accepted COHMAT6 order. uint32 fields are flags, part
index, case index, and three zero reserves. Shader source is not executed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "coh_accepted_scalar_material", ROOT / "material-probe/contract/material_reference.py")
_scalar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scalar)
f32, fragment, framebuffer = _scalar.f32, _scalar.fragment, _scalar.framebuffer

MAGIC = b"COHCMAT8"
HEADER = struct.Struct("<8s14I")
RECORD = struct.Struct("<26f6I")
WIDTH = HEIGHT = 64
PIXEL_BYTES = WIDTH * HEIGHT * 4
CASE_STRIDE = RECORD.size + PIXEL_BYTES
SWATCH_RGBA8 = (51, 153, 230, 128)
CASES_PER_PART = 6
VECTOR_KEYS = ("const0", "const1", "vertex_color", "fog_params", "fog_color", "clear")


def _require(value, message):
    if not value:
        raise ValueError(message)


def _color(values):
    _require(len(values) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in values),
             "costume color requires three source RGB bytes")
    # rt_bonedmodel setupCustomColors performs scaleVec3(byte,1.f/255.f).
    reciprocal = f32(1.0 / 255.0)
    return [f32(f32(v) * reciprocal) for v in values]


def _texture(texture):
    width, height = texture["width"], texture["height"]
    raw = texture["rgba"]
    _require(isinstance(width, int) and isinstance(height, int)
             and 0 < width <= 1024 and 0 < height <= 1024
             and isinstance(raw, bytes) and len(raw) == width * height * 4,
             "texture dimensions or RGBA byte span differ")
    return raw, width, height


def _sample(texture, x, y):
    raw, width, height = texture
    tx = min(width - 1, ((2 * x + 1) * width) // (2 * WIDTH))
    ty = min(height - 1, ((2 * y + 1) * height) // (2 * HEIGHT))
    offset = (ty * width + tx) * 4
    return tuple(value / 255.0 for value in raw[offset:offset + 4])


def cases(part, index):
    color1 = part.get("color1", part.get("effective_colors_rgb", [None, None])[0])
    color2 = part.get("color2", part.get("effective_colors_rgb", [None, None])[1])
    alpha = part.get("draw_alpha", 255)
    _require(isinstance(alpha, int) and 0 <= alpha <= 255, "draw alpha is not a source byte")
    defaults = {"const0": _color(color1) + [f32(alpha * f32(1 / 255.0))],
                "const1": _color(color2) + [1.0],
                "vertex_color": [.25, .25, .25, 1],
                "fog_params": [0, 0, 20, .1],
                "fog_color": [32 / 255, 64 / 255, 96 / 255, 1],
                "clear": [32 / 255, 96 / 255, 160 / 255, 128 / 255],
                "fog_coord": 0, "alpha_ref": 0, "flags": 0}
    overrides = [
        ("authored_costume_colors", {}),
        ("authored_half_fade_source_over", {"fade": .5, "flags": 1}),
        ("authored_mid_fog", {"fog_coord": 15}),
        ("authored_strict_alpha_ref_one_discard", {"alpha_ref": 1, "flags": 1}),
        ("authored_colors_controlled_dual_rgb_alpha", {"flags": 2}),
        ("authored_colors_controlled_dual_ref_point6_discard", {"flags": 3, "alpha_ref": .6}),
    ]
    result = []
    for case_index, (name, override) in enumerate(overrides):
        case = dict(defaults, **{k: v for k, v in override.items() if k != "fade"})
        for key in VECTOR_KEYS:
            case[key] = [f32(value) for value in case[key]]
        if "fade" in override:
            case["const0"][3] = f32(override["fade"])
        case["fog_coord"], case["alpha_ref"] = f32(case["fog_coord"]), f32(case["alpha_ref"])
        case.update(name=name, part_index=index, case_index=case_index,
                    part=part.get("part", part.get("name", str(index))),
                    dual_texture_mode="controlled_swatch" if case["flags"] & 2 else "actual_costume_asset")
        result.append(case)
    return result


def record(case):
    return RECORD.pack(*(value for key in VECTOR_KEYS for value in case[key]),
                       case["fog_coord"], case["alpha_ref"], case["flags"],
                       case["part_index"], case["case_index"], 0, 0, 0)


def prepare(parts, textures):
    """parts: base_texture/dual_texture indices + source RGB byte colors.

    Each texture is {rgba: bytes, width: int, height: int, name: str}. Return
    (canonical binary, evidence cases). A separate case is kept for both boots
    so the runtime gate covers every draw binding, including shared materials.
    """
    _require(0 < len(parts) <= 16 and 0 < len(textures) <= 32, "scene material cardinality exceeds bounds")
    decoded = [_texture(texture) for texture in textures]
    count = len(parts) * CASES_PER_PART
    total = HEADER.size + count * CASE_STRIDE
    output = bytearray(HEADER.pack(MAGIC, 1, HEADER.size, WIDTH, HEIGHT, count,
                                  RECORD.size, len(parts), PIXEL_BYTES, CASE_STRIDE,
                                  HEADER.size, total, 0, 0, 0))
    evidence = []
    for part_index, part in enumerate(parts):
        b, d = part["base_texture"], part["dual_texture"]
        _require(isinstance(b, int) and isinstance(d, int)
                 and 0 <= b < len(decoded) and 0 <= d < len(decoded),
                 "scene material references absent texture")
        for case in cases(part, part_index):
            output.extend(record(case))
            pixels, discarded = bytearray(), 0
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    dual = (tuple(value / 255.0 for value in SWATCH_RGBA8)
                            if case["flags"] & 2 else _sample(decoded[d], x, y))
                    rgba = fragment(_sample(decoded[b], x, y), dual, case["const0"], case["const1"],
                                    case["vertex_color"], case["fog_params"], case["fog_color"],
                                    case["fog_coord"], case["alpha_ref"])
                    discarded += rgba is None
                    pixels.extend(framebuffer(rgba, case["clear"], bool(case["flags"] & 1)))
            _require(len(pixels) == PIXEL_BYTES, "reference pixel size differs")
            output.extend(pixels)
            evidence.append(dict(case, base_texture_index=b, dual_texture_index=d,
                                 base_texture=textures[b].get("name", str(b)),
                                 dual_texture=textures[d].get("name", str(d)),
                                 expected_rgba_sha256=hashlib.sha256(pixels).hexdigest(),
                                 discarded_pixels=discarded, passed_pixels=WIDTH * HEIGHT - discarded))
    _require(len(output) == total, "canonical material reference size differs")
    return bytes(output), evidence


def self_check():
    _scalar.self_check()
    # Explicit source byte multiplication and white/non-swappable detail checks.
    assert _color([179, 140, 120]) == [f32(179 * f32(1 / 255)), f32(140 * f32(1 / 255)), f32(120 * f32(1 / 255))]
    probe = {"part": "skin", "effective_colors_rgb": [[179, 140, 120], [255, 255, 255]],
             "base_texture": 0, "dual_texture": 1}
    selected = cases(probe, 0)
    assert len(selected) == 6 and [item["flags"] for item in selected] == [0, 1, 0, 1, 2, 3]
    assert RECORD.size == 128 and HEADER.size == 64
    assert struct.unpack_from("<III", record(selected[5]), 104) == (3, 0, 5)
    assert selected[0]["const0"][3] == 1 and selected[1]["const0"][3] == .5
    color = selected[0]["const0"]
    # White detail means first costume color, not an arbitrary grey default.
    rgba = fragment((.5, .25, .75, 0), (1, 1, 1, 1), color, (1, 1, 1, 1),
                    (.25, .25, .25, 1), (0, 0, 20, .1), (0, 0, 0, 1), 0, 0)
    assert rgba == (.5 * color[0], .25 * color[1], .75 * color[2], 1)
    assert fragment((1, 1, 1, 0), (1, 1, 1, 1), color, color,
                    (.25, .25, .25, 1), (0, 0, 20, .1), (0, 0, 0, 1), 0, 1) is None
    return {"passed": True, "cases_per_part": CASES_PER_PART,
            "source_byte_to_color": "float(byte) * (1.f / 255.f)",
            "oracle": "accepted independent source-semantic scalar evaluator; new costume inputs",
            "original_cg_execution": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        print(json.dumps(self_check(), indent=2))
    else:
        parser.error("Use prepare(parts,textures) from the character fixture builder or --self-check")


if __name__ == "__main__":
    main()

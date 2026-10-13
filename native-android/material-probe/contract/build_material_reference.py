#!/usr/bin/env python3
"""Prepare a fixed binary scalar reference from two actual GPU-role RGBA textures.

Header <8s10I> (48 bytes): COHMAT6\0, version, width, height, case_count,
record_bytes, base_width, base_height, dual_width, dual_height, reserved.
Each case <26f2I> (112 bytes), followed immediately by width*height*4 expected
bytes in lower-left FBO sample order. Fields are six vec4s (const0, const1,
vertex_color, fog_params, fog_color, clear), fog_coord, alpha_ref, flags,
reserved. Flag bit0 enables SRC_ALPHA/ONE_MINUS_SRC_ALPHA for RGBA.
Flag bit1 selects a controlled diagnostic dual-texture swatch, explicitly not
the real grey asset: 1x1 RGBA8 (51,153,230,128).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from material_reference import f32, fragment, framebuffer, self_check

HEADER = struct.Struct("<8s10I")
RECORD = struct.Struct("<26f2I")
MAGIC = b"COHMAT6\0"
WIDTH = HEIGHT = 64
CONTROLLED_DUAL_RGBA8 = (51, 153, 230, 128)


def cases():
    defaults = {"const0": [1, 1, 1, 1], "const1": [1, 1, 1, 1],
                "vertex_color": [.25, .25, .25, 1], "fog_params": [0, 0, 20, .1],
                "fog_color": [32/255, 64/255, 96/255, 1],
                "clear": [32/255, 96/255, 160/255, 128/255],
                "fog_coord": 0, "alpha_ref": 0, "flags": 0}
    overrides = [
        ("untinted_material", {}),
        ("dual_tint_mask", {"const0": [.125, .75, .25, 1], "const1": [.875, .25, .5, 1]}),
        ("colored_vertex_lighting", {"vertex_color": [.125, .375, .625, 1]}),
        ("mid_fog", {"fog_coord": 15}),
        ("full_fog", {"fog_coord": 30}),
        ("fog_start_clamp", {"fog_coord": 5}),
        ("zero_fade_discard", {"const0": [1, 1, 1, 0], "flags": 1}),
        ("half_fade_source_over", {"const0": [1, 1, 1, .5], "flags": 1}),
        ("full_fade_source_over", {"flags": 1}),
        ("strict_half_alpha_ref", {"const0": [1, 1, 1, .5], "alpha_ref": .5, "flags": 1}),
        ("cutout_ref_0_6", {"alpha_ref": .6, "flags": 1}),
        ("bright_source_over", {"vertex_color": [1, .75, .5, 1], "flags": 1}),
        ("tinted_fog_fade", {"const0": [.75, .125, .5, .5], "const1": [.25, .625, .875, 1],
                              "vertex_color": [.25, .5, .125, 1], "fog_coord": 15, "flags": 1}),
        ("no_coverage_ref_one", {"alpha_ref": 1, "flags": 1}),
        ("controlled_dual_rgb_and_alpha", {"const0": [.125, .875, .25, 1],
                                            "const1": [.875, .125, .75, 1], "flags": 2}),
        ("controlled_dual_half_fade_blend", {"const0": [.125, .875, .25, .5],
                                              "const1": [.875, .125, .75, 1], "flags": 3}),
        ("controlled_dual_ref_half_pass", {"const0": [.125, .875, .25, 1],
                                            "const1": [.875, .125, .75, 1], "alpha_ref": .5, "flags": 2}),
        ("controlled_dual_ref_point6_discard", {"const0": [.125, .875, .25, 1],
                                                 "const1": [.875, .125, .75, 1], "alpha_ref": .6, "flags": 3}),
    ]
    result = []
    for name, values in overrides:
        case = dict(defaults, **values)
        for key in ("const0", "const1", "vertex_color", "fog_params", "fog_color", "clear"):
            case[key] = [f32(v) for v in case[key]]
        case["fog_coord"] = f32(case["fog_coord"])
        case["alpha_ref"] = f32(case["alpha_ref"])
        case["name"] = name
        case["dual_texture_mode"] = "controlled_swatch" if case["flags"] & 2 else "original_asset"
        result.append(case)
    return result


def record(case):
    values = [v for key in ("const0", "const1", "vertex_color", "fog_params", "fog_color", "clear")
              for v in case[key]]
    return RECORD.pack(*values, case["fog_coord"], case["alpha_ref"], case["flags"], 0)


def sample_rgba(data, width, height, x, y):
    # Integer form of nearest GL_CLAMP_TO_EDGE sampling at (x+.5)/64.
    # Texture byte row0 is uploaded as GL row0; there is no FBO y flip.
    tx = min(width - 1, ((2 * x + 1) * width) // (2 * WIDTH))
    ty = min(height - 1, ((2 * y + 1) * height) // (2 * HEIGHT))
    at = (ty * width + tx) * 4
    return tuple(v / 255.0 for v in data[at:at + 4])


def texture(path, width, height):
    if not 0 < width <= 4096 or not 0 < height <= 4096:
        raise ValueError("fixture texture dimensions outside bounded contract")
    data = Path(path).read_bytes()
    if len(data) != width * height * 4:
        raise ValueError("RGBA texture length differs from dimensions")
    return data


def prepare(base, base_width, base_height, dual, dual_width, dual_height):
    if (len(base) != base_width * base_height * 4 or len(dual) != dual_width * dual_height * 4
            or not 0 < base_width <= 4096 or not 0 < base_height <= 4096
            or not 0 < dual_width <= 4096 or not 0 < dual_height <= 4096):
        raise ValueError("texture span/dimensions differ from bounded RGBA contract")
    selected = cases()
    output = bytearray(HEADER.pack(MAGIC, 1, WIDTH, HEIGHT, len(selected), RECORD.size,
                                  base_width, base_height, dual_width, dual_height, 0))
    evidence = []
    for case in selected:
        output.extend(record(case))
        pixels = bytearray()
        discarded = 0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                result = fragment(sample_rgba(base, base_width, base_height, x, y),
                                  (tuple(v/255.0 for v in CONTROLLED_DUAL_RGBA8) if case["flags"] & 2 else
                                   sample_rgba(dual, dual_width, dual_height, x, y)),
                                  case["const0"], case["const1"], case["vertex_color"],
                                  case["fog_params"], case["fog_color"],
                                  case["fog_coord"], case["alpha_ref"])
                discarded += result is None
                pixels.extend(framebuffer(result, case["clear"], bool(case["flags"] & 1)))
        assert len(pixels) == WIDTH * HEIGHT * 4
        output.extend(pixels)
        evidence.append(dict(case, expected_rgba_sha256=hashlib.sha256(pixels).hexdigest(),
                             discarded_pixels=discarded, passed_pixels=WIDTH*HEIGHT-discarded))
    expected_size = HEADER.size + len(selected) * (RECORD.size + WIDTH * HEIGHT * 4)
    assert len(output) == expected_size
    return bytes(output), evidence


generate = prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for prefix in ("base", "dual"):
        parser.add_argument("--"+prefix+"-rgba", type=Path, required=True)
        parser.add_argument("--"+prefix+"-width", type=int, required=True)
        parser.add_argument("--"+prefix+"-height", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    self_check()
    base = texture(args.base_rgba, args.base_width, args.base_height)
    dual = texture(args.dual_rgba, args.dual_width, args.dual_height)
    if args.output.resolve() in (args.base_rgba.resolve(), args.dual_rgba.resolve()):
        raise ValueError("reference output must not replace a texture")
    binary, selected = prepare(base, args.base_width, args.base_height,
                               dual, args.dual_width, args.dual_height)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(binary)
    evidence = {"format": "coh-material-reference-v1", "oracle": "independent_scalar_source_semantics",
                "original_cg_execution": False, "captured_runtime_parameters": False,
                "parameter_storage": "IEEE754-binary32", "calculation": "Python-binary64",
                "pixel_tolerance_quantization_units": 2, "width": WIDTH, "height": HEIGHT,
                "case_count": len(selected), "header_bytes": HEADER.size, "case_record_bytes": RECORD.size,
                "binary_sha256": hashlib.sha256(binary).hexdigest(), "binary_bytes": len(binary),
                "base": {"width": args.base_width, "height": args.base_height,
                         "rgba_sha256": hashlib.sha256(base).hexdigest()},
                "dual": {"width": args.dual_width, "height": args.dual_height,
                         "rgba_sha256": hashlib.sha256(dual).hexdigest()}, "cases": selected}
    evidence["controlled_dual_swatch"] = {"rgba8": CONTROLLED_DUAL_RGBA8, "width": 1, "height": 1,
                                           "case_count": 4, "original_asset": False}
    args.output.with_suffix(".json").write_text(json.dumps(evidence, indent=2)+"\n")
    print(json.dumps({key: evidence[key] for key in ("case_count", "binary_sha256", "binary_bytes")}, indent=2))


if __name__ == "__main__":
    main()

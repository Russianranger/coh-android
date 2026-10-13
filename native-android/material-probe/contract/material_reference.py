#!/usr/bin/env python3
"""Independent scalar CoH material/skin semantics, not an original-Cg GPU oracle.

The GLSL derivative is never parsed or executed here. This evaluator follows
hash-pinned source arithmetic and controlled parameter cases. Python binary64
calculation is compared with actual GPU float arithmetic using declared tolerances.
"""
from __future__ import annotations

import math
import struct


def finite(values):
    values = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("non-finite contract input")
    return values


def clamp(value, lo=0.0, hi=1.0):
    return min(hi, max(lo, value))


def f32(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("non-finite float parameter")
    return struct.unpack("<f", struct.pack("<f", value))[0]


def vertex(position, normal, weights, row_indices, rows, projection, light, diffuse, ambient):
    """Original hardware skin contract; rows are uploaded affine rows, not Mat4 columns."""
    position, normal, weights = finite(position), finite(normal), finite(weights)
    rows, projection = [finite(r) for r in rows], [finite(r) for r in projection]
    light, diffuse, ambient = finite(light), finite(diffuse), finite(ambient)
    if (len(position) != 3 or len(normal) != 3 or len(weights) != 2
            or len(rows) % 3 or not 0 < len(rows) <= 45
            or len(projection) != 4 or any(len(r) != 4 for r in rows + projection)
            or len(light) != 3 or len(diffuse) != 4 or len(ambient) != 4
            or len(row_indices) != 2):
        raise ValueError("invalid vertex/palette shape")
    if not 0.0 <= weights[1] <= 1.0:
        raise ValueError("weight.y outside [0,1]")
    p4 = (*position, 1.0)
    positions, normals = [], []
    for index in row_indices:
        if not isinstance(index, int) or index < 0 or index % 3 or index + 2 >= len(rows):
            raise ValueError("invalid local palette row index")
        positions.append(tuple(sum(row[i] * p4[i] for i in range(4))
                               for row in rows[index:index + 3]))
        normals.append(tuple(sum(row[i] * normal[i] for i in range(3))
                             for row in rows[index:index + 3]))
    w = weights[1]
    view = tuple(a + (b - a) * w for a, b in zip(*positions))
    blended = tuple(a + (b - a) * w for a, b in zip(*normals))
    length = math.sqrt(sum(v * v for v in blended))
    if length == 0:
        raise ValueError("undefined zero-length blended normal")
    n = tuple(v / length for v in blended)
    clip = tuple(sum(row[i] * (*view, 1.0)[i] for i in range(4)) for row in projection)
    factor = clamp(sum(a * b for a, b in zip(n, light)))
    lit = tuple(factor * d + a for d, a in zip(diffuse, ambient))
    fog = math.sqrt(sum(v * v for v in view) + 1e-16)
    return {"view_position": view, "view_normal": n, "clip_position": clip,
            "lit_color": lit, "fog_coord": fog}


def fragment(base, dual, const0, const1, lit_color, fog_params, fog_color, fog_coord, alpha_ref):
    vectors = [finite(v) for v in (base, dual, const0, const1, lit_color, fog_params, fog_color)]
    if any(len(v) != 4 for v in vectors):
        raise ValueError("fragment vectors require four components")
    base, dual, const0, const1, lit_color, fog_params, fog_color = vectors
    fog_coord, alpha_ref = finite((fog_coord, alpha_ref))
    if not 0 <= alpha_ref <= 1:
        raise ValueError("alpha reference outside fixed normalized range")
    tint = [const1[i] + (const0[i] - const1[i]) * dual[i] for i in range(3)]
    tint = [v + (1.0 - v) * base[3] for v in tint]
    rgb = [tint[i] * base[i] * (4.0 * lit_color[i]) for i in range(3)]
    alpha = dual[3] * const0[3]
    fog_factor = clamp(fog_params[3] * (fog_params[2] - fog_coord))
    rgb = [fog_color[i] + (rgb[i] - fog_color[i]) * fog_factor for i in range(3)]
    return None if not alpha > alpha_ref else (*rgb, alpha)


def unorm8(value):
    """Nearest normalized-byte reference; GPU gate allows <=2 quantization units."""
    return int(math.floor(clamp(value) * 255.0 + 0.5))


def framebuffer(source, clear, blend):
    """One RGBA8 draw over a clear; same SRC_ALPHA factors for all four channels."""
    dst_bytes = tuple(unorm8(v) for v in finite(clear))
    if len(dst_bytes) != 4:
        raise ValueError("clear must be RGBA")
    if source is None:
        return dst_bytes
    src = tuple(clamp(v) for v in finite(source))
    if len(src) != 4:
        raise ValueError("source must be RGBA")
    if not blend:
        return tuple(unorm8(v) for v in src)
    dst = tuple(v / 255.0 for v in dst_bytes)
    a = src[3]
    return tuple(unorm8(src[i] * a + dst[i] * (1.0 - a)) for i in range(4))


def self_check():
    # Independently specified boundary results; deliberately catch tint alpha,
    # fixed-function destination-alpha, fog and post-blend-normalization mistakes.
    identity = (1.0, 1.0, 1.0, 1.0)
    raw = fragment((.25, .5, .75, 1), (.3, .7, .1, .5), (.1, .2, .3, .5),
                   (.8, .6, .4, 1), (.25, .25, .25, 1), (0, 0, 10, .1),
                   (.1, .2, .3, 1), 0, 0)
    assert raw == (.25, .5, .75, .25), raw
    masked = fragment((.5, .25, .75, 0), (.25, .5, .75, .5), (1, 0, .5, .5),
                      (0, 1, 0, 1), (.25, .25, .25, 1), (0, 0, 10, .1),
                      (.1, .2, .3, 1), 0, 0)
    assert masked == (.125, .125, .28125, .25), masked
    partial = fragment((.5, .25, .75, .5), (.25, .5, .75, .5), (1, 0, .5, .5),
                       (0, 1, 0, 1), (.25, .25, .25, 1), (0, 0, 10, .1),
                       (.1, .2, .3, 1), 0, 0)
    assert partial == (.3125, .1875, .515625, .25), partial
    assert fragment(identity, (1, 1, 1, .5), identity, identity, identity,
                    (0, 0, 10, .1), identity, 0, .5) is None
    fogged = fragment(identity, identity, identity, identity, (.25, .25, .25, 1),
                      (0, 0, 10, .1), (.2, .4, .6, 1), 20, 0)
    assert all(abs(a-b) < 1e-12 for a,b in zip(fogged, (.2, .4, .6, 1)))
    # Alpha=.5 with dest alpha=.5 gives .5, not .75.
    assert framebuffer((1, 0, 0, .5), (0, 0, 1, .5), True) == (128, 0, 128, 128)
    assert framebuffer((2, -1, .5, .5), (0, 0, 0, 0), True) == (128, 0, 64, 64)
    # Normal interpolation is normalized and palette rows are affine dot rows.
    rows = [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0),
            (0, -1, 0, 2), (1, 0, 0, 0), (0, 0, 1, 0)]
    proj = [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]
    skinned = vertex((1, 0, 0), (1, 0, 0), (.5, .5), (0, 3), rows, proj,
                     (1, 0, 0), (.5, .5, .5, 0), (.1, .1, .1, 0))
    assert skinned["view_position"] == (1.5, .5, 0)
    assert abs(skinned["view_normal"][0] - math.sqrt(.5)) < 1e-12
    assert abs(sum(v*v for v in skinned["view_normal"]) - 1) < 1e-12
    return {"status": "passed", "kind": "source-semantic-boundaries",
            "original_cg_execution": False, "shader_execution": False}


if __name__ == "__main__":
    import json
    print(json.dumps(self_check(), indent=2))

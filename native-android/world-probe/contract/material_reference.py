#!/usr/bin/env python3
"""Independent Phase 9 rigid-world lighting and accepted dual-fragment semantics.

This module does not execute the GLSL derivative or the original Cg compiler.
The original-source world/camera transform oracle is maintained separately.
Only the scalar, low-profile COLORBLEND_DUAL fragment evaluator is reused.
"""
from __future__ import annotations

import importlib.util
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "coh_accepted_world_fragment", ROOT / "material-probe/contract/material_reference.py")
_scalar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scalar)
f32 = _scalar.f32
dual_fragment = _scalar.fragment
framebuffer = _scalar.framebuffer
unorm8 = _scalar.unorm8
clamp = _scalar.clamp


def _audit_read(path, stage):
    try:
        return path.read_bytes()
    except OSError as error:
        error.audit_stage = stage
        raise


def stock_grey_declaration(data):
    """Resolve the actual secondary BasicTexture declaration, not a shader override."""
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != 266 or digest != "a225c46b8701da525dd93f76dc455e8eb5f214d1ffc561b682eba9863a3facdc":
        raise ValueError("stock grey source declaration identity differs")
    text = data.decode("ascii")
    block = re.search(r"(?ims)^Texture grey\.tga\s*\n(.*?)^End\s*$", text)
    if not block:
        raise ValueError("stock grey source declaration is absent")
    tokens = [line.strip().lower() for line in block.group(1).splitlines() if line.strip()]
    if tokens != ["flags truecolor"]:
        raise ValueError("stock grey source TexOpt body differs")
    return {"lookup_name": "grey", "source_path": "upstream/i24/data/tricks/btest.txt",
            "source_sha256": digest, "tokens": tokens, "resolved_texopt_flags": 2,
            "selected_role": "secondary BasicTexture in Signmetal generic layer",
            "changes_composite_shader_family": False,
            "clamp_s": False, "clamp_t": False, "mirror_s": False, "mirror_t": False,
            "point_sample": False, "no_mip": False,
            "qualified_mip": 0, "qualified_rgba": [128, 128, 128, 255]}


def stock_white_declaration(data):
    """The actual white TexOpt is empty; white_tintable is a separate alias."""
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != 887 or digest != "5d15cb3c5c692eb108b87b6c2efdc6ab86f23bec6f39ad945d05c76947ba5943":
        raise ValueError("stock white source declaration identity differs")
    text = data.decode("ascii")
    block = re.search(r"(?ims)^Texture white\.tga\s*\n(.*?)^End\s*$", text)
    if not block:
        raise ValueError("stock white source declaration is absent")
    tokens = [line.strip().lower() for line in block.group(1).splitlines() if line.strip()]
    if tokens:
        raise ValueError("stock white source TexOpt body differs")
    return {"lookup_name": "white", "source_path": "upstream/i24/data/tricks/streets/elements/freeway_signs.txt",
            "source_sha256": digest, "tokens": [], "resolved_texopt_flags": 0,
            "selected_role": "secondary BasicTexture in modern_bench generic layer",
            "changes_composite_shader_family": False,
            "clamp_s": False, "clamp_t": False, "mirror_s": False, "mirror_t": False,
            "point_sample": False, "no_mip": False,
            "qualified_mip": 0, "qualified_rgba": [255, 255, 255, 255]}


def audit_source_tricks(source_root):
    """Fail closed if the complete immutable trick tree cannot be inspected.

    Original trickFromTextureName tries a direct basename and then each parent
    texture directory. Searching only for 'Signmetal' would miss directory
    overrides. This check reads and verifies every tracked source trick blob.
    It verifies the absence of selected direct/directory overrides for default
    Signmetal, the actual stock-grey Truecolor and stock-white empty TexOpts, and
    modern_bench/mbench declarations. It is a bounded declaration audit, not a complete
    original TexOpt parser or an Atlas light-grid execution.
    """
    source_root = Path(source_root).resolve()
    pins = json.loads(Path(__file__).with_name("source-material-pins.json").read_text())
    source_file_checks = []
    for identity in pins["source_files"]:
        data = _audit_read(source_root / identity["path"], "primary-source-identity")
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != identity["bytes"] or digest != identity["sha256"]:
            raise ValueError("original primary material source differs: " + identity["path"])
        source_file_checks.append({"path": identity["path"], "bytes": len(data), "sha256": digest})
    prefix = "upstream/i24/data/tricks"
    actual_tree = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD:" + prefix], text=True).strip()
    if actual_tree != pins["tricks_tree"]["git_tree_sha"]:
        raise ValueError("original complete trick tree differs from source pin")
    entries = subprocess.check_output(
        ["git", "-C", str(source_root), "ls-tree", "-r", "--format=%(objectname)\t%(path)",
         "HEAD", prefix], text=True).splitlines()
    if len(entries) != pins["tricks_tree"]["file_count"]:
        raise ValueError("original complete trick tree file count differs")
    matched = []
    declarations = {}
    model_tricks = {}
    for entry in entries:
        blob_sha, relative = entry.split("\t", 1)
        path = source_root / relative
        data = _audit_read(path, "complete-trick-blob-identity")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if digest != blob_sha:
            raise ValueError("original trick source blob differs: " + relative)
        text = data.removeprefix(b"\xef\xbb\xbf").decode("latin1")
        # Comment delimiters do not form actual parser declarations.
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        # InternalName can replace TexOpt.name. Conservatively retain both
        # labels: an unexpected selected alias must be resolved explicitly.
        for match in re.finditer(r'(?im)^\s*(?:Texture|InternalName)\s+("[^"\n]+"|[^\s]+)', text):
            raw_name = match.group(1).strip('"').replace("\\", "/").lstrip("/").lower()
            name = raw_name.rsplit(".", 1)[0] if not raw_name.endswith("/") else raw_name
            declarations.setdefault(name, []).append(relative)
        for match in re.finditer(r'(?im)^\s*Trick\s+("[^"\n]+"|[^\s]+)', text):
            name = match.group(1).strip('"').lower()
            model_tricks.setdefault(name, []).append(relative)
    lookup_names = {
        "Signmetal": ["signmetal", "world/swappables_and_decals/signs/billboard/billboard_structure/",
                      "world/swappables_and_decals/signs/billboard/", "world/swappables_and_decals/signs/",
                      "world/swappables_and_decals/", "world/"],
        "grey": ["grey", "world/filler/", "world/"],
        "white": ["white", "world/filler/", "world/"],
    }
    grey_path = "upstream/i24/data/tricks/btest.txt"
    grey = stock_grey_declaration(_audit_read(source_root / grey_path, "stock-grey-declaration"))
    white_path = "upstream/i24/data/tricks/streets/elements/freeway_signs.txt"
    white = stock_white_declaration(_audit_read(source_root / white_path, "stock-white-declaration"))
    errors, lookup_context = [], []
    for alias, candidates in lookup_names.items():
        found = {candidate: declarations[candidate] for candidate in candidates if candidate in declarations}
        expected = {"grey": [grey_path]} if alias == "grey" else {"white": [white_path]} if alias == "white" else {}
        lookup_context.append({"alias": alias, "actual_declarations": found, "expected_declarations": expected,
                               "passed": found == expected})
        if found != expected:
            errors.append("unexpected selected source material override for " + alias + ": " + repr(found))
        matched.append({"alias": alias, "lookup_candidates": candidates,
                        "source_matches": [grey] if alias == "grey" else [white] if alias == "white" else [],
                        "default_generic": "grey" if alias == "Signmetal" else None})
    required_path = "upstream/i24/data/tricks/streets/elements/streets_misc.txt"
    if declarations.get("modern_bench") != [required_path]:
        errors.append("selected modern bench direct source declaration differs: " + repr(declarations.get("modern_bench")))
    if model_tricks.get("mbench") != [required_path]:
        errors.append("selected model mbench direct source declaration differs: " + repr(model_tricks.get("mbench")))
    text = (source_root / required_path).read_text()
    texture = re.search(r"(?ims)^Texture modern_bench\.tga\s*\n(.*?)^End\s*$", text)
    trick = re.search(r"(?ims)^Trick mbench\s*\n(.*?)^End\s*$", text)
    texture_tokens = [line.strip().lower() for line in texture.group(1).splitlines() if line.strip()] if texture else None
    trick_tokens = [line.strip().lower() for line in trick.group(1).splitlines() if line.strip()] if trick else None
    if texture_tokens != ["surface metal", "blend white.tga", "blendtype colorblenddual"]:
        errors.append("selected bench texture trick body differs: " + repr(texture_tokens))
    if trick_tokens != ["lodfar 250", "lodfarfade 75"]:
        errors.append("selected bench model trick body differs: " + repr(trick_tokens))
    context = {"lookup_resolutions": lookup_context,
               "modern_bench_declarations": declarations.get("modern_bench", []),
               "mbench_declarations": model_tricks.get("mbench", []),
               "modern_bench_tokens": texture_tokens, "mbench_tokens": trick_tokens}
    if errors:
        error = ValueError("; ".join(errors))
        error.audit_stage = "complete-selected-source-resolution"
        error.audit_context = context
        raise error
    return {"passed": True, "kind": "complete immutable original trick declaration audit",
            "git_tree_sha": actual_tree, "source_files_verified": len(entries),
            "primary_source_files_verified": source_file_checks,
            "direct_and_directory_lookup": matched,
            "selected_source_resolution_context": context,
            "modern_bench_source": required_path, "modern_bench_tokens": texture_tokens,
            "mbench_tokens": trick_tokens,
            "full_original_texopt_parser_executed": False,
            "original_atlas_lighting_executed": False}


def multiply_fragment(base, blend, const0, const1, lit_color, fog_params, fog_color, fog_coord, alpha_ref):
    """multiplyregfp.cg without HQ/shadow/cubemap/debug variants.

    Original g_Env0FP.rgb and g_Env1FP do not tint the MULTIPLY family.
    Fixed-function GREATER alpha testing occurs after the fragment operation.
    """
    vectors = [_scalar.finite(v) for v in (base, blend, const0, const1, lit_color, fog_params, fog_color)]
    if any(len(v) != 4 for v in vectors):
        raise ValueError("multiply fragment vectors require four components")
    base, blend, const0, const1, lit_color, fog_params, fog_color = vectors
    fog_coord, alpha_ref = _scalar.finite((fog_coord, alpha_ref))
    if not 0 <= alpha_ref <= 1:
        raise ValueError("alpha reference outside fixed normalized range")
    rgb = [base[i] * blend[i] * (8.0 * lit_color[i]) for i in range(3)]
    alpha = base[3] * blend[3] * const0[3]
    fog_factor = clamp(fog_params[3] * (fog_params[2] - fog_coord))
    rgb = [fog_color[i] + (rgb[i] - fog_color[i]) * fog_factor for i in range(3)]
    return None if not alpha > alpha_ref else (*rgb, alpha)


def fragment(base, dual, const0, const1, lit_color, fog_params, fog_color, fog_coord, alpha_ref, mode=1):
    if mode not in (0, 1):
        raise ValueError("unsupported source world material mode")
    evaluator = multiply_fragment if mode == 0 else dual_fragment
    return evaluator(base, dual, const0, const1, lit_color, fog_params, fog_color, fog_coord, alpha_ref)


def source_rgb(values):
    """modelDrawDirect's scaleVec3(c[n], 1.f/255.f, constColorN)."""
    if len(values) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in values):
        raise ValueError("source tint requires three unsigned RGB bytes")
    reciprocal = f32(1.0 / 255.0)
    return tuple(f32(f32(v) * reciprocal) for v in values)


def world_lighting(view_normal, light, diffuse, ambient, attr_color=(1, 1, 1, 1)):
    """FF_LIT_GL with controlled zero specular and white vertex color.

    vp_master_vp.cg normalizes the model-view transformed normal. Its original
    diffuse/specular helper has saturate(dot(N,L) * diffuse.rgb). The
    selected neutral specular input is zero; this does not qualify original
    Atlas light grids, baked RGB buffers, sun state or specular material state.
    """
    vectors = [tuple(float(v) for v in vector)
               for vector in (view_normal, light, diffuse, ambient, attr_color)]
    if [len(v) for v in vectors] != [3, 3, 4, 4, 4] or not all(
            math.isfinite(value) for vector in vectors for value in vector):
        raise ValueError("invalid rigid-world lighting vectors")
    view_normal, light, diffuse, ambient, attr_color = vectors
    length = math.sqrt(sum(v * v for v in view_normal))
    if not length:
        raise ValueError("zero rigid-world normal")
    normal = tuple(v / length for v in view_normal)
    raw_dot = sum(n * l for n, l in zip(normal, light))
    factor = clamp(raw_dot)
    color = tuple((clamp(raw_dot * diffuse[i]) + ambient[i]) * attr_color[i] for i in range(3))
    return {"normal": normal, "diffuse_factor": factor,
            "color": (*color, attr_color[3])}


def self_check():
    _scalar.self_check()
    expected = tuple(f32(v * f32(1 / 255)) for v in (67, 139, 202))
    assert source_rgb((67, 139, 202)) == expected
    assert source_rgb((0, 0, 0)) == (0, 0, 0)
    lit = world_lighting((0, 0, 4), (0, 0, 1), (.3, .4, .5, 0), (.1, .2, .3, 0))
    assert lit["normal"] == (0, 0, 1) and lit["diffuse_factor"] == 1
    assert all(abs(a - b) < 1e-12 for a, b in zip(lit["color"], (.4, .6, .8, 1)))
    neutral = world_lighting((0, 3, 0), (0, 0, 1), (0, 0, 0, 0), (.25, .25, .25, 0))
    assert neutral["color"] == (.25, .25, .25, 1)
    tint = (*source_rgb((67, 139, 202)), 1)
    black = (0, 0, 0, 1)
    # Real stock white selects tint0; base alpha remains the source tint bypass.
    tinting = fragment((.5, .25, .75, 0), (1, 1, 1, 1), tint, black,
                      neutral["color"], (0, 0, 20, .1), (0, 0, 0, 1), 0, 0)
    assert tinting == (.5 * tint[0], .25 * tint[1], .75 * tint[2], 1)
    bypass = fragment((.5, .25, .75, 1), (1, 1, 1, 1), tint, black,
                      neutral["color"], (0, 0, 20, .1), (0, 0, 0, 1), 0, 0)
    assert bypass == (.5, .25, .75, 1)
    multiplied = fragment((.5, .25, .75, 1), (.5, .5, .5, 1), tint, black,
                          neutral["color"], (0, 0, 20, .1), (0, 0, 0, 1), 0, 0, mode=0)
    assert multiplied == (.5, .25, .75, 1)
    # Base and blend alpha both matter for multiply, rather than only dual alpha.
    assert fragment((1, 1, 1, .5), (1, 1, 1, .5), (*tint[:3], .5), black,
                    neutral["color"], (0, 0, 20, .1), (0, 0, 0, 1), 0, 0, mode=0)[3] == .125
    assert fragment((1, 1, 1, .5), (1, 1, 1, .5), tint, black,
                    neutral["color"], (0, 0, 20, .1), (0, 0, 0, 1), 0, .25, mode=0) is None
    return {"passed": True, "shader_execution": False, "original_cg_execution": False,
            "oracle": "independent scalar original-source semantics",
            "static_atlas_lighting_qualified": False,
            "source_byte_to_color": "float(byte) * (1.f / 255.f)",
            "selected_specular_rgb": [0, 0, 0]}


if __name__ == "__main__":
    import json
    print(json.dumps(self_check(), indent=2))

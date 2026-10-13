#!/usr/bin/env python3
"""Recover bounded Wretch costume material bindings from pinned source text.

This explicitly selects the original no-MULTITEX/no-BUMPMAPS renderer profile.
It does not approximate the full MULTI material or silently use GEO defaults.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = Path(__file__).resolve().parent
SOURCE_PATHS = [
    "upstream/i24/data/tricks/v_shaders/arachnos/henchmen/arachnos_wretch.txt",
    "upstream/i24/data/tricks/v_shaders/arachnos/wolf_spiders/wolf_spiders.txt",
    "upstream/i24/data/tricks/v_enemy.txt",
    "upstream/i24/data/tricks/hero_bump.txt",
    "upstream/ouroboros/Common/seq/tricks.c",
    "upstream/ouroboros/Game/src/render/tex.c",
    "upstream/ouroboros/Game/src/render/rendermodel.c",
    "upstream/ouroboros/Game/src/render/model.c",
    "upstream/ouroboros/Game/src/render/rendertree.c",
    "upstream/ouroboros/Game/src/render/thread/rt_bonedmodel.c",
    "upstream/ouroboros/Game/src/render/thread/rt_state.c",
    "upstream/ouroboros/Game/src/render/thread/rt_init.c",
    "upstream/ouroboros/Game/src/render/thread/rt_tricks.c",
    "upstream/i24/data/shaders/cgfx/colorblenddualfp.cg",
    "upstream/i24/data/shaders/cgfx/functions.cgh",
]


def source(path):
    local = ROOT / path
    if local.is_file():
        return local.read_bytes()
    # Read-only original-source copies created by the binding audit can avoid
    # redundant sparse-checkout blob fetches. Their SHA256 is retained below;
    # a complete checkout/CI reads the repository file directly.
    cached = ROOT.parent / "native-phase8/source-binding" / Path(path).name
    if cached.is_file() and path.startswith("upstream/ouroboros/"):
        return cached.read_bytes()
    return subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT)


def blocks(text):
    result = {}
    # The admitted two source files use simple Texture/End blocks; comments
    # are stripped before tokenizing, matching the original semantic tokens.
    active = None
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip()
        fields = line.split()
        if not fields:
            continue
        if fields[0].lower() == "texture":
            active = {"name": fields[1], "fields": {}}
            result[fields[1].lower()] = active
        elif fields[0].lower() == "end":
            active = None
        elif active is not None:
            active["fields"][fields[0].lower()] = fields[1:]
    return result


def normalized(name):
    return None if name is None or name.lower() == "none" or name.lower().startswith("texture_name") else name


def resolve():
    raw = {path: source(path) for path in SOURCE_PATHS}
    definitions = {}
    for path in SOURCE_PATHS[:2]:
        for name, block in blocks(raw[path].decode("utf-8", "replace")).items():
            block["source_path"] = path
            definitions[name] = block
    binding = json.loads((CONTRACT / "binding.json").read_text())
    parts = []
    for part in binding["parts"]:
        alias = part["resolved_texture1"]
        composite = definitions.get(alias.lower())
        if composite:
            fields = composite["fields"]
            names = {key: normalized(values[0]) for key, values in fields.items()
                     if key in ("base1", "dualcolor1", "multiply1", "addglow1", "mask", "base2",
                                "multiply2", "dualcolor2", "bumpmap1", "bumpmap2")}
            if not names.get("mask") or names["mask"].lower().startswith("white"):
                for key in ("mask", "base2", "multiply2", "dualcolor2", "bumpmap2"):
                    names[key] = None
            is_multi = any(names.get(key) for key in ("multiply1", "addglow1", "mask", "base2",
                                                      "multiply2", "dualcolor2", "bumpmap2"))
            # Every active layer in these exact admitted source blocks has unit
            # UV scale and zero scroll; there is no explicit Fallback block.
            for layer in names:
                if names[layer]:
                    if fields.get(layer + "scale", ["1", "1"]) != ["1", "1"]:
                        raise ValueError("selected material has unsupported UV scale")
                    if fields.get(layer + "scroll", ["0", "0"]) != ["0", "0"]:
                        raise ValueError("selected material has unsupported UV scroll")
            if any(key.endswith("swappable") and values != ["0"] for key, values in fields.items()):
                raise ValueError("selected material unexpectedly has a swappable layer")
            base, dual = names["base1"], names.get("dualcolor1") or "white"
            path = composite["source_path"]
            origin = "MULTI automatic fallback" if is_multi else "setupTexOpt single-material demotion; bump capability disabled"
            stored_scale = [.5, .5, .5] if is_multi else [1, 1, 1]
        else:
            base, dual = alias, part["resolved_texture2"]
            path = "upstream/i24/data/tricks/v_enemy.txt" if "skin_wretch" in alias.lower() else None
            origin = "old-style costume base and swappable generic override; bump capability disabled"
            stored_scale = None
        parts.append({"part_index": part["index"], "part": part["part"],
                      "costume_composite_alias": alias if composite else None,
                      "base_alias": base, "dual_alias": dual,
                      "effective_colors_rgb": part["effective_colors_rgb"], "draw_alpha": part["draw_alpha"],
                      "shader_family": "COLORBLEND_DUAL", "blend_bits": ["BMB_NV1XWORLD"],
                      "resolution": origin, "source_material_file": path,
                      "costume_generic_override": part["resolved_texture2"],
                      "costume_generic_override_applied": composite is None,
                      "stored_fallback_ambient_scale": stored_scale,
                      "stored_fallback_diffuse_scale": stored_scale,
                      "draw_ambient_multiplier": [1, 1, 1], "draw_diffuse_multiplier": [1, 1, 1],
                      "double_sided": "__collar2x" in part["source_model_name"].lower(),
                      "front_face": "CW", "cull_face": "BACK", "depth_write": True,
                      "blend_source": "SRC_ALPHA", "blend_destination": "ONE_MINUS_SRC_ALPHA",
                      "alpha_sort_flag": False,
                      "alpha_sort_origin": "model.c GEO_* colorblend_alpha_hack skips modelNeedsAlphaSort; rendertree.c customtexture alpha-sort guard is disabled; Collar2x only DoubleSided",
                      "source_object_trick": "Collar2x" if "__collar2x" in part["source_model_name"].lower() else None,
                      "alpha_ref": 0.0, "alpha_ref_origin": "rt_state.c:1103 glAlphaFunc(GL_GREATER,0); no object-specific alpha-ref in Collar2x",
                      "sampler": {"min_filter": "NEAREST", "mag_filter": "NEAREST", "wrap": "CLAMP_TO_EDGE", "mip": 0},
                      "uv_scale_base": [1, 1], "uv_scale_dual": [1, 1], "uv_scroll": [0, 0],
                      "full_quality_material_qualified": False})
    if len(parts) != 11 or parts[6]["dual_alias"] != "white" or parts[1]["dual_alias"] != "Chest_Wolf_01b":
        raise ValueError("material source identity changed")
    result = {"format": "phase8-wretch-resolved-materials-v1", "part_count": len(parts),
              "profile": {"GFXF_MULTITEX": False, "GFXF_BUMPMAPS": False, "vertex_shaders": True,
                          "fragment_program": "colorblenddualfp.cg", "BIT_HIGH_QUALITY": False,
                          "BIT_SHADOWMAP": False, "BIT_DEBUG": False,
                          "lighting": "controlled character lighting; unmodified by stored TexOpt scales in original dual boned branch"},
              "source_pins": [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                              for path, data in raw.items()],
              "notes": ["six authored X_* costume composite identities are retained; both boots share one",
                        "none and texture_name* are cleared before TexOpt family selection",
                        "chest Mask none removes second material; it demotes to an old dual+bump family before no-bump filtering",
                        "other five X_* families retain masks and choose the source automatic dual-color fallback",
                        "fixed authored DualColor1 masks are non-swappable; a costume generic white cannot replace them",
                        "belt DualColor1 texture_name is cleared; source white is retained",
                        "stock white is required by texFindNeededBinds and loaded as white.tga by texMakeWhite; retain actual acquired pixels/dimensions/hash",
                        "BMB_NV1XWORLD is a legacy register-combiner choice; it adds no Cg dual fragment operation",
                        "Collar2x makes Hair and Neck double-sided; it supplies no alpha cutout or alpha reference",
                        "probe nearest/mip0/clamp samplers and controlled lights are explicit validation inputs, not captured runtime state",
                        "advanced MULTI masks, reflections, bump maps, specular, original driver texture decompression and draw sorting remain unqualified"],
              "parts": parts, "original_windows_pixel_capture": False}
    (CONTRACT / "materials.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    result = resolve()
    print(json.dumps({"prepared": True, "part_count": len(result["parts"]),
                      "pairs": [[p["part"], p["base_alias"], p["dual_alias"]] for p in result["parts"]]}, indent=2))

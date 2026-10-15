#!/usr/bin/env python3
"""Bounded offline FreeType atlas for original CoH fonts; no runtime font decode.

Uses the original ttFontRenderGlyphEx defaultSize==renderSize, normal grayscale
render, and mont_hvbold NOHINT policy. Uses the host FreeType, not the legacy
version; identical original-client glyph rasterization is not claimed.
"""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
import re
from pathlib import Path

class Generic(C.Structure):
    _fields_=[("data",C.c_void_p),("finalizer",C.c_void_p)]
class Vector(C.Structure):
    _fields_=[("x",C.c_long),("y",C.c_long)]
class BBox(C.Structure):
    _fields_=[("xMin",C.c_long),("yMin",C.c_long),("xMax",C.c_long),("yMax",C.c_long)]
class Bitmap(C.Structure):
    _fields_=[("rows",C.c_uint),("width",C.c_uint),("pitch",C.c_int),("buffer",C.POINTER(C.c_ubyte)),
              ("num_grays",C.c_ushort),("pixel_mode",C.c_ubyte),("palette_mode",C.c_ubyte),("palette",C.c_void_p)]
class Metrics(C.Structure):
    _fields_=[(name,C.c_long) for name in ("width","height","horiBearingX","horiBearingY","horiAdvance","vertBearingX","vertBearingY","vertAdvance")]
class Slot(C.Structure):
    _fields_=[("library",C.c_void_p),("face",C.c_void_p),("next",C.c_void_p),("glyph_index",C.c_uint),
              ("generic",Generic),("metrics",Metrics),("linearHoriAdvance",C.c_long),("linearVertAdvance",C.c_long),
              ("advance",Vector),("format",C.c_uint),("bitmap",Bitmap),("bitmap_left",C.c_int),("bitmap_top",C.c_int)]
class Face(C.Structure):
    _fields_=[("num_faces",C.c_long),("face_index",C.c_long),("face_flags",C.c_long),("style_flags",C.c_long),
              ("num_glyphs",C.c_long),("family_name",C.c_char_p),("style_name",C.c_char_p),("num_fixed_sizes",C.c_int),
              ("available_sizes",C.c_void_p),("num_charmaps",C.c_int),("charmaps",C.c_void_p),("generic",Generic),
              ("bbox",BBox),("units_per_EM",C.c_ushort),("ascender",C.c_short),("descender",C.c_short),("height",C.c_short),
              ("max_advance_width",C.c_short),("max_advance_height",C.c_short),("underline_position",C.c_short),
              ("underline_thickness",C.c_short),("glyph",C.POINTER(Slot)),("size",C.c_void_p),("charmap",C.c_void_p)]

def checked(value,what):
    if value:raise ValueError(f"FreeType {what} failed: {value}")

def render(font,size=16,codepoints=range(32,127),nohint=True):
    if size<8 or size>64:raise ValueError("Atlas design size must be 8..64")
    points=list(codepoints)
    if not points or len(points)>512 or points!=sorted(set(points)):raise ValueError("1..512 sorted unique codepoints required")
    if any(c<32 or c==127 or c>0x10ffff or 0xd800<=c<=0xdfff for c in points):raise ValueError("Invalid scalar")
    if font.stat().st_size>8*1024*1024:raise ValueError("Font exceeds 8 MiB preparation limit")
    ft=C.CDLL(ctypes.util.find_library("freetype") or "libfreetype.so.6")
    ft.FT_Init_FreeType.argtypes=[C.POINTER(C.c_void_p)]
    ft.FT_New_Face.argtypes=[C.c_void_p,C.c_char_p,C.c_long,C.POINTER(C.POINTER(Face))]
    ft.FT_Set_Pixel_Sizes.argtypes=[C.POINTER(Face),C.c_uint,C.c_uint]
    ft.FT_Get_Char_Index.argtypes=[C.POINTER(Face),C.c_ulong];ft.FT_Get_Char_Index.restype=C.c_uint
    ft.FT_Load_Glyph.argtypes=[C.POINTER(Face),C.c_uint,C.c_int32]
    ft.FT_Render_Glyph.argtypes=[C.POINTER(Slot),C.c_uint]
    ft.FT_Done_Face.argtypes=[C.POINTER(Face)];ft.FT_Done_FreeType.argtypes=[C.c_void_p]
    ft.FT_Library_Version.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_int)]
    library=C.c_void_p();face=C.POINTER(Face)();checked(ft.FT_Init_FreeType(C.byref(library)),"init")
    try:
        checked(ft.FT_New_Face(library,str(font).encode(),0,C.byref(face)),"new face")
        checked(ft.FT_Set_Pixel_Sizes(face,size,size),"size")
        version=[C.c_int() for _ in range(3)]
        ft.FT_Library_Version(library,*[C.byref(v) for v in version])
        glyphs=[]
        for cp in points:
            index=ft.FT_Get_Char_Index(face,cp)
            if not index:raise ValueError(f"Missing original font glyph U+{cp:04X}")
            checked(ft.FT_Load_Glyph(face,index,2 if nohint else 0),"load glyph") # FT_LOAD_NO_HINTING=2
            checked(ft.FT_Render_Glyph(face.contents.glyph,0),"render glyph") # FT_RENDER_MODE_NORMAL=0
            slot=face.contents.glyph.contents;bitmap=slot.bitmap
            if bitmap.width>256 or bitmap.rows>256 or abs(bitmap.pitch)>1024:raise ValueError("Oversized glyph bitmap")
            if bitmap.width and bitmap.rows and bitmap.pixel_mode!=2:raise ValueError("Expected grayscale bitmap")
            pixels=bytearray()
            for row in range(bitmap.rows):
                address=C.addressof(bitmap.buffer.contents)+row*bitmap.pitch
                pixels.extend(C.string_at(address,bitmap.width))
            glyphs.append({"codepoint":cp,"glyph_index":index,"width":bitmap.width,"height":bitmap.rows,
                           "bearing_x":slot.bitmap_left,"bearing_y":size-slot.bitmap_top,
                           "advance":slot.advance.x/64,"alpha":bytes(pixels)})
        return glyphs,{"freetype_version":".".join(str(v.value) for v in version),
                       "family":face.contents.family_name.decode(errors="replace"),
                       "style":face.contents.style_name.decode(errors="replace"),"units_per_em":face.contents.units_per_EM,
                       "no_hinting":nohint,"pixel_size":[size,size],"mode":"normal grayscale"}
    finally:
        if face:ft.FT_Done_Face(face)
        ft.FT_Done_FreeType(library)

def build(font,output,size=16,resource=7,font_id=1,prefix="coh_hud_font",nohint=True):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",prefix):raise ValueError("C identifier prefix required")
    if resource<1 or resource>0xffffffff or font_id<1 or font_id>0xffffffff:raise ValueError("Positive uint32 resource and font IDs required")
    glyphs,info=render(font,size,nohint=nohint)
    width=256;x=y=1;row_height=0
    for g in glyphs:
        if x+g["width"]+1>width:x=1;y+=row_height+1;row_height=0
        g["x"]=x;g["y"]=y;x+=g["width"]+1;row_height=max(row_height,g["height"])
    height=1
    while height<y+row_height+1:height*=2
    if width*height>1024*1024:raise ValueError("Atlas exceeds 1 MiB alpha budget")
    pixels=bytearray(width*height)
    for g in glyphs:
        for row in range(g["height"]):
            a=(g["y"]+row)*width+g["x"];b=row*g["width"]
            pixels[a:a+g["width"]]=g["alpha"][b:b+g["width"]]
    output.mkdir(parents=True,exist_ok=True)
    from PIL import Image
    image=Image.frombytes("L",(width,height),bytes(pixels));image.save(output/"atlas.png")
    (output/"atlas.alpha").write_bytes(pixels)
    def cf(n):return f"{float(n):.9f}f"
    lines=['/* Generated from user-owned original game font; preparation only. */',
           '#include "coh_hud_atlas.h"',f'#define {prefix.upper()}_WIDTH {width}',f'#define {prefix.upper()}_HEIGHT {height}',
           f'static const unsigned char {prefix}_alpha[{len(pixels)}]={{']
    for offset in range(0,len(pixels),32):lines.append(",".join(str(v) for v in pixels[offset:offset+32])+",")
    lines+=['};',f'static const CohHudAtlasEntry {prefix}_entries[{len(glyphs)}]={{']
    entries=[]
    for g in glyphs:
        uv=[g["x"]/width,g["y"]/height,g["width"]/width,g["height"]/height]
        fields=[g[k] for k in ("width","height","bearing_x","bearing_y","advance")]
        lines.append('{'+str(g["codepoint"])+',{'+str(resource)+',{'+','.join(cf(v) for v in uv)+'},'+','.join(cf(v) for v in fields)+'}},')
        entries.append({k:v for k,v in g.items() if k!="alpha"}|{"uv":uv,"mask_sha256":hashlib.sha256(g["alpha"]).hexdigest()})
    lines+=['};',f'static CohHudAtlas {prefix}={{ {font_id}, {cf(size)}, {prefix}_entries, {len(glyphs)}, 63 }};']
    (output/"atlas.h").write_text("\n".join(lines)+"\n")
    manifest={"font_name":font.name,"font_sha256":hashlib.sha256(font.read_bytes()).hexdigest(),
              "source_identity":"caller-provided original external asset pack font; no font bytes embedded in repository",
              "width":width,"height":height,"alpha_bytes":len(pixels),"glyphs":entries,"resource_id":resource,
              "font_id":font_id,"fallback_codepoint":63,"design_size":size,"rasterization":info,
              "alpha_sha256":hashlib.sha256(pixels).hexdigest(),"header_sha256":hashlib.sha256((output/"atlas.h").read_bytes()).hexdigest(),
              "scope":"Authentic font bytes, bounded ASCII atlas, source NOHINT loading policy. Host FreeType version differs; not legacy/GPU visual parity."}
    (output/"atlas.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument("--font",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--size",type=int,default=16);p.add_argument("--resource-id",type=int,default=7);p.add_argument("--font-id",type=int,default=1)
    p.add_argument("--prefix",default="coh_hud_font");p.add_argument("--hinted",action="store_true")
    a=p.parse_args();m=build(a.font,a.output,a.size,a.resource_id,a.font_id,a.prefix,not a.hinted)
    print(json.dumps({"output":str(a.output),"font_sha256":m["font_sha256"],"alpha_bytes":m["alpha_bytes"],"glyphs":len(m["glyphs"])}))
if __name__=="__main__":main()

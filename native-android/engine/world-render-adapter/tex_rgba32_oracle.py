"""Whole original DDS reader/upload functions with explicit host observers.

Only the canonical bounded RGBA32 test domain is admitted by the wrapper. The
GL entry points observe bytes; they never create a context or execute GL.
"""
from pathlib import Path
import hashlib


def _block(text, signature, declaration=False):
    """Extract one unchanged balanced C definition, ignoring quoted braces."""
    if text.count(signature) != 1:
        raise ValueError("original definition is not unique: " + signature)
    start = text.index(signature)
    position = text.index("{", start)
    depth = 0
    state = "code"
    while position < len(text):
        char = text[position]
        following = text[position:position + 2]
        if state == "line":
            if char == "\n":
                state = "code"
        elif state == "comment":
            if following == "*/":
                state = "code"
                position += 1
        elif state in ("'", '"'):
            if char == "\\":
                position += 1
            elif char == state:
                state = "code"
        elif following == "//":
            state = "line"
            position += 1
        elif following == "/*":
            state = "comment"
            position += 1
        elif char in ("'", '"'):
            state = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = position + 1
                if declaration:
                    end = text.index(";", end) + 1
                return text[start:end] + "\n"
        position += 1
    raise ValueError("unterminated original definition: " + signature)


def create(root):
    root = Path(root)
    base = root / "upstream/ouroboros/Game/src/render"
    tex = (base / "tex.c").read_text()
    header = (base / "tex.h").read_text()
    render = (base / "thread/rt_tex.c").read_text()
    render_header = (base / "thread/rt_tex.h").read_text()
    dd = (base / "dd.h").read_text()
    functions = {
        "ddsLoad": _block(tex, "static int ddsLoad("),
        "texCopyDirect": _block(render, "void texCopyDirect("),
    }
    types = {
        "TexReadInfo": _block(header, "typedef struct TexReadInfo", True),
        "TexFormat": _block(header, "enum\n{\n    TEXFMT_8BIT", True),
        "RdrTexParams": _block(render_header, "typedef struct RdrTexParams", True),
        "dd.h": dd,
    }
    dds_flags = "\n".join(line for line in header.splitlines()
                          if line.startswith(("#define DDS_RGB\t", "#define DDS_RGBA\t",
                                              "#define DDS_RGB ", "#define DDS_RGBA ")))
    if len(dds_flags.splitlines()) != 2:
        raise ValueError("original DDS pixel flags differ")
    code = r'''#include "tests/tex_rgba32_fixture.h"
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef uint8_t U8, BYTE;
typedef uint16_t U16, WORD;
typedef uint32_t U32, DWORD;
typedef int32_t LONG;
/* Original Win32 serialized pointer slot; it is never dereferenced. */
typedef uint32_t LPVOID;
''' + dd + '\n' + types["TexReadInfo"] + types["TexFormat"] + types["RdrTexParams"] + dds_flags + r'''
_Static_assert(sizeof(DWORD)==4 && sizeof(LONG)==4 && sizeof(LPVOID)==4,"Win32 DDS scalar observer");
_Static_assert(sizeof(DDPIXELFORMAT)==32 && sizeof(DDSURFACEDESC2)==124,"original Win32 DDS wire sizes");
_Static_assert(offsetof(DDSURFACEDESC2,lpSurface)==36 && offsetof(DDSURFACEDESC2,ddpfPixelFormat)==72 && offsetof(DDSURFACEDESC2,ddsCaps)==104,"original Win32 DDS wire offsets");
_Static_assert(sizeof(RdrTexParams)==28 && offsetof(RdrTexParams,id)==12,"original scalar render-command layout observer");
_Static_assert(TEXFMT_ARGB_8888==7,"original RGBA32 source format");
enum {
 GL_TEXTURE_2D=0x0de1, GL_TEXTURE_CUBE_MAP_ARB=0x8513,
 GL_TEXTURE_CUBE_MAP_POSITIVE_X_ARB=0x8515,
 GL_TEXTURE_CUBE_MAP_NEGATIVE_X_ARB=0x8516,
 GL_TEXTURE_CUBE_MAP_NEGATIVE_Z_ARB=0x851a,
 GL_TEXTURE_WRAP_S=0x2802, GL_TEXTURE_WRAP_T=0x2803, GL_CLAMP=0x2900,
 GL_MIRRORED_REPEAT_IBM=0x8370, GL_TEXTURE_MAG_FILTER=0x2800,
 GL_TEXTURE_MIN_FILTER=0x2801, GL_NEAREST=0x2600, GL_LINEAR=0x2601,
 GL_LINEAR_MIPMAP_LINEAR=0x2703, GL_TEXTURE_MAX_ANISOTROPY_EXT=0x84fe,
 GL_RGBA8=0x8058, GL_RGB8=0x8051, GL_RGB5_A1=0x8057,
 GL_RGB5=0x8050, GL_RGBA4=0x8056, GL_RGBA=0x1908, GL_RGB=0x1907,
 GL_BGRA=0x80e1, GL_BGR=0x80e0, GL_UNSIGNED_BYTE=0x1401,
 GL_FLOAT=0x1406, GL_UNSIGNED_SHORT_1_5_5_5_REV=0x8366,
 GL_UNSIGNED_SHORT_4_4_4_4_REV=0x8365,
 GL_COMPRESSED_RGBA_S3TC_DXT1_EXT=0x83f1,
 GL_COMPRESSED_RGBA_S3TC_DXT3_EXT=0x83f2,
 GL_COMPRESSED_RGBA_S3TC_DXT5_EXT=0x83f3
};
static uint32_t requested_skip;
static int bgra_extension,marker_depth,observed_uploads;
static const uint8_t *upload_begin;
static size_t upload_bytes;
static Rgba32Oracle *observed;
static struct {int supports_anisotropy;} rdr_caps;
static struct {float texAnisotropic;} rdr_view_state={1.0f};
static int gl_clamp_val=0x812f;
#define GLEW_VERSION_1_2 0
#define GLEW_EXT_bgra bgra_extension
#define GLEW_EXT_packed_pixels 0
#define CHECKGL ((void)0)
static void Errorf(const char *format,...){(void)format;abort();}
static int texGetNumMipsToSkip(U32 width,U32 height,int for_entity){assert(width&&height&&width<=64&&height<=64&&!for_entity);return (int)requested_skip;}
static void rdrBeginMarker(const char *name){assert(name&&marker_depth==0);marker_depth=1;}
static void rdrEndMarker(void){assert(marker_depth==1);marker_depth=0;}
static void WCW_BindTexture(int target,int unit,int id){assert(marker_depth==1&&target==GL_TEXTURE_2D&&unit==0&&id==1);}
static void glTexParameterf(int target,int name,float value){assert(marker_depth==1&&target==GL_TEXTURE_2D);(void)name;(void)value;}
static void oracle_unexpected(void){assert(!"outside the bounded RGBA32 observer domain");abort();}
#define winCopyFrameBufferDirect(...) oracle_unexpected()
#define COH_Build2DMipmapsSRC(...) oracle_unexpected()
#define glCompressedTexImage2DARB(...) oracle_unexpected()
static void glTexImage2D(int target,int level,int internal,int width,int height,int border,int format,int type,const void *pixels){
 assert(observed&&marker_depth==1&&target==GL_TEXTURE_2D&&level==(int)observed->count&&observed->count<15);
 assert(internal==GL_RGBA8&&border==0&&type==GL_UNSIGNED_BYTE&&width>0&&height>0&&width<=64&&height<=64);
 assert(format==(bgra_extension?GL_BGRA:GL_RGBA));
 size_t bytes=(size_t)width*(size_t)height*4u;
 uintptr_t address=(uintptr_t)pixels,begin=(uintptr_t)upload_begin;
 assert(address>=begin&&address-begin<=upload_bytes&&bytes<=upload_bytes-(address-begin));
 assert(address-begin==observed->bytes&&bytes<=sizeof(observed->rgba)-observed->bytes);
 uint8_t *out=observed->rgba+observed->bytes;const uint8_t *in=pixels;
 if(format==GL_BGRA)for(size_t at=0;at<bytes;at+=4){out[at]=in[at+2];out[at+1]=in[at+1];out[at+2]=in[at];out[at+3]=in[at+3];}
 else memcpy(out,in,bytes);
 observed->mips[observed->count++]=(Rgba32OracleMip){(uint32_t)width,(uint32_t)height,observed->bytes,bytes};
 observed->bytes+=bytes;observed_uploads++;
}
''' + functions["ddsLoad"] + '\n' + functions["texCopyDirect"] + r'''
/* The original reader assumes successful reads and the upload loop uses <=.
 * Admit only the finite complete-chain/base-only controls before calling it;
 * this guard is not a replacement DDS decoder or a malformed-input oracle. */
static int oracle_domain(CohBytes dds,uint32_t skip){
 const uint16_t endian=1;if(*(const uint8_t*)&endian!=1)return 0;
 if(!dds.data||dds.size<128||dds.size>32768+128||memcmp(dds.data,"DDS ",4))return 0;
 DDSURFACEDESC2 wire;memcpy(&wire,dds.data+4,sizeof(wire));
 if(wire.dwSize!=124||wire.ddpfPixelFormat.dwSize!=32||!wire.dwWidth||!wire.dwHeight||wire.dwWidth>64||wire.dwHeight>64)return 0;
 if(wire.ddpfPixelFormat.dwFourCC||wire.ddpfPixelFormat.dwFlags!=DDS_RGBA||wire.ddpfPixelFormat.dwRGBBitCount!=32||wire.ddpfPixelFormat.dwRBitMask!=0x00ff0000||wire.ddpfPixelFormat.dwGBitMask!=0x0000ff00||wire.ddpfPixelFormat.dwBBitMask!=0x000000ff||wire.ddpfPixelFormat.dwRGBAlphaBitMask!=0xff000000)return 0;
 if(wire.dwDepth>1||wire.ddsCaps.dwCaps2)return 0;
 uint32_t w=wire.dwWidth,h=wire.dwHeight,maximum=0,largest=w>h?w:h;
 for(;largest;largest>>=1)maximum++;
 if(wire.dwMipMapCount&&wire.dwMipMapCount!=maximum)return 0;
 uint32_t count=wire.dwMipMapCount?wire.dwMipMapCount:1;if(skip>=count)return 0;
 size_t bytes=128;for(uint32_t i=0;i<count;i++){bytes+=(size_t)w*h*4u;w=w>1?w>>1:1;h=h>1?h>>1:1;}
 return bytes==dds.size;
}
int original_rgba32(CohBytes dds,uint32_t skip,int bgra_available,Rgba32Oracle *out){
 if(!out)return 0;
 memset(out,0,sizeof(*out));
 if((bgra_available!=0&&bgra_available!=1)||observed||!oracle_domain(dds,skip))return 0;
 FILE *file=tmpfile();if(!file)return 0;
 if(fwrite(dds.data,1,dds.size,file)!=dds.size||fflush(file)||fseek(file,0,SEEK_SET)){fclose(file);return 0;}
 requested_skip=skip;TexReadInfo info={0};
 int loaded=ddsLoad(file,&info,(int)dds.size,0,0);
 int read_ok=!ferror(file)&&ftell(file)==(long)dds.size;
 if(fclose(file))read_ok=0;
 if(!loaded||!read_ok||!info.data||info.format!=TEXFMT_ARGB_8888||info.size<=0||info.width<=0||info.height<=0||info.width>64||info.height>64||info.mip_count<0||info.mip_count>=15){free(info.data);return 0;}
 RdrTexParams *command=calloc(1,sizeof(*command)+(size_t)info.size);
 if(!command){free(info.data);return 0;}
 /* Explicit scalar queue observer for the DDS, non-JPEG, 2D setup path. It
  * copies ddsLoad outputs; no sampler/default/material policy is supplied. */
 command->width=(U16)info.width;command->height=(U16)info.height;
 command->dxtc=1;command->mipmap=info.mip_count!=0;command->mip_count=(U32)info.mip_count;
 command->id=1;command->target=GL_TEXTURE_2D;command->src_format=info.format;command->dst_format=GL_RGBA8;
 memcpy(command+1,info.data,(size_t)info.size);
 out->source_mip_count=(uint32_t)info.mip_count;out->format=(uint32_t)info.format;
 bgra_extension=bgra_available;observed=out;observed_uploads=0;
 upload_begin=(const uint8_t*)(command+1);upload_bytes=(size_t)info.size;
 texCopyDirect(command);
 assert(marker_depth==0&&observed_uploads==(int)out->count&&out->count&&out->bytes==(size_t)info.size);
 /* The extension path leaves queue bytes alone. The old GL1.1 branch must
  * have performed its own in-place red/blue swap before the RGBA observer. */
 const uint8_t *queue=(const uint8_t*)(command+1);
 for(size_t at=0;at<(size_t)info.size;at+=4){
  assert(queue[at]==info.data[at+(bgra_available?0:2)]&&queue[at+1]==info.data[at+1]);
  assert(queue[at+2]==info.data[at+(bgra_available?2:0)]&&queue[at+3]==info.data[at+3]);
 }
 observed=NULL;upload_begin=NULL;upload_bytes=0;requested_skip=0;bgra_extension=0;observed_uploads=0;
 free(command);free(info.data);return 1;
}
'''
    observers = {
        "schema": "coh-dds-rgba32-original-observers-v1",
        "whole_unchanged_functions": list(functions),
        "source_type_sha256_lf": {name: hashlib.sha256(value.encode()).hexdigest()
                                  for name, value in types.items()},
        "original_dds_pixel_flags_sha256_lf": hashlib.sha256(dds_flags.encode()).hexdigest(),
        "Win32_DWORD_LONG_LPVOID_bytes": 4,
        "Win32_DDSURFACEDESC2_bytes": 124,
        "Win32_DDPIXELFORMAT_bytes": 32,
        "original_render_command_bytes": 28,
        "original_render_command_type_unchanged": True,
        "original_TexReadInfo_and_format_enum_unchanged": True,
        "ddsLoad_needRawData": 0,
        "ddsLoad_forEntity": 0,
        "texGetNumMipsToSkip_observer": "exact requested skip; no Game graphics settings",
        "bounded_oracle_domain": "canonical tightly packed BGRA32, 1..64 dimensions, complete terminating chain or count-zero base only",
        "file_observer": "bounded input copied to a private tmpfile; original fread/fseek execute",
        "queue_observer": "copied original DDS info fields into original RdrTexParams followed by copied bytes; no material or sampler admission",
        "GLEW_VERSION_1_2_observed": False,
        "GLEW_EXT_bgra_observed": "caller capability Boolean, both values tested by caller",
        "GLEW_EXT_packed_pixels_observed": False,
        "GL_observer": "ordered per-mip upload metadata and GL_BGRA or GL_RGBA interpretation; no GL calls execute",
        "legacy_fallback_in_place_red_blue_swap_checked": True,
        "unexercised_format_framebuffer_generated_mipmap_branches": "explicit aborting observers",
        "actual_GL_or_GPU_executed": False,
        "current_namespace_default_material_world_authority": False,
    }
    return code, functions, observers

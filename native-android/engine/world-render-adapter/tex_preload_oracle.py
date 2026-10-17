"""Original GetTex producer/CLIENT consumer with explicit wire/storage/render observers."""
from pathlib import Path

def create(root,extract):
 root=Path(root);tex=(root/'upstream/ouroboros/Game/src/render/tex.c').read_text();header=(root/'upstream/ouroboros/Game/src/render/tex.h').read_text();gettex=(root/'upstream/ouroboros/Utilities/GetTex/src/gettex.c').read_text();gl=(root/'upstream/ouroboros/3rdparty/cg/include/GL/glext.h').read_text();dd=(root/'upstream/ouroboros/Game/src/render/dd.h').read_text()
 a=header.index('typedef struct {');b=header.index('} TextureFileMipHeader;',a)+len('} TextureFileMipHeader;');types=header[a:b];a=header.index('typedef struct TexReadInfo');b=header.index('};',a)+2;types+='\n'+header[a:b]
 constants='\n'.join(line for line in gl.splitlines() if line.startswith(('#define GL_COMPRESSED_RGBA_S3TC_DXT1_EXT','#define GL_COMPRESSED_RGBA_S3TC_DXT3_EXT','#define GL_COMPRESSED_RGBA_S3TC_DXT5_EXT')))
 constants+='\n'+'\n'.join(line for line in header.splitlines() if line.startswith(('#define DDS_RGB\t','#define DDS_RGBA',' #define DDS_RGB')) or line.startswith('#define DDS_RGB '))
 # MAKEFOURCC is copied verbatim with its original BYTE/DWORD width observers.
 constants+='\n'+dd[dd.index('#ifndef MAKEFOURCC'):dd.index('typedef struct DDCOLORKEY')]
 blocks={name:extract(source,sig) for name,source,sig in [('count_gettex',gettex,'static int countMipMapLevels('),('writeMipMapHeader',gettex,'static void writeMipMapHeader('),('texBindLowMips',tex,'static void texBindLowMips('),('texGetFormat',tex,'int texGetFormat('),('texFindNeededBinds',tex,'static void texFindNeededBinds()\n{')]}
 code=r'''#include "tests/tex_preload_fixture.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <setjmp.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
typedef uint8_t U8;typedef float F32;typedef uint32_t TexOptFlags,DWORD;typedef uint8_t BYTE;
'''+constants+'\n'+types+r'''
/* Win32 DDS124-byte WIRE observer, not original host/runtime pointer ABI. */
typedef struct{uint32_t dwSize,dwFlags,dwFourCC,dwRGBBitCount,dwRBitMask,dwGBitMask,dwBBitMask,dwRGBAlphaBitMask;}Pixel;
typedef struct{uint32_t dwSize,dwFlags,dwHeight,dwWidth,dwLinearSize,dwDepth,dwMipMapCount,reserved[11];Pixel ddpfPixelFormat;uint32_t caps[5];}DDSURFACEDESC2;
_Static_assert(sizeof(TextureFileHeader)==32&&sizeof(TextureFileMipHeader)==16&&sizeof(DDSURFACEDESC2)==124,"source wire sizes");
_Static_assert(offsetof(DDSURFACEDESC2,dwWidth)==12&&offsetof(DDSURFACEDESC2,dwMipMapCount)==24&&offsetof(DDSURFACEDESC2,ddpfPixelFormat)==72,"DDS wire fields");
static void Errorf(const char*s,...){(void)s;abort();}static void*compatibleGetConsoleWindow(void){abort();}static void msgAlert(void*w,const char*s){(void)w;(void)s;abort();}
'''+blocks['count_gettex']+blocks['writeMipMapHeader']+r'''
typedef struct{uint8_t*mipdata;int mipsize,mipid;uint32_t texopt_flags,flags;}BasicTexture;
typedef struct{int id;}RdrTexParams;
static PreloadPacket*packet;static int copies;
static int rdrAllocTexHandle(void){return 101;} /* symbolic observer, no GPU */
static void texSetupParamsFromBind(BasicTexture*b,TexReadInfo*i,RdrTexParams*r){(void)b;memset(r,0,sizeof(*r));packet->width=(uint32_t)i->width;packet->height=(uint32_t)i->height;packet->levels=(uint32_t)i->mip_count;packet->format=(uint32_t)i->format;}
static void rdrTexCopy(RdrTexParams*r,const void*p,int n){assert(r->id==101&&n>=0&&n<=1024);packet->bytes=(size_t)n;memcpy(packet->data,p,(size_t)n);copies++;}
#define TEXOPT_JPEG (1u<<17)
#define GL_RGB8 0x8051
#define GL_RGBA8 0x8058
'''+blocks['texBindLowMips']+blocks['texGetFormat']+r'''
static BasicTexture*white_tex,*grey_tex,*invisible_tex,*black_tex,*dummy_bump_tex,*dummy_dynamic_cubemap_tex,*building_lights_tex;
#define TEX_ALPHA 1
#define devassert(x) assert(x)
static jmp_buf default_unknown;static char*default_key;
static BasicTexture*texFind(const char*key){assert(strlen(key)<128);strcpy(default_key,key);longjmp(default_unknown,1);}
'''+blocks['texFindNeededBinds']+r'''
size_t original_preload_write(CohBytes dds,uint8_t out[1024]){assert(dds.size<=1024*1024);char*aligned=malloc(dds.size);assert(aligned);memcpy(aligned,dds.data,dds.size);FILE*f=tmpfile();assert(f);TextureFileHeader tfh;memset(&tfh,0,sizeof(tfh));writeMipMapHeader(f,aligned,(int)dds.size,&tfh);assert(tfh.header_size>=0&&tfh.header_size<=1024);rewind(f);assert(fread(out,1,(size_t)tfh.header_size,f)==(size_t)tfh.header_size);assert(fgetc(f)==EOF&&!fclose(f));free(aligned);return(size_t)tfh.header_size;}
void original_preload_consume(CohBytes raw,PreloadPacket*out){assert(raw.size>=16&&raw.size<=1024);uint8_t*aligned=malloc(raw.size);assert(aligned);memcpy(aligned,raw.data,raw.size);BasicTexture basic;memset(&basic,0,sizeof(basic));basic.mipdata=aligned;basic.mipsize=(int)raw.size;packet=out;copies=0;memset(out,0,sizeof(*out));texBindLowMips(&basic);assert(copies==1&&basic.mipid==101&&texGetFormat(&basic)==(int)out->format);free(aligned);packet=NULL;}
void original_defaults_unknown(char out[128]){default_key=out;out[0]=0;if(!setjmp(default_unknown)){texFindNeededBinds();abort();}assert(!strcmp(out,"white"));default_key=NULL;}
'''
 return code,blocks,types

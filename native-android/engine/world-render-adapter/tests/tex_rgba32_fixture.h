#ifndef TEX_RGBA32_FIXTURE_H
#define TEX_RGBA32_FIXTURE_H
#include "../coh_wr_tex_rgba32.h"
typedef struct {uint32_t width,height;size_t offset,bytes;} Rgba32OracleMip;
typedef struct {
 uint32_t count,source_mip_count,format;
 size_t bytes;
 Rgba32OracleMip mips[15];
 uint8_t rgba[32768];
} Rgba32Oracle;
int original_rgba32(CohBytes,uint32_t skip,int bgra_available,Rgba32Oracle*);
#endif

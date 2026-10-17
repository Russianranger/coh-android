#ifndef TEX_PRELOAD_FIXTURE_H
#define TEX_PRELOAD_FIXTURE_H
#include "../coh_wr_tex_preload.h"
typedef struct{uint32_t width,height,levels,format;size_t bytes;uint8_t data[1024];}PreloadPacket;
size_t original_preload_write(CohBytes,uint8_t[1024]);
void original_preload_consume(CohBytes,PreloadPacket*);
void original_defaults_unknown(char[128]);
#endif

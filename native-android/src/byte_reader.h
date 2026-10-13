#ifndef COH_BYTE_READER_H
#define COH_BYTE_READER_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <float.h>
_Static_assert(sizeof(float)==4 && FLT_RADIX==2 && FLT_MANT_DIG==24,"binary32 required");
static inline uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static inline uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static inline void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static inline float f32(const uint8_t *p){uint32_t v=u32(p);float f;memcpy(&f,&v,4);return f;}
static inline int span(size_t bytes,size_t offset,size_t count,size_t stride){return offset<=bytes && (!stride || count<=(bytes-offset)/stride);}
#endif

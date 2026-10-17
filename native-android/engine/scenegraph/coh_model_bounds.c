#include "coh_model_bounds.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const uint8_t *p){uint32_t v=u32(p);float out;memcpy(&out,&v,4);return out;}
static int span(size_t n,size_t at,size_t bytes){return at<=n&&bytes<=n-at;}
static int disjoint(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int numbers_ok(const CohModelBoundsNumbers *b){for(unsigned n=0;n<3;n++)if(!isfinite(b->min[n])||!isfinite(b->max[n])||!isfinite(b->scale[n])||b->min[n]>b->max[n])return 0;return isfinite(b->radius)&&b->radius>=0;}
static int table_ok(const CohModelBoundsTable *t){
    if(!t->header.data||!t->header.size||t->header.size>COH_MODEL_BOUNDS_HEADER_MAX||!t->names.data||!t->names.size||!t->models||t->models>COH_MODEL_BOUNDS_MODELS_MAX||t->records_offset>t->header.size)return 0;
    if(t->version!=0&&t->version!=2&&t->version!=3&&t->version!=4&&t->version!=5&&t->version!=7&&t->version!=8)return 0;
    uintptr_t h=(uintptr_t)t->header.data,n=(uintptr_t)t->names.data;
    if(t->header.size>UINTPTR_MAX-h||n<h||n-h>t->header.size||t->names.size>t->header.size-(n-h))return 0;
    return 1;
}
static CohStatus row(const CohModelBoundsTable *t,size_t at,uint32_t index,CohModelBoundsView *out){
    if(!span(t->header.size,at,4))return COH_INVALID;
    size_t bytes=t->version<3?216u:u32(t->header.data+at);
    if(bytes<204||bytes>4096||!span(t->header.size,at,bytes))return COH_INVALID;
    const uint8_t *p=t->header.data+at;size_t scale=t->version<3?92u:t->version==8?72u:68u;
    size_t nameoff=t->version<3?80u:t->version==8?64u:60u;uint32_t name=u32(p+nameoff);
    if(name>=t->names.size)return COH_INVALID;
    size_t len=0;const char *s=(const char*)t->names.data+name;
    while(len<t->names.size-name&&len<256u&&s[len]){unsigned c=(unsigned char)s[len];if(c<32||c>126)return COH_INVALID;len++;}
    if(!len||len==256u||len==t->names.size-name)return COH_INVALID;
    CohModelBoundsView v={0};for(unsigned n=0;n<3;n++){v.numbers.scale[n]=f32(p+scale+4*n);v.numbers.min[n]=f32(p+scale+12+4*n);v.numbers.max[n]=f32(p+scale+24+4*n);}v.numbers.radius=f32(p+4);
    if(!numbers_ok(&v.numbers))return COH_INVALID;
    v.name=s;v.record=(CohBytes){p,bytes};v.disk_row=index;*out=v;return COH_OK;
}
CohStatus coh_model_bounds_open(CohBytes header,uint32_t version,CohModelBoundsTable *out){
    if(!out||!header.data||header.size>COH_MODEL_BOUNDS_HEADER_MAX)return COH_INVALID;
    if(!disjoint(out,sizeof(*out),header.data,header.size))return COH_INVALID;
    if(version!=0&&version!=2&&version!=3&&version!=4&&version!=5&&version!=7&&version!=8)return COH_UNSUPPORTED;
    size_t fields=version>=2&&version<=6?5u:4u,at=fields*4;
    if(header.size<at)return COH_INVALID;
    CohModelBoundsTable t={0};t.header=header;t.version=version;
    for(unsigned n=0;n<3;n++){size_t bytes=u32(header.data+4+4*n);if(!span(header.size,at,bytes))return COH_INVALID;if(n==1)t.names=(CohBytes){header.data+at,bytes};at+=bytes;}
    if(fields==5){size_t bytes=u32(header.data+16);if(!span(header.size,at,bytes))return COH_INVALID;at+=bytes;}
    if(!span(header.size,at,140))return COH_INVALID;
    t.models=u32(header.data+at+136);t.records_offset=at+140;
    if(!t.models||t.models>COH_MODEL_BOUNDS_MODELS_MAX)return COH_LIMIT;
    at=t.records_offset;
    for(uint32_t n=0;n<t.models;n++){CohModelBoundsView v;CohStatus status=row(&t,at,n,&v);if(status!=COH_OK)return status;at+=v.record.size;}
    if(at!=header.size)return COH_INVALID;
    *out=t;return COH_OK;
}
CohStatus coh_model_bounds_begin(const CohModelBoundsTable *table,CohModelBoundsCursor *out){
    if(!table||!out||!table_ok(table))return COH_INVALID;
    if(!disjoint(table,sizeof(*table),out,sizeof(*out))||!disjoint(table->header.data,table->header.size,out,sizeof(*out)))return COH_INVALID;
    *out=(CohModelBoundsCursor){*table,table->records_offset,0};return COH_OK;
}
CohStatus coh_model_bounds_next(CohModelBoundsCursor *cursor,CohModelBoundsView *out){
    if(!cursor||!out||!table_ok(&cursor->table))return COH_INVALID;
    if(!disjoint(cursor,sizeof(*cursor),out,sizeof(*out))||!disjoint(cursor,sizeof(*cursor),cursor->table.header.data,cursor->table.header.size)||!disjoint(out,sizeof(*out),cursor->table.header.data,cursor->table.header.size))return COH_INVALID;
    if(cursor->row>=cursor->table.models)return cursor->row==cursor->table.models&&cursor->offset==cursor->table.header.size?COH_NOT_FOUND:COH_INVALID;
    CohModelBoundsView v;CohStatus status=row(&cursor->table,cursor->offset,cursor->row,&v);if(status!=COH_OK)return status;
    cursor->offset+=v.record.size;cursor->row++;*out=v;return COH_OK;
}
CohStatus coh_model_bounds_compare(const CohModelBoundsNumbers *source,const CohModelBoundsNumbers *disk,uint32_t *out){
    if(!source||!disk||!out)return COH_INVALID;
    if(!disjoint(source,sizeof(*source),out,sizeof(*out))||!disjoint(disk,sizeof(*disk),out,sizeof(*out))||!numbers_ok(source)||!numbers_ok(disk))return COH_INVALID;
    uint32_t mask=0;const float *a[]={source->min,source->max,source->scale,&source->radius},*b[]={disk->min,disk->max,disk->scale,&disk->radius};
    for(unsigned group=0;group<4;group++)for(unsigned n=0;n<(group==3?1u:3u);n++){uint32_t x,y;memcpy(&x,a[group]+n,4);memcpy(&y,b[group]+n,4);if(x!=y)mask|=1u<<(3u*group+n);}
    *out=mask;return COH_OK;
}

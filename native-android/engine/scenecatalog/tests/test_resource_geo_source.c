#include "../coh_resource_geo_source.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check%u line%d failed: %s\n",checks,__LINE__,#x);exit(2);}}while(0)
extern unsigned original_read_model_compare(CohBytes,const CohAssetGeo *,uint32_t,const CohAssetGeoModel *);
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(uint8_t*p,uint32_t n){for(unsigned k=0;k<4;k++)p[k]=(uint8_t)(n>>(8*k));}
static void refuse(CohBytes raw,uint8_t *workspace,size_t cap){CohAssetGeo out,before;memset(&out,0xa5,sizeof(out));before=out;uint32_t zero=0x12345678;CHECK(coh_resource_geo_source_open(raw,workspace,cap,65536,&out,&zero)!=COH_OK);CHECK(!memcmp(&out,&before,sizeof(out))&&zero==0x12345678);}
static void mutate(const CohAssetGeo *g,size_t offset,uint32_t value,uint8_t *workspace,size_t cap){
 uint8_t *h=malloc(g->header.size);CHECK(h);memcpy(h,g->header.data,g->header.size);put(h+offset,value);uLongf packed=compressBound((uLong)g->header.size);uint8_t *b=malloc(16+packed+g->payload.size);CHECK(b);CHECK(compress2(b+16,&packed,h,(uLong)g->header.size,Z_BEST_SPEED)==Z_OK);put(b,(uint32_t)packed+12);put(b+4,0);put(b+8,8);put(b+12,(uint32_t)g->header.size);memcpy(b+16+packed,g->payload.data,g->payload.size);refuse((CohBytes){b,16+packed+g->payload.size},workspace,cap);free(b);free(h);
}
int main(int argc,char **argv){CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long bytes=ftell(f);CHECK(bytes>0&&bytes<16*1024*1024);rewind(f);uint8_t *raw=malloc((size_t)bytes);CHECK(raw);CHECK(fread(raw,1,(size_t)bytes,f)==(size_t)bytes);CHECK(!fclose(f));size_t cap;CHECK(coh_asset_geo_workspace((CohBytes){raw,(size_t)bytes},&cap)==COH_OK);uint8_t *workspace=malloc(cap),*scratch=malloc(cap);CHECK(workspace&&scratch);CohAssetGeo g;uint32_t zero=99;
 CHECK(coh_asset_geo_open((CohBytes){raw,(size_t)bytes},workspace,cap,65536,&g)==COH_INVALID);
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},workspace,cap,65536,&g,&zero)==COH_OK);CHECK(zero==4&&g.model_count==72&&g.version==8);
 /* Known output/control/source aliases must refuse before any workspace write. */
 memset(scratch,0x5a,cap);uint8_t *save=malloc(cap);CHECK(save);memcpy(save,scratch,cap);
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},scratch,cap,65536,(CohAssetGeo*)scratch,&zero)==COH_INVALID);CHECK(!memcmp(save,scratch,cap));
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},scratch,cap,65536,&g,(uint32_t*)scratch)==COH_INVALID);CHECK(!memcmp(save,scratch,cap));
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},scratch,cap,65536,&g,(uint32_t*)&g)==COH_INVALID);CHECK(!memcmp(save,scratch,cap));
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},scratch,cap,65536,(CohAssetGeo*)raw,&zero)==COH_INVALID);CHECK(!memcmp(save,scratch,cap));
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},raw,(size_t)bytes,65536,&g,&zero)==COH_INVALID);
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},scratch,cap,65536,&g,(uint32_t*)raw)==COH_INVALID);CHECK(!memcmp(save,scratch,cap));
 CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)bytes},(uint8_t*)(UINTPTR_MAX-8),32,65536,&g,&zero)==COH_INVALID);
 CHECK(coh_resource_geo_source_open((CohBytes){(uint8_t*)(UINTPTR_MAX-8),32},scratch,cap,65536,&g,&zero)==COH_INVALID);
 CohAssetGeoModel aliasmodel;CHECK(coh_resource_geo_source_model(&g,0,&aliasmodel,(uint32_t*)&aliasmodel)==COH_INVALID);
 CHECK(coh_resource_geo_source_model(&g,0,(CohAssetGeoModel*)g.header.data,&zero)==COH_INVALID);
 CHECK(coh_resource_geo_source_model(&g,0,&aliasmodel,(uint32_t*)g.header.data)==COH_INVALID);free(save);
 size_t at=g.records_offset;unsigned empty=0;size_t firstempty=0;
 for(uint32_t k=0;k<g.model_count;k++){uint32_t n=u32(g.header.data+at);CohAssetGeoModel m;uint32_t iszero=99;CHECK(coh_resource_geo_source_model(&g,k,&m,&iszero)==COH_OK);checks+=original_read_model_compare((CohBytes){g.header.data+at,n},&g,k,&m);if(iszero){empty++;if(!firstempty)firstempty=at;CHECK(!m.vertex_count&&!m.triangle_count&&!m.material_count);CHECK(m.pack_count==10&&m.packs[7].packed_bytes&&m.packs[8].packed_bytes);CHECK(coh_asset_geo_model(&g,k,&m)==COH_INVALID);}else{CohAssetGeoModel protected;CHECK(coh_asset_geo_model(&g,k,&protected)==COH_OK);CHECK(!strcmp(m.name,protected.name)&&m.vertex_count==protected.vertex_count);}at+=n;}
 CHECK(empty==4&&at==g.header.size);
 for(size_t n=0;n<128;n++)refuse((CohBytes){raw,n},scratch,cap);
 for(size_t n=1;n<=64;n++)refuse((CohBytes){raw,(size_t)bytes-n},scratch,cap);
 refuse((CohBytes){raw,(size_t)bytes},scratch,cap-1);
 for(unsigned k=0;k<7;k++)mutate(&g,firstempty+108+12*k,1,scratch,cap);
 mutate(&g,firstempty+108+12*9,1,scratch,cap);mutate(&g,firstempty+12,4,scratch,cap);mutate(&g,firstempty+16,1,scratch,cap);mutate(&g,firstempty+20,1,scratch,cap);mutate(&g,firstempty+8,1,scratch,cap);mutate(&g,firstempty+24,1,scratch,cap);mutate(&g,firstempty+32,1,scratch,cap);mutate(&g,firstempty+64,UINT32_MAX,scratch,cap);mutate(&g,firstempty+68,UINT32_MAX,scratch,cap);mutate(&g,firstempty+72,0x7fc00000u,scratch,cap);mutate(&g,firstempty+84,0x7fc00000u,scratch,cap);mutate(&g,firstempty+108+7*12+8,UINT32_MAX,scratch,cap);mutate(&g,firstempty+108+8*12+8,UINT32_MAX,scratch,cap);
 /* An ordinary malformed record remains rejected even if other rows are empty. */
 mutate(&g,g.records_offset+16,0,scratch,cap);mutate(&g,g.records_offset+64,UINT32_MAX,scratch,cap);mutate(&g,0,(uint32_t)g.payload.size+1,scratch,cap);mutate(&g,g.records_offset,0,scratch,cap);
 free(scratch);free(workspace);free(raw);printf("{\"passed\":true,\"checks\":%u,\"source_models\":72,\"zero_draw_models\":4,\"draw_authority\":false}\n",checks);return 0;
}

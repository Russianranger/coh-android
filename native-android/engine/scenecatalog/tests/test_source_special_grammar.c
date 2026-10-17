/* Synthetic borrowed-lease grammar controls ONLY. This stub bypasses real Body
 * admission intentionally; it cannot qualify source identity/generation. */
#include "../coh_source_special.h"
#include "../coh_resource_geo_source.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;static CohSourceBodyLease fake;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"special grammar%d %s\n",__LINE__,#x);abort();}}while(0)
CohStatus coh_source_body_lease(const CohSourceBody*b,uint32_t n,CohSourceBodyLease*out){(void)b;(void)n;*out=fake;return COH_OK;}
static uint32_t get(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(uint8_t*p,uint32_t n){for(unsigned k=0;k<4;k++)p[k]=(uint8_t)(n>>(k*8));}
static void refuses(void*w,size_t cap,CohStatus expected){CohSourceSpecial out,prior;memset(&out,0xa5,sizeof(out));prior=out;CohSourceSpecialBudget b={96u<<20,262144};CHECK(coh_source_special_prepare((const CohSourceBody*)&fake,0,w,cap,&b,(CohCancel){0},&out)==expected);CHECK(!memcmp(&out,&prior,sizeof(out)));}
int main(int argc,char**argv){CHECK(argc==3);FILE*f=fopen(argv[1],"rb");CHECK(f&&!fseek(f,0,SEEK_END));long size=ftell(f);CHECK(size>0);rewind(f);uint8_t*raw=malloc((size_t)size);CHECK(raw&&fread(raw,1,(size_t)size,f)==(size_t)size&&!fclose(f));size_t required;CHECK(coh_asset_geo_workspace((CohBytes){raw,(size_t)size},&required)==COH_OK);uint8_t*header=malloc(required),*w=malloc(512u<<10);CHECK(header&&w);CohAssetGeo geo;uint32_t zeros;CHECK(coh_resource_geo_source_open((CohBytes){raw,(size_t)size},header,required,65536,&geo,&zeros)==COH_OK);uint32_t row=(uint32_t)strtoul(argv[2],NULL,10);CohAssetGeoModel model;CHECK(coh_asset_geo_model(&geo,row,&model)==COH_OK);size_t at=geo.records_offset;for(uint32_t k=0;k<row;k++)at+=geo.version?get(header+at):216u;
 memset(&fake,0,sizeof(fake));fake.actual_sources.header=geo.header;fake.actual_sources.blob=(CohBytes){raw,(size_t)size};fake.model.geo_version=geo.version;fake.model.geo_disk_row=row;fake.model.model=model;
 CohSourceSpecialBudget budget={96u<<20,262144};CohSourceSpecial out;CHECK(coh_source_special_prepare((const CohSourceBody*)&fake,0,w,512u<<10,&budget,(CohCancel){0},&out)==COH_OK);
 if(geo.version==8){
  uint32_t count=get(header+at+24);put(header+at+24,0);refuses(w,512u<<10,COH_INVALID);put(header+at+24,257);refuses(w,512u<<10,COH_LIMIT);put(header+at+24,count);
  CohPack32 old=fake.model.model.packs[9];fake.model.model.packs[9].unpacked_bytes=0;refuses(w,512u<<10,COH_INVALID);fake.model.model.packs[9]=old;fake.model.model.packs[9].unpacked_bytes=COH_SOURCE_SPECIAL_MAX_STREAM+1;refuses(w,512u<<10,COH_LIMIT);fake.model.model.packs[9]=old;
  /* Out-of-range stored channel and malformed original delta grammar. */
  fake.model.model.packs[9].offset=UINT32_MAX;refuses(w,512u<<10,COH_INVALID);fake.model.model.packs[9]=old;
  size_t payload=(size_t)get(raw)+4;uint8_t*stream=raw+payload+old.offset;uint8_t saved[52];CHECK(payload+old.offset+52<=(size_t)size);memcpy(saved,stream,52);memset(stream,0,52);stream[0]=stream[1]=stream[2]=255;put(stream+4,0x7fc00000);put(header+at+24,1);fake.model.model.packs[9].packed_bytes=0;fake.model.model.packs[9].unpacked_bytes=52;refuses(w,512u<<10,COH_INVALID);memcpy(stream,saved,52);put(header+at+24,count);fake.model.model.packs[9]=old;
 }else if(get(header+at+84)){
  uint32_t offset=get(header+at+84);size_t payload=(size_t)get(raw)+8;uint8_t*p=raw+payload+offset;uint32_t count=get(p),first=get(p+4);put(p,16);refuses(w,512u<<10,COH_INVALID);put(p,count);put(p+4,0x7f800000);refuses(w,512u<<10,COH_INVALID);put(p+4,first);put(header+at+84,UINT32_MAX);refuses(w,512u<<10,COH_INVALID);put(header+at+84,offset);
 }
 CohBytes saved=fake.actual_sources.blob;fake.actual_sources.blob.size=8;refuses(w,512u<<10,COH_INVALID);fake.actual_sources.blob=saved;fake.model.geo_version=7;refuses(w,512u<<10,COH_UNSUPPORTED);
 free(w);free(header);free(raw);printf("{\"passed\":true,\"synthetic_grammar_only\":true,\"checks\":%u}\n",checks);return 0;
}

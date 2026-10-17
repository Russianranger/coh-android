/* Authentic cached texture decoding; NO effective CLIENT material admission. */
#include "../../assets/coh_asset_loader.h"
#include "../../../include/coh_native_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"texture line%d\n",__LINE__);exit(1);}}while(0)
int main(int argc,char**argv){
 CHECK(argc==3);FILE*f=fopen(argv[1],"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n==43990);rewind(f);
 unsigned char*bytes=malloc((size_t)n);CHECK(bytes);CHECK(fread(bytes,1,(size_t)n,f)==(size_t)n);CHECK(!fclose(f));
 CohAssetTexture t;CHECK(coh_asset_texture((CohBytes){bytes,(size_t)n},&t)==COH_OK);
 CHECK(t.name&&strstr(t.name,"Box-1"));CohDdsMip m;CHECK(!coh_dds_mip(t.dds.data,t.dds.size,0,&m));unsigned levels=m.mip_count;
 f=fopen(argv[2],"wb");CHECK(f);
 for(unsigned i=0;i<levels;i++){
   CHECK(!coh_dds_mip(t.dds.data,t.dds.size,i,&m));unsigned char*rgba=malloc(m.rgba_bytes);CHECK(rgba);
   CHECK(coh_asset_texture_rgba(&t,i,rgba,m.rgba_bytes)==COH_OK);CHECK(fwrite(rgba,1,m.rgba_bytes,f)==m.rgba_bytes);free(rgba);
 }
 CHECK(!fclose(f));
 CohAssetTexture old=t;CHECK(coh_asset_texture((CohBytes){bytes,32},&t)!=COH_OK);CHECK(!memcmp(&old,&t,sizeof(t)));
 printf("{\"passed\":true,\"checks\":%u,\"width\":%u,\"height\":%u,\"levels\":%u,\"cached_texopt_flags\":%u,\"format\":%u,\"material_authority\":false}\n",checks,t.width,t.height,levels,t.flags,m.format);free(bytes);
}

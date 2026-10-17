/* Read-only host metadata diagnostic; no decoded CPU/material/world permit. */
#include "coh_resource_geo_source.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void name(const char*s){putchar('"');for(;*s;s++){unsigned char c=(unsigned char)*s;if(c=='"'||c=='\\')putchar('\\');if(c<32||c>126)exit(2);putchar(c);}putchar('"');}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f||fseek(f,0,SEEK_END))return 2;long n=ftell(f);if(n<=0||n>16*1024*1024)return 2;rewind(f);uint8_t*raw=malloc((size_t)n);if(!raw||fread(raw,1,(size_t)n,f)!=(size_t)n||fclose(f))return 2;
 size_t wn;CohBytes bytes={raw,(size_t)n};if(coh_asset_geo_workspace(bytes,&wn)!=COH_OK||wn>16*1024*1024)return 2;uint8_t*w=malloc(wn);CohAssetGeo g;uint32_t zeros;if(!w||coh_resource_geo_source_open(bytes,w,wn,65536,&g,&zeros)!=COH_OK)return 2;
 size_t at=g.records_offset;for(uint32_t i=0;i<g.model_count;i++){
  if(at>g.header.size||g.header.size-at<(g.version<3?216u:4u))return 2;
  size_t size=g.version<3?216u:u32(g.header.data+at);if(size<4||size>g.header.size-at)return 2;
  CohAssetGeo one=g;one.records_offset=at;one.model_count=1;CohAssetGeoModel m;uint32_t zero;if(coh_resource_geo_source_model(&one,0,&m,&zero)!=COH_OK)return 2;
  uint32_t legacy_invalid=0,legacy_flags=0,legacy_alternate=0,reflection=0,alternate=0;
  if(g.version<3){const uint8_t*p=g.header.data+at;legacy_invalid=!!(u32(p+24)||u32(p+40)||u32(p+72)||u32(p+76)||u32(p+88));legacy_flags=u32(p);legacy_alternate=u32(p+84);}else{CohGeoModel meta;if(coh_geo_model(g.header.data+at,g.header.size-at,g.version,&meta))return 2;reflection=meta.reflection_count;alternate=meta.alternate_pivot_offset;}
  printf("{\"row\":%u,\"version\":%u,\"name\":",i,g.version);name(m.name);printf(",\"zero\":%u,\"vertices\":%u,\"triangles\":%u,\"parts\":%u,\"bone_info\":%u,\"unit_scale\":%s,\"legacy_invalid_pointers\":%u,\"legacy_flags\":%u,\"legacy_alternate\":%u,\"reflections\":%u,\"alternate\":%u,\"packs\":[",zero,m.vertex_count,m.triangle_count,m.material_count,m.bone_info_offset,m.scale[0]==1.f&&m.scale[1]==1.f&&m.scale[2]==1.f?"true":"false",legacy_invalid,legacy_flags,legacy_alternate,reflection,alternate);
  for(unsigned k=0;k<10;k++){printf("%s%u",k?",":"",m.packs[k].unpacked_bytes);}
  puts("]}");at+=size;
 }
 if(at!=g.header.size)return 2;
 free(w);free(raw);return 0;
}

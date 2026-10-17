/* Inspection-only fixed-seven driver. No namespace or default object is made. */
#include "coh_wr_tex_inputs.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {uint8_t*data;size_t size;}Body;
static const char*paths[7]={"data/texture_library/world/filler/white.texture","data/texture_library/world/filler/grey.texture","data/texture_library/world/world_fx/portal/invisible.texture","data/texture_library/world/filler/black.texture","data/texture_library/btest/dummy_bump.texture","data/texture_library/static_cubemaps/dummy_dynamic/dummy_dynamic_cubemap_face0.texture","data/texture_library/btest/buildinglightpattern.texture"};
static CohStatus readat(void*v,uint64_t at,void*out,size_t n){Body*b=v;if(at>b->size||n>b->size-at)return COH_IO;memcpy(out,b->data+(size_t)at,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static int body(const char*path,Body*b){FILE*f=fopen(path,"rb");if(!f)return 0;if(fseek(f,0,SEEK_END)){fclose(f);return 0;}long n=ftell(f);if(n<=0||n>16384){fclose(f);return 0;}rewind(f);b->data=malloc((size_t)n);b->size=(size_t)n;int ok=b->data&&fread(b->data,1,b->size,f)==b->size;return fclose(f)==0&&ok;}
static void hex(const uint8_t*h){for(unsigned i=0;i<32;i++)printf("%02x",h[i]);}
int main(int argc,char**argv){
 if(argc!=8)return 2;
 Body bodies[7]={{0}};CohWrTexInputPin pins[7];CohAssetTexture parsed[7];CohStatus statuses[7];int result=2,all=1;CohAssetLoader*loader=NULL;CohWrTexInputs*owner=NULL;
 for(unsigned i=0;i<7;i++){if(!body(argv[i+1],bodies+i))goto done;pins[i].asset=(CohAssetId){paths[i],1};SHA256(bodies[i].data,bodies[i].size,pins[i].sha256);statuses[i]=coh_asset_texture((CohBytes){bodies[i].data,bodies[i].size},parsed+i);if(statuses[i]!=COH_OK)all=0;}
 /* Label1 is this short-lived inspection invocation only, not a provider or
  * current CLIENT generation. The source bytes are separately hash admitted. */
 CohAssetLimits limits={262144,131072,16384,16384,7,7,7};if(coh_asset_create(&limits,&loader)!=COH_OK)goto done;
 for(unsigned i=0;i<7;i++)if(coh_asset_mount_file(loader,paths[i],(CohAssetSource){readat,bodies+i,bodies[i].size,1})!=COH_OK)goto done;
 CohStatus owner_status=COH_STATE;CohWrTexInputsReport report;memset(&report,0,sizeof(report));
 if(all){CohWrTexInputsRequest request={pins,NULL,7,0,1,digest,NULL};CohWrTexInputsLimits admission={32768,524288,262144,65536};owner_status=coh_wr_tex_inputs_build(loader,&request,&admission,(CohCancel){0},&owner);if(owner_status==COH_OK&&coh_wr_tex_inputs_report(owner,&report)!=COH_OK)goto done;}
 printf("{\"schema\":\"coh-fixed-seven-header-inspection-v1\",\"inspection_label_only\":1,\"rows\":[");
 for(unsigned i=0;i<7;i++){
  if(i){printf(",");}printf("{\"ordinal\":%u,\"bytes\":%zu,\"sha256\":\"",i,bodies[i].size);hex(pins[i].sha256);printf("\",\"protected_parser_status\":%u",(unsigned)statuses[i]);
  if(statuses[i]==COH_OK)printf(",\"width\":%u,\"height\":%u,\"cached_flags\":%u,\"cached_alpha\":%u",parsed[i].width,parsed[i].height,parsed[i].flags,(unsigned)parsed[i].alpha);
  if(owner){CohWrTexHeaderInput h;if(coh_wr_tex_inputs_header(owner,i,&h)!=COH_OK)goto done;printf(",\"owner_header_ordinal\":%u",h.input_ordinal);}printf("}");
 }
 printf("],\"seven_header_owner_attempted\":%s,\"seven_header_owner_status\":%u,\"seven_header_owner_created\":%s,\"owner_bytes\":%zu,\"loader_reservation\":%zu,\"aggregate_reserved_bytes\":%zu,\"owner_retired_before_exit\":true,\"current_provider_generation\":false,\"namespace_complete\":false,\"default_identity\":false,\"GPU\":false}\n",all?"true":"false",(unsigned)owner_status,owner?"true":"false",report.owned_bytes,report.loader_reservation,report.aggregate_reserved_bytes);result=0;
done:
 coh_wr_tex_inputs_release(&owner);if(loader&&coh_asset_destroy(&loader)!=COH_OK)result=2;for(unsigned i=0;i<7;i++)free(bodies[i].data);return result;
}

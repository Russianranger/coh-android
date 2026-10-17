#include "coh_wr_texopt.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/sha.h>
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"tex10499 line%d %s\n",__LINE__,#x);exit(1);}}while(0)
static unsigned checks;
void*__real_calloc(size_t,size_t);void*__wrap_calloc(size_t n,size_t s){return __real_calloc(n,s);}
typedef struct{uint8_t*data;size_t size;}Source;
static Source file(const char*name){FILE*f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<16*1024*1024);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data);CHECK(fread(s.data,1,s.size,f)==s.size);CHECK(!fclose(f));return s;}
static CohStatus readat(void*v,uint64_t o,void*out,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(out,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t h[32]){(void)v;SHA256(b.data,b.size,h);return COH_OK;}
extern void original_state_initialize(void),original_state_destroy(void),original_setup_initialize(const uint8_t*,size_t),original_setup_destroy(void);
extern unsigned original_10499_skip(void);
int main(int argc,char**argv){CHECK(argc==3);Source cache=file(argv[1]),states=file(argv[2]);original_state_initialize();original_setup_initialize(cache.data,cache.size);CHECK(original_10499_skip()==3);CohWrSurfaceStates*s=NULL;CohWrSurfaceLimits sl={200000,400000,1000};CHECK(coh_wr_surface_prepare((CohBytes){states.data,states.size},17,digest,NULL,&sl,(CohCancel){0},&s)==COH_OK);CohAssetLoader*l=NULL;CohAssetLimits al={32u<<20,30u<<20,16u<<20,16u<<20,4,4,4};CHECK(coh_asset_create(&al,&l)==COH_OK);CHECK(coh_asset_mount_file(l,"data/bin/tricks.bin",(CohAssetSource){readat,&cache,cache.size,17})==COH_OK);CohWrTexOptCache*c=NULL;CohWrTexOptLimits limits={1u<<20,256u<<20,32u<<20,192u<<20};CHECK(coh_wr_texopt_cache_open(l,(CohAssetId){"data/bin/tricks.bin",17},digest,NULL,&limits,(CohCancel){0},&c)==COH_OK);CohWrTexOptRecord*r=NULL;CHECK(coh_wr_texopt_record_create(c,10499,s,&limits,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r);uint32_t ordinal=123;CHECK(coh_wr_texopt_cache_find(c,"ArchEnt_INT_Elevator_Door_G\xef\xbf\xbd",&ordinal)==COH_UNSUPPORTED&&ordinal==123);coh_wr_texopt_cache_release(&c);coh_wr_surface_release(&s);CHECK(coh_asset_destroy(&l)==COH_OK);original_setup_destroy();original_state_destroy();free(cache.data);free(states.data);printf("{\"passed\":true,\"checks\":%u,\"source_prefix_executed\":true,\"factory_single_row_guard_skipped_LWC_false_and_true\":true,\"native_identity_refusal_preserved\":true,\"whole_dictionary_exclusion\":false,\"material_authority\":false,\"world_authority\":false}\n",checks);return 0;}

#include "../coh_wr_surface_states.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <openssl/sha.h>
static unsigned checks,digests;static int fail_alloc,polls,cancel_at,fail_digest;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"surface line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);void*__wrap_calloc(size_t n,size_t size){if(fail_alloc){fail_alloc=0;return NULL;}return __real_calloc(n,size);}
static CohStatus digest(void*v,CohBytes b,uint8_t hash[32]){(void)v;digests++;if(fail_digest)return COH_IO;SHA256(b.data,b.size,hash);return COH_OK;}
static int cancel(void*v){(void)v;polls++;return cancel_at&&polls==cancel_at;}
typedef struct{char*name;uint32_t bitNum,flags;}StateBit;
extern void original_state_initialize(void);extern void original_state_destroy(void);extern unsigned original_state_count(void);extern const StateBit*original_state(unsigned);extern int seqGetStateNumberFromName(const char*);
int main(int argc,char**argv){
 CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);uint8_t body[15380];CHECK(fread(body,1,sizeof(body),f)==sizeof(body)&&fgetc(f)==EOF);CHECK(!fclose(f));CohBytes b={body,sizeof(body)};CohWrSurfaceStates*s=NULL;CohWrSurfaceLimits limit={200000,400000,1000};CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_OK);CohWrSurfaceReport report;CHECK(coh_wr_surface_report(s,&report)==COH_OK);original_state_initialize();CHECK(report.count==original_state_count()&&report.count==875&&report.historical_input_generation==17);
 for(unsigned i=0;i<report.count;i++){const StateBit*state=original_state(i);uint32_t got=99999;CHECK(coh_wr_surface_lookup(s,state->name,&got)==COH_OK&&got==state->bitNum&&seqGetStateNumberFromName(state->name)==(int)got);char lower[100];size_t n=strlen(state->name);CHECK(n<sizeof(lower));for(size_t j=0;j<=n;j++)lower[j]=(state->name[j]>='A'&&state->name[j]<='Z')?(char)(state->name[j]+32):state->name[j];CHECK(coh_wr_surface_lookup(s,lower,&got)==COH_OK&&got==i&&seqGetStateNumberFromName(lower)==(int)i);}
 const char*surfaces[]={"Gravel","METALPLATE","WOODHOLLOW","Asphalt","CATWALK","INWATER","SNOW","Cement","not-a-source-state"};for(unsigned i=0;i<sizeof(surfaces)/sizeof(*surfaces);i++){uint32_t got=99999;int expected=seqGetStateNumberFromName(surfaces[i]);CohStatus status=coh_wr_surface_lookup(s,surfaces[i],&got);CHECK(expected<0?(status==COH_NOT_FOUND&&got==99999):(status==COH_OK&&got==(uint32_t)expected));}
 CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_STATE);CHECK(coh_wr_surface_report(s,(CohWrSurfaceReport*)s)==COH_INVALID);CHECK(coh_wr_surface_lookup(s,"METAL",(uint32_t*)s)==COH_INVALID);uint32_t got=123;CHECK(coh_wr_surface_lookup(s,"\xff",&got)==COH_UNSUPPORTED&&got==123);char longkey[101];memset(longkey,'a',100);longkey[100]=0;CHECK(coh_wr_surface_lookup(s,longkey,&got)==COH_LIMIT&&got==123);
 coh_wr_surface_release(&s);CHECK(!s);unsigned before=digests;limit.owned_limit=report.owned_bytes-1;CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_LIMIT&&!s&&digests==before);limit.owned_limit=200000;limit.aggregate_limit=report.aggregate_reserved_bytes-1;CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_LIMIT&&!s&&digests==before);limit.aggregate_limit=400000;
 fail_digest=1;CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_IO&&!s);fail_digest=0;fail_alloc=1;CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_LIMIT&&!s);body[100]^=1;CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_INVALID&&!s);body[100]^=1;
 CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},(CohWrSurfaceStates**)body)==COH_INVALID);CHECK(coh_wr_surface_prepare(b,0,digest,NULL,&limit,(CohCancel){0},&s)==COH_INVALID);
 for(cancel_at=1;cancel_at<=766;cancel_at++){polls=0;CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){cancel,NULL},&s)==COH_CANCELLED&&!s);}cancel_at=0;
 CHECK(coh_wr_surface_prepare(b,17,digest,NULL,&limit,(CohCancel){0},&s)==COH_OK);coh_wr_surface_release(&s);CHECK(!s);original_state_destroy();printf("{\"passed\":true,\"checks\":%u,\"historical_states\":875,\"material_authority\":false,\"world_authority\":false}\n",checks);return 0;
}

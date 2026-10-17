#include "coh_initial_suffix.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,cuts,mutations,acquisitions,releases,peak;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"suffix check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario,control,count;size_t spans[10][2];}Fixture;
#include "fixtures.h"
typedef struct{void*active;unsigned ordinal,fail_at,kind;const uint8_t*packet;}Owner;
static CohStatus acquire(void*context,size_t minimum,size_t maximum,CohSuffixLoan*loan){Owner*o=context;CHECK(!o->active);o->ordinal++;if(o->fail_at==o->ordinal)return COH_LIMIT;size_t bytes=o->kind==1?coh_initial_suffix_stage_bytes(COH_SUFFIX_CHARACTER):minimum;if(bytes<minimum)bytes=minimum;if(bytes>SIZE_MAX-16||bytes+16>maximum)return COH_LIMIT;void*data=malloc(bytes+16);CHECK(data);o->active=data;*loan=(CohSuffixLoan){data,bytes,bytes+16};if(o->kind==2)loan->data=(uint8_t*)data+1;if(o->kind==3)loan->data=(void*)o->packet;if(o->kind==4)loan->charged_bytes=bytes-1;if(o->kind==5)loan->data=o;acquisitions++;if(bytes+16>peak)peak=bytes+16;return o->kind==6?COH_LIMIT:COH_OK;}
static void release(void*context,CohSuffixLoan*loan){Owner*o=context;CHECK(o->active);free(o->active);o->active=NULL;memset(loan,0,sizeof(*loan));releases++;}
static CohSuffixDiagnostic out,prior;static CohSuffixReport report;
static CohRepReader reader(const Fixture*f,const uint8_t*d,size_t bytes,size_t bits){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){d,bytes},bits,(int)f->mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=f->start;return r;}
static CohSuffixContext context(const Fixture*f){CohSuffixContext c;memset(&c,0,sizeof(c));c.full_update=1;c.packet_id=10;c.diagnostic_dynamic_count=f->count;c.packet_lease_token=UINT64_C(0x12345678abcdef01);c.character_profile=(CohCharacterWireProfile){7,1,1,1,{0}};memset(c.character_profile.source_profile_sha256,0x11,32);return c;}
static CohStatus parse(CohRepReader*r,const CohSuffixContext*c,Owner*owner,size_t budget,size_t retained){CohRepReader before=*r;CohSuffixMemory memory={owner,sizeof(*owner),acquire,release};memset(&out,0xa5,sizeof(out));prior=out;CohStatus s=coh_initial_suffix_diagnostic(r,c,&memory,&out,&report,budget,retained);CHECK(s!=COH_OK);CHECK(!memcmp(r,&before,sizeof(*r))&&!memcmp(&out,&prior,sizeof(out)));CHECK(!owner->active);CHECK(report.validated.complete_initial_update==0&&report.validated.ack_permitted==0&&report.validated.actor_publication==0);return s;}
int main(void){
 for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*f=&fixtures[i];CohSuffixContext c=context(f);Owner o={0};o.packet=f->data;CohRepReader r=reader(f,f->data,f->bytes,f->bits);CohStatus s=parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0);
  if(!f->control){CHECK(s==COH_UNSUPPORTED&&report.stage==COH_SUFFIX_DYNAMIC&&report.validated.stage_count==10&&report.validated.raw_suffix_syntax_validated==1);CHECK(report.validated.end_bit==f->bits&&report.validated.packet.data==f->data&&report.validated.packet.size==f->bytes&&report.validated.packet_lease_token==c.packet_lease_token);for(unsigned j=0;j<10;j++)CHECK(report.validated.stages[j].begin_bit==f->spans[j][0]&&report.validated.stages[j].end_bit==f->spans[j][1]);}
  else{unsigned expected=f->control==1?COH_SUFFIX_INVENTORY:f->control==2?COH_SUFFIX_ATTRIBUTES:COH_SUFFIX_SOCIAL;CHECK(report.stage==expected&&report.validated.stage_count==expected-1&&report.validated.raw_suffix_syntax_validated==0);CHECK(s==(f->control==3?COH_INVALID:COH_UNSUPPORTED));}
  if(!f->control&&f->scenario==0){
   for(unsigned j=0;j<10;j++)for(unsigned d=0;d<2;d++){size_t end=f->spans[j][d];if(end<=f->start)continue;r=reader(f,f->data,f->bytes,end-1);o=(Owner){0};parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0);CHECK(report.validated.raw_suffix_syntax_validated==0);cuts++;}
   for(unsigned fail=1;fail<=10;fail++){o=(Owner){0};o.fail_at=fail;r=reader(f,f->data,f->bytes,f->bits);CHECK(parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0)==COH_LIMIT);CHECK(report.stage==fail);}
   for(unsigned kind=1;kind<=6;kind++){o=(Owner){0};o.kind=kind;o.packet=f->data;r=reader(f,f->data,f->bytes,f->bits);CohStatus wanted=(kind==1||kind==6)?COH_LIMIT:COH_INVALID;CHECK(parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0)==wanted);if(kind==1)CHECK(report.stage==COH_SUFFIX_BADGES);}
   o=(Owner){0};r=reader(f,f->data,f->bytes,f->bits);CHECK(parse(&r,&c,&o,1024,0)==COH_LIMIT&&o.ordinal==0);o=(Owner){0};r=reader(f,f->data,f->bytes,f->bits);CHECK(parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,SIZE_MAX)==COH_LIMIT&&o.ordinal==0);
   c.full_update=0;o=(Owner){0};r=reader(f,f->data,f->bytes,f->bits);CHECK(parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0)==COH_UNSUPPORTED&&o.ordinal==0);c.full_update=1;
  }
  if(!f->control&&f->scenario==1){uint8_t*d=malloc(f->bytes+8);CHECK(d);memcpy(d,f->data,f->bytes);memset(d+f->bytes,0xa5,8);r=reader(f,d,f->bytes+8,(f->bytes+8)*8);o=(Owner){0};CHECK(parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0)==COH_UNSUPPORTED&&report.validated.end_bit==f->bits&&report.validated.raw_suffix_syntax_validated);for(size_t j=0;j<f->bytes;j+=997){memcpy(d,f->data,f->bytes);d[j]^=255;r=reader(f,d,f->bytes,f->bits);o=(Owner){0};parse(&r,&c,&o,COH_SUFFIX_RAM_MAX,0);CHECK(report.validated.end_bit<=f->bits);mutations++;}free(d);}
 }
 CHECK(acquisitions==releases);printf("{\"passed\":true,\"checks\":%llu,\"source_component_compositions\":%zu,\"boundary_truncations\":%llu,\"sampled_mutations\":%llu,\"scratch_acquires\":%llu,\"scratch_releases\":%llu,\"peak_scratch_bytes\":%llu,\"whole_initial_update_complete\":false,\"actor_publication\":false,\"ack_permitted\":false}\n",(unsigned long long)checks,sizeof(fixtures)/sizeof(fixtures[0]),(unsigned long long)cuts,(unsigned long long)mutations,(unsigned long long)acquisitions,(unsigned long long)releases,(unsigned long long)peak);return 0;
}

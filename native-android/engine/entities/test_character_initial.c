#include "coh_character_initial.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"initial check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {const uint8_t *data;size_t bytes,bits,prefix_end,character_end,stats_begin,names_end,start;unsigned mode,scenario;uint32_t words[15];uint8_t auth[128];float stats[16];int32_t integers[6];}InitialFixture;
#include "initial_fixtures.h"
static CohCharacterInitialPrefix *out,*prior;static CohCharacterInitialWorkspace *workspace;
static CohCharacterData *shadow;static CohCharacterWorkspace *shadow_workspace;
static CohCharacterWireProfile profile(unsigned scenario){
 CohCharacterWireProfile p={0};unsigned base=scenario<6?scenario:1;p.generation=7;p.shared_set_count_bound=1;p.player=base?1:0;p.shared_set_count=base==5?3:(base==2?0:(base==3?2:1));memset(p.source_profile_sha256,0x11,32);return p;
}
static CohRepReader reader(const InitialFixture*f){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->data,f->bytes},f->bits,(int)f->mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=f->start;return r;}
static CohStatus parse(CohRepReader*r,const CohCharacterWireProfile*p){return coh_character_initial_read(r,p,10,workspace,out,COH_CHARACTER_INITIAL_RAM_MAX,0,NULL);}
static void reject(CohRepReader r,const CohCharacterWireProfile*p,CohStatus expected){
 CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohCharacterInitialFailure f={0};CohStatus s=coh_character_initial_read(&r,p,10,workspace,out,COH_CHARACTER_INITIAL_RAM_MAX,0,&f);CHECK(s!=COH_OK);if(expected!=COH_OK)CHECK(s==expected);CHECK(f.status==s);CHECK(!memcmp(&r,&before,sizeof(r)));CHECK(!memcmp(out,prior,sizeof(*out)));
}
static uint32_t seed=0x15989ab3u;static uint32_t random32(void){seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;}
int main(void){
 out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));shadow=malloc(sizeof(*shadow));shadow_workspace=malloc(sizeof(*shadow_workspace));CHECK(out&&prior&&workspace&&shadow&&shadow_workspace);
 for(size_t i=0;i<sizeof(initial_fixtures)/sizeof(initial_fixtures[0]);i++){
  const InitialFixture*f=&initial_fixtures[i];CohCharacterWireProfile p=profile(f->scenario);CohRepReader r=reader(f);
  if(f->scenario==5){reject(r,&p,COH_INVALID);continue;}
  if(f->scenario==7){reject(r,&p,COH_LIMIT);continue;}
  CHECK(parse(&r,&p)==COH_OK);CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->end_bit==f->bits);CHECK(out->prefix_end_bit==f->prefix_end&&out->character_end_bit==f->character_end&&out->names_end_bit==f->names_end);
  CHECK(out->account.boost_diminishing==f->words[0]&&out->account.power_diminishing==f->words[1]&&out->account.no_base_edit==f->words[2]&&out->account.beta_base==f->words[3]&&out->account.base_raid==f->words[4]);
  CHECK(out->account.player_type==f->words[5]&&out->account.player_subtype==f->words[6]&&out->account.praetorian_progress==f->words[7]&&out->account.player_type_by_location==f->words[8]);CHECK(!memcmp(out->account.auth_user_data,f->auth,128));
  CHECK(out->ally_id==f->words[9]&&out->gang_id==f->words[10]&&out->pvp_switch==f->words[11]&&out->pvp_active==f->words[12]&&out->pvp_timer==f->words[13]&&out->is_ganker==f->words[14]);
  CHECK(!strcmp(out->secondary_set,"Unknown_Secondary_Set"));CHECK(f->scenario==6?strlen(out->primary_set)==127:!strcmp(out->primary_set,"Unknown_Primary_Set"));
  for(unsigned j=0;j<8;j++)CHECK(fabsf(out->self_stats.current[j]-f->stats[j])<0.001f);
  for(unsigned j=0;j<7;j++)CHECK(fabsf(out->self_stats.maximum[j]-f->stats[j+8])<0.001f);
  CHECK(!memcmp(out->self_stats.integers,f->integers,sizeof(f->integers)));CHECK(out->self_stats.current_valid==255&&out->self_stats.maximum_valid==127&&out->self_stats.integer_valid==63);
  /* Reused qualified child sees exactly its original boundary, not a caller
   * guessed offset. Compare every staged metadata byte with standalone parse. */
  CohRepReader sub=reader(f);sub.cursor=f->prefix_end;CHECK(coh_character_data_read(&sub,&p,shadow_workspace,shadow,COH_CHARACTER_RAM_MAX,0,NULL)==COH_OK);CHECK(sub.cursor==f->character_end);CHECK(!memcmp(shadow,&out->character,sizeof(*shadow)));CHECK(!out->character.dictionary_bindings_verified);
  if(f->scenario==8){CHECK(!strcmp(out->character.class_name,"Unknown_Class")&&!strcmp(out->character.origin_name,"Unknown_Origin"));CHECK(out->character.powers[0].power_crc==0xfedcba98);CHECK(out->ally_id==UINT32_MAX&&out->gang_id==UINT32_MAX&&out->pvp_timer==UINT32_MAX);}
  if(f->scenario==0&&f->start==0){
   /* Every earlier/later field cut must roll back even already-complete
    * character metadata and account entitlements. */
   for(size_t bit=f->start;bit<f->bits;bit++){CohRepReader cut=reader(f);cut.bits=bit;reject(cut,&p,COH_OK);truncations++;}
   size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_INITIAL_STACK_RESERVE+f->bytes;r=reader(f);CHECK(coh_character_initial_read(&r,&p,10,workspace,out,minimum,0,NULL)==COH_OK);CohRepReader before=reader(f);r=before;*prior=*out;
   CHECK(coh_character_initial_read(&r,&p,10,workspace,out,minimum-1,0,NULL)==COH_LIMIT);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));
   CHECK(coh_character_initial_read(&r,&p,10,workspace,out,minimum,1,NULL)==COH_LIMIT);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));
   CHECK(coh_character_initial_read(&r,&p,10,(CohCharacterInitialWorkspace*)out,out,COH_CHARACTER_INITIAL_RAM_MAX,0,NULL)==COH_INVALID);
   CHECK(coh_character_initial_read(&r,&p,10,workspace,out,COH_CHARACTER_INITIAL_RAM_MAX,0,(CohCharacterInitialFailure*)out)==COH_INVALID);
   CHECK(coh_character_initial_read(&r,(CohCharacterWireProfile*)out,10,workspace,out,COH_CHARACTER_INITIAL_RAM_MAX,0,NULL)==COH_INVALID);
  }
  uint8_t*bytes=malloc(f->bytes+8);CHECK(bytes);memcpy(bytes,f->data,f->bytes);memset(bytes+f->bytes,0x7f,8);r=reader(f);r.bytes=(CohBytes){bytes,f->bytes+8};r.bits=(f->bytes+8)*8;CHECK(parse(&r,&p)==COH_OK&&r.cursor==f->bits);
  for(size_t j=0;j<f->bytes;j+=(j>=f->character_end/8?1:128)){
   memcpy(bytes,f->data,f->bytes);bytes[j]^=255;r=reader(f);r.bytes.data=bytes;CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=parse(&r,&p);if(s!=COH_OK){CHECK(!memcmp(&before,&r,sizeof(r)));CHECK(!memcmp(out,prior,sizeof(*out)));}else{CHECK(r.cursor<=r.bits);CHECK(out->character.power_count<=COH_CHARACTER_POWERS_MAX);}mutations++;
  }
  free(bytes);
 }
 for(unsigned i=0;i<1000;i++){
  uint8_t bytes[512];for(unsigned j=0;j<sizeof(bytes);j++)bytes[j]=(uint8_t)random32();CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},sizeof(bytes)*8,i%2)==COH_OK);CohCharacterWireProfile p=profile(i%5);CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=parse(&r,&p);if(s!=COH_OK){CHECK(!memcmp(&before,&r,sizeof(r)));CHECK(!memcmp(out,prior,sizeof(*out)));}else CHECK(r.cursor<=r.bits);randomized++;
 }
 printf("{\"passed\":true,\"checks\":%llu,\"fixtures\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"randomized\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"stack_reserve\":%u,\"aggregate_limit\":%u,\"whole_character_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(initial_fixtures)/sizeof(initial_fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,(unsigned long long)randomized,sizeof(*out),sizeof(*workspace),COH_CHARACTER_INITIAL_STACK_RESERVE,COH_CHARACTER_INITIAL_RAM_MAX);
 free(out);free(prior);free(workspace);free(shadow);free(shadow_workspace);return 0;
}

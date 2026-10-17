/* Reuse the already qualified owner/rollback checks without duplicating the
 * production-sized state. This is one translation unit, not two test mains. */
#define main component_fixture_main
#include "test_selected_record.c"
#undef main
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;unsigned count=word(f);CohEntCostumeDictionary*d=dictionary();State*s=malloc(sizeof(*s));if(!s)abort();
 for(unsigned which=0;which<count;which++){
  unsigned bytes=word(f),bits=word(f),begin=word(f),aligned=word(f),scenario=word(f),bounds[26];for(unsigned i=0;i<26;i++)bounds[i]=word(f);
  unsigned char*data=malloc(bytes);if(!data||fread(data,1,bytes,f)!=bytes)abort();
#define OUTER_INIT() do{init(s,data,bytes,bits,aligned,begin,d);s->prior.index=17;s->context.entity_index=17;}while(0)
  OUTER_INIT();ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_OK&&s->reader.cursor==bits);
  for(unsigned i=0;i<13;i++){ENSURE(s->out.stages[i].begin_bit==bounds[i*2]);ENSURE(s->out.stages[i].end_bit==bounds[i*2+1]);}
  ENSURE(s->out.selected.index==17&&s->out.selected.identity.entity_id==91&&s->out.selected.identity.dbid==4242);
  ENSURE(s->out.titles.valid&&s->out.titles.title_the==scenario&&s->out.titles.badge==7&&s->out.titles.gender==1&&s->out.titles.name_gender==2);
  ENSURE(!strcmp(s->out.titles.name,"selected-source-fixture")&&!strcmp(s->out.titles.common,"Fixture")&&!strcmp(s->out.titles.origin,"Source")&&!strcmp(s->out.titles.special,"Bounded"));
  ENSURE(s->out.selected.vision_phases==1&&s->out.selected.exclusive_vision_phase==(scenario&3)&&s->out.selected.con_yellow==(scenario&1)&&s->out.selected.combat_mod_shift==scenario);
  ENSURE(s->out.rare_prefix.ally_id==1&&s->out.rare_prefix.gang_id==scenario&&s->out.rare_prefix.pvp_timer==scenario&&s->out.rare_prefix.show_on_map==1);
  ENSURE(s->out.rare_prefix.ignore_combat==((scenario>>2)&1));if((scenario>>2)&1)ENSURE(s->out.rare_prefix.combat_shift==-3);
  /* Every source group boundary is a rollback barrier, including zero-length
   * stages. No stage is an admitted independent record or framing sentinel. */
  for(unsigned i=0;i<26;i++)if(bounds[i]>begin&&bounds[i]<=bits){OUTER_INIT();s->reader.bits=bounds[i]-1;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK);cuts++;}
  OUTER_INIT();s->context.selected_dbid=4243;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
  OUTER_INIT();s->context.expected_dictionary_sha256[0]^=1;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
  for(unsigned i=begin/8;i<bytes;i+=31){data[i]^=0x81;OUTER_INIT();(void)parse(s,COH_SELECTED_RECORD_RAM_MAX,0);data[i]^=0x81;mutations++;}
#undef OUTER_INIT
  free(data);
 }
 ENSURE(fgetc(f)==EOF);fclose(f);free(s);coh_ent_costume_dictionary_free(d);printf("{\"checks\":%lu,\"source_outer_fixtures\":%u,\"successes\":%lu,\"refusals\":%lu,\"boundary_cuts\":%lu,\"byte_mutations\":%lu}\n",checks,count,successes,refusals,cuts,mutations);return 0;
}

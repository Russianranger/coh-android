#include "coh_initial_list.h"
#include "../entities/coh_teammate_buffs.h"
#define main component_fixture_main
#include "../selected-record/test_selected_record.c"
#undef main
static CohStatus record_parse(State*s){
 CohRepReader r=s->reader;CohSelectedRecord out=s->out;CohEntSlot prior=s->prior;
 CohStatus status=coh_initial_record_read(&s->reader,&s->context,&s->prior,&s->memory,&s->out,&s->workspace,&s->failure,COH_SELECTED_RECORD_RAM_MAX,0);
 ENSURE(!s->owner.active&&s->owner.acquires==s->owner.releases);ENSURE(!memcmp(&prior,&s->prior,sizeof(prior)));
 if(status==COH_OK){successes++;ENSURE(s->out.raw_record_validated&&s->out.stage_count==13);ENSURE(s->out.selected_wire_dbid_matched==s->out.core.identity.is_self);ENSURE(!s->out.actor_publication&&!s->out.ack_permitted&&!s->out.complete_initial_update&&!s->out.dictionary_authority);size_t at=r.cursor;for(unsigned i=0;i<13;i++){ENSURE(s->out.stages[i].begin_bit==at&&s->out.stages[i].end_bit>=at);at=s->out.stages[i].end_bit;}ENSURE(at==s->reader.cursor&&s->out.end_bit==at);}
 else{refusals++;ENSURE(!memcmp(&r,&s->reader,sizeof(r))&&!memcmp(&out,&s->out,sizeof(out)));}
 return status;
}
typedef struct{CohRepReader reader;CohSelectedRecordContext context;Owner owner;CohSelectedRecordMemory memory;CohInitialListEntry entries[COH_ENT_LIST_MAX];CohInitialList out;CohInitialListWorkspace work;CohInitialListFailure failure;}ListState;
static void list_init(ListState*s,const unsigned char*wire,unsigned bytes,unsigned bits,unsigned aligned,unsigned begin,CohEntCostumeDictionary*d){
 memset(s,0,sizeof(*s));ENSURE(coh_rep_reader_bounded(&s->reader,(CohBytes){wire,bytes},bits,aligned,1024*1024)==COH_OK);s->reader.cursor=begin;s->context.selected_dbid=4242;s->context.packet_id=10;s->context.interp_level=2;s->context.dictionary_generation=9;s->context.costume_dictionary=d;s->context.packet_lease_token=777;memset(s->context.expected_dictionary_sha256,0x42,32);s->memory=(CohSelectedRecordMemory){&s->owner,sizeof(s->owner),acquire,release};memset(&s->out,0xa5,sizeof(s->out));memset(s->entries,0xa5,sizeof(s->entries));
}
static CohStatus list_parse(ListState*s,size_t capacity,size_t budget,size_t retained){
 CohRepReader r=s->reader;CohInitialList before=s->out;CohInitialListEntry entries[COH_ENT_LIST_MAX];memcpy(entries,s->entries,sizeof(entries));
 CohStatus status=coh_initial_list_read(&s->reader,&s->context,&s->memory,s->entries,capacity,&s->out,&s->work,&s->failure,budget,retained);
 ENSURE(!s->owner.active&&s->owner.acquires==s->owner.releases);
 if(status==COH_OK){successes++;ENSURE(s->out.raw_list_validated&&s->out.unique_selected_self&&s->out.selected_dbid==4242&&s->out.self_index);ENSURE(s->out.count<=capacity&&s->reader.cursor==s->out.end_bit&&s->out.begin_bit==r.cursor);ENSURE(s->out.packet.data==r.bytes.data&&s->out.packet_bits==r.bits&&s->out.packet_lease_token==777);ENSURE(!s->out.complete_initial_update&&!s->out.actor_publication&&!s->out.dictionary_authority&&!s->out.ack_permitted);}
 else{refusals++;ENSURE(!memcmp(&r,&s->reader,sizeof(r))&&!memcmp(&before,&s->out,sizeof(before))&&!memcmp(entries,s->entries,sizeof(entries)));}
 return status;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;CohEntCostumeDictionary*d=dictionary();State*s=malloc(sizeof(*s));ListState*ls=malloc(sizeof(*ls));if(!s||!ls)abort();unsigned count=word(f),record_cases=count,list_cases;
 for(unsigned which=0;which<count;which++){
  unsigned bytes=word(f),bits=word(f),begin=word(f),aligned=word(f),profile=word(f),variant=word(f),scenario=word(f),index=word(f),entity=word(f),dbid=word(f),type=word(f),events=word(f);unsigned triples[72];ENSURE(events<=24);for(unsigned i=0;i<events*3;i++)triples[i]=word(f);unsigned char*wire=malloc(bytes);if(!wire||fread(wire,1,bytes,f)!=bytes)abort();
#define RECORD_INIT() do{init(s,wire,bytes,bits,aligned,begin,d);s->prior.index=index;s->context.entity_index=index;}while(0)
  RECORD_INIT();ENSURE(record_parse(s)==COH_OK&&s->reader.cursor==bits);ENSURE(s->out.core.identity.entity_id==entity&&s->out.core.identity.dbid==dbid&&s->out.core.identity.type==type&&s->out.core.identity.is_self==!profile);ENSURE(s->out.core.pchar_things==(profile!=3));ENSURE(s->out.titles.valid==(profile<2));ENSURE(s->out.selected.position.valid&&s->out.selected.orientation.valid==7&&s->out.selected.state_packet==10&&s->out.selected.sequence_packet==10);ENSURE(s->out.selected.sequence_index==(variant==2?0:variant==3?INT32_MAX:33)&&s->out.selected.sequence_ticks==(variant==2?0:variant==3?65535:4)&&s->out.selected.sequence_bits==(variant==2?1248:0));
  ENSURE(s->out.selected.vision_phases==1&&s->out.selected.exclusive_vision_phase==(scenario&3)&&s->out.selected.con_yellow==(scenario&1)&&s->out.selected.combat_mod_shift==(profile<3?scenario:0));ENSURE(s->out.rare_prefix.ally_id==(profile<3?1u:0u)&&s->out.rare_prefix.gang_id==(profile<3?scenario:0));ENSURE(s->out.selected.inventory.valid==!profile);ENSURE(!profile||s->out.stages[9].begin_bit==s->out.stages[9].end_bit);
  static const unsigned stage_for_child[24]={0,0,1,1,1,1,2,2,3,4,5,7,8,8,8,8,9,9,10,10,11,11,11,12};
  for(unsigned i=0;i<events;i++){unsigned id=triples[i*3];ENSURE(id>0&&id<24);unsigned stage=stage_for_child[id];ENSURE(triples[i*3+1]>=s->out.stages[stage].begin_bit&&triples[i*3+2]<=s->out.stages[stage].end_bit);if(profile)ENSURE(id!=15&&id!=16&&id!=17&&id!=14);if(profile==3)ENSURE(id!=8&&id!=12&&id!=13);}
  if(which%17==0){for(unsigned i=0;i<events;i++){unsigned at=triples[i*3+2];if(at>begin){RECORD_INIT();s->reader.bits=at-1;ENSURE(record_parse(s)!=COH_OK);cuts++;}}}
  unsigned stride=bytes/16+1;for(unsigned at=begin/8;at<bytes;at+=stride){wire[at]^=0x81;RECORD_INIT();(void)record_parse(s);wire[at]^=0x81;mutations++;}
#undef RECORD_INIT
  free(wire);
 }
 list_cases=word(f);
 for(unsigned which=0;which<list_cases;which++){
  unsigned bytes=word(f),bits=word(f),begin=word(f),aligned=word(f),n=word(f),capacity=word(f),expected=word(f),end=word(f);unsigned*rows=malloc((n?n:1)*7*sizeof(unsigned));if(!rows)abort();for(unsigned i=0;i<n*7;i++)rows[i]=word(f);unsigned char*wire=malloc(bytes);if(!wire||fread(wire,1,bytes,f)!=bytes)abort();
#define LIST_INIT() list_init(ls,wire,bytes,bits,aligned,begin,d)
  LIST_INIT();ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)==(CohStatus)expected);
  if(!expected){ENSURE(ls->reader.cursor==end&&ls->out.count==n);for(unsigned i=0;i<n;i++){CohInitialListEntry*e=&ls->entries[i];ENSURE(e->index==rows[i*7]&&e->entity_id==rows[i*7+1]&&e->dbid==rows[i*7+2]&&e->type==rows[i*7+3]&&e->is_self==rows[i*7+4]&&e->begin_bit==rows[i*7+5]&&e->end_bit==rows[i*7+6]);ENSURE(e->position_valid&&e->orientation_valid==7);ENSURE(e->position.x==12.5f&&e->position.y==-6.25f&&e->position.z==128.0f);if(e->is_self){ENSURE(!memcmp(&e->position,&ls->out.selected_record.selected.position.position,sizeof(e->position)));ENSURE(!memcmp(e->quaternion,ls->out.selected_record.selected.orientation.quaternion,sizeof(e->quaternion)));}}
   size_t occupied=COH_INITIAL_LIST_STACK_RESERVE+sizeof(ls->reader)+sizeof(ls->context)+sizeof(ls->memory)+capacity*sizeof(ls->entries[0])+sizeof(ls->out)+sizeof(ls->work)+sizeof(ls->failure)+bytes+sizeof(ls->owner)+coh_ent_costume_dictionary_bytes(d);
   ENSURE(ls->owner.maximum==COH_ENT_BUFF_AGGREGATE_MAX-occupied);
   unsigned loans=ls->owner.acquires;
   for(unsigned i=0;i<n;i++)if(n<8||i%31==0||n-i<=2){unsigned at=rows[i*7+6];LIST_INIT();ls->reader.bits=at-1;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK);cuts++;}
   for(unsigned mode=1;mode<=6;mode++)for(unsigned pick=0;pick<3;pick++){LIST_INIT();ls->owner.fail_at=pick==0?1:pick==1?(loans+1)/2:loans;ls->owner.mode=mode;ls->owner.alias=pick==0?(void*)ls->entries:pick==1?(void*)&ls->out:(void*)ls->work.entries;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK);loan_controls++;}
   LIST_INIT();ENSURE(list_parse(ls,capacity,1,0)==COH_LIMIT);LIST_INIT();ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,COH_SELECTED_RECORD_RAM_MAX)==COH_LIMIT);
   LIST_INIT();ls->context.entity_index=17;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
   LIST_INIT();ls->context.selected_dbid=4243;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
   LIST_INIT();ls->context.expected_dictionary_sha256[0]^=1;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
   LIST_INIT();ls->context.costume_dictionary=(const CohEntCostumeDictionary*)&ls->out;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
   LIST_INIT();ls->memory.context=&ls->context;ENSURE(list_parse(ls,capacity,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
  }
#undef LIST_INIT
  free(rows);free(wire);
 }
 ENSURE(fgetc(f)==EOF);fclose(f);free(s);free(ls);coh_ent_costume_dictionary_free(d);printf("{\"checks\":%lu,\"record_cases\":%u,\"list_cases\":%u,\"successes\":%lu,\"refusals\":%lu,\"cuts\":%lu,\"mutations\":%lu,\"loan_controls\":%lu}\n",checks,record_cases,list_cases,successes,refusals,cuts,mutations,loan_controls);return 0;
}

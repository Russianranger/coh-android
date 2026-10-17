#include "coh_initial_update.h"
#define main selected_component_main
#include "../selected-record/test_selected_record.c"
#undef main
static CohStatus charged_acquire(void*opaque,size_t minimum,size_t maximum,CohSelectedRecordLoan*l){
 Owner*o=opaque;o->acquires++;o->maximum=maximum;o->requested=minimum;
 if(o->active||minimum>SIZE_MAX-32||minimum+32>maximum)return COH_LIMIT;
 o->allocation=malloc(minimum+32);if(!o->allocation)abort();o->active=1;
 *l=(CohSelectedRecordLoan){o->allocation,minimum+32,minimum+32};
 if(o->fail_at==o->acquires){switch(o->mode){case 1:return COH_STATE;case 2:l->bytes=minimum-1;break;case 3:l->data=(char*)l->data+1;break;case 4:l->charged_bytes=maximum+1;break;case 5:l->data=(void*)o->alias;break;case 6:l->charged_bytes=minimum-1;break;default:abort();}}
 return COH_OK;
}
typedef struct{CohRepReader reader;CohInitialUpdateContext context;CohRepSchema schema;CohSelectedRecordMemory memory;Owner owner;CohInitialUpdateWorkspace workspace;CohInitialUpdateReport report;}WholeState;
static void whole_init(WholeState*s,const unsigned char*wire,unsigned bytes,unsigned bits,unsigned aligned,unsigned begin,unsigned dynamic,CohEntCostumeDictionary*d){
 memset(s,0,sizeof(*s));ENSURE(coh_rep_reader_bounded(&s->reader,(CohBytes){wire,bytes},bits,aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);s->reader.cursor=begin;s->context.record=(CohSelectedRecordContext){4242,10,0,2,9,d,777,{0}};memset(s->context.record.expected_dictionary_sha256,0x42,32);s->context.session_generation=s->context.schema_generation=99;s->context.diagnostic_dynamic_count=dynamic;s->context.character=(CohCharacterWireProfile){7,1,1,1,{0}};memset(s->context.character.source_profile_sha256,0x11,32);s->schema=(CohRepSchema){{{11,1},{12,4},{13,10}},3,0};s->memory=(CohSelectedRecordMemory){&s->owner,sizeof(s->owner),charged_acquire,release};
}
static CohStatus whole_parse(WholeState*s,size_t budget,size_t retained){CohRepReader before=s->reader;CohStatus status=coh_initial_update_diagnostic(&s->reader,&s->context,&s->schema,&s->memory,&s->workspace,&s->report,budget,retained);ENSURE(status!=COH_OK);ENSURE(!memcmp(&before,&s->reader,sizeof(before)));ENSURE(!s->owner.active&&s->owner.acquires==s->owner.releases);ENSURE(!s->report.validated.complete_initial_update&&!s->report.validated.actor_publication&&!s->report.validated.ack_permitted&&!s->report.validated.dictionary_authority&&!s->report.validated.dynamic_owner_verified&&!s->report.validated.selected_owner_verified);return status;}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;unsigned total=word(f);WholeState*s=malloc(sizeof(*s));if(!s)abort();CohEntCostumeDictionary*d=dictionary();unsigned syntax=0;
 for(unsigned i=0;i<total;i++){
  unsigned bytes=word(f),bits=word(f),begin=word(f),aligned=word(f),count=word(f),dynamic=word(f),tail=word(f),ends[5];for(unsigned j=0;j<5;j++)ends[j]=word(f);unsigned char*wire=malloc(bytes);if(!wire||fread(wire,1,bytes,f)!=bytes)abort();
#define INIT() whole_init(s,wire,bytes,bits,aligned,begin,dynamic,d)
  INIT();CohStatus status=whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0);
  if(tail<3){
   if(status!=COH_UNSUPPORTED||!s->report.validated.raw_initial_syntax_validated){fprintf(stderr,"case%u stage%u status%u bit%zu suffixstage%u expected suffixend%u\n",i,s->report.stage,status,s->report.bit,s->report.suffix.stage,ends[4]);return 1;}
   ENSURE(s->report.stage==COH_INITIAL_AUTHORITY&&s->report.validated.end_bit==bits&&s->report.validated.transport_end_verified);syntax++;
   ENSURE(s->report.validated.header_end_bit==ends[0]&&s->report.validated.list_end_bit==ends[1]&&s->report.validated.control_end_bit==ends[2]&&s->report.validated.deletes_end_bit==ends[3]&&s->report.validated.suffix_end_bit==ends[4]);ENSURE(s->report.validated.list.count==count&&s->report.validated.list.unique_selected_self&&s->report.validated.list.selected_dbid==4242);ENSURE(s->report.validated.suffix.stage_count==10&&s->report.validated.suffix.raw_suffix_syntax_validated&&!s->report.validated.suffix.transport_end_verified);ENSURE(s->report.validated.command_count==tail);unsigned loans=s->owner.acquires;
   if(i%15==0){
    for(unsigned j=0;j<5;j++){INIT();s->reader.bits=ends[j]-1;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK&&!s->report.validated.raw_initial_syntax_validated);cuts++;}
    for(unsigned j=0;j<3;j++)for(unsigned mode=1;mode<=6;mode++){INIT();s->owner.fail_at=j==0?1:j==1?(loans+1)/2:loans;s->owner.mode=mode;s->owner.alias=j==0?(const void*)&s->context:j==1?(const void*)&s->report:(const void*)&s->workspace;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK&&!s->report.validated.raw_initial_syntax_validated);loan_controls++;}
    INIT();ENSURE(whole_parse(s,1,0)==COH_LIMIT);INIT();ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,SIZE_MAX)==COH_LIMIT);
    INIT();s->context.record.selected_dbid++;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
    INIT();s->context.legacy_commands=1;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_UNSUPPORTED);
    INIT();s->context.schema_generation++;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
    INIT();s->schema.entries[1].id=11;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
    INIT();s->context.record.costume_dictionary=(const CohEntCostumeDictionary*)&s->report;ENSURE(whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
    INIT();s->memory.context=&s->context;ENSURE(coh_initial_update_diagnostic(&s->reader,&s->context,&s->schema,&s->memory,&s->workspace,&s->report,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
    for(unsigned k=begin/8;k<bytes;k+=bytes/23+1){wire[k]^=0x81;INIT();(void)whole_parse(s,COH_SELECTED_RECORD_RAM_MAX,0);wire[k]^=0x81;mutations++;}
   }
  }else if(tail>=16){ENSURE(s->report.stage==COH_INITIAL_SUFFIX&&!s->report.validated.raw_initial_syntax_validated);unsigned expected=tail==16?COH_SUFFIX_INVENTORY:tail==17?COH_SUFFIX_ATTRIBUTES:COH_SUFFIX_SOCIAL;ENSURE(s->report.suffix.stage==expected&&status==(tail==18?COH_INVALID:COH_UNSUPPORTED));}
  else if(tail==8){ENSURE(s->report.stage==COH_INITIAL_DELETES&&status==COH_NOT_FOUND);}
  else if(tail==9){ENSURE(s->report.stage==COH_INITIAL_SUFFIX&&s->report.validated.deletes.count==1&&!s->report.validated.raw_initial_syntax_validated);}
  else{ENSURE(s->report.stage==COH_INITIAL_COMMAND_TAIL&&!s->report.validated.raw_initial_syntax_validated&&!s->report.validated.transport_end_verified);ENSURE(status==(tail==3?COH_UNSUPPORTED:tail==6?COH_LIMIT:COH_INVALID));if(tail==3)ENSURE(s->report.refused_command==999);}
#undef INIT
  free(wire);
 }
 ENSURE(fgetc(f)==EOF);fclose(f);free(s);coh_ent_costume_dictionary_free(d);printf("{\"checks\":%lu,\"fixtures\":%u,\"syntax_only\":%u,\"cuts\":%lu,\"mutations\":%lu,\"loan_controls\":%lu,\"whole_update_accepted\":false,\"actor_publication\":false,\"ack_permitted\":false}\n",checks,total,syntax,cuts,mutations,loan_controls);return 0;
}

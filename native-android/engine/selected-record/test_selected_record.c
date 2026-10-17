#include "coh_selected_record.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ENSURE(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static unsigned long checks,cuts,mutations,successes,refusals,loan_controls;
typedef struct{unsigned acquires,releases,active,fail_at,mode;size_t maximum,requested;void*allocation;const void*alias;}Owner;
static CohStatus acquire(void*opaque,size_t minimum,size_t maximum,CohSelectedRecordLoan*l){
 Owner*o=opaque;o->acquires++;o->maximum=maximum;o->requested=minimum;
 if(o->active||minimum>maximum)abort();
 o->allocation=malloc(minimum+32);if(!o->allocation)abort();o->active=1;
 l->data=o->allocation;l->bytes=l->charged_bytes=minimum;
 if(o->fail_at==o->acquires){switch(o->mode){case 1:return COH_STATE;case 2:l->bytes=minimum-1;break;case 3:l->data=(char*)l->data+1;break;case 4:l->charged_bytes=maximum+1;break;case 5:l->data=(void*)o->alias;break;case 6:l->charged_bytes=minimum-1;break;default:abort();}}
 return COH_OK;
}
static void release(void*opaque,CohSelectedRecordLoan*l){Owner*o=opaque;if(!o->active||!l->data)abort();free(o->allocation);o->allocation=NULL;o->active=0;o->releases++;}
typedef struct{CohRepReader reader;CohSelectedRecordContext context;CohEntSlot prior;Owner owner;CohSelectedRecordMemory memory;CohSelectedRecord out;CohSelectedRecordWorkspace workspace;CohSelectedRecordFailure failure;}State;
static void init(State*s,const unsigned char*data,size_t bytes,size_t bits,unsigned aligned,unsigned begin,CohEntCostumeDictionary*d){
 memset(s,0,sizeof(*s));if(coh_rep_reader_bounded(&s->reader,(CohBytes){data,bytes},bits,aligned,1024*1024)!=COH_OK)abort();s->reader.cursor=begin;coh_ent_slot_init(&s->prior,7);
 s->context.selected_dbid=4242;s->context.packet_id=10;s->context.entity_index=7;s->context.interp_level=2;s->context.dictionary_generation=9;s->context.packet_lease_token=777;s->context.costume_dictionary=d;memset(s->context.expected_dictionary_sha256,0x42,32);
 s->memory=(CohSelectedRecordMemory){&s->owner,sizeof(s->owner),acquire,release};memset(&s->out,0xa5,sizeof(s->out));
}
static CohStatus parse(State*s,size_t budget,size_t retained){
 CohRepReader before=s->reader;CohEntSlot prior=s->prior;CohSelectedRecord before_out=s->out;
 CohStatus status=coh_selected_record_read(&s->reader,&s->context,&s->prior,&s->memory,&s->out,&s->workspace,&s->failure,budget,retained);
 ENSURE(!s->owner.active&&s->owner.acquires==s->owner.releases);ENSURE(!memcmp(&prior,&s->prior,sizeof(prior)));
 if(status==COH_OK){successes++;ENSURE(s->out.raw_record_validated&&s->out.stage_count==13&&s->out.selected_wire_dbid_matched);ENSURE(s->out.selected.identity.dbid==4242&&s->out.selected.identity.is_self&&s->out.selected.identity.create);ENSURE(s->out.packet.data==before.bytes.data&&s->out.packet.size==before.bytes.size&&s->out.packet_bits==before.bits&&s->out.packet_lease_token==777);ENSURE(s->out.end_bit==s->reader.cursor&&s->out.begin_bit==before.cursor);ENSURE(!s->out.actor_publication&&!s->out.ack_permitted&&!s->out.dictionary_authority&&!s->out.complete_initial_update&&!s->out.whole_list_uniqueness_verified);size_t at=before.cursor;for(unsigned i=0;i<13;i++){ENSURE(s->out.stages[i].begin_bit==at&&s->out.stages[i].end_bit>=at);at=s->out.stages[i].end_bit;}ENSURE(at==s->reader.cursor);}
 else{refusals++;ENSURE(!memcmp(&before,&s->reader,sizeof(before)));ENSURE(!memcmp(&before_out,&s->out,sizeof(before_out)));}
 return status;
}
static CohEntCostumeDictionary* dictionary(void){
 CohBytes strings[16]={{0}},extra[8]={{0}};uint32_t colors[8]={0};uint8_t present[8]={0},sha[32];memset(sha,0x42,32);
 strings[1]=(CohBytes){(const uint8_t*)"None",4};strings[3]=(CohBytes){(const uint8_t*)"Male",4};strings[4]=(CohBytes){(const uint8_t*)"FixtureEntity",13};strings[5]=(CohBytes){(const uint8_t*)"FixtureGeometry",15};extra[2]=(CohBytes){(const uint8_t*)"Upper",5};extra[4]=(CohBytes){(const uint8_t*)"BodySet",7};colors[2]=0x11223344;colors[5]=0x55667788;present[2]=present[5]=1;
 CohEntCostumeDictionaryInput in={0};in.generation=9;in.body_parts=4;in.body_types=6;memcpy(in.manifest_sha256,sha,32);in.strings=(CohEntCostumeStringTable){16,strings};in.extra_strings=(CohEntCostumeStringTable){8,extra};in.palette_max_size=8;in.palette=colors;in.palette_present=present;CohEntCostumeDictionary*d=NULL;ENSURE(coh_ent_costume_dictionary_load(&d,&in,9,sha)==COH_OK);return d;
}
static uint32_t word(FILE*f){unsigned char b[4];if(fread(b,1,4,f)!=4)abort();return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
int main(int argc,char**argv){if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 2;uint32_t count=word(f);CohEntCostumeDictionary*d=dictionary();State*s=malloc(sizeof(*s));if(!s)abort();
 for(unsigned which=0;which<count;which++){
  unsigned bytes=word(f),bits=word(f),begin=word(f),aligned=word(f),full=word(f),expected[10];for(unsigned i=0;i<10;i++)expected[i]=word(f);
  unsigned char*data=malloc(bytes);if(!data||fread(data,1,bytes,f)!=bytes)abort();
  init(s,data,bytes,bits,aligned,begin,d);ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_OK);ENSURE(s->reader.cursor==bits);if(full){unsigned stages[]={4,5,6,7,8,9,10,11,12};for(unsigned i=0;i<9;i++)ENSURE(s->out.stages[stages[i]].end_bit==expected[i]);ENSURE(s->out.dictionary_manifest_matched);}
  unsigned loan_count=s->owner.acquires;
  /* Every bit of small front profiles, stage boundaries and densely sampled
   * long bodies plus the last64 bits: each later failure rolls back all output. */
  for(unsigned cut=begin;cut<bits;cut++)if(!full||cut%97==0||bits-cut<=64){init(s,data,bytes,cut,aligned,begin,d);ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK);cuts++;}
  for(unsigned i=0;i<loan_count;i++)for(unsigned mode=1;mode<=6;mode++){init(s,data,bytes,bits,aligned,begin,d);s->owner.fail_at=i+1;s->owner.mode=mode;s->owner.alias=data;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)!=COH_OK);ENSURE(s->owner.acquires==i+1);loan_controls++;}
  init(s,data,bytes,bits,aligned,begin,d);ENSURE(parse(s,1,0)==COH_LIMIT);
  init(s,data,bytes,bits,aligned,begin,d);ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,COH_SELECTED_RECORD_RAM_MAX)==COH_LIMIT);
  init(s,data,bytes,bits,aligned,begin,d);s->context.selected_dbid++;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
  init(s,data,bytes,bits,aligned,begin,d);s->prior.present=1;s->prior.create_packet=10;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
  init(s,data,bytes,bits,aligned,begin,d);s->prior.delete_packet=11;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);
  if(full){init(s,data,bytes,bits,aligned,begin,d);s->context.expected_dictionary_sha256[0]^=1;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_STATE);}
  init(s,data,bytes,bits,aligned,begin,d);s->context.costume_dictionary=(const CohEntCostumeDictionary*)&s->out;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
  init(s,data,bytes,bits,aligned,begin,d);s->memory.context=&s->context;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
  init(s,data,bytes,bits,aligned,begin,d);s->reader.bytes.data=(const unsigned char*)&s->out;ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_INVALID);
  /* Preserve a packet trailer: successful record end is not transport end. */
  unsigned char*trailer=calloc(bytes+16,1);if(!trailer)abort();memcpy(trailer,data,bytes);init(s,trailer,bytes+16,bits+64,aligned,begin,d);ENSURE(parse(s,COH_SELECTED_RECORD_RAM_MAX,0)==COH_OK&&s->reader.cursor==bits);free(trailer);
  for(unsigned at=begin/8;at<bytes;at+=full?19:1){data[at]^=0x81;init(s,data,bytes,bits,aligned,begin,d);(void)parse(s,COH_SELECTED_RECORD_RAM_MAX,0);data[at]^=0x81;mutations++;}
  free(data);
 }
 ENSURE(fgetc(f)==EOF);fclose(f);free(s);coh_ent_costume_dictionary_free(d);printf("{\"checks\":%lu,\"fixtures\":%u,\"successes\":%lu,\"refusals\":%lu,\"truncations\":%lu,\"byte_mutations\":%lu,\"loan_controls\":%lu}\n",checks,count,successes,refusals,cuts,mutations,loan_controls);return 0;
}

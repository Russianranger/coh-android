#include "coh_attrib_description.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations,cancellations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"attribute full %u: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{uint32_t key,power,type,server,chance,mag;const char*name;}ExpectedMod;
typedef struct{const unsigned char*wire;size_t bytes,bits,begin;unsigned mode,new_target,has_target,target,mod_count;const uint32_t*values,*buff;const ExpectedMod*mods;}Fixture;
typedef struct{const unsigned char*wire;size_t bytes,bits,begin;unsigned mode;CohAttribMonitor expected;}MonitorFixture;
typedef struct{const unsigned char*wire;size_t bytes,bits;unsigned mode,status,count;}ControlFixture;
#include "description-fixtures.h"
typedef struct{unsigned calls,cancel_at;}Control;
static int poll(void*opaque){Control*c=opaque;c->calls++;return c->calls==c->cancel_at;}
static CohStatus digest(void*context,CohBytes input,uint8_t out[32]){(void)context;SHA256(input.data,input.size,out);return COH_OK;}
typedef struct{CohRepReader reader;CohAttribDescription out,before;CohAttribDescriptionWorkspace work;CohAttribReadControl control;Control cancellation;uint8_t sha[32];}State;
static void init(State*s,const unsigned char*wire,size_t bytes,size_t bits,size_t begin,unsigned mode,const CohAttributeDictionary*d){memset(s,0,sizeof(*s));CHECK(coh_rep_reader_bounded(&s->reader,(CohBytes){wire,bytes},bits,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);s->reader.cursor=begin;memcpy(s->sha,d->input_sha256,32);s->control=(CohAttribReadControl){{poll,&s->cancellation},sizeof(s->cancellation),0};memset(&s->out,0xa5,sizeof(s->out));}
static CohStatus parse(State*s,const CohAttributeDictionary*d,size_t budget,size_t retained){CohRepReader before=s->reader;s->before=s->out;CohStatus status=coh_attrib_description_read(&s->reader,d,d?s->sha:NULL,d?123:0,&s->control,&s->out,&s->work,budget,retained);if(status!=COH_OK)CHECK(!memcmp(&before,&s->reader,sizeof(before))&&!memcmp(&s->before,&s->out,sizeof(s->out)));else CHECK(s->out.raw_description_validated&&!s->out.original_state_applied&&!s->out.dictionary_authority&&!s->out.actor_authority);return status;}
int main(int argc,char**argv){if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 2;unsigned char input[5892];CHECK(fread(input,1,sizeof(input),f)==sizeof(input)&&fgetc(f)==EOF);fclose(f);CohAttributeDictionary*d=malloc(sizeof(*d));CohAttributeDictionaryWorkspace*dw=malloc(sizeof(*dw));State*s=malloc(sizeof(*s));CHECK(d&&dw&&s);CohCostumeImportDigest di={digest,NULL,0,0};uint8_t hash[32];SHA256(input,sizeof(input),hash);CHECK(coh_attribute_dictionary_read((CohBytes){input,sizeof(input)},123,hash,&di,d,dw,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==COH_OK);CHECK(d->row_count==69);
 for(unsigned i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*v=&fixtures[i];init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);CohStatus status=parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0);CHECK(status==COH_OK&&s->reader.cursor==v->bits&&s->out.end_bit==v->bits&&s->out.begin_bit==v->begin&&s->out.full&&s->out.new_target==v->new_target&&s->out.has_target==v->has_target&&s->out.target_server_index==v->target&&s->out.modifier_count==v->mod_count&&s->out.value_count==69&&s->out.schema_input_lease==123&&!memcmp(s->out.schema_input_sha256,hash,32));unsigned polls=s->cancellation.calls;
  for(unsigned j=0;j<69;j++)CHECK(s->out.value_words[j]==v->values[j]&&s->out.buff[j]==v->buff[j]);
  for(unsigned j=0;j<v->mod_count;j++){const ExpectedMod*e=&v->mods[j];CohAttribModifier*a=&s->out.modifiers[j];CHECK(a->key==e->key&&a->power_crc==e->power&&a->source_type==e->type&&a->server_entity_id==e->server&&a->chance_word==e->chance&&a->magnitude_word==e->mag);CHECK(a->name_bytes==strlen(e->name));if(e->type>=2)CHECK(a->name_offset<s->out.text_bytes&&!strcmp(s->out.text+a->name_offset,e->name));}
  for(unsigned bit=v->begin;bit<v->bits;bit++){init(s,v->wire,v->bytes,bit,v->begin,v->mode,d);CHECK(parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)!=COH_OK);cuts++;}
  if(i%16==0){
   for(unsigned call=1;call<=polls;call++){init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);s->cancellation.cancel_at=call;CHECK(parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_CANCELLED);cancellations++;}
   init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);CHECK(parse(s,NULL,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_UNSUPPORTED);init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);s->sha[0]^=1;CHECK(parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_STATE);
   init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);CHECK(parse(s,d,1,0)==COH_LIMIT&&s->cancellation.calls==0);init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);CHECK(parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,SIZE_MAX)==COH_LIMIT&&s->cancellation.calls==0);
   init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);CHECK(coh_attrib_description_read(&s->reader,d,s->sha,124,&s->control,&s->out,&s->work,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_STATE);init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);s->control.cancel.context=&s->out;CHECK(coh_attrib_description_read(&s->reader,d,s->sha,123,&s->control,&s->out,&s->work,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_INVALID);
   unsigned char*trailer=calloc(v->bytes+8,1);CHECK(trailer);memcpy(trailer,v->wire,v->bytes);init(s,trailer,v->bytes+8,v->bits+64,v->begin,v->mode,d);CHECK(parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_OK&&s->reader.cursor==v->bits);free(trailer);
   for(unsigned at=v->begin/8;at<v->bytes;at+=v->bytes/21+1){unsigned char*wire=malloc(v->bytes);CHECK(wire);memcpy(wire,v->wire,v->bytes);wire[at]^=0x81;init(s,wire,v->bytes,v->bits,v->begin,v->mode,d);(void)parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0);free(wire);mutations++;}
  }
 }
 for(unsigned i=0;i<sizeof(monitors)/sizeof(monitors[0]);i++){
  const MonitorFixture*v=&monitors[i];init(s,v->wire,v->bytes,v->bits,v->begin,v->mode,d);CHECK(parse(s,NULL,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==COH_OK&&!s->out.full&&s->reader.cursor==v->bits&&s->out.new_target==v->expected.new_target&&s->out.modifier_count==0&&s->out.value_count==0);for(unsigned j=0;j<11;j++){CohAttribMonitorSlot*a=&s->out.monitor.slots[j];const CohAttribMonitorSlot*e=&v->expected.slots[j];CHECK(a->present==e->present&&a->key==e->key&&a->value_word==e->value_word&&a->buff==e->buff);}
 }
 for(unsigned i=0;i<sizeof(bound_controls)/sizeof(bound_controls[0]);i++){const ControlFixture*v=&bound_controls[i];init(s,v->wire,v->bytes,v->bits,0,v->mode,d);CHECK(parse(s,d,COH_ATTRIB_DESCRIPTION_RAM_MAX,0)==(CohStatus)v->status);if(!v->status)CHECK(s->out.modifier_count==v->count&&s->reader.cursor==v->bits);if(!v->status&&v->bytes>65536)CHECK(s->out.text_bytes==65536&&s->out.modifiers[0].name_bytes==65535&&s->out.modifiers[0].name_offset==0);}
 free(s);free(dw);free(d);printf("{\"checks\":%lu,\"full_cases\":%zu,\"monitor_cases\":%zu,\"truncations\":%lu,\"mutations\":%lu,\"cancel_controls\":%lu,\"dictionary_authority\":false,\"actor_authority\":false}\n",checks,sizeof(fixtures)/sizeof(fixtures[0]),sizeof(monitors)/sizeof(monitors[0]),cuts,mutations,cancellations);return 0;}

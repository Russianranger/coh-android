#include "coh_attrib_description.h"
#include <math.h>
#include <string.h>
typedef struct{const void*p;size_t n;}Span;
static int valid(Span a){return a.p?(uintptr_t)a.p<=UINTPTR_MAX-a.n:!a.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static CohStatus scalar(CohRepReader*r,unsigned n,uint32_t*v){CohStatus s=coh_rep_read(r,n,v);return s==COH_OK&&n<32&&*v>=(UINT32_C(1)<<n)?COH_INVALID:s;}
static CohStatus automatic(CohRepReader*r,uint32_t*v){static const unsigned widths[4]={2,10,24,32};uint32_t tag;CohStatus s=scalar(r,2,&tag);if(s!=COH_OK)return s;return scalar(r,widths[tag],v);}
static CohStatus floatword(CohRepReader*r,uint32_t*v){CohStatus s=scalar(r,32,v);float f;memcpy(&f,v,4);return s==COH_OK&&!isfinite(f)?COH_INVALID:s;}
#define CALL(x) do{status=(x);if(status!=COH_OK)return status;}while(0)
static CohStatus cancelled(const CohAttribReadControl*c){return c&&c->cancel.poll&&c->cancel.poll(c->cancel.context)?COH_CANCELLED:COH_OK;}
CohStatus coh_attrib_description_read(CohRepReader*reader,const CohAttributeDictionary*schema,
 const uint8_t expected[32],uint64_t lease,const CohAttribReadControl*control,
 CohAttribDescription*out,CohAttribDescriptionWorkspace*w,size_t budget,size_t retained){
 if(!reader||!out||!w||!budget||budget>COH_ATTRIB_DESCRIPTION_RAM_MAX)return COH_INVALID;
 if(control&&((!control->cancel.context&&control->context_bytes)||(control->cancel.context&&!control->context_bytes)||(!control->cancel.poll&&(control->cancel.context||control->context_bytes||control->scratch_reserve))))return COH_INVALID;
 CohRepReader r=*reader;uint32_t ignored;CohStatus status;CALL(coh_rep_read(&r,0,&ignored));
 Span spans[]={{reader,sizeof(*reader)},{out,sizeof(*out)},{w,sizeof(*w)},{r.bytes.data,r.bytes.size},{schema,schema?sizeof(*schema):0},{expected,expected?32:0},{control,control?sizeof(*control):0},{control?control->cancel.context:NULL,control?control->context_bytes:0},{NULL,0}};
 for(unsigned i=0;i<8;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;}
 if(schema){spans[8]=(Span){schema->input.data,schema->input.size};if(!valid(spans[8])||!spans[8].p||!spans[8].n||spans[8].n>COH_ATTRIBUTE_DICTIONARY_INPUT_MAX)return COH_INVALID;for(unsigned i=0;i<8;i++)if(overlap(spans[8],spans[i]))return COH_INVALID;}
 size_t charge=COH_ATTRIB_DESCRIPTION_STACK_RESERVE;
 for(unsigned i=0;i<9;i++){if(spans[i].n>budget||charge>budget-spans[i].n)return COH_LIMIT;charge+=spans[i].n;}
 size_t scratch=control?control->scratch_reserve:0;if(scratch>budget-charge)return COH_LIMIT;charge+=scratch;if(retained>budget-charge)return COH_LIMIT;
 CALL(cancelled(control));CohAttribDescription*c=&w->candidate;memset(c,0,sizeof(*c));c->begin_bit=r.cursor;CALL(scalar(&r,1,&c->new_target));CALL(scalar(&r,1,&c->full));
 if(!c->full){
  r=*reader;CALL(coh_attrib_monitor_read(&r,&c->monitor,&w->monitor,budget,charge-sizeof(c->monitor)-sizeof(w->monitor)-COH_ATTRIB_MONITOR_STACK_RESERVE-r.bytes.size));c->new_target=c->monitor.new_target;
 }else{
  if(!schema||!expected||!lease)return COH_UNSUPPORTED;
  if(!schema->raw_schema_validated||!schema->schema_crc_matched||schema->schema_crc!=UINT32_C(0x315acdb1)||schema->row_count>COH_ATTRIBUTE_DICTIONARY_ROWS_MAX||schema->category_count>COH_ATTRIBUTE_DICTIONARY_CATEGORIES_MAX||schema->input_lease_token!=lease||memcmp(schema->input_sha256,expected,32))return COH_STATE;
  memcpy(c->schema_input_sha256,schema->input_sha256,32);c->schema_input_lease=lease;c->value_count=schema->row_count;
  CALL(scalar(&r,1,&c->has_target));if(c->has_target)CALL(scalar(&r,32,&c->target_server_index));
  for(unsigned i=0;i<c->value_count;i++){CALL(cancelled(control));CALL(floatword(&r,&c->value_words[i]));CALL(scalar(&r,2,&c->buff[i]));}
  for(;;){
   uint32_t present;CALL(cancelled(control));CALL(scalar(&r,1,&present));if(!present)break;if(c->modifier_count>=COH_ATTRIB_MODIFIERS_MAX)return COH_LIMIT;CohAttribModifier*m=&c->modifiers[c->modifier_count];CALL(coh_rep_pack(&r,10,&m->key));CALL(automatic(&r,&m->power_crc));CALL(scalar(&r,2,&m->source_type));
   if(m->source_type==2||m->source_type==3){m->name_offset=c->text_bytes;for(;;){uint32_t b;CALL(scalar(&r,8,&b));if(c->text_bytes>=COH_ATTRIB_SOURCE_TEXT_MAX)return COH_LIMIT;c->text[c->text_bytes++]=(char)b;if(!b)break;m->name_bytes++;}CALL(coh_rep_pack(&r,20,&m->server_entity_id));}
   CALL(floatword(&r,&m->chance_word));CALL(floatword(&r,&m->magnitude_word));c->modifier_count++;
  }
 }
 CALL(cancelled(control));c->end_bit=r.cursor;c->raw_description_validated=1;*out=*c;*reader=r;return COH_OK;
}

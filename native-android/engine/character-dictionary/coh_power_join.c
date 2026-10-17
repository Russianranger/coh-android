#include "coh_power_join.h"
#include <string.h>
#include "../stash32/coh_stash32.h"
typedef struct {const void *p;size_t n;} Span;
typedef struct {CohBytes input;size_t at;} Cursor;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static CohStatus charge(size_t *used,size_t n,size_t budget){if(*used>budget||n>budget-*used)return COH_LIMIT;*used+=n;return COH_OK;}
static CohStatus word(Cursor*c,uint32_t*out){if(c->at>c->input.size||c->input.size-c->at<4)return COH_STATE;const uint8_t*p=c->input.data+c->at;*out=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;c->at+=4;return COH_OK;}
static CohStatus text(Cursor*c,CohBytes*out){if(c->at>c->input.size||c->input.size-c->at<2)return COH_STATE;const uint8_t*p=c->input.data+c->at;size_t n=(size_t)p[0]|(size_t)p[1]<<8,padded=(n+2+3)&~(size_t)3;if(n>=260)return COH_UNSUPPORTED;if(padded>c->input.size-c->at)return COH_STATE;for(size_t i=0;i<n;i++)if(!p[2+i]||p[2+i]>127)return COH_UNSUPPORTED;*out=(CohBytes){p+2,n};c->at+=padded;return COH_OK;}
static CohStatus crc(CohBytes name,uint32_t*out){uint32_t h=0;if(!name.size)return COH_UNSUPPORTED;for(size_t j=0;j<name.size;j++){unsigned b=name.data[j];if(!b||b>127)return COH_UNSUPPORTED;if(b>='A'&&b<='Z')b+=32;if(b=='\\')b='/';h^=b;for(unsigned k=0;k<8;k++)h=(h>>1)^((0u-(h&1u))&UINT32_C(0x82f63b78));}if(!h)return COH_UNSUPPORTED;*out=h;return COH_OK;}
static CohStatus cancelled(const CohPowerStreamDictionary*p){return p->provider.cancelled&&p->provider.cancelled(p->provider.context)?COH_CANCELLED:COH_OK;}
static CohStatus power_name(const CohPowerStreamDictionary*p,uint32_t index,int short_name,uint8_t*buffer,CohBytes*out,size_t*work){
 if(index>=p->count)return COH_STATE;
 const CohPowerStreamEntry*e=&p->entries[index];uint32_t at=short_name?e->short_name:e->full_name;size_t n=short_name?e->short_name_bytes:e->full_name_bytes;
 if(!n||n>=260)return COH_UNSUPPORTED;
 if(e->begin>e->end||e->end>p->provider.input_bytes||at<e->begin||at>e->end||n>e->end-at)return COH_STATE;
 if(n>*work)return COH_LIMIT;
 *work-=n;CohStatus s=cancelled(p);if(s!=COH_OK)return s;s=p->provider.read_at(p->provider.context,at,buffer,n);if(s!=COH_OK)return s;
 for(size_t i=0;i<n;i++)if(!buffer[i]||buffer[i]>127)return COH_UNSUPPORTED;
 s=cancelled(p);if(s!=COH_OK)return s;*out=(CohBytes){buffer,n};return COH_OK;
}
static CohStatus find_power(const CohPowerStreamDictionary*p,CohBytes name,uint32_t*out,size_t*work){
 if(name.size>*work)return COH_LIMIT;
 *work-=name.size;uint32_t key;CohStatus status=crc(name,&key);if(status!=COH_OK)return status;
 if(p->index_slots<8||p->index_slots>COH_POWER_STREAM_SLOT_MAX||(p->index_slots&(p->index_slots-1)))return COH_STATE;
 uint32_t slot=coh_stash32_int_hash(key,COH_STASH32_DEFAULT_SEED)&(p->index_slots-1),probe=1;
 for(unsigned i=0;i<COH_POWER_STREAM_SLOT_MAX;i++){
  if(!*work)return COH_LIMIT;
  (*work)--;uint32_t row=p->slots[slot];if(!row)return COH_NOT_FOUND;if(row>p->count)return COH_STATE;if(p->entries[row-1].crc==key){*out=row-1;return COH_OK;}slot=(slot+probe*probe)&(p->index_slots-1);probe++;
 }
 return COH_LIMIT;
}
static unsigned fold(unsigned ch){return ch>='A'&&ch<='Z'?ch+32:ch;}
static CohStatus find_set(const CohPowerSetDictionary*s,CohBytes key,uint32_t*out,size_t*work){
 if(key.size>=260)return COH_UNSUPPORTED;
 if(key.size>*work)return COH_LIMIT;
 *work-=key.size;for(size_t i=0;i<key.size;i++)if(!key.data[i]||key.data[i]>127)return COH_UNSUPPORTED;
 if(s->index_slots<8||s->index_slots>COH_POWER_SET_INDEX_SLOTS||(s->index_slots&(s->index_slots-1)))return COH_STATE;
 uint32_t hash;CohStatus status=coh_stash32_string_hash(key,COH_STASH32_DEFAULT_SEED,&hash);if(status!=COH_OK)return status;
 uint32_t slot=hash&(s->index_slots-1),probe=1;
 for(unsigned i=0;i<COH_STASH32_SLOT_MAX;i++){
  if(!*work)return COH_LIMIT;
  (*work)--;uint32_t row=s->slots[slot];if(!row)return COH_NOT_FOUND;if(row>s->count)return COH_STATE;
  CohPowerSetSpan span=s->entries[row-1].full_name;if(span.begin>span.end||span.end>s->input.size)return COH_STATE;
  Cursor cursor={{s->input.data+span.begin,span.end-span.begin},0};CohBytes other;status=text(&cursor,&other);if(status!=COH_OK)return status;if(cursor.at!=cursor.input.size)return COH_STATE;
  if(key.size==other.size){if(key.size>*work)return COH_LIMIT;*work-=key.size;size_t j=0;while(j<key.size&&fold(key.data[j])==fold(other.data[j]))j++;if(j==key.size){*out=row-1;return COH_OK;}}
  slot=(slot+probe*probe)&(s->index_slots-1);probe++;
 }
 return COH_LIMIT;
}
static CohStatus build_set(CohPowerJoin*c,uint32_t row,size_t*work){
 const CohPowerSetDictionary*s=c->sets;const CohPowerStreamDictionary*p=c->powers;CohPowerJoinSet*link=&c->set_links[row];CohPowerSetSpan record=s->entries[row].record;if(record.begin>record.end||record.end>s->input.size)return COH_STATE;size_t scan=(size_t)(record.end-record.begin)*2;if(scan>*work)return COH_LIMIT;*work-=scan;CohBytes full,encoded;CohStatus status=coh_power_sets_field(s,row,1,&encoded);if(status!=COH_OK)return status;Cursor name_cursor={encoded,0};status=text(&name_cursor,&full);if(status!=COH_OK||name_cursor.at!=encoded.size)return status==COH_OK?COH_STATE:status;
 status=coh_power_sets_field(s,row,21,&encoded);if(status!=COH_OK)return status;Cursor refs={encoded,0};uint32_t n;status=word(&refs,&n);if(status!=COH_OK)return status;if(n>COH_POWER_JOIN_REF_MAX-c->power_reference_count)return COH_LIMIT;link->first=c->power_reference_count;link->count=n;
 for(uint32_t i=0;i<n;i++){
  if(!*work)return COH_LIMIT;
  (*work)--;CohBytes declared;status=text(&refs,&declared);if(status!=COH_OK)return status;uint32_t raw,chosen;status=find_power(p,declared,&raw,work);if(status!=COH_OK)return status;
  uint8_t short_buffer[260],full_buffer[260],alternate[512];CohBytes short_name,original;status=power_name(p,raw,1,short_buffer,&short_name,work);if(status!=COH_OK)return status;status=power_name(p,raw,0,full_buffer,&original,work);if(status!=COH_OK)return status;
  if(full.size+1+short_name.size>=sizeof(alternate))return COH_LIMIT;
  size_t len=full.size+1+short_name.size;if(len>*work)return COH_LIMIT;*work-=len;memcpy(alternate,full.data,full.size);alternate[full.size]='.';memcpy(alternate+full.size+1,short_name.data,short_name.size);chosen=raw;
  if(len!=original.size||memcmp(alternate,original.data,len)){
   status=find_power(p,(CohBytes){alternate,len},&chosen,work);if(status!=COH_OK)return status;c->alternate_name_count++;
  }
  c->power_links[c->power_reference_count++]=(CohPowerJoinReference){raw,chosen};
 }
 if(refs.at!=encoded.size)return COH_STATE;
 c->reached_set_count++;return COH_OK;
}
CohStatus coh_power_join_prepare(const CohPowerCategoryDictionary*categories,const CohPowerSetDictionary*sets,const CohPowerStreamDictionary*powers,CohPowerJoin*out,CohPowerJoinWorkspace*w,size_t budget,size_t retained){
 if(!categories||!sets||!powers||!out||!w||!budget||budget>COH_POWER_JOIN_RAM_MAX)return COH_INVALID;
 Span spans[]={{categories,sizeof(*categories)},{sets,sizeof(*sets)},{powers,sizeof(*powers)},{out,sizeof(*out)},{w,sizeof(*w)},{sets->input.data,sets->input.size},{powers->provider.context,powers->provider.context_bytes}};size_t used=COH_POWER_JOIN_STACK_RESERVE;
 for(unsigned i=0;i<sizeof(spans)/sizeof(spans[0]);i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;CohStatus status=charge(&used,spans[i].n,budget);if(status!=COH_OK)return status;}
 CohStatus status=charge(&used,powers->provider.scratch_reserve,budget);if(status!=COH_OK)return status;status=charge(&used,retained,budget);if(status!=COH_OK)return status;
 if(!categories->raw_schema_validated||!categories->source_lease||categories->count>COH_CATEGORY_MAX||categories->set_count>COH_CATEGORY_REFS_MAX||categories->text_bytes>COH_CATEGORY_TEXT_MAX||!sets->raw_schema_validated||!sets->input_lease||!sets->source_constructor_accepted||sets->count>COH_POWER_SET_MAX||!sets->input.data||sets->input.size>COH_POWER_SET_INPUT_MAX||!powers->raw_schema_validated||!powers->provider.lease||!powers->provider.context||!powers->provider.context_bytes||!powers->provider.read_at||!powers->provider.input_bytes||powers->provider.input_bytes>COH_POWER_STREAM_MAX||powers->count>COH_POWER_STREAM_RECORD_MAX||powers->duplicate_count)return COH_STATE;
 status=cancelled(powers);if(status!=COH_OK)return status;CohPowerJoin*c=&w->candidate;memset(c,0,sizeof(*c));c->categories=categories;c->sets=sets;c->powers=powers;c->category_count=categories->count;c->set_count=sets->count;c->power_count=powers->count;c->category_reference_count=categories->set_count;
 for(uint32_t i=0;i<COH_POWER_SET_MAX;i++){c->set_links[i].first=COH_POWER_JOIN_NONE;c->set_links[i].parent_category=COH_POWER_JOIN_NONE;}
 for(uint32_t i=0;i<COH_POWER_STREAM_RECORD_MAX;i++)c->power_parent_sets[i]=COH_POWER_JOIN_NONE;
 size_t work=COH_POWER_JOIN_WORK_MAX;uint32_t next_ref=0;
 for(uint32_t ci=0;ci<categories->count;ci++){
  const CohPowerCategoryEntry*cat=&categories->entries[ci];if(cat->set_first!=next_ref||cat->set_count>categories->set_count-next_ref)return COH_STATE;
  for(uint32_t ri=0;ri<cat->set_count;ri++){
   if(!work)return COH_LIMIT;
   work--;status=cancelled(powers);if(status!=COH_OK)return status;CohOriginText name=categories->sets[next_ref];if(name.offset>categories->text_bytes||name.size>categories->text_bytes-name.offset)return COH_STATE;uint32_t row;status=find_set(sets,(CohBytes){(const uint8_t*)categories->text+name.offset,name.size},&row,&work);if(status!=COH_OK)return status;c->category_sets[next_ref++]=row;
   if(c->set_links[row].first==COH_POWER_JOIN_NONE){status=build_set(c,row,&work);if(status!=COH_OK)return status;}
  }
 }
 if(next_ref!=categories->set_count)return COH_STATE;
 /* Original reverse category/set/power loops overwrite parents: earliest source
  * category/reference wins, while unreferenced raw objects keep no parent. */
 size_t parent_work=0;
 for(uint32_t i=0;i<c->category_reference_count;i++){
  size_t cost=(size_t)c->set_links[c->category_sets[i]].count+1;
  if(cost>work-parent_work)return COH_LIMIT;
  parent_work+=cost;
 }
 work-=parent_work;
 for(uint32_t ci=categories->count;ci>0;ci--){
  const CohPowerCategoryEntry*cat=&categories->entries[ci-1];
  for(uint32_t ri=cat->set_count;ri>0;ri--){
   status=cancelled(powers);if(status!=COH_OK)return status;
   uint32_t row=c->category_sets[cat->set_first+ri-1];CohPowerJoinSet*link=&c->set_links[row];link->parent_category=ci-1;
   for(uint32_t pi=link->count;pi>0;pi--){
    if(!(pi%256)){status=cancelled(powers);if(status!=COH_OK)return status;}
    c->power_parent_sets[c->power_links[link->first+pi-1].resolved_power]=row;
   }
  }
 }

 status=cancelled(powers);if(status!=COH_OK)return status;c->complete_forward_join=c->parent_projection=1;*out=*c;return COH_OK;
}

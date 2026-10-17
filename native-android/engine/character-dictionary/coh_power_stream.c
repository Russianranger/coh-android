#include "coh_power_stream.h"
#include "power_stream_schema.inc"
#include "../stash32/coh_stash32.h"
#include <string.h>
typedef struct{const void*p;size_t n;} Span;
typedef struct {const CohPowerStreamProvider*p;CohPowerStreamWorkspace*w;uint32_t at,loaded,used;CohStatus status;} Reader;
static int valid(Span a){return a.p?(uintptr_t)a.p<=UINTPTR_MAX-a.n:!a.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static void need(Reader*r,int yes,CohStatus s){if(r->status==COH_OK&&!yes)r->status=s;}
static uint8_t byte(Reader*r){
 if(r->status!=COH_OK)return 0;
 if(r->at>=r->p->input_bytes){r->status=COH_INVALID;return 0;}
 if(r->used==r->loaded){
  if(r->p->cancelled&&r->p->cancelled(r->p->context)){r->status=COH_CANCELLED;return 0;}
  uint32_t n=r->p->input_bytes-r->at;if(n>sizeof(r->w->buffer))n=sizeof(r->w->buffer);
  r->status=r->p->read_at(r->p->context,r->at,r->w->buffer,n);if(r->status!=COH_OK)return 0;
  r->status=r->p->update(r->p->context,(CohBytes){r->w->buffer,n});if(r->status!=COH_OK)return 0;r->loaded=n;r->used=0;
 }
 r->at++;return r->w->buffer[r->used++];
}
static uint32_t word(Reader*r){uint32_t v=0;for(unsigned i=0;i<4;i++)v|=(uint32_t)byte(r)<<(8*i);return v;}
static uint32_t crcbyte(uint32_t h,unsigned c){if(c>='A'&&c<='Z')c+=32;if(c=='\\')c='/';h^=c;for(unsigned i=0;i<8;i++)h=(h>>1)^((0u-(h&1u))&UINT32_C(0x82f63b78));return h;}
/* Offsets point to raw text bytes after the Pascal length, not C strings. */
static uint16_t text(Reader*r,uint32_t limit,uint32_t*offset,uint32_t*hash,const char*literal){
 uint32_t n=byte(r);n|=(uint32_t)byte(r)<<8;need(r,n<12000,COH_LIMIT);need(r,r->at<=limit&&n<=limit-r->at,COH_INVALID);
 if(offset)*offset=r->at;
 uint32_t h=0;
 for(uint32_t i=0;i<n&&r->status==COH_OK;i++){unsigned c=byte(r);need(r,c!=0,COH_INVALID);if(hash){need(r,c<128&&n<260,COH_UNSUPPORTED);h=crcbyte(h,c);}if(literal)need(r,literal[i]&&c==(unsigned char)literal[i],COH_UNSUPPORTED);}
 if(literal&&r->status==COH_OK)need(r,strlen(literal)==n,COH_UNSUPPORTED);
 unsigned pad=(4-(n+2)%4)%4;for(unsigned i=0;i<pad&&r->status==COH_OK;i++)(void)byte(r);need(r,r->at<=limit,COH_INVALID);if(hash)*hash=h;return(uint16_t)n;
}
static uint32_t segment(Reader*r,uint32_t parent){uint32_t n=word(r);need(r,r->at<=parent&&n<=parent-r->at,COH_INVALID);return r->status==COH_OK?r->at+n:r->at;}
static void words(Reader*r,uint32_t n,uint32_t end){need(r,r->at<=end&&n<=(end-r->at)/4,COH_INVALID);for(uint32_t i=0;i<n&&r->status==COH_OK;i++)(void)word(r);}
static void record(Reader*r,unsigned table,unsigned depth,uint32_t parent,CohPowerStreamEntry*entry){
 need(r,table<5&&depth<=3,COH_LIMIT);if(r->status!=COH_OK)return;
 uint32_t begin=r->at,end=segment(r,parent);need(r,end-begin<=65536,COH_LIMIT);r->w->candidate.table_counts[table]++;
 uint32_t hash=0;
 for(unsigned i=0;i<power_field_counts[table]&&r->status==COH_OK;i++){
  PowerField f=power_fields[table][i];uint32_t n;
  switch(f.kind){
  case 1:if(table==0&&i==0)entry->full_name_bytes=text(r,end,&entry->full_name,&hash,NULL);else if(table==0&&i==3)entry->short_name_bytes=text(r,end,&entry->short_name,NULL,NULL);else(void)text(r,end,NULL,NULL,NULL);break;
  case 9:need(r,word(r)<=255,COH_INVALID);break;
  case 3:case 5:n=word(r);if(table==0&&i==1)entry->crc=n;break;
  case 2:n=word(r);need(r,r->at<=end&&n<=(end-r->at)/4,COH_INVALID);for(uint32_t j=0;j<n&&r->status==COH_OK;j++)(void)text(r,end,NULL,NULL,NULL);break;
  case 4:n=word(r);words(r,n,end);break;
  case 6:n=word(r);need(r,r->at<=end&&n<=(end-r->at)/4,COH_INVALID);for(uint32_t j=0;j<n&&r->status==COH_OK;j++)record(r,f.sub,depth+1,end,entry);break;
  case 7:words(r,3,end);break;
  case 8:for(unsigned j=0;j<4&&r->status==COH_OK;j++)need(r,word(r)<=255,COH_INVALID);break;
  default:need(r,0,COH_STATE);break;
  }
  need(r,r->at<=end,COH_INVALID);
 }
 need(r,r->at==end,COH_INVALID);if(table==0){entry->begin=begin;entry->end=end;need(r,hash==entry->crc,COH_STATE);need(r,entry->crc!=0,COH_UNSUPPORTED);}
}
static CohStatus index_insert(CohPowerStreamDictionary*d,uint32_t row,uint32_t*work){
 uint32_t crc=d->entries[row].crc,slot=coh_stash32_int_hash(crc,COH_STASH32_DEFAULT_SEED)&(d->index_slots-1),probe=1;
 for(unsigned i=0;i<COH_POWER_STREAM_SLOT_MAX;i++){
  if(!(i%256)&&d->provider.cancelled&&d->provider.cancelled(d->provider.context))return COH_CANCELLED;
  if(!*work)return COH_LIMIT;
  (*work)--;uint32_t prior=d->slots[slot];if(!prior){d->slots[slot]=row+1;d->unique_count++;return COH_OK;}
  if(d->entries[prior-1].crc==crc){d->duplicate_count++;return COH_OK;}slot=(slot+probe*probe)&(d->index_slots-1);probe++;
 }return COH_LIMIT;
}
CohStatus coh_power_stream_read(const CohPowerStreamProvider*p,const uint8_t expected[32],CohPowerStreamDictionary*out,CohPowerStreamWorkspace*w,size_t budget,size_t retained){
 if(!p||!expected||!out||!w||!p->context||!p->context_bytes||!p->lease||!p->input_bytes||p->input_bytes>COH_POWER_STREAM_MAX||!p->read_at||!p->begin||!p->update||!p->finish||!p->abort||!budget||budget>COH_POWER_STREAM_RAM_MAX)return COH_INVALID;
 Span spans[]={{p,sizeof(*p)},{expected,32},{out,sizeof(*out)},{w,sizeof(*w)},{p->context,p->context_bytes}};size_t charge=COH_POWER_STREAM_STACK_RESERVE;
 for(unsigned i=0;i<5;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;if(spans[i].n>budget||charge>budget-spans[i].n)return COH_LIMIT;charge+=spans[i].n;}
 if(p->scratch_reserve>budget-charge)return COH_LIMIT;
 charge+=p->scratch_reserve;if(retained>budget-charge)return COH_LIMIT;unsigned any=0;for(unsigned i=0;i<32;i++)any|=expected[i];if(!any)return COH_STATE;
 CohPowerStreamDictionary*c=&w->candidate;memset(c,0,sizeof(*c));c->provider=*p;Reader r={p,w,0,0,0,COH_OK};CohStatus status=p->begin(p->context);if(status!=COH_OK){p->abort(p->context);return status;}
 const char*magic="CrypticS";for(unsigned i=0;i<8;i++)need(&r,byte(&r)==(uint8_t)magic[i],COH_INVALID);c->observed_schema_crc=word(&r);
 (void)text(&r,p->input_bytes,NULL,NULL,"Parse6");(void)text(&r,p->input_bytes,NULL,NULL,"Files1");uint32_t files_end=segment(&r,p->input_bytes);c->dependency_count=word(&r);need(&r,r.at<=files_end&&c->dependency_count<=(files_end-r.at)/8,COH_INVALID);
 for(uint32_t i=0;i<c->dependency_count&&r.status==COH_OK;i++){(void)text(&r,files_end,NULL,NULL,NULL);(void)word(&r);need(&r,r.at<=files_end,COH_INVALID);}need(&r,r.at==files_end,COH_INVALID);
 uint32_t root_end=segment(&r,p->input_bytes);need(&r,root_end==p->input_bytes,COH_INVALID);c->count=word(&r);need(&r,c->count<=COH_POWER_STREAM_RECORD_MAX,COH_LIMIT);
 for(uint32_t i=0;i<c->count&&r.status==COH_OK;i++)record(&r,0,0,root_end,&c->entries[i]);
 need(&r,r.at==root_end&&r.at==p->input_bytes,COH_INVALID);
 if(r.status!=COH_OK){p->abort(p->context);return r.status;}
 if(p->cancelled&&p->cancelled(p->context)){p->abort(p->context);return COH_CANCELLED;}
 c->index_slots=8;uint32_t optimal=(c->count*3+1)/2;while(c->index_slots<optimal)c->index_slots*=2;uint32_t work=COH_POWER_STREAM_WORK_MAX;for(uint32_t i=0;i<c->count;i++){status=index_insert(c,i,&work);if(status!=COH_OK){p->abort(p->context);return status;}}
 if(p->cancelled&&p->cancelled(p->context)){p->abort(p->context);return COH_CANCELLED;}
 uint8_t hash[32];status=p->finish(p->context,hash);if(status!=COH_OK){p->abort(p->context);return status;}if(p->cancelled&&p->cancelled(p->context))return COH_CANCELLED;if(memcmp(hash,expected,32))return COH_STATE;memcpy(c->input_sha256,hash,32);c->raw_schema_validated=1;*out=*c;return COH_OK;
}
CohStatus coh_power_stream_find_crc(const CohPowerStreamDictionary*d,uint32_t key,uint32_t*out){
 if(!d||!out||!key)return COH_INVALID;
 Span a={d,sizeof(*d)},b={out,sizeof(*out)};if(!valid(a)||!valid(b)||!valid((Span){d->provider.context,d->provider.context_bytes})||overlap(a,b)||overlap((Span){d->provider.context,d->provider.context_bytes},b))return COH_INVALID;
 if(!d->raw_schema_validated||!d->provider.lease||d->count>COH_POWER_STREAM_RECORD_MAX||d->index_slots<8||d->index_slots>COH_POWER_STREAM_SLOT_MAX||(d->index_slots&(d->index_slots-1)))return COH_STATE;
 uint32_t slot=coh_stash32_int_hash(key,COH_STASH32_DEFAULT_SEED)&(d->index_slots-1),probe=1;for(unsigned i=0;i<COH_POWER_STREAM_SLOT_MAX;i++){uint32_t row=d->slots[slot];if(!row)return COH_NOT_FOUND;if(row>d->count)return COH_STATE;if(d->entries[row-1].crc==key){*out=row-1;return COH_OK;}slot=(slot+probe*probe)&(d->index_slots-1);probe++;}return COH_LIMIT;
}

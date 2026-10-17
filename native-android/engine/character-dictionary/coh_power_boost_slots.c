#include "coh_power_boost_slots.h"
#include "power_stream_schema.inc"
#include <string.h>
typedef struct{const void*p;size_t n;}Span;
typedef struct{const uint8_t*p;uint32_t at,end,max_boosts,boosts_allowed_count,crc,full_crc;CohStatus status;}Cursor;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static CohStatus charge(size_t*used,size_t n,size_t cap){if(*used>cap||n>cap-*used)return COH_LIMIT;*used+=n;return COH_OK;}
static void need(Cursor*r,int ok,CohStatus status){if(r->status==COH_OK&&!ok)r->status=status;}
static uint8_t byte(Cursor*r){if(r->status!=COH_OK)return 0;if(r->at>=r->end){r->status=COH_INVALID;return 0;}return r->p[r->at++];}
static uint32_t word(Cursor*r){uint32_t n=0;for(unsigned i=0;i<4;i++)n|=(uint32_t)byte(r)<<(8*i);return n;}
static uint32_t crcbyte(uint32_t h,unsigned c){if(c>='A'&&c<='Z')c+=32;if(c=='\\')c='/';h^=c;for(unsigned i=0;i<8;i++)h=(h>>1)^((0u-(h&1u))&UINT32_C(0x82f63b78));return h;}
static void text(Cursor*r,uint32_t end,int fullname){uint32_t n=byte(r);n|=(uint32_t)byte(r)<<8;need(r,n<12000&&r->at<=end&&n<=end-r->at,COH_INVALID);uint32_t h=0;for(uint32_t i=0;i<n&&r->status==COH_OK;i++){unsigned ch=byte(r);need(r,ch!=0,COH_INVALID);if(fullname){need(r,ch<128&&n<260,COH_UNSUPPORTED);h=crcbyte(h,ch);}}for(unsigned pad=(4-(n+2)%4)%4;pad&&r->status==COH_OK;pad--)(void)byte(r);need(r,r->at<=end,COH_INVALID);if(fullname)r->full_crc=h;}
static void words(Cursor*r,uint32_t n,uint32_t end){need(r,r->at<=end&&n<=(end-r->at)/4,COH_INVALID);for(uint32_t i=0;i<n&&r->status==COH_OK;i++)(void)word(r);}
static void record(Cursor*r,unsigned table,unsigned depth,uint32_t parent){need(r,table<5&&depth<=3,COH_LIMIT);if(r->status!=COH_OK)return;uint32_t n=word(r);need(r,r->at<=parent&&n<=parent-r->at,COH_INVALID);if(r->status!=COH_OK)return;uint32_t end=r->at+n;
 for(unsigned i=0;i<power_field_counts[table]&&r->status==COH_OK;i++){PowerField f=power_fields[table][i];switch(f.kind){case 1:text(r,end,table==0&&i==0);break;case 9:need(r,word(r)<=255,COH_INVALID);break;case 3:case 5:n=word(r);if(table==0&&i==1)r->crc=n;if(table==0&&i==93)r->max_boosts=n;break;case 2:n=word(r);need(r,r->at<=end&&n<=(end-r->at)/4,COH_INVALID);for(uint32_t j=0;j<n&&r->status==COH_OK;j++)text(r,end,0);break;case 4:n=word(r);if(table==0&&i==80)r->boosts_allowed_count=n;words(r,n,end);break;case 6:n=word(r);need(r,r->at<=end&&n<=(end-r->at)/4,COH_INVALID);for(uint32_t j=0;j<n&&r->status==COH_OK;j++)record(r,f.sub,depth+1,end);break;case 7:words(r,3,end);break;case 8:for(unsigned j=0;j<4&&r->status==COH_OK;j++)need(r,word(r)<=255,COH_INVALID);break;default:need(r,0,COH_STATE);break;}need(r,r->at<=end,COH_INVALID);}need(r,r->at==end,COH_INVALID);
}
static int32_t signed_word(uint32_t n){return n<=INT32_MAX?(int32_t)n:-1-(int32_t)(UINT32_MAX-n);}
static CohStatus cancelled(const CohPowerStreamDictionary*d){return d->provider.cancelled&&d->provider.cancelled(d->provider.context)?COH_CANCELLED:COH_OK;}
CohStatus coh_power_boost_slots_prepare(const CohPowerStreamDictionary*d,const CohSchedules*s,uint32_t row,int32_t level,int32_t bought,uint32_t wire,CohPowerBoostSlots*out,CohPowerBoostSlotsWorkspace*w,size_t budget,size_t retained){
 if(!d||!s||!out||!w||!budget||budget>COH_POWER_SLOT_RAM_MAX)return COH_INVALID;
 Span spans[]={{d,sizeof(*d)},{s,sizeof(*s)},{d->provider.context,d->provider.context_bytes},{out,sizeof(*out)},{w,sizeof(*w)}};size_t used=COH_POWER_SLOT_STACK_RESERVE;
 for(unsigned i=0;i<5;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;CohStatus status=charge(&used,spans[i].n,budget);if(status!=COH_OK)return status;}
 CohStatus status=charge(&used,d->provider.scratch_reserve,budget);if(status!=COH_OK)return status;status=charge(&used,retained,budget);if(status!=COH_OK)return status;
 if(!d->raw_schema_validated||!d->provider.lease||!d->provider.context||!d->provider.context_bytes||!d->provider.read_at||!d->provider.input_bytes||d->provider.input_bytes>COH_POWER_STREAM_MAX||d->count>COH_POWER_STREAM_RECORD_MAX||row>=d->count)return COH_STATE;
 uint32_t validated;status=coh_schedule_count(s,0,0,&validated);if(status!=COH_OK)return status;
 if(wire>2048)return COH_LIMIT;
 const CohPowerStreamEntry*entry=&d->entries[row];if(entry->begin>entry->end||entry->end>d->provider.input_bytes||entry->end-entry->begin<4||entry->end-entry->begin>COH_POWER_SLOT_RECORD_MAX)return COH_STATE;
 uint32_t bytes=entry->end-entry->begin;for(uint32_t at=0;at<bytes;){status=cancelled(d);if(status!=COH_OK)return status;uint32_t n=bytes-at;if(n>4096)n=4096;status=d->provider.read_at(d->provider.context,entry->begin+at,w->record+at,n);if(status!=COH_OK)return status;at+=n;status=cancelled(d);if(status!=COH_OK)return status;}
 Cursor r={w->record,0,bytes,0,0,0,0,COH_OK};record(&r,0,0,bytes);if(r.status!=COH_OK)return r.status;if(r.at!=bytes||r.crc!=entry->crc||r.full_crc!=entry->crc)return COH_STATE;
 int64_t age=(int64_t)level-(int64_t)bought;if(age<INT32_MIN||age>INT32_MAX)return COH_UNSUPPORTED;uint32_t free_count;status=coh_schedule_count(s,0,(int32_t)age,&free_count);if(status!=COH_OK)return status;int32_t maximum=signed_word(r.max_boosts),allowed=(int32_t)free_count;if(maximum<allowed)allowed=maximum;int64_t purchased=(int64_t)wire-allowed;if(purchased<0)purchased=0;if(purchased>INT32_MAX)return COH_UNSUPPORTED;
 CohPowerBoostSlots value={d,s,row,entry->crc,wire,free_count,r.boosts_allowed_count,level,bought,maximum,allowed,(int32_t)purchased,1,0,0};status=cancelled(d);if(status!=COH_OK)return status;*out=value;return COH_OK;
}

#include "coh_stash32.h"
#include <stdint.h>
#include <string.h>
#define MIX(a,b,c) do{a-=b;a-=c;a^=c>>13;b-=c;b-=a;b^=a<<8;c-=a;c-=b;c^=b>>13;a-=b;a-=c;a^=c>>12;b-=c;b-=a;b^=a<<16;c-=a;c-=b;c^=b>>5;a-=b;a-=c;a^=c>>3;b-=c;b-=a;b^=a<<10;c-=a;c-=b;c^=b>>15;}while(0)
static uint32_t little(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
CohStatus coh_stash32_string_hash(CohBytes key,uint32_t seed,uint32_t*out){
 uint32_t a=0x9e3779b9u,b=a,c=seed;size_t n=key.size,i;const uint8_t*p=key.data;
 if(!out||(uintptr_t)out%sizeof(uint32_t)||key.size>259||(!key.data&&key.size))return COH_INVALID;
 if((uintptr_t)out>UINTPTR_MAX-sizeof(*out)||(key.data&&(uintptr_t)key.data>UINTPTR_MAX-key.size))return COH_INVALID;
 if(key.size&&(uintptr_t)out<(uintptr_t)key.data+key.size&&(uintptr_t)key.data<(uintptr_t)out+sizeof(*out))return COH_INVALID;
 while(n>=12){a+=little(p)|0x20202020u;b+=little(p+4)|0x20202020u;c+=little(p+8)|0x20202020u;MIX(a,b,c);p+=12;n-=12;}
 c+=(uint32_t)key.size;
 for(i=0;i<n;i++){uint32_t v=(uint32_t)(p[i]|0x20u);if(i<4)a+=v<<(8*i);else if(i<8)b+=v<<(8*(i-4));else c+=v<<(8*(i-7));}
 MIX(a,b,c);*out=c;return COH_OK;
}
uint32_t coh_stash32_int_hash(uint32_t key,uint32_t seed){uint32_t a=0x9e3779b9u,b=a,c=seed+1u;a+=key;MIX(a,b,c);return c;}
static int span(const void*p,size_t n){return p?(uintptr_t)p<=UINTPTR_MAX-n:!n;}
static int apart(const void*a,size_t an,const void*b,size_t bn){return !an||!bn||(uintptr_t)a+an<=(uintptr_t)b||(uintptr_t)b+bn<=(uintptr_t)a;}
static CohStatus insert(uint32_t*slots,uint32_t max,uint32_t key,int*added){
 uint32_t index=coh_stash32_int_hash(key,COH_STASH32_DEFAULT_SEED)&(max-1),probe=1;
 for(uint32_t n=0;n<COH_STASH32_SLOT_MAX;n++){
  if(!slots[index]){slots[index]=key;*added=1;return COH_OK;}
  if(slots[index]==key){*added=0;return COH_OK;}
  index=(index+probe*probe)&(max-1);probe++;
 }return COH_LIMIT;
}
CohStatus coh_stash32_int_prefix(const uint32_t*keys,size_t count,uint32_t initial,
 CohStash32IntWorkspace*w,CohStash32IntSnapshot*out,size_t budget,size_t retained){
 size_t input_bytes,charged;uint32_t valid=0,resizes=0,duplicates=0,zeros=0,max=initial,active=0;CohStatus status;
 if(count>COH_STASH32_KEY_MAX||initial<8||initial>COH_STASH32_SLOT_MAX||(initial&(initial-1))||!w||!out)return COH_INVALID;
 input_bytes=count*sizeof(*keys);if(!span(keys,input_bytes)||!span(w,sizeof(*w))||!span(out,sizeof(*out)))return COH_INVALID;
 if(input_bytes&&(uintptr_t)keys%sizeof(uint32_t))return COH_INVALID;
 if(!apart(keys,input_bytes,w,sizeof(*w))||!apart(keys,input_bytes,out,sizeof(*out))||!apart(w,sizeof(*w),out,sizeof(*out)))return COH_INVALID;
 charged=sizeof(*w)+sizeof(*out)+COH_STASH32_STACK_RESERVE+input_bytes;
 if(!budget||budget>COH_STASH32_BUDGET_MAX||charged>budget||retained>budget-charged)return COH_LIMIT;
 memset(w,0,sizeof(*w));
 for(size_t n=0;n<count;n++){
  int added=0;uint32_t key=keys[n];if(!key){zeros++;continue;}
  status=insert(w->slots[active],max,key,&added);if(status!=COH_OK)return status;
  if(!added){duplicates++;continue;}valid++;
  if(valid>=(max>>1)+(max>>2)){
   uint32_t next=8,other=1-active,seen=0;
   while(next<(valid<<1)){if(next>=COH_STASH32_SLOT_MAX)return COH_LIMIT;next*=2;}
   memset(w->slots[other],0,sizeof(w->slots[other]));
   for(uint32_t i=0;i<max;i++)if(w->slots[active][i]){int fresh=0;status=insert(w->slots[other],next,w->slots[active][i],&fresh);if(status!=COH_OK||!fresh)return COH_STATE;seen++;}
   if(seen!=valid)return COH_STATE;
   active=other;max=next;resizes++;
  }
 }
 memset(out,0,sizeof(*out));out->initial_slots=initial;out->max_size=max;out->valid_count=valid;out->resize_count=resizes;out->duplicate_count=duplicates;out->zero_count=zeros;memcpy(out->slots,w->slots[active],(size_t)max*sizeof(uint32_t));out->source_hash_bits=32;out->source_prefix_only=1;return COH_OK;
}

#include "coh_initial_partcount_admission.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,queries,allocation_calls;
void *__wrap_malloc(size_t n){(void)n;allocation_calls++;return NULL;}
void *__wrap_calloc(size_t a,size_t b){(void)a;(void)b;allocation_calls++;return NULL;}
void *__wrap_realloc(void*p,size_t n){(void)p;(void)n;allocation_calls++;return NULL;}
void __wrap_free(void*p){(void)p;allocation_calls++;}
static uint32_t catalog_parts=28,catalog_types=9;
static int query_mode;static char fake_owner,wrong_owner;
static CohCostumePacketBinding expected_binding;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
/* Explicit LINK-TIME TEST DOUBLE. No production owner constructor is supplied. */
CohStatus coh_costume_owner_query(const CohCostumeOwner*o,const CohCostumePacketBinding*b,
 uint32_t*parts,uint32_t*types){
 queries++;if(!o)return COH_NOT_FOUND;if(o!=(const CohCostumeOwner*)&fake_owner)return COH_STATE;
 if(query_mode)return query_mode==1?COH_STATE:COH_UNSUPPORTED;
 if(b->generation!=expected_binding.generation||b->loan_owner!=expected_binding.loan_owner||
    b->session_owner!=expected_binding.session_owner||b->source_owner!=expected_binding.source_owner||
    b->generation_owner!=expected_binding.generation_owner)return COH_STATE;
 *parts=catalog_parts;*types=catalog_types;return COH_OK;
}
CohStatus coh_costume_owner_output_disjoint(const CohCostumeOwner*o,const void*out,size_t n){
 uintptr_t a=(uintptr_t)o,b=(uintptr_t)out;
 if(!out||n>UINTPTR_MAX-b)return COH_INVALID;
 return o&&a<b+n&&b<a+1?COH_INVALID:COH_OK;
}
typedef struct{unsigned char bytes[1024];size_t bits;unsigned compressed;} Writer;
static void bits(Writer*w,unsigned n,uint32_t v){if(w->compressed)n=(n+7u)&~7u;for(unsigned i=0;i<n;i++){if((v>>i)&1u)w->bytes[w->bits/8]|=(uint8_t)(1u<<(w->bits%8));w->bits++;}}
static void pack(Writer*w,unsigned n,uint32_t v){if(w->compressed){bits(w,32,v);return;}while(n<32){uint32_t m=(UINT32_C(1)<<n)-1u;if(v<m){bits(w,n,v);return;}bits(w,n,m);v-=m;n*=2;if(n>32)n=32;}bits(w,32,v);}
static size_t fixture(Writer*w,unsigned compressed,unsigned start,uint32_t type,uint32_t flag,uint32_t count){
 memset(w,0,sizeof(*w));w->compressed=compressed;w->bits=start;
 pack(w,6,type);bits(w,32,0);bits(w,1,1);bits(w,3,0);bits(w,1,1);
 for(unsigned i=0;i<72+30;i++)bits(w,32,0);
 size_t at=w->bits;bits(w,1,flag);if(flag==1)pack(w,4,count);return at;
}
static CohStatus call(CohRepReader*r,const CohCostumeOwner*o,CohCostumePacketBinding*b,CohInitialCountAdmission*d){
 CohRepReader saved=*r;unsigned char copy[1024];memcpy(copy,r->bytes.data,r->bytes.size);
 CohStatus s=coh_initial_partcount_admission(r,o,b,d);CHECK(s!=COH_OK);CHECK(!memcmp(r,&saved,sizeof(saved)));CHECK(!memcmp(copy,r->bytes.data,r->bytes.size));return s;
}
int main(void){
 Writer w;CohRepReader r;CohCostumePacketBinding b;CohInitialCountAdmission d;
 for(unsigned mode=0;mode<2;mode++)for(unsigned start=0;start<(mode?1u:8u);start++)
 for(unsigned parts=1;parts<=30;parts++)for(unsigned flag=0;flag<2;flag++)for(unsigned variant=0;variant<5;variant++){
  uint32_t count=variant==0?0:variant==1?1:variant==2?parts:variant==3?parts+1:30;
  size_t begin=fixture(&w,mode,start,8,flag,count);CHECK(coh_rep_reader_bounded(&r,(CohBytes){w.bytes,(w.bits+7)/8},w.bits,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=start;
  b=(CohCostumePacketBinding){.packet=r.bytes,.bit_length=r.bits,.compressed=mode,.loan_owner=&w,.session_owner=&fake_owner,.source_owner=&wrong_owner,.generation_owner=&b,.generation=7};expected_binding=b;
  CohRepReader framing=r;framing.cursor=begin;CohInitialPartcountProbe old={0};
  CohStatus old_status=coh_initial_partcount_probe(&framing,&old);
  if(!flag){CHECK(old_status==COH_UNSUPPORTED&&37u+(unsigned)old.stage==41u&&!old.part_count&&!old.count_read&&old.framing_validated);}
  else if(count<=30){CHECK(old_status==COH_UNSUPPORTED&&37u+(unsigned)old.stage==43u&&old.part_count==count&&old.framing_validated);}
  catalog_parts=parts;catalog_types=9;query_mode=0;
  CohStatus s=call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d);
  if(flag&&count>30){CHECK(s==COH_LIMIT&&d.stage==COH_INITIAL_COUNT_ADMISSION_FRAMING&&!d.catalog_validated);}
  else if(flag&&count>parts){CHECK(s==COH_LIMIT&&d.stage==COH_INITIAL_COUNT_ADMISSION_COUNT&&!d.catalog_validated);}
  else{CHECK(s==COH_UNSUPPORTED&&d.stage==COH_INITIAL_COUNT_ADMISSION_PART_BODY&&d.catalog_validated);CHECK(d.part_count==(flag?count:parts)&&d.count_begin_bit==begin&&d.end_bit==w.bits&&d.failure_bit==w.bits);}
 }
 /* Missing, stale/reloaded and mismatched actual owners do not supply a count. */
 for(unsigned flag=0;flag<2;flag++){
  fixture(&w,0,0,0,flag,1);CHECK(coh_rep_reader_bounded(&r,(CohBytes){w.bytes,(w.bits+7)/8},w.bits,0,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
  b=(CohCostumePacketBinding){.packet=r.bytes,.bit_length=r.bits,.compressed=0};expected_binding=b;catalog_parts=28;catalog_types=9;
  query_mode=0;CHECK(call(&r,NULL,&b,&d)==COH_NOT_FOUND&&!d.part_count&&!d.catalog_validated);
  CHECK(call(&r,(const CohCostumeOwner*)&wrong_owner,&b,&d)==COH_STATE&&!d.part_count);
  query_mode=1;CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d)==COH_STATE&&!d.part_count);
  query_mode=2;CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d)==COH_UNSUPPORTED&&!d.catalog_validated);
  CHECK(d.stage==(flag?COH_INITIAL_COUNT_ADMISSION_EXPLICIT_CATALOG:COH_INITIAL_COUNT_ADMISSION_DEFAULT_CATALOG));
  query_mode=0;
  for(unsigned bad=0;bad<5;bad++){
   CohCostumePacketBinding changed=b;
   if(bad==0)changed.generation++;
   if(bad==1)changed.loan_owner=&fake_owner;
   if(bad==2)changed.session_owner=&wrong_owner;
   if(bad==3)changed.source_owner=&fake_owner;
   if(bad==4)changed.generation_owner=&wrong_owner;
   CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&changed,&d)==COH_STATE&&!d.part_count&&!d.catalog_validated);
  }

 }
 query_mode=0;catalog_parts=28;catalog_types=9;
 for(unsigned mode=0;mode<2;mode++){
  fixture(&w,mode,0,9,0,0);CHECK(coh_rep_reader_bounded(&r,(CohBytes){w.bytes,(w.bits+7)/8},w.bits,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);b=(CohCostumePacketBinding){.packet=r.bytes,.bit_length=r.bits,.compressed=mode};expected_binding=b;
  CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d)==COH_LIMIT&&d.stage==COH_INITIAL_COUNT_ADMISSION_BODYTYPE&&!d.catalog_validated);
  fixture(&w,mode,0,0,0,0);r.bytes.size=(w.bits+7)/8;r.bits=w.bits;b.packet=r.bytes;b.bit_length=r.bits;
  for(size_t cut=0;cut<w.bits;cut++){CohRepReader cutr=r;cutr.bits=cut;b.bit_length=cut;unsigned before=queries;CHECK(call(&cutr,(const CohCostumeOwner*)&fake_owner,&b,&d)!=COH_OK&&!d.catalog_validated);CHECK(queries==before);}b.bit_length=r.bits;
  for(unsigned bad=0;bad<4;bad++){
   CohCostumePacketBinding changed=b;if(bad==0)changed.packet.data++;if(bad==1)changed.packet.size++;if(bad==2)changed.bit_length--;if(bad==3)changed.compressed^=1;
   unsigned before=queries;CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&changed,&d)==COH_STATE&&!d.catalog_validated);CHECK(queries==before);
  }
 }
 /* Zero/oversized catalog is never transformed into a native default. */
 for(unsigned n=0;n<3;n++){catalog_parts=n==0?0:n==1?31:UINT32_MAX;CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d)==COH_LIMIT&&!d.part_count&&!d.catalog_validated);}catalog_parts=28;
 for(unsigned n=0;n<3;n++){catalog_types=n==0?0:n==1?65:UINT32_MAX;CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d)==COH_LIMIT&&!d.catalog_validated);}catalog_types=9;
 /* A malformed rounded Boolean refuses before consulting any owner. */
 fixture(&w,1,0,0,2,0);CHECK(coh_rep_reader_bounded(&r,(CohBytes){w.bytes,(w.bits+7)/8},w.bits,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);b=(CohCostumePacketBinding){.packet=r.bytes,.bit_length=r.bits,.compressed=1};
 unsigned qbefore=queries;CHECK(call(&r,(const CohCostumeOwner*)&fake_owner,&b,&d)==COH_INVALID&&d.stage==COH_INITIAL_COUNT_ADMISSION_FRAMING&&!d.catalog_validated&&queries==qbefore);
 CohInitialCountAdmission before;memset(&d,0xa5,sizeof(d));before=d;
 CHECK(coh_initial_partcount_admission(NULL,NULL,&b,&d)==COH_INVALID&&!memcmp(&before,&d,sizeof(d)));
 CHECK(coh_initial_partcount_admission(&r,NULL,NULL,&d)==COH_INVALID&&!memcmp(&before,&d,sizeof(d)));
 CHECK(coh_initial_partcount_admission(&r,NULL,&b,NULL)==COH_INVALID);
 CHECK(coh_initial_partcount_admission(&r,NULL,&b,(CohInitialCountAdmission*)&r)==COH_INVALID);
 CHECK(coh_initial_partcount_admission(&r,NULL,&b,(CohInitialCountAdmission*)&b)==COH_INVALID);
 CHECK(coh_initial_partcount_admission(&r,NULL,&b,(CohInitialCountAdmission*)w.bytes)==COH_INVALID);
 CHECK(coh_initial_partcount_admission(&r,(const CohCostumeOwner*)&fake_owner,&b,(CohInitialCountAdmission*)&fake_owner)==COH_INVALID);
 CHECK(coh_initial_partcount_admission(&r,NULL,&b,(CohInitialCountAdmission*)(uintptr_t)(UINTPTR_MAX-1))==COH_INVALID);
 CHECK(coh_initial_partcount_admission(&r,NULL,(const CohCostumePacketBinding*)(uintptr_t)(UINTPTR_MAX-1),&d)==COH_INVALID);
 CHECK(coh_initial_partcount_admission((const CohRepReader*)(uintptr_t)(UINTPTR_MAX-1),NULL,&b,&d)==COH_INVALID);
 CohRepReader overflow=r;overflow.bytes=(CohBytes){(const uint8_t*)(uintptr_t)(UINTPTR_MAX-2),4};CHECK(coh_initial_partcount_admission(&overflow,NULL,&b,&d)==COH_INVALID);
 r.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX+1u;CHECK(coh_initial_partcount_admission(&r,NULL,&b,&d)==COH_INVALID);
 CHECK(!allocation_calls);
 printf("{\"checks\":%u,\"synthetic_owner_queries\":%u,\"parts_read\":0,\"direct_allocation_calls\":%u}\n",checks,queries,allocation_calls);return 0;
}

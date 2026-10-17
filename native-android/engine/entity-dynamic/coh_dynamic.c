#include "coh_dynamic.h"
#include <limits.h>
#include <string.h>
#include <zlib.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static voidpf arena_allocate(voidpf opaque,uInt items,uInt size){CohDynamicWorkspace*w=(CohDynamicWorkspace*)opaque;size_t alignment=sizeof(long double)>sizeof(void*)?sizeof(long double):sizeof(void*);size_t padding=(alignment-w->arena_used%alignment)%alignment;if(size&&items>SIZE_MAX/size)return NULL;size_t bytes=(size_t)items*size;if(padding>COH_DYNAMIC_ZLIB_ARENA_BYTES-w->arena_used||bytes>COH_DYNAMIC_ZLIB_ARENA_BYTES-w->arena_used-padding)return NULL;w->arena_used+=padding;void*p=w->arena.bytes+w->arena_used;memset(p,0,bytes);w->arena_used+=bytes;return p;}
static void arena_release(voidpf opaque,voidpf address){(void)opaque;(void)address;}
static CohStatus scalar(CohRepReader*r,unsigned n,uint32_t*out){CohStatus s=coh_rep_read(r,n,out);if(s==COH_OK&&n<32&&*out>=(UINT32_C(1)<<n))s=COH_INVALID;return s;}
#define CALL(expr) do{status=(expr);if(status!=COH_OK)return status;}while(0)
CohStatus coh_dynamic_diagnostic_read(CohRepReader*reader,uint32_t expected,CohDynamicDiagnostic*out,CohDynamicWorkspace*workspace,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||expected>COH_DYNAMIC_COUNT_MAX||!budget||budget>COH_DYNAMIC_RAM_MAX)return COH_INVALID;
 r=*reader;CALL(coh_rep_read(&r,0,&ignored));
 const void*objects[]={reader,out,workspace,r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_DYNAMIC_STACK_RESERVE;if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return COH_LIMIT;
 CohDynamicDiagnostic*v=&workspace->candidate;memset(v,0,sizeof(*v));v->expected_count=expected;v->begin_bit=r.cursor;CALL(coh_rep_pack(&r,1,&v->modified_count));
 if(v->modified_count==UINT32_MAX){CALL(coh_rep_pack(&r,1,&v->compressed_bytes));CALL(coh_rep_pack(&r,1,&v->raw_bytes));if(v->compressed_bytes>COH_DYNAMIC_ZIP_MAX||v->raw_bytes>COH_DYNAMIC_COUNT_MAX)return COH_LIMIT;if(v->raw_bytes!=expected)return COH_INVALID;size_t skip=(8-r.cursor%8)%8;if(skip>r.bits-r.cursor)return COH_INVALID;r.cursor+=skip;if(v->compressed_bytes>(r.bits-r.cursor)/8)return COH_INVALID;
  z_stream z;memset(&z,0,sizeof(z));workspace->arena_used=0;z.zalloc=arena_allocate;z.zfree=arena_release;z.opaque=workspace;int code=inflateInit(&z);if(code!=Z_OK)return code==Z_MEM_ERROR?COH_LIMIT:COH_INVALID;z.next_in=(Bytef*)(r.bytes.data+r.cursor/8);z.avail_in=(uInt)v->compressed_bytes;z.next_out=v->full_status;z.avail_out=(uInt)v->raw_bytes+1;code=inflate(&z,Z_FINISH);int exact=code==Z_STREAM_END&&z.total_in==v->compressed_bytes&&z.total_out==v->raw_bytes;int ended=inflateEnd(&z);if(!exact||ended!=Z_OK)return code==Z_MEM_ERROR?COH_LIMIT:COH_INVALID;r.cursor+=(size_t)v->compressed_bytes*8;
 }else{if(v->modified_count>COH_DYNAMIC_COUNT_MAX)return COH_LIMIT;for(uint32_t i=0;i<v->modified_count;i++){CohDynamicDelta*d=&v->deltas[i];CALL(coh_rep_pack(&r,16,&d->index));if(d->index>=expected)return COH_INVALID;CALL(scalar(&r,7,&d->hp));CALL(scalar(&r,1,&d->repair));}}
 v->end_bit=r.cursor;*out=*v;*reader=r;return COH_OK;
}

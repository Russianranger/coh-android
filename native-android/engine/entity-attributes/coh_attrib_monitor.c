#include "coh_attrib_monitor.h"
#include <math.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus scalar(CohRepReader*r,unsigned n,uint32_t*out){CohStatus s=coh_rep_read(r,n,out);if(s==COH_OK&&n<32&&*out>=(UINT32_C(1)<<n))s=COH_INVALID;return s;}
#define CALL(expr) do{status=(expr);if(status!=COH_OK)return status;}while(0)
CohStatus coh_attrib_monitor_read(CohRepReader*reader,CohAttribMonitor*out,CohAttribMonitorWorkspace*workspace,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_ATTRIB_MONITOR_RAM_MAX)return COH_INVALID;
 r=*reader;CALL(coh_rep_read(&r,0,&ignored));
 const void*objects[]={reader,out,workspace,r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_ATTRIB_MONITOR_STACK_RESERVE;if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return COH_LIMIT;
 CohAttribMonitor*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=r.cursor;CALL(scalar(&r,1,&v->new_target));CALL(scalar(&r,1,&v->full));if(v->full)return COH_UNSUPPORTED;
 for(unsigned i=0;i<COH_ATTRIB_MONITOR_SLOTS;i++){CohAttribMonitorSlot*s=&v->slots[i];CALL(scalar(&r,1,&s->present));if(s->present){CALL(scalar(&r,32,&s->key));CALL(scalar(&r,32,&s->value_word));float f;memcpy(&f,&s->value_word,4);if(!isfinite(f))return COH_INVALID;CALL(scalar(&r,2,&s->buff));}}
 v->end_bit=r.cursor;*out=*v;*reader=r;return COH_OK;
}

#include "coh_view.h"
#include <math.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus scalar(CohRepReader*r,unsigned n,uint32_t*out){CohStatus s=coh_rep_read(r,n,out);if(s==COH_OK&&n<32&&*out>=(UINT32_C(1)<<n))s=COH_INVALID;return s;}
static CohStatus number(CohRepReader*r,uint32_t*out){CohStatus s=scalar(r,32,out);float f;memcpy(&f,out,4);return s==COH_OK&&!isfinite(f)?COH_INVALID:s;}
#define CALL(expr) do{status=(expr);if(status!=COH_OK)return status;}while(0)
CohStatus coh_world_view_read(CohRepReader*reader,CohWorldView*out,CohWorldViewWorkspace*workspace,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_VIEW_RAM_MAX)return COH_INVALID;
 r=*reader;CALL(coh_rep_read(&r,0,&ignored));
 const void*objects[]={reader,out,workspace,r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_VIEW_STACK_RESERVE;if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return COH_LIMIT;
 CohWorldView*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=r.cursor;v->sky2=1;CALL(scalar(&r,1,&v->sky_interesting));if(v->sky_interesting){CALL(number(&r,&v->sky_weight_word));CALL(coh_rep_pack(&r,2,&v->sky1));CALL(coh_rep_pack(&r,2,&v->sky2));}v->sky_end_bit=r.cursor;
 CALL(scalar(&r,1,&v->slave_present));if(v->slave_present)for(unsigned i=0;i<3;i++)CALL(number(&r,&v->slave_pyr_words[i]));v->end_bit=r.cursor;*out=*v;*reader=r;return COH_OK;
}

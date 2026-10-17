#include "coh_power_ranges.h"
#include <string.h>
static int overlaps(const void*a,size_t an,const void*b,size_t bn) {
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
static CohStatus scalar(CohRepReader*r,unsigned n,uint32_t*out) {
    CohStatus s=coh_rep_read(r,n,out);
    if(s==COH_OK&&n<32&&*out>=(UINT32_C(1)<<n))return COH_INVALID;
    return s;
}
static CohStatus read_ranges(CohRepReader*r,CohPowerRanges*out,
    CohPowerRangesWorkspace*workspace,size_t retained,size_t limit,int outer) {
    CohRepReader q;CohStatus s;uint32_t flag;size_t needed;
    if(!r||!out||!workspace||!limit||limit>COH_POWER_RANGES_AGGREGATE_MAX)return COH_INVALID;
    q=*r;s=coh_rep_read(&q,0,&flag);if(s!=COH_OK)return s;
    const void*spans[]={r,out,workspace,q.bytes.data};
    const size_t sizes[]={sizeof(*r),sizeof(*out),sizeof(*workspace),q.bytes.size};
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)
        if(overlaps(spans[i],sizes[i],spans[j],sizes[j]))return COH_INVALID;
    needed=sizeof(*out)+sizeof(*workspace)+COH_POWER_RANGES_STACK_RESERVE;
    if(needed>limit||q.bytes.size>limit-needed)return COH_LIMIT;
    needed+=q.bytes.size;if(retained>limit-needed)return COH_LIMIT;
    CohPowerRanges*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=q.cursor;
    if(outer) {
        s=scalar(&q,1,&flag);if(s!=COH_OK)return s;
        if(flag)return COH_UNSUPPORTED;
    }
    for(;;) {
        s=scalar(&q,1,&flag);if(s!=COH_OK)return s;
        if(!flag)break;
        if(v->count==COH_POWER_RANGES_MAX)return COH_LIMIT;
        static const unsigned widths[]={2,10,24,32};uint32_t bin;
        s=scalar(&q,2,&bin);if(s!=COH_OK)return s;
        CohPowerRange*p=&v->ranges[v->count];
        /* Identical basepower CRC wire encoding used by character-data's
         * power_ref. Unlike dictionary-bound character admission, retain zero
         * here: original basepower_Send(NULL) emits it and consumer reads range. */
        s=scalar(&q,widths[bin],&p->power_crc);if(s!=COH_OK)return s;
        s=coh_rep_read(&q,32,&p->range_word);if(s!=COH_OK)return s;
        v->count++;
    }
    v->end_bit=q.cursor;*out=*v;*r=q;return COH_OK;
}
CohStatus coh_power_ranges(CohRepReader*r,CohPowerRanges*out,
    CohPowerRangesWorkspace*w,size_t retained,size_t limit) {
    return read_ranges(r,out,w,retained,limit,0);
}
CohStatus coh_power_info_no_changes(CohRepReader*r,CohPowerRanges*out,
    CohPowerRangesWorkspace*w,size_t retained,size_t limit) {
    return read_ranges(r,out,w,retained,limit,1);
}

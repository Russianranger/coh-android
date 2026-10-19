#include "coh_initial_scales_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialScalesProbe*out,CohInitialScalesProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
CohStatus coh_initial_scales_probe(const CohRepReader*input,CohInitialScalesProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialScalesProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.compressed=r.compressed;
 d.stage=COH_INITIAL_SCALES_VALUE;
 for(unsigned i=0;i<COH_INITIAL_SCALES_COUNT;i++){
  CohStatus status=coh_rep_read(&r,32,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if((value&UINT32_C(0x7f800000))==UINT32_C(0x7f800000)){
   d.stage=COH_INITIAL_SCALES_NONFINITE;d.nonfinite_seen=1;
   return finish(out,&d,COH_INVALID,r.cursor);
  }
  d.scales_read++;
 }
 d.stage=COH_INITIAL_SCALES_PART_COUNT;d.end_bit=r.cursor;d.scales_validated=1;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
static int valid(const CohInitialScalesProbe*d){
 if((d->status!=COH_INVALID&&d->status!=COH_UNSUPPORTED)||d->compressed>1||
    d->scales_read>COH_INITIAL_SCALES_COUNT||d->nonfinite_seen>1||d->begin_bit>d->failure_bit||
    d->failure_bit>COH_REP_BOUNDED_MESSAGE_MAX*8u||
    d->failure_bit-d->begin_bit!=(size_t)(d->scales_read+d->nonfinite_seen)*32u)return 0;
 if(d->stage==COH_INITIAL_SCALES_VALUE||d->stage==COH_INITIAL_SCALES_NONFINITE)
  return d->status==COH_INVALID&&d->scales_read<COH_INITIAL_SCALES_COUNT&&
   d->nonfinite_seen==(d->stage==COH_INITIAL_SCALES_NONFINITE)&&!d->scales_validated&&!d->end_bit;
 return d->stage==COH_INITIAL_SCALES_PART_COUNT&&d->scales_read==COH_INITIAL_SCALES_COUNT&&
  !d->nonfinite_seen&&d->scales_validated==1&&d->end_bit==d->failure_bit;
}
int coh_initial_scales_probe_json(const CohInitialScalesProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 if(!valid(d))return -1;
 return snprintf(out,bytes,"[%u,%u,%llu,%llu,%u,%u,%u]",(unsigned)d->status,(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)(d->failure_bit-d->begin_bit),
  d->scales_read,d->nonfinite_seen,d->scales_validated);
}
int coh_initial_scales_progress_json(const CohInitialRewardListProbe*l,
 const CohInitialCostumeSlotsProbe*s,const CohInitialCostumeBodyProbe*b,
 const CohInitialAppearanceProbe*a,const CohInitialSgcolorsProbe*g,
 const CohInitialScalesProbe*d,char*out,size_t bytes){
 if(!l||!s||!b||!a||!g||!d||!out||!bytes||overlap(l,sizeof(*l),out,bytes)||overlap(s,sizeof(*s),out,bytes)||
    overlap(b,sizeof(*b),out,bytes)||overlap(a,sizeof(*a),out,bytes)||overlap(g,sizeof(*g),out,bytes)||
    overlap(d,sizeof(*d),out,bytes)||!valid(d)||g->stage!=COH_INITIAL_SGCOLORS_SCALES||
    g->array_validated!=1||g->words_read!=COH_INITIAL_SGCOLORS_WORDS||g->compressed!=d->compressed||
    g->end_bit!=d->begin_bit||g->failure_bit!=g->end_bit)return -1;
 char parent[COH_INITIAL_SGCOLORS_REPORT_MAX];
 int n=coh_initial_sgcolors_progress_json(l,s,b,a,g,parent,sizeof(parent));
 if(n<=0||(size_t)n>=sizeof(parent))return -1;
 size_t width=a->bodytype_end_bit-a->begin_bit;
 uint32_t selector=d->compressed?0u:width==6?0u:width==18?1u:width==42?2u:3u;
 uint32_t pair=s->body_count*(s->body_count-1u)/2u+s->current;
 uint32_t m=pair|(s->additional<<6)|(s->deferred<<14)|(b->present_mask<<15)|
  ((b->cached_mask>>1)<<17)|(d->compressed<<18)|(selector<<19)|(d->scales_read<<21)|
  (d->nonfinite_seen<<26);
 return snprintf(out,bytes,"[%u,%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,33u+(unsigned)d->stage,
  l->entries[0],l->entries[1],(unsigned long long)l->end_bit,
  (unsigned long long)(d->failure_bit-l->end_bit),m);
}

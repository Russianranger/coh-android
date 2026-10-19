#include "coh_initial_partcount_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialPartcountProbe*out,CohInitialPartcountProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
CohStatus coh_initial_partcount_probe(const CohRepReader*input,CohInitialPartcountProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialPartcountProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.compressed=r.compressed;
 d.stage=COH_INITIAL_PARTCOUNT_FLAG;
 CohStatus status=coh_rep_read(&r,1,&value);
 if(status!=COH_OK||value>1)return finish(out,&d,COH_INVALID,r.cursor);
 d.flag_read=1;d.explicit_count=value;
 if(!value){
  d.stage=COH_INITIAL_PARTCOUNT_DEFAULT_CATALOG;d.end_bit=r.cursor;d.framing_validated=1;
  return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 }
 d.stage=COH_INITIAL_PARTCOUNT_COUNT;size_t count_begin=r.cursor;
 status=coh_rep_pack(&r,4,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.count_read=1;d.count_width=(uint32_t)(r.cursor-count_begin);
 if(value>COH_COSTUME_PART_MAX){
  d.stage=COH_INITIAL_PARTCOUNT_COUNT_LIMIT;d.part_count=COH_INITIAL_PARTCOUNT_EXCESS;
  return finish(out,&d,COH_LIMIT,r.cursor);
 }
 d.part_count=value;d.stage=COH_INITIAL_PARTCOUNT_CATALOG;
 d.end_bit=r.cursor;d.framing_validated=1;
 return finish(out,&d,COH_UNSUPPORTED,r.cursor);
}
static int valid(const CohInitialPartcountProbe*d){
 if(d->compressed>1||(d->compressed&&(d->begin_bit&7))||d->explicit_count>1||d->flag_read>1||d->count_read>1||
    d->framing_validated>1||d->part_count>COH_INITIAL_PARTCOUNT_EXCESS||
    d->begin_bit>d->failure_bit||d->failure_bit>COH_REP_BOUNDED_MESSAGE_MAX*8u)return 0;
 size_t delta=d->failure_bit-d->begin_bit;unsigned flag=d->compressed?8u:1u;
 if(d->stage==COH_INITIAL_PARTCOUNT_FLAG)
  return d->status==COH_INVALID&&!d->explicit_count&&!d->flag_read&&!d->count_read&&
   !d->part_count&&!d->count_width&&!d->framing_validated&&!d->end_bit&&
   (!delta||(d->compressed&&delta==flag));
 if(!d->flag_read)return 0;
 if(d->stage==COH_INITIAL_PARTCOUNT_COUNT)
  return d->status==COH_INVALID&&d->explicit_count&&!d->count_read&&!d->part_count&&
   !d->count_width&&!d->framing_validated&&!d->end_bit&&delta==flag;
 if(d->stage==COH_INITIAL_PARTCOUNT_DEFAULT_CATALOG)
  return d->status==COH_UNSUPPORTED&&!d->explicit_count&&!d->count_read&&!d->part_count&&
   !d->count_width&&d->framing_validated&&d->end_bit==d->failure_bit&&delta==flag;
 if(!d->explicit_count||!d->count_read||delta!=flag+d->count_width)return 0;
 if(d->stage==COH_INITIAL_PARTCOUNT_COUNT_LIMIT)
  return d->status==COH_LIMIT&&d->part_count==COH_INITIAL_PARTCOUNT_EXCESS&&
   !d->framing_validated&&!d->end_bit&&
   (d->compressed?d->count_width==32:
    d->count_width==12||d->count_width==28||d->count_width==60);
 return d->stage==COH_INITIAL_PARTCOUNT_CATALOG&&d->status==COH_UNSUPPORTED&&
  d->part_count<=COH_COSTUME_PART_MAX&&d->framing_validated&&d->end_bit==d->failure_bit&&
  d->count_width==(d->compressed?32u:d->part_count<15?4u:12u);
}
int coh_initial_partcount_probe_json(const CohInitialPartcountProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 if(!valid(d))return -1;
 return snprintf(out,bytes,"[%u,%u,%llu,%llu,%u,%u,%u,%u]",(unsigned)d->status,(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)(d->failure_bit-d->begin_bit),
  d->explicit_count,d->part_count,d->count_width,d->framing_validated);
}
int coh_initial_partcount_progress_json(const CohInitialRewardListProbe*l,
 const CohInitialCostumeSlotsProbe*s,const CohInitialCostumeBodyProbe*b,
 const CohInitialAppearanceProbe*a,const CohInitialSgcolorsProbe*g,
 const CohInitialScalesProbe*f,const CohInitialPartcountProbe*d,char*out,size_t bytes){
 if(!l||!s||!b||!a||!g||!f||!d||!out||!bytes||overlap(l,sizeof(*l),out,bytes)||
    overlap(s,sizeof(*s),out,bytes)||overlap(b,sizeof(*b),out,bytes)||overlap(a,sizeof(*a),out,bytes)||
    overlap(g,sizeof(*g),out,bytes)||overlap(f,sizeof(*f),out,bytes)||overlap(d,sizeof(*d),out,bytes)||
    !valid(d)||f->stage!=COH_INITIAL_SCALES_PART_COUNT||f->scales_validated!=1||
    f->scales_read!=COH_INITIAL_SCALES_COUNT||f->nonfinite_seen||f->compressed!=d->compressed||
    f->end_bit!=d->begin_bit||f->failure_bit!=f->end_bit)return -1;
 char parent[COH_INITIAL_SCALES_REPORT_MAX];
 int n=coh_initial_scales_progress_json(l,s,b,a,g,f,parent,sizeof(parent));
 if(n<=0||(size_t)n>=sizeof(parent))return -1;
 size_t width=a->bodytype_end_bit-a->begin_bit;
 uint32_t scalar=d->compressed?0u:width==6?0u:width==18?1u:width==42?2u:3u;
 uint32_t selector=d->count_width==4?1u:d->count_width==12?2u:d->count_width==28?3u:
  d->count_width==60?4u:d->count_width==32?5u:
  d->stage==COH_INITIAL_PARTCOUNT_FLAG&&d->failure_bit>d->begin_bit?6u:0u;
 uint32_t pair=s->body_count*(s->body_count-1u)/2u+s->current;
 uint32_t m=pair|(s->additional<<6)|(s->deferred<<14)|(b->present_mask<<15)|
  ((b->cached_mask>>1)<<17)|(d->compressed<<18)|(scalar<<19)|(d->part_count<<21)|(selector<<26);
 return snprintf(out,bytes,"[%u,%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,37u+(unsigned)d->stage,
  l->entries[0],l->entries[1],(unsigned long long)l->end_bit,
  (unsigned long long)(d->failure_bit-l->end_bit),m);
}

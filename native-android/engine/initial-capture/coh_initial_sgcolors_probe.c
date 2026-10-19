#include "coh_initial_sgcolors_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialSgcolorsProbe*out,CohInitialSgcolorsProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
CohStatus coh_initial_sgcolors_probe(const CohRepReader*input,CohInitialSgcolorsProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialSgcolorsProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.compressed=r.compressed;
 d.stage=COH_INITIAL_SGCOLORS_WORD;
 for(unsigned i=0;i<COH_INITIAL_SGCOLORS_WORDS;i++){
  CohStatus status=coh_rep_read(&r,32,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  d.words_read++;
 }
 d.stage=COH_INITIAL_SGCOLORS_SCALES;d.end_bit=r.cursor;d.array_validated=1;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
static int valid(const CohInitialSgcolorsProbe*d){
 if((d->status!=COH_INVALID&&d->status!=COH_UNSUPPORTED)||d->compressed>1||
    d->words_read>COH_INITIAL_SGCOLORS_WORDS||d->begin_bit>d->failure_bit||
    d->failure_bit>COH_REP_BOUNDED_MESSAGE_MAX*8u||
    d->failure_bit-d->begin_bit!=(size_t)d->words_read*32u)return 0;
 if(d->stage==COH_INITIAL_SGCOLORS_WORD)
  return d->status==COH_INVALID&&d->words_read<COH_INITIAL_SGCOLORS_WORDS&&
   !d->array_validated&&!d->end_bit;
 return d->stage==COH_INITIAL_SGCOLORS_SCALES&&d->words_read==COH_INITIAL_SGCOLORS_WORDS&&
  d->array_validated==1&&d->end_bit==d->failure_bit;
}
int coh_initial_sgcolors_probe_json(const CohInitialSgcolorsProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 if(!valid(d))return -1;
 return snprintf(out,bytes,"[%u,%u,%llu,%llu,%u,%u]",(unsigned)d->status,(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)(d->failure_bit-d->begin_bit),
  d->words_read,d->array_validated);
}
int coh_initial_sgcolors_progress_json(const CohInitialRewardListProbe*l,
 const CohInitialCostumeSlotsProbe*s,const CohInitialCostumeBodyProbe*b,
 const CohInitialAppearanceProbe*a,const CohInitialSgcolorsProbe*d,char*out,size_t bytes){
 if(!l||!s||!b||!a||!d||!out||!bytes||overlap(l,sizeof(*l),out,bytes)||overlap(s,sizeof(*s),out,bytes)||
    overlap(b,sizeof(*b),out,bytes)||overlap(a,sizeof(*a),out,bytes)||overlap(d,sizeof(*d),out,bytes)||
    !valid(d)||a->stage!=COH_INITIAL_APPEARANCE_COLORS||a->scalars_validated!=1||a->fields_read!=5||
    a->compressed!=d->compressed||a->end_bit!=d->begin_bit||a->failure_bit!=a->end_bit||
    a->bodytype_end_bit<a->begin_bit)return -1;
 /* Reuse the accepted parent projection's context/range validation, without
  * rerunning any packet parser, fixture entrypoint or dictionary operation. */
 char parent[COH_INITIAL_APPEARANCE_REPORT_MAX];
 int n=coh_initial_appearance_progress_json(l,s,b,a,parent,sizeof(parent));
 if(n<=0||(size_t)n>=sizeof(parent))return -1;
 size_t width=a->bodytype_end_bit-a->begin_bit;uint32_t selector=0;
 if(d->compressed){if(width!=32||a->end_bit-a->begin_bit!=88)return -1;}
 else{
  static const unsigned widths[]={6,18,42,74};
  for(selector=0;selector<4&&width!=widths[selector];selector++){}
  if(selector==4||a->end_bit-a->begin_bit!=width+37u)return -1;
 }
 uint32_t pair=s->body_count*(s->body_count-1u)/2u+s->current;
 uint32_t m=pair|(s->additional<<6)|(s->deferred<<14)|(b->present_mask<<15)|
  ((b->cached_mask>>1)<<17)|(d->compressed<<18)|(selector<<19)|(d->words_read<<21);
 return snprintf(out,bytes,"[%u,%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,31u+(unsigned)d->stage,
  l->entries[0],l->entries[1],(unsigned long long)l->end_bit,
  (unsigned long long)(d->failure_bit-l->end_bit),m);
}

#include "coh_initial_appearance_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialAppearanceProbe*out,CohInitialAppearanceProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus scalar(CohRepReader*r,unsigned width,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,width,&value);
 if(status!=COH_OK)return status;
 if(width<32&&value>=(UINT32_C(1)<<width))return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_appearance_probe(const CohRepReader*input,CohInitialAppearanceProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialAppearanceProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.compressed=r.compressed;
 d.stage=COH_INITIAL_APPEARANCE_BODYTYPE;CohStatus status=coh_rep_pack(&r,6,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.bodytype_end_bit=r.cursor;d.fields_read=1;
 const unsigned widths[]={32,1,3,1};
 for(unsigned i=0;i<4;i++){
  d.stage=(CohInitialAppearanceStage)(COH_INITIAL_APPEARANCE_SKIN+i);
  status=scalar(&r,widths[i],&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  d.fields_read++;
 }
 if(!value)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.stage=COH_INITIAL_APPEARANCE_COLORS;d.scalars_validated=1;d.end_bit=r.cursor;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
static int valid(const CohInitialAppearanceProbe*d){
 return (d->status==COH_INVALID||d->status==COH_UNSUPPORTED)&&
  d->stage>=COH_INITIAL_APPEARANCE_BODYTYPE&&d->stage<=COH_INITIAL_APPEARANCE_COLORS&&
  d->compressed<=1&&d->begin_bit<=d->failure_bit&&d->failure_bit<=COH_REP_BOUNDED_MESSAGE_MAX*8u&&
  d->failure_bit-d->begin_bit<=(d->compressed?88u:111u)&&d->fields_read<=5&&d->scalars_validated<=1&&
  (!d->bodytype_end_bit||(d->bodytype_end_bit>=d->begin_bit&&d->bodytype_end_bit<=d->failure_bit));
}
int coh_initial_appearance_probe_json(const CohInitialAppearanceProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 if(!valid(d))return -1;
 return snprintf(out,bytes,"[%u,%u,%llu,%llu,%llu,%u,%u]",(unsigned)d->status,(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)d->bodytype_end_bit,
  (unsigned long long)(d->failure_bit-d->begin_bit),d->fields_read,d->scalars_validated);
}
int coh_initial_appearance_progress_json(const CohInitialRewardListProbe*l,
 const CohInitialCostumeSlotsProbe*s,const CohInitialCostumeBodyProbe*b,
 const CohInitialAppearanceProbe*d,char*out,size_t bytes){
 if(!l||!s||!b||!d||!out||!bytes||overlap(l,sizeof(*l),out,bytes)||overlap(s,sizeof(*s),out,bytes)||
    overlap(b,sizeof(*b),out,bytes)||overlap(d,sizeof(*d),out,bytes)||!valid(d)||
    l->list_validated!=1||l->stage!=COH_INITIAL_REWARD_LIST_SLOTS||
    (l->status!=COH_INVALID&&l->status!=COH_UNSUPPORTED)||
    l->entries[0]>COH_COSTUME_REWARDS_MAX||l->entries[1]>COH_COSTUME_REWARDS_MAX||
    l->entries[0]!=l->counts[0]||l->entries[1]!=l->counts[1]||
    s->stage!=COH_INITIAL_COSTUME_SLOTS_BODY||s->framing_validated!=1||s->multiple!=1||
    (s->status!=COH_INVALID&&s->status!=COH_UNSUPPORTED)||
    s->current>=COH_COSTUME_STORED_MAX||s->additional>255||s->deferred>1||
    !s->body_count||s->body_count>COH_COSTUME_STORED_MAX||s->current>=s->body_count||
    s->begin_bit!=l->end_bit||s->end_bit!=b->begin_bit||s->failure_bit!=s->end_bit||
    s->end_bit<s->begin_bit||s->end_bit-s->begin_bit!=(d->compressed?40u:22u)||
    b->stage!=COH_INITIAL_COSTUME_BODY_BODYTYPE||b->prefix_validated!=1||b->field!=2||
    (b->status!=COH_INVALID&&b->status!=COH_UNSUPPORTED)||b->complete_mask!=3||b->seen_mask!=3||
    b->present_mask>3||(b->cached_mask!=0&&b->cached_mask!=2)||
    (b->cached_mask==2&&b->present_mask!=3)||b->compressed!=d->compressed||
    b->begin_bit>b->end_bit||b->end_bit-b->begin_bit>(d->compressed?4224u:4168u)||
    b->end_bit!=d->begin_bit||b->failure_bit!=b->end_bit)return -1;
 uint32_t m=s->current|(s->additional<<4)|(s->deferred<<12)|(s->body_count<<13)|
  (b->present_mask<<17)|((b->cached_mask>>1)<<19)|(d->compressed<<20)|
  ((uint32_t)(d->failure_bit-d->begin_bit)<<21);
 return snprintf(out,bytes,"[%u,%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,25u+(unsigned)d->stage,
  l->entries[0],l->entries[1],(unsigned long long)l->end_bit,
  (unsigned long long)(d->failure_bit-l->end_bit),m);
}

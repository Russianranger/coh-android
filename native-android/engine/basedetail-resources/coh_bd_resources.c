#include "coh_bd_resources.h"
#include <string.h>
typedef struct { const void *p; size_t n; } Span;
typedef struct { CohBytes b; size_t at,end,work,values; CohStatus status;
 const CohBdResourceControl *control; } Read;
static const unsigned char schema[]={
#include "../character-dictionary/salvage_details_schema.inc"
};
#define ALIGNED(p,t) ((uintptr_t)(p)%offsetof(struct{char c;t v;},v)==0)
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static int nonzero(const uint8_t*p){unsigned n=0;for(unsigned i=0;i<32;i++)n|=p[i];return n!=0;}
static void need(Read*r,int ok,CohStatus s){if(r->status==COH_OK&&!ok)r->status=s;}
static int charge(Read*r,size_t n){if(r->status!=COH_OK)return 0;if(n>COH_BD_RESOURCE_WORK_MAX-r->work){r->status=COH_LIMIT;return 0;}r->work+=n;return 1;}
static void poll(Read*r){if(charge(r,1)&&r->control->cancel.poll&&r->control->cancel.poll(r->control->cancel.context))r->status=COH_CANCELLED;}
static const uint8_t*take(Read*r,size_t n){if(!charge(r,n))return NULL;if(r->at>r->end||n>r->end-r->at){r->status=COH_INVALID;return NULL;}const uint8_t*p=r->b.data+r->at;r->at+=n;return p;}
static uint32_t word(Read*r){const uint8_t*p=take(r,4);return p?(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24:0;}
static size_t segment(Read*r){uint32_t n=word(r);need(r,r->at<=r->end&&n<=r->end-r->at,COH_INVALID);return r->status==COH_OK?r->at+n:r->at;}
static CohBytes string(Read*r){CohBytes b={0};const uint8_t*p=take(r,2);if(!p)return b;size_t n=(size_t)p[0]|(size_t)p[1]<<8;need(r,n<12000,COH_LIMIT);p=take(r,n);if(!p)return b;for(size_t i=0;i<n&&r->status==COH_OK;i++){if(!charge(r,1))break;need(r,p[i]!=0,COH_INVALID);}b=(CohBytes){p,n};(void)take(r,(4-(n+2)%4)%4);return b;}
static int literal(Read*r,CohBytes b,const char*s){size_t n=strlen(s);return charge(r,b.size)&&b.size==n&&!memcmp(b.data,s,n);}
static CohBdResourceText copy(Read*r,CohBdResources*d,CohBytes b,unsigned key){CohBdResourceText t={0,0};need(r,b.size<(key?128u:1024u)&&(!key||b.size>0),COH_UNSUPPORTED);for(size_t i=0;i<b.size&&r->status==COH_OK;i++){if(!charge(r,1))break;need(r,b.data[i]>0&&b.data[i]<128,COH_UNSUPPORTED);}if(!b.size)return t;need(r,b.size+1<=COH_BD_RESOURCE_TEXT_MAX-d->text_bytes,COH_LIMIT);if(r->status!=COH_OK||!charge(r,b.size+1))return t;t=(CohBdResourceText){d->text_bytes,(uint32_t)b.size};memcpy(d->text+t.offset,b.data,b.size);d->text_bytes+=(uint32_t)b.size+1;return t;}
static void parse(Read*r,CohBdResources*d){r->at=0;r->end=r->b.size;const uint8_t*p=take(r,8);need(r,p&&!memcmp(p,"CrypticS",8),COH_INVALID);d->schema_crc=word(r);need(r,d->schema_crc==UINT32_C(0x326ad4e9),COH_STATE);CohBytes sig=string(r),files=string(r);need(r,literal(r,sig,"Parse6")&&literal(r,files,"Files1"),COH_UNSUPPORTED);size_t end=segment(r),outer=r->end;r->end=end;d->dependencies=word(r);need(r,d->dependencies<=4096,COH_LIMIT);for(unsigned i=0;i<d->dependencies&&r->status==COH_OK;i++){poll(r);(void)string(r);(void)word(r);}need(r,r->at==end,COH_INVALID);r->end=outer;end=segment(r);need(r,end==r->end,COH_INVALID);d->count=word(r);need(r,d->count<=COH_BD_RESOURCE_ROWS_MAX,COH_LIMIT);
 for(unsigned i=0;i<d->count&&r->status==COH_OK;i++){size_t rowend=segment(r);outer=r->end;r->end=rowend;poll(r);CohBdResourceRow*row=&d->rows[i];for(unsigned j=0;j<sizeof(schema)&&r->status==COH_OK;j++){poll(r);if(schema[j]=='W'){uint32_t u=word(r);if(j==12)memcpy(&row->surface,&u,4);else if(j==15)row->mounted=(uint8_t)u;else if(j==19)row->animated=(uint8_t)u;}else if(schema[j]=='S'){CohBytes b=string(r);if(!j)row->name=copy(r,d,b,1);else if(j>=6&&j<12)row->groups[j-6]=copy(r,d,b,0);}else if(schema[j]=='A'){unsigned n=word(r);need(r,n<=8192-r->values,COH_LIMIT);if(r->status==COH_OK)r->values+=n;for(unsigned k=0;k<n&&r->status==COH_OK;k++){poll(r);(void)string(r);}}else need(r,0,COH_STATE);}need(r,r->at==rowend,COH_INVALID);r->end=outer;}
 need(r,r->at==r->end,COH_INVALID);
}
CohStatus coh_bd_resources_read(CohBytes body,const CohBdResourcePins*p,const CohCostumeImportDigest*d,const CohBdResourceControl*c,CohBdResources*out,CohBdResourcesWorkspace*w,size_t budget,size_t retained){
 if(!p||!d||!c||!out||!w||!ALIGNED(p,CohBdResourcePins)||!ALIGNED(d,CohCostumeImportDigest)||!ALIGNED(c,CohBdResourceControl)||!ALIGNED(out,CohBdResources)||!ALIGNED(w,CohBdResourcesWorkspace)||!budget||budget>COH_BD_RESOURCE_RAM_MAX)return COH_INVALID;
 Span fixed[]={{p,sizeof(*p)},{d,sizeof(*d)},{c,sizeof(*c)},{out,sizeof(*out)},{w,sizeof(*w)}};size_t used=COH_BD_RESOURCE_STACK_RESERVE;
 for(unsigned i=0;i<5;i++){if(!valid(fixed[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(fixed[i],fixed[j]))return COH_INVALID;if(fixed[i].n>budget||used>budget-fixed[i].n)return COH_LIMIT;used+=fixed[i].n;}
 if(!body.data||!body.size||body.size>COH_BD_RESOURCE_INPUT_MAX)return COH_LIMIT;
 if(!d->sha256||(!d->context!=!d->context_bytes)||(!c->cancel.context!=!c->context_bytes))return COH_INVALID;
 Span variable[]={{body.data,body.size},{d->context,d->context_bytes},{c->cancel.context,c->context_bytes}};
 for(unsigned i=0;i<3;i++){if(!valid(variable[i]))return COH_INVALID;for(unsigned j=0;j<5;j++)if(overlap(variable[i],fixed[j]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(variable[i],variable[j]))return COH_INVALID;if(variable[i].n>budget-used)return COH_LIMIT;used+=variable[i].n;}
 if(d->scratch_reserve>budget-used)return COH_LIMIT;
 used+=d->scratch_reserve;if(c->scratch_reserve>budget-used)return COH_LIMIT;
 used+=c->scratch_reserve;if(retained>budget-used)return COH_LIMIT;
 if(!p->provenance||!nonzero(p->expected_sha256))return COH_STATE;
 Read r={body,0,0,0,0,COH_OK,c};poll(&r);if(r.status!=COH_OK)return r.status;CohBdResources*v=&w->candidate;memset(v,0,sizeof(*v));v->provenance=p->provenance;parse(&r,v);if(r.status!=COH_OK)return r.status;poll(&r);if(r.status!=COH_OK)return r.status;CohStatus status=d->sha256(d->context,body,v->sha256);if(status!=COH_OK)return (unsigned)status<=COH_STATE?status:COH_INVALID;if(memcmp(v->sha256,p->expected_sha256,32))return COH_STATE;poll(&r);if(r.status!=COH_OK)return r.status;v->complete=1;*out=*v;return COH_OK;
}
CohStatus coh_bd_resources_group(const CohBdResources*d,uint32_t row,CohBdGroupKind kind,CohBytes*out){Span a={d,sizeof(*d)},b={out,sizeof(*out)};if(!d||!out||!ALIGNED(d,CohBdResources)||!ALIGNED(out,CohBytes)||!valid(a)||!valid(b)||overlap(a,b))return COH_INVALID;if(d->complete!=1||!d->provenance||!nonzero(d->sha256)||d->schema_crc!=UINT32_C(0x326ad4e9)||d->count>COH_BD_RESOURCE_ROWS_MAX||d->text_bytes>COH_BD_RESOURCE_TEXT_MAX||d->runtime_generation||d->actor_authority)return COH_STATE;if((unsigned)kind>=COH_BD_GROUP_COUNT)return COH_INVALID;if(row>=d->count)return COH_NOT_FOUND;CohBdResourceText t=d->rows[row].groups[kind];if(!t.size)return COH_NOT_FOUND;if(t.size>=1024||t.offset>=d->text_bytes||t.size>=d->text_bytes-t.offset||d->text[t.offset+t.size])return COH_STATE;for(unsigned i=0;i<t.size;i++)if(!d->text[t.offset+i]||(unsigned char)d->text[t.offset+i]>=128)return COH_STATE;*out=(CohBytes){(const uint8_t*)d->text+t.offset,t.size};return COH_OK;}

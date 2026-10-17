#include "coh_costume_inputs.h"
#include <string.h>
#include <stdint.h>
#include <math.h>
typedef struct{const void*p;size_t n;} Span;
typedef struct{CohBytes b;size_t at;CohStatus status;} Parse;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static uint32_t bits32(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static const uint8_t* bytes(Parse*p,size_t n){const uint8_t*r;if(p->status!=COH_OK)return NULL;if(n>p->b.size-p->at){p->status=COH_INVALID;return NULL;}r=p->b.data+p->at;p->at+=n;return r;}
static uint32_t word(Parse*p){const uint8_t*b=bytes(p,4);return b?bits32(b):0;}
static void need(Parse*p,int v,CohStatus status){if(p->status==COH_OK&&!v)p->status=status;}
static void text(Parse*p,char out[260]){
 const uint8_t*b=bytes(p,2);size_t n,pad;if(!b)return;n=(size_t)b[0]|((size_t)b[1]<<8);need(p,n<260,COH_LIMIT);if(p->status!=COH_OK)return;
 b=bytes(p,n);if(!b)return;need(p,memchr(b,0,n)==NULL,COH_INVALID);if(p->status!=COH_OK)return;
 memcpy(out,b,n);out[n]=0;pad=(4-(n+2)%4)%4;(void)bytes(p,pad);
}
static size_t segment(Parse*p){uint32_t n=word(p);need(p,n<=p->b.size-p->at,COH_INVALID);return p->status==COH_OK?p->at+n:p->at;}
static void header(Parse*p,CohCostumeInput*out){
 const uint8_t*b=bytes(p,8);char signature[260],section[260];size_t end;
 need(p,b&&memcmp(b,"CrypticS",8)==0,COH_INVALID);out->schema_crc=word(p);
 need(p,out->schema_crc==(out->kind==COH_COSTUME_INPUT_BODY_PARTS?0xcf27aba3u:0xf0095ef2u),COH_STATE);
 text(p,signature);text(p,section);if(p->status!=COH_OK)return;need(p,!strcmp(signature,"Parse6")&&!strcmp(section,"Files1"),COH_UNSUPPORTED);
 end=segment(p);out->dependency_count=word(p);need(p,out->dependency_count<=COH_COSTUME_INPUT_DEPENDENCY_MAX,COH_LIMIT);
 for(uint32_t i=0;i<out->dependency_count&&p->status==COH_OK;i++){text(p,out->dependencies[i].path);out->dependencies[i].timestamp=word(p);need(p,p->at<=end,COH_INVALID);}
 need(p,p->at==end,COH_INVALID);
}
CohStatus coh_costume_input_read(CohBytes b,uint32_t kind,const uint8_t sha[32],const CohCostumeImportDigest*d,
 CohCostumeInputWorkspace*w,CohCostumeInput*out,size_t budget,size_t retained){
 Span spans[6];size_t i,j,charge=COH_COSTUME_INPUT_STACK_RESERVE,end;uint8_t hash[32],any=0;Parse p;CohCostumeInput*c;CohStatus status;
 if(!b.data||!b.size||b.size>COH_COSTUME_INPUT_BYTES_MAX||!sha||!d||!w||!out)return COH_INVALID;
 if(kind!=COH_COSTUME_INPUT_BODY_PARTS&&kind!=COH_COSTUME_INPUT_SUPER_PALETTE)return COH_UNSUPPORTED;
 spans[0]=(Span){b.data,b.size};spans[1]=(Span){sha,32};spans[2]=(Span){d,sizeof(*d)};spans[3]=(Span){w,sizeof(*w)};spans[4]=(Span){out,sizeof(*out)};
 for(i=0;i<5;i++){if(!valid(spans[i]))return COH_INVALID;for(j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 if(!d->sha256||(!d->context&&d->context_bytes))return COH_STATE;
 spans[5]=(Span){d->context,d->context_bytes};if(!valid(spans[5]))return COH_INVALID;for(j=0;j<5;j++)if(!apart(spans[5],spans[j]))return COH_INVALID;
 if(!budget||budget>COH_COSTUME_INPUT_BUDGET_MAX)return COH_LIMIT;
 for(i=0;i<6;i++){if(spans[i].n>budget||charge>budget-spans[i].n)return COH_LIMIT;charge+=spans[i].n;}
 if(d->scratch_reserve>budget||charge>budget-d->scratch_reserve)return COH_LIMIT;
 charge+=d->scratch_reserve;if(retained>budget||charge>budget-retained)return COH_LIMIT;
 for(i=0;i<32;i++)any|=sha[i];
 if(!any)return COH_STATE;
 memset(w,0,sizeof(*w));c=&w->candidate;c->kind=kind;p=(Parse){b,0,COH_OK};header(&p,c);end=segment(&p);need(&p,end==b.size,COH_INVALID);
 if(kind==COH_COSTUME_INPUT_BODY_PARTS){
  c->part_count=word(&p);need(&p,c->part_count>0&&c->part_count<=COH_COSTUME_INPUT_PART_MAX,COH_LIMIT);
  for(uint32_t n=0;n<c->part_count&&p.status==COH_OK;n++){
   CohCostumeInputPart*row=&c->parts[n];size_t rowend=segment(&p);
   text(&p,row->name);text(&p,row->source_file);row->bone_count_first=word(&p);row->influence_cost=word(&p);
   text(&p,row->geometry_name);text(&p,row->texture_name);text(&p,row->base_name);row->bone_count_last=word(&p);row->dont_clear_word=word(&p);row->bones[0]=word(&p);row->bones[1]=word(&p);row->part_index=word(&p);need(&p,p.at==rowend&&rowend<=end,COH_INVALID);
  }
 }else{
  c->color_count=word(&p);need(&p,c->color_count<=COH_COSTUME_INPUT_COLOR_MAX,COH_LIMIT);
  for(uint32_t n=0;n<c->color_count&&p.status==COH_OK;n++){
   size_t rowend=segment(&p);
   for(unsigned k=0;k<3;k++){float value;c->colors[n][k]=word(&p);memcpy(&value,&c->colors[n][k],4);need(&p,isfinite(value),COH_INVALID);}
   need(&p,p.at==rowend&&rowend<=end,COH_INVALID);
  }text(&p,c->palette_name);
 }
 need(&p,p.at==end&&p.at==b.size,COH_INVALID);if(p.status!=COH_OK)return p.status;
 status=d->sha256(d->context,b,hash);if(status!=COH_OK)return status;if(memcmp(hash,sha,32))return COH_STATE;
 c->end_byte=p.at;memcpy(c->payload_sha256,hash,32);*out=*c;return COH_OK;
}

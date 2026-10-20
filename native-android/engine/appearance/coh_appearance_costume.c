#include "coh_appearance_costume.h"
#include <string.h>
typedef struct {const void *p;size_t n;} Span;
static int valid(Span a){return !a.n||(a.p&&a.n<=UINTPTR_MAX-(uintptr_t)a.p);}
static int separate(Span a,Span b){return !a.n||!b.n||((uintptr_t)a.p<(uintptr_t)b.p?a.n<=(uintptr_t)b.p-(uintptr_t)a.p:b.n<=(uintptr_t)a.p-(uintptr_t)b.p);}
static int readable(Span a,const Span *writes){unsigned i;if(!valid(a))return 0;for(i=0;i<4;i++)if(!separate(a,writes[i]))return 0;return 1;}
static int text(const char *s,const Span *writes){size_t n;if(!s)return 0;for(n=0;n<256;n++){
 Span c={(const void *)((uintptr_t)s+n),1};if((uintptr_t)s>UINTPTR_MAX-n||!readable(c,writes))return 0;if(!s[n])return 1;
 }return 0;}
static int fixed_text(const char *s,uint32_t present){return memchr(s,0,260)&&((present!=0)||s[0]==0);}
static void rgba(uint8_t out[4],uint32_t value){unsigned i;for(i=0;i<4;i++)out[i]=(uint8_t)(value>>(i*8));}
static void clear_borrows(CohAppearanceCostumeWorkspace *w){memset(&w->request,0,sizeof(w->request));memset(w->parts,0,sizeof(w->parts));}
CohStatus coh_appearance_costume_assemble(const CohOriginalCostumeSnapshot *s,const CohAppearanceCostumeInputs *in,CohAppearanceCostumeWorkspace *w,CohAppearanceDraw *out,size_t capacity,size_t *count,CohAppearanceCostumeDiagnostics *diag){
 Span writes[4],borrowed;unsigned i,j;CohStatus status;CohAppearanceCostumeDiagnostics result;size_t n;
 if(!s||!in||!w||!out||!count||!diag)return COH_INVALID;
 if((uintptr_t)s%sizeof(uint32_t)||(uintptr_t)in%sizeof(void*)||(uintptr_t)w%sizeof(void*)||(uintptr_t)out%sizeof(uint32_t)||(uintptr_t)count%sizeof(size_t)||(uintptr_t)diag%sizeof(size_t))return COH_INVALID;
 if(capacity>SIZE_MAX/sizeof(*out))return COH_LIMIT;
 writes[0]=(Span){w,sizeof(*w)};writes[1]=(Span){out,capacity*sizeof(*out)};writes[2]=(Span){count,sizeof(*count)};writes[3]=(Span){diag,sizeof(*diag)};
 for(i=0;i<4;i++){if(!valid(writes[i]))return COH_INVALID;for(j=0;j<i;j++)if(!separate(writes[i],writes[j]))return COH_INVALID;}
 borrowed=(Span){s,sizeof(*s)};if(!readable(borrowed,writes))return COH_INVALID;
 borrowed=(Span){in,sizeof(*in)};if(!readable(borrowed,writes))return COH_INVALID;
 if(s->bodytype>=9||s->part_count>30||s->header_present>3||!in->definitions||!in->definition_count||in->definition_count>60||s->part_count>in->definition_count||in->chest_link_count>16||(in->chest_link_count&&!in->chest_links))return COH_INVALID;
 if((uintptr_t)in->definitions%sizeof(void*)||(uintptr_t)in->chest_links%sizeof(void*))return COH_INVALID;
 if(!fixed_text(s->ent_type,s->header_present&1)||!fixed_text(s->geometry_prefix,s->header_present&2))return COH_INVALID;
 borrowed=(Span){in->definitions,in->definition_count*sizeof(*in->definitions)};if(!readable(borrowed,writes))return COH_INVALID;
 for(i=0;i<in->definition_count;i++){
  const CohAppearancePartDef *d=in->definitions+i;
  if(!text(d->name,writes)||!text(d->geometry_name,writes)||!text(d->texture_name,writes)||!text(d->base_name,writes))return COH_INVALID;
 }
 borrowed=(Span){in->chest_links,in->chest_link_count*sizeof(*in->chest_links)};if(!readable(borrowed,writes))return COH_INVALID;
 for(i=0;i<in->chest_link_count;i++)if(!text(in->chest_links[i],writes))return COH_INVALID;
 for(i=0;i<s->part_count;i++){
  const CohOriginalCostumeSnapshotPart *p=s->parts+i;if(p->present_mask>63)return COH_INVALID;
  for(j=0;j<6;j++)if(!fixed_text(p->strings[j],p->present_mask&(1u<<j)))return COH_INVALID;
 }
 memset(&result,0,sizeof(result));status=coh_appearance_body(s->bodytype,s->header_present&1?s->ent_type:NULL,s->header_present&2?s->geometry_prefix:NULL,&result.body);if(status)return status;
 memset(&w->request,0,sizeof(w->request));memset(w->parts,0,sizeof(w->parts));
 w->request.body=result.body;w->request.definitions=in->definitions;w->request.definition_count=in->definition_count;w->request.parts=w->parts;w->request.part_count=s->part_count;w->request.generation=in->generation;
 rgba(w->request.skin,s->color_skin);w->request.chest_links=in->chest_links;w->request.chest_link_count=in->chest_link_count;w->request.probe=in->probe;w->request.probe_context=in->probe_context;w->request.cancel=in->cancel;
 for(i=0;i<s->part_count;i++){
  const CohOriginalCostumeSnapshotPart *p=s->parts+i;CohAppearancePart *part=w->parts+i;part->definition=i;
  part->geometry=p->present_mask&1?p->strings[0]:NULL;part->texture[0]=p->present_mask&2?p->strings[1]:NULL;part->texture[1]=p->present_mask&4?p->strings[2]:NULL;
  for(j=0;j<4;j++)rgba(part->color[j],p->colors[j]);
 }
 status=coh_appearance_assemble(&w->request,&w->assembly,out,capacity,&n,&result.assembly);clear_borrows(w);if(status)return status;
 result.workspace_bytes=sizeof(*w);*count=n;*diag=result;return COH_OK;
}

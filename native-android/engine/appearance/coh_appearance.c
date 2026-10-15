#include "coh_appearance.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static const char *const ent_types[]={"male","fem","bm","bf","huge","enemy","enemy","enemy2","enemy3"};
static const char *const tex_prefixes[]={"SM","SF","BM","BF","SH","EY","EY","EY","EY"};
/* Bounded ASCII identity matches original stricmp, independent of locale. */
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32u:c;}
static int equal(const char *a,const char *b){for(;*a&&*b;a++,b++)if(lower((unsigned char)*a)!=lower((unsigned char)*b))return 0;return *a==*b;}
static const char *find(const char *s,const char *needle){size_t n=strlen(needle);for(;*s;s++){size_t i=0;while(i<n&&s[i]&&lower((unsigned char)s[i])==lower((unsigned char)needle[i]))i++;if(i==n)return s;}return NULL;}
static int valid(const char *s,int allow_empty){if(!s)return 0;size_t n=0;for(;n<256&&s[n];n++){unsigned c=(unsigned char)s[n];if(c<32u||c>126u||c=='\\')return 0;}return n<256&&(allow_empty||n);}
static int plain(const char *s){return valid(s,0)&&!strchr(s,'/')&&!strchr(s,'.')&&!strchr(s,'*');}
static int copy(char *d,const char *s){if(!valid(s,0))return 0;memcpy(d,s,strlen(s)+1);return 1;}
static int formatted(char *out,const char *a,const char *b,const char *c,const char *d,const char *e){int n=snprintf(out,256,"%s%s%s%s%s",a,b,c,d,e);return n>=0&&n<256;}
static int chest(const char *s){return equal(s,"Collar")||equal(s,"Capeharness")||equal(s,"Broach")||equal(s,"Back")||equal(s,"Cape");}
static int probe(const CohAppearanceRequest *r,uint32_t kind,const char *s,CohAppearanceDiagnostics *d){if(!r->probe)return 0;if(kind==COH_APPEARANCE_TEXTURE)d->texture_probes++;else d->geometry_probes++;return r->probe(r->probe_context,kind,s)!=0;}

CohStatus coh_appearance_body(uint32_t type,const char *ent,const char *prefix,CohAppearanceBody *out){
 if(!out||type>=9u)return COH_INVALID;
 if(type==6u&&(!ent||!prefix))return COH_UNSUPPORTED;
 if((ent&&!plain(ent))||(prefix&&!plain(prefix)))return COH_INVALID;
 CohAppearanceBody b;memset(&b,0,sizeof b);b.body_type=type;
 copy(b.ent_type,ent?ent:ent_types[type]);copy(b.geometry_prefix,prefix?prefix:ent_types[type]);
 copy(b.texture_prefix,type==6u?prefix:tex_prefixes[type]);*out=b;return COH_OK;
}
static CohStatus geometry(const CohAppearanceRequest *r,const CohAppearancePartDef *def,const char *name,char keys[2][256],uint32_t *emit,CohAppearanceDiagnostics *diag){
 *emit=0;if(!name)return COH_OK;
 if(!valid(name,0))return COH_INVALID;
 if(equal(name,"NONE")){for(uint32_t i=0;i<def->socket_count;i++)copy(keys[i],"NONE");*emit=def->socket_count;return COH_OK;}
 const char *sep=find(name,".geo/");char base[256],tmp[256];
 if(sep){
  size_t n=(size_t)(sep-name);if(!n||n>=256||!sep[5])return COH_INVALID;
  memcpy(base,name,n);base[n]=0;
  if(!plain(base)||strchr(sep+5,'/')||strchr(sep+5,'.'))return COH_UNSUPPORTED;
  if(!formatted(keys[0],base,".",sep+5,"",""))return COH_LIMIT;
  if(chest(def->name)){
   for(uint32_t j=0;j<r->chest_link_count;j++){if(!formatted(tmp,keys[0],"_",r->chest_links[j],"",""))return COH_LIMIT;if(probe(r,COH_APPEARANCE_GEOMETRY,tmp,diag)){copy(keys[0],tmp);break;}}
   *emit=1;return COH_OK;
  }
  if(def->socket_count==1u){*emit=1;return COH_OK;}
  char *star=strchr(keys[0],'*');
  if(star){if(strchr(star+1,'*'))return COH_INVALID;*star='R';copy(keys[1],keys[0]);keys[1][star-keys[0]]='L';*emit=2;return COH_OK;}
  if(find(keys[0],"LArmR")||find(keys[0],"LLegR")){copy(keys[1],"NONE");*emit=2;return COH_OK;}
  if(find(keys[0],"LArmL")||find(keys[0],"LLegL")){copy(keys[1],keys[0]);copy(keys[0],"NONE");*emit=2;return COH_OK;}
  /* Original performs no changeGeo call in this branch. Preserve old part. */
  return COH_OK;
 }
 if(strchr(name,'/')||strchr(name,'.')||strchr(name,'*'))return COH_UNSUPPORTED;
 if(!formatted(base,r->body.geometry_prefix,"_",def->base_name,".GEO_",def->geometry_name))return COH_LIMIT;
 for(uint32_t i=0;i<def->socket_count;i++){
  char side[2]={def->socket_count==2u?(i==0?'R':'L'):0,0};
  if(!formatted(tmp,base,side,"_",name,""))return COH_LIMIT;
  copy(keys[i],tmp);
  if(i==0&&chest(def->name))for(uint32_t j=0;j<r->chest_link_count;j++){
   char linked[256];if(!formatted(tmp,base,side,"_",r->chest_links[j],"_")||!formatted(linked,tmp,name,"","",""))return COH_LIMIT;
   if(probe(r,COH_APPEARANCE_GEOMETRY,linked,diag)){copy(keys[i],linked);break;}
  }
 }
 *emit=def->socket_count;return COH_OK;
}
static CohStatus textures(const CohAppearanceRequest *r,const CohAppearancePartDef *d,const CohAppearancePart *p,char names[2][256],CohAppearanceDiagnostics *diag){
 if(!p->texture[0]||!valid(p->texture[0],0)||(p->texture[1]&&!valid(p->texture[1],0)))return COH_INVALID;
 const char *n1=p->texture[0],*n2=p->texture[1];size_t n=strlen(n1);
 int single=lower((unsigned char)n1[n-1])=='x',dual=lower((unsigned char)n1[n-1])=='a';
 for(uint32_t i=0;i<2;i++){
  const char *s=i?n2:n1;int explicit_name=s&&s[0]=='!';const char *bare=s?s+explicit_name:NULL;
  if(bare&&!*bare)return COH_INVALID;
  if(!bare||equal(bare,"NONE")||(i&&single))copy(names[i],"none");
  else if(explicit_name)copy(names[i],bare);
  else if(i&&dual&&r->body.geometry_prefix[0]&&(n=strlen(names[0]))>=3&&equal(names[0]+n-3,"01a")){
   copy(names[1],names[0]);names[1][n-1]='B';
  }else if(!formatted(names[i],d->texture_name,"_",bare,"",""))return COH_LIMIT;
 }
 /* Prefix lookup occurs after both base names are computed in source. */
 for(uint32_t i=0;i<2;i++){
  const char *s=p->texture[i];if(!s||s[0]!='!'){
   char candidate[256];if(!formatted(candidate,r->body.texture_prefix,"_",names[i],".tga",""))return COH_LIMIT;
   if(probe(r,COH_APPEARANCE_TEXTURE,candidate,diag)){candidate[strlen(candidate)-4]=0;copy(names[i],candidate);}
  }
 }
 return COH_OK;
}
static CohStatus split(CohAppearanceDraw *d){
 if(equal(d->geometry_key,"NONE")){d->flags|=COH_APPEARANCE_CLEAR;return COH_OK;}
 const char *dot=strchr(d->geometry_key,'.');if(!dot||dot==d->geometry_key||!dot[1])return COH_INVALID;
 size_t n=(size_t)(dot-d->geometry_key);char file[256];memcpy(file,d->geometry_key,n);file[n]=0;
 if(!formatted(d->geometry_path,"data/player_library/",file,".geo","",""))return COH_LIMIT;
 if(!copy(d->model_name,dot+1))return COH_INVALID;
 return COH_OK;
}
CohStatus coh_appearance_assemble(const CohAppearanceRequest *r,CohAppearanceWorkspace *w,CohAppearanceDraw *out,size_t capacity,size_t *count,CohAppearanceDiagnostics *diagnostics){
 if(!r||!w||!out||!count||!diagnostics||r->body.body_type>=9||!valid(r->body.ent_type,0)||!plain(r->body.geometry_prefix)||!plain(r->body.texture_prefix)||!r->definitions||!r->definition_count||r->definition_count>60||r->part_count>60||(r->part_count&&!r->parts)||r->chest_link_count>16||(r->chest_link_count&&!r->chest_links))return COH_INVALID;
 /* Overlap would invalidate transactionality or mutate borrowed inputs. */
 uintptr_t wb=(uintptr_t)w,ob=(uintptr_t)out;size_t output_bytes;
 if(capacity>SIZE_MAX/sizeof(*out))return COH_LIMIT;
 output_bytes=capacity*sizeof(*out);
 if((ob>=wb&&ob-wb<sizeof(*w))||(wb>=ob&&wb-ob<output_bytes))return COH_INVALID;
 for(uint32_t i=0;i<r->definition_count;i++){
  const CohAppearancePartDef *d=r->definitions+i;
  if(!plain(d->name)||!plain(d->geometry_name)||!plain(d->texture_name)||!plain(d->base_name)||!d->socket_count||d->socket_count>2||(d->socket[0]>=99&&d->socket[0]!=UINT32_MAX)||(d->socket_count==2&&((d->socket[1]>=99&&d->socket[1]!=UINT32_MAX)||d->socket[0]==d->socket[1])))return COH_INVALID;
 }
 for(uint32_t i=0;i<r->chest_link_count;i++)if(!plain(r->chest_links[i]))return COH_INVALID;
 for(uint32_t i=0;i<r->part_count;i++){
  if(r->parts[i].definition>=r->definition_count)return COH_INVALID;
  for(uint32_t j=0;j<i;j++)if(r->parts[j].definition==r->parts[i].definition)return COH_INVALID;
 }
 CohAppearanceDiagnostics diag={0};diag.scratch_bytes=sizeof(*w);size_t total=0;
 for(uint32_t i=0;i<r->part_count;i++){
  if(r->cancel.poll&&r->cancel.poll(r->cancel.context))return COH_CANCELLED;
  const CohAppearancePart *p=r->parts+i;const CohAppearancePartDef *d=r->definitions+p->definition;
  if(d->socket[0]==UINT32_MAX)continue;
  char keys[2][256]={{0}},tex[2][256]={{0}};uint32_t emit=0;
  CohStatus status=geometry(r,d,p->geometry,keys,&emit,&diag);if(status)return status;
  if(!emit)continue;
  for(uint32_t j=0;j<emit;j++)if(d->socket[j]>=99)return COH_INVALID;
  status=textures(r,d,p,tex,&diag);if(status)return status;
  if(total+emit>capacity)return COH_LIMIT;
  for(uint32_t j=0;j<emit;j++){
   CohAppearanceDraw *draw=&w->draws[total++];memset(draw,0,sizeof(*draw));
   draw->definition=p->definition;draw->socket=d->socket[j];draw->generation=r->generation;
   copy(draw->geometry_key,keys[j]);copy(draw->texture[0],tex[0]);copy(draw->texture[1],tex[1]);memcpy(draw->color,p->color,16);
   if(find(p->texture[0],"skin")){memcpy(draw->color[1],p->color[0],4);memcpy(draw->color[0],r->skin,4);draw->flags|=COH_APPEARANCE_SKIN_COLOR;diag.skin_routed++;}
   status=split(draw);if(status)return status;if(draw->flags&COH_APPEARANCE_CLEAR)diag.cleared++;
  }
 }
 memcpy(out,w->draws,total*sizeof(*out));diag.draws=(uint32_t)total;*count=total;*diagnostics=diag;return COH_OK;
}

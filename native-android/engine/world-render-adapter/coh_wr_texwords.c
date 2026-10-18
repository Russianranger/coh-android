#include "coh_wr_texwords.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <stdio.h>

#define MAX_CACHE (16u*1024u*1024u)
#define OWN_RESERVE 32768u
#define QUERY_RESERVE 16384u
#define K_INT 1u
#define K_FLOAT 2u
#define K_STRING 3u
#define K_STRUCT 4u
#define K_ARRAY 256u
#define K_FIXED 512u
#define TOK_END 0u
#define TOK_IGNORE 0u
#define TOK_STRUCTPARAM 1024u
#define TOK_STRING(s,m,d) K_STRING,0,d
#define TOK_CURRENTFILE(s,m) K_STRING,0,0
#define TOK_INT(s,m,d) K_INT,0,d
#define TOK_U8(s,m,d) K_INT,0,d
#define TOK_BOOLFLAG(s,m,d) K_INT,0,d
#define TOK_F32(s,m,d) K_FLOAT,0,d
#define TOK_VEC2(s,m) K_FIXED|K_FLOAT,0,2
#define TOK_INTARRAY(s,m) K_ARRAY|K_INT,0,0
#define TOK_STRUCT(s,m,t) K_ARRAY|K_STRUCT,0,0,t
#define TOK_EMBEDDEDSTRUCT(s,m,t) K_STRUCT,0,0,t
#define TOK_NULLSTRUCT(t) K_STRUCT,0,0,t
typedef struct Table {const char *name;uint32_t type,offset;intptr_t param;const void *subtable;} Table;
static const int ParseTexWordLayerType[]={0},ParseTexWordLayerStretch[]={0},ParseTexWordFilterType[]={0},ParseTexWordBlendType[]={0};
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#define TokenizerParseInfo static const Table
#include "coh_wr_texwords_tables_source.inc"
#undef TokenizerParseInfo
#pragma GCC diagnostic pop

typedef struct {uint32_t offset,length,timestamp;} File;
typedef struct {
 uint32_t offset,bytes,name,length,owner,priority;
 char key[260],stem[128],locale[32];
} Row;
struct CohWrTexWords {
 CohWrTexWordsReport report;size_t allocation;
 uint32_t verbose,row_count,file_count,node_limit;
 Row *rows;File *files;uint8_t *data;
};
typedef struct {const uint8_t *data;size_t pos,end;CohWrTexWords *owner;CohCancel cancel;} Reader;
static int apart(const void *a,size_t an,const void *b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 return an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);
}
static int add(size_t *v,size_t n){if(n>SIZE_MAX-*v)return 0;*v+=n;return 1;}
static int stopped(CohCancel c){return c.poll&&c.poll(c.context);}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int icmp(const char *a,const char *b){for(;*a&&*b;a++,b++){int d=(int)fold((unsigned char)*a)-(int)fold((unsigned char)*b);if(d)return d;}return (unsigned char)*a-(unsigned char)*b;}
static int readable_name(const char *s,size_t bound,size_t *length){
 if(!s)return 0;
 for(size_t i=0;i<bound;i++){unsigned c=(unsigned char)s[i];if(!c){*length=i;return 1;}if(c<32||c>126)return 0;}
 return 0;
}
static int word(Reader *r,uint32_t *v){
 if(r->pos>r->end||r->end-r->pos<4)return 0;
 const uint8_t *p=r->data+r->pos;r->pos+=4;
 *v=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;return 1;
}
static int string(Reader *r,uint32_t *offset,uint32_t *length){
 if(r->pos>r->end||r->end-r->pos<2)return 0;
 uint32_t n=(uint32_t)r->data[r->pos]|(uint32_t)r->data[r->pos+1]<<8;
 r->pos+=2;size_t padding=(4-(n+2)%4)%4;
 if(n>=12000u||n>r->end-r->pos||padding>r->end-r->pos-n||memchr(r->data+r->pos,0,n))return 0;
 *offset=(uint32_t)r->pos;*length=n;r->pos+=n+padding;return 1;
}
static CohStatus table(Reader*,const Table*,Row*,unsigned);
static CohStatus subtable(Reader *r,const Table *t,Row *row,unsigned depth){
 uint32_t bytes;if(!word(r,&bytes)||bytes>r->end-r->pos)return COH_INVALID;
 Reader child=*r;child.end=child.pos+bytes;
 if(row){row->offset=(uint32_t)child.pos;row->bytes=bytes;}
 CohStatus status=table(&child,t,row,depth+1);
 if(status!=COH_OK)return status;
 if(child.pos!=child.end)return COH_INVALID;
 r->pos=child.end;return COH_OK;
}
static CohStatus table(Reader *r,const Table *t,Row *row,unsigned depth){
 CohWrTexWords *c=r->owner;
 if(depth>16||c->report.nested_structs>=c->node_limit)return COH_LIMIT;
 c->report.nested_structs++;
 for(unsigned i=0;t[i].type||t[i].name[0];i++){
  unsigned kind=t[i].type&255u;if(!kind)continue;
  if(stopped(r->cancel))return COH_CANCELLED;
  if(c->report.fields==UINT32_MAX)return COH_LIMIT;
  c->report.fields++;
  uint32_t n=(t[i].type&K_FIXED)?(uint32_t)t[i].param:1;
  if(t[i].type&K_ARRAY){if(!word(r,&n))return COH_INVALID;if(n>4096)return COH_LIMIT;}
  for(uint32_t j=0;j<n;j++){
   if(kind==K_STRUCT){
    Row *root=NULL;
    if(t==ParseTexWordFiles){if(j>=c->row_count)return COH_INVALID;root=&c->rows[j];}
    CohStatus status=subtable(r,t[i].subtable,root,depth);if(status!=COH_OK)return status;
   } else if(kind==K_STRING){
    uint32_t offset,length;if(!string(r,&offset,&length))return COH_INVALID;
    if(row&&t==ParseTexWord&&i==1){row->name=offset;row->length=length;}
   } else if(kind==K_INT||kind==K_FLOAT){
    uint32_t v;if(!word(r,&v))return COH_INVALID;
    if(kind==K_FLOAT){float f;memcpy(&f,&v,4);if(!isfinite(f))return COH_UNSUPPORTED;}
   } else return COH_UNSUPPORTED;
  }
 }
 return COH_OK;
}
static int ascii_span(const uint8_t *p,size_t n){for(size_t i=0;i<n;i++)if(p[i]<32||p[i]>126)return 0;return 1;}
static int same_span(const uint8_t *a,uint32_t an,const uint8_t *b,uint32_t bn){if(an!=bn)return 0;for(uint32_t i=0;i<an;i++)if(fold(a[i])!=fold(b[i]))return 0;return 1;}
static CohStatus configuration(const CohWrTexWordsConfig *q,CohWrTexWordsReport *r){
 if(q->region_eu>1||q->texword_edit>1||q->production_mode>1||q->verbose>1||q->allow_loading!=1||q->pending_compositors||q->has_override)return COH_UNSUPPORTED;
 if(q->production_mode&&q->texword_edit)return COH_UNSUPPORTED;
 size_t n;if(!readable_name(q->locale,32,&n)||!n)return COH_INVALID;
 for(size_t i=0;i<n;i++){unsigned x=(unsigned char)q->locale[i];if(!((x>='A'&&x<='Z')||(x>='a'&&x<='z')||x=='_'||x=='-'))return COH_UNSUPPORTED;}
 const char *locale=q->locale;
 if(q->texword_edit&&!icmp(locale,"English"))locale="Base";
 memcpy(r->locale,locale,strlen(locale)+1);
 if(!icmp(locale,"English")){
  if(q->region_eu){memcpy(r->secondary_locale,"UK",3);(void)snprintf(r->search_path,sizeof(r->search_path),"#UK;#%s",locale);}
  else (void)snprintf(r->search_path,sizeof(r->search_path),"#%s",locale);
 } else {
  int count=snprintf(r->search_path,sizeof(r->search_path),"#%s;#Base",locale);
  if(count<0||(size_t)count>=sizeof(r->search_path))return COH_LIMIT;
 }
 return COH_OK;
}
static CohStatus frame(Reader *r,uint32_t *files,uint32_t *rows,size_t *file_pos,size_t *root_pos){
 uint32_t v,offset,n;
 if(r->end<36||memcmp(r->data,"CrypticS",8))return COH_INVALID;
 r->pos=8;
 if(!word(r,&v)||v!=0x479da30au||!string(r,&offset,&n)||n!=6||memcmp(r->data+offset,"Parse6",6)||
    !string(r,&offset,&n)||n!=6||memcmp(r->data+offset,"Files1",6)||!word(r,&v)||v>r->end-r->pos)return COH_INVALID;
 Reader f=*r;f.end=f.pos+v;*file_pos=f.pos;
 if(!word(&f,files)||*files>4096)return COH_LIMIT;
 for(uint32_t i=0;i<*files;i++)if(!string(&f,&offset,&n)||!n||n>=260||!ascii_span(f.data+offset,n)||!word(&f,&v))return COH_INVALID;
 if(f.pos!=f.end)return COH_INVALID;
 r->pos=f.end;
 if(!word(r,&v)||v!=r->end-r->pos)return COH_INVALID;
 *root_pos=r->pos;
 if(!word(r,rows)||*rows>4096)return COH_LIMIT;
 return COH_OK;
}
static CohStatus dictionary(CohWrTexWords *c,CohCancel cancel){
 for(uint32_t i=0;i<c->row_count;i++){
  if(stopped(cancel))return COH_CANCELLED;
  Row *row=&c->rows[i];const uint8_t *raw=c->data+row->name;size_t n=row->length;
  if(n<17||n>=260||!ascii_span(raw,n)||memchr(raw,'\\',n)||memchr(raw,':',n))return COH_UNSUPPORTED;
  int source_file=0;for(uint32_t k=0;k<c->file_count;k++)if(same_span(raw,(uint32_t)n,c->data+c->files[k].offset,c->files[k].length))source_file++;
  if(source_file!=1)return COH_INVALID;
  char path[260];memcpy(path,raw,n);path[n]=0;for(size_t k=0;k<n;k++)if(path[k]=='\\')path[k]='/';
  if(icmp(path+strlen(path)-8,".texword")||strstr(path,"//")||strstr(path,"/../")||strstr(path,"/./"))return COH_UNSUPPORTED;
  if(fold(raw[0])!='t'||fold(raw[1])!='e'||fold(raw[2])!='x'||fold(raw[3])!='t'||fold(raw[4])!='s'||raw[5]!='/')return COH_UNSUPPORTED;
  char *p=path;if(n>=5&&fold((unsigned char)p[0])=='t'&&fold((unsigned char)p[1])=='e'&&fold((unsigned char)p[2])=='x'&&fold((unsigned char)p[3])=='t'&&fold((unsigned char)p[4])=='s')p+=5;
  while(*p=='/')p++;
  char *slash=strchr(p,'/');if(!slash||slash==p)return COH_UNSUPPORTED;
  size_t locale=(size_t)(slash-p);if(locale>=sizeof(row->locale))return COH_LIMIT;memcpy(row->locale,p,locale);row->locale[locale]=0;
  char *base=strrchr(path,'/');base=base?base+1:path;char *dot=strrchr(base,'.');if(!dot||icmp(dot,".texword"))return COH_UNSUPPORTED;
  size_t stem=(size_t)(dot-base);if(!stem||stem>=sizeof(row->stem))return COH_LIMIT;memcpy(row->stem,base,stem);row->stem[stem]=0;
  row->priority=!icmp(row->locale,c->report.secondary_locale)&&c->report.secondary_locale[0]?2u:!icmp(row->locale,c->report.locale)?1u:0u;
  int count=row->priority?snprintf(row->key,sizeof(row->key),"%s",row->stem):snprintf(row->key,sizeof(row->key),"%s#%s",row->stem,row->locale);
  if(count<0||(size_t)count>=sizeof(row->key))return COH_LIMIT;
  row->owner=i;
  for(uint32_t k=0;k<i;k++){
   Row *old=&c->rows[k];
   if(!icmp(old->stem,row->stem)&&!icmp(old->locale,row->locale))return COH_UNSUPPORTED;
   if(!icmp(old->key,row->key)){
    if(old->priority==row->priority||!old->priority||!row->priority)return COH_UNSUPPORTED;
    row->owner=old->priority>row->priority?old->owner:i;
    for(uint32_t x=0;x<i;x++)if(!icmp(c->rows[x].key,row->key))c->rows[x].owner=row->owner;
   }
  }
 }
 for(uint32_t i=0;i<c->row_count;i++)if(c->rows[i].owner==i)c->report.keys++;
 return COH_OK;
}
static int output_ok(const CohWrTexWords *c,const void *out,size_t bytes){return apart(c,c->allocation,out,bytes);}
CohStatus coh_wr_texwords_create(CohAssetLoader *loader,const CohWrTexWordsRequest *q,const CohWrTexWordsLimits *lim,CohCancel cancel,CohWrTexWords **out){
 if(!loader||!q||!lim||!out||(uintptr_t)out%_Alignof(CohWrTexWords*))return COH_INVALID;
 if(!apart(q,sizeof(*q),out,sizeof(*out))||!apart(lim,sizeof(*lim),out,sizeof(*out)))return COH_INVALID;
 size_t path_bytes,locale_bytes;
 if(!readable_name(q->asset.path,32,&path_bytes)||strcmp(q->asset.path,"data/bin/texWords.bin")||!q->asset.generation||!q->digest||q->bytes<36||q->bytes>MAX_CACHE||
    !readable_name(q->config.locale,32,&locale_bytes)||!apart(q->asset.path,path_bytes+1,out,sizeof(*out))||!apart(q->config.locale,locale_bytes+1,out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 if(!lim->record_limit||lim->record_limit>4096||!lim->node_limit||lim->node_limit>65536||!lim->loader_reservation)return COH_LIMIT;
 CohWrTexWordsReport report={0};CohStatus status=configuration(&q->config,&report);if(status!=COH_OK)return status;
 size_t total=lim->external_bytes;
 if(!add(&total,lim->loader_reservation)||!add(&total,lim->owned_limit)||!add(&total,OWN_RESERVE)||!add(&total,sizeof(*q)+sizeof(*lim)+path_bytes+locale_bytes+2)||total>lim->aggregate_limit||coh_asset_stats(loader).peak_allocated_bytes>lim->loader_reservation)return COH_LIMIT;
 if(stopped(cancel))return COH_CANCELLED;
 const CohAssetBlob *blob=NULL;CohWrTexWords *c=NULL;status=coh_asset_acquire(loader,q->asset,cancel,&blob);if(status!=COH_OK)return status;
 CohBytes bytes=coh_asset_bytes(blob);CohAssetId identity=coh_asset_identity(blob);uint8_t hash[32];
 if(!apart(bytes.data,bytes.size,out,sizeof(*out))||bytes.size!=q->bytes||identity.generation!=q->asset.generation||strcmp(identity.path,q->asset.path)){status=COH_INVALID;goto done;}
 status=q->digest(q->digest_context,bytes,hash);if(status!=COH_OK)goto done;
 if(memcmp(hash,q->sha256,32)){status=COH_INVALID;goto done;}
 if(coh_asset_stats(loader).peak_allocated_bytes>lim->loader_reservation){status=COH_LIMIT;goto done;}
 Reader initial={bytes.data,0,bytes.size,NULL,{0}};uint32_t files,rows;size_t file_pos,root_pos;
 status=frame(&initial,&files,&rows,&file_pos,&root_pos);if(status!=COH_OK)goto done;
 if(rows>lim->record_limit){status=COH_LIMIT;goto done;}
 size_t allocation=sizeof(*c);if(!add(&allocation,(size_t)rows*sizeof(Row))||!add(&allocation,(size_t)files*sizeof(File))||!add(&allocation,bytes.size)||allocation>lim->owned_limit){status=COH_LIMIT;goto done;}
 c=calloc(1,allocation);if(!c){status=COH_LIMIT;goto done;}
 c->allocation=allocation;c->rows=(Row*)(c+1);c->files=(File*)(c->rows+rows);c->data=(uint8_t*)(c->files+files);memcpy(c->data,bytes.data,bytes.size);
 c->report=report;c->verbose=q->config.verbose;c->row_count=rows;c->file_count=files;c->node_limit=lim->node_limit;
 c->report.source_generation=identity.generation;c->report.records=rows;c->report.source_files=files;c->report.owned_bytes=allocation;c->report.preparation_aggregate_reserved_bytes=total;c->report.layout_composition_unqualified=1;c->report.current_generation_unqualified=1;memcpy(c->report.sha256,hash,32);
 Reader fr={c->data,file_pos,root_pos-4,c,cancel};uint32_t count;
 if(!word(&fr,&count)||count!=files){status=COH_INVALID;goto done;}
 for(uint32_t i=0;i<files;i++){
  if(stopped(cancel)){status=COH_CANCELLED;goto done;}
  File *file=&c->files[i];if(!string(&fr,&file->offset,&file->length)||!word(&fr,&file->timestamp)){status=COH_INVALID;goto done;}
  for(uint32_t k=0;k<i;k++)if(same_span(c->data+file->offset,file->length,c->data+c->files[k].offset,c->files[k].length)){status=COH_UNSUPPORTED;goto done;}
 }
 if(fr.pos!=fr.end){status=COH_INVALID;goto done;}
 Reader tree={c->data,root_pos,bytes.size,c,cancel};status=table(&tree,ParseTexWordFiles,NULL,0);if(status!=COH_OK)goto done;
 if(tree.pos!=tree.end){status=COH_INVALID;goto done;}
 status=dictionary(c,cancel);if(status!=COH_OK)goto done;
 if(stopped(cancel)){status=COH_CANCELLED;goto done;}
done:
 coh_asset_release(loader,blob);
 if(status!=COH_OK){free(c);return status;}
 *out=c;return COH_OK;
}
CohStatus coh_wr_texwords_destroy(CohWrTexWords **p){if(!p||(uintptr_t)p%_Alignof(CohWrTexWords*))return COH_INVALID;if(!*p)return COH_OK;CohWrTexWords *c=*p;if(!output_ok(c,p,sizeof(*p)))return COH_INVALID;free(c);*p=NULL;return COH_OK;}
CohStatus coh_wr_texwords_report(const CohWrTexWords *c,CohWrTexWordsReport *out){if(!c||!out||(uintptr_t)out%_Alignof(CohWrTexWordsReport)||!output_ok(c,out,sizeof(*out)))return COH_INVALID;*out=c->report;return COH_OK;}
CohStatus coh_wr_texwords_record(const CohWrTexWords *c,uint32_t row,CohWrTexWordRecord *out){
 if(!c||!out||(uintptr_t)out%_Alignof(CohWrTexWordRecord)||!output_ok(c,out,sizeof(*out)))return COH_INVALID;
 if(row>=c->row_count)return COH_NOT_FOUND;
 Row r=c->rows[row];CohWrTexWordRecord v={{c->data+r.name,r.length},{c->data+r.offset,r.bytes},row,c->report.source_generation};*out=v;return COH_OK;
}
static uint32_t lookup(const CohWrTexWords *c,const char *key){for(uint32_t i=0;i<c->row_count;i++)if(!icmp(c->rows[i].key,key))return c->rows[i].owner;return UINT32_MAX;}
CohStatus coh_wr_texwords_find(const CohWrTexWords *c,const CohWrTexNamespace *ns,const char *name,int search,const CohWrTexWordQueryLimits *lim,CohWrTexWordSelection *out){
 if(!c||!name||!lim||!out||(uintptr_t)out%_Alignof(CohWrTexWordSelection)||!output_ok(c,out,sizeof(*out))||!apart(lim,sizeof(*lim),out,sizeof(*out))||(search!=0&&search!=1))return COH_INVALID;
 size_t n;if(!readable_name(name,128,&n)||!n||!apart(name,n+1,out,sizeof(*out)))return COH_INVALID;
 char key[128];memcpy(key,name,n+1);char *suffix=strchr(key,'#');int has_locale=suffix!=NULL,is_base=0;if(suffix){*suffix++=0;is_base=!icmp(suffix,"Base");}
 size_t stem=strlen(key);if(stem<3||stem>122||strpbrk(key,"./\\!")||strchr(key,'#'))return COH_UNSUPPORTED;
 uint32_t row=lookup(c,key),route=row==UINT32_MAX?0:COH_WR_TEXWORD_CURRENT_LOCALE;
 CohWrTexWordSelection v={0};v.source_ordinal=UINT32_MAX;v.source_generation=c->report.source_generation;v.layout_composition_unqualified=1;v.current_generation_unqualified=1;
 size_t total=lim->external_bytes;if(total<c->allocation||!add(&total,QUERY_RESERVE)||!add(&total,n+1+sizeof(*lim)+sizeof(v))||total>lim->aggregate_limit)return COH_LIMIT;
 if(row==UINT32_MAX&&(is_base||search)){
  memcpy(key+stem,"#Base",6);row=lookup(c,key);if(row!=UINT32_MAX)route=COH_WR_TEXWORD_BASE_EXPLICIT;
 } else if(row==UINT32_MAX&&!is_base&&!has_locale){
  if(!ns)return COH_STATE;
  CohWrTexNamespaceReport report;CohStatus status=coh_wr_tex_namespace_report(ns,&report);if(status!=COH_OK)return status;
  size_t minimum=c->allocation;if(!add(&minimum,report.aggregate_reserved_bytes)||lim->external_bytes<minimum)return COH_LIMIT;
  memcpy(key+stem,"#Base",6);memcpy(v.basic_query,key,stem+6);v.namespace_queries=1;
  CohWrTexNamespaceBasic basic;status=coh_wr_tex_namespace_find(ns,key,&basic);
  if(status==COH_NOT_FOUND){row=lookup(c,key);if(row!=UINT32_MAX)route=COH_WR_TEXWORD_BASE_WITHOUT_BASIC;}
  else if(status!=COH_OK)return status;
 }
 if(row==UINT32_MAX&&is_base&&c->verbose){row=lookup(c,"DUMMYLAYOUT");if(row!=UINT32_MAX)route=COH_WR_TEXWORD_DEBUG_DUMMY;}
 v.matched=row!=UINT32_MAX;v.source_ordinal=row;v.route=route;*out=v;return COH_OK;
}

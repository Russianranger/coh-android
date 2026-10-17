#include "coh_wr_texopt.h"
#include "coh_wr_texopt_types_internal.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <math.h>
#include <assert.h>
#define ARENA_BYTES 4096u
#define COUNT 14715u
#define FRAME_RESERVE 32768u
#define TOK_U8_X 1
#define TOK_INT_X 2
#define TOK_F32_X 3
#define TOK_STRING_X 4
#define TOK_CURRENTFILE_X 4
#define TOK_TIMESTAMP_X 2
#define TOK_FLAGS_X 2
#define TOK_STRUCT_X 5
#define TOK_FIXED_ARRAY 256
#define TOK_REDUNDANTNAME 512
#define TOK_STRUCTPARAM 1024
#define TOK_END 0
#define TOK_U8(s,m,d) TOK_U8_X,offsetof(s,m),d
#define TOK_INT(s,m,d) TOK_INT_X,offsetof(s,m),d
#define TOK_F32(s,m,d) TOK_F32_X,offsetof(s,m),d
#define TOK_FLAGS(s,m,d) TOK_FLAGS_X,offsetof(s,m),d
#define TOK_STRING(s,m,d) TOK_STRING_X,offsetof(s,m),d
#define TOK_CURRENTFILE(s,m) TOK_CURRENTFILE_X,offsetof(s,m),0
#define TOK_TIMESTAMP(s,m) TOK_TIMESTAMP_X,offsetof(s,m),0
#define TOK_VEC2(s,m) TOK_FIXED_ARRAY|TOK_F32_X,offsetof(s,m),2
#define TOK_VEC3(s,m) TOK_FIXED_ARRAY|TOK_F32_X,offsetof(s,m),3
#define TOK_EMBEDDEDSTRUCT(s,m,t) TOK_STRUCT_X,offsetof(s,m),0,t
#define TOK_NULLSTRUCT(t) TOK_STRUCT_X,0,0,t
/* Defaults and define-table pointers are not interpreted when reading persisted
 * complete fields. Original struct zero-initialization is retained. */
typedef struct Table{const char*name;int type;size_t offset;intptr_t param;const void*subtable;}TokenizerParseInfo;
static const int texblend_flags[]={0},tex_flags[]={0},model_flags[]={0},parse_texopt_scroll_type[]={0};
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#define TokenizerParseInfo static const TokenizerParseInfo
#include "coh_wr_texopt_tables_internal.inc"
#undef TokenizerParseInfo
#pragma GCC diagnostic pop
typedef struct{uint32_t offset,size,name;uint16_t length,pad;}Row;
struct CohWrTexOptCache{CohAssetLoader*loader;const CohAssetBlob*blob;CohWrTexOptCacheReport report;Row rows[COUNT],files[1585];uint32_t index[COUNT];};
struct CohWrTexOptRecord{TexOpt tex,parsed,duplicate_stub;const CohWrSurfaceStates*preparing_surface;CohStatus status;uint32_t generation,ordinal,owner,diagnostics;size_t used,aggregate;uint8_t cache_sha256[32];char arena[ARENA_BYTES];};
_Static_assert(offsetof(CohWrTexOptRecord,tex)==0,"owner-local source context");
_Static_assert(BLEND_NUM_BLEND_NAMES==COH_WR_TEXOPT_LAYERS,"source layer count");
typedef struct{CohBytes b;size_t pos,end;}Reader;
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int stop(CohCancel c){return c.poll&&c.poll(c.context);}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int take(Reader*r,size_t n,const uint8_t**p){if(n>r->end-r->pos)return 0;*p=r->b.data+r->pos;r->pos+=n;return 1;}
static int word(Reader*r,uint32_t*v){const uint8_t*p;if(!take(r,4,&p))return 0;*v=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;return 1;}
static int pascal(Reader*r,const uint8_t**p,uint32_t*n){const uint8_t*q;if(!take(r,2,&q))return 0;*n=(uint32_t)q[0]|(uint32_t)q[1]<<8;if(*n>=1024||!take(r,*n,p)||memchr(*p,0,*n))return 0;return take(r,(4-(*n+2)%4)%4,&q);}
static int equal(const uint8_t*p,uint32_t n,const char*s){return strlen(s)==n&&!memcmp(p,s,n);}
static char*copy(CohWrTexOptRecord*r,const uint8_t*s,size_t n){if(n+1>ARENA_BYTES-r->used){r->status=COH_LIMIT;return NULL;}char*out=r->arena+r->used;memcpy(out,s,n);out[n]=0;r->used+=n+1;return out;}
static CohStatus table(Reader*r,const TokenizerParseInfo*t,uint8_t*object,CohWrTexOptRecord*owner,unsigned depth){
 if(depth>4)return COH_LIMIT;
 for(unsigned i=0;t[i].type;i++){
  if(t[i].type&TOK_REDUNDANTNAME)continue;
  unsigned kind=(unsigned)t[i].type&255;size_t n=(t[i].type&TOK_FIXED_ARRAY)?(size_t)t[i].param:1;if(n>4)return COH_LIMIT;
  uint8_t*dest=object?object+t[i].offset:NULL;
  if(kind==TOK_STRUCT_X){uint32_t bytes;if(!word(r,&bytes)||bytes>r->end-r->pos)return COH_INVALID;Reader child={r->b,r->pos,r->pos+bytes};CohStatus s=table(&child,t[i].subtable,dest,owner,depth+1);if(s!=COH_OK)return s;if(child.pos!=child.end)return COH_INVALID;r->pos=child.end;}
  else if(kind==TOK_STRING_X){const uint8_t*p;uint32_t bytes;if(!pascal(r,&p,&bytes))return COH_INVALID;if(dest){char*str=bytes?copy(owner,p,bytes):NULL;if(owner->status!=COH_OK)return owner->status;memcpy(dest,&str,sizeof(str));}}
  else for(size_t j=0;j<n;j++){uint32_t v;if(!word(r,&v))return COH_INVALID;if(kind==TOK_F32_X){float f;memcpy(&f,&v,4);if(!isfinite(f))return COH_UNSUPPORTED;if(dest)memcpy(dest+j*4,&f,4);}else if(kind==TOK_U8_X){if(dest)dest[j]=(uint8_t)v;}else if(kind==TOK_INT_X){if(dest)memcpy(dest+j*4,&v,4);}else return COH_UNSUPPORTED;}
 }
 return COH_OK;
}
static int order(const CohWrTexOptCache*c,uint32_t a,uint32_t b){CohBytes bytes=coh_asset_bytes(c->blob);Row x=c->rows[a],y=c->rows[b];uint32_t n=x.length<y.length?x.length:y.length;for(uint32_t i=0;i<n;i++){int d=(int)fold(bytes.data[x.name+i])-(int)fold(bytes.data[y.name+i]);if(d)return d;}return (int)x.length-(int)y.length;}
static void sift(CohWrTexOptCache*c,uint32_t root,uint32_t n){for(;;){uint32_t child=root*2+1;if(child>=n)return;if(child+1<n&&order(c,c->index[child],c->index[child+1])<0)child++;if(order(c,c->index[root],c->index[child])>=0)return;uint32_t tmp=c->index[root];c->index[root]=c->index[child];c->index[child]=tmp;root=child;}}
static int spans(CohBytes b,Row a,Row z){uint32_t n=a.length<z.length?a.length:z.length;for(uint32_t k=0;k<n;k++){int d=(int)fold(b.data[a.name+k])-(int)fold(b.data[z.name+k]);if(d)return d;}return (int)a.length-(int)z.length;}
static int source_file(const CohWrTexOptCache*c,CohBytes b,Row key,uint32_t stamp){uint32_t lo=0,hi=1585;while(lo<hi){uint32_t mid=lo+(hi-lo)/2;int d=spans(b,key,c->files[mid]);if(d>0)lo=mid+1;else if(d<0)hi=mid;else return c->files[mid].size==stamp;}return 0;}
static int output_cache(const CohWrTexOptCache*c,const void*out,size_t n){CohBytes b=coh_asset_bytes(c->blob);return apart(c,sizeof(*c),out,n)&&apart(b.data,b.size,out,n);}
void coh_wr_texopt_cache_release(CohWrTexOptCache**p){if(p&&*p){CohWrTexOptCache*c=*p;coh_asset_release(c->loader,c->blob);free(c);*p=NULL;}}
CohStatus coh_wr_texopt_cache_open(CohAssetLoader*l,CohAssetId id,CohWrTexOptDigest digest,void*context,const CohWrTexOptLimits*lim,CohCancel cancel,CohWrTexOptCache**out){
 if(!l||!id.path||!id.generation||!digest||!lim||!out)return COH_INVALID;
 if(strcmp(id.path,"data/bin/tricks.bin"))return COH_UNSUPPORTED;
 if(!apart(lim,sizeof(*lim),out,sizeof(*out))||!apart(id.path,20,out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 size_t total=lim->external_bytes;if(!lim->loader_reservation||!add(&total,lim->loader_reservation)||!add(&total,sizeof(CohWrTexOptCache))||!add(&total,FRAME_RESERVE)||total>lim->aggregate_limit||sizeof(CohWrTexOptCache)>lim->owned_limit||coh_asset_stats(l).peak_allocated_bytes>lim->loader_reservation)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 CohWrTexOptCache*c=calloc(1,sizeof(*c));if(!c)return COH_LIMIT;c->loader=l;CohStatus status=coh_asset_acquire(l,id,cancel,&c->blob);if(status!=COH_OK)goto fail;
 if(coh_asset_stats(l).peak_allocated_bytes>lim->loader_reservation){status=COH_LIMIT;goto fail;}CohAssetId actual=coh_asset_identity(c->blob);CohBytes b=coh_asset_bytes(c->blob);if(!apart(b.data,b.size,out,sizeof(*out))||actual.generation!=id.generation||strcmp(actual.path,id.path)||b.size!=13537052){status=COH_INVALID;goto fail;}
 static const uint8_t expected[32]={0xcf,0x95,0x95,0xe5,0x4b,0xc6,0x5a,0x40,0xd2,0xdd,0xdc,0x3a,0x5a,0x13,0xc4,0x75,0xd7,0xc2,0xce,0x07,0xa9,0x64,0x20,0xe6,0x00,0x1b,0x0e,0x23,0x12,0x92,0x6b,0xc1};uint8_t hash[32];status=digest(context,b,hash);if(status!=COH_OK)goto fail;if(memcmp(hash,expected,32)){status=COH_INVALID;goto fail;}
 Reader r={b,8,b.size};uint32_t v,n;const uint8_t*p;if(memcmp(b.data,"CrypticS",8)||!word(&r,&v)||v!=0x5ba1b0e3u||!pascal(&r,&p,&n)||!equal(p,n,"Parse6")||!pascal(&r,&p,&n)||!equal(p,n,"Files1")||!word(&r,&v)||v>r.end-r.pos){status=COH_INVALID;goto fail;}
 Reader files={b,r.pos,r.pos+v};if(!word(&files,&n)||n!=1585){status=COH_INVALID;goto fail;}for(uint32_t i=0;i<n;i++){if(stop(cancel)){status=COH_CANCELLED;goto fail;}if(!pascal(&files,&p,&v)||!v||v>=260){status=COH_INVALID;goto fail;}for(uint32_t j=0;j<v;j++)if(p[j]<32||p[j]>126){status=COH_UNSUPPORTED;goto fail;}c->files[i]=(Row){0,0,(uint32_t)(p-b.data),(uint16_t)v,0};if(i&&spans(b,c->files[i-1],c->files[i])>=0){status=COH_INVALID;goto fail;}if(!word(&files,&v)){status=COH_INVALID;goto fail;}c->files[i].size=v;}if(files.pos!=files.end){status=COH_INVALID;goto fail;}r.pos=files.end;
 if(!word(&r,&v)||v!=r.end-r.pos||!word(&r,&n)||n!=COUNT){status=COH_INVALID;goto fail;}
 for(uint32_t i=0;i<COUNT;i++){
  if(stop(cancel)){status=COH_CANCELLED;goto fail;}if(!word(&r,&v)||v>r.end-r.pos){status=COH_INVALID;goto fail;}Reader row={b,r.pos,r.pos+v},name=row;if(!pascal(&name,&p,&n)||!n||n>=260){status=COH_INVALID;goto fail;}c->rows[i]=(Row){(uint32_t)r.pos,v,(uint32_t)(p-b.data),(uint16_t)n,0};const uint8_t*file,*internal;uint32_t file_n,internal_n,stamp;if(!pascal(&name,&file,&file_n)||file_n>=260||!word(&name,&stamp)||!pascal(&name,&internal,&internal_n)||internal_n!=n||memcmp(p,internal,n)||!source_file(c,b,(Row){0,0,(uint32_t)(file-b.data),(uint16_t)file_n,0},stamp)){status=COH_INVALID;goto fail;}status=table(&row,parse_tex_opt,NULL,NULL,0);if(status!=COH_OK)goto fail;if(row.pos!=row.end){status=COH_INVALID;goto fail;}r.pos=row.end;c->index[i]=i;
 }
 /* Trick records remain SOURCE-opaque, exactly bounded; no Trick/AutoLOD semantics. */
 if(!word(&r,&n)||n!=3644){status=COH_INVALID;goto fail;}for(uint32_t i=0;i<n;i++){if(stop(cancel)){status=COH_CANCELLED;goto fail;}if(!word(&r,&v)||v>r.end-r.pos){status=COH_INVALID;goto fail;}r.pos+=v;}if(r.pos!=r.end){status=COH_INVALID;goto fail;}
 for(uint32_t k=COUNT/2;k>0;k--)sift(c,k-1,COUNT);
 for(uint32_t k=COUNT;k>1;k--){if(stop(cancel)){status=COH_CANCELLED;goto fail;}uint32_t tmp=c->index[0];c->index[0]=c->index[k-1];c->index[k-1]=tmp;sift(c,0,k-1);}
 memset(&c->report,0,sizeof(c->report));c->report.historical_input_generation=id.generation;c->report.count=COUNT;c->report.owned_bytes=sizeof(*c);c->report.loader_reservation=lim->loader_reservation;c->report.aggregate_reserved_bytes=total;c->report.observed_schema_crc=0x5ba1b0e3u;memcpy(c->report.cache_sha256,expected,32);if(stop(cancel)){status=COH_CANCELLED;goto fail;}*out=c;return COH_OK;
fail:if(c->blob)coh_asset_release(l,c->blob);free(c);return status;
}
CohStatus coh_wr_texopt_cache_report(const CohWrTexOptCache*c,CohWrTexOptCacheReport*out){if(!c||!out||!output_cache(c,out,sizeof(*out)))return COH_INVALID;*out=c->report;return COH_OK;}
CohStatus coh_wr_texopt_cache_find(const CohWrTexOptCache*c,const char*key,uint32_t*out){
 if(!c||!key||!out||!output_cache(c,out,sizeof(*out)))return COH_INVALID;
 size_t n;for(n=0;n<260;n++){unsigned x=(unsigned char)key[n];if(!x)break;if(x<32||x>126)return COH_UNSUPPORTED;}if(!n)return COH_INVALID;if(n==260)return COH_LIMIT;if(!apart(key,n+1,out,sizeof(*out)))return COH_INVALID;
 CohBytes b=coh_asset_bytes(c->blob);uint32_t lo=0,hi=COUNT;
 while(lo<hi){uint32_t mid=lo+(hi-lo)/2;Row row=c->rows[c->index[mid]];size_t m=n<row.length?n:row.length;int d=0;for(size_t j=0;j<m&&!d;j++)d=(int)fold((unsigned char)key[j])-(int)fold(b.data[row.name+j]);if(!d)d=(int)n-(int)row.length;if(d>0)lo=mid+1;else if(d<0)hi=mid;else{uint32_t winner=c->index[mid];for(uint32_t j=mid;j>0&&!order(c,c->index[j-1],c->index[mid]);j--)if(c->index[j-1]>winner)winner=c->index[j-1];for(uint32_t j=mid+1;j<COUNT&&!order(c,c->index[j],c->index[mid]);j++)if(c->index[j]>winner)winner=c->index[j];*out=winner;return COH_OK;}}
 return COH_NOT_FOUND;
}
/* Original CLIENT postprocessing, private owner-local adaptation. No shared
 * globals or external table mutation; highest ordinal ownership is precomputed. */
static CohWrTexOptRecord*record_of(TexOpt*t){return (CohWrTexOptRecord*)t;}
static char*duplicate(TexOpt*t,const char*s){return copy(record_of(t),(const uint8_t*)s,strlen(s));}
static int icmp(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=(int)fold((unsigned char)*a)-(int)fold((unsigned char)*b);if(d)return d;}return (unsigned char)*a-(unsigned char)*b;}
static int nicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=(int)fold((unsigned char)a[i])-(int)fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static const char*strstriConst(const char*s,const char*k){for(;*s;s++)if(!nicmp(s,k,strlen(k)))return s;return NULL;}
static int surface_for(TexOpt*t,const char*name){CohWrTexOptRecord*r=record_of(t);uint32_t value;CohStatus s=coh_wr_surface_lookup(r->preparing_surface,name,&value);if(s==COH_OK)return (int)value;if(s!=COH_NOT_FOUND)r->status=s;return -1;}
static int wr_starts(const char*,const char*);
static int wr_ends(const char*,const char*);
static TexOptFlags wr_name_flags(const char*,TexOptFlags);
#define strStartsWith wr_starts
#define strEndsWith wr_ends
#define texOptFlagsFromName wr_name_flags
#define stricmp icmp
#define strnicmp nicmp
#define MAX_PATH 260
#define SERVER 0
#define CLIENT 1
#define seqGetStateNumberFromName(name) surface_for(tex,name)
#define StructFreeStringConst(s) ((void)(s))
#define isSharedMemory(s) ((void)(s),false)
#define onlyfulldebugdevassert(s) assert(s)
#define ParserAllocString(s) duplicate(tex,s)
#define allocAddSharedString(s) duplicate(tex,s)
#define stashAddPointer(table,key,value,overwrite) (record_of(tex)->owner==record_of(tex)->ordinal)
#define stashFindPointer(table,key,out) do{*(out)=&record_of(tex)->duplicate_stub;}while(0)
#define ErrorFilenamef(...) ((void)record_of(tex)->diagnostics++)
#define Errorf(...) ((void)record_of(tex)->diagnostics++)
#define ErrorFilenameDup(a,b,c,d) ((void)(a),(void)(b),(void)(c),(void)(d),(void)record_of(tex)->diagnostics++)
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
#define copyVec3(src,dst) (((dst)[0])=((src)[0]),((dst)[1])=((src)[1]),((dst)[2])=((src)[2]))
#define scaleVec3(v,s,r) ((r)[0]=(v)[0]*(s),(r)[1]=(v)[1]*(s),(r)[2]=(v)[2]*(s))
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-value"
#include "coh_wr_texopt_post_source.inc"
#pragma GCC diagnostic pop
#undef SERVER
#undef CLIENT
void coh_wr_texopt_record_release(CohWrTexOptRecord**p){if(p&&*p){free(*p);*p=NULL;}}
CohStatus coh_wr_texopt_record_create(const CohWrTexOptCache*c,uint32_t ordinal,const CohWrSurfaceStates*surface,const CohWrTexOptLimits*lim,CohCancel cancel,CohWrTexOptRecord**out){
 if(!c||!surface||!lim||!out||!output_cache(c,out,sizeof(*out))||!apart(lim,sizeof(*lim),out,sizeof(*out)))return COH_INVALID;
 CohWrSurfaceReport sr;CohStatus status=coh_wr_surface_report(surface,&sr);if(status!=COH_OK)return status;
 if(!apart(surface,sr.owned_bytes,out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 if(ordinal>=COUNT)return COH_NOT_FOUND;
 if(sr.historical_input_generation!=c->report.historical_input_generation)return COH_STATE;
 size_t minimum=c->report.owned_bytes;if(!add(&minimum,c->report.loader_reservation)||!add(&minimum,sr.owned_bytes)||!add(&minimum,16384))return COH_LIMIT;
 size_t total=lim->external_bytes;if(lim->external_bytes<minimum||!add(&total,sizeof(CohWrTexOptRecord))||!add(&total,FRAME_RESERVE)||total>lim->aggregate_limit||sizeof(CohWrTexOptRecord)>lim->owned_limit)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 CohWrTexOptRecord*r=calloc(1,sizeof(*r));if(!r)return COH_LIMIT;r->generation=c->report.historical_input_generation;r->ordinal=ordinal;r->preparing_surface=surface;r->aggregate=total;memcpy(r->cache_sha256,c->report.cache_sha256,32);
 CohBytes b=coh_asset_bytes(c->blob);Row source=c->rows[ordinal];Reader input={b,source.offset,source.offset+source.size};status=table(&input,parse_tex_opt,(uint8_t*)&r->tex,r,0);if(status!=COH_OK)goto fail;if(input.pos!=input.end||!r->tex.name){status=COH_INVALID;goto fail;}
 /* Original CRT string helpers/MAX_PATH are qualified only for bounded ASCII.
  * The raw high-byte record remains in cache; no substitute definition is made. */
 for(size_t i=0;i<r->used;i++)if(r->arena[i]&&((unsigned char)r->arena[i]<32||(unsigned char)r->arena[i]>126)){status=COH_UNSUPPORTED;goto fail;}
 status=coh_wr_texopt_cache_find(c,r->tex.name,&r->owner);if(status!=COH_OK)goto fail;
 if(r->owner!=ordinal){Row winner=c->rows[r->owner];Reader prefix={b,winner.offset,winner.offset+winner.size};const uint8_t*p;uint32_t n;if(!pascal(&prefix,&p,&n)||!pascal(&prefix,&p,&n)){status=COH_INVALID;goto fail;}r->duplicate_stub.file_name=copy(r,p,n);if(r->status!=COH_OK){status=r->status;goto fail;}}
 r->parsed=r->tex;
 if(stop(cancel)){status=COH_CANCELLED;goto fail;}setupTexOpt(&r->tex,false);if(r->status!=COH_OK){status=r->status;goto fail;}r->preparing_surface=NULL;if(stop(cancel)){status=COH_CANCELLED;goto fail;}*out=r;return COH_OK;
fail:free(r);return status;
}
static CohStatus record_view(const CohWrTexOptRecord*r,CohWrTexOptView*out,int source){
 if(!r||!out||!apart(r,sizeof(*r),out,sizeof(*out)))return COH_INVALID;
 const TexOpt*t=source?&r->parsed:&r->tex;const ScrollsScales*s=&t->scrollsScales;CohWrTexOptView v;memset(&v,0,sizeof(v));memcpy(v.cache_sha256,r->cache_sha256,32);v.owned_bytes=sizeof(*r);v.aggregate_reserved_bytes=r->aggregate;v.historical_input_generation=r->generation;v.source_ordinal=r->ordinal;v.table_owner_ordinal=r->owner;v.is_table_owner=r->owner==r->ordinal;v.unresolved_client_semantics=1;v.original_CLIENT_postprocessed=source?0:1;v.diagnostics=r->diagnostics;v.name=t->name;v.source_file=t->file_name;v.table_owner_source_file=r->owner==r->ordinal?t->file_name:r->duplicate_stub.file_name;v.surface_name=t->surface_name;v.df_name=t->df_name;v.flags=(uint32_t)t->flags;v.model_flags=(uint32_t)t->model_flags;v.blend_mode=(uint32_t)t->blend_mode;v.surface=(uint32_t)t->surface;v.source_age=t->fileAge;memcpy(v.fade,t->texopt_fade,sizeof(v.fade));v.gloss=t->gloss;
 for(unsigned i=0;i<COH_WR_TEXOPT_LAYERS;i++){v.layers[i].name=t->blend_names[i];memcpy(v.layers[i].scale,s->texopt_scale[i],sizeof(v.layers[i].scale));memcpy(v.layers[i].scroll,s->texopt_scroll[i],sizeof(v.layers[i].scroll));v.layers[i].scroll_type=(uint32_t)s->texopt_scrollType[i];v.layers[i].swappable=t->swappable[i];}
 v.alpha_mask=s->alphaMask;v.has_rgb34=s->hasRgb34;v.multiply1_reflect=s->multiply1Reflect;v.multiply2_reflect=s->multiply2Reflect;v.base_add_glow=s->baseAddGlow;v.min_add_glow=s->minAddGlow;v.max_add_glow=s->maxAddGlow;v.add_glow_mat2=s->addGlowMat2;v.tint_glow=s->tintGlow;v.tint_reflection=s->tintReflection;v.desaturate_reflection=s->desaturateReflection;v.alpha_water=s->alphaWater;memcpy(v.rgba3,s->rgba3,4);memcpy(v.rgba4,s->rgba4,4);memcpy(v.specular_rgba1,s->specularRgba1,4);memcpy(v.specular_rgba2,s->specularRgba2,4);v.parsed_specular_exponent1=t->specularExponent1_parser;v.parsed_specular_exponent2=t->specularExponent2_parser;v.specular_exponent1=s->specularExponent1;v.specular_exponent2=s->specularExponent2;v.reflectivity=s->reflectivity;v.reflectivity_base=s->reflectivityBase;v.reflectivity_scale=s->reflectivityScale;v.reflectivity_power=s->reflectivityPower;v.mask_weight=s->maskWeight;memcpy(v.diffuse_scale,s->diffuseScale,sizeof(v.diffuse_scale));memcpy(v.ambient_scale,s->ambientScale,sizeof(v.ambient_scale));memcpy(v.diffuse_trick,s->diffuseScaleTrick,sizeof(v.diffuse_trick));memcpy(v.ambient_trick,s->ambientScaleTrick,sizeof(v.ambient_trick));memcpy(v.ambient_min,s->ambientMin,sizeof(v.ambient_min));v.fallback.base=t->fallback.base_name;v.fallback.blend=t->fallback.blend_name;v.fallback.bumpmap=t->fallback.bumpmap;v.fallback.blend_mode=(uint32_t)t->fallback.blend_mode;v.fallback.use_fallback=t->fallback.useFallback;memcpy(v.fallback.scale,t->fallback.scaleST,sizeof(v.fallback.scale));memcpy(v.fallback.diffuse,t->fallback.diffuseScaleTrick,sizeof(v.fallback.diffuse));memcpy(v.fallback.ambient,t->fallback.ambientScaleTrick,sizeof(v.fallback.ambient));memcpy(v.fallback.ambient_min,t->fallback.ambientMin,sizeof(v.fallback.ambient_min));*out=v;return COH_OK;
}

CohStatus coh_wr_texopt_record_view(const CohWrTexOptRecord*r,CohWrTexOptView*out){return record_view(r,out,0);}
CohStatus coh_wr_texopt_record_source_view(const CohWrTexOptRecord*r,CohWrTexOptView*out){return record_view(r,out,1);}

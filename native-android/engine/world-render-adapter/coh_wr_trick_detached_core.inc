/* Mechanical frozen-reader slices; exact transformation checked by qualifier. */
#define COUNT 3644u
#define RESERVE 32768u
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
#define TOK_EARRAY 2048
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
#define TOK_STRUCT(s,m,t) TOK_STRUCT_X|TOK_EARRAY,offsetof(s,m),0,t
#define TOK_NULLSTRUCT(t) TOK_STRUCT_X,0,0,t
/* Defaults and define-table pointers are not interpreted when reading persisted
 * complete fields. Original struct zero-initialization is retained. */
typedef struct Table{const char*name;int type;size_t offset;intptr_t param;const void*subtable;}TokenizerParseInfo;
static const int trick_flags[]={0},model_flags[]={0},group_flags[]={0},stanim_flags[]={0},autolod_flags[]={0};
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#define TokenizerParseInfo static const TokenizerParseInfo
#include "coh_wr_trick_tables_internal.inc"
#undef TokenizerParseInfo
#pragma GCC diagnostic pop

typedef struct{uint32_t offset,size,name,name_length,file,file_length,age,st_offset,st_count,lod_offset,lod_count,winner;}Row;

typedef struct{CohBytes bytes;size_t pos,end;}Reader;
typedef struct{CohBytes strings[3];uint32_t string_count,st_offset,st_count,lod_offset,lod_count,children;}Meta;
_Static_assert(4*sizeof(TrickInfo)+4*sizeof(Meta)+4096<16384,"bounded preparation/view control frames");

#include "coh_wr_trick_detached_storage_internal.h"

static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}

static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}

static int stop(CohCancel c){return c.poll&&c.poll(c.context);}

static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}

static int compare(CohBytes a,CohBytes b){size_t n=a.size<b.size?a.size:b.size;for(size_t i=0;i<n;i++){int d=(int)fold(a.data[i])-(int)fold(b.data[i]);if(d)return d;}return a.size>b.size?1:a.size<b.size?-1:0;}

static int take(Reader*r,size_t n,const uint8_t**out){if(r->pos>r->end||n>r->end-r->pos)return 0;*out=r->bytes.data+r->pos;r->pos+=n;return 1;}

static int word(Reader*r,uint32_t*out){const uint8_t*p;if(!take(r,4,&p))return 0;*out=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;return 1;}

static int string(Reader*r,CohBytes*out){const uint8_t*p,*q;if(!take(r,2,&p))return 0;size_t n=(size_t)p[0]|(size_t)p[1]<<8;if(n>=1024||!take(r,n,&q)||memchr(q,0,n)||!take(r,(4-(n+2)%4)%4,&p))return 0;*out=(CohBytes){n?q:NULL,n};return 1;}

static int ascii(CohBytes b){if(!b.size)return 0;for(size_t i=0;i<b.size;i++)if(b.data[i]<32||b.data[i]>126)return 0;return 1;}

static CohStatus table(Reader*r,const TokenizerParseInfo*t,void*object,Meta*meta,unsigned depth){
 if(depth>1)return COH_LIMIT;
 for(unsigned i=0;t[i].type;i++){
  if(t[i].type&TOK_REDUNDANTNAME)continue;
  unsigned kind=(unsigned)t[i].type&255;size_t n=(t[i].type&TOK_FIXED_ARRAY)?(size_t)t[i].param:1;if(n>4)return COH_LIMIT;uint8_t*dest=object?(uint8_t*)object+t[i].offset:NULL;
  if(t[i].type&TOK_EARRAY){uint32_t count;size_t start=r->pos;if(depth||kind!=TOK_STRUCT_X)return COH_UNSUPPORTED;if(!word(r,&count))return COH_INVALID;if(count>256||meta->children>512-count)return COH_LIMIT;meta->children+=count;if(t[i].subtable==parse_st_anim){meta->st_offset=(uint32_t)start;meta->st_count=count;}else if(t[i].subtable==parse_auto_lod){meta->lod_offset=(uint32_t)start;meta->lod_count=count;}else return COH_UNSUPPORTED;
   for(uint32_t j=0;j<count;j++){uint32_t bytes;if(!word(r,&bytes)||bytes>r->end-r->pos)return COH_INVALID;Reader child={r->bytes,r->pos,r->pos+bytes};Meta cm;memset(&cm,0,sizeof(cm));CohStatus s=table(&child,t[i].subtable,NULL,&cm,depth+1);if(s!=COH_OK)return s;if(child.pos!=child.end)return COH_INVALID;r->pos=child.end;}
  }else if(kind==TOK_STRING_X){CohBytes b;if(!string(r,&b)||meta->string_count>=3)return COH_INVALID;meta->strings[meta->string_count++]=b;/* Original indirect empty string->NULL; public byte spans retain nonempty bytes. Runtime pointers remain unresolved. */}
  else for(size_t j=0;j<n;j++){uint32_t value;if(!word(r,&value))return COH_INVALID;if(kind==TOK_F32_X){float f;memcpy(&f,&value,4);if(!isfinite(f))return COH_UNSUPPORTED;if(dest)memcpy(dest+j*4,&f,4);}else if(kind==TOK_U8_X){if(dest)dest[j]=(uint8_t)value;}else if(kind==TOK_INT_X){if(dest)memcpy(dest+j*4,&value,4);}else return COH_UNSUPPORTED;}
 }
 return COH_OK;
}

static CohBytes name(const CohWrTrickDetached*c,uint32_t row){CohBytes b=c->bytes;return(CohBytes){b.data+c->rows[row].name,c->rows[row].name_length};}

static int order(const CohWrTrickDetached*c,uint32_t a,uint32_t b){return compare(name(c,a),name(c,b));}

static void sift(CohWrTrickDetached*c,uint32_t root,uint32_t n){for(;;){uint32_t child=root*2+1;if(child>=n)return;if(child+1<n&&order(c,c->index[child],c->index[child+1])<0)child++;if(order(c,c->index[root],c->index[child])>=0)return;uint32_t x=c->index[root];c->index[root]=c->index[child];c->index[child]=x;root=child;}}

static uint32_t winner(const CohWrTrickDetached*c,CohBytes key){uint32_t lo=0,hi=COUNT;while(lo<hi){uint32_t mid=lo+(hi-lo)/2;int d=compare(key,name(c,c->index[mid]));if(d<0)hi=mid;else if(d>0)lo=mid+1;else{uint32_t best=c->index[mid];return c->rows[best].winner;}}return UINT32_MAX;}

static int output(const CohWrTrickDetached*c,const void*out,size_t n){CohBytes b=c->bytes;return apart(c,sizeof(*c),out,n)&&apart(b.data,b.size,out,n);}

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic ignored "-Wunused-parameter"
#include "coh_wr_trick_post_source.inc"
#pragma GCC diagnostic pop

static CohStatus view(const CohWrTrickDetached*c,uint32_t ordinal,CohWrTrickView*out,int projected){
 if(!c||!out||!output(c,out,sizeof(*out)))return COH_INVALID;
 if(ordinal>=COUNT)return COH_NOT_FOUND;
 CohBytes b=c->bytes;Row row=c->rows[ordinal];Reader r={b,row.offset,row.offset+row.size};TrickInfo t;memset(&t,0,sizeof(t));Meta m;memset(&m,0,sizeof(m));CohStatus status=table(&r,parse_trick,&t,&m,0);if(status!=COH_OK)return status;if(r.pos!=r.end)return COH_INVALID;if(projected){source_numeric_prefix(&t,false);source_group_projection(&t);}CohWrTrickView v;memset(&v,0,sizeof(v));v.name=m.strings[0];v.source_file=m.strings[1];v.ordinal=ordinal;v.table_owner_ordinal=row.winner;v.is_table_owner=v.table_owner_ordinal==ordinal;v.source_age=t.fileAge;v.historical_input_generation=c->report.historical_input_generation;memcpy(v.cache_sha256,c->report.cache_sha256,32);v.lod_near=t.lod_near;v.lod_far=t.lod_far;v.lod_nearfade=t.lod_nearfade;v.lod_farfade=t.lod_farfade;v.lod_scale=t.lod_scale;v.shadow_dist=t.shadow_dist;v.alpha_ref=t.alpha_ref;v.alpha_ref_parser=t.alpha_ref_parser;v.tex_bias=t.tex_bias;memcpy(v.nightglow,t.nightglow_times,8);memcpy(v.sway,t.sway,8);memcpy(v.sway_random,t.sway_random,8);memcpy(v.sway_pitch,t.sway_pitch,8);memcpy(v.sway_roll,t.sway_roll,8);memcpy(v.scroll,t.texScrollAmt,sizeof(v.scroll));v.tighten_up=t.tighten_up;v.sort_bias=t.alpha_sort_mod;v.water_skew=t.water_reflection_skew;v.water_strength=t.water_reflection_strength;v.flags1=(uint32_t)t.tnode.flags1;v.flags2=(uint32_t)t.tnode.flags2;v.model_flags=(uint32_t)t.model_flags;v.group_flags=t.group_flags;v.stanim_count=m.st_count;v.autolod_count=m.lod_count;memcpy(v.rgba,t.tnode.trick_rgba,4);memcpy(v.rgba2,t.tnode.trick_rgba2,4);v.numeric_group_projection=(uint32_t)projected;v.animation_binding_unresolved=m.st_count!=0;v.unresolved_client_semantics=1;*out=v;return COH_OK;
}

CohStatus coh_wr_trick_detached_view(const CohWrTrickDetached*c,uint32_t row,CohWrTrickView*out){return view(c,row,out,0);}

CohStatus coh_wr_trick_detached_numeric_projection(const CohWrTrickDetached*c,uint32_t row,CohWrTrickView*out){return view(c,row,out,1);}

CohStatus coh_wr_trick_detached_find(const CohWrTrickDetached*c,const char*key,uint32_t*out){if(!c||!key||!out||!output(c,out,sizeof(*out)))return COH_INVALID;size_t n;for(n=0;n<260;n++){unsigned x=(unsigned char)key[n];if(!x)break;if(x<32||x>126)return COH_UNSUPPORTED;}if(!n)return COH_INVALID;if(n==260)return COH_LIMIT;if(!apart(key,n+1,out,sizeof(*out)))return COH_INVALID;uint32_t found=winner(c,(CohBytes){(const uint8_t*)key,n});if(found==UINT32_MAX)return COH_NOT_FOUND;*out=found;return COH_OK;}

static CohStatus child(const CohWrTrickDetached*c,uint32_t ordinal,uint32_t index,int lod,void*value,Meta*meta){if(ordinal>=COUNT)return COH_NOT_FOUND;Row row=c->rows[ordinal];uint32_t count=lod?row.lod_count:row.st_count;if(index>=count)return COH_NOT_FOUND;
 CohBytes b=c->bytes;Reader r={b,(lod?row.lod_offset:row.st_offset)+4,row.offset+row.size};for(uint32_t i=0;i<=index;i++){uint32_t bytes;if(!word(&r,&bytes)||bytes>r.end-r.pos)return COH_INVALID;if(i==index){Reader selected={b,r.pos,r.pos+bytes};CohStatus s=table(&selected,lod?parse_auto_lod:parse_st_anim,value,meta,1);if(s==COH_OK&&selected.pos!=selected.end)return COH_INVALID;return s;}r.pos+=bytes;}return COH_NOT_FOUND;}

CohStatus coh_wr_trick_detached_stanim(const CohWrTrickDetached*c,uint32_t row,uint32_t index,CohWrTrickStAnim*out){if(!c||!out||!output(c,out,sizeof(*out)))return COH_INVALID;StAnim a;memset(&a,0,sizeof(a));Meta m;memset(&m,0,sizeof(m));CohStatus s=child(c,row,index,0,&a,&m);if(s!=COH_OK)return s;CohWrTrickStAnim v={a.speed_scale,a.st_scale,m.strings[0],(uint32_t)a.flags,1};*out=v;return COH_OK;}

CohStatus coh_wr_trick_detached_autolod(const CohWrTrickDetached*c,uint32_t row,uint32_t index,CohWrTrickAutoLOD*out){if(!c||!out||!output(c,out,sizeof(*out)))return COH_INVALID;AutoLOD a;memset(&a,0,sizeof(a));Meta m;memset(&m,0,sizeof(m));CohStatus s=child(c,row,index,1,&a,&m);if(s!=COH_OK)return s;CohWrTrickAutoLOD v={a.max_error,a.lod_near,a.lod_far,a.lod_nearfade,a.lod_farfade,(uint32_t)a.flags,a.modelname_specified,m.strings[0],{0},1};*out=v;return COH_OK;}

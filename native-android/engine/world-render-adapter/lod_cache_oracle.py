"""Original typed LOD reader and initial dictionary precedence under path observers."""
from pathlib import Path

def create(root,extract):
 from texopt_setup_oracle import create as typed_create
 root=Path(root);source=(root/'upstream/ouroboros/Common/seq/AutoLOD.c').read_text();header=(root/'upstream/ouroboros/Common/seq/AutoLOD.h').read_text()
 def decl(start,end):p=header.index(start);return header[p:header.index(end,p)+len(end)]
 code=typed_create(root,extract)
 code=code.replace('arrays[2];','arrays[3];').replace('#define TOKARRAY_INFO(t) arrays[!!((t)&TOK_FIXED_ARRAY)]','#define TOKARRAY_INFO(t) arrays[((t)&TOK_EARRAY)?2:!!((t)&TOK_FIXED_ARRAY)]')
 insert=decl('typedef struct AutoLOD\n','} AutoLOD;')+'\n'+decl('typedef struct ModelLODInfo\n','} ModelLODInfo;')+'\ntypedef struct {ModelLODInfo**infos;} LODInfos;\n'
 insert+='typedef struct TrickInfo TrickInfo;\n#define TOK_FUNCTIONCALL_X 6\n#define TOK_EARRAY 2048\n#define TOK_STRUCT(s,m,t) TOK_STRUCT_X|TOK_EARRAY,offsetof(s,m),sizeof(**((s*)0)->m),t\n#define TOK_BOOL(s,m,d) TOK_U8_X,offsetof(s,m),d\nstatic int autolod_flags[]={0};\n'
 for name in ['parse_auto_lod','parse_model_lodinfo','parse_lods']:
  p=source.index('TokenizerParseInfo '+name+'[]');insert+=source[p:source.index('\n};',p)+3]+'\n'
 code=code.replace('typedef int(*ReadBin)',insert+'\ntypedef int(*ReadBin)')
 before='static void*TokenStoreAlloc(ParseTable*t,int c,void*s,int i,intptr_t p,void*a,void*b){(void)i;(void)p;(void)a;(void)b;return(char*)s+t[c].storeoffset;}'
 after='''static void TokenStoreSetCapacity(ParseTable*t,int c,void*s,int n){assert(n>0&&n<=5000);void***slot=(void***)((char*)s+t[c].storeoffset);assert(!*slot);*slot=calloc((size_t)n+1,sizeof(void*));assert(*slot);}
static void*TokenStoreAlloc(ParseTable*t,int c,void*s,int i,intptr_t p,void*a,void*b){(void)a;(void)b;if(t[c].type&TOK_EARRAY){void***slot=(void***)((char*)s+t[c].storeoffset);assert(*slot&&!(*slot)[i]);(*slot)[i]=calloc(1,(size_t)p);assert((*slot)[i]);return(*slot)[i];}return(char*)s+t[c].storeoffset;}
'''
 if code.count(before)!=1:raise ValueError('typed storage adapter drift')
 code=code.replace(before,after)
 reader=(root/'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c').read_text()
 code+='\n'+extract(reader,'int earray_readbin(')
 code+=r'''
#include "coh_wr_lod_cache.h"
int seqGetStateNumberFromName(const char*name){(void)name;abort();}
static LODInfos all_lodinfos;
static unsigned lod_entries,lod_duplicates,object_library_calls;
static ModelLODInfo*last_lod_candidate;
static ModelLODInfo*lod_values[5000];static char lod_keys[5000][260];
static int lod_hash;
static CohWrLodWritablePath original_resolver;static void*original_context;
static int lod_add(const char*key,ModelLODInfo*row){for(unsigned i=0;i<lod_entries;i++)if(!stricmp(lod_keys[i],key)){lod_duplicates++;return 0;}assert(lod_entries<5000&&strlen(key)<260);strcpy(lod_keys[lod_entries],key);lod_values[lod_entries++]=row;return 1;}
static int lod_find(const char*key,ModelLODInfo**out){*out=NULL;for(unsigned i=0;i<lod_entries;i++)if(!stricmp(lod_keys[i],key)){*out=lod_values[i];last_lod_candidate=*out;return 1;}return 0;}
static int fileLocateWrite(const char*path,char*out){return original_resolver(original_context,path,out)==COH_OK;}
static unsigned observed_count(void*const*array){unsigned n=0;if(array)while(array[n]){n++;assert(n<=5000);}return n;}
static char*objectLibraryPathFromObj(const char*name){assert(name&&*name);object_library_calls++;return NULL;}
#undef stashAddPointer
#undef stashFindPointer
#undef Errorf
#define stashAddPointer(table,key,value,overwrite) lod_add(key,value)
#define stashFindPointer(table,key,out) lod_find(key,out)
#define Errorf(...) ((void)0)
#define errorLogFileHasError(path) ((void)(path))
#define StashDeepCopyKeys 1
#define stashTableCreateWithStringKeys(size,flags) 1
#define ParserFreeString(s) free(s)
#define eaSize(array) ((int)observed_count((void*const*)*(array)))
#define strstri(s,k) ((char*)strstriConst(s,k))
'''
 code+='\n'+extract(source,'static void fillInLODFilenames(')+'\n'+extract(source,'void lodinfoLoadPostProcess(')+'\n'+extract(source,'char *getLODFileName(')
 prefix=extract(source,'ModelLODInfo *lodinfoFromObjectName(')
 prefix=prefix[:prefix.index('    if (lod_info && lod_info->removed)')]
 prefix=prefix.replace('lodinfoFromObjectName(', 'source_precedence(',1)+'    return NULL;\n}\n'
 code+=prefix+r'''
void original_lod_initialize(const unsigned char*body,size_t n){arrays[0].readbin=nonarray_readbin;arrays[1].readbin=fixedarray_readbin;arrays[2].readbin=earray_readbin;types[1].readbin=u8_readbin;types[2].readbin=int_readbin;types[3].readbin=float_readbin;types[4].readbin=string_readbin;types[5].readbin=struct_readbin;Buffer b={(unsigned char*)body,n,28};U32 files;assert(SimpleBufReadU32(&files,&b));SimpleBufSeek(&b,files,SEEK_CUR);int sum=0;assert(ParserReadBinaryTable(&b,parse_lods,&all_lodinfos,&sum)&&b.pos==n&&observed_count((void*const*)all_lodinfos.infos)==4976);}
const ModelLODInfo*original_lod_row(unsigned i){assert(i<4976);return all_lodinfos.infos[i];}
void original_lod_postprocess(CohWrLodWritablePath resolve,void*context){original_resolver=resolve;original_context=context;lod_entries=lod_duplicates=object_library_calls=0;lodinfoLoadPostProcess();}
unsigned original_lod_duplicates(void){return lod_duplicates;}
unsigned original_lod_library_calls(void){return object_library_calls;}
unsigned original_lod_lookup(const char*geo,const char*model){char name[260];assert(strlen(model)<260);strcpy(name,model);ModelLODInfo*row=source_precedence(NULL,name,(char*)geo,1,0,1,NULL);if(!row)return UINT32_MAX;for(unsigned i=0;i<4976;i++)if(all_lodinfos.infos[i]==row)return i;abort();}
unsigned original_lod_decision(const char*geo,const char*model,unsigned*out){char name[260];assert(strlen(model)<260);strcpy(name,model);last_lod_candidate=NULL;ModelLODInfo*row=source_precedence(NULL,name,(char*)geo,1,0,1,NULL);ModelLODInfo*chosen=row?row:last_lod_candidate;*out=UINT32_MAX;if(!chosen)return 0;for(unsigned i=0;i<4976;i++)if(all_lodinfos.infos[i]==chosen){*out=i;return row?1:2;}abort();}
const char*original_lod_filename(const char*geo){return getLODFileName(geo);}
static void clear_lod(ModelLODInfo*r){free(r->modelname);free(r->parsed_filename);if(r->lods){for(unsigned j=0;r->lods[j];j++){free(r->lods[j]->lod_modelname);free(r->lods[j]->lod_filename);free(r->lods[j]);}free(r->lods);}free(r);}
void original_lod_destroy(void){for(unsigned i=0;i<4976;i++)clear_lod(all_lodinfos.infos[i]);free(all_lodinfos.infos);all_lodinfos.infos=NULL;}
'''
 return code

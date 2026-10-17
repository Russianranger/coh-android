"""Original source scene/locale prefixes with UNKNOWN longjmp, not white invention."""
from pathlib import Path

def create(root,extract,basic_create,patch):
 root=Path(root);tex=(root/'upstream/ouroboros/Game/src/render/tex.c').read_text();code,repair,blocks=basic_create(root,extract,patch)
 code=code.replace('typedef struct{unsigned ordinal;}BasicTexture;','typedef struct BasicTexture{unsigned ordinal;const char*name;int load_state[2],use_category;struct BasicTexture*actualTexture;}BasicTexture;').replace('entries[2]','entries[6]').replace('keys[2]','keys[6]').replace('i<2;i++)if(same','i<fixture_count;i++)if(same')
 old='static int stashFindPointer(void*t,const char*key,BasicTexture**out){(void)t;calls++;strcpy(observed,key);for(unsigned i=0;i<fixture_count;i++)if(same(key,keys[i])){*out=entries+i;return 1;}return 0;}'
 new='static int stashFindPointer(void*t,const char*key,BasicTexture**out){(void)t;calls++;strcpy(observed,key);REQUIRE(active->lookup_count<2);strcpy(active->lookup_keys[active->lookup_count++],key);for(unsigned i=0;i<fixture_count;i++)if(same(key,keys[i])){*out=entries+i;return 1;}longjmp(unknown_namespace,1);}'
 if code.count(old)!=1:raise ValueError('basic observer preimage differs')
 code=code.replace(old,new)
 code='#include <setjmp.h>\n#include <stdio.h>\n#include "tests/tex_permutation_fixture.h"\nstatic jmp_buf unknown_namespace;static PermutationOracle*active;static unsigned fixture_count;\n'+code
 code+=r'''
#define MAX_PATH 260
#define TEX_NOT_LOADED 0
#define TEX_LOAD_IN_BACKGROUND 2
#define stricmp(a,b) (same(a,b)?0:1)
static int quickload=1;
static BasicTexture white_storage={0};static BasicTexture*white_tex=&white_storage;
typedef struct{char*src,*dst;}TexSwap;
static TexSwap**swaps;static TexSwap*rows;static unsigned swap_count;static int active_guarded;
static TexSwap**sceneGetTexSwaps(int*n){*n=(int)swap_count;return swaps;}
static BasicTexture*texFind(const char*q){return active_guarded?guarded_find(q):strict_find(q);}
static BasicTexture*texLoadBasic(const char*n,int m,int u){(void)n;(void)m;(void)u;abort();} /* source NOT_LOADED domain only */
static void Errorf(const char*fmt,...){(void)fmt;abort();} /* never invent white on UNKNOWN */
#define verbose_printf(...) ((void)0)
static char*eaPop(char***p);static void eaPush(char***p,char*s);static int eaSize(char***p);
static char*observer_strdup(const char*s){size_t n=strlen(s);char*p=malloc(n+1);REQUIRE(p);memcpy(p,s,n+1);return p;}
#define strdup observer_strdup
char **textureSearchPath=NULL;int numTextureSearchPaths=0;static unsigned locale_storage_count;
static char*eaPop(char***p){return locale_storage_count?(*p)[--locale_storage_count]:NULL;}
static void eaPush(char***p,char*s){if(!*p){*p=calloc(17,sizeof(char*));REQUIRE(*p);}REQUIRE(locale_storage_count<16);(*p)[locale_storage_count++]=s;}
static int eaSize(char***p){(void)p;return(int)locale_storage_count;}
'''
 for signature in ['static int texCheckForSceneSwaps(','void texSetSearchPath(','static int texCheckForSwaps(BasicTexture *texbind) {']:
  body=extract(tex,signature);blocks[signature]=body;code+=body+'\n'
 code+=r'''
void original_permutation(const char*const*names,unsigned count,const CohWrTexPermutationInput*q,PermutationOracle*out){
 REQUIRE(count<=6&&q->swap_count<=256);memset(out,0,sizeof(*out));out->candidate_ordinal=UINT32_MAX;out->scene_index=-99;active=out;fixture_count=count;active_guarded=(int)q->guarded_short_key_policy;
 for(unsigned i=0;i<count;i++){memset(entries+i,0,sizeof(entries[i]));keys[i]=entries[i].name=names[i];entries[i].ordinal=i;}
 rows=calloc(q->swap_count?q->swap_count:1,sizeof(*rows));swaps=calloc(q->swap_count?q->swap_count:1,sizeof(*swaps));REQUIRE(rows&&swaps);swap_count=q->swap_count;
 for(unsigned i=0;i<swap_count;i++){rows[i].src=malloc(128);rows[i].dst=malloc(128);REQUIRE(rows[i].src&&rows[i].dst);if(active_guarded){guarded_fix(q->swaps[i].source,rows[i].src,128);guarded_fix(q->swaps[i].destination,rows[i].dst,128);}else{strict_fix(q->swaps[i].source,rows[i].src,128);strict_fix(q->swaps[i].destination,rows[i].dst,128);}swaps[i]=rows+i;}
 char path[1025];REQUIRE(strlen(q->search_path)<sizeof(path));strcpy(path,q->search_path);texSetSearchPath(path);out->locale_count=(unsigned)numTextureSearchPaths;for(unsigned i=0;i<out->locale_count;i++)strcpy(out->locales[i],textureSearchPath[i]);
 if(!setjmp(unknown_namespace)){out->scene_index=texCheckForSwaps(entries+q->base_header_ordinal);out->candidate_ordinal=entries[q->base_header_ordinal].actualTexture->ordinal;out->fully_executed=1;}
 for(unsigned i=0;i<swap_count;i++){free(rows[i].src);free(rows[i].dst);}free(rows);rows=NULL;free(swaps);swaps=NULL;char*last;while((last=eaPop(&textureSearchPath)))free(last);free(textureSearchPath);textureSearchPath=NULL;numTextureSearchPaths=0;active=NULL;
}
'''
 return code,repair,blocks

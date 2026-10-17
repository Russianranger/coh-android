"""Unchanged original initial trick texture gate; explicit subset lookup observers."""
from pathlib import Path

def create(root,extract,patch):
 root=Path(root);tricks=(root/'upstream/ouroboros/Common/seq/tricks.c').read_text();tex=(root/'upstream/ouroboros/Game/src/render/tex.c').read_text()
 names=['static bool IsValidTexName(','static bool trickFindAllTextures(','void trickCreateTextures(']
 blocks={name.split('(')[0].split()[-1]:extract(tricks,name) for name in names}
 fix=extract(tex,'static int texFixName(');find=extract(tex,'BasicTexture *texFind(');guarded,repair=patch(fix)
 header=(root/'upstream/ouroboros/Game/src/render/tex.h').read_text();start=header.index('typedef enum TexFlags');flags=header[start:header.index('} TexFlags;',start)+len('} TexFlags;')]
 code=r'''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <stdio.h>
#include "coh_wr_tex_seed.h"
#include "coh_wr_texopt_types_internal.h"
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
typedef struct {unsigned ordinal;} BasicTexture;
typedef struct {unsigned classification,queries,slots[16],ordinals[16],flags[16];char keys[16][128];} SeedOracle;
static struct {TexOpt**texopts;} trick_list;
static void*texopt_delayedLoad;
static TexOpt current;static TexOpt*list[1];static const CohWrTexOptView*view;
static const char*header_keys[256];static unsigned header_count,guarded_policy,sequence[16],sequence_count;
static BasicTexture headers[256];static SeedOracle observed;static jmp_buf frontier;static CohStatus refusal;
static int g_basicTextures_ht;
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int stricmp(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=(int)fold((unsigned char)*a)-(int)fold((unsigned char)*b);if(d)return d;}return(unsigned char)*a-(unsigned char)*b;}
static int strnicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=(int)fold((unsigned char)a[i])-(int)fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static void strncpyt(char*d,const char*s,int n){assert(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static int eaSize(const void*p){assert(p==&trick_list.texopts);return 1;}
static void eaCreate(void**p){(void)p;abort();}
static void eaPush(void**p,TexOpt*t){(void)p;(void)t;abort();}
static int LWC_IsActive(void){return 0;}
static void ErrorFilenamef(const char*a,const char*b,const char*c,const char*d){(void)a;(void)b;(void)c;(void)d;abort();}
static void texCreateTrickTexture(const char*file,const char*name,const char*base){assert(file==current.file_name&&name==current.name&&base==current.blend_names[BLEND_BASE1]);observed.classification=COH_WR_TEX_SEED_CREATE_CANDIDATE;}
static int stashFindPointer(int table,const char*key,BasicTexture**out){assert(table==0&&observed.queries<16);unsigned q=observed.queries++;observed.slots[q]=sequence[q];assert(strlen(key)<128);strcpy(observed.keys[q],key);for(unsigned i=0;i<header_count;i++)if(!stricmp(key,header_keys[i])){observed.ordinals[q]=i;*out=headers+i;return 1;}refusal=COH_NOT_FOUND;longjmp(frontier,1);}
'''+flags+'\n#undef assert\n#define assert(x) ((void)0) /* original release debug poison assertions disabled */\n'
 for tag,body in [('strict',fix),('guarded',guarded)]:
  code+=body.replace('texFixName(',tag+'_fix(',1)
  code+='static int '+tag+'_observed(const char*s,char*r,int n){int type='+tag+'_fix(s,r,n);observed.flags[observed.queries]=(unsigned)type;return type;}\n#define texFixName '+tag+'_observed\n#define texFind '+tag+'_find\n'+find+'\n#undef texFixName\n#undef texFind\n'
 code+='\n#undef assert\n#include <assert.h>\n'+r'''
static BasicTexture*texFind(const char*name){assert(name);const char*s=*name=='!'?name+1:name;size_t n=strlen(s);if(n>127){refusal=COH_LIMIT;longjmp(frontier,1);}if(!guarded_policy&&n>=4&&n<8&&s[n-4]!='.'){refusal=COH_UNSUPPORTED;longjmp(frontier,1);}return guarded_policy?guarded_find(name):strict_find(name);}
'''+blocks['IsValidTexName']+'\n'+blocks['trickFindAllTextures']+'\n'+blocks['trickCreateTextures']+r'''
void original_seed_headers(unsigned count,const char*const*keys){assert(count<=256);header_count=count;for(unsigned i=0;i<count;i++){header_keys[i]=keys[i];headers[i].ordinal=i;}}
int original_seed(const CohWrTexOptView*v,unsigned guarded,SeedOracle*out){
 view=v;(void)view;memset(&current,0,sizeof(current));current.name=(char*)v->name;current.file_name=(char*)v->source_file;
 for(unsigned i=0;i<13;i++)current.blend_names[i]=v->layers[i].name;
 current.fallback.useFallback=v->fallback.use_fallback;current.fallback.base_name=(char*)v->fallback.base;current.fallback.blend_name=(char*)v->fallback.blend;current.fallback.bumpmap=(char*)v->fallback.bumpmap;
 list[0]=&current;trick_list.texopts=list;guarded_policy=guarded;refusal=COH_OK;sequence_count=0;
 for(unsigned i=0;i<16;i++){const char*s=i<13?v->layers[i].name:i==13?v->fallback.base:i==14?v->fallback.blend:v->fallback.bumpmap;if(i>=13&&!v->fallback.use_fallback)break;if(IsValidTexName(s))sequence[sequence_count++]=i;}
 memset(&observed,0,sizeof(observed));observed.classification=current.blend_names[BLEND_BASE1]?COH_WR_TEX_SEED_NAME_MATCHES_BASE1:COH_WR_TEX_SEED_NO_BASE1;
 if(!setjmp(frontier)){trickCreateTextures();}*out=observed;return refusal;
}
'''
 blocks.update(texFixName=fix,texFind=find,guarded_texFixName=guarded,TexFlags=flags)
 return code,blocks,repair

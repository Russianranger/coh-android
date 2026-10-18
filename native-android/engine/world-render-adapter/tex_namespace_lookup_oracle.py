"""Whole original texFind/fix observers; no old qualifier entrypoint executes."""
from pathlib import Path

def create(root,extract,patch):
 root=Path(root);source=(root/'upstream/ouroboros/Game/src/render/tex.c').read_text();header=(root/'upstream/ouroboros/Game/src/render/tex.h').read_text()
 fix=extract(source,'static int texFixName(');find=extract(source,'BasicTexture *texFind(');guarded,repair=patch(fix)
 start=header.index('typedef enum TexFlags');flags=header[start:header.index('} TexFlags;',start)+len('} TexFlags;')]
 code=r'''#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define assert(x) ((void)0) /* original release debug assertions disabled */
#define REQUIRE(x) do{if(!(x))abort();}while(0)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
typedef struct{unsigned ordinal;}BasicTexture;
static BasicTexture entries[32];static const char*keys[32];static unsigned count,calls,format;static char observed[128];static void*g_basicTextures_ht;
static void strncpyt(char*d,const char*s,int n){REQUIRE(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int same(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return!*a&&!*b;}
static int stashFindPointer(void*t,const char*key,BasicTexture**out){(void)t;calls++;strcpy(observed,key);for(unsigned i=0;i<count;i++)if(same(key,keys[i])){*out=entries+i;return 1;}return 0;}
'''+flags+'\n'
 for tag,body in [('strict',fix),('guarded',guarded)]:
  code+=body.replace('texFixName(',tag+'_fix(',1)
  code+='static int '+tag+'_observe(const char*s,char*r,int n){int type='+tag+'_fix(s,r,n);format=(unsigned)type;return type;}\n#define texFixName '+tag+'_observe\n#define texFind '+tag+'_find\n'+find+'\n#undef texFixName\n#undef texFind\n'
 code+=r'''void original_namespace_rows(unsigned n,const char*const*names){REQUIRE(n<=32);count=n;for(unsigned i=0;i<n;i++){keys[i]=names[i];entries[i].ordinal=i;}}
int original_namespace_lookup(const char*q,unsigned guarded,char key[128],unsigned*flags,unsigned*lookups){calls=format=0;observed[0]=0;BasicTexture*found=guarded?guarded_find(q):strict_find(q);strcpy(key,observed);*flags=format;*lookups=calls;return found?(int)found->ordinal:-1;}
'''
 return code,repair,{'texFind':find,'texFixName':fix,'guarded_texFixName':guarded,'TexFlags':flags}

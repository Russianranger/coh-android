"""Exact texFind/fix functions, bounded storage/table observers and explicit repair."""
from pathlib import Path

def create(root,extract,patch):
 root=Path(root);tex=(root/'upstream/ouroboros/Game/src/render/tex.c').read_text();header=(root/'upstream/ouroboros/Game/src/render/tex.h').read_text();fix=extract(tex,'static int texFixName(');find=extract(tex,'BasicTexture *texFind(');guarded,proof=patch(fix);a=header.index('typedef enum TexFlags');enum=header[a:header.index('} TexFlags;',a)+len('} TexFlags;')]
 code=r'''#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define assert(x) ((void)0) /* original release-mode debug assertions disabled */
#define REQUIRE(x) do{if(!(x))abort();}while(0)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
typedef struct{unsigned ordinal;}BasicTexture;
static BasicTexture entries[2];static const char*keys[2];static unsigned calls,format;static char observed[128];static void*g_basicTextures_ht;
static void strncpyt(char*d,const char*s,int n){REQUIRE(n>0&&strlen(s)<(unsigned)n);memcpy(d,s,strlen(s)+1);}
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int same(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return!*a&&!*b;}
static int stashFindPointer(void*t,const char*key,BasicTexture**out){(void)t;calls++;strcpy(observed,key);for(unsigned i=0;i<2;i++)if(same(key,keys[i])){*out=entries+i;return 1;}return 0;}
'''+enum+'\n'
 for tag,body in [('strict',fix),('guarded',guarded)]:
  code+=body.replace('texFixName(',tag+'_fix(',1)
  code+='static int '+tag+'_observed(const char*s,char*r,int n){int type='+tag+'_fix(s,r,n);format=(unsigned)type;return type;}\n#define texFixName '+tag+'_observed\n#define texFind '+tag+'_find\n'+find+'\n#undef texFixName\n#undef texFind\n'
 code+=r'''void original_basic_headers(const char*a,const char*b){keys[0]=a;keys[1]=b;entries[0].ordinal=0;entries[1].ordinal=1;}
int original_basic_find(const char*q,int guarded,char key[128],unsigned*flags,unsigned*lookups){calls=format=0;observed[0]=0;BasicTexture*match=guarded?guarded_find(q):strict_find(q);strcpy(key,observed);*flags=format;*lookups=calls;return match?(int)match->ordinal:-1;}
'''
 return code,proof,{'texFind':find,'texFixName':fix,'guarded_texFixName':guarded,'TexFlags':enum}

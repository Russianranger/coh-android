"""Extract and compile original costume name/color functions, unchanged bodies.
The shim implements source container/string/existence services only. It does not
invoke this module's assembly algorithm and does not emulate original GPU output.
"""
from pathlib import Path
import ctypes as C,hashlib,re,subprocess
FUNCTIONS=['get_color','gender_prefix_fixup','bodyPartIsLinkedToChest','doChangeGeo','determineTextureNames','calc_tex_types1']

def extract(text,name):
 m=re.search(r'(?m)^(?:(?:static|const|unsigned)\s+)*(?:[\w]+(?:\s*\*)?\s+|[\w]+\s*\*)'+re.escape(name)+r'\s*\(',text)
 if not m:raise ValueError('function absent: '+name)
 start=m.start();brace=text.index('{',m.end());i=brace+1;depth=1;quote=None;line=False;block=False
 while depth:
  c=text[i];n=text[i+1] if i+1<len(text) else ''
  if line:
   if c=='\n':line=False
  elif block:
   if c=='*' and n=='/':block=False;i+=1
  elif quote:
   if c=='\\':i+=1
   elif c==quote:quote=None
  elif c=='/' and n=='/':line=True;i+=1
  elif c=='/' and n=='*':block=True;i+=1
  elif c in '\"\'':quote=c
  elif c=='{':depth+=1
  elif c=='}':depth-=1
  i+=1
 return text[start:i]

PREAMBLE=r'''
#include <string.h>
#include <strings.h>
#include <stdio.h>
#include <stdbool.h>
#include <ctype.h>
#include "coh_appearance.h"
#define TRUE 1
#define FALSE 0
#define MAX_NAME_LEN 256
#define kBodyType_Villain 6
#define kBodyType_Male 0
#define kBodyType_Female 1
#define kBodyType_BasicMale 2
#define kBodyType_BasicFemale 3
#define kBodyType_Huge 4
#define kBodyType_Enemy 5
#define kBodyType_Enemy2 7
#define kBodyType_Enemy3 8
#define stricmp strcasecmp
#define strstriConst istrstr
#define strstri(s,n) ((char *)istrstr(s,n))
#define STR_COMBINE_BEGIN(a) {char *concat_buf=(a);size_t concat_size=sizeof(a);concat_buf[0]=0;
#define STR_COMBINE_BEGIN_S(a,n) {char *concat_buf=(a);size_t concat_size=(n);concat_buf[0]=0;
#define STR_COMBINE_CAT(a) strncat(concat_buf,(a),concat_size-strlen(concat_buf)-1)
#define STR_COMBINE_END() }
typedef union {unsigned int integer;unsigned char rgba[4];} Color;
typedef struct {int bodytype;const char *costumeFilePrefix;} Appearance;
typedef struct {Appearance appearance;} Costume;
typedef struct {Costume *costume;} Entity;
typedef struct {const char *name,*base_var,*name_geo,*name_tex;int bone_num[2],num_parts;} BodyPart;
typedef struct {int bodytype;const char *pchEntType,*pchTexPrefix;} BodyTypeInfo;
static const char *istrstr(const char *s,const char *n){for(;*s;s++){size_t i=0;while(n[i]&&s[i]&&tolower((unsigned char)n[i])==tolower((unsigned char)s[i]))i++;if(!n[i])return s;}return NULL;}
static CohAppearanceProbe exists_callback;static void *exists_context;
static int texFind(const char *s){return exists_callback&&exists_callback(exists_context,2,s);}
static int texFindComposite(const char *s){(void)s;return 1;}
static const char **links;static int nlinks;
#define eaSize(x) nlinks
static const char **getChestGeoLink(Entity *e){(void)e;return links;}
static int call_count;static char call_keys[2][256];static int call_bones[2];
static int changeGeo(Entity *e,int bone,const char *key,int warn){(void)e;if(!warn&&!(exists_callback&&exists_callback(exists_context,1,key)))return 0;if(call_count>=2)return 0;strcpy(call_keys[call_count],key);call_bones[call_count++]=bone;return 1;}
int calc_tex_types1(const char*,int*,int*);
'''
WRAPPERS=r'''
int ref_geometry(const CohAppearanceBody *b,const CohAppearancePartDef *d,const char *name,const char **cl,int n,CohAppearanceProbe cb,void *ctx,char *out,int *bones){
 Costume costume={{(int)b->body_type,b->geometry_prefix}};Entity e={&costume};BodyPart part={d->name,d->base_name,d->geometry_name,d->texture_name,{(int)d->socket[0],(int)d->socket[1]},(int)d->socket_count};
 exists_callback=cb;exists_context=ctx;call_count=0;links=cl;nlinks=n;memset(call_keys,0,sizeof call_keys);doChangeGeo(&e,&part,name,NULL,NULL);memcpy(out,call_keys,sizeof call_keys);memcpy(bones,call_bones,call_count*sizeof(int));return call_count;
}
void ref_textures(const CohAppearanceBody *b,const CohAppearancePartDef *d,const char *one,const char *two,CohAppearanceProbe cb,void *ctx,char *out){
 Appearance appearance={(int)b->body_type,b->geometry_prefix};BodyPart part={d->name,d->base_name,d->geometry_name,d->texture_name,{(int)d->socket[0],(int)d->socket[1]},(int)d->socket_count};exists_callback=cb;exists_context=ctx;determineTextureNames(&part,&appearance,one,two,out,256,out+256,256,NULL,NULL);
}
void ref_colors(const unsigned char *skin,const unsigned char *colors,const char *texture,unsigned char *out){Color s,a,b;memcpy(&s,skin,4);memcpy(&a,colors,4);memcpy(&b,colors+4,4);get_color(NULL,s,a,b,(int*)out,(int*)(out+4),texture);}
const char *ref_ent(int t){return g_BodyTypeInfos[t].pchEntType;}
const char *ref_tex(int t){return g_BodyTypeInfos[t].pchTexPrefix;}
'''
def build(source_root,temp,include):
 source=source_root/'upstream/ouroboros';client=(source/'Game/src/entity/costume_client.c').read_text(encoding='latin1').replace('\r\n','\n');common=(source/'Common/entity/costume.c').read_text(encoding='latin1').replace('\r\n','\n')
 snippets=[extract(client,n) for n in FUNCTIONS];prefix=extract(common,'costumePrefixName');table=re.search(r'BodyTypeInfo g_BodyTypeInfos\[\]\s*=\s*\{.*?\n\};',common,re.S).group()
 c=temp/'original.c';c.write_text(PREAMBLE+'\n'+table+'\n'+prefix+'\n'+'\n'.join(snippets)+'\n'+WRAPPERS)
 so=temp/'original.so';subprocess.run(['cc','-std=c99','-O0','-fPIC','-shared','-I',str(include),str(c),'-o',str(so)],check=True)
 pins={n:hashlib.sha256(s.encode()).hexdigest() for n,s in zip(FUNCTIONS,snippets)};pins['costumePrefixName']=hashlib.sha256(prefix.encode()).hexdigest();pins['g_BodyTypeInfos']=hashlib.sha256(table.encode()).hexdigest()
 return C.CDLL(str(so)),pins

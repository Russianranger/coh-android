"""Complete original three-cache grammar/finalizers with bounded host storage.
No shared memory, geometry, UI, evaluation or current cache authority.
"""
import ctypes as C,hashlib,json,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/salvage.c','Common/entity/salvage.h','Common/entity/TokenizerUiWidget.h','Common/entity/character_inventory.c','Common/entity/character_inventory.h','Common/bases/basedata.c','Common/bases/basedata.h','Common/bases/baseparse.c','Common/entity/character_eval.c','Common/entity/load_def.c','Common/entity/RewardItemType.c','libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','libs/UtilitiesLib/src/components/earray.c','libs/UtilitiesLib/include/utilitieslib/utils/structDefines.h']
def sha(b):return hashlib.sha256(b).hexdigest()
LOCKED={}
def module(n,p):
 p=p.resolve();raw=p.read_bytes()
 if LOCKED.get(p)!=sha(raw):raise ValueError('unadmitted Salvage source provider')
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__);return m
def admit(root):
 pins=json.loads((HERE/'salvage-source-pins.json').read_bytes())
 if set(pins)!={'source_sha256_raw','source_sha256_lf','helper_sha256_raw','scope'}:raise ValueError('Salvage source manifest shape')
 for path,expected in pins['source_sha256_raw'].items():
  raw=(root/'upstream/ouroboros'/path).read_bytes()
  if sha(raw)!=expected or sha(raw.replace(b'\r\n',b'\n'))!=pins['source_sha256_lf'].get(path):raise ValueError('Salvage original source differs '+path)
 for path,expected in pins['helper_sha256_raw'].items():
  p=(root/path).resolve()
  if sha(p.read_bytes())!=expected:raise ValueError('Salvage source helper differs '+path)
  LOCKED[p]=expected
 return pins

def extract(text,name):
 match=re.search(r'^[\w \t*]+(?:\n[ \t]*)?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('original Salvage function '+name)
 at=text.index('{',match.start());depth=0;mode='code'
 while at<len(text):
  char=text[at];pair=text[at:at+2]
  if mode=='code':
   if pair=='//':mode='line';at+=2;continue
   if pair=='/*':mode='comment';at+=2;continue
   if char in ('"',"'"):mode=char
   elif char=='{':depth+=1
   elif char=='}':
    depth-=1
    if not depth:return text[match.start():at+1]+'\n'
  elif mode=='line':
   if char=='\n':mode='code'
  elif mode=='comment':
   if pair=='*/':mode='code';at+=2;continue
  elif char=='\\':at+=2;continue
  elif char==mode:mode='code'
  at+=1
 raise ValueError('unclosed original Salvage function '+name)
def build(root,work):
 root=Path(root);pins=admit(root)
 small=module('salvage_small',HERE/'../costume-inputs/oracle.py');small.extract=extract;tmp=work/'small';tmp.mkdir();_,baseproof=small.build(root,tmp);code=(tmp/'original.c').read_text()
 for n in ('original_decode','original_result_size'):code=code.replace(small.extract(code,n),'')
 code=code.replace('65536','1048576').replace('typedef struct{int size;void*items[256];}Vec;','typedef struct{int size,capacity;void*items[];}Vec;').replace('n<=256','n<=8192').replace('raw_ints[1024]','raw_ints[262144]').replace('raw_int_count<1024','raw_int_count<262144').replace('allocations[2048]','allocations[131072]').replace('allocation_count<2048','allocation_count<131072')
 # The storage adapter now also supports primitive indirect arrays and links.
 for n in ('TokenStoreGetPointer','TokenStoreSetString','TokenStoreGetString','TokenStoreSetCapacity'):
  code=code.replace(small.extract(code,n),'')
 insert='''
static Vec*vector(unsigned capacity,unsigned size){assert(capacity<=8192&&size<=capacity);Vec*v=alloc(sizeof(*v)+(size_t)capacity*sizeof(void*));v->capacity=(int)capacity;v->size=(int)size;return v;}
static void TokenStoreSetCapacity(ParseTable*t,int c,void*p,int n){assert(n>=0&&n<=8192);*(Vec**)field(t,c,p)=vector((unsigned)n,(unsigned)n);}
static void*TokenStoreGetPointer(ParseTable*t,int c,const void*p,int i){if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i>=0&&i<v->size);return v->items[i];}return *(void**)field(t,c,p);}
static void TokenStoreSetPointer(ParseTable*t,int c,void*p,int i,void*v){if(t[c].type&TOK_EARRAY){Vec*a=*(Vec**)field(t,c,p);assert(a&&i>=0&&i<a->size);a->items[i]=v;}else *(void**)field(t,c,p)=v;}
static void TokenStoreSetString(ParseTable*t,int c,void*p,int i,const char*s,void*a,void*b){(void)a;(void)b;size_t n=strlen(s);assert(n<12000);char*q=alloc(n+1);memcpy(q,s,n+1);TokenStoreSetPointer(t,c,p,i,q);}
static char*TokenStoreGetString(ParseTable*t,int c,const void*p,int i){return TokenStoreGetPointer(t,c,p,i);}
'''
 anchor='typedef struct{int(*readbin)';code=code.replace(anchor,insert+'\n'+anchor)
 code=code.replace('static Handler typeinfo(U32 t)', 'static Handler unused_typeinfo(U32 t)')
 src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};tp=(root/'upstream/ouroboros'/small.PATHS[5]).read_text();functions={};tables={}
 def f(path,n):
  body=small.extract(tp if path==small.PATHS[5] else src[path],n);functions[path+':'+n]=sha(body.encode());return body
 code+='''
#include <strings.h>
#include <ctype.h>
#define stricmp strcasecmp
#include "coh_salvage.h"
typedef int bool;
#define false 0
#define true 1
#define FINAL 1
#define SERVER 0
#define verify(x) (x)
#undef devassert
#define devassert(x) (assert(x),(x))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof(*(x)))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define cpp_const_cast(t) (t)
#define stashShared(x) (x)
#define StashKeyTypeInts 1
#define StashDeepCopyKeys 0
#define stashOptimalSize(x) (x)
#define MAX_LINK_LEN 128
static unsigned source_errors,source_roundtrip_sizes[3];
#define Errorf(...) (source_errors++)
typedef struct{const char*name;intptr_t value;int id;}Slot;
typedef struct{unsigned n,kind;Slot slots[8192];}Map;
typedef Map*StashTable;typedef Map*cStashTable;typedef Slot*StashElement;
typedef struct{Map*m;unsigned i;}StashTableIterator;
static Map*stashTableCreateWithStringKeys(unsigned n,int shared){(void)n;(void)shared;return alloc(sizeof(Map));}
static Map*stashTableCreate(unsigned n,int shared,int kind,unsigned bytes){(void)bytes;Map*m=stashTableCreateWithStringKeys(n,shared);m->kind=kind;return m;}
static Map*stashTableCreateAddress(unsigned n){Map*m=stashTableCreateWithStringKeys(n,0);m->kind=2;return m;}
static int keyeq(Map*m,const void*a,const void*b){return m->kind==2?a==b:!strcasecmp(a,b);}
static int stashFindElementConst(Map*m,const void*key,Slot**out){for(unsigned i=0;i<m->n;i++)if(keyeq(m,m->slots[i].name,key)){if(out)*out=&m->slots[i];return 1;}return 0;}
static int stashAddPointerConst(Map*m,const void*key,const void*v,int overwrite){Slot*p;if(stashFindElementConst(m,key,&p)){if(overwrite)p->value=(intptr_t)v;return overwrite;}assert(m->n<8192);m->slots[m->n++]=(Slot){key,(intptr_t)v,0};return 1;}
#define stashAddPointer stashAddPointerConst
static int stashAddPointerAndGetElement(Map*m,const void*key,const void*v,int over,Slot**out){int r=stashAddPointerConst(m,key,v,over);stashFindElementConst(m,key,out);return r;}
static int stashAddIntConst(Map*m,const void*k,int v,int over){return stashAddPointerConst(m,k,(void*)(intptr_t)v,over);}
static int stashIntAddPointerConst(Map*m,int id,const void*v,int over){(void)over;for(unsigned i=0;i<m->n;i++)if(m->slots[i].id==id)return 0;assert(m->n<8192);m->slots[m->n++]=(Slot){NULL,(intptr_t)v,id};return 1;}
static int stashFindPointer(Map*m,const void*k,void*out){Slot*p;int found=stashFindElementConst(m,k,&p);if(out)*(void**)out=found?(void*)p->value:NULL;return found;}
static int stashFindInt(Map*m,const void*k,int*out){Slot*p;int found=stashFindElementConst(m,k,&p);if(out)*out=found?(int)p->value:0;return found;}
#define stashAddressFindPointer stashFindPointer
#define stashAddressAddPointer stashAddPointerConst
static void*stashElementGetPointer(Slot*p){return(void*)p->value;}
static void stashElementSetPointer(Slot*p,void*v){p->value=(intptr_t)v;}
static const char*stashElementGetStringKey(Slot*p){return p->name;}
static void stashGetIterator(Map*m,StashTableIterator*i){*i=(StashTableIterator){m,0};}
static int stashGetNextElement(StashTableIterator*i,Slot**out){if(i->i==i->m->n)return 0;*out=&i->m->slots[i->i++];return 1;}
static unsigned stashGetValidElementCount(Map*m){return m->n;}
static void stashTableDestroy(Map*m){(void)m;}
#define eaSize(pp) (*(pp)?((Vec*)((char*)*(pp)-offsetof(Vec,items)))->size:0)
#define EAINRANGE(i,a) ((i)>=0&&(i)<eaSize(&(a)))
static void eaCreateWithCapacity(void*out,int cap){assert(cap>=0&&cap<=8192);Vec*v=vector((unsigned)cap,0);*(void***)out=v->items;}
#define eaCreateWithCapacityConst eaCreateWithCapacity
static void eaSetSize(void*out,int n){Vec*v=(Vec*)((char*)*(void***)out-offse tof(Vec,items));assert(n>=0&&n<=v->capacity);v->size=n;}
static int eaSet(void*out,const void*p,int i){Vec*v=(Vec*)((char*)*(void***)out-offse tof(Vec,items));if(i<0||i>=v->size)return 0;v->items[i]=(void*)p;return 1;}
static int eaPush(void*out,const void*p){Vec*v=(Vec*)((char*)*(void***)out-offse tof(Vec,items));assert(v->size<8192);if(v->size==v->capacity){unsigned capacity=v->capacity?(unsigned)v->capacity*2:1;assert(capacity<=8192);Vec*larger=vector(capacity,(unsigned)v->size);memcpy(larger->items,v->items,(size_t)v->size*sizeof(void*));v=larger;*(void***)out=v->items;}v->items[v->size++]=(void*)p;return v->size-1;}
static void eaCompress(void*out,void*in,void*a,void*b){(void)a;(void)b;*(void***)out=*(void***)in;}
#define eaCompressConst eaCompress
static void eaDestroy(void*out){*(void***)out=NULL;}
#define customSharedMalloc NULL
'''.replace('offse tof','offsetof')
 # Exact schema declarations on explicit host member-layout adapters.
 code+=re.search(r'typedef struct TokenizerUiWidget\b.*?} TokenizerUiWidget;',src[EXTRA[2]],re.S).group()+'\n'
 code+=src[EXTRA[2]][src[EXTRA[2]].index('#define TOKENIZERUIWIDGET_INLINEPARSEINFO'):src[EXTRA[2]].index('\n\n\n#endif')]+'\n'
 code+='typedef struct {char*key;char*value;char*display;}StaticDefine;typedef struct{const char*key;intptr_t value;const char*display;}StaticDefineInt;\n#define DM_END 0\n#define DM_INT 1\n#define DM_STRING 2\n#define DM_DYNLIST 3\n#define DM_NOTYPE 4\n#define U32_TO_PTR(x) ((void*)(uintptr_t)(x))\n#define PTR_TO_S32(x) ((int)(intptr_t)(x))\n#define DEFINE_INT {(char*)U32_TO_PTR(DM_INT),0},\n#define DEFINE_END {(char*)U32_TO_PTR(DM_END),0},\n'
 for path,names in ((EXTRA[1],('SalvageRarity','SalvageType')),(EXTRA[6],('Surface','DetailFunction'))):
  for n in names:code+=re.search(r'typedef enum '+n+r'[^\n]*\n\{.*?} '+n+';',src[path],re.S).group()+'\n'
 code+='\n'.join(l for l in src[EXTRA[1]].splitlines() if re.match(r'#define\s+SALVAGE_',l))+'\n'
 for path,names in ((EXTRA[0],('RarityEnum','TypeEnum','ParseSalvageFlags')),(EXTRA[5],('SurfaceEnum','DetailFunctionEnum'))):
  for n in names:code+=re.search(r'(?:static )?StaticDefineInt '+n+r'\[\]\s*=.*?\n};',src[path],re.S).group()+'\n'
 detail_table=re.search(r'static TokenizerParseInfo ParseDetail\[\]\s*=.*?\n};',src[EXTRA[5]],re.S).group();members=['const char *pchName,*pchDisplayName,*pchDisplayHelp,*pchDisplayShortHelp;']
 for typ,member in re.findall(r'(?<!/)\bTOK_(STRINGARRAY|STRING|INT|BOOLFLAG|BOOL|F32)\(\s*Detail,\s*(\w+)',detail_table):members.append({'STRINGARRAY':'const char**','STRING':'const char*','INT':'int ','BOOLFLAG':'U8 ','BOOL':'U8 ','F32':'F32 '}[typ]+member+';')
 code+='typedef struct Detail{'+''.join(members)+'}Detail;typedef struct{const Detail**ppDetails;}DetailDict;static DetailDict g_DetailDict;\n'
 for n in ('SalvageItem','SalvageDictionary'):code+=re.search(r'typedef struct '+n+r'\s*\{.*?}\s*'+n+';',src[EXTRA[1]],re.S).group()+'\n'
 for n in ('AttribFileItem','AttribFileDict'):code+=re.search(r'typedef struct '+n+r'\s*\{.*?}\s*'+n+';',src[EXTRA[4]],re.S).group()+'\n'
 code+='static AttribFileDict original_attrs;\n#define kInventoryType_Salvage 0\nstatic AttribFileDict*inventorytype_GetAttribs(int kind){assert(kind==0);return &original_attrs;}\n'
 # Original whole StructLink leaf lookup/writer execute with bounded maps.
 code+=re.search(r'typedef struct StructLinkOffset\s*\{.*?} StructLinkOffset;', (root/'upstream/ouroboros'/small.PATHS[9]).read_text(),re.S).group()+'\n'
 code+=re.search(r'typedef struct StructLink\b[^\n]*\n\{.*?} StructLink;', (root/'upstream/ouroboros'/small.PATHS[9]).read_text(),re.S).group()+'\n'
 code+='typedef StructLink ParseLink;\n'+re.search(r'ParseLink g_base_detailInfoLink\s*=.*?\n};',src[EXTRA[7]],re.S).group()+'\n'
 code+='typedef struct LinkCacheElt{union{U8***psubarray;void*value;};Map*hashChildren;}LinkCacheElt;\nstatic LinkCacheElt*linkcacheelt_Create(U8***p){LinkCacheElt*v=alloc(sizeof(*v));if(p){v->psubarray=p;v->hashChildren=stashTableCreateWithStringKeys(32,0);}return v;}\nstatic void AddToStructLinkCacheTracker(struct StructLinkCache*p){(void)p;}\nstatic char*adapter_strdup(const char*s){char*p=alloc(strlen(s)+1);strcpy(p,s);return p;}\n#define strdup adapter_strdup\n#define strcpy_s(d,n,s) (assert(strlen(s)<(n)),strcpy(d,s))\n#define strcat_s(d,n,s) (assert(strlen(d)+strlen(s)<(n)),strcat(d,s))\n'
 for n in ('makeLinkStringRecur','findLinkFromStringRecur','StructLinkToString','StructLinkFromString'):code+=f(small.PATHS[5],n)
 # Observe only the actual unchanged link reader's Pascal-string result. This
 # keeps persisted spelling independent of the source-selected Details label.
 code+='''
static const char*source_link_texts[8192];static unsigned source_link_count,source_link_cursor;
static int observed_link_pascal(SimpleBufHandle in,char*out,int cap){int n=ReadPascalString(in,out,cap);assert(source_link_count<8192);source_link_texts[source_link_count++]=adapter_strdup(out);return n;}
#define ReadPascalString observed_link_pascal
'''+f(small.PATHS[5],'link_readbin')+'#undef ReadPascalString\n'+f(small.PATHS[5],'link_writebin')
 code+='''
#define TOK_STRINGARRAY(s,m) TOK_INDIRECT|TOK_EARRAY|TOK_STRING_X,offsetof(s,m),0
#define TOK_LINKARRAY(s,m,dict) TOK_INDIRECT|TOK_EARRAY|TOK_LINK_X,offsetof(s,m),0,dict
#define TOK_FLAGS(s,m,d) TOK_FLAGS_X,offsetof(s,m),d
#define TOK_BOOL(s,m,d) TOK_BOOL_X,offsetof(s,m),d
#define TOK_F32(s,m,d) TOK_F32_X,offsetof(s,m),d
static Handler typeinfo(U32 t){switch(TOK_GET_TYPE(t)){case TOK_FLAGS_X:case TOK_INT_X:return(Handler){int_readbin,int_writebin};case TOK_BOOL_X:case TOK_BOOLFLAG_X:return(Handler){u8_readbin,u8_writebin};case TOK_F32_X:return(Handler){float_readbin,float_writebin};case TOK_STRING_X:case TOK_CURRENTFILE_X:return(Handler){string_readbin,string_writebin};case TOK_LINK_X:return(Handler){link_readbin,link_writebin};case TOK_STRUCT_X:return(Handler){struct_readbin,struct_writebin};case TOK_START:case TOK_END:return(Handler){0,0};default:assert(0);return(Handler){0,0};}}
'''
 code+=re.search(r'#define PARSE_NAME_AND_HELP.*?\n\n',src[EXTRA[5]],re.S).group()+'\n'
 for path,names in ((EXTRA[0],('ParseSalvageDef','ParseSalvageDictionary')),(EXTRA[3],('ParseAttributeItem','ParseAttributeItems')),(EXTRA[5],('ParseDetail','ParseDetailDict'))):
  for n in names:
   body=re.search(r'(?:static )?TokenizerParseInfo '+n+r'\[\]\s*=.*?\n};',src[path],re.S).group();tables[n]=sha(body.encode());code+='\n'+body
 code+=f(EXTRA[3],'attribfiledict_FinalProcess')+f(EXTRA[8],'chareval_Validate')+f(EXTRA[0],'salvage_CreateTabNameHash')+f(EXTRA[0],'salvage_FinalProcess')
 # Execute the actual bounded getters as well as the finalizer maps.
 code+='static SalvageDictionary g_SalvageDict;\nstatic const void*stashFindPointerReturnPointerConst(Map*m,const char*name){void*out=NULL;stashFindPointer(m,name,&out);return out;}\n'
 code+=f(EXTRA[0],'salvage_GetItem')+f(EXTRA[0],'salvage_GetItemById')
 # Copy source state only; do not execute Details gameplay pre/post/finalizers.
 code+='''
static CohSalvageText original_copy(CohSalvageDictionary*out,const char*s){if(!s)s="";unsigned n=strlen(s);assert(n+1<=COH_SALVAGE_TEXT_MAX-out->text_bytes);CohSalvageText t={out->text_bytes,n};memcpy(out->text+t.offset,s,n+1);out->text_bytes+=n+1;return t;}
static void original_array(CohSalvageDictionary*out,CohSalvageRange*range,const void*array,int links){Vec*v=(Vec*)array;range->first=out->value_count;range->count=v?v->size:0;for(unsigned i=0;i<range->count;i++){assert(out->value_count<COH_SALVAGE_VALUES_MAX);CohSalvageValue*t=&out->values[out->value_count++];if(links){assert(source_link_cursor<source_link_count);t->text=original_copy(out,source_link_texts[source_link_cursor++]);const Detail*d=v->items[i];if(d){for(int j=0;j<eaSize(&g_DetailDict.ppDetails);j++)if(g_DetailDict.ppDetails[j]==d){t->detail_plus_one=j+1;out->workshop_joins++;break;}}}else t->text=original_copy(out,v->items[i]);}}
int original_salvage(const unsigned char*const bytes[3],const unsigned sizes[3],const unsigned begins[3],CohSalvageDictionary*out,unsigned char*roundtrip[3]){
 reset();source_errors=0;source_link_count=source_link_cursor=0;memset(out,0,sizeof(*out));memset(&original_attrs,0,sizeof(original_attrs));memset(&g_DetailDict,0,sizeof(g_DetailDict));memset(&g_base_detailInfoLink.cache,0,sizeof(g_base_detailInfoLink.cache));SalvageDictionary dict={0};Vec*dv=NULL,*sv=NULL,*iv=NULL;
 for(unsigned step=0;step<3;step++){unsigned k=step==0?2:step==1?1:0;SimpleBuffer*in=alloc(sizeof(*in)),*wr=alloc(sizeof(*wr));assert(sizes[k]<=1048576);memcpy(in->data,bytes[k],sizes[k]);in->filesize=sizes[k];in->curposition=begins[k];int sum=0;ParseTable*table=k==0?ParseSalvageDictionary:k==1?ParseAttributeItems:ParseDetailDict;void*obj=k==0?(void*)&dict:k==1?(void*)&original_attrs:(void*)&g_DetailDict;assert(ParserReadBinaryTable(in,table,obj,&sum)&&in->curposition==(int)sizes[k]);wr->curposition=wr->filesize=begins[k];memcpy(wr->data,bytes[k],begins[k]);assert(ParserWriteBinaryTable(wr,table,obj,&sum,0,0));assert(wr->filesize>=0&&(unsigned)wr->filesize<=sizes[k]);source_roundtrip_sizes[k]=(unsigned)wr->filesize;memset(roundtrip[k],0,sizes[k]);memcpy(roundtrip[k],wr->data,(size_t)wr->filesize);if(k==2){dv=(Vec*)g_DetailDict.ppDetails;if(!dv)dv=vector(0,0);g_DetailDict.ppDetails=(const Detail**)dv->items;}}
 sv=(Vec*)dict.ppSalvageItems;iv=(Vec*)original_attrs.ppAttribItems;if(!sv)sv=vector(0,0);if(!iv)iv=vector(0,0);dict.ppSalvageItems=(const SalvageItem**)sv->items;original_attrs.ppAttribItems=(const AttribFileItem**)iv->items;int id_ok=attribfiledict_FinalProcess(NULL,&original_attrs,0);int ok=salvage_FinalProcess(NULL,&dict,0);out->count=sv->size;out->id_count=iv->size;out->details_count=dv->size;out->max_id=original_attrs.maxId;out->slot_count=eaSize(&dict.itemsById);g_SalvageDict=dict;
 for(unsigned i=0;i<out->count;i++){const SalvageItem*s=sv->items[i];CohSalvageItem*t=&out->items[i];const char*fields[]={s->pchName,s->ui.pchDisplayName,s->ui.pchDisplayHelp,s->ui.pchDisplayShortHelp,s->ui.pchIcon,s->pchDisplayTabName,s->pchDisplayDropMsg};for(unsigned j=0;j<7;j++)t->fields[j]=original_copy(out,fields[j]);t->words[0]=s->rarity;t->words[1]=s->type;t->words[2]=s->challenge_points;t->words[3]=s->minRevEngLevel;t->words[4]=s->maxInvAmount;t->words[5]=s->sellAmount;t->words[6]=s->flags;t->id=s->salId;original_array(out,&t->arrays[0],s->ppWorkshops,1);original_array(out,&t->arrays[1],s->ppchRewardTables,0);original_array(out,&t->arrays[2],s->ppchOpenRequires,0);original_array(out,&t->arrays[3],s->ppchAuctionRequires,0);t->fields[7]=original_copy(out,s->pchDisplayOpenRequiresFail);t->fields[8]=original_copy(out,s->pchStoreProduct);}
 for(unsigned i=0;i<out->id_count;i++){const AttribFileItem*s=iv->items[i];out->id_rows[i].id=s->id;out->id_rows[i].name=original_copy(out,s->name);}for(unsigned i=0;i<out->details_count;i++)out->details[i]=original_copy(out,((Detail*)dv->items[i])->pchName);
 for(unsigned id=0;id<out->slot_count;id++){const SalvageItem*selected=salvage_GetItemById((int)id);assert(selected==dict.itemsById[id]);if(selected)for(unsigned i=0;i<out->count;i++)if(selected==sv->items[i])out->slots[id]=i+1;}
 for(unsigned i=0;i<out->count;i++){const SalvageItem*s=sv->items[i];const SalvageItem*selected=salvage_GetItem(s->pchName);unsigned first;for(first=0;first<out->count;first++)if(!strcasecmp(((const SalvageItem*)sv->items[first])->pchName,s->pchName))break;assert(first<out->count&&selected==sv->items[first]);}
 for(unsigned i=0;i<out->count;i++){const SalvageItem*s=sv->items[i];unsigned tab;for(tab=0;tab<out->tab_count;tab++){const char*n=out->text+out->tabs[tab].name.offset;if(!strcasecmp(n,s->pchDisplayTabName))break;}if(tab==out->tab_count){out->tabs[tab].name=out->items[i].fields[5];out->tab_count++;}}
 unsigned cursor=0;for(unsigned t=0;t<out->tab_count;t++){const char*name=out->text+out->tabs[t].name.offset;void**members=NULL;assert(stashFindPointer(dict.itemsFromTabName,name,&members));out->tabs[t].members=(CohSalvageRange){cursor,eaSize(&members)};for(int j=0;j<eaSize(&members);j++){unsigned row;for(row=0;row<out->count;row++)if(sv->items[row]==members[j])break;assert(row<out->count);out->tab_members[cursor++]=row;}}
 assert(source_link_cursor==source_link_count);int result=ok&&id_ok;reset();memset(&g_SalvageDict,0,sizeof(g_SalvageDict));return result;
}
size_t original_salvage_sizeof(void){return sizeof(CohSalvageDictionary);}
unsigned original_salvage_roundtrip_size(unsigned k){assert(k<3);return source_roundtrip_sizes[k];}
unsigned original_salvage_error_count(void){return source_errors;
}
'''
 crc=module('salvage_crc',HERE/'../costume-tree/crc_provider.py');cc,crcproof=crc.generate(root,tp,small.extract);cc=cc[:cc.index('unsigned original_tree_crc(')];cc=cc.replace('static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(0);}', 'static void UpdateCrcFromStaticDefines(StaticDefine[]);')
 cc=cc.replace('case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:', 'case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:case TOK_BOOL_X:case TOK_FLAGS_X:').replace('case TOK_END:return(CrcHandler)', 'case TOK_START:case TOK_END:return(CrcHandler)').replace('case TOK_STRUCT_X:return(CrcHandler)', 'case TOK_LINK_X:return(CrcHandler){link_interpretfield};case TOK_STRUCT_X:return(CrcHandler)')
 cc=cc.replace('typedef struct{ParseInfoFieldUsage(*interpretfield)',f(small.PATHS[5],'link_interpretfield')+'\ntypedef struct{ParseInfoFieldUsage(*interpretfield)')
 code+='\n'+cc+'\n'+f(small.PATHS[5],'UpdateCrcFromStaticDefines')+'\nunsigned original_salvage_crc(unsigned k){return (U32)ParseTableCRC(k==0?ParseSalvageDictionary:k==1?ParseAttributeItems:ParseDetailDict,NULL);}\n'
 path=work/'original-salvage.c';path.write_text(code);admit(root);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE),'-I'+str(HERE/'../costume-inputs'),path,'-lz','-o',work/'original-salvage.so'],check=True)
 admit(root);lib=C.CDLL(str(work/'original-salvage.so'));lib.original_salvage.argtypes=[C.c_void_p]*5;lib.original_salvage.restype=C.c_int;lib.original_salvage_sizeof.argtypes=[];lib.original_salvage_sizeof.restype=C.c_size_t;lib.original_salvage_error_count.argtypes=[];lib.original_salvage_error_count.restype=C.c_uint;lib.original_salvage_roundtrip_size.argtypes=[C.c_uint];lib.original_salvage_roundtrip_size.restype=C.c_uint;lib.original_salvage_crc.argtypes=[C.c_uint];lib.original_salvage_crc.restype=C.c_uint
 return lib,{'source_sha256_lf':{p:sha(t.encode()) for p,t in src.items()},'whole_function_sha256_lf':functions,'table_sha256_lf':tables,'binary_provider':baseproof,'crc':crcproof,'generated_source_sha256':sha(code.encode()),'original_stash_hash_allocator':False,'Details_gameplay_finalizers':False,'CLIENT_chareval_body_executed_as_noop':True,'shared_memory_branch':False,'original_oracle_sanitized':False,'source_admission_manifest':pins,'bounded_storage':'parsed vectors exact count; tab vectors grow by doubling to8192 with former buffers retained until reset; slot vectors support8192 elements','ordinary_source_getters_executed':True,'serialized_workshop_text_observed_at_original_link_ReadPascalString_boundary':True}

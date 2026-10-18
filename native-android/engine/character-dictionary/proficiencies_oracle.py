"""Whole original Parse6 readers/writers and two inventory finalizers.
Bounded host TokenStore/earray/stash storage adapters, ASCII default key equality;
not the engine hash allocator, shared-memory loader, ABI, or live cache branch.
"""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/Proficiency.c','Common/entity/Proficiency.h','Common/entity/TokenizerUiWidget.h','Common/entity/character_inventory.c','Common/entity/character_inventory.h','Common/entity/load_def.c','Common/entity/RewardItemType.c','libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','libs/UtilitiesLib/src/components/earray.c','libs/UtilitiesLib/include/utilitieslib/utils/structDefines.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 small=module('proficiency_small',HERE/'../costume-inputs/oracle.py');prior=work/'small';prior.mkdir();_,proof=small.build(root,prior)
 code=(prior/'original.c').read_text()
 for n in ('original_decode','original_result_size'):code=code.replace(small.extract(code,n),'')
 code=code.replace('items[256]','items[8192]').replace('n<=256','n<=1024').replace('raw_ints[1024]','raw_ints[4096]').replace('raw_int_count<1024','raw_int_count<4096').replace('allocations[2048]','allocations[8192]').replace('allocation_count<2048','allocation_count<8192')
 src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};functions={};tables={}
 def f(path,name):
  t=small.extract(src[path],name);functions[path+':'+name]=sha(t.encode());return t
 code+='''
#include <strings.h>
typedef int bool;
#define false 0
#define true 1
#define verify(x) (x)
#define MAX(a,b) ((a)>(b)?(a):(b))
#define cpp_const_cast(t) (t)
#define stashShared(x) (x)
#define StashKeyTypeInts 1
#define stashOptimalSize(x) (x)
typedef struct {char*name;intptr_t value;int id;} Slot;
typedef struct {unsigned n;int ints;Slot slots[1024];} Map;
typedef Map* StashTable;typedef Map* cStashTable;
static Map*stashTableCreateWithStringKeys(unsigned n,int shared){(void)n;(void)shared;return alloc(sizeof(Map));}
static Map*stashTableCreate(unsigned n,int shared,int type,unsigned size){(void)size;Map*m=stashTableCreateWithStringKeys(n,shared);m->ints=type;return m;}
static int stashAddPointerConst(Map*m,const void*key,const void*v,int overwrite){(void)overwrite;for(unsigned i=0;i<m->n;i++)if(!strcasecmp(m->slots[i].name,key))return 0;assert(m->n<1024);m->slots[m->n++]=(Slot){(char*)key,(intptr_t)v,0};return 1;}
static int stashAddIntConst(Map*m,const void*key,int v,int overwrite){return stashAddPointerConst(m,key,(void*)(intptr_t)v,overwrite);}
static int stashIntAddPointerConst(Map*m,int id,const void*v,int overwrite){(void)overwrite;for(unsigned i=0;i<m->n;i++)if(m->slots[i].id==id)return 0;assert(m->n<1024);m->slots[m->n++]=(Slot){NULL,(intptr_t)v,id};return 1;}
static int stashFindInt(const Map*m,const char*key,int*out){for(unsigned i=0;i<m->n;i++)if(!strcasecmp(m->slots[i].name,key)){*out=(int)m->slots[i].value;return 1;}return 0;}
static const void*stashFindPointerReturnPointerConst(const Map*m,const char*key){for(unsigned i=0;i<m->n;i++)if(!strcasecmp(m->slots[i].name,key))return(void*)m->slots[i].value;return NULL;}
#define eaSize(pp) (*(pp)?((Vec*)((char*)*(pp)-offsetof(Vec,items)))->size:0)
#define EAINRANGE(i,a) ((i)>=0&&(i)<eaSize(&(a)))
static void eaCreateWithCapacity(void*out,int cap){assert(cap>=0&&cap<8192);Vec*v=alloc(sizeof(Vec)+8192*sizeof(void*));*(void***)out=v->items;}
static void eaSetForced(void*out,const void*p,int i){assert(i>=0&&i<8192);Vec*v=(Vec*)((char*)*(void***)out-offse tof(Vec,items));if(i>=v->size)v->size=i+1;v->items[i]=(void*)p;}
static void eaCompressConst(void*out,void*in,void*a,void*b){(void)a;(void)b;*(void***)out=*(void***)in;}
static void eaDestroy(void*p){*(void***)p=NULL;}
#define customSharedMalloc NULL
'''.replace('offse tof','offsetof')
 code+=re.search(r'typedef struct TokenizerUiWidget\b.*?} TokenizerUiWidget;',src[EXTRA[2]],re.S).group()+'\n'
 macro=src[EXTRA[2]][src[EXTRA[2]].index('#define TOKENIZERUIWIDGET_INLINEPARSEINFO'):src[EXTRA[2]].index('\n\n\n#endif')];code+=macro+'\n'
 for name in ('ProfOriginType','ProfRarityType'):code+=re.search(r'typedef enum '+name+r'\s*\{.*?} '+name+';',src[EXTRA[1]],re.S).group()+'\n'
 code+='typedef struct {char*key;char*value;char*display;} StaticDefine;typedef struct {const char*key;intptr_t value;const char*display;}StaticDefineInt;\n#define DM_END 0\n#define DM_INT 1\n#define DM_STRING 2\n#define DM_DYNLIST 3\n#define DM_NOTYPE 4\n#define U32_TO_PTR(x) ((void*)(uintptr_t)(x))\n#define PTR_TO_S32(x) ((int)(intptr_t)(x))\n#define DEFINE_INT {(char*)U32_TO_PTR(DM_INT),0},\n#define DEFINE_END {(char*)U32_TO_PTR(DM_END),0},\n'
 for name in ('OriginEnum','RarityEnum'):code+=re.search(r'(?:static )?StaticDefineInt '+name+r'\[\]\s*=.*?\n};',src[EXTRA[0]],re.S).group()+'\n'

 code+=re.search(r'typedef struct ProficiencyItem\b.*?} ProficiencyItem;',src[EXTRA[1]],re.S).group()+'\n'+re.search(r'typedef struct ProficiencyDictionary\b.*?} ProficiencyDictionary;',src[EXTRA[1]],re.S).group()+'\n'
 code+='typedef struct {int id;char*name;}GenericInventoryType;typedef struct{const GenericInventoryType**ppItems;cStashTable haItemNames;const GenericInventoryType**itemsById;}GenericInvDictionary;\n'
 for name in ('AttribFileItem','AttribFileDict'):
  code+=re.search(r'typedef struct '+name+r'\s*\{.*?}\s*'+name+';',src[EXTRA[4]],re.S).group()+'\n'
 for path,names in ((EXTRA[0],('ParseProficiencyDef','ParseProficiencyDictionary')),(EXTRA[3],('ParseAttributeItem','ParseAttributeItems'))):
  for name in names:
   t=re.search(r'(?:static )?TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',src[path],re.S).group();tables[name]=sha(t.encode());code+='\n'+t
 code=code.replace('case TOK_END:return(Handler)','case TOK_START:case TOK_END:return(Handler)')
 code+='\n'+f(EXTRA[3],'attribfiledict_FinalProcess')+f(EXTRA[3],'genericinvdict_CreateHashes')+'\nstatic ProficiencyDictionary g_ProficiencyDict;\n'
 for name in ('proficiency_ValidId','proficiency_GetItem','proficiency_GetItemById'):code+=f(EXTRA[0],name)
 # Pin unexecuted map equality/overwrite and load/reward witnesses separately.
 witnesses={}
 for path,names in ((EXTRA[7],('stashAddValueInternal','stashAddPointerConst','stashAddIntConst','stashFindInt')),(EXTRA[5],('load_ProficiencyDictionary',)),(EXTRA[6],('rewarditemtype_NameFromId',))):
  for name in names:witnesses[path+':'+name]=sha(small.extract(src[path],name).encode())
 code+='''
int original_proficiencies(const unsigned char*defs,unsigned dn,unsigned dbegin,const unsigned char*ids,unsigned in,unsigned ibegin,unsigned*out,unsigned char*dr,unsigned char*ir){
 SimpleBuffer d={0},a={0},dw={0},iw={0};ProficiencyDictionary dict={0};AttribFileDict attrs={0};int sum=0;reset();assert(dn<=65536&&in<=65536);memcpy(d.data,defs,dn);d.filesize=dn;d.curposition=dbegin;memcpy(a.data,ids,in);a.filesize=in;a.curposition=ibegin;
 assert(ParserReadBinaryTable(&a,ParseAttributeItems,&attrs,&sum)&&a.curposition==(int)in);assert(ParserReadBinaryTable(&d,ParseProficiencyDictionary,&dict,&sum)&&d.curposition==(int)dn);
 Vec*dv=(Vec*)dict.ppProficiencyItems;Vec*av=(Vec*)attrs.ppAttribItems;if(!dv)dv=alloc(sizeof(Vec));if(!av)av=alloc(sizeof(Vec));dw.curposition=dw.filesize=dbegin;memcpy(dw.data,defs,dbegin);iw.curposition=iw.filesize=ibegin;memcpy(iw.data,ids,ibegin);assert(ParserWriteBinaryTable(&dw,ParseProficiencyDictionary,&dict,&sum,0,0)&&dw.filesize==(int)dn);assert(ParserWriteBinaryTable(&iw,ParseAttributeItems,&attrs,&sum,0,0)&&iw.filesize==(int)in);memcpy(dr,dw.data,dn);memcpy(ir,iw.data,in);
 dict.ppProficiencyItems=(const ProficiencyItem**)dv->items;attrs.ppAttribItems=(const AttribFileItem**)av->items;out[0]=attribfiledict_FinalProcess(NULL,&attrs,0);genericinvdict_CreateHashes((GenericInvDictionary*)&dict,&attrs,0);g_ProficiencyDict=dict;out[1]=attrs.maxId;out[2]=eaSize(&dict.itemsById);out[3]=dv->size;
 unsigned at=4;for(int i=0;i<dv->size;i++){ProficiencyItem*p=dv->items[i];out[at++]=p->id;out[at++]=proficiency_GetItem(p->name)==p;}
 for(int i=0;i<eaSize(&dict.itemsById);i++){const ProficiencyItem*p=dict.itemsById[i];unsigned row=0;if(p){assert(proficiency_GetItemById(i)==p);for(int j=0;j<dv->size;j++)if(dv->items[j]==p)row=j+1;}out[at++]=row;}
 for(int j=0;j<av->size;j++){const AttribFileItem*p=av->items[j];unsigned a=0,b=0;int id=0;if(stashFindInt(attrs.idHash,p->name,&id))for(int k=0;k<av->size;k++){const AttribFileItem*q=av->items[k];if(q->id>0&&!strcasecmp(q->name,p->name)){a=k+1;break;}}if(p->id>0)for(int k=0;k<av->size;k++)if(((const AttribFileItem*)av->items[k])->id==p->id){b=k+1;break;}out[at++]=a;out[at++]=b;}reset();return at;
}
'''
 crc=module('proficiency_crc',HERE/'../costume-tree/crc_provider.py');crc_code,crcproof=crc.generate(root,(root/'upstream/ouroboros'/small.PATHS[5]).read_text(),small.extract)
 crc_code=crc_code[:crc_code.index('unsigned original_tree_crc(')].replace('static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(0);}', 'static void UpdateCrcFromStaticDefines(StaticDefine[]);').replace('case TOK_END:return(CrcHandler)', 'case TOK_START:case TOK_END:return(CrcHandler)')
 actual=small.extract((root/'upstream/ouroboros'/small.PATHS[5]).read_text(),'UpdateCrcFromStaticDefines');functions[small.PATHS[5]+':UpdateCrcFromStaticDefines']=sha(actual.encode())
 code+='\n'+crc_code+'\n'+actual+'\nunsigned original_proficiency_crc(unsigned kind){return(U32)ParseTableCRC(kind?ParseAttributeItems:ParseProficiencyDictionary,NULL); }\n'
 (work/'original-proficiencies.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'original-proficiencies.c','-lz','-o',work/'original-proficiencies.so'],check=True)
 lib=C.CDLL(str(work/'original-proficiencies.so'));lib.original_proficiencies.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p]
 return lib,{'binary_provider':proof,'crc':crcproof,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'whole_function_sha256_lf':functions,'tables_sha256_lf':tables,'unexecuted_source_witnesses_sha256_lf':witnesses,'generated_c_sha256':sha(code.encode()),'storage_adapters':'bounded TokenStore/earray/default ASCII case-insensitive first-wins maps; no original stash allocation/hash engine execution','shared_memory_branch_executed':False,'original_oracle_sanitized':False}

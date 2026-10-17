"""Original power-set binary schema/CRC prototype; no runtime owner admission."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/powers.h','Common/entity/powers_load.c','Common/entity/power_system.h','Common/entity/power_system.c','libs/UtilitiesLib/include/utilitieslib/utils/structDefines.h','libs/UtilitiesLib/src/utils/textparser.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 classes=module('pset_classes',HERE/'classes_oracle.py');classes.module=module;small=module('pset_small',HERE/'../costume-inputs/oracle.py');cw=work/'classes';cw.mkdir();_,proof=classes.build(root,cw);code=(cw/'original-classes.c').read_text().replace('void*items[256]','void*items[]');capacity=small.extract(code,'TokenStoreSetCapacity');code=code.replace(capacity,'static void TokenStoreSetCapacity(ParseTable*t,int c,void*p,int n){assert(n>=0&&n<=8192);Vec*v=alloc(sizeof(*v)+(size_t)n*sizeof(void*));v->size=n;*(void**)field(t,c,p)=v;}');src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};header=src[EXTRA[0]];defs=src[EXTRA[4]];definitions=defs[defs.index('typedef struct DefineList'):defs.index('DefineContext* DefineCreate();')]+defs[defs.index('#define DM_END'):defs.index('// all lookups')];code=code.replace('typedef void DefineContext;','typedef struct DefineContext DefineContext;\n#define U32_TO_PTR(v) ((void*)(uintptr_t)(U32)(v))\n#define PTR_TO_S32(v) ((int32_t)(intptr_t)(v))\n'+definitions);code=code.replace('static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(0);}','static void UpdateCrcFromStaticDefines(StaticDefine*);');functions={}
 body=small.extract(src[EXTRA[5]],'UpdateCrcFromStaticDefines');functions['UpdateCrcFromStaticDefines']=sha(body.encode());code+='\n'+body
 boolenum=re.search(r'StaticDefineInt BoolEnum\[\]\s*=.*?\n};',src[EXTRA[1]],re.S).group();code=code.replace('static ParseTable*ParsePowerDefines[1];static ParseTable*BoolEnum[1];','static ParseTable*ParsePowerDefines[1];\n'+boolenum)
 code+='\n'+re.search(r'typedef enum PowerSystem\s*\{.*?} PowerSystem;',src[EXTRA[2]],re.S).group()+'\n'+re.search(r'typedef enum ShowPowerSetting\s*\{.*?} ShowPowerSetting;',header,re.S).group()
 for name,path in [('PowerSystemEnum',EXTRA[3]),('ShowPowerSettingEnum',EXTRA[1])]:code+='\n'+re.search(r'StaticDefineInt '+name+r'\[\]\s*=.*?\n};',src[path],re.S).group()
 code+='\ntypedef struct BasePower BasePower;typedef struct BasePowerSet BasePowerSet;\n#define TOK_AUTOINTEARRAY(s,m) TOK_EARRAY|TOK_INT_X,offsetof(s,m),0\n'
 for name in('PowerCategory','PowerDictionary','BasePowerSet'):
  decl=re.search(r'typedef struct '+name+r'\s*\{.*?} '+name+';',header,re.S).group()
  if name=='PowerCategory':decl=decl.replace('const BasePowerSet **ppPowerSets;','uint32_t *ppPowerSets;')
  if name=='BasePowerSet':decl=decl.replace('const BasePower **ppPowers;','uint32_t *ppPowers;')
  code+='\n'+decl
 tables={}
 for name in('ParseBasePowerSet','ParsePowerSetDictionary'):
  body=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',src[EXTRA[1]],re.S).group();tables[name]=sha(body.encode());code+='\n'+body
 code=code.replace('case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:return(CrcHandler)','case TOK_BOOL_X:case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:return(CrcHandler)')
 code+='''
unsigned original_sets_crc(void){return ParseTableCRC(ParsePowerSetDictionary,NULL);}
unsigned original_sets_tree(const unsigned char*input,unsigned size,unsigned begin,unsigned char*out,unsigned*counts,unsigned scenario){assert(size<=8388608);SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr);reset();memcpy(in->data,input,size);in->filesize=size;in->curposition=begin;PowerDictionary data={0};int sum=0;assert(ParserReadBinaryTable(in,ParsePowerSetDictionary,&data,&sum)&&in->curposition==(int)size);Vec*v=(Vec*)data.ppPowerSets;if(scenario){assert(scenario<=7&&v&&v->size);BasePowerSet*first=v->items[0];if(scenario==1)first->pchFullName="Unknown_Set.Unique";if(scenario==2)((BasePowerSet*)v->items[v->size-1])->pchFullName=first->pchFullName;if(scenario==3)v->size=0;if(scenario==4){unsigned i=0;while(i<(unsigned)v->size){BasePowerSet*set=v->items[i];Vec*n=(Vec*)set->ppPowerNames;if(n&&n->size){n->items[0]="Unknown_Power.Name";break;}i++;}assert(i<(unsigned)v->size);}if(scenario==5){Vec*n=alloc(sizeof(*n)+3*sizeof(void*));n->size=3;n->items[0]=NULL;n->items[1]=(void*)(uintptr_t)1;n->items[2]=(void*)(uintptr_t)0xffffffff;first->ppPowers=(uint32_t*)n;}if(scenario==6)first->pchFullName="";if(scenario==7)first->eSystem=-1;}counts[0]=v?v->size:0;counts[1]=counts[2]=0;for(unsigned i=0;v&&i<(unsigned)v->size;i++){BasePowerSet*s=v->items[i];Vec*n=(Vec*)s->ppPowerNames,*indices=(Vec*)s->ppPowers;counts[1]+=n?n->size:0;counts[2]+=indices?indices->size:0;}memcpy(wr->data,input,begin);wr->curposition=wr->filesize=begin;sum=0;assert(ParserWriteBinaryTable(wr,ParsePowerSetDictionary,&data,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);reset();free(in);free(wr);return n;}
'''
 (work/'sets.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'sets.c','-lz','-o',work/'sets.so'],check=True);lib=C.CDLL(str(work/'sets.so'));lib.original_sets_tree.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_uint]
 return lib,{'class_provider':proof,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'tables_sha256_lf':tables,'function_sha256_lf':functions,'generated_c_sha256':sha(code.encode()),'runtime_generation':False}

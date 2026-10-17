"""Original power-category binary schema probe; excludes power/set construction."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/powers.h','Common/entity/powers_load.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 classes=module('pcat_classes',HERE/'classes_oracle.py');classes.module=module;cw=work/'classes';cw.mkdir();_,proof=classes.build(root,cw);code=(cw/'original-classes.c').read_text().replace('void*items[256]','void*items[4096]').replace('n<=256','n<=4096');src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};header=src[EXTRA[0]];code+='\ntypedef struct BasePower BasePower;typedef struct BasePowerSet BasePowerSet;\n#define TOK_AUTOINTEARRAY(s,m) TOK_EARRAY|TOK_INT_X,offsetof(s,m),0\n'
 for name in('PowerCategory','PowerDictionary'):
  decl=re.search(r'typedef struct '+name+r'\s*\{.*?} '+name+';',header,re.S).group()
  # Persisted pointer array contains original donor32-bit indices, not pointers.
  if name=='PowerCategory':decl=decl.replace('const BasePowerSet **ppPowerSets;','uint32_t *ppPowerSets;')
  code+='\n'+decl
 tables={}
 for name in('ParsePowerCategory','ParsePowerCatDictionary'):
  body=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',src[EXTRA[1]],re.S).group();tables[name]=sha(body.encode());code+='\n'+body
 code=code.replace('case TOK_START:case TOK_END:return(Handler)','case TOK_IGNORE:case TOK_START:case TOK_END:return(Handler)').replace('case TOK_START:case TOK_END:return(CrcHandler)','case TOK_IGNORE:case TOK_START:case TOK_END:return(CrcHandler)')
 code+='''
unsigned original_category_crc(void){return ParseTableCRC(ParsePowerCatDictionary,NULL);}
unsigned original_category_tree(const unsigned char*input,unsigned size,unsigned begin,unsigned char*out,unsigned*counts,unsigned scenario){SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr&&size<=1048576);PowerDictionary data={0};int sum=0;reset();memcpy(in->data,input,size);in->filesize=size;in->curposition=begin;assert(ParserReadBinaryTable(in,ParsePowerCatDictionary,&data,&sum)&&in->curposition==(int)size);Vec*v=(Vec*)data.ppPowerCategories;if(scenario){assert(scenario<=7&&v&&v->size);PowerCategory*first=v->items[0];if(scenario==1)first->pchName="Unknown_Category";if(scenario==2)((PowerCategory*)v->items[v->size-1])->pchName=first->pchName;if(scenario==3)v->size=0;if(scenario==4){unsigned i=0;while(i<(unsigned)v->size){PowerCategory*c=v->items[i];Vec*n=(Vec*)c->ppPowerSetNames;if(n&&n->size){n->items[0]="Unknown_Set.Reference";break;}i++;}assert(i<(unsigned)v->size);}if(scenario==5){Vec*n=alloc(sizeof(*n));n->size=3;n->items[0]=NULL;n->items[1]=(void*)(uintptr_t)1;n->items[2]=(void*)(uintptr_t)0xffffffffu;first->ppPowerSets=(uint32_t*)n;}if(scenario==6)first->pchName="unknown_category";if(scenario==7){first->pchSourceFile="";first->pchName="CountOnly";first->pchDisplayName="";first->pchDisplayHelp="";first->pchDisplayShortHelp="";first->ppPowerSetNames=NULL;first->ppPowerSets=NULL;v->size=257;for(unsigned i=0;i<257;i++)v->items[i]=first;}}counts[0]=v?v->size:0;counts[1]=counts[2]=0;for(int i=0;v&&i<v->size;i++){PowerCategory*c=v->items[i];Vec*n=(Vec*)c->ppPowerSetNames,*p=(Vec*)c->ppPowerSets;counts[1]+=n?n->size:0;counts[2]+=p?p->size:0;}memcpy(wr->data,input,begin);wr->curposition=wr->filesize=begin;sum=0;assert(ParserWriteBinaryTable(wr,ParsePowerCatDictionary,&data,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);free(in);free(wr);reset();return n;}
'''
 (work/'categories.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'categories.c','-lz','-o',work/'categories.so'],check=True);lib=C.CDLL(str(work/'categories.so'));lib.original_category_tree.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_uint]
 return lib,{'class_provider':proof,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'tables_sha256_lf':tables,'generated_c_sha256':sha(code.encode()),'persisted_pointer_index_width':32,'runtime_powerset_power_dictionary':False}

"""Whole original class repack/transpose with explicit pointer/heap interfaces."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/classes.c','Common/entity/character_attribs.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 prior=module('repack_classes',HERE/'classes_oracle.py');prior.module=module;small=module('repack_extract',HERE/'../costume-inputs/oracle.py');cw=work/'classes';cw.mkdir();_,proof=prior.build(root,cw);code=(cw/'original-classes.c').read_text();src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};functions={}
 def f(path,name):
  b=small.extract(src[path],name);functions[path+':'+name]=sha(b.encode());return b
 code+='''
#undef bool
#define cpp_const_cast(t)
static void*ParserAllocStruct(size_t n){return alloc(n);}
typedef struct{unsigned count;float values[];} FloatValues;
#define eafSize(pp) (*(pp)?((FloatValues*)((char*)*(pp)-offsetof(FloatValues,values)))->count:0)
static void eaCreate(void***pp){Vec*v=alloc(sizeof(*v));*pp=v->items;}
static void eaPushConst(const void*pp,const void*x){Vec*v=(Vec*)((char*)*(void***)pp - offsetof(Vec,items));assert(v->size<256);v->items[v->size++]=(void*)x;}
struct PowerCategory {const char*name;};
struct PowerDictionary {unsigned count;PowerCategory categories[256];};
static const PowerCategory*powerdict_GetCategoryByName(const PowerDictionary*d,const char*name){for(unsigned i=0;i<d->count;i++)if(!strcasecmp(d->categories[i].name,name))return &d->categories[i];return NULL;}
/* This callback records retirement only; all parser allocations are released by
 * fixture reset after output. It does not claim original parser allocator ABI. */
static unsigned retired;
static void ParserDestroyStruct(ParseTable*t,void*p){(void)t;(void)p;retired++;}
'''
 destroy=re.search(r'TokenizerParseInfo DestroyUnusedCharacterAttributeTable\[\].*?\n};',src[EXTRA[0]],re.S).group();code+='\n'+destroy
 code+='\n'+f(EXTRA[1],'TransposeArray')+'\n#define TRANSPOSE_ARRAY(attrib) TransposeArray(pptab[0]->p##attrib, pattr, (int)offsetof(CharacterAttributes, attrib), iNum, fDefault)\n'+f(EXTRA[1],'CreateCharacterAttributes')+'\n'+f(EXTRA[0],'classes_Repack')
 code+='''
static void fix_repack_fields(CharacterClass*c){
 const CharacterAttributes***scalar[]={&c->ppattrMin,&c->ppattrBase,&c->ppattrStrengthMin,&c->ppattrResistanceMin};
 for(unsigned i=0;i<4;i++){Vec*v=(Vec*)*scalar[i];*scalar[i]=v?(const CharacterAttributes**)v->items:NULL;}
 const CharacterAttributesTable***tables[]={&c->ppTempAttribMax,&c->ppTempAttribMaxMax,&c->ppTempStrengthMax,&c->ppTempResistanceMax};
 for(unsigned i=0;i<4;i++){Vec*v=(Vec*)*tables[i];assert(v&&v->size==1);*tables[i]=(const CharacterAttributesTable**)v->items;CharacterAttributesTable*t=v->items[0];assert(sizeof(*t)==115*sizeof(void*));for(unsigned j=0;j<115;j++){Vec*values=((Vec**)t)[j];FloatValues*flat=alloc(sizeof(*flat)+(values?values->size:0)*sizeof(float));flat->count=values?values->size:0;for(unsigned k=0;k<flat->count;k++){U32 w=(U32)(uintptr_t)values->items[k];memcpy(flat->values+k,&w,4);}((float**)t)[j]=flat->values;}}
}
unsigned original_class_repack(const unsigned char*bytes,unsigned size,unsigned begin,unsigned which,unsigned level,unsigned scenario,const char*const*categories,unsigned category_count,unsigned*out,unsigned*meta){
 assert(size<=8388608&&category_count<=256);SimpleBuffer*in=calloc(1,sizeof(*in));assert(in);reset();memcpy(in->data,bytes,size);in->filesize=size;in->curposition=begin;CharacterClasses list={0};int sum=0;assert(ParserReadBinaryTable(in,ParseCharacterClasses,&list,&sum)&&in->curposition==(int)size);Vec*v=(Vec*)list.ppClasses;assert(v&&which<(unsigned)v->size);list.ppClasses=(const CharacterClass**)v->items;
 for(unsigned i=0;i<(unsigned)v->size;i++)fix_repack_fields(v->items[i]);CharacterClass*c=v->items[which];if(scenario){assert(scenario<=2);c->ppattrStrengthMin=NULL;if(scenario==2)c->ppattrResistanceMin=NULL;}
 PowerDictionary dict={0};dict.count=category_count;for(unsigned i=0;i<category_count;i++)dict.categories[i].name=categories[i];retired=0;classes_Repack(&list,&dict);assert(retired==(unsigned)v->size&&sizeof(CharacterAttributes)==460);meta[0]=c->iNumLevels;meta[1]=c->iNumBytesTables;meta[2]=retired;for(unsigned i=0;i<4;i++)meta[3+i]=(unsigned)(c->pcat[i]-dict.categories);unsigned ok=level<(unsigned)c->iNumLevels;if(ok){const CharacterAttributes*t[]={c->pattrMax,c->pattrMaxMax,c->pattrStrengthMax,c->pattrResistanceMax,c->ppattrStrengthMin[0],c->ppattrResistanceMin[0]};for(unsigned i=0;i<6;i++)memcpy(out+115*i,t[i]+(i<4?level:0),460);}reset();free(in);return ok;}
'''
 code+=r"""
unsigned original_repack_variant(const unsigned char*bytes,unsigned size,unsigned begin,unsigned scenario,unsigned char*out){
 assert(scenario>=1&&scenario<=3);SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr&&size<=8388608);reset();memcpy(in->data,bytes,size);in->filesize=size;in->curposition=begin;CharacterClasses list={0};int sum=0;assert(ParserReadBinaryTable(in,ParseCharacterClasses,&list,&sum)&&in->curposition==(int)size);Vec*v=(Vec*)list.ppClasses;assert(v&&v->size);CharacterClass*c=v->items[0];c->ppattrStrengthMin=NULL;if(scenario>=2){c->ppattrResistanceMin=NULL;Vec*t=(Vec*)c->ppTempAttribMax;assert(t&&t->size==1);CharacterAttributesTable*a=t->items[0];a->pfDamageType[0]=NULL;Vec*h=(Vec*)a->pfHitPoints;assert(h&&h->size);h->size=1;}if(scenario==3){c->pchTempCategory[2]=NULL;c->pchTempCategory[3]=NULL;}memcpy(wr->data,bytes,begin);wr->curposition=wr->filesize=begin;sum=0;assert(ParserWriteBinaryTable(wr,ParseCharacterClasses,&list,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);reset();free(in);free(wr);return n;}
"""
 for qualified,h in functions.items():assert sha(small.extract(code,qualified.rsplit(':',1)[1]).encode())==h
 (work/'repack.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'repack.c','-lz','-o',work/'repack.so'],check=True);lib=C.CDLL(str(work/'repack.so'));lib.original_class_repack.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_void_p]
 lib.original_repack_variant.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p]
 return lib,{'classes_provider':proof,'whole_functions_sha256_lf':functions,'retirement_schema_sha256_lf':sha(destroy.encode()),'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'generated_c_sha256':sha(code.encode()),'original_category_lookup_executed':False,'original_parser_retirement_executed':False,'runtime_generation':False}

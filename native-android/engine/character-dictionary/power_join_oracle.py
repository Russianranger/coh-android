"""Whole original forward/backpointer functions on compact fixture objects.

Lookup arrays/heap/earray storage are explicit fixture adapters. Original source
lookup/fullname/hash functions execute; the previously source-qualified raw index
constructors are not repeated and no original cache startup is claimed.
"""
import ctypes as C,hashlib,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['Common/entity/powers_load.c','Common/entity/powers.c','libs/UtilitiesLib/src/network/crc32c.cpp']
def extract(text,name):
 m=re.search(r'(?m)^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;]*?\)\s*\{',text);assert m,name
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def sha(b):return hashlib.sha256(b).hexdigest()
def build(root,work):
 texts={p:subprocess.check_output(['git','-C',root,'show','HEAD:upstream/ouroboros/'+p]).decode().replace('\r\n','\n')for p in PATHS};functions={}
 code=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stddef.h>
#include <assert.h>
#include <ctype.h>
#include <alloca.h>
typedef uint32_t U32;typedef uint8_t U8;typedef int bool;
#define false 0
#define true 1
#define _alloca alloca
#define cpp_const_cast(t)
typedef struct BasePower BasePower;typedef struct BasePowerSet BasePowerSet;typedef struct PowerCategory PowerCategory;
typedef struct AttribModTemplate {BasePower*ppowBase;int ppowBaseIndex;} AttribModTemplate;
struct BasePower {const char*pchFullName,*pchName,*pchSourceFile;BasePowerSet*psetParent;const AttribModTemplate**ppTemplates;};
struct BasePowerSet {const char*pchFullName,*pchSourceFile;const char**ppPowerNames;const BasePower**ppPowers;PowerCategory*pcatParent;};
struct PowerCategory {const char*pchName,*pchSourceFile;const char**ppPowerSetNames;const BasePowerSet**ppPowerSets;};
typedef struct {const PowerCategory**ppPowerCategories;const BasePowerSet**ppPowerSets;const BasePower**ppPowers;void*haSetNames,*haPowerCRCs;} PowerDictionary;
typedef struct {unsigned n,cap;void*items[];} V;
static int eaSize(const void*array){const void*const*a=*(const void*const*const*)array;return a?((const V*)((const char*)a-sizeof(V)))->n:0;}
static void eaSetSizeConst(void*array,int n){void**a=*(void***)array;assert(n==0);if(a)((V*)((char*)a-sizeof(V)))->n=0;}
static void eaPushConst(void*array,const void*value){void***ptr=array;V*v=*ptr?(V*)((char*)*ptr-sizeof(V)):NULL;if(!v||v->n==v->cap){unsigned cap=v?v->cap*2:4;v=realloc(v,sizeof(V)+(size_t)cap*sizeof(void*));assert(v);if(!*ptr)v->n=0;v->cap=cap;*ptr=v->items;}v->items[v->n++]=(void*)value;}
static unsigned source_errors;static U32*powerkeys;
static void ErrorFilenamef(const char*path,const char*fmt,...){(void)path;(void)fmt;source_errors++;}
static void Errorf(const char*fmt,...){(void)fmt;source_errors++;}
/* Lookup adapters retain first source array winner, as independently qualified
 * CreateDictHashes/stash owners do. No live hash construction runs here. */
static const void*stashFindPointerReturnPointerConst(const void*context,const char*name){const PowerDictionary*d=context;for(int i=0;i<eaSize(&d->ppPowerSets);i++)if(!strcasecmp(name,d->ppPowerSets[i]->pchFullName))return d->ppPowerSets[i];return NULL;}
'''
 crc=texts[PATHS[2]];code+='\n'+re.search(r'static const U32 s_crc32c\[0x100\].*?\n};',crc,re.S).group()
 def f(path,name):
  body=extract(texts[path],name);functions[path+':'+name]=sha(body.encode());return body
 for name in ('Crc32c_cpu','Crc32c','Crc32cLowerStringHash'):code+='\n'+f(PATHS[2],name)
 code+='\n'+f(PATHS[1],'powerdict_GetCRCOfBasePower')
 code+='\nstatic bool stashIntFindPointerConst(const void*context,int crc,const void*out){const PowerDictionary*d=context;for(int i=0;i<eaSize(&d->ppPowers);i++)if(powerkeys[i]==(U32)crc){*(const BasePower**)out=d->ppPowers[i];return true;}return false;}\n'
 for name in ('powerdict_GetBasePowerSetByFullNameEx','powerdict_GetBasePowerSetByFullName','powerdict_GetBasePowerByCRCEx','powerdict_GetBasePowerByFullNameEx','powerdict_GetBasePowerByFullName'):code+='\n'+f(PATHS[1],name)
 for name in ('powerdict_SetForwardPointers','powerdict_SetBackPointers'):code+='\n'+f(PATHS[0],name)
 code+=r'''
typedef struct {const char*name;unsigned n;const char**refs;} CatSpec;
typedef struct {const char*name;unsigned n;const char**refs;} SetSpec;
typedef struct {const char*name,*short_name;} PowSpec;
static unsigned set_index(PowerDictionary*d,const BasePowerSet*p){if(!p)return UINT32_MAX;for(unsigned i=0;i<(unsigned)eaSize(&d->ppPowerSets);i++)if(d->ppPowerSets[i]==p)return i;assert(0);return 0;}
static unsigned pow_index(PowerDictionary*d,const BasePower*p){if(!p)return UINT32_MAX;for(unsigned i=0;i<(unsigned)eaSize(&d->ppPowers);i++)if(d->ppPowers[i]==p)return i;assert(0);return 0;}
static unsigned cat_index(PowerDictionary*d,const PowerCategory*p){if(!p)return UINT32_MAX;for(unsigned i=0;i<(unsigned)eaSize(&d->ppPowerCategories);i++)if(d->ppPowerCategories[i]==p)return i;assert(0);return 0;}
static void free_array(const void*a){if(a)free((char*)a-sizeof(V));}
unsigned original_join(const CatSpec*cats,unsigned nc,const SetSpec*sets,unsigned ns,const PowSpec*pows,unsigned np,unsigned*category_sets,unsigned*set_counts,unsigned*power_refs,unsigned*set_parents,unsigned*power_parents,unsigned*stats){
 PowerDictionary d={0};source_errors=0;
 for(unsigned i=0;i<np;i++){BasePower*p=calloc(1,sizeof(*p));assert(p);p->pchFullName=pows[i].name;p->pchName=pows[i].short_name;p->pchSourceFile="fixture";/* Nonempty template lists execute the entire source inner backpointer loop. */for(unsigned j=0;j<2;j++){AttribModTemplate*m=calloc(1,sizeof(*m));assert(m);eaPushConst(&p->ppTemplates,m);}eaPushConst(&d.ppPowers,p);}
 for(unsigned i=0;i<ns;i++){BasePowerSet*s=calloc(1,sizeof(*s));assert(s);s->pchFullName=sets[i].name;s->pchSourceFile="fixture";for(unsigned j=0;j<sets[i].n;j++)eaPushConst(&s->ppPowerNames,sets[i].refs[j]);eaPushConst(&d.ppPowerSets,s);}
 for(unsigned i=0;i<nc;i++){PowerCategory*c=calloc(1,sizeof(*c));assert(c);c->pchName=cats[i].name;c->pchSourceFile="fixture";for(unsigned j=0;j<cats[i].n;j++)eaPushConst(&c->ppPowerSetNames,cats[i].refs[j]);eaPushConst(&d.ppPowerCategories,c);}
 powerkeys=calloc(np?np:1,sizeof(*powerkeys));assert(powerkeys);for(unsigned i=0;i<np;i++)powerkeys[i]=powerdict_GetCRCOfBasePower(d.ppPowers[i]);d.haSetNames=d.haPowerCRCs=&d;powerdict_SetForwardPointers(&d);powerdict_SetBackPointers(&d);unsigned ci=0,pi=0,mods=0;
 for(unsigned i=0;i<nc;i++){const PowerCategory*c=d.ppPowerCategories[i];for(int j=0;j<eaSize(&c->ppPowerSets);j++)category_sets[ci++]=set_index(&d,c->ppPowerSets[j]);}
 for(unsigned i=0;i<ns;i++){const BasePowerSet*s=d.ppPowerSets[i];set_counts[i]=eaSize(&s->ppPowers);set_parents[i]=cat_index(&d,s->pcatParent);for(unsigned j=0;j<set_counts[i];j++)power_refs[pi++]=pow_index(&d,s->ppPowers[j]);}
 for(unsigned i=0;i<np;i++){const BasePower*p=d.ppPowers[i];power_parents[i]=set_index(&d,p->psetParent);for(int j=0;j<eaSize(&p->ppTemplates);j++){const AttribModTemplate*m=p->ppTemplates[j];if(p->psetParent){assert(m->ppowBase==p&&m->ppowBaseIndex==j);mods++;}else assert(!m->ppowBase&&!m->ppowBaseIndex);free((void*)m);}free_array(p->ppTemplates);free((void*)p);}
 for(unsigned i=0;i<ns;i++){const BasePowerSet*s=d.ppPowerSets[i];free_array(s->ppPowerNames);free_array(s->ppPowers);free((void*)s);}
 for(unsigned i=0;i<nc;i++){const PowerCategory*c=d.ppPowerCategories[i];free_array(c->ppPowerSetNames);free_array(c->ppPowerSets);free((void*)c);}
 free(powerkeys);powerkeys=NULL;free_array(d.ppPowerCategories);free_array(d.ppPowerSets);free_array(d.ppPowers);stats[0]=source_errors;stats[1]=ci;stats[2]=pi;stats[3]=mods;return source_errors==0;
}
'''
 for qualified,pin in functions.items():assert sha(extract(code,qualified.split(':')[-1]).encode())==pin
 path=work/'power-join-original.c';path.write_text(code);subprocess.run(['cc','-std=gnu99','-O2','-shared','-fPIC','-w',path,'-o',work/'power-join-original.so'],check=True)
 lib=C.CDLL(str(work/'power-join-original.so'));lib.original_join.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]+[C.c_void_p]*6
 return lib,{'whole_function_sha256_lf':functions,'source_sha256_lf':{p:sha(t.encode())for p,t in texts.items()},'generated_c_sha256':sha(code.encode()),'lookup_adapter':'first-array-winner; original stash/index constructors separately qualified, not executed here','earray_heap_adapter':True,'compact_fixture_objects':True,'live_cache_startup':False}

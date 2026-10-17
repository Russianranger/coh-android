"""Whole original FinalizeDict/SetID/sort and source sorted backpointer order."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['Common/entity/powers_load.c','Common/entity/powers.c','Common/entity/powers.h','libs/UtilitiesLib/src/utils/textparser.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 m=types.ModuleType(name);m.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
def build(root,work):
 prior=module('ids_prior',HERE/'power_join_oracle.py');before=work/'join';before.mkdir();_,proof=prior.build(root,before);code=(before/'power-join-original.c').read_text();functions={};declarations={};texts={p:subprocess.check_output(['git','-C',root,'show','HEAD:upstream/ouroboros/'+p]).decode().replace('\r\n','\n')for p in PATHS}
 def f(path,name):
  body=prior.extract(texts[path],name);functions[path+':'+name]=sha(body.encode());return body
 structs=''
 for name in ('BasePowerID','PowerStats'):
  body=re.search(r'typedef struct '+name+r'\s*\{.*?} '+name+';',texts[PATHS[2]],re.S).group();declarations[name]=sha(body.encode());structs+='\n'+body
 structs+='''
typedef struct {int iFramesBeforeHit,iInitialFramesBeforeHit,iFramesBeforeBlock,iInitialFramesBeforeBlock,iFramesAttack;float fTimeToHit,fInitialTimeToHit,fTimeToBlock,fInitialTimeToBlock;} PowerFX;
typedef struct {PowerFX fx;} PowerCustomFX;
'''
 code=code.replace('struct BasePower {',structs+'\nstruct BasePower {').replace('const AttribModTemplate**ppTemplates;','const AttribModTemplate**ppTemplates;BasePowerID id;PowerStats stats;PowerFX fx;const PowerCustomFX**customfx;float fTimeToActivate;').replace('const char*pchFullName,*pchSourceFile;const char**ppPowerNames;','const char*pchFullName,*pchSourceFile,*pchName;const char**ppPowerNames;')
 at=code.index('unsigned original_join(');wrapper=code[at:];code=code[:at]
 code+='''
typedef float F32;
typedef struct {int bDefault;} DimReturnSet;
static const DimReturnSet*pDimSetDefault;
static DimReturnSet fixture_default={1};
static struct {const DimReturnSet**ppSets;} g_DimReturnList;
static int artTestPowerLoaded;
static BasePower artTestPower;
static int isDevelopmentMode(void){return 0;}
#define stricmp strcasecmp
static void eaQSortConst(const void*array,int(*compare)(const void*,const void*)){void**a=(void**)array;if(a)qsort(a,((V*)((char*)a-sizeof(V)))->n,sizeof(void*),compare);}
'''
 for path,name in [(PATHS[1],'basepower_SetID'),(PATHS[1],'powerdict_ResetStats'),(PATHS[0],'powerdict_FinalizeDictFx'),(PATHS[0],'powerdict_compareCategories'),(PATHS[0],'powerdict_FinalizeDict')]:code+='\n'+f(path,name)
 wrapper=wrapper.replace('unsigned original_join(','unsigned original_ids(').replace('unsigned*stats){','unsigned*stats,unsigned*ids,unsigned*sorted){').replace('s->pchSourceFile="fixture";','s->pchSourceFile="fixture";s->pchName="fixture";').replace('powerdict_SetForwardPointers(&d);powerdict_SetBackPointers(&d);','powerdict_SetForwardPointers(&d);eaPushConst(&g_DimReturnList.ppSets,&fixture_default);powerdict_FinalizeDict(&d);assert(pDimSetDefault==&fixture_default);powerdict_SetBackPointers(&d);')
 # Capture sorted raw ordinals before fixture cleanup; final source category
 # array has been reordered while original CatSpec storage is unchanged.
 wrapper=wrapper.replace('for(unsigned i=0;i<nc;i++){const PowerCategory*c=d.ppPowerCategories[i];for(int j=0;', 'for(unsigned i=0;i<nc;i++){const PowerCategory*c=d.ppPowerCategories[i];unsigned raw=0;while(raw<nc&&strcmp(c->pchName,cats[raw].name))raw++;assert(raw<nc);sorted[i]=raw;for(int j=0;')
 wrapper=wrapper.replace('p->pchSourceFile="fixture";', 'p->pchSourceFile="fixture";memset(&p->stats,0x5a,sizeof(p->stats));p->fx.iFramesBeforeHit=14;p->fx.iInitialFramesBeforeHit=17;p->fx.iFramesBeforeBlock=28;p->fx.iInitialFramesBeforeBlock=37;for(unsigned j=0;j<2;j++){PowerCustomFX*fx=calloc(1,sizeof(*fx));assert(fx);fx->fx=p->fx;eaPushConst(&p->customfx,fx);}')
 wrapper=wrapper.replace('free_array(p->ppTemplates);', 'if(p->psetParent){assert(p->fx.fTimeToHit==14/30.0f&&p->fx.fInitialTimeToHit==17/30.0f&&p->fx.fTimeToBlock==28/30.0f&&p->fx.fInitialTimeToBlock==37/30.0f);}for(int j=0;j<eaSize(&p->customfx);j++){const PowerCustomFX*fx=p->customfx[j];if(p->psetParent)assert(fx->fx.fTimeToHit==14/30.0f&&fx->fx.fInitialTimeToHit==17/30.0f&&fx->fx.fTimeToBlock==28/30.0f&&fx->fx.fInitialTimeToBlock==37/30.0f);free((void*)fx);}free_array(p->customfx);free_array(p->ppTemplates);')
 wrapper=wrapper.replace('power_parents[i]=set_index(&d,p->psetParent);','power_parents[i]=set_index(&d,p->psetParent);ids[3*i]=p->id.icat;ids[3*i+1]=p->id.iset;ids[3*i+2]=p->id.ipow;if(p->psetParent){assert(p->stats.fDamageGiven==0&&p->stats.fHealingGiven==0&&!p->stats.iCntUsed&&!p->stats.iCntHits&&!p->stats.iCntMisses);}else{for(unsigned k=0;k<sizeof(p->stats);k++)assert(((const unsigned char*)&p->stats)[k]==0x5a);}')
 wrapper=wrapper.replace('free(powerkeys);powerkeys=NULL;','free_array(g_DimReturnList.ppSets);g_DimReturnList.ppSets=NULL;free(powerkeys);powerkeys=NULL;')
 code+=wrapper
 for key,pin in functions.items():assert sha(prior.extract(code,key.rsplit(':',1)[1]).encode())==pin
 path=work/'power-ids-original.c';path.write_text(code);subprocess.run(['cc','-std=gnu99','-O2','-shared','-fPIC','-w',path,'-o',work/'power-ids-original.so'],check=True);lib=C.CDLL(str(work/'power-ids-original.so'));lib.original_ids.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]+[C.c_void_p]*8
 loader=prior.extract(texts[PATHS[3]],'ParserLoadFiles');cache=loader.index('if (ParserReadBinaryFile(');early=loader.index('return 1;',cache);preprocess=loader.index('if (preprocessor)');assert cache<early<preprocess
 return lib,{'prior_forward_fixture':proof,'whole_function_sha256_lf':functions,'declaration_sha256_lf':declarations,'generated_c_sha256':sha(code.encode()),'source_sha256_lf':{p:sha(t.encode())for p,t in texts.items()},'loader_branch_audit':{'whole_ParserLoadFiles_sha256_lf':sha(loader.encode()),'cache_hit_return_precedes_preprocessing':True,'text_rebuild_callback_not_executed_here':True,'actual_runtime_branch_witness':False},'explicit_fixtures':{'diminishing_return_default':True,'no_development_art_override':True,'nonzero_synthetic_normal_and_custom_FX_not_authentic_fx_finalization':True,'earray_sort_storage_adapter':True},'complete_FinalizePower':False,'runtime_generation':False}

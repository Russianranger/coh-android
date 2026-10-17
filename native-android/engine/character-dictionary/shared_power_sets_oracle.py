"""Original source FindSharedPowersets on the finalized compact fixture hierarchy."""
import ctypes as C,hashlib,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['Common/entity/powers_load.c','libs/UtilitiesLib/src/utils/textparser.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 m=types.ModuleType(name);m.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
def build(root,work):
 ids=module('shared_ids',HERE/'power_ids_oracle.py');ids.module=module;prior=work/'ids';prior.mkdir();_,proof=ids.build(root,prior);join=module('shared_join',HERE/'power_join_oracle.py');code=(prior/'power-ids-original.c').read_text();texts={p:subprocess.check_output(['git','-C',root,'show','HEAD:upstream/ouroboros/'+p]).decode().replace('\r\n','\n')for p in PATHS};source=join.extract(texts[PATHS[0]],'powerdict_FindSharedPowersets');u8=join.extract(texts[PATHS[1]],'u8_readbin');assert 'TokenStoreSetU8(tpi, column, structptr, index, (U8)value);'in u8
 code=code.replace('const char*pchFullName,*pchSourceFile,*pchName;','const char*pchFullName,*pchSourceFile,*pchName;U8 bIsShared;')
 at=code.index('unsigned original_ids(');wrapper=code[at:];code=code[:at]+'''
typedef struct {U32 value;} U8Buffer;typedef U8Buffer*SimpleBufHandle;typedef int ParseTable;typedef U32 StructTypeField;
static int SimpleBufReadU32(U32*out,SimpleBufHandle file){*out=file->value;return 1;}
static void TokenStoreSetU8(ParseTable*t,int c,void*p,int index,U8 value){(void)t;(void)c;(void)index;*(U8*)p=value;}
'''+u8+'\nstatic const BasePowerSet**g_SharedPowersets;static int g_numSharedPowersets;\n#define eaPush eaPushConst\n'+source
 wrapper=wrapper.replace('unsigned original_ids(','unsigned original_shared(').replace('unsigned*sorted){','unsigned*sorted,const unsigned*shared_flags,unsigned*shared_rows,unsigned*counts){').replace('s->pchName="fixture";','s->pchName="fixture";U8Buffer flag={shared_flags[i]};int flag_sum=0;assert(u8_readbin(&flag,NULL,0,&s->bIsShared,0,&flag_sum)&&flag_sum==4);')
 before='assert(pDimSetDefault==&fixture_default);powerdict_SetBackPointers(&d);'
 after='''assert(pDimSetDefault==&fixture_default);powerdict_SetBackPointers(&d);powerdict_FindSharedPowersets(&d);counts[0]=g_numSharedPowersets;for(unsigned k=0;k<counts[0];k++)shared_rows[k]=set_index(&d,g_SharedPowersets[k]);powerdict_FindSharedPowersets(&d);counts[1]=g_numSharedPowersets;for(unsigned k=0;k<counts[1];k++)shared_rows[8192+k]=set_index(&d,g_SharedPowersets[k]);free_array(g_SharedPowersets);g_SharedPowersets=NULL;g_numSharedPowersets=0;'''
 assert before in wrapper;wrapper=wrapper.replace(before,after);code+=wrapper;assert sha(join.extract(code,'powerdict_FindSharedPowersets').encode())==sha(source.encode());path=work/'shared-original.c';path.write_text(code);subprocess.run(['cc','-std=gnu99','-O2','-shared','-fPIC','-w',path,'-o',work/'shared-original.so'],check=True);lib=C.CDLL(str(work/'shared-original.so'));lib.original_shared.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]+[C.c_void_p]*11
 return lib,{'prior_finalized_ID_fixture':proof,'whole_FindSharedPowersets_sha256_lf':sha(source.encode()),'original_u8_readbin_sha256_lf':sha(u8.encode()),'original_u8_readbin_executed':True,'u8_binary_word_and_storage_adapter':True,'source_sha256_lf':{p:sha(t.encode())for p,t in texts.items()},'generated_c_sha256':sha(code.encode()),'source_calls':2,'global_shared_storage_initially_empty':True,'runtime_initial_or_reload_state_observed':False,'field_storage_binding':'original U32 binary to U8 storage; native getter keeps raw byte low8','runtime_generation':False,'actor_authority':False}

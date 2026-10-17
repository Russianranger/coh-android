"""Additional exact original record leaves for composition; host fixture only."""
import ctypes as C,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def extract(text,name):
 m=re.search(r'^[^\n;{}=]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError('Original leaf missing '+name)
 at=m.end();depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def build(root,work):
 provider=module('record_leaf_base',root/'native-android/engine/entities/check.py');base=work/'base';base.mkdir();_,pins,*_=provider.oracle(root,base);code=(base/'source-oracle.c').read_text();functions={}
 paths=['MapServer/src/entity/entsend.c','MapServer/src/entity/character_net_server.c','libs/UtilitiesLib/src/utils/structNet.c','Common/entity/entity.h','Common/seq/seqstate.h','libs/UtilitiesLib/include/utilitieslib/stdtypes.h'];texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in paths}
 expected=json.loads((HERE/'leaf-source-pins.json').read_text())
 if {p:sha(s.encode())for p,s in texts.items()}!=expected['additional_full_sources_sha256_lf']:raise ValueError('Original leaf source changed')
 def function(path,name):
  s=extract(texts[path],name);functions[path+':'+name]=sha(s.encode());return s
 send=paths[0];structnet=paths[2]
 code+='\n#define PERFINFO_AUTO_START(a,b) ((void)0)\n#define PERFINFO_AUTO_STOP() ((void)0)\n'
 code+=function(structnet,'ParserSendEmptyDiff')
 code+='''
typedef struct{StatsCharacter*pchar,*pcharLast;int sentStats;}LeafStatsEntity;
static int leaf_no_diff(ParseTable*t,void*a,void*b){(void)t;(void)a;(void)b;assert(0);return 0;}
#define Entity LeafStatsEntity
#define sdHasDiff leaf_no_diff
#define sdPackEmptyDiff ParserSendEmptyDiff
#define sdPackDiff ParserSend
'''+function(send,'entSendCharacterStats')+'\n#undef Entity\n'
 code+=function(send,'entSendRagdollUpdate')
 wanted=['STATE_RIGHTHAND','STATE_LEFTHAND','STATE_TWOHAND','STATE_DUALHAND','STATE_EPICRIGHTHAND','STATE_SHIELD','STATE_HOVER','STATE_AMMO','STATE_INCENDIARYROUNDS','STATE_CRYOROUNDS','STATE_CHEMICALROUNDS']
 definitions=[]
 for text,names in[(texts[paths[4]],wanted),(texts[paths[3]],['NEXTMOVEBIT_'+n for n in ['RIGHTHAND','LEFTHAND','TWOHAND','DUALHAND','EPICRIGHTHAND','SHIELD','HOVER','AMMO','INCENDIARYROUNDS','CRYOROUNDS','CHEMICALROUNDS','COUNT']]),(texts[paths[5]],['xcase'])]:
  for name in names:
   m=re.search(r'^#define\s+'+name+r'\s+[^\n]+',text,re.M)
   if not m:raise ValueError('Exact source constant missing '+name)
   definitions.append(m.group())
 code+='\n'+'\n'.join(definitions)+'\n'+(HERE/'leaf_adapters.h').read_text().split('/* STATUS_ADAPTERS */')[0]
 code+='#define Entity LeafSeqEntity\n'+function(send,'entSendSeqMoveUpdate')+'\n#undef Entity\n'
 code+=(HERE/'leaf_adapters.h').read_text().split('/* STATUS_ADAPTERS */')[1]
 code+='#define Character LeafStatusCharacter\n#define CharacterAttributes LeafStatusAttributes\n'+function(paths[1],'character_SendStatusEffects')+'\n#undef Character\n#undef CharacterAttributes\n'
 if functions!=expected['whole_functions_sha256_lf'] or sha('\n'.join(definitions).encode())!=expected['exact_constant_definitions_sha256']:raise ValueError('Original leaf functions/constants changed')
 code+=(HERE/'leaf_wrapper.h').read_text();(work/'leaf-source.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-O0','-fwrapv','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(root/'native-android/engine/entities'),work/'leaf-source.c','-lz','-lm','-o',work/'leaf-source.so'],check=True)
 lib=C.CDLL(str(work/'leaf-source.so'));lib.original_record_leaf.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
 return lib,{'base_source_pins':pins,'additional_full_sources_sha256_lf':{p:sha(s.encode())for p,s in texts.items()},'whole_functions_sha256_lf':functions,'exact_constant_definitions_sha256':sha('\n'.join(definitions).encode()),'generated_c_sha256':sha(code.encode()),'full_self_stats_force_all_fields':True,'original_child_functions_executed':True,'RAGDOLL_defined':False,'class_stance_array_interfaces':'explicit bounded fixture shells; no dictionary/gameplay admission','whole_engine_win32_sanitizer_actor_ACK':False}

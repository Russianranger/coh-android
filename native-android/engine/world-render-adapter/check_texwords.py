#!/usr/bin/env python3
"""Focused immutable TexWord whole-cache/locale lookup qualification; host only."""
import argparse,hashlib,io,json,os,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ORIGINAL={'upstream/ouroboros/Game/src/render/texWords.c': '81c5090c7bcf811b77bcfce76bca6ae42da6201d47a41f05c4e2bf4a7a7c9831', 'upstream/ouroboros/Game/src/render/tex.c': '4507ee6fa752ed9452e78c4c989a9de0bdf93d81dd3597f1b1db063d73f1ca5c', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c': '22be253a9e48e2565086e051d469ff92e68c2ae5a84802d8dc3d90713c766fef', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/serialize.c': '11e10da37766cd5329fbabe86dbae378c7f4f99a02b9a3e334d6411e3adb0f56', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c': '9ed817dc9dd6233fe5e06d7d0958ff9ae87aaec9c159d0c86dd8b129f55a1ecf', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils_opt.c': 'e86e629114f213a0c13cc101f5690fd47a9f6b48eb21c1f4dc3cff62ab3ec351', 'upstream/ouroboros/Game/src/render/tex.h': '56e56aea12a4126250f5f6f4d2211f62814b7eae4ad2598271f5423b60680552', 'upstream/ouroboros/Game/src/render/texWords.h': 'e3630b3bc7a8d4702a5f8bd3fca5b6765e1ca430e6f97abd8a9df47fa2031220', 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h': '737a1208ae67a0212c79128050d1ac34ba68b9b04d1979f83b2d697f08593e28', 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/structTokenizer.h': 'a9990ca55c6bd07cc812036c8f7d29ba8f81092e94ff550ef5ce63707a7dfa71', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c': '17a192e9a0fcd6016f670e1ece8e10c458c3853866945a0bed5eb72038710df7'}
LOCAL=['coh_wr_texwords.c','coh_wr_texwords.h','coh_wr_texwords_tables_source.inc','check_texwords.py','texwords_oracle.py','tests/test_texwords.c','tests/test_texwords_cpp.cpp','tests/texwords_fixture.h','TEXWORDS.md']
NATIVE=[HERE/'coh_wr_tex_namespace.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
DEPS=list(dict.fromkeys([HERE/x for x in LOCAL]+[ROOT/x for x in ORIGINAL]+NATIVE+[HERE/'coh_wr_tex_namespace.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h']))
def sha(b):return hashlib.sha256(b).hexdigest()
def run(command,directory,label,env=None):
 result=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,env=env)
 (directory/(label+'.stdout')).write_bytes(result.stdout);(directory/(label+'.stderr')).write_bytes(result.stderr)
 if result.returncode:raise ValueError('focused stage failed: '+label+'; retained stderr/stdout; status '+str(result.returncode))
 return result.stdout

def inputs(cache,defaults):
 raw=cache.read_bytes()
 if len(raw)!=27071659 or sha(raw)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact accepted cache archive differs')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if z.testzip() is not None:raise ValueError('cache CRC differs')
  manifest=z.read('client-cache-manifest.json');body=z.read('data/bin/texWords.bin')
  if sha(manifest)!='e5bc9ff306f90f96b6d34d4d481b30804af078b0e07845dafd71f7324dff6352' or len(body)!=694324 or sha(body)!='4a4eac7c3464febdf11d67a9afd0e349fb4e49f3f06ea33933e258a495739b11':raise ValueError('TexWord donor body/manifest differs')
 raw=defaults.read_bytes()
 if len(raw)!=12308 or sha(raw)!='87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24':raise ValueError('exact seven-default archive differs')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if z.testzip() is not None:raise ValueError('default CRC differs')
  manifest2=z.read('fresh-default-headers/manifest.json');report=z.read('default-headers.json')
  if sha(manifest2)!='1fe575013883344e4ce9f04d83739356e5605f9d6caf7e8190385f420ea5e2c5' or sha(report)!='ab1cf2773b540061c62fd9b42e3ca5f6d58e191805b8a35c8dbf0a06646789a5':raise ValueError('default receipt differs')
  rows=json.loads(manifest2)['files'];selected=[r for r in rows if r['virtual_asset_path']=='data/texture_library/world/filler/grey.texture']
  if len(rows)!=7 or len(selected)!=1 or len(z.namelist())!=9:raise ValueError('default inventory differs')
  grey=z.read('fresh-default-headers/'+selected[0]['filename'])
  if len(grey)!=894 or sha(grey)!='b628966e91a864f9edcb0634605823a7ef3d8e2305f36d1a9f6e9834b018a013':raise ValueError('grey whole body differs')
 return body,grey,json.loads(manifest)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--actual-cache-zip',type=Path,required=True);parser.add_argument('--actual-defaults-zip',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 if args.output.exists():raise ValueError('fresh output directory required')
 args.output.mkdir(parents=True);d=args.output.resolve()
 admitted=list(DEPS);closures={}
 for source in [HERE/'coh_wr_texwords.c',HERE/'tests/test_texwords.c',*NATIVE]:
  raw=run(['cc','-MM','-std=c11','-I',HERE,'-I',ROOT/'native-android/include',source],d,'deps-'+source.stem)
  paths=[]
  for token in raw.decode().replace('\\\n',' ').split()[1:]:
   dependency=Path(token).resolve();dependency.relative_to(ROOT);paths.append(str(dependency.relative_to(ROOT)))
   if dependency not in admitted:admitted.append(dependency)
  closures[str(source.relative_to(ROOT))]=paths
 pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in admitted}
 if any(pins[k]!=v for k,v in ORIGINAL.items()):raise ValueError('original source differs')
 body,grey,manifest=inputs(args.actual_cache_zip,args.actual_defaults_zip);cache=d/'texWords.bin';cache.write_bytes(body);grey_path=d/'grey.texture';grey_path.write_bytes(grey)
 helper=HERE/'texwords_oracle.py';raw=helper.read_bytes()
 if sha(raw)!=pins[str(helper.relative_to(ROOT))]:raise ValueError('helper readmission differs')
 namespace={'__file__':str(helper),'__name__':'texwords_trusted_oracle'};exec(compile(raw,str(helper),'exec'),namespace);oracle,functions,observers=namespace['create'](ROOT)
 table=(HERE/'coh_wr_texwords_tables_source.inc').read_text().split('\n',1)[1]
 if sha(table.encode())!=observers['tables_sha256_lf']:raise ValueError('native original table bytes differ')
 original=d/'original.c';original.write_text(oracle);modes={};binaries={};objects={};stacks=[];mutations=[]
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include']
 # Original readers are unchanged and receive trusted complete positive fixtures;
 # their legacy implementation is kept separate from instrumented native code.
 old=d/'oracle.o';run([*common,'-O0','-Wno-sign-compare','-Wno-unused-parameter','-Wno-unused-variable','-Wno-unused-function','-Wno-unused-result','-Wno-unused-but-set-variable','-Wno-parentheses','-Wno-pedantic','-Wno-missing-field-initializers','-Wno-pointer-sign','-c',original,'-o',old],d,'build-original')
 for mode,extra in [('address',['-O1','-g','-fsanitize=address','-no-pie']),('release',['-O2']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  obj=d/(mode+'-native.o');run([*common,*extra,'-fstack-usage','-c',HERE/'coh_wr_texwords.c','-o',obj],d,mode+'-build-native');objects[mode]=sha(obj.read_bytes())
  if mode=='release':stacks=obj.with_suffix('.su').read_text().splitlines()
  binary=d/mode;run([*common,*extra,HERE/'tests/test_texwords.c',*NATIVE,old,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary],d,mode+'-build')
  modes[mode]=json.loads(run([binary,cache,grey_path],d,mode+'-run',dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
 core=[]
 for i,path in enumerate(NATIVE):
  obj=d/('core-'+str(i)+'.o');run([*common,'-O2','-c',path,'-o',obj],d,'core-'+str(i));core.append(obj)
 cpp=d/'cpp';run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',HERE/'tests/test_texwords_cpp.cpp',d/'release-native.o',*core,'-lz','-lm','-o',cpp],d,'cpp-build');run([cpp],d,'cpp-run')
 source=(HERE/'coh_wr_texwords.c').read_text();test=(HERE/'tests/test_texwords.c').read_text();include='#include "../coh_wr_texwords.c"'
 changes=[('ignore_secondary_priority','old->priority>row->priority','old->priority<row->priority'),('ignore_primary_before_base','row==UINT32_MAX&&(is_base||search)','(is_base||search)'),('invert_actual_basic_presence','status==COH_NOT_FOUND){row=lookup','status==COH_OK){row=lookup'),('ignore_search','is_base||search','is_base||0'),('allow_nonfinite_layers','if(!isfinite(f))','if(0)'),('ignore_ambiguity','if(!icmp(old->stem,row->stem)&&!icmp(old->locale,row->locale))','if(0)'),('skip_owned_limit','allocation>lim->owned_limit','0'),('leak_real_source_pin','coh_asset_release(loader,blob);','(void)blob;'),('ignore_final_cancel','if(stopped(cancel)){status=COH_CANCELLED;goto done;}\ndone:','if(0){status=COH_CANCELLED;goto done;}\ndone:')]
 for label,before,after in changes:
  if source.count(before)!=1 or test.count(include)!=1:raise ValueError('mutation preimage differs '+label)
  changed=d/(label+'.c');mutant=source.replace(before,after)
  if label=='ignore_ambiguity':
   guard='if(old->priority==row->priority||!old->priority||!row->priority)return COH_UNSUPPORTED;'
   if mutant.count(guard)!=1:raise ValueError('secondary ambiguity guard differs')
   mutant=mutant.replace(guard,'')
  changed.write_text(mutant);wrapper=d/(label+'-test.c');wrapper.write_text(test.replace(include,'#include "'+str(changed)+'"'));binary=d/label
  run([*common,'-O2','-I',HERE/'tests',wrapper,*NATIVE,old,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary],d,label+'-build');result=subprocess.run([binary,cache,grey_path],capture_output=True,timeout=180)
  (d/(label+'.stdout')).write_bytes(result.stdout);(d/(label+'.stderr')).write_bytes(result.stderr)
  if result.returncode==0:raise ValueError('semantic mutation escaped '+label)
  mutations.append(label)
 frames={}
 for line in stacks:
  parts=line.split('\t')
  if len(parts)!=3 or ('dynamic' in parts[2] and 'bounded' not in parts[2]):raise ValueError('unbounded native frame')
  frames[parts[0].rsplit(':',1)[-1]]=int(parts[1])
 # Recursive table/subtable mutually recurse no more than17levels.
 control=sum(frames.values())+16*(frames.get('table',0)+frames.get('subtable',0))
 if control>32768:raise ValueError('32KiB own control reserve insufficient')
 if pins!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in admitted} or (body,grey)!=inputs(args.actual_cache_zip,args.actual_defaults_zip)[:2]:raise ValueError('final source/input readmission differs')
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD'],d,'source-revision').decode().strip(),'source_sha256':pins,'compiler_project_dependency_closures':closures,'actual_cache':{'archive_bytes':27071659,'archive_sha256':'5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051','member':'data/bin/texWords.bin','whole_body_bytes':len(body),'whole_body_sha256':sha(body),'manifest_sha256':'e5bc9ff306f90f96b6d34d4d481b30804af078b0e07845dafd71f7324dff6352','manifest':manifest},'modes':modes,'binary_sha256':binaries,'standalone_C_object_sha256':objects,'actual_C_object_CPP_call_link':{'passed':True,'sha256':sha(cpp.read_bytes())},'generated_oracle_sha256':sha(oracle.encode()),'whole_original_functions_sha256_lf':{k:sha(v.encode()) for k,v in functions.items()},'original_observers':observers,'original_oracle_sanitized':False,'native_sanitizers':['AddressSanitizer','UndefinedBehaviorSanitizer'],'LeakSanitizer_executed':False,'release_host_stack_usage':stacks,'conservative_recursive_control_bytes':control,'own_preparation_reserve_bytes':32768,'own_query_reserve_bytes':16384,'mutations_refused':mutations,'fixture_external_policy':'master actual694324B + copied provider694324B + controlled Basic bodies +2MiB static schema builder + oracle dictionary/copies + libc/crypto runtime covered by explicit16MiB fixture policy allowance, not measured RSS/global proof; original2MiB builder is static','loader_configured_total_bytes':8388608,'loader_configured_total_bound_is_caller_precondition':True,'copied_cache_bytes':694324,'finite_float_and_embedded_NUL_and_noncanonical_path_refusals_are_stricter_native_domain':True,'final_cancellation_after_dictionary_completion_independent_control':True,'development_failure_history':['1: source extractor refused trailing signature comment before compilation','2: original adapter lacked bounded seek and narrow legacy warning flags; header comment warning','3: controlled Basic fixture filename did not match its admitted TX2 stem','4/5: test used forged destroy slot; ASan identified test fault, replaced with genuine owner pointer stored inside own allocation','6: ambiguity mutation removed only one of two refusal guards; strengthened mutation removes both','7: all3modes9mutations passed before final metadata/workspace additions','8: overlap test expected equal input reservations despite French/English locale strings differing by1byte; fixed exact same-profile comparison','final: all3modes9mutations passed; corrected output label to distinguish14 retired source loaders from10 actually freed authentic provider contexts/bytes','precise: all3modes9mutations passed; replaced genuine alias-control pointer-member type pun with correctly typed aligned allocation-tail pointer slot'],'old_qualifiers_replayed':False,'layout_preprocessor_or_composition':False,'actual_current_namespace':False,'current_generation':False,'material_or_world_authority':False,'Android':False,'GPU':False,'RSS_or_global_budget':False}
 (d/'texwords.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()

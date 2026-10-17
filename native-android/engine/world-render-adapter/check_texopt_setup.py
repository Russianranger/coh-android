#!/usr/bin/env python3
"""Qualify compact native historical TexOpt import and original CLIENT postprocessing."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;body=Path(path).read_bytes();key=str(Path(path).relative_to(ROOT));
 if key not in START or sha(body)!=START[key]:raise ValueError('helper identity differs before execution')
 exec(compile(body,str(path),'exec'),m.__dict__);return m
NATIVE=['CLIENT_TEXOPT_NATIVE.md','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','texopt_setup_oracle.py','texopt_full_oracle.py','check_surface_states.py','check_texopt_cache.py','check_texname.py','texopt_cache_contract.py','texopt_full_cache.py','check_texopt_setup.py','tests/test_texopt_setup.c']
UPSTREAM=['Common/seq/tricks.c','Common/seq/tricks.h','Common/seq/seqstate.c','Common/seq/seqstate.h','Common/seq/TriggeredMove.h','Game/src/render/texEnums.h','Game/src/render/thread/rt_state.h','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/src/utils/serialize.c','libs/UtilitiesLib/src/utils/tokenstore.c','libs/UtilitiesLib/src/utils/utils.c','libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h']
DEPS=[HERE/x for x in NATIVE]+[ROOT/'upstream/ouroboros'/x for x in UPSTREAM]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--actual-states',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh receipt required')
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source changed before helper import')
 body=a.actual_cache.read_bytes();states=a.actual_states.read_bytes()
 if len(body)!=13537052 or sha(body)!='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1' or len(states)!=15380 or sha(states)!='9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac':raise ValueError('exact producing-generation cache bodies differ')
 old=load('check_texname',HERE/'check_texname.py');cachehelper=load('check_texopt_cache',HERE/'check_texopt_cache.py');cachehelper.load=load;surface=load('check_surface_states',HERE/'check_surface_states.py');load('texopt_full_oracle',HERE/'texopt_full_oracle.py');producer=load('texopt_setup_oracle',HERE/'texopt_setup_oracle.py')
 # Exact native private declarations are regenerated from readonly original input.
 expected='/* Exact original type declarations retained privately for source-qualified cache inputs. */\n#ifndef COH_WR_TEXOPT_TYPES_H\n#define COH_WR_TEXOPT_TYPES_H\n#include <stdint.h>\n'+producer.declarations(ROOT)+'\n_Static_assert(sizeof(F32)==4 && sizeof(U32)==4 && sizeof(TexOptFlags)==4 && sizeof(BlendModeShader)==4,"source scalar layout");\n#endif\n'
 if expected!=(HERE/'coh_wr_texopt_types_internal.h').read_text():raise ValueError('exact source private type declarations differ')
 source=(ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text();utils=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c').read_text();tables=['/* Exact original parse declaration text, interpreted through bounded wire descriptors. */']
 for name in ['Vec2Default1','Vec3Default1','RGBDefault255','parse_rgb3','parse_tex_opt_fallback','parse_tex_opt']:
  start=source.index('TokenizerParseInfo '+name+'[]');tables.append(source[start:source.index('\n};',start)+3])
 if '\n'.join(tables)+'\n'!=(HERE/'coh_wr_texopt_tables_internal.inc').read_text():raise ValueError('exact source tables differ')
 post=['/* Exact original source functions; bounded owner adapters supply storage/dictionary/error hooks. */',old.extract(utils,'int strStartsWith('),old.extract(utils,'int strEndsWith('),old.extract(source,'TexOptFlags texOptFlagsFromName('),old.extract(source,'static bool texOptNeedsMultiTex('),next(x for x in source.splitlines() if x.startswith('#define SAFE_STRUCT_FREE_STRING_CONST')),old.extract(source,'static void setupTexOpt(')]
 if '\n'.join(post)+'\n'!=(HERE/'coh_wr_texopt_post_source.inc').read_text():raise ValueError('unchanged original postprocess functions differ')
 results={}
 with tempfile.TemporaryDirectory(prefix='coh-texopt-setup-') as directory:
  d=Path(directory);(d/'producer.c').write_text(producer.create(ROOT,old.extract));(d/'states.c').write_text(surface.oracle(surface.states(states),old.extract))
  for mode,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include',*flags]
   sources=[HERE/'coh_wr_texopt.c',HERE/'coh_wr_surface_states.c',HERE/'tests/test_texopt_setup.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c'];objects=[]
   for i,path in enumerate(sources):
    obj=d/(str(i)+'.o');old.run([*common,'-c',path,'-o',obj]);objects.append(obj)
   for path,extra in [(d/'producer.c',['-Wno-missing-field-initializers','-Wno-error=unused-but-set-variable','-Wno-error=unused-value']),(d/'states.c',['-Wno-error=discarded-qualifiers','-Wno-error=sign-compare'])]:
    obj=path.with_suffix('.o');old.run([*common,*extra,'-c',path,'-o',obj]);objects.append(obj)
   old.run(['cc',*flags,*objects,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',d/mode]);results[mode]=json.loads(old.run([d/mode,a.actual_cache,a.actual_states],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS} or sha(a.actual_cache.read_bytes())!=sha(body) or sha(a.actual_states.read_bytes())!=sha(states):raise ValueError('source or exact body changed')
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'actual_cache_sha256':sha(body),'actual_states_sha256':sha(states),'original_postprocess_function_sha256_lf':sha(old.extract(source,'static void setupTexOpt(').encode()),'modes':results,'full_native_TexOpt_wire_validation':True,'original_typed_readers_and_CLIENT_setup_executed':True,'original_surface_dictionary_executed':True,'original_stash_input_observer':True,'compiled_schema_crc_recomputed':False,'actual_CLIENT_runtime_executed':False,'active_client_generation':False,'BasicTexture_composite_factory_executed':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()

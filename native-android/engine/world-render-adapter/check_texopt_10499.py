#!/usr/bin/env python3
"""Qualify retained unsupported TexOpt identity and source factory skip witness."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];DRIVER=Path(__file__).resolve();TEST=HERE/'tests/test_texopt_10499.c'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;body=Path(path).read_bytes();key=str(Path(path).relative_to(ROOT));
 if key not in START or sha(body)!=START[key]:raise ValueError('helper identity differs before execution')
 exec(compile(body,str(path),'exec'),m.__dict__);return m
NATIVE=['CLIENT_TEXOPT_NATIVE.md','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','texopt_setup_oracle.py','texopt_full_oracle.py','check_surface_states.py','check_texopt_cache.py','check_texname.py','texopt_cache_contract.py','texopt_full_cache.py','check_texopt_setup.py','tests/test_texopt_setup.c','CLIENT_TEXOPT_10499.md']
UPSTREAM=['Common/seq/tricks.c','Common/seq/tricks.h','Common/seq/seqstate.c','Common/seq/seqstate.h','Common/seq/TriggeredMove.h','Game/src/render/model.c','Game/src/render/texEnums.h','Game/src/render/thread/rt_state.h','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/src/utils/serialize.c','libs/UtilitiesLib/src/utils/tokenstore.c','libs/UtilitiesLib/src/utils/utils.c','libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h']
DEPS=[HERE/x for x in NATIVE]+[ROOT/'upstream/ouroboros'/x for x in UPSTREAM]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
DEPS += [DRIVER,TEST]
def depkey(x):return str(x.relative_to(ROOT)) if x.is_relative_to(ROOT) else 'external-source/'+x.name
START={depkey(x):sha(x.read_bytes()) for x in DEPS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--actual-states',type=Path,required=True);p.add_argument('--partition-ledger',type=Path,required=True);p.add_argument('--resources',type=Path,required=True);p.add_argument('--root-coverage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh receipt required')
 if START!={depkey(x):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source changed before helper import')
 body=a.actual_cache.read_bytes();states=a.actual_states.read_bytes()
 if len(body)!=13537052 or sha(body)!='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1' or len(states)!=15380 or sha(states)!='9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac':raise ValueError('exact producing-generation cache bodies differ')
 pins={'partition-ledger':('46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a',2<<20,a.partition_ledger),'resources':('8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6',32<<20,a.resources),'root-coverage':('5df9bc58cb49c9a177a8315a841701bd300dbdf6641d27ef0b81345f1f6be197',4<<20,a.root_coverage)}
 inputs={}
 for key,(expected,limit,path) in pins.items():
  if path.stat().st_size>limit:raise ValueError('bounded retained input')
  value=path.read_bytes()
  if sha(value)!=expected:raise ValueError('exact retained input digest')
  inputs[key]=value
 ledger=json.loads(inputs['partition-ledger']);names=[v[2] for r in ledger['rows'] for v in r['textures']]
 if len(ledger['rows'])!=3083 or len(names)!=5535 or len(set(names))!=1769 or ledger['resources_sha256']!=pins['resources'][0] or ledger['root_coverage_sha256']!=pins['root-coverage'][0] or any(not name.isascii() for name in names):raise ValueError('fixed captured partition ledger')
 unsupported=b'ArchEnt_INT_Elevator_Door_G\xef\xbf\xbd'
 exact_matches=[name for name in names if name.encode('ascii')==unsupported or name.rsplit('.',1)[0].encode('ascii')==unsupported]
 if exact_matches or unsupported.endswith(b'/'):raise ValueError('unexpected candidate reference')
 relevance={'observed_root_model_owner_rows':3083,'observed_partitions':5535,'unique_partition_names':1769,'all_initial_partition_names_ASCII':True,'initial_exact_name_or_last_extension_stem_matches':exact_matches,'directory_suffix_can_equal_10499':False,'unknown_active_Basic_or_scene_locale_dynamic_remaps':True,'global_unreachable_or_dictionary_exclusion_proven':False,'ledger_regenerated_here':False,'ledger_generation_and_source_pin_provided_by_separate_supplier':True,'independent_generator_review_not_inferred_here':True}
 old=load('check_texname',HERE/'check_texname.py');cachehelper=load('check_texopt_cache',HERE/'check_texopt_cache.py');cachehelper.load=load;surface=load('check_surface_states',HERE/'check_surface_states.py');load('texopt_full_oracle',HERE/'texopt_full_oracle.py');producer=load('texopt_setup_oracle',HERE/'texopt_setup_oracle.py')
 framing=load('texopt_cache_contract',HERE/'texopt_cache_contract.py');full=load('texopt_full_cache',HERE/'texopt_full_cache.py');cache=framing.frame(body,sha(body));wire=full.decode_record(cache,10499,full.schema((ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text(),START['upstream/ouroboros/Common/seq/tricks.c']))
 strings=[{'field':v.name,'hex':v.value.hex()} for v in wire.values if v.kind=='string'];rawfacts={'ordinal':10499,'offset':cache.texopts[10499].offset,'size':cache.texopts[10499].size,'name_hex':cache.texopts[10499].name.hex(),'source_file':cache.texopts[10499].source_file.decode('ascii'),'persisted_string_fields':strings,'zero_initialized_legacy_base_not_serialized':True}
 if cache.texopts[10499].name!=unsupported or any(v.value for v in wire.values if v.kind=='string' and v.name not in ('','F','InternalName')):raise ValueError('exact raw nonmaterial row differs')
 # Exact native private declarations are regenerated from readonly original input.
 expected='/* Exact original type declarations retained privately for source-qualified cache inputs. */\n#ifndef COH_WR_TEXOPT_TYPES_H\n#define COH_WR_TEXOPT_TYPES_H\n#include <stdint.h>\n'+producer.declarations(ROOT)+'\n_Static_assert(sizeof(F32)==4 && sizeof(U32)==4 && sizeof(TexOptFlags)==4 && sizeof(BlendModeShader)==4,"source scalar layout");\n#endif\n'
 if expected!=(HERE/'coh_wr_texopt_types_internal.h').read_text():raise ValueError('exact source private type declarations differ')
 source=(ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text();utils=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c').read_text();tables=['/* Exact original parse declaration text, interpreted through bounded wire descriptors. */']
 for name in ['Vec2Default1','Vec3Default1','RGBDefault255','parse_rgb3','parse_tex_opt_fallback','parse_tex_opt']:
  start=source.index('TokenizerParseInfo '+name+'[]');tables.append(source[start:source.index('\n};',start)+3])
 if '\n'.join(tables)+'\n'!=(HERE/'coh_wr_texopt_tables_internal.inc').read_text():raise ValueError('exact source tables differ')
 post=['/* Exact original source functions; bounded owner adapters supply storage/dictionary/error hooks. */',old.extract(utils,'int strStartsWith('),old.extract(utils,'int strEndsWith('),old.extract(source,'TexOptFlags texOptFlagsFromName('),old.extract(source,'static bool texOptNeedsMultiTex('),next(x for x in source.splitlines() if x.startswith('#define SAFE_STRUCT_FREE_STRING_CONST')),old.extract(source,'static void setupTexOpt(')]
 if '\n'.join(post)+'\n'!=(HERE/'coh_wr_texopt_post_source.inc').read_text():raise ValueError('unchanged original postprocess functions differ')
 prefix=old.extract(source,'static void setupTexOpt(');prefix=prefix[:prefix.index('    tex->flags = texOptFlagsFromName(tex->name, tex->flags);')]+'}\n';prefix=prefix.replace('setupTexOpt(', 'setup_before_nameflags(',1)
 factory=old.extract(source,'void trickCreateTextures(')
 oracle=producer.create(ROOT,old.extract)+'\n'+prefix+r"""
#undef ErrorFilenamef
#define ErrorFilenamef(...) abort()
static struct{TexOpt**texopts;}trick_list;
static void*texopt_delayedLoad;
#define eaSize(any) 1
#define eaCreate(any) abort()
#define eaPush(any,value) abort()
static bool trickFindAllTextures(TexOpt*t,const char**missing){(void)t;(void)missing;abort();}
static void*texCreateTrickTexture(const char*a,const char*b,const char*c){(void)a;(void)b;(void)c;abort();}
static int factory_lwc;static int LWC_IsActive(void){return factory_lwc;}
"""+factory+r"""
unsigned original_10499_skip(void){TexOpt t=raw_original[10499];assert(t.name&&!strcmp(t.name,"ArchEnt_INT_Elevator_Door_G\xef\xbf\xbd"));for(unsigned i=0;i<13;i++)assert(!t.blend_names[i]);const char*name=t.name;setup_before_nameflags(&t,false);assert(t.name==name&&!t.blend_names[BLEND_BASE1]);for(unsigned i=0;i<13;i++)assert(!t.blend_names[i]);TexOpt*one=&t;trick_list.texopts=&one;factory_lwc=0;trickCreateTextures();factory_lwc=1;trickCreateTextures();trick_list.texopts=NULL;return 3;}
"""
 results={}
 with tempfile.TemporaryDirectory(prefix='coh-texopt-setup-') as directory:
  d=Path(directory);(d/'producer.c').write_text(oracle);(d/'states.c').write_text(surface.oracle(surface.states(states),old.extract))
  for mode,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include',*flags]
   sources=[HERE/'coh_wr_texopt.c',HERE/'coh_wr_surface_states.c',TEST,HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c'];objects=[]
   for i,path in enumerate(sources):
    obj=d/(str(i)+'.o');old.run([*common,'-c',path,'-o',obj]);objects.append(obj)
   for path,extra in [(d/'producer.c',['-Wno-missing-field-initializers','-Wno-error=unused-but-set-variable','-Wno-error=unused-value','-Wno-error=unused-variable']),(d/'states.c',['-Wno-error=discarded-qualifiers','-Wno-error=sign-compare'])]:
    obj=path.with_suffix('.o');old.run([*common,*extra,'-c',path,'-o',obj]);objects.append(obj)
   old.run(['cc',*flags,*objects,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',d/mode]);results[mode]=json.loads(old.run([d/mode,a.actual_cache,a.actual_states],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 if any(sha(path.read_bytes())!=expected for expected,limit,path in pins.values()):raise ValueError('retained partition input changed')
 if START!={depkey(x):sha(x.read_bytes()) for x in DEPS} or sha(a.actual_cache.read_bytes())!=sha(body) or sha(a.actual_states.read_bytes())!=sha(states):raise ValueError('source or exact body changed')
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'partition_input_sha256':{key:sha(value) for key,value in inputs.items()},'relevance':relevance,'raw_row':rawfacts,'actual_cache_sha256':sha(body),'actual_states_sha256':sha(states),'original_postprocess_function_sha256_lf':sha(old.extract(source,'static void setupTexOpt(').encode()),'modes':results,'setup_prefix_before_nameflags_sha256_lf':sha(prefix.encode()),'trickCreateTextures_function_sha256_lf':sha(factory.encode()),'source_prefix_and_single_row_factory_guard_executed':True,'unqualified_nameflags_and_stash_executed_for_10499':False,'full_native_TexOpt_wire_validation':True,'original_typed_readers_and_CLIENT_setup_executed_for_other_rows_only':True,'original_surface_dictionary_executed':True,'original_stash_input_observer':True,'compiled_schema_crc_recomputed':False,'actual_CLIENT_runtime_executed':False,'active_client_generation':False,'BasicTexture_composite_factory_executed':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()

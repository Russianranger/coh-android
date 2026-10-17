#!/usr/bin/env python3
"""Qualify immutable cached-header Basic parameter and dependency staging."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;body=Path(path).read_bytes();key=str(Path(path).relative_to(ROOT));
 if key not in START or sha(body)!=START[key]:raise ValueError('helper identity differs before execution')
 exec(compile(body,str(path),'exec'),m.__dict__);return m
NATIVE=['CLIENT_TEXOPT_NATIVE.md','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','texopt_setup_oracle.py','texopt_full_oracle.py','check_surface_states.py','check_texopt_cache.py','check_texname.py','texopt_cache_contract.py','texopt_full_cache.py','check_texopt_setup.py','tests/test_texopt_setup.c','coh_wr_texopt_lookup.c','coh_wr_texopt_lookup.h','coh_wr_texopt_lookup_source.inc','tests/test_texopt_lookup.c','check_texopt_lookup.py','CLIENT_TEXOPT_LOOKUP.md','coh_wr_tex_inputs.c','coh_wr_tex_inputs.h','coh_wr_tex_dependencies.c','coh_wr_tex_dependencies.h','coh_wr_tex_dependencies_source.inc','tests/test_tex_dependencies.c','check_tex_dependencies.py','CLIENT_TEX_DEPENDENCIES.md']
UPSTREAM=['Common/seq/tricks.c','Common/seq/tricks.h','Common/seq/seqstate.c','Common/seq/seqstate.h','Common/seq/TriggeredMove.h','Game/src/render/tex.h','Game/src/render/tex.c','Game/src/render/texEnums.h','Game/src/render/thread/rt_state.h','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/src/utils/serialize.c','libs/UtilitiesLib/src/utils/tokenstore.c','libs/UtilitiesLib/src/utils/utils.c','libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','libs/UtilitiesLib/src/components/StashTable.c']
DEPS=[HERE/x for x in NATIVE]+[ROOT/'upstream/ouroboros'/x for x in UPSTREAM]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--actual-states',type=Path,required=True);p.add_argument('--actual-bar',type=Path,required=True);p.add_argument('--actual-box',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh receipt required')
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source changed before helper import')
 body=a.actual_cache.read_bytes();states=a.actual_states.read_bytes();bar=a.actual_bar.read_bytes();box=a.actual_box.read_bytes()
 if len(box)!=43990 or sha(box)!='c36001854f75ff7e8ef5304138537f1de4b71dcc3529a9a40f6093fde959df9a':raise ValueError('exact retained Box body differs')
 if len(bar)!=22163 or sha(bar)!='c224a6dff69716bde300bb956d7415745780ceeee249e526ad1de69cab654b58':raise ValueError('exact retained Bar body differs')
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
 lookup=old.extract(source,'TexOpt *trickFromTextureName(')
 expectedlookup='/* Unchanged original function bodies; lookup signature receives private context. */\n'+'\n'.join([old.extract(utils,'int strEndsWith('),old.extract(source,'TexOptFlags texOptFlagsFromName('),lookup.replace('trickFromTextureName(const char *name, TexOptFlags *texopt_flags)','source_lookup(Lookup *ctx, const char *name, TexOptFlags *texopt_flags)',1)])+'\n'
 if expectedlookup!=(HERE/'coh_wr_texopt_lookup_source.inc').read_text():raise ValueError('original lookup bodies differ')
 oracle=producer.create(ROOT,old.extract)+r"""
#undef stashFindPointer
static unsigned lookup_attempts;static char lookup_key[260];
static void lookup_find(const char*key,TexOpt**out){lookup_attempts++;*out=NULL;if(find_stash(key,out)){assert(strlen(key)<260);strcpy(lookup_key,key);}}
#define stashFindPointer(table,key,out) lookup_find(key,out)
static void forwardSlashes(char*s){for(;*s;s++)if(*s=='\\')*s='/';}
#define strstri(s,k) ((char*)strstriConst(s,k))
"""+lookup+r"""
int original_lookup_check(const char*path,uint32_t*ordinal,uint32_t*flags,unsigned*attempts,char*key){TexOptFlags f=0;lookup_attempts=0;lookup_key[0]=0;TexOpt*t=trickFromTextureName(path,&f);*ordinal=t?(uint32_t)(t-original):UINT32_MAX;*flags=(uint32_t)f;*attempts=lookup_attempts;strcpy(key,lookup_key);return t!=NULL;}
"""
 tex=(ROOT/'upstream/ouroboros/Game/src/render/tex.c').read_text();th=(ROOT/'upstream/ouroboros/Game/src/render/tex.h').read_text()
 astart=th.index('typedef enum TexFlags');enum=th[astart:th.index('} TexFlags;',astart)+len('} TexFlags;')]
 astart=tex.index('    if(tfh.alpha && !(tfh.flags & TEXOPT_FADE))');header=tex[astart:tex.index('    bind->height = tfh.height;',astart)]
 astart=tex.index('    if (bind->flags & TEX_CUBEMAPFACE || bind->texopt_flags & TEXOPT_CUBEMAP)');target=tex[astart:tex.index('    bind->texWord = texWordFind',astart)]
 bodies=enum+'\n'+old.extract(tex,'static int texFixName(')+'\n'+old.extract(source,'static bool IsValidTexName(')+'\n'+old.extract(tex,'int texResetTrickBasedParametersBasic(')+'\nstatic void header_flags(BasicTexture *bind, Header tfh) {\n'+header+'}\nstatic void target_projection(BasicTexture *bind) {\n'+target+'}\n'
 if '/* Exact original private declarations and source projection bodies. */\n'+bodies!=(HERE/'coh_wr_tex_dependencies_source.inc').read_text():raise ValueError('original Basic projection differs')
 oracle+=r"""
#include "coh_wr_tex_dependencies.h"
#define TEX_NOT_LOADED 0
#define GL_TEXTURE_2D 0x0de1u
#define GL_TEXTURE_CUBE_MAP_ARB 0x8513u
typedef struct{const char*name,*dirname;uint32_t flags,texopt_flags,texopt_surface,target,load_state[2];int hasBeenComposited;float gloss;}BasicTexture;
typedef struct{uint32_t flags;uint8_t alpha;}Header;
static void bounded_copy(char*out,const char*in,int n){assert(n>0&&(size_t)n>strlen(in));memcpy(out,in,strlen(in)+1);}
#define strncpyt bounded_copy
#define STR_COMBINE_SSS(out,a,b,c) do{assert(snprintf(out,sizeof(out),"%s%s%s",a,b,c)>0);assert(strlen(a)+strlen(b)+strlen(c)<sizeof(out));}while(0)
"""+old.extract(tex,'static TexOpt *trickFromTextureDirName(')+'\n'+bodies+r"""
int original_dependency_valid(const char*name){return IsValidTexName(name);}
void original_basic_check(const CohWrTexHeaderInput*h,CohWrTexBasicInput*out){BasicTexture b;memset(&b,0,sizeof(b));b.name=h->basic_key;b.dirname=h->directory;char key[128];assert(snprintf(key,sizeof(key),"%s.dds",h->basic_key)>0);b.flags=(uint32_t)texFixName(key,key,-1);header_flags(&b,(Header){h->cached_flags,h->cached_alpha});TexOpt*t=trickFromTextureDirName(b.dirname,b.name,(TexOptFlags*)&b.texopt_flags);b.texopt_surface=t?(uint32_t)t->surface:0;out->initial_basic_flags=b.flags;out->reload_required=(uint32_t)texResetTrickBasedParametersBasic(&b,NULL,0);target_projection(&b);out->effective_basic_flags=b.flags;out->effective_texopt_flags=b.texopt_flags;out->texopt_surface=b.texopt_surface;out->gloss=b.gloss;out->target=b.target;}
"""
 results={}
 with tempfile.TemporaryDirectory(prefix='coh-texopt-setup-') as directory:
  d=Path(directory);(d/'producer.c').write_text(oracle);(d/'states.c').write_text(surface.oracle(surface.states(states),old.extract))
  for mode,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include',*flags]
   sources=[HERE/'coh_wr_texopt.c',HERE/'coh_wr_surface_states.c',HERE/'coh_wr_texopt_lookup.c',HERE/'coh_wr_tex_inputs.c',HERE/'coh_wr_tex_dependencies.c',HERE/'tests/test_tex_dependencies.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c'];objects=[]
   for i,path in enumerate(sources):
    obj=d/(str(i)+'.o');old.run([*common,'-c',path,'-o',obj]);objects.append(obj)
   for path,extra in [(d/'producer.c',['-Wno-missing-field-initializers','-Wno-error=unused-but-set-variable','-Wno-error=unused-value','-Wno-error=unused-parameter','-Wno-error=unused-variable']),(d/'states.c',['-Wno-error=discarded-qualifiers','-Wno-error=sign-compare'])]:
    obj=path.with_suffix('.o');old.run([*common,*extra,'-c',path,'-o',obj]);objects.append(obj)
   old.run(['cc',*flags,*objects,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',d/mode]);results[mode]=json.loads(old.run([d/mode,a.actual_cache,a.actual_states,a.actual_bar,a.actual_box],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS} or sha(a.actual_cache.read_bytes())!=sha(body) or sha(a.actual_states.read_bytes())!=sha(states) or sha(a.actual_bar.read_bytes())!=sha(bar) or sha(a.actual_box.read_bytes())!=sha(box):raise ValueError('source or exact body changed')
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'actual_box_sha256':sha(box),'actual_bar_sha256':sha(bar),'actual_cache_sha256':sha(body),'actual_states_sha256':sha(states),'original_postprocess_function_sha256_lf':sha(old.extract(source,'static void setupTexOpt(').encode()),'modes':results,'original_lookup_body_sha256_lf':sha(lookup.encode()),'original_Basic_reset_body_executed':True,'original_header_target_statement_projections_executed':True,'original_lookup_body_executed':True,'full_native_TexOpt_wire_validation':True,'original_typed_readers_and_CLIENT_setup_executed':True,'original_surface_dictionary_executed':True,'original_stash_input_observer':True,'compiled_schema_crc_recomputed':False,'actual_CLIENT_runtime_executed':False,'active_client_generation':False,'BasicTexture_composite_factory_executed':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()

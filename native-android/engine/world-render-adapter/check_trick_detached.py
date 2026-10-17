#!/usr/bin/env python3
"""Qualify exact detached Trick suffix and whole-cache retirement."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;body=Path(path).read_bytes();key=str(Path(path).relative_to(ROOT));
 if key not in START or sha(body)!=START[key]:raise ValueError('helper identity differs before execution')
 exec(compile(body,str(path),'exec'),m.__dict__);return m
NATIVE=['coh_wr_trick_detached.c','coh_wr_trick_detached.h','coh_wr_trick_detached_core.inc','coh_wr_trick_detached_storage_internal.h','trick_detached_contract.py','check_trick_detached.py','tests/test_trick_detached.c','CLIENT_TRICK_DETACHED.md','CLIENT_TEXOPT_NATIVE.md','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','texopt_setup_oracle.py','texopt_full_oracle.py','check_surface_states.py','check_texopt_cache.py','check_texname.py','texopt_cache_contract.py','texopt_full_cache.py','check_texopt_setup.py','tests/test_texopt_setup.c','coh_wr_trick.c','coh_wr_trick.h','coh_wr_trick_types_internal.h','coh_wr_trick_tables_internal.inc','coh_wr_trick_post_source.inc','trick_oracle.py','trick_cache_contract.py','tests/test_trick_cache.c','check_trick_cache.py','CLIENT_TRICK_CACHE.md']
UPSTREAM=['Common/seq/AutoLOD.c','Common/seq/AutoLOD.h','Common/seq/animtrackanimate.h','Common/seq/tricks.c','Common/seq/tricks.h','Common/seq/seqstate.c','Common/seq/seqstate.h','Common/seq/TriggeredMove.h','Game/src/render/texEnums.h','Game/src/render/thread/rt_state.h','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/src/utils/serialize.c','libs/UtilitiesLib/src/utils/tokenstore.c','libs/UtilitiesLib/src/utils/utils.c','libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','libs/UtilitiesLib/src/components/StashTable.c']
DEPS=[HERE/x for x in NATIVE]+[ROOT/'upstream/ouroboros'/x for x in UPSTREAM]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh receipt required')
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source changed before helper import')
 body=a.actual_cache.read_bytes()
 if len(body)!=13537052 or sha(body)!='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1':raise ValueError('exact producing-generation cache bodies differ')
 old=load('check_texname',HERE/'check_texname.py');cachehelper=load('check_texopt_cache',HERE/'check_texopt_cache.py');cachehelper.load=load;load('check_surface_states',HERE/'check_surface_states.py');load('texopt_full_oracle',HERE/'texopt_full_oracle.py');load('texopt_setup_oracle',HERE/'texopt_setup_oracle.py');producer=load('trick_oracle',HERE/'trick_oracle.py');detached=load('trick_detached_contract',HERE/'trick_detached_contract.py');framing=load('texopt_cache_contract',HERE/'texopt_cache_contract.py');wire=load('trick_cache_contract',HERE/'trick_cache_contract.py')
 source=(ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text();auto=(ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c').read_text();schema=wire.schema(source,auto,{'tricks':sha(source.encode()),'autolod':sha(auto.encode())});cache=framing.frame(body,sha(body));rows=[wire.decode(cache,i,schema) for i in range(3644)]
 if (HERE/'coh_wr_trick_types_internal.h').read_text()!='/* Exact original private persisted structure declarations; runtime pointers unresolved. */\n#ifndef COH_WR_TRICK_TYPES_H\n#define COH_WR_TRICK_TYPES_H\n#include "coh_wr_texopt_types_internal.h"\n'+producer.declarations(ROOT)+'\n#endif\n':raise ValueError('original type declarations differ')
 if (HERE/'coh_wr_trick_tables_internal.inc').read_text()!='/* Exact original Parse6 declarations, interpreted through bounded wire metadata. */\n'+producer.tables(ROOT):raise ValueError('original full Parse6 tables differ')
 if (HERE/'coh_wr_trick_post_source.inc').read_text()!='/* Exact original numeric prefix and independent group-tray statements only. */\n'+producer.projection(ROOT,old.extract):raise ValueError('original numeric/group projection differs')
 if (HERE/'coh_wr_trick_detached_core.inc').read_text()!=detached.core(ROOT,old.extract):raise ValueError('frozen reader transformation differs')
 results={};exports={}
 with tempfile.TemporaryDirectory(prefix='coh-texopt-setup-') as directory:
  d=Path(directory);(d/'producer.c').write_text(producer.create(ROOT,old.extract))
  for mode,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include',*flags]
   standalone=d/('native-'+mode+'.o');old.run([*common,'-c',HERE/'coh_wr_trick_detached.c','-o',standalone]);symbols=old.run(['nm','-g','--defined-only',standalone]).decode();names=sorted(row.split()[-1] for row in symbols.splitlines());expected=sorted(['coh_wr_trick_detach']+['coh_wr_trick_detached_'+x for x in ['autolod','find','numeric_projection','release','report','source_bytes','stanim','view']])
   if names!=expected:raise ValueError('private source symbol leaked')
   exports[mode]={'symbols':names,'object_sha256':sha(standalone.read_bytes())}
   sources=[HERE/'coh_wr_texopt.c',HERE/'coh_wr_surface_states.c',HERE/'coh_wr_trick.c',HERE/'coh_wr_trick_detached.c',HERE/'tests/test_trick_detached.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c'];objects=[]
   for i,path in enumerate(sources):
    obj=d/(str(i)+'.o');old.run([*common,'-c',path,'-o',obj]);objects.append(obj)
   for path,extra in [(d/'producer.c',['-Wno-missing-field-initializers','-Wno-error=unused-but-set-variable','-Wno-error=unused-value','-Wno-error=unused-variable','-Wno-error=unused-parameter'])]:
    obj=path.with_suffix('.o');old.run([*common,*extra,'-c',path,'-o',obj]);objects.append(obj)
   old.run(['cc',*flags,*objects,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',d/mode]);results[mode]=json.loads(old.run([d/mode,a.actual_cache],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS} or sha(a.actual_cache.read_bytes())!=sha(body):raise ValueError('source or exact body changed')
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'actual_cache_sha256':sha(body),'modes':results,'standalone_public_exports':exports,'wire_rows':len(rows),'wire_tables':[(name,len(fields)) for name,fields in schema],'full_TrickInfo_StAnim_AutoLOD_wire':True,'exact_original_suffix_copied':True,'source_suffix_offset':12769880,'source_suffix_size':767172,'source_suffix_sha256':'e82e825340e7abb16ccb3d34a756a991b73eeab33bc291021a608822620c65a5','old_wholecache_reader_unchanged':True,'wholecache_retires_only_after_all_other_owners_retired':True,'unchanged_original_typed_readers_executed':True,'earray_storage_observer':True,'numeric_group_source_projection_only':True,'compiled_schema_crc_recomputed':False,'animation_binding_executed':False,'actual_CLIENT_runtime_executed':False,'active_client_generation':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()

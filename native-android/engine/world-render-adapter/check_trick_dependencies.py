#!/usr/bin/env python3
"""Preserve exact root-model historical StAnim/AutoLOD obligations with source controls."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
LOCAL=['check_trick_dependencies.py','trick_dependencies_oracle.py','tests/test_trick_dependencies.c','inspect_trick_associations.py','texopt_cache_contract.py','trick_cache_contract.py','check_texname.py','coh_wr_trick_types_internal.h','coh_wr_texopt_types_internal.h','ROOT_TRICK_DEPENDENCIES.md']
UPSTREAM=['tricks.c','tricks.h','AutoLOD.c','AutoLOD.h','animtrackanimate.c','animtrackanimate.h','animtrack.h','anim.c']
PATHS=[HERE/x for x in LOCAL]+[ROOT/'upstream/ouroboros/Common/seq'/x for x in UPSTREAM]+[ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py']
START={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS}
def load(name,path):
 b=path.read_bytes()
 if sha(b)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before import')
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;exec(compile(b,str(path),'exec'),m.__dict__);return m

def preserve(value):
 if isinstance(value,bytes):return value.decode('ascii')
 if isinstance(value,tuple):return [preserve(x) for x in value]
 if hasattr(value,'name') and hasattr(value,'value'):return {'name':value.name,'kind':value.kind,'wire_offset':value.offset,'wire_size':value.size,'value':preserve(value.value)}
 return value

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--resources',type=Path,required=True);p.add_argument('--root-partitions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 old=load('dependency_commands',HERE/'check_texname.py');audit=load('dependency_correlation',HERE/'inspect_trick_associations.py');frame=load('texopt_cache_contract',HERE/'texopt_cache_contract.py');wire=load('trick_cache_contract',HERE/'trick_cache_contract.py');observ=load('dependency_resources',ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py');producer=load('dependency_oracle',HERE/'trick_dependencies_oracle.py')
 paths=(a.actual_cache,a.resources,a.root_partitions);sizes=(13537052,12596422,1103262);bodies=[audit.bounded(p,n) for p,n in zip(paths,sizes)];correlation=audit.correlate(*bodies,frame,wire,observ);cache=frame.frame(bodies[0],audit.PINS['cache']);resources=observ.decode(bodies[1]);base=ROOT/'upstream/ouroboros/Common/seq';src=(base/'tricks.c').read_text();auto=(base/'AutoLOD.c').read_text();schema=wire.schema(src,auto,{'tricks':sha(src.encode()),'autolod':sha(auto.encode())});ledger=[];stnames=[];lodrows=[];counts={'root_model_named':1959,'unique_historical_root_tricks':0,'root_models_with_stanim':0,'unique_root_tricks_with_stanim':0,'root_models_with_autolod':0,'unique_root_tricks_with_autolod':0}
 for group in correlation['associations']:
  rootids=group['root_model_source_ordinals']
  if not rootids:continue
  counts['unique_historical_root_tricks']+=1;row=wire.decode(cache,group['historical_ordinal'],schema);values={v.name:v.value for v in row.values};st=values['StAnim'];lod=values['AutoLOD']
  if not st and not lod:continue
  owners=[]
  for ordinal in rootids:
   r=resources[ordinal];owners.append({'source_ordinal':ordinal,'owner_kind':r['owner_kind'],'file':r['file'],'slot':r['slot'],'original_id':r['original_id'],'definition_name':r['strings'][0],'model':r['strings'][1],'source_geo_name':r['strings'][2],'captured_trick_name':r['strings'][3],'captured_trick_file':r['strings'][4]})
  item={'historical_ordinal':row.ordinal,'historical_name':group['historical_name'],'historical_source_file':group['historical_source_file'],'historical_source_age':row.values[2].value,'root_model_owners':owners,'stanim_children':[preserve(x) for x in st],'autolod_children':[preserve(x) for x in lod]}
  if st:
   counts['root_models_with_stanim']+=len(rootids);counts['unique_root_tricks_with_stanim']+=1
   name=st[0][2].value.decode('ascii')
   if not name or len(name.encode())+len('tscroll/')>=256:raise ValueError('qualified source StAnim key bound')
   stnames.append(name);item['stanim_obligation']={'source_consumes_first_child_only':True,'all_persisted_children_retained':True,'requested_anim_key':'tscroll/'+name,'diagnostic_asset_candidate':'player_library/animations/tscroll/'+name+'.anim','client_load_type':2,'server_load_type':4,'bone_ids':[0,1],'requires_at_least_one_matching_track':True,'track_binding_qualified':False,'STANIMATE_bit_requires_success':True}
  if lod:
   counts['root_models_with_autolod']+=len(rootids);counts['unique_root_tricks_with_autolod']+=1;lodrows.append(lod);item['autolod_obligation']={'selection_not_proven':True,'requires_original_existing_LOD_dictionary_precedence':True,'requires_force_auto_no_lod_legacy_cape_tray_inputs':True,'requires_default_GEO_LOD_reductions_model_radius_distances':True,'conditional_trick_branch_preserves_child_order':True,'model_names_and_object_library_resolution_unresolved':True,'runtime_modelname_specified_and_filename_not_persisted':True}
  ledger.append(item)
 expected={'root_model_named':1959,'unique_historical_root_tricks':528,'root_models_with_stanim':32,'unique_root_tricks_with_stanim':13,'root_models_with_autolod':50,'unique_root_tricks_with_autolod':3}
 if counts!=expected or len(ledger)!=16:raise ValueError('exact dependency subset changed')
 source=producer.create(ROOT,old.extract,stnames,lodrows)+(HERE/'tests/test_trick_dependencies.c').read_text();modes={};binaries={};mutations=[]
 with tempfile.TemporaryDirectory(prefix='coh-trick-dependencies-') as directory:
  d=Path(directory);c=d/'original.c';c.write_text(source)
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   modes[mode]={}
   for target in ['CLIENT','SERVER']:
    binary=d/(mode+'-'+target);old.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-D'+target+'=1',*flags,c,'-o',binary]);modes[mode][target]=json.loads(old.run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode+'-'+target]=sha(binary.read_bytes())
  for name,before,after in [('requires_both_tracks','if( !stAnim->btTex0 && !stAnim->btTex1 )','if( !stAnim->btTex0 || !stAnim->btTex1 )'),('uses_second_child','setStAnim(*trick->stAnim)','setStAnim(trick->stAnim[1])'),('fills_later_LODs','if (!done_far)','if (1)')]:
   if source.count(before)!=1:raise ValueError('mutation source drift '+name)
   mutated=d/(name+'.c');mutated.write_text(source.replace(before,after));binary=d/name;old.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-but-set-variable','-pedantic','-I',HERE,'-DCLIENT=1','-O2',mutated,'-o',binary]);result=subprocess.run([binary],capture_output=True,timeout=30)
   if not result.returncode:raise ValueError('source mutation escaped '+name)
   mutations.append(name)
 if START!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS} or [sha(audit.bounded(p,n)) for p,n in zip(paths,sizes)]!=[audit.PINS[k] for k in ['cache','resources','roots']]:raise ValueError('source/input readmission differs')
 functions={'animFindTrackInSkeleton':old.extract((base/'animtrackanimate.c').read_text(),'const BoneAnimTrack * animFindTrackInSkeleton('),'setStAnim':old.extract((base/'animtrackanimate.c').read_text(),'int setStAnim('),'conditional_AutoLOD_copy_branch':old.extract(auto,'    if (!lod_info->force_auto && !no_lod && trick && trick->auto_lod)')}
 result={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'input_sha256':audit.PINS,'counts':counts,'dependencies':ledger,'modes':modes,'binary_sha256':binaries,'source_semantic_mutations_refused':mutations,'generated_source_sha256':sha(source.encode()),'original_source_blocks_sha256':{k:sha(v.encode()) for k,v in functions.items()},'original_setStAnim_and_track_search_executed':True,'isolated_original_AutoLOD_conditional_branch_executed':True,'fixture_loader_storage_and_bounded_string_observers':True,'full_LOD_selection_executed':False,'actual_animation_or_LOD_asset_loaded':False,'generation_equality_proven':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'counts':counts,'modes':modes}))
if __name__=='__main__':main()

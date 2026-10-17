#!/usr/bin/env python3
"""Receipt-only named-budget ledger. No native build, execution or RSS claim."""
import argparse,gzip,hashlib,json,subprocess
from pathlib import Path
CAP=96*1024*1024
HERE=Path(__file__).resolve().parent

def require(ok,why):
 if not ok:raise ValueError(why)
def load(root,pins):
 values={}
 for role,row in pins['proofs'].items():
  data=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'show',row['commit']+':'+row['path']],timeout=30)
  require(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'proof identity '+role)
  d=json.loads(gzip.decompress(data)if row['path'].endswith('.gz')else data);require(d['passed']is True,'passed proof '+role);values[role]=d
 return values

def charge(rows):
 seen=set();total=0
 for identity,size in rows:
  require(identity not in seen,'duplicate owner identity '+identity);require(type(size)is int and size>=0,'nonnegative charge');seen.add(identity);total+=size
 return total

def ledger(proofs):
 w=proofs['world'];r=w['modes']['release']['result'];require(all(v['result']==r for v in w['modes'].values()),'world equal mode results')
 world_prep=r['batch_peak'];world_steady=world_prep-w['preparation_reserve'];decode=r['mesh_peak']
 require((world_prep,world_steady,decode)==(90851310,90834926,91075118),'qualified world baselines')
 classes=proofs['classes'];actual={r['input']:r for r in classes['original_cases']if r['scenario']==0}
 owner=classes['checks']['release']['native_owner_bytes'];require(owner==463208,'class owner')
 classfamilies={n:actual[n]['bytes']+owner for n in ('classes.bin','villain_classes.bin')}
 require(classfamilies=={'classes.bin':1682500,'villain_classes.bin':4691296},'exact raw class input and metadata')
 cat=proofs['categories']['checks']['release']['owner_bytes'];level=proofs['level']['checks']['release']['projection_bytes'];named=proofs['named']['checks']['release']['owner_bytes'];origin=37952
 require((cat,level,named)==(374856,2880,56),'retained compact owners')
 # Origin37952 follows the frozen64bit header layout:40bytes SHA/lease,
 # 16bytes counts,4flags,128*40byte entries,32768text,8byte alignment.
 require(origin==((40+16+4+128*40+32768+7)//8*8),'origin64 layout')
 base=[('normal_class',classfamilies['classes.bin']),('villain_class',classfamilies['villain_classes.bin']),('two_origins',2*origin),('category',cat),('level',level),('normal_named',named),('villain_named',named)]
 known=charge(base);sets=proofs['power_sets'];setowner=sets['checks']['release']['owner_bytes'];setbytes=sets['exact_input_bytes'];settotal=setowner+setbytes;require((known,setowner,setbytes)==(6827548,196704,3179276),'dictionary baseline')
 plans=[]
 def add(name,items,include_sets=False):
  amount=charge(items)+(settotal if include_sets else 0)
  plans.append({'scenario':name,'retained_dictionary_bytes':amount,'includes_source_admitted_power_sets':include_sets,'world_named_retained_total':world_steady+amount,'world_named_retained_allowance':CAP-world_steady-amount,'batch_preparation_total':world_prep+amount,'batch_preparation_allowance':CAP-world_prep-amount,'earlier_decode_preparation_total':decode+amount,'earlier_decode_preparation_allowance':CAP-decode-amount,'integrated_execution_qualified':False,'actor_or_gpu_fit_proved':False})
 add('both_class_families_qualified_dictionary_components',base)
 add('both_class_families_plus_include_sets',base,True)
 normal=[r for r in base if r[0]not in('villain_class','villain_named')]
 villain=[r for r in base if r[0]not in('normal_class','normal_named')]
 add('only_normal_class_family_plus_include_sets',normal,True);add('only_villain_class_family_plus_include_sets',villain,True)
 # Pure phase arithmetic: workspace and borrowed input retirement are different.
 category_import=239304+2*cat+8192+64
 origin_import=504+2*origin+8192+64
 local_conflicts=[{'operation':'category_import_with_two_origin_owners','minimum_bytes':category_import+2*origin,'standalone_cap':1048576},{'operation':'origin_import_with_category_owner','minimum_bytes':origin_import+cat,'standalone_cap':262144},{'operation':'class_level_call_with_world_named_reservation','minimum_bytes':world_steady+known+level+16384,'standalone_cap':8388608}]
 require(all(x['minimum_bytes']>x['standalone_cap'] for x in local_conflicts),'concrete standalone/global cap conflicts')
 # Controls protect against false feasibility or ownership credits.
 require(plans[1]['world_named_retained_allowance']==-375158,'full dictionaries+sets exceeds global cap')
 require(plans[2]['world_named_retained_allowance']==4316194 and plans[3]['world_named_retained_allowance']==1307398,'selected-family arithmetic')
 try:charge([('same_actual_owner',1),('same_actual_owner',1)])
 except ValueError:pass
 else:raise AssertionError('duplicate identity admitted')
 return {'schema':'coh-independent-cross-module-named-budget-v1','passed':True,'cap_bytes':CAP,'world_batch_preparation':world_prep,'world_named_retained_baseline':world_steady,'world_earlier_decode_preparation':decode,'baseline_is_named_reservations_not_process_rss':True,'known_dictionary_retained':known,'power_sets_retained':settotal,'normal_class_input':actual['classes.bin']['bytes'],'villain_class_input':actual['villain_classes.bin']['bytes'],'class_owner_each':owner,'origin_owner_each':origin,'category_owner':cat,'selected_level':level,'named_owner_each':named,'class_workspace_transient':owner,'origin_workspace_transient':origin,'category_workspace_transient':cat,'selected_level_workspace_transient':level,'sets_workspace_transient':setowner,'scenarios':plans,'standalone_cap_conflicts':local_conflicts,'duplicate_symbolic_identity_refused':True,'parent_global_child_budget_adapter_qualified':False,'integrated_pipeline_qualified':False,'actual_device_memory_measured':False,'actor_fit_proved':False,'gpu_fit_proved':False,'world_authority':False}

def retirement_extension(proofs):
 base=ledger(proofs);d=proofs['sealed'];r=d['modes']['release']['result']
 require(all(x['result']==r for x in d['modes'].values()),'sealed equal mode results')
 require(r['source_loader_destroyed'] is True,'actual fixture GEO loader cleanup')
 require(r['sealed_owned']+r['shared_source']==r['owner_live_after_actual_geo_destroy']==39505455,'sealed retained owners')
 require(r['aggregate_with_prior_dictionary_allowance']==r['owner_live_after_actual_geo_destroy']+r['dictionary_reservation_kept_for_conservative_comparison']==57138703,'conservative retained dictionary allowance')
 require(r['retirement_peak']==93228133 and r['retired_geo_reservation']==33554432,'old plus new transition')
 parent=proofs['parent_foundation'];require(parent['reservation_only'] is True and parent['module_adapters'] is False and parent['global_pipeline'] is False,'generic parent scope')
 measured=parent['modes']['release'];require(all(x==measured for x in parent['modes'].values()),'equal parent measured results')
 parent_metadata=measured['parent_metadata_bytes'];parent_extra=measured['parent_base_reserved_bytes']
 require(parent_metadata==2616 and parent_extra==parent_metadata+16384==19000 and measured['parent_allocations']==measured['parent_frees']==2,'actual measured generic parent accounting')
 all_dict=base['known_dictionary_retained']+base['power_sets_retained'];post=r['aggregate_with_prior_dictionary_allowance'];transition=r['retirement_peak']
 require(post+all_dict==67342231 and CAP-post-all_dict==33321065,'post retirement dictionary arithmetic')
 require(transition+base['known_dictionary_retained']==100055681,'transition withoutsets')
 require(transition+all_dict-CAP==2768365,'transition allsets refusal')
 scenarios=[]
 for label,world,dictionary in [('sealed_before_additional_C_dictionaries',post,0),('sealed_all_C_dictionaries_and_sets',post,all_dict),('seal_transition_with_qualified_C_dictionaries_no_sets',transition,base['known_dictionary_retained']),('seal_transition_with_all_C_and_sets',transition,all_dict)]:
  total=world+dictionary
  scenarios.append({'scenario':label,'world_named_bytes':world,'additional_dictionary_bytes':dictionary,'total':total,'allowance':CAP-total,'plus_measured_parent_reservation_total':total+parent_extra,'plus_measured_parent_allowance':CAP-total-parent_extra,'module_adapters_qualified':False,'integrated_execution_qualified':False,'actor_or_gpu_fit_proved':False})
 return {'sealed_fixture_actual_external_geo_retirement_verified':True,'current_application_cleanup_observed':False,'sealed_world_comparison_baseline':post,'seal_transition_baseline':transition,'measured_parent_metadata_bytes':parent_metadata,'measured_parent_metadata_and_reserve_bytes':parent_extra,'parent_footprint_is_actual_frozen_host_observation':True,'retirement_scenarios':scenarios,'retirement_order_required_for_all_families_and_sets':'seal and actually retire GEO pins/cache/loader/provider before adding retained powersets','parent_foundation_is_module_adapter':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();pins=json.loads((HERE/'source-pins.json').read_bytes());proofs=load(a.source_root,pins);result=ledger(proofs);result.update(retirement_extension(proofs));result['proofs']=pins['proofs'];a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'scenarios':len(result['scenarios']),'full_sets_named_retained_allowance':result['scenarios'][1]['world_named_retained_allowance'],'integrated_pipeline_qualified':False}))

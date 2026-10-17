"""Read-only arithmetic over existing startup and actual resource-join receipts.
No server, cache, accepted APK, profile or production source is changed.
"""
from pathlib import Path
import argparse,hashlib,json,math
LIMIT=2*1024*1024
NATIVE_STAGES=('local_dbserver_startup','local_atlas_startup')
def load(path):
 if path.is_symlink() or not path.is_file() or path.stat().st_size>LIMIT:raise ValueError('receipt path/size')
 raw=path.read_bytes();return json.loads(raw),hashlib.sha256(raw).hexdigest()
def number(v):
 if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('nonnegative finite measurement required')
 return v
def attempt(row):
 ready=number(row['ready_boundary_ms']);stages={}
 for s in row['stages']:
  if s['stage'] in NATIVE_STAGES:
   if s['stage'] in stages:raise ValueError('duplicate native stage')
   stages[s['stage']]=number(s['next_boundary_delta_ms'])
 if set(stages)!=set(NATIVE_STAGES) or sum(stages.values())>ready:raise ValueError('stage envelope')
 native=sum(stages.values());prep=row['guest_detail']['preparation_seconds']
 return {'history_index':row.get('history_index'),'ready_ms':ready,'stage_boundary_native_ms':stages,'native_total_ms':native,'other_exclusive_boundary_ms':ready-native,'native_fraction':native/ready,'preparation_seconds':{k:number(v) for k,v in prep.items()},'preparation_overlap':'Preparation counters are suboperations within guest stages; do not add to boundary totals.'}
def analyze(startup,join,aggregate_limit=96*1024*1024):
 if startup.get('schema')!='coh-offline-startup-analysis-v1':raise ValueError('startup schema')
 current=attempt(startup['current']);history=[]
 for r in startup['historical_attempts']:
  if r.get('ready_boundary_ms') is not None:history.append(attempt(r))
 if join.get('passed')is not True or join.get('actual_resource_capture')is not True or any(join.get(k)is not False for k in ['assets_admitted','world_authority','android_executed']):raise ValueError('resource join scope')
 modes=join.get('modes',{});results=[modes[m]['result'] for m in ['release','asan','ubsan']]
 if any(r!=results[0] for r in results[1:]):raise ValueError('resource mode mismatch')
 r=results[0];peak=number(r['join_aggregate_peak_bytes']);owned=number(r['join_owned_bytes']);source_input=number(r['resource_input_bytes'])
 if type(aggregate_limit)is not int or aggregate_limit<=0 or peak>aggregate_limit:raise ValueError('resource aggregate budget')
 for k in ['passed','source_association_verified']:
  if r.get(k)is not True:raise ValueError('source join admission')
 measurements={'current':current,'historical_ready_attempts':history,'current_vs_other_warm_observation':None}
 warm=[h for h in history if 'warm_schema_restore' in h['preparation_seconds']]
 if warm:
  h=warm[-1];measurements['current_vs_other_warm_observation']={'history_index':h['history_index'],'ready_delta_ms':current['ready_ms']-h['ready_ms'],'db_delta_ms':current['stage_boundary_native_ms'][NATIVE_STAGES[0]]-h['stage_boundary_native_ms'][NATIVE_STAGES[0]],'atlas_delta_ms':current['stage_boundary_native_ms'][NATIVE_STAGES[1]]-h['stage_boundary_native_ms'][NATIVE_STAGES[1]],'other_delta_ms':current['other_exclusive_boundary_ms']-h['other_exclusive_boundary_ms'],'controlled_speedup_established':False}
 scenarios=[]
 for fraction in [0.1,0.25,0.5]:scenarios.append({'hypothetical_native_stage_reduction_fraction':fraction,'ready_ms_if_all_other_boundaries_fixed':current['ready_ms']-current['native_total_ms']*fraction,'measured_speedup':False})
 scenarios.append({'hypothetical_other_exclusive_boundaries_removed':True,'ready_ms_if_native_unchanged':current['native_total_ms'],'measured_speedup':False})
 return {'schema':'coh-startup-resource-budget-observation-v1','passed':True,'measurements':measurements,'counterfactual_arithmetic_only':scenarios,'resource_metadata_transaction':{'aggregate_limit_bytes':aggregate_limit,'observed_join_aggregate_peak_bytes':peak,'observed_peak_fraction':peak/aggregate_limit,'remaining_named_payload_bytes':aggregate_limit-peak,'remaining_named_payload_mib':(aggregate_limit-peak)/2**20,'owned_join_bytes':owned,'resource_input_bytes':source_input,'rows':r['rows'],'model_references':r['model_references'],'resources_indices_built':r['resource_indices_built'],'scope':'Named payload reservations only. Excludes Python process RSS, allocator metadata, actual GPU heaps and future GEO/material/texture owners. Input/copy coexist at import peak; no peak reduction measured.'},'ranked_measurements':[
 {'rank':1,'target':'Native Atlas startup','observed_envelope_ms':current['stage_boundary_native_ms'][NATIVE_STAGES[1]],'next_evidence':'Separate original loader/cache-hit/file-open/decompression/world-build/idle-wait stage times; retain exact bytes/checksums. Measure during next meaningful consolidated run.','production_optimization_justified':False},
 {'rank':2,'target':'Native DB startup','observed_envelope_ms':current['stage_boundary_native_ms'][NATIVE_STAGES[0]],'next_evidence':'Separate DB connect/schema/cache deserialization/import/file and listener-wait timers. Preserve accepted SQL/profile/checksum policy.','production_optimization_justified':False},
 {'rank':3,'target':'Beacon preparation inside Atlas envelope','observed_seconds':current['preparation_seconds'].get('atlas_beacon_graph'),'next_evidence':'Export already-generated cache receipt first: archive_decoded, inventory/fingerprint walks, bytes_hashed/reused, writes and refusal. Then split operation timers; missing counters cannot prove repeated decode.','production_optimization_justified':False},
 {'rank':4,'target':'Scene import and visibility resource working set','observed_envelope_bytes':peak,'next_evidence':'Before authentic GEO/texture admission, measure unique acquired blobs, metadata wire copies, decoded geometry/RGBA, active visibility and old/new retirement overlap within the existing aggregate cap.','production_optimization_justified':False},
 {'rank':5,'target':'Concurrent owned process memory','next_evidence':'Use existing opt-in PID/starttime/UID sampler during next meaningful run; correlate timestamps across DB/Atlas/launcher. Historical boundary high-waters cannot establish overlapping RSS/PSS peak.','production_optimization_justified':False},
 {'rank':6,'target':'Warm checkout/definition/animation preparation','observed_seconds':{k:current['preparation_seconds'].get(k) for k in ['server_data_cache_checkout','prepared_server_definition_caches','server_animation_pack','warm_schema_restore']},'next_evidence':'Retain operation receipts and quantify hashing/copy/decode separately. Warm schema restore is only0.183s; it cannot explain native DB/Atlas envelopes.','production_optimization_justified':False}],
 'evidence_limits':{'startup_accepted_apk_rebuilt':False,'new_server_or_device_run':False,'physical_speedup_measured':False,'cache_hit_or_native_cache_consumption_proven_by_duration':False,'current_concurrent_process_peak_established':False,'resource_geos_materials_or_textures_admitted':False,'world_authority':False}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--startup',type=Path,required=True);p.add_argument('--resource-join',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();startup,sh=load(a.startup);join,jh=load(a.resource_join);r=analyze(startup,join);r['input_sha256']={'startup':sh,'resource_join':jh};a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'native_fraction':r['measurements']['current']['native_fraction'],'metadata_peak_bytes':r['resource_metadata_transaction']['observed_join_aggregate_peak_bytes'],'remaining_named_payload_bytes':r['resource_metadata_transaction']['remaining_named_payload_bytes']}))

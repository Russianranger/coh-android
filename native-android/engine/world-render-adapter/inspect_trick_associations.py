#!/usr/bin/env python3
"""Exact historical name/source-file correlation; never a live generation join."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PATHS=[HERE/'inspect_trick_associations.py',HERE/'trick_cache_contract.py',HERE/'texopt_cache_contract.py',ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py',ROOT/'upstream/ouroboros/Common/seq/tricks.c',ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c']
def sha(b):return hashlib.sha256(b).hexdigest()
START={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS}
PINS={'cache':'cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1','resources':'8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6','roots':'46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a'}
def bounded(path,size):
 with path.open('rb') as stream:body=stream.read(size+1)
 if len(body)!=size:raise ValueError('exact bounded input extent differs')
 return body

def load(name,path):
 body=path.read_bytes()
 if sha(body)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;exec(compile(body,str(path),'exec'),m.__dict__);return m

def correlate(cache,resources,roots,framing,wire,observer):
 for role,body in [('cache',cache),('resources',resources),('roots',roots)]:
  if sha(body)!=PINS[role]:raise ValueError('exact '+role+' input differs')
 if len(cache)!=13537052:raise ValueError('cache extent')
 parsed=framing.frame(cache,PINS['cache']);source=(ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text();auto=(ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c').read_text();schema=wire.schema(source,auto,{'tricks':sha(source.encode()),'autolod':sha(auto.encode())});owners={}
 for i in range(3644):
  row=wire.decode(parsed,i,schema);name,file=row.values[0].value,row.values[1].value
  if not name or any(x<32 or x>126 for x in name+file):raise ValueError('ASCII correlation domain')
  owners[name.lower()]=(i,name.decode(),file.decode())
 observed=observer.decode(resources);ledger=json.loads(roots);rootids=set()
 if ledger['resources_sha256']!=PINS['resources'] or ledger['model_owner_rows']!=3083 or len(ledger['rows'])!=3083:raise ValueError('root ledger identity')
 for row in ledger['rows']:
  ordinal=row['source_ordinal']
  if type(ordinal)!=int or ordinal<0 or ordinal>=len(observed) or ordinal in rootids:raise ValueError('root source ordinal')
  actual=observed[ordinal]
  if actual['strings'][1]!=row['model'] or actual['strings'][2]!=row['source_geo_name'] or actual['textures']!=[tuple(x) for x in row['textures']]:raise ValueError('root model association differs')
  rootids.add(ordinal)
 groups={};counts={'root_model_named':0,'other_observation_named':0,'name_matches':0,'source_file_casefold_matches':0};unresolved=[]
 for ordinal,actual in enumerate(observed):
  name,file=actual['strings'][3:5]
  if not name:continue
  scope='root_model_named' if ordinal in rootids else 'other_observation_named';counts[scope]+=1;owner=owners.get(name.encode().lower())
  if owner is None:unresolved.append({'source_ordinal':ordinal,'name':name,'source_file':file,'reason':'historical_name_absent'});continue
  counts['name_matches']+=1
  if not file or file.lower()!=owner[2].lower():unresolved.append({'source_ordinal':ordinal,'name':name,'source_file':file,'historical_ordinal':owner[0],'reason':'source_file_differs'});continue
  counts['source_file_casefold_matches']+=1
  group=groups.setdefault(owner[0],{'historical_ordinal':owner[0],'historical_name':owner[1],'historical_source_file':owner[2],'root_model_source_ordinals':[],'other_observation_source_ordinals':[]})
  group['root_model_source_ordinals' if ordinal in rootids else 'other_observation_source_ordinals'].append(ordinal)
 return {'captured_records':len(observed),'historical_rows':3644,'historical_unique_names':len(owners),'root_model_rows':len(rootids),'counts':counts,'unresolved':unresolved,'associations':[groups[k] for k in sorted(groups)]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--resources',type=Path,required=True);p.add_argument('--root-partitions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 framing=load('texopt_cache_contract',HERE/'texopt_cache_contract.py');wire=load('trick_cache_contract',HERE/'trick_cache_contract.py');observer=load('historical_resource_observer',ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py')
 paths=(a.actual_cache,a.resources,a.root_partitions);sizes=(13537052,12596422,1103262);bodies=[bounded(x,n) for x,n in zip(paths,sizes)];result=correlate(*bodies,framing,wire,observer);refusals=[]
 for i,role in enumerate(('cache','resources','roots')):
  mutated=list(bodies);mutated[i]=mutated[i][:-1]+bytes([mutated[i][-1]^1])
  try:correlate(*mutated,framing,wire,observer)
  except ValueError:refusals.append(role)
  else:raise AssertionError('changed input accepted')
 if refusals!=['cache','resources','roots'] or START!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS} or [sha(bounded(p,n)) for p,n in zip(paths,sizes)]!=[PINS[x] for x in ('cache','resources','roots')]:raise ValueError('readmission failed')
 if result['counts']!={'root_model_named':1959,'other_observation_named':4035,'name_matches':5994,'source_file_casefold_matches':5994} or result['unresolved']:raise ValueError('exact cohort correlation changed')
 result.update({'source_sha256':START,'input_sha256':PINS,'changed_input_refusals':refusals,'scope':'Historical CLIENT dictionary versus captured SERVER source name/file correlation only','other_observations_unreachable':False,'generation_equality_proven':False,'postprocessed_flags_compared':False,'animation_binding_proven':False,'material_authority':False,'world_authority':False,'android_execution':False})
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['counts','historical_unique_names','changed_input_refusals']}))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Bind integration replay to historical source bytes and the published graph patch."""
import collections,gzip,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;E=HERE/'evidence';script=Path(__file__).read_bytes()
files=[E/'source-measure-host.json',E/'source-measure-integrated-host.json',E/'source-stack-integrated.json.gz'];raw={p:p.read_bytes()for p in files}
old=json.loads(raw[files[0]]);new=json.loads(raw[files[1]]);stack=json.loads(gzip.decompress(raw[files[2]]))
def digest(b):return hashlib.sha256(b).hexdigest()
assert stack['historical_receipt_sha256']==digest(raw[files[1]])and stack['source_sha256']==new['source_sha256']
def roles(receipt):
 result=collections.defaultdict(list)
 for p,h in receipt['source_sha256'].items():result[p.split('/native-android/')[-1]].append({'path':p,'sha256':h})
 return result
before,after=roles(old),roles(new);changes={k for k in before.keys()&after.keys()if{r['sha256']for r in before[k]}!={r['sha256']for r in after[k]}}
assert changes=={'engine/scenegraph/runtime_graph.h','engine/scenegraph/runtime_snapshot.c'}
assert before.keys()-after.keys()=={'engine/scenecatalog/check_source_measure.py'}and after.keys()-before.keys()=={'engine/scenecatalog/qualify_integrated_source.py'}
root=Path(new['integrated_source_root']);commit=subprocess.run(['git','-C',str(root),'rev-parse','5d3ad2283'],check=True,capture_output=True,text=True).stdout.strip();bindings=[]
for role,rows in sorted(after.items()):
 for row in rows:assert digest(Path(row['path']).read_bytes())==row['sha256']
 value={'role':role,'integrated_rows':rows}
 if role in changes:
  body=subprocess.run(['git','-C',str(root),'show',commit+':native-android/'+role],check=True,capture_output=True).stdout;assert{r['sha256']for r in rows}=={digest(body)}
  value.update(kind='published_graph_bytes',commit=commit,git_blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest(),historical_rows=before[role])
 elif role in before:
  assert{r['sha256']for r in rows}=={r['sha256']for r in before[role]};value.update(kind='byte_identical_historical_qualified_source',historical_rows=before[role])
 else:value.update(kind='new_directly_executed_qualification_driver')
 bindings.append(value)
assert all(new['modes'][m]['result']==old['modes'][m]['result']for m in old['modes'])
assert stack['all_modes_fit_reserve']and stack['native_geometry_reexecuted']==False
for p,b in raw.items():assert p.read_bytes()==b
assert Path(__file__).read_bytes()==script
result={'passed':True,'observed_root_head':new['observed_source_head'],'observed_head_is_not_source_prerequisite':True,'published_graph_source_commit':commit,'input_sha256':{p.name:digest(b)for p,b in raw.items()},'binder_source_sha256':digest(script),'source_roles':bindings,'changed_native_roles':sorted(changes),'all_geometry_mode_results_byte_identical_to_historical':True,'stack_maxima':{m:r['maximum_native_chain_bytes']for m,r in stack['modes'].items()},'production_changed':False,'historical_evidence_preserved':True,'world_authority':False}
out=E/'source-integration-binding.json'
with out.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'roles':len(bindings),'graph_commit':commit,'inputs':result['input_sha256'],'binding_sha256':digest(out.read_bytes())}))

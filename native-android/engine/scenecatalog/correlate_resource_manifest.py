#!/usr/bin/env python3
"""Bounded read-only provenance lookup candidates; never resource admission."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,json,re,struct
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root',type=Path,required=True)
p.add_argument('--closure',type=Path,required=True)
p.add_argument('--closure-sha256',required=True)
p.add_argument('--resources',type=Path,required=True)
p.add_argument('--manifest',nargs=2,action='append',required=True,metavar=('PATH','SHA256'))
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def document(path,pin,limit):
 if not re.fullmatch('[a-f0-9]{64}',pin) or path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=limit:raise ValueError('Invalid bounded pinned document')
 raw=path.read_bytes()
 if sha(raw)!=pin:raise ValueError('Document digest differs')
 return json.loads(raw)
if a.output.exists():raise ValueError('New output required')
closure=document(a.closure,a.closure_sha256,4*1024**2)
if not closure['passed'] or not closure['native_join']['source_association_verified'] or closure['native_join']['assets_admitted']:raise ValueError('Actual source association required')
resourcepin=closure['capture_sha256']['resources.cohres'];raw=a.resources.read_bytes()
if len(raw)>64*1024**2 or sha(raw)!=resourcepin:raise ValueError('Resource source digest differs')
oracle=a.source_root/'native-android/engine/scenecatalog-server/resource_oracle.py'
spec=importlib.util.spec_from_file_location('source_resource_oracle',oracle);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);records=m.decode(raw)
ordinals=closure['reachable_model_ordinals']
if ordinals!=sorted(set(ordinals)) or len(ordinals)!=closure['partitions']['reachable']['model_references']:raise ValueError('Reachable ordinal identity differs')
bygeo=collections.defaultdict(list);at=0;offsets=[]
for r in records:
 size=struct.unpack_from('<I',raw,at+16)[0];offsets.append((at,size));at+=size
for k in ordinals:
 if not 0<=k<len(records) or not records[k]['model_present']:raise ValueError('Reachable model ordinal invalid')
 bygeo[records[k]['strings'][2]].append(k)
if sorted(bygeo)!=closure['reachable_exact_geo_names']:raise ValueError('Exact reachable GEO names differ')
lookup=collections.defaultdict(list);manifestpins={}
for filename,pin in a.manifest:
 path=Path(filename);manifest=document(path,pin,64*1024**2);
 if path.name in manifestpins and manifestpins[path.name]!=pin:raise ValueError('Manifest basename ambiguity')
 manifestpins[path.name]=pin
 files=manifest['files'];entries=manifest['provenance']['entries']
 if len(files)>200000 or len(entries)>200000:raise ValueError('Manifest index bound')
 for asset,row in entries.items():
  if not asset.endswith('.geo'):continue
  original=row.get('path')
  if not isinstance(original,str) or not original.isascii() or not original or '\\' in original or '..' in original.split('/'):raise ValueError('Original source path absent or unsafe')
  if asset not in files or files[asset]!={k:row[k] for k in ('bytes','sha256')}:raise ValueError('Manifest file/provenance pin differs')
  lookup[original.casefold()].append((path.name,asset,row))
source=document(a.resources.parent/'source-identity.json',closure['capture_sha256']['source-identity.json'],8*1024**2)
control=document(a.resources.parent.parent/'control-fixture.json',source['control_fixture_sha256'],8*1024**2)
for name,pin in manifestpins.items():
 if control['client_asset_hashes'].get(name)!=pin:raise ValueError('Manifest is not pinned by actual control fixture')
report={'schema':1,'passed':True,'scope':'Original provenance path lookup candidates only; no inferred source path or assets admitted','inspector_sha256':sha(Path(__file__).read_bytes()),'oracle_sha256':sha(oracle.read_bytes()),'closure_sha256':a.closure_sha256,'capture_sha256':closure['capture_sha256'],'manifest_sha256':manifestpins,'control_fixture_sha256':source['control_fixture_sha256'],'control_fixture_manifest_chain_verified':True,'actual_runtime_inventory':source['runtime_inventory'],'source_graph_association_verified':True,'direct_opened_geo_hash_available':False,'same_source_generation_established':False,'assets_admitted':False,'world_authority':False,'counts':{},'files':[]}
counts=collections.Counter();models=0
for sourcegeo,ks in sorted(bygeo.items()):
 candidates=lookup.get(sourcegeo.casefold(),[]);result={'source_geo_name':sourcegeo,'source_ordinals':ks,'candidate_matches':[],'models':[]}
 if len(candidates)!=1:counts['missing' if not candidates else 'ambiguous']+=1
 else:
  mf,asset,row=candidates[0];counts[mf]+=1;kind='exact_provenance_path' if row['path']==sourcegeo else 'ascii_casefold_provenance_path';counts[kind]+=1
  versions={records[k]['format'] for k in ks};expected=row.get('geometry_header',{}).get('version');match=versions=={expected};counts['header_version_equal' if match else 'header_version_mismatch']+=1
  result['candidate_matches'].append({'manifest':mf,'manifest_asset_path':asset,'original_pigg_path':row['path'],'comparison':kind,'bytes':row['bytes'],'sha256':row['sha256'],'source_archive':row.get('source_archive'),'source_metadata_sha256':row.get('source_metadata_sha256'),'source_url':row.get('source_url'),'source_etag':row.get('source_etag'),'source_member_range':row.get('source_member_range',row.get('source_content_range')),'md5_table':row.get('md5_table'),'cached_header_sha256':row.get('cached_header_sha256'),'cached_header_id':row.get('cached_header_id'),'geometry_header':row.get('geometry_header'),'observed_header_version_equal':match,'body_bytes_acquired':False,'source_generation_proven':False,'status':'lookup_candidate_not_resource_pin'})
 grouped=collections.defaultdict(list)
 for k in ks:grouped[records[k]['strings'][1]].append(k)
 for name,indices in sorted(grouped.items()):
  observations=[]
  for k in indices:
   r=records[k];start,size=offsets[k]
   observations.append({'resource_ordinal':k,'record_sha256':sha(raw[start:start+size]),'owner_kind':r['owner_kind'],'file':r['file'],'slot':r['slot'],'original_id':r['original_id'],'definition_name':r['strings'][0],'sorted_runtime_model_row':r['row'],'geo_version':r['format'],'texture_partitions':r['textures']})
  result['models'].append({'exact_model_name':name,'source_observations':observations,'model_in_candidate_body_verified':False});models+=1
 report['files'].append(result)
counts['source_geo_files']=len(bygeo);counts['unique_geo_model_pairs']=models;counts['source_model_references']=len(ordinals);report['counts']=dict(counts)
report['remaining_source_proof']=['Captured per-file original/runtime root identity or deterministic complete inventory reconstruction linking each selected path to exact manifest body hash, with original overlay/file lookup precedence preserved','Acquire candidate full bytes; independently verify body SHA and original PIGG table/header provenance against pinned receipts','Protected native GEO open: exact full model name, unique original comparator rank versus disk order, vertex/triangle/material texture partition equality','Effective CLIENT texture/material/trick/capability/swap/LOD closure remains absent from SERVER capture']
if sha(a.resources.read_bytes())!=resourcepin or sha(a.closure.read_bytes())!=a.closure_sha256:raise ValueError('Source changed during correlation')
for path,pin in a.manifest:
 if sha(Path(path).read_bytes())!=pin:raise ValueError('Manifest changed during correlation')
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'counts':report['counts'],'assets_admitted':False,'same_source_generation_established':False}))

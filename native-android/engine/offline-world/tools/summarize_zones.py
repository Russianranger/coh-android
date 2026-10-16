#!/usr/bin/env python3
"""Compact checked-in evidence; large instance payloads remain external packs."""
import argparse,collections,gzip,hashlib,json,pathlib,struct,zipfile

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=pathlib.Path,required=True);p.add_argument('--evidence',type=pathlib.Path,required=True);p.add_argument('--pack',type=pathlib.Path,required=True);p.add_argument('--accepted-map',type=pathlib.Path);a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
 reports=[];source_bytes=0
 for zone in ('city_01_01','city_01_02'):
  path=a.prepared/(zone+'-manifest.json');r=json.loads(path.read_text());encoded=json.dumps(r,separators=(',',':'),sort_keys=True).encode();z=a.evidence/(zone+'-dependencies.json.gz');z.write_bytes(gzip.compress(encoded,compresslevel=9,mtime=0))
  versions=collections.Counter(str(e['geometry_version']) if e['geometry_version'] is not None else 'uninspected' for e in r['endpoints'].values())
  summary={k:r[k] for k in ('zone','source_revision','source_visits','instance_count','endpoint_count','top_level_geometry_refs','map_local_definition_count','traversal_truncated','limits','definition_graph','most_repeated_placed_rootmods','count_semantics','occupied_origin_cells','instance_payload','asset_manifest_identity','unavailable_source_blobs')}
  summary['definition_graph']={k:v for k,v in summary['definition_graph'].items() if k not in ('missing_edges','root_keys')}
  summary.update(source_file_count=len(r['source_files']),source_bytes=sum(f['bytes'] for f in r['source_files']),missing_definition_keys=len(r['missing_definitions']),parser_failures=r['parser_failures'],geometry_versions_by_endpoint=dict(versions),unique_external_geometry_identities=len(r['external_geometry_identities']),unique_external_geometry_bytes=sum(g['bytes'] for g in r['external_geometry_identities'].values()),original_math_comparison={k:v for k,v in r['original_math_comparison'].items() if k!='source_function_pins'},dependencies=dict(file=z.name,bytes=z.stat().st_size,sha256=sha(z)),complete_zone=False,gpu_qualified=False,collision_render_geometry_qualified=False)
  if a.accepted_map and zone=='city_01_01':
   baseline=json.loads(a.accepted_map.read_text());wanted={x['name'].casefold().rsplit('/',1)[-1] for x in baseline['instances']};instances=json.loads((a.prepared/(zone+'-instances.json')).read_text());candidate=[x for x in instances if x['endpoint'].rsplit('#',1)[-1].casefold() in wanted]
   original=collections.Counter((x['name'].casefold().rsplit('/',1)[-1],struct.pack('<12f',*x['world'])) for x in baseline['instances']);current=collections.Counter((x['endpoint'].rsplit('#',1)[-1].casefold(),struct.pack('<12f',*x['world'])) for x in candidate)
   if original!=current:raise ValueError('accepted map transform/placement regression')
   summary['accepted_map_subset_regression']=dict(passed=True,instances=len(candidate),binary32_matrix_components=12*len(candidate),byte_differences=0,fixture_sha256=sha(a.accepted_map))
  reports.append(summary)
 # Deterministic metadata-only pack; raw original asset payloads are NEVER embedded.
 with zipfile.ZipFile(a.pack,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for path in sorted(a.prepared.glob('city_01_0[12]-*.json')):
   info=zipfile.ZipInfo(path.name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
   with path.open('rb') as source,archive.open(info,'w',force_zip64=True) as target:
    for b in iter(lambda:source.read(1<<20),b''):target.write(b)
 result=dict(schema='coh-offline-world-source-summary-v1',zones=reports,pack=dict(filename=a.pack.name,bytes=a.pack.stat().st_size,sha256=sha(a.pack),contents='Source metadata only. External original GEO/texture packs still required; no new rendered world APK.'),qualification_scope='Source hierarchy and exact matrices plus independent bounded runtime adapter. Original model/material admission and conservative per-page geometry bounds remain open.',admitted_expanded_gpu_instances=0,physical_qualified=False)
 (a.evidence/'source-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'zones':[{k:r[k] for k in ('zone','source_visits','instance_count','traversal_truncated')} for r in reports],'pack':result['pack']}))
if __name__=='__main__':main()

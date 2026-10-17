#!/usr/bin/env python3
"""Replay available authenticated GEO bodies against captured source observations."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile,struct,zlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--candidates',type=Path,required=True);p.add_argument('--candidates-sha256',required=True)
p.add_argument('--capture-directory',type=Path,required=True);p.add_argument('--body-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,**kwargs):
 x=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kwargs)
 if x.returncode:raise RuntimeError(x.stdout+x.stderr)
 return x.stdout
if a.output.exists() or a.candidates.stat().st_size>8*1024**2 or sha(a.candidates)!=a.candidates_sha256:raise ValueError('New output and pinned bounded candidates required')
doc=json.loads(a.candidates.read_bytes());cap=a.capture_directory
for name,pin in doc['capture_sha256'].items():
 if sha(cap/name)!=pin:raise ValueError('Actual source capture identity differs')
binding=json.loads((cap/'resource-binding.json').read_bytes());sources=[HERE/'verify_resource_candidates.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
deps=sources+[ROOT/'upstream/ouroboros/Common/seq/anim.c',HERE/'coh_resource_index.h',HERE/'coh_resource_geo_source.h',ENGINE/'assets/coh_asset_loader.h',ENGINE/'assets/coh_asset_geo.h',ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__)]
pins={str(x.relative_to(ROOT)):sha(x) for x in deps};table=[];selected=[];missing=[]
def header_derivation(path):
 raw=path.read_bytes()
 if len(raw)<8:raise ValueError('Truncated original GEO envelope')
 bias,n=struct.unpack_from('<II',raw);version=0;start=8;packed=bias-4;data=bias+8
 if not n:
  if len(raw)<16:raise ValueError('Truncated new GEO envelope')
  version,n=struct.unpack_from('<II',raw,8);start=16;packed=bias-12;data=bias+4
  if not 2<=version<=8 or version==6:raise ValueError('Original geoLoadStubs version refusal')
 if not 0<n<=64*1024**2 or packed<=0 or start+packed>len(raw) or data>len(raw):raise ValueError('Original GEO envelope bounds')
 decoder=zlib.decompressobj();header=decoder.decompress(raw[start:start+packed],n+1)
 if len(header)!=n or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise ValueError('Original GEO compressed header extent')
 return {'version':version,'uncompressed_bytes':n,'uncompressed_sha256':hashlib.sha256(header).hexdigest(),'header_read_prefix_bytes':start+packed,'header_read_prefix_sha256':hashlib.sha256(raw[:start+packed]).hexdigest(),'data_offset':data,'old_format_data_offset_extra_gap_bytes':data-(start+packed)}
for item in doc['files']:
 if len(item['candidate_matches'])!=1:raise ValueError('Unique candidate required')
 c=item['candidate_matches'][0];name=c['manifest_asset_path'];path=a.body_directory/name
 if not path.exists():missing.append(item['source_geo_name']);continue
 if path.is_symlink() or not path.is_file() or path.stat().st_size!=c['bytes'] or sha(path)!=c['sha256']:raise ValueError('Existing body differs from candidate SHA')
 fields=[item['source_geo_name'],name,str(path.resolve()),c['sha256'],doc['manifest_sha256'][c['manifest']]]
 if any('\t' in x or '\n' in x or '\r' in x for x in fields):raise ValueError('Unsafe table field')
 table.append('\t'.join(fields)+'\n');selected.append({'source_geo_name':item['source_geo_name'],'asset_path':name,'sha256':c['sha256'],'bytes':c['bytes'],'reachable_unique_models':len(item['models']),'independent_original_envelope_derivation':header_derivation(path),'manifest_cached_header_sha256':c.get('cached_header_sha256')})
if not selected:raise ValueError('No authenticated body available')
modes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
with tempfile.TemporaryDirectory(prefix='coh-real-geo-comparison-') as tmp:
 tmp=Path(tmp);path=tmp/'bodies.tsv';path.write_text(''.join(table))
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=tmp/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),*flags,*sources,'-lcrypto','-lz','-lm','-o',binary])
  rows=[json.loads(line) for line in run([binary,cap/'resources.cohres',binding['resources']['sha256'],binding['source_identity']['sha256'],binding['run_identity']['sha256'],path,str(binding['asset_generation'])],env=env).splitlines()]
  if len(rows)!=len(selected) or [r['ordinal'] for r in rows]!=list(range(len(selected))):raise ValueError('Native file order differs')
  for k,row in enumerate(rows):
   if row['status']==0:
    h=selected[k]['independent_original_envelope_derivation']
    if row['uncompressed_header_bytes']!=h['uncompressed_bytes'] or row['uncompressed_header_sha256']!=h['uncompressed_sha256']:raise ValueError('Native header differs from independent original envelope derivation')
  modes[mode]={'binary_sha256':sha(binary),'results':rows}
if any(modes[m]['results']!=modes['release']['results'] for m in modes):raise ValueError('Native mode comparison differs')
if pins!={str(x.relative_to(ROOT)):sha(x) for x in deps}:raise ValueError('Native sources changed')
for s in selected:
 if sha(a.body_directory/s['asset_path'])!=s['sha256']:raise ValueError('Actual GEO body changed')
for name,pin in doc['capture_sha256'].items():
 if sha(cap/name)!=pin:raise ValueError('Actual source capture changed')
rows=modes['release']['results'];success=sum(r['status']==0 for r in rows)
result={'schema':1,'passed':True,'scope':'Host source-metadata comparison of exact candidate full GEO bodies; no captured opened-file generation or CLIENT resource authority','source_sha256':pins,'candidate_report_sha256':a.candidates_sha256,'capture_sha256':doc['capture_sha256'],'available_files':len(selected),'metadata_equal_files':success,'metadata_refused_files':len(selected)-success,'unavailable_files':missing,'files':selected,'modes':modes,'all391_bodies_acquired':not missing,'source_generation_admitted':False,'assets_admitted':False,'client_materials_available':False,'client_lods_available':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps({'passed':True,'available_files':len(selected),'metadata_equal':success,'refused':len(selected)-success,'missing':len(missing),'assets_admitted':False}))

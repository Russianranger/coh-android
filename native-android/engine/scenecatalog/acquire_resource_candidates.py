#!/usr/bin/env python3
"""Recover exact candidate bodies by bounded ZIP ranges, without source authority."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,zipfile
def resume_records(output,candidate_sha256,capture_identity):
 """Merge immutable interruption journals; caller rehashes each selected body."""
 import re
 paths=[output/'acquisition.json',*output.glob('acquisition-resume-*.json')]
 merged={}
 for path in paths:
  if not re.fullmatch(r'acquisition(?:-resume-[1-9][0-9]*)?\.json',path.name) or path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=8*1024**2:raise ValueError('Unsafe resume receipt')
  old=json.loads(path.read_bytes())
  if old['candidate_report_sha256']!=candidate_sha256 or old['source_capture_identity']!=capture_identity or len(old['records'])>512:raise ValueError('Resume source identity differs')
  seen=set()
  for row in old['records']:
   name=row['asset_path']
   if name in seen:raise ValueError('Repeated receipt body')
   seen.add(name)
   if name in merged:
    keys=('source_geo_name','asset_path','manifest','bytes','sha256','zip_crc32','zip_header_offset','zip_method','zip_compressed_bytes')
    if any(merged[name][key]!=row[key] for key in keys):raise ValueError('Resume body identity conflict')
   merged[name]=row
 return merged

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source-root',type=Path,required=True)
 p.add_argument('--candidates',type=Path,required=True)
 p.add_argument('--candidates-sha256',required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--resume',action='store_true')
 a=p.parse_args();root=a.source_root.resolve();out=a.output.resolve()
 if out==root or out.is_relative_to(root) or (out.exists() and not a.resume) or (a.resume and not out.is_dir()):p.error('New external output or explicit existing resume required')
 raw=a.candidates.read_bytes()
 if len(raw)>8*1024**2 or hashlib.sha256(raw).hexdigest()!=a.candidates_sha256:raise ValueError('Candidate document identity differs')
 doc=json.loads(raw)
 if not doc['passed'] or doc['assets_admitted'] or not doc['control_fixture_manifest_chain_verified']:raise ValueError('Expected source-only pinned candidates')
 if len(doc['files'])>512:raise ValueError('File count bound')
 helper=root/'native-android/tools/material_fixture/acquire.py';helperpin=hashlib.sha256(helper.read_bytes()).hexdigest()
 spec=importlib.util.spec_from_file_location('original_bounded_zip_ranges',helper);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 # These exact published archive identities are recorded in the actual control
 # fixture, preparation modules and the two independently hash-pinned manifests.
 archives={'atlas-world-supplement-manifest.json':('atlas-world-supplement.zip',207803201,'c7ed82aaaf987410fa471e19ee2b19115ef660892a06f79e2e2401d5672b095f'),'client-visual-manifest.json':('client-visual-assets.zip',859075775,'5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60')}
 url='https://github.com/Russianranger/coh-android/releases/download/coh-assets-v1.0.0/COH-Assets-1.0.0-Base.zip';outerbytes=1630092780
 reader=r.HTTPRange(url,outerbytes,128*1024**2);streams={};zips={}
 prior={}
 if a.resume:
  prior=resume_records(out,a.candidates_sha256,doc['capture_sha256'])
 else:out.mkdir(parents=True)
 receipt={'schema':1,'passed':False,'candidate_report_sha256':a.candidates_sha256,'helper_sha256':helperpin,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_capture_identity':doc['capture_sha256'],'manifest_sha256':doc['manifest_sha256'],'outer_asset_url':url,'outer_expected_bytes':outerbytes,'outer_full_sha_verified':False,'inner_full_sha_verified':False,'selected_payload_sha_verified':False,'same_source_generation_established':False,'assets_admitted':False,'records':[],'resume_verified_files':len(prior),'archive_expected_sha256':{k:v[2] for k,v in archives.items()}}
 try:
  with zipfile.ZipFile(reader) as outer:
   for manifest,(archive,size,digest) in archives.items():
    info=outer.getinfo('payloads/runtime/'+archive)
    if info.file_size!=size or info.flag_bits&1:raise ValueError('Pinned inner archive envelope differs')
    streams[manifest]=r.subzip(reader,info);zips[manifest]=zipfile.ZipFile(streams[manifest])
  total=0;seen=set()
  for ordinal,item in enumerate(doc['files']):
   if len(item['candidate_matches'])!=1:raise ValueError('Missing/ambiguous candidate')
   c=item['candidate_matches'][0];name=c['manifest_asset_path'];parts=Path(name).parts
   if not name.isascii() or not name.startswith('data/object_library/') or '\\' in name or '..' in parts or name in seen or not name.endswith('.geo'):raise ValueError('Unsafe or repeated candidate path')
   seen.add(name);total+=c['bytes']
   if not 0<c['bytes']<=16*1024**2 or total>96*1024**2:raise ValueError('Candidate payload bound')
   target=out/name
   if name in prior:
    old=prior[name]
    if not target.is_file() or target.is_symlink() or target.stat().st_size!=c['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest()!=c['sha256'] or old['sha256']!=c['sha256'] or old['bytes']!=c['bytes'] or old['source_geo_name']!=item['source_geo_name'] or old['manifest']!=c['manifest']:raise ValueError('Resume payload SHA differs')
    receipt['records'].append(dict(old,resumed_verified=True));continue
   info=zips[c['manifest']].getinfo(name)
   if info.file_size!=c['bytes'] or info.flag_bits&1 or info.compress_type not in (0,8):raise ValueError('Candidate ZIP envelope differs')
   body=zips[c['manifest']].read(info)
   if len(body)!=c['bytes'] or hashlib.sha256(body).hexdigest()!=c['sha256']:raise ValueError('Exact candidate payload SHA differs')
   target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as f:f.write(body)
   receipt['records'].append({'source_geo_name':item['source_geo_name'],'asset_path':name,'manifest':c['manifest'],'bytes':len(body),'sha256':c['sha256'],'zip_crc32':f'{info.CRC:08x}','zip_header_offset':info.header_offset,'zip_method':info.compress_type,'zip_compressed_bytes':info.compress_size,'payload_sha_verified':True,'same_source_generation_established':False})
   if ordinal%25==0:print(json.dumps({'completed':ordinal+1,'files':len(doc['files']),'payload_bytes':total,'range_bytes':reader.total}),flush=True)
  if a.candidates.read_bytes()!=raw or hashlib.sha256(helper.read_bytes()).hexdigest()!=helperpin:raise ValueError('Pinned inputs changed during acquisition')
  receipt.update(passed=True,selected_payload_sha_verified=True,payload_bytes=total)
 except Exception as failure:
  receipt['failure']=str(failure);raise
 finally:
  for z in zips.values():z.close()
  receipt.update(range_bytes=reader.total,ranges=reader.requests,etag=reader.etag)
  name='acquisition.json'
  if a.resume:
   number=1
   while (out/f'acquisition-resume-{number}.json').exists():number+=1
   name=f'acquisition-resume-{number}.json'
  with (out/name).open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps({'passed':True,'files':len(receipt['records']),'payload_bytes':total,'range_bytes':reader.total,'assets_admitted':False}))

if __name__=='__main__':main()

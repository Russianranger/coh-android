#!/usr/bin/env python3
"""Offline interruption-journal controls; no network or game assets created."""
from pathlib import Path
import importlib.util,json,tempfile,hashlib,argparse
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise ValueError('New output required')
source=HERE/'acquire_resource_candidates.py';spec=importlib.util.spec_from_file_location('actual_resource_acquirer',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=0
with tempfile.TemporaryDirectory(prefix='coh-acquire-resume-controls-') as temp:
 root=Path(temp);pin='a'*64;capture={'resources.cohres':'b'*64}
 def record(name):return {'source_geo_name':'source/'+name,'asset_path':'data/'+name,'manifest':'fixture','bytes':1,'sha256':'c'*64,'zip_crc32':'12345678','zip_header_offset':5,'zip_method':0,'zip_compressed_bytes':1}
 def write(name,rows):
  x={'candidate_report_sha256':pin,'source_capture_identity':capture,'records':rows};(root/name).write_text(json.dumps(x));return x
 def refuse():
  global checks
  try:m.resume_records(root,pin,capture)
  except (ValueError,KeyError,TypeError):checks+=1;return
  raise AssertionError('Malformed journal accepted')
 first=record('one.geo');second=record('two.geo');third=record('three.geo')
 write('acquisition.json',[first]);assert list(m.resume_records(root,pin,capture))==['data/one.geo'];checks+=1
 write('acquisition-resume-1.json',[first,second]);assert set(m.resume_records(root,pin,capture))=={'data/one.geo','data/two.geo'};checks+=1
 write('acquisition-resume-2.json',[dict(first,resumed_verified=True),second,third]);assert len(m.resume_records(root,pin,capture))==3;checks+=1
 # Enumerated journal order cannot discard later verified bodies.
 write('acquisition-resume-10.json',[first,second,third]);assert len(m.resume_records(root,pin,capture))==3;checks+=1
 x=write('acquisition-resume-3.json',[first,second]);x['records'][1]['sha256']='d'*64;(root/'acquisition-resume-3.json').write_text(json.dumps(x));refuse()
 (root/'acquisition-resume-3.json').unlink();x=write('acquisition-resume-3.json',[first]);x['candidate_report_sha256']='d'*64;(root/'acquisition-resume-3.json').write_text(json.dumps(x));refuse()
 (root/'acquisition-resume-3.json').unlink();x=write('acquisition-resume-3.json',[first]);x['source_capture_identity']={};(root/'acquisition-resume-3.json').write_text(json.dumps(x));refuse()
 (root/'acquisition-resume-3.json').unlink();write('acquisition-resume-3.json',[first,first]);refuse()
 (root/'acquisition-resume-3.json').unlink();(root/'acquisition-resume-3.json').symlink_to(root/'acquisition.json');refuse()
 (root/'acquisition-resume-3.json').unlink();(root/'acquisition-resume-bad.json').write_text('{}');refuse()
result={'passed':True,'checks':checks,'network_started':False,'game_asset_files_written':False,'source_sha256':{source.name:hashlib.sha256(source.read_bytes()).hexdigest(),Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))

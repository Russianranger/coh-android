#!/usr/bin/env python3
"""Bounded read-only retained archive inventory; never obtain missing bytes."""
import argparse,hashlib,io,json,subprocess,tarfile,zipfile
from pathlib import Path,PurePosixPath
DONOR_SHA='6d6312b3ef4f7b9d25252ced724cbbdb36a4712a011647a8339b5a3207857911'
SYSTEM={'odbc32.dll','iphlpapi.dll','ws2_32.dll','winmm.dll','advapi32.dll','user32.dll','gdi32.dll','kernel32.dll'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def target(name):
 base=PurePosixPath(name.replace('\\','/')).name.lower()
 return base in SYSTEM or (base.startswith('api-ms-win-crt-') and base.endswith('.dll'))
def zip_rows(raw):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  rows=z.infolist()
  if len(rows)>100000:raise ValueError('central_directory_budget')
  return [{'name':m.filename,'bytes':m.file_size} for m in rows]
def inspect(donor,roots):
 raw=donor.read_bytes()
 if sha(raw)!=DONOR_SHA:raise ValueError('exact_donor_identity')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:apkraw=z.read('COH-Atlas-Gameplay-0.13.33.apk')
 with zipfile.ZipFile(io.BytesIO(apkraw)) as apk:
  lockraw=apk.read('assets/runtime/runtime-lock.json');lock=json.loads(lockraw);nested=[];matches=[]
  for name in ('client-runtime.zip','client-prerequisites.zip','hardware-renderer.zip','dbserver-package.tar.gz','game-package.tar.gz','postgresql-runtime.tar.gz'):
   data=apk.read('assets/runtime/'+name)
   if name.endswith('.zip'):rows=zip_rows(data)
   else:
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
     members=tar.getmembers()
     if len(members)>100000:raise ValueError('tar_member_budget')
     rows=[{'name':m.name,'bytes':m.size} for m in members]
   hits=[m for m in rows if target(m['name'])];matches.extend({'nested_archive':name,**m} for m in hits)
   nested.append({'name':name,'bytes':len(data),'sha256':sha(data),'members':len(rows),'matching_module_members':hits})
  apk_members=[{'name':m.filename,'bytes':m.file_size} for m in apk.infolist() if target(m.filename)]
  native=[{'name':m.filename,'bytes':m.file_size,'sha256':sha(apk.read(m))} for m in apk.infolist() if m.filename.startswith('lib/')]
  available_payloads={name:{'bytes':apk.getinfo('assets/runtime/'+name).file_size,'sha256':sha(apk.read('assets/runtime/'+name))} for name in ('psqlodbc_x86.msi','postgresql-runtime.tar.gz')}
 # rg defaults intentionally preserve ignored/hidden boundaries; no claim about
 # device profiles, remote assets, Library or names outside the selected roots.
 paths=subprocess.check_output(['rg','--files',*map(str,roots),'-g','*.zip','-g','*.apk','-g','*.tar.gz','-g','*.tar.xz','-g','*.tar.zst'],text=True,timeout=30).splitlines()
 seen=set();observations=[];direct=[];errors=[];zip_count=entries=0;size_candidates=[]
 for name in paths:
  p=Path(name)
  try:
   st=p.stat();key=(st.st_dev,st.st_ino)
   if key in seen:continue
   seen.add(key);observations.append({'path':str(p),'bytes':st.st_size})
   if st.st_size in (lock['base']['bytes'],lock['wine']['bytes']):size_candidates.append(str(p))
   if p.suffix.lower() not in ('.zip','.apk'):continue
   with zipfile.ZipFile(p) as z:
    rows=z.infolist()
    if len(rows)>100000:raise ValueError('central_directory_budget')
    zip_count+=1;entries+=len(rows)
    direct.extend({'archive':str(p),'name':m.filename,'bytes':m.file_size} for m in rows if target(m.filename))
  except Exception as error:errors.append({'path':str(p),'classification':type(error).__name__})
 return {'schema':'coh-retained-wine-platform-input-inventory-v1','donor_sha256':DONOR_SHA,'apk_sha256':sha(apkraw),'runtime_lock_sha256':sha(lockraw),'external_runtime_locks':{n:lock[n] for n in ('base','wine')},'apk_direct_module_members':apk_members,'apk_native_libraries':native,'apk_nested_archives':nested,'apk_nested_matching_modules':matches,'available_other_payloads':available_payloads,'bounded_local_search':{'roots':list(map(str,roots)),'policy':'rg default visible/nonignored archive names only; ZIP central directories; no other tar recursion','archive_path_count':len(paths),'unique_archive_inodes':len(seen),'zip_central_directories':zip_count,'central_entries':entries,'observed_path_size_map_sha256':sha(json.dumps(sorted(observations,key=lambda x:x['path']),sort_keys=True).encode()),'matching_direct_members':direct,'exact_locked_archive_size_candidates':size_candidates,'errors':errors},'actual_wine_modules_recovered':False,'static_platform_closure_admitted':False,'runtime_profile_admitted':False,'downloads_or_binary_execution':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--donor',type=Path,required=True);p.add_argument('--roots',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('new_output_required')
 q=inspect(a.donor,a.roots);q['helper_sha256']=sha(Path(__file__).read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'actual_wine_modules_recovered':False,'nested_matches':len(q['apk_nested_matching_modules']),'direct_matches':len(q['bounded_local_search']['matching_direct_members']),'search_errors':len(q['bounded_local_search']['errors'])}))

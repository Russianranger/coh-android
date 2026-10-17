#!/usr/bin/env python3
"""Admit only seven public source bodies from an exact prepared .31 staging owner.

No account, PostgreSQL, capture, server-runtime or other profile file is opened.
Optional retention has a fixed allowlist and is independent of parser support.
"""
from __future__ import annotations
import argparse,ast,builtins,hashlib,json,os,re,stat,subprocess,sys,tempfile,types,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DEFAULTS=HERE/'qualification/texture-seed-eligibility-20261017/required-default-inputs.json'
DEFAULTS_SHA='21b428e876e537fff374fbd6a17baaed5ad0457f04b7ae2833fc62c9ad8bf787'
HELPERS={
 'client_startup_diagnostic.py':(91242,'8ac9477951ff7a6252a1a72f8184242bb5c0863e604913ea452303e6d4696a53'),
 'texture_header_index.py':(17875,'41adbf003f4ff481b158be09bba8393dd99f615ccb4a036470968596c93459ff'),
 'character_server_data_cache.py':(32868,'d742fe7348424db7406281c1346b845ec092d2a30725e4005b63de750e041bb7'),
 'diagnostic.py':(69529,'748975acf9b0c01b094166150112306edfc12c18656bc4b1926e00ea9460dbaf')}
NAMES=('white','grey','invisible','black','dummy_bump','dummy_dynamic_cubemap_face0','buildinglightpattern')
COUNT,BYTES,EPOCH=173011,2977730517,1767225600
DONOR={'bytes':41203812,'sha256':'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'}
STAGING_SOURCE=ROOT/'tools/android/atlasgame/prepare_server_fx_control_fixture.py'
COMPILE=[HERE/'inspect_default_headers.c',HERE/'coh_wr_tex_inputs.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
SOURCES=[Path(__file__),DEFAULTS,*COMPILE,HERE/'coh_wr_tex_inputs.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',STAGING_SOURCE,ROOT/'tools/android/interactive/qualify_full_startup_preflight.py']
class Refused(ValueError):pass
def require(value,code):
 if not value:raise Refused(code)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def stamp(info):return tuple(getattr(info,k) for k in ('st_dev','st_ino','st_uid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
def directory(path):
 path=Path(path);require(path.is_absolute() and path==path.resolve(strict=True),'REAL_ABSOLUTE_DIRECTORY')
 info=path.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid() and not info.st_mode&0o022,'OWNED_DIRECTORY');return path
def fresh(path):
 path=Path(path);require(path.is_absolute() and path.name not in ('','.','..') and path.parent==path.parent.resolve(strict=True),'FRESH_OUTPUT_PATH')
 directory(path.parent);require(not os.path.lexists(path),'OUTPUT_EXISTS');return path
class Inputs:
 def __init__(self):self.files={};self.dirs={}
 def root(self,path):
  path=directory(path);identity=stamp(path.lstat());require(path not in self.dirs or self.dirs[path]==identity,'SOURCE_DIRECTORY_CHANGED');self.dirs[path]=identity;return path
 def read(self,path,maximum,expected=None,single=False):
  path=Path(path);info=path.lstat();require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and not info.st_mode&0o022 and (not single or info.st_nlink==1) and 0<info.st_size<=maximum,'SOURCE_REGULAR_FILE')
  before=stamp(info)
  with path.open('rb') as stream:
   require(stamp(os.fstat(stream.fileno()))==before,'SOURCE_FILE_CHANGED');body=stream.read(maximum+1);require(stamp(os.fstat(stream.fileno()))==before,'SOURCE_FILE_CHANGED')
  require(stamp(path.lstat())==before and len(body)==info.st_size,'SOURCE_FILE_CHANGED');pin={'bytes':len(body),'sha256':sha(body)}
  if expected is not None:require(pin==expected,'SOURCE_PIN')
  require(path not in self.files or self.files[path]==(before,pin),'SOURCE_FILE_CHANGED');self.files[path]=(before,pin);return body
 def verify(self):
  for path,identity in self.dirs.items():require(stamp(path.lstat())==identity,'SOURCE_DIRECTORY_CHANGED')
  for path,(identity,pin) in self.files.items():
   require(stamp(path.lstat())==identity,'SOURCE_FILE_CHANGED');self.read(path,pin['bytes'],pin)
def object_bytes(raw):
 value=json.loads(raw);require(type(value) is dict,'JSON_OBJECT');return value
def archive_member(raw,name,maximum):
 import io
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  require(len(z.namelist())==len(set(z.namelist())),'ZIP_DUPLICATE');item=z.getinfo(name);require(not item.is_dir() and not item.flag_bits&1 and 0<item.file_size<=maximum,'ZIP_MEMBER');return z.read(name)
def extracted(blob,names,namespace):
 tree=ast.parse(blob);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
 require({n.name for n in nodes}==set(names) and len(nodes)==len(names),'PINNED_HELPER_SYMBOLS');exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned-read-only-helper>','exec'),namespace);return namespace
class Context:
 def check(self):pass
def read_only_helpers(blobs):
 # Execute only exact pinned original read-only functions/class. Their two
 # imports resolve to this isolated original resolver and typed refusal service;
 # no protected guest module initialization or prepare()/write function executes.
 namespace={'Path':Path,'hashlib':hashlib,'json':json,'os':os,'stat':stat,'re':re,'require':require,'DATA_COUNT':COUNT,'DATA_BYTES':BYTES}
 client=extracted(blobs['client_startup_diagnostic.py'],('import_identity','native_closure_identity','worktree_data_identity','identity_sha256'),dict(namespace))
 resolver=extracted(blobs['character_server_data_cache.py'],('CheckedInputResolver',),dict(namespace))['CheckedInputResolver']
 def imports(name,*args,**kwargs):
  if name=='character_server_data_cache':return types.SimpleNamespace(CheckedInputResolver=resolver)
  if name=='diagnostic':return types.SimpleNamespace(DiagnosticError=Refused)
  return builtins.__import__(name,*args,**kwargs)
 namespace.update(MAX_RECORDS=65536,canonical=canonical);namespace['__builtins__']=dict(vars(builtins),__import__=imports)
 scanner=extracted(blobs['texture_header_index.py'],('texture_inputs',),namespace)['texture_inputs'];return client,resolver,scanner
def source_pins(committed=True):
 pins={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in SOURCES}
 if committed:
  for name,pin in pins.items():
   result=subprocess.run(['git','-C',str(ROOT),'show','HEAD:'+name],capture_output=True,timeout=30);require(result.returncode==0 and {'bytes':len(result.stdout),'sha256':sha(result.stdout)}==pin,'ADMITTER_COMMITTED_SOURCE')
 return pins
def resolve_inputs(staging,payloads,control_pin,*,registry=None):
 r=registry or Inputs();staging=r.root(staging);payloads=r.root(payloads);owned=r.root(staging/'owned');assets=r.root(staging/'assets');packaged=r.root(staging/'apk-runtime')
 control_raw=r.read(staging/'control-fixture.json',4<<20,single=True);require(sha(control_raw)==control_pin,'CONTROL_FIXTURE_PIN');control=object_bytes(control_raw)
 require(control.get('format')==1 and control.get('role')=='complete_prepared_public_031_native_fx_control' and control.get('status')=='prepared' and control.get('source_commit')=='74fe247be85173e618f1af2c8af71b1316de4cd8' and control.get('donor_apk')==DONOR and control.get('native_processes_started') is False and control.get('live_sql_started') is False and control.get('player_database_used') is False,'CONTROL_FIXTURE_SCOPE')
 require(control.get('source_script')=={'bytes':STAGING_SOURCE.stat().st_size,'sha256':sha(STAGING_SOURCE.read_bytes())},'STAGING_SOURCE_PIN')
 expected_helpers=control.get('packaged_guest_sources');require(type(expected_helpers) is dict and 4<=len(expected_helpers)<=256,'PACKAGED_HELPER_INVENTORY');blobs={}
 helper_bytes=0
 for name,pin in expected_helpers.items():
  require(re.fullmatch(r'[A-Za-z0-9_]+\.py',name) is not None and type(pin) is dict and set(pin)=={'bytes','sha256'} and type(pin['bytes']) is int and 0<pin['bytes']<=1<<20 and re.fullmatch('[0-9a-f]{64}',str(pin['sha256'])),'PACKAGED_HELPER_PIN')
  helper_bytes+=pin['bytes'];require(helper_bytes<=16<<20,'PACKAGED_HELPER_BOUND');body=r.read(packaged/name,1<<20,pin,single=True)
  if name in HELPERS:
   require((len(body),sha(body))==HELPERS[name],'EXACT_031_READ_ONLY_HELPER');blobs[name]=body
 require(set(blobs)==set(HELPERS),'EXACT_031_READ_ONLY_HELPER')
 client,resolver_type,scanner=read_only_helpers(blobs)
 imported=r.root(payloads.parent/'full-original-import-fixture-v1'/'data');r.root(imported.parent);r.read(imported.parent/'complete.properties',4096,single=True)
 identity=client['import_identity'](imported);original=control.get('original_import',{});require(original.get('files')==COUNT and original.get('bytes')==BYTES and original.get('all_leaf_sha256_checked') is True and original.get('contract_sha256')==identity['contract_sha256'],'CONTROL_IMPORT_IDENTITY')
 asset_hashes=control.get('client_asset_hashes');require(type(asset_hashes) is dict,'CONTROL_ASSET_HASHES');archives={}
 for name,maximum in [('client-runtime.zip',64<<20),('client-caches.zip',32<<20),('client-prerequisites.zip',1<<20)]:
  raw=r.read(assets/name,maximum);require(asset_hashes.get(name)==sha(raw),'STAGED_ARCHIVE_PIN');archives[name]=raw
 package=object_bytes(archive_member(archives['client-runtime.zip'],'client-package.json',1<<20));require(package.get('source_commit')=='0b75ade0c801735e10c5798f641948a45cc50488' and package.get('data_commit')=='d51533ec8e6a9cf726b9214968077a05fdcf19f3' and type(package.get('files')) is dict and len(package['files'])==21,'CLIENT_PACKAGE_IDENTITY')
 prerequisite_sha=sha(archive_member(archives['client-prerequisites.zip'],'client-prerequisites-manifest.json',1<<20));cache=object_bytes(archive_member(archives['client-caches.zip'],'client-cache-manifest.json',1<<20));require(cache.get('prerequisites_manifest_sha256')==prerequisite_sha,'CACHE_PREREQUISITE_IDENTITY')
 expected={'format':1,'source_data':str(imported),'import':identity,'package_sha256':sha(archives['client-runtime.zip']),'cache_archive_sha256':sha(archives['client-caches.zip']),'prerequisites_archive_sha256':sha(archives['client-prerequisites.zip']),'prerequisites_manifest_sha256':prerequisite_sha,'normalized_mtime_epoch':EPOCH}
 content=client['identity_sha256']({'data':client['worktree_data_identity'](expected),'native':client['native_closure_identity'](package)})
 work=r.root(owned/('client-work-'+content[:24]));r.root(work/'data');marker_raw=r.read(work/'client-work.json',1<<20,single=True);marker=object_bytes(marker_raw)
 require(all(marker.get(k)==v for k,v in expected.items()) and marker.get('content_identity_sha256')==content and marker.get('worktree_key')==work.name and marker.get('input_files')==COUNT and marker.get('input_bytes')==BYTES and marker.get('imported_inputs_readonly') is True,'COLD_WORKTREE_IDENTITY')
 records,inventory,scanned_marker=scanner(work,Context());require(scanned_marker==marker,'WORKTREE_RECEIPT_CHANGED');lookup=dict(records);require(len(lookup)==len(records),'TEXTURE_PATH_AMBIGUOUS')
 raw_defaults=DEFAULTS.read_bytes();require(sha(raw_defaults)==DEFAULTS_SHA,'FIXED_DEFAULT_ALLOWLIST');entries=object_bytes(raw_defaults)['required_defaults'];require(len(entries)==7 and tuple(Path(x['required_virtual_asset_path']).stem for x in entries)==NAMES,'FIXED_DEFAULT_ALLOWLIST')
 resolver=resolver_type((imported,(work/'data').resolve(strict=True)),Context());bodies=[];leaves=[]
 for entry in entries:
  logical=entry['required_virtual_asset_path'][5:];require(logical in lookup,'FIXED_DEFAULT_NOT_STAGED');path=lookup[logical];link=stamp(path.lstat());target,info=resolver.leaf(path);require(not info.st_mode&0o222,'READONLY_DEFAULT_SOURCE')
  pin={'bytes':entry['whole_body_bytes'],'sha256':entry['whole_body_sha256']};body=r.read(target,pin['bytes'],pin);bodies.append(body);leaves.append((path,link,target,stamp(target.lstat())))
 resolver.verify();again,inventory_after,marker_after=scanner(work,Context());require(inventory_after==inventory and marker_after==marker and again==records,'TEXTURE_INPUT_INVENTORY_CHANGED');r.verify()
 proof={'control_fixture_sha256':control_pin,'client_work_receipt_sha256':sha(marker_raw),'client_content_identity_sha256':content,'completed_import_identity':identity,'texture_metadata_inventory_sha256':inventory,'texture_metadata_records':len(records),'packaged_read_only_helper_sha256':{k:v[1] for k,v in HELPERS.items()},'whole_seven_body_bytes':sum(map(len,bodies)),'independently_rehashed_original_import':False}
 def verify():
  for path,link,target,target_stamp in leaves:require(stamp(path.lstat())==link and path.resolve(strict=True)==target and stamp(target.lstat())==target_stamp,'DEFAULT_SOURCE_CHANGED')
  resolver.verify();r.verify()
 return entries,bodies,proof,verify,(staging,payloads,imported,work)
def native_inspection(bodies,temporary,pins):
 binary=temporary/'inspect-default-headers';command=['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),*map(str,COMPILE),'-lcrypto','-lz','-lm','-o',str(binary)]
 require(source_pins(False)==pins,'ADMITTER_SOURCE_CHANGED')
 result=subprocess.run(command,capture_output=True,timeout=180);require(result.returncode==0,'EXISTING_PARSER_BUILD')
 paths=[]
 for i,body in enumerate(bodies):
  path=temporary/(NAMES[i]+'.texture');path.write_bytes(body);path.chmod(0o400);paths.append(path)
 binary_sha=sha(binary.read_bytes());require(source_pins(False)==pins,'ADMITTER_SOURCE_CHANGED')
 result=subprocess.run([str(binary),*map(str,paths)],capture_output=True,stdin=subprocess.DEVNULL,timeout=30);require(sha(binary.read_bytes())==binary_sha,'NATIVE_EXECUTABLE_CHANGED');require(result.returncode==0 and len(result.stdout)<=16384,'EXISTING_PARSER_INSPECTION');value=object_bytes(result.stdout)
 require(value.get('schema')=='coh-fixed-seven-header-inspection-v1' and value.get('inspection_label_only')==1 and type(value.get('rows')) is list and len(value['rows'])==7,'EXISTING_PARSER_RESULT')
 for i,(row,body) in enumerate(zip(value['rows'],bodies)):require(row.get('ordinal')==i and row.get('bytes')==len(body) and row.get('sha256')==sha(body) and type(row.get('protected_parser_status')) is int and 0<=row['protected_parser_status']<=7,'EXISTING_PARSER_BODY_ASSOCIATION')
 return value,binary_sha
def secondary(primary,code,count=1):
 # Keep the first failure and expose only a fixed code/count, never paths or
 # secondary exception text. Cleanup must continue after independent failures.
 if hasattr(primary,'add_note'):primary.add_note(code+'='+str(count))
def write_new(path,body,created):
 stream=path.open('xb');primary=None
 try:
  created.append((path,stamp(os.fstat(stream.fileno()))[:3]));stream.write(body);stream.flush();os.fsync(stream.fileno())
 except BaseException as error:primary=error;raise
 finally:
  try:stream.close()
  except BaseException:
   if primary is None:raise
   secondary(primary,'OUTPUT_CLOSE_SECONDARY_FAILURES')
 path.chmod(0o400)
def publish(output,retain,entries,bodies,proof,verify):
 created=[];made_directory=False;directory_id=None
 try:
  verify()
  if retain is not None:
   retain.mkdir(mode=0o700);made_directory=True;directory_id=stamp(retain.lstat())[:3]
   rows=[]
   for name,entry,body in zip(NAMES,entries,bodies):
    filename=name+'.texture';path=retain/filename;write_new(path,body,created);require(path.read_bytes()==body,'RETAINED_BODY_VERIFY');rows.append({'filename':filename,'virtual_asset_path':entry['required_virtual_asset_path'],'bytes':len(body),'sha256':sha(body)})
   verify();manifest={'schema':'coh-fixed-seven-public-source-bodies-v1','source_admission':{k:proof[k] for k in ('control_fixture_sha256','client_work_receipt_sha256','client_content_identity_sha256')},'files':rows,'current_provider_generation':False,'namespace_complete':False,'default_identity':False,'GPU':False}
   raw=canonical(manifest)+b'\n';write_new(retain/'manifest.json',raw,created);fd=os.open(retain,os.O_RDONLY|os.O_DIRECTORY);primary=None
   try:os.fsync(fd)
   except BaseException as error:primary=error;raise
   finally:
    try:os.close(fd)
    except BaseException:
     if primary is None:raise
     secondary(primary,'DIRECTORY_CLOSE_SECONDARY_FAILURES')
   proof['retained_fixed_seven']={'files':7,'body_bytes':sum(map(len,bodies)),'manifest_sha256':sha(raw)}
  verify();write_new(output,json.dumps(proof,indent=2).encode()+b'\n',created);verify()
 except BaseException as primary:
  failures=0
  for path,identity in reversed(created):
   try:
    if os.path.lexists(path):
     require(stamp(path.lstat())[:3]==identity,'ROLLBACK_OUTPUT_CHANGED');path.unlink()
   except BaseException:failures+=1
  if made_directory:
   try:
    require(stamp(retain.lstat())[:3]==directory_id,'ROLLBACK_DIRECTORY_CHANGED');retain.rmdir()
   except BaseException:failures+=1
  if failures:secondary(primary,'ROLLBACK_SECONDARY_FAILURES',failures)
  raise
def inspect(staging,payloads,control_pin,output,retain=None):
 require(re.fullmatch('[0-9a-f]{64}',control_pin) is not None,'CONTROL_FIXTURE_PIN');pins=source_pins();output=fresh(output);retain=fresh(retain) if retain is not None else None
 if retain is not None:require(output!=retain and retain not in output.parents and output not in retain.parents,'OUTPUT_OVERLAP')
 entries,bodies,admission,verify,roots=resolve_inputs(staging,payloads,control_pin)
 for path in [output]+([retain] if retain is not None else []):require(all(path!=root and root not in path.parents for root in roots),'OUTPUT_SOURCE_OVERLAP')
 with tempfile.TemporaryDirectory(prefix='coh-default-source-inspect-') as raw:native,binary_sha=native_inspection(bodies,Path(raw),pins)
 require(source_pins()==pins,'ADMITTER_SOURCE_CHANGED');verify()
 proof={'schema':'coh-staged-fixed-seven-header-admission-v1','passed':True,'admission':admission,'control_fixture_sha256':admission['control_fixture_sha256'],'client_work_receipt_sha256':admission['client_work_receipt_sha256'],'client_content_identity_sha256':admission['client_content_identity_sha256'],'source_sha256':pins,'source_revision':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'native_inspection':native,'native_executable_sha256':binary_sha,'optional_retention_independent_of_parser_support':True,'retained_fixed_seven':None,'inspection_owner_retired':True,'current_provider_generation':False,'original_scan_or_LWC_or_duplicate_precedence_verified':False,'namespace_complete':False,'default_identity':False,'material_authority':False,'GPU':False,'world_authority':False}
 def final_verify():verify();require(source_pins()==pins,'ADMITTER_SOURCE_CHANGED')
 publish(output,retain,entries,bodies,proof,final_verify);return proof
def failure_result(error):
 value={'passed':False,'failure_code':str(error) if isinstance(error,Refused) and re.fullmatch('[A-Z0-9_]+',str(error)) else 'DEPENDENCY_OR_SOURCE_FAILURE'};counts={}
 for note in getattr(error,'__notes__',()):
  match=re.fullmatch('(OUTPUT_CLOSE_SECONDARY_FAILURES|DIRECTORY_CLOSE_SECONDARY_FAILURES|ROLLBACK_SECONDARY_FAILURES)=([1-9][0-9]?)',note) if isinstance(note,str) else None
  if match and int(match[2])<=16:counts[match[1]]=int(match[2])
 if counts:value['secondary_failure_counts']=counts
 return value
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--staging-root',type=Path,required=True);p.add_argument('--payloads',type=Path,required=True);p.add_argument('--control-fixture-sha256',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--retain-directory',type=Path);a=p.parse_args()
 try:value=inspect(a.staging_root,a.payloads,a.control_fixture_sha256,a.output,a.retain_directory);print(json.dumps({'passed':True,'seven_source_bodies':7,'all_seven_header_owner_created':value['native_inspection']['seven_header_owner_created'],'fixed_seven_retained':value['retained_fixed_seven'] is not None,'current_provider_generation':False}));return 0
 except Exception as error:print(json.dumps(failure_result(error)));return 2
if __name__=='__main__':raise SystemExit(main())

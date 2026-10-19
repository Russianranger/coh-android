#!/usr/bin/env python3
"""Original body-part exact-cache-hit loader, with measured fixture provenance."""
import argparse,hashlib,importlib.util,json,os,platform,re,shlex,shutil,struct,subprocess,sys,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE='native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip'
ARCHIVE_SHA='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241';ARCHIVE_BLOB='606fd1e17751fbdf6d7c903dee4eaea40c2014f3'
BODY_SHA='b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError('BODY_PART_LOADER_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('body_part_loader_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(work):
 command=shutil.which('cc')
 if not command:raise ValueError('Compiler unavailable')
 path=Path(command).resolve();raw=path.read_bytes();version=run([path,'--version'])
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 (work/'cc-version.stdout').write_text(version.stdout)
 return {'command':'cc','resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
class Projection:
 """Independent expectation projection of trusted/synthetic cache fixture bytes."""
 def __init__(self,raw):self.raw=raw;self.at=0
 def take(self,n):
  if n<0 or n>len(self.raw)-self.at:raise ValueError('Fixture extent')
  out=self.raw[self.at:self.at+n];self.at+=n;return out
 def word(self):return struct.unpack('<I',self.take(4))[0]
 def text(self):
  begin=self.at;n=struct.unpack('<H',self.take(2))[0];value=self.take(n)
  if n>259 or b'\0'in value or not value.isascii():raise ValueError('Fixture string profile')
  self.take((4-(n+2)%4)%4);return value,begin+2
 def end(self):return self.word()+self.at
def project(raw):
 p=Projection(raw)
 if p.take(8)!=b'CrypticS'or p.word()!=0xcf27aba3 or p.text()[0]!=b'Parse6'or p.text()[0]!=b'Files1':raise ValueError('Fixture header')
 end=p.end();deps=[]
 for _ in range(p.word()):deps.append((p.text()[0],p.word()))
 if p.at!=end or len(deps)!=1:raise ValueError('Fixture dependency')
 end=p.end();count_at=p.at;count=p.word();rows=[]
 if not 0<count<=29:raise ValueError('Fixture count')
 for _ in range(count):
  extent_at=p.at;row_end=p.end();strings=[];positions=[]
  for _ in range(2):value,at=p.text();strings.append(value);positions.append(at)
  first=p.word();influence=p.word()
  for _ in range(3):value,at=p.text();strings.append(value);positions.append(at)
  numeric_at=p.at;last=p.word();dont=p.word();b0=p.word();b1=p.word();index=p.word()
  if p.at!=row_end:raise ValueError('Fixture row extent')
  rows.append({'strings':strings,'words':[first,influence,last,dont,b0,b1,index],'numeric_at':numeric_at,'extent_at':extent_at,'string_at':positions})
 if end!=p.at or end!=len(raw):raise ValueError('Fixture end')
 return {'deps':deps,'rows':rows,'count_at':count_at}
def fixtures(root,work):
 status_values={name:int(value)for name,value in re.findall(r'(COH_[A-Z_]+)\s*=\s*([0-9]+)',(root/'native-android/engine/coh_contracts.h').read_text())}
 if not all(name in status_values for name in('COH_OK','COH_INVALID','COH_LIMIT')):raise ValueError('Native status ABI absent')
 archive=root/ARCHIVE;packed=archive.read_bytes()
 if len(packed)!=2253704 or sha(packed)!=ARCHIVE_SHA or run(['git','-C',root,'rev-parse','HEAD:'+ARCHIVE]).stdout.strip()!=ARCHIVE_BLOB:raise ValueError('Exact retained CLIENT archive changed')
 with zipfile.ZipFile(archive)as z:
  members=z.infolist();inventory={'data/bin/BodyParts.bin':2584,'data/bin/costume.bin':17691352,'data/bin/supergroupColors.bin':2664}
  if len(members)!=3 or {i.filename:i.file_size for i in members}!=inventory or any(i.flag_bits&1 or i.is_dir()for i in members):raise ValueError('Exact subset inventory changed')
  raw=z.read('data/bin/BodyParts.bin')
 if len(raw)!=2584 or sha(raw)!=BODY_SHA:raise ValueError('Authentic CLIENT body bytes changed')
 original=project(raw);(work/'BodyParts.bin').write_bytes(raw);cases=[(status_values['COH_OK'],raw,original)]
 changed=bytearray(raw);at=original['rows'][0]['numeric_at'];struct.pack_into('<5I',changed,at,3,0x7f,0x76543210,0xabcdef01,0x11223344);cases.append((0,bytes(changed),project(changed)))
 changed=bytearray(raw);at=original['rows'][-1]['string_at'][2];changed[at:at+5]=b'XXXXX';cases.append((0,bytes(changed),project(changed)))
 cases.append((status_values['COH_INVALID'],raw[:-1],None))
 changed=bytearray(raw);struct.pack_into('<I',changed,original['rows'][-1]['extent_at'],0xffffffff);cases.append((status_values['COH_INVALID'],bytes(changed),None))
 changed=bytearray(raw);struct.pack_into('<I',changed,original['count_at'],30);cases.append((status_values['COH_LIMIT'],bytes(changed),None))
 changed=bytearray(raw);struct.pack_into('<I',changed,original['rows'][-1]['numeric_at']+4,256);cases.append((status_values['COH_LIMIT'],bytes(changed),None))
 path=work/'loader-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x314c5042,len(cases)))
  for i,(status,data,reference)in enumerate(cases):
   f.write(struct.pack('<IIII',i,status,len(data),len(reference['rows'])if reference else 0));f.write(bytes.fromhex(sha(data)));f.write(data)
   if reference:
    f.write(struct.pack('<I',len(reference['deps'])))
    for name,stamp in reference['deps']:f.write(struct.pack('<I',len(name)));f.write(name);f.write(struct.pack('<I',stamp))
    for row in reference['rows']:
     for value in row['strings']:f.write(struct.pack('<I',len(value)));f.write(value)
     f.write(struct.pack('<7I',*row['words']))
   manifest.append({'case':i,'expected_status':status,'bytes':len(data),'sha256':sha(data),'authentic_retained_CLIENT_input':i==0,'synthetic_modified_cache_control':i!=0})
 proof={'archive_path':ARCHIVE,'archive_bytes':len(packed),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'member':'data/bin/BodyParts.bin','member_bytes':len(raw),'member_sha256':BODY_SHA,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'authentic_rows':len(original['rows']),'fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'cases':manifest,'independent_expectations':'All retained strings, duplicate BoneCount first/last, influence cost, full serialized DontClear word, two raw bones/index and dependency fields projected independently from trusted exact bytes. Synthetic changes and recomputed hashes remain labelled; no old checker/native suite or original full Parse6 reader replay.','current_server_consumption_verified':False}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,hexvalue):return 'static const unsigned char '+name+'[32]={'+','.join(str(v)for v in bytes.fromhex(hexvalue))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 provider=module(HERE/'body_part_loader_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'test_body_part_loader.c',HERE/'body_part_loader_provider.py',HERE/'body-part-loader-source-pins.json',root/ARCHIVE,root/'native-android/engine/costume-inputs/coh_costume_inputs.c',root/'native-android/engine/costume-inputs/coh_costume_inputs.h',root/'native-android/engine/costume-inputs/source-pins.json',root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths}
 temporary=tempfile.TemporaryDirectory(prefix='coh-body-loader-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  tool=compiler(work);python_path=Path(sys.executable).resolve();host_environment={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_pointer_bytes':struct.calcsize('P'),'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False};wire,inputs=fixtures(root,work);generated,origin=provider.build(root,work);generated=Path(generated);source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Loader source pin changed')
   source_paths.add(path)
  decoder=root/'native-android/engine/costume-inputs/coh_costume_inputs.c';test=HERE/'test_body_part_loader.c';input_include=root/'native-android/engine/costume-inputs'
  # The identity header is build-derived below, deliberately outside the source
  # identity closure to avoid a circular executable/receipt self-hash.
  identity_stub=work/'loader-qualification-identity.h';identity_stub.write_text('/* dependency discovery only */\n')
  for source in(decoder,test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header=work/'body-part-loader-provider.h';header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())}
  source_identity={'schema':'coh-body-loader-fixture-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['loader-qualification-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-body-loader-fixture-profile-v1','shared_memory_branch':'controlled SMAR_Error','inner_loader_branch':'exact cache hit','native_decoder_bridge':'unchanged bounded coh_costume_input_read','preprocess_postprocess_finalprocess_calls':0,'input_max':65536,'row_policy_max':29,'copied_string_max':259,'materialized_U8_DontClear_max':255,'fixture_only':True,'current_Map_runtime_admitted':False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes)
  input_ledger_bytes=canonical(inputs);(work/'input-ledger.json').write_bytes(input_ledger_bytes);input_ledger_id=sha(input_ledger_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or generated.read_bytes()!=generated_raw or header.read_bytes()!=header_raw:raise ValueError('Source changed during loader qualification')
   if Path(shutil.which('cc')).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed during loader qualification')
   if sha(python_path.read_bytes())!=host_environment['python_executable_sha256']:raise ValueError('Python executable changed during loader qualification')
  checks={};bindings={};builds={};stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  common=['-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-unused-parameter','-Wno-parentheses','-pedantic','-fno-strict-aliasing']
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-body-loader-fixture-compile-profile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile))
   identity='/* Derived fixture self-measurement only; no runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',BODY_SHA),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_ledger_id),('fixture_compile_profile_id',compile_id)])
   (directory/'loader-qualification-identity.h').write_text(identity);exe=directory/'loader';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(decoder),str(test),'-lcrypto','-lm','-o',str(exe)];built=run(cmd);(directory/'compile.stdout').write_text(built.stdout);(directory/'compile.stderr').write_text(built.stderr)
   build={'schema':'coh-body-loader-fixture-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes)
   ledger=b'COHBLD1\0'+b''.join(bytes.fromhex(x)for x in(source_id,build_id,profile_id,nonce,BODY_SHA,build['executable_sha256'],input_ledger_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger)
   ran=run([exe,wire,directory/'run-ledger.bin',directory/'build.json',work/'input-ledger.json'],env=env)
   if ran.stderr or len(ran.stdout.encode())>4096:raise ValueError('Native output bound/refusal')
   (directory/'native.stdout').write_text(ran.stdout);(directory/'native.stderr').write_text(ran.stderr);result=json.loads(ran.stdout);checks[mode]=result['checks'];bindings[mode]=result['fixture_binding'];expected={'source_id':source_id,'build_id':build_id,'profile_id':profile_id,'run_id':nonce,'input_sha256':BODY_SHA,'fixture_sha256':inputs['fixture_sha256'],'executable_sha256':build['executable_sha256'],'input_ledger_sha256':input_ledger_id,'compile_profile_sha256':compile_id,'run_ledger_sha256':sha(ledger)}
   if bindings[mode]!=expected:raise ValueError('Child measured fixture association differs')
   builds[mode]=build;verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native check counts differ')
  for path in work.rglob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded native stack')
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};proof={'schema':'coh-original-body-part-cache-loader-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host_environment,'host_python_binary_stable_before_after':True,'host_compiler_identity':tool,'host_compiler_stable_before_after':True,'original_loader_provider':origin,'retained_authentic_CLIENT_input':inputs,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'evidence_files':files,'scope':'Bounded original bpReadBodyPartFiles -> ParserLoadFilesShared controlled SMAR_Error -> whole ParserLoadFiles exact-cache-hit source execution. Original binary-file backend replaced explicitly by unchanged already-qualified native cache decoder; all loaded source fields/order compared. Child measures own ELF and exact input/build/ledger bytes and matches compiled source/profile/random fixture-run identities. These are controlled fixture associations, not runtime attestation or evidence current MapServer consumed this CLIENT cache.','original_full_Parse6_reader_executed':False,'native_decoder_bridge_explicit':True,'preprocess_callback_executed':False,'old_checker_mains_executed':False,'old_native_suites_executed':False,'external_crypto_libc_sanitizer_or_stack_closure':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'authentic_rows':inputs['authentic_rows']}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

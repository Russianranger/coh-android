#!/usr/bin/env python3
"""Original SerializeReadOpen header-only leaf, measured fixture provenance."""
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
 if p.returncode:raise RuntimeError('BINARY_READ_OPEN_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('binary_read_open_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(work):
 command=shutil.which('cc')
 if not command:raise ValueError('Compiler unavailable')
 path=Path(command).resolve();raw=path.read_bytes();version=run([path,'--version'])
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 (work/'cc-version.stdout').write_text(version.stdout)
 return {'command':'cc','resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def fixtures(root,work):
 status={name:int(value)for name,value in re.findall(r'(COH_[A-Z_]+)\s*=\s*([0-9]+)',(root/'native-android/engine/coh_contracts.h').read_text())}
 if not all(name in status for name in('COH_OK','COH_INVALID','COH_LIMIT','COH_UNSUPPORTED')):raise ValueError('Native status ABI absent')
 archive=root/ARCHIVE;packed=archive.read_bytes()
 if len(packed)!=2253704 or sha(packed)!=ARCHIVE_SHA or run(['git','-C',root,'rev-parse','HEAD:'+ARCHIVE]).stdout.strip()!=ARCHIVE_BLOB:raise ValueError('Exact retained CLIENT archive changed')
 with zipfile.ZipFile(archive)as z:
  members=z.infolist();inventory={'data/bin/BodyParts.bin':2584,'data/bin/costume.bin':17691352,'data/bin/supergroupColors.bin':2664}
  if len(members)!=3 or {i.filename:i.file_size for i in members}!=inventory or any(i.flag_bits&1 or i.is_dir()for i in members):raise ValueError('Exact subset inventory changed')
  raw=z.read('data/bin/BodyParts.bin')
 if len(raw)!=2584 or sha(raw)!=BODY_SHA or raw[:20]!=b'CrypticS'+struct.pack('<IH',0xcf27aba3,6)+b'Parse6':raise ValueError('Authentic CLIENT header changed')
 (work/'BodyParts.bin').write_bytes(raw)
 cases=[]
 def add(label,data,build=0xcf27aba3,ignore=1,fault=0):
  # Independent framing and original strcmp/CRC predicate projection, not a
  # copied source implementation or a full-body decoder.
  end=0;failure=0;accepted=0
  if len(data)>65536:code,stage=status['COH_LIMIT'],1
  elif ignore>1 or fault>1:code,stage=status['COH_UNSUPPORTED'],3
  elif len(data)<14:code,stage=status['COH_INVALID'],4;failure=len(data)
  else:
   length=struct.unpack_from('<H',data,12)[0];end=14+length+(4-(length+2)%4)%4
   if length>=4096:code,stage=status['COH_LIMIT'],5;failure=12
   elif len(data)<end:code,stage=status['COH_INVALID'],6;failure=len(data)
   elif fault:code,stage=status['COH_UNSUPPORTED'],8
   else:
    actual=struct.unpack_from('<I',data,8)[0];kind=data[14:14+length].split(b'\0',1)[0]
    accepted=int(data[:8]==b'CrypticS' and kind==b'Parse6' and (ignore or actual==build))
    code,stage=(status['COH_OK'],10)if accepted else(status['COH_UNSUPPORTED'],9)
  cases.append({'label':label,'data':data,'build':build,'ignore':ignore,'fault':fault,'status':code,'stage':stage,'failure':failure,'end':end if accepted else 0,'accepted':accepted})
 def header(value,padding=None,crc=0xcf27aba3):
  pad=(4-(len(value)+2)%4)%4
  return b'CrypticS'+struct.pack('<IH',crc,len(value))+value+(bytes(pad)if padding is None else padding)
 add('authentic_CLIENT_complete_input_only_header_consumed',raw)
 add('authentic_header_exact_end_synthetic_extent',raw[:20])
 add('source_production_ignore_CRC_mismatch',raw,build=0)
 add('source_strict_CRC_equal',raw,ignore=0)
 add('source_strict_CRC_mismatch',raw,build=0,ignore=0)
 for i in range(8):
  changed=bytearray(raw[:20]);changed[i]^=0x80;add('synthetic_magic_byte_'+str(i),bytes(changed))
 for n in range(20):add('synthetic_truncated_authentic_header_'+str(n),raw[:n])
 for value in(b'',b'Parse',b'parse6',b'Parse6X',b'\xffParse6',b'Parse6\0',b'Parse6\0suffix',b'Parse6\0\xff',b'\0Parse6'):
  add('synthetic_type_'+value.hex(),header(value))
 add('synthetic_arbitrary_nonzero_padding',header(b'Parse6\0',b'\xa5\xff\x7f'))
 add('synthetic_max_safe_type_length_embedded_NUL',header(b'Parse6\0'+b'X'*4088,b'\xff'*3))
 add('synthetic_type_length4096_refused_before_source',b'CrypticS'+struct.pack('<IH',0xcf27aba3,4096))
 add('synthetic_type_length65535_refused_before_source',b'CrypticS'+struct.pack('<IH',0xcf27aba3,65535))
 add('synthetic_open_adapter_refusal',raw,fault=1)
 add('synthetic_unsupported_ignore_flag',raw,ignore=2)
 add('synthetic_unsupported_fault',raw,fault=2)
 add('synthetic_input_max_unused_tail',raw[:20]+bytes(65536-20))
 add('synthetic_input_overmax_unused_tail',raw[:20]+bytes(65537-20))
 # Full declared payload present but every required padding truncation is blocked.
 padded=header(b'Parse6\0')
 for n in range(21,24):add('synthetic_padding_truncated_'+str(n),padded[:n])
 path=work/'binary-open-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x314f5242,len(cases)))
  for i,c in enumerate(cases):
   data=c['data'];f.write(struct.pack('<10I',i,c['status'],c['stage'],c['failure'],c['end'],c['build'],c['ignore'],c['fault'],c['accepted'],len(data)));f.write(bytes.fromhex(sha(data)));f.write(data)
   manifest.append({k:v for k,v in c.items()if k!='data'}|{'case':i,'bytes':len(data),'sha256':sha(data),'authentic_retained_CLIENT_input':i==0,'synthetic_control':i!=0})
 if path.stat().st_size>262144:raise ValueError('Fixture bound')
 proof={'archive_path':ARCHIVE,'archive_bytes':len(packed),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'member':'data/bin/BodyParts.bin','member_bytes':len(raw),'member_sha256':BODY_SHA,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'authentic_headers':1,'authentic_header_consumed_bytes':20,'unused_suffix_bound_by_whole_input_hash':True,'fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'cases':manifest,'independent_expectations':'Header-only little-endian extent projection plus original C-string type/magic and strict/ignore CRC predicates. All synthetic controls explicitly labelled; no old checker/native suite or full-body decoder replay. ParseTableCRC not executed and raw comparison argument never presented as schema provenance.','current_server_consumption_verified':False}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,hexvalue):return 'static const unsigned char '+name+'[32]={'+','.join(str(v)for v in bytes.fromhex(hexvalue))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 provider=module(HERE/'binary_read_open_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'test_binary_read_open.c',HERE/'binary_read_open_provider.py',HERE/'binary-read-open-source-pins.json',root/ARCHIVE,root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths}
 temporary=tempfile.TemporaryDirectory(prefix='coh-binary-open-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  tool=compiler(work);python_path=Path(sys.executable).resolve();host_environment={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_pointer_bytes':struct.calcsize('P'),'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False};wire,inputs=fixtures(root,work);generated,origin=provider.build(root,work);generated=Path(generated);source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Binary header source pin changed')
   source_paths.add(path)
  test=HERE/'test_binary_read_open.c';input_include=root/'native-android/engine/costume-import'
  # The identity header is build-derived below, deliberately outside the source
  # identity closure to avoid a circular executable/receipt self-hash.
  identity_stub=work/'binary-open-qualification-identity.h';identity_stub.write_text('/* dependency discovery only */\n')
  for source in(test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header=work/'binary-read-open-provider.h';header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())}
  source_identity={'schema':'coh-binary-open-fixture-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['binary-open-qualification-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-binary-open-fixture-profile-v1','leaf':'unchanged original SerializeReadOpen + ReadPascalString + U16/U32/read/seek/tell','callsite':'ParserIsPersistNewer source audit only; original ParseTableCRC not executed','fixed_source_type':'Parse6','binary_backend':'explicit fixed-buffer open/close/growth adapters','input_max':65536,'declared_type_max':4095,'complete_header_preflight':True,'Files1_or_FileListRead_calls':0,'source_embedded_NUL_and_arbitrary_padding_semantics_preserved':True,'fixture_only':True,'current_Map_runtime_admitted':False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes)
  input_ledger_bytes=canonical(inputs);(work/'input-ledger.json').write_bytes(input_ledger_bytes);input_ledger_id=sha(input_ledger_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or generated.read_bytes()!=generated_raw or header.read_bytes()!=header_raw:raise ValueError('Source changed during binary-open qualification')
   if Path(shutil.which('cc')).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed during binary-open qualification')
   if sha(python_path.read_bytes())!=host_environment['python_executable_sha256']:raise ValueError('Python executable changed during binary-open qualification')
  checks={};bindings={};builds={};stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  common=['-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-unused-parameter','-pedantic','-fno-strict-aliasing']
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-binary-open-fixture-compile-profile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile))
   identity='/* Derived fixture self-measurement only; no runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',BODY_SHA),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_ledger_id),('fixture_compile_profile_id',compile_id)])
   (directory/'binary-open-qualification-identity.h').write_text(identity);exe=directory/'binary-open';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(test),'-lcrypto','-o',str(exe)];built=run(cmd);(directory/'compile.stdout').write_text(built.stdout);(directory/'compile.stderr').write_text(built.stderr)
   build={'schema':'coh-binary-open-fixture-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes)
   ledger=b'COHBRO1\0'+b''.join(bytes.fromhex(x)for x in(source_id,build_id,profile_id,nonce,BODY_SHA,build['executable_sha256'],input_ledger_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger)
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
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};proof={'schema':'coh-original-binary-read-open-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host_environment,'host_python_binary_stable_before_after':True,'host_compiler_identity':tool,'host_compiler_stable_before_after':True,'original_binary_header_provider':origin,'retained_authentic_CLIENT_input':inputs,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'evidence_files':files,'scope':'Bounded unchanged original SerializeReadOpen header leaf with fixed-buffer open/close/growth adapters. Only first20 authentic bytes consumed; whole2584-byte retained CLIENT input hash binds unused suffix. Original ParserIsPersistNewer callsite audited, not executed; original ParseTableCRC not executed. Child measures own ELF and exact input/build/ledger bytes against compiled source/profile/random fixture labels. Controlled fixture associations only, not runtime attestation or evidence current MapServer consumed cache.','original_full_Parse6_reader_executed':False,'native_fullbody_decoder_executed':False,'ParserIsPersistNewer_executed':False,'ParseTableCRC_executed':False,'Files1_or_FileListRead_executed':False,'old_checker_mains_executed':False,'old_native_suites_executed':False,'external_crypto_libc_sanitizer_or_stack_closure':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'authentic_headers':inputs['authentic_headers']}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

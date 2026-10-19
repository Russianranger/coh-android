#!/usr/bin/env python3
"""Original FileListRead bounded dependency stage, measured fixture provenance."""
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
 if p.returncode:raise RuntimeError('FILE_LIST_READ_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('file_list_read_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
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
 def pascal(value,padding=None):
  pad=(4-(len(value)+2)%4)%4
  if padding is not None and len(padding)!=pad:raise ValueError('Synthetic padding extent')
  return struct.pack('<H',len(value))+value+(bytes(pad)if padding is None else padding)
 def segment(rows=(),tag=b'Files1',declared=None,count=None,padding=None):
  payload=struct.pack('<I',len(rows)if count is None else count)+b''.join(pascal(path)+struct.pack('<I',date)for path,date in rows)
  return pascal(tag,padding)+struct.pack('<I',len(payload)if declared is None else declared)+payload
 def signed(value):return value if value<0x80000000 else value-0x100000000
 def cstr(value):return value.split(b'\0',1)[0]
 cases=[]
 def add(label,data,mode=1,build=0xcf27aba3,ignore=1):
  # Independently project ONLY entered bytes and source predicates. Native
  # execution still decides acceptance; no full-body reader or old main runs.
  c={'label':label,'data':data,'build':build,'ignore':ignore,'mode':mode,'status':status['COH_OK'],'stage':15,'failure':0,'header_end':0,'dependency_end':0,'count_observed':0,'count':0,'nodes':0,'reads':0,'seeks':0,'warnings':0,'header_accepted':0,'filelist_called':0,'source_result':0,'entries':[]}
  def refuse(code,stage,failure=0):c.update(status=status[code],stage=stage,failure=failure)
  if len(data)>65536:refuse('COH_LIMIT',1)
  elif ignore>1 or mode>1:refuse('COH_UNSUPPORTED',3)
  elif len(data)<14:refuse('COH_INVALID',4,len(data))
  else:
   length=struct.unpack_from('<H',data,12)[0];header_end=14+length+(4-(length+2)%4)%4
   if length>=4096:refuse('COH_LIMIT',5,12)
   elif len(data)<header_end:refuse('COH_INVALID',6,len(data))
   else:
    header_ok=data[:8]==b'CrypticS' and cstr(data[14:14+length])==b'Parse6' and (ignore or struct.unpack_from('<I',data,8)[0]==build)
    if not header_ok:
     refuse('COH_UNSUPPORTED',13);c.update(reads=4,seeks=1,header_end=header_end)
    else:
     at=header_end
     if len(data)-at<2:refuse('COH_INVALID',7,len(data))
     else:
      siglen=struct.unpack_from('<H',data,at)[0];sigat=at+2;sizeat=sigat+siglen+(4-(siglen+2)%4)%4
      if sizeat>len(data)or len(data)-sizeat<4:refuse('COH_INVALID',7,len(data))
      else:
       declared=signed(struct.unpack_from('<I',data,sizeat)[0]);at=sizeat+4
       if not mode:
        if declared<0:refuse('COH_UNSUPPORTED',8,sizeat)
        elif declared>len(data)-at:refuse('COH_INVALID',8,len(data))
        else:c.update(header_end=header_end,dependency_end=at+declared,reads=6,seeks=3,header_accepted=1,filelist_called=1,source_result=1)
       else:
        sigok=siglen<20 and cstr(data[sigat:sigat+siglen])==b'Files1'
        if not sigok or declared<=0:
         refuse('COH_UNSUPPORTED',14);c.update(header_end=header_end,dependency_end=at,reads=7-int(siglen>=20),seeks=2,warnings=int(siglen>=20),header_accepted=1,filelist_called=1)
        elif len(data)-at<4:refuse('COH_INVALID',9,len(data))
        else:
         countat=at;n=signed(struct.unpack_from('<I',data,at)[0]);at+=4
         if n>16:refuse('COH_LIMIT',9,countat)
         else:
          remaining=declared-4;entries=[];reads=8;seeks=2;warnings=0;bad_extent=False
          for _ in range(max(0,n)):
           if len(data)-at<2:bad_extent=True;break
           pathlen=struct.unpack_from('<H',data,at)[0];payload=at+2;amount=2+pathlen+(4-(pathlen+2)%4)%4
           if amount>len(data)-at or len(data)-at-amount<4:bad_extent=True;break
           path=cstr(data[payload:payload+pathlen])if pathlen<260 else b'';date=struct.unpack_from('<I',data,at+amount)[0]
           at+=amount+4;remaining-=amount+4;reads+=3-int(pathlen>=260);seeks+=1;warnings+=int(pathlen>=260)
           if remaining<0:break
           entries.append((path,date))
          if bad_extent:refuse('COH_INVALID',10,len(data))
          else:
           accepted=n>=0 and len(entries)==n and remaining==0
           c.update(header_end=header_end,dependency_end=at,reads=reads,seeks=seeks,warnings=warnings,header_accepted=1,filelist_called=1,nodes=len(entries),source_result=int(accepted))
           if accepted:c.update(count_observed=1,count=len(entries),entries=entries)
           else:refuse('COH_UNSUPPORTED',14)
  cases.append(c)
 header=raw[:20]
 add('authentic_CLIENT_actual_loader_NULL_skip',raw,0)
 add('authentic_CLIENT_explicit_fresh_collect_inspection',raw,1)
 add('synthetic_extent_exact_dependency_end_NULL',raw[:64],0)
 add('synthetic_extent_exact_dependency_end_collect',raw[:64],1)
 for mode in(0,1):add('synthetic_body_size_and_records_unentered_mode'+str(mode),raw[:64]+b'\xff'*32,mode)
 add('synthetic_production_ignore_CRC_difference',raw,0,build=0)
 add('synthetic_strict_CRC_equal',raw,1,ignore=0)
 add('synthetic_strict_CRC_difference_header_rejection',raw[:20],1,build=0,ignore=0)
 add('synthetic_unsupported_mode',raw,2)
 add('synthetic_unsupported_ignore_flag',raw,1,ignore=2)
 changed=bytearray(header);changed[0]^=0x80;add('synthetic_header_bad_magic',bytes(changed))
 changed=bytearray(header);changed[14]^=0x20;add('synthetic_header_bad_type',bytes(changed))
 add('synthetic_header_type_overlimit',b'CrypticS'+struct.pack('<IH',0xcf27aba3,4096))
 for n in range(64):add('synthetic_collect_truncated_authentic_'+str(n),raw[:n])
 for n in list(range(20,33))+[63]:add('synthetic_NULL_truncated_authentic_'+str(n),raw[:n],0)
 garbage=pascal(b'Wrong!')+struct.pack('<I',32)+b'\xff'*32
 for mode in(0,1):add('synthetic_NULL_opaque_bad_tag_and_count_mode'+str(mode),header+garbage,mode)
 for mode in(0,1):add('synthetic_zero_outer_extent_mode'+str(mode),header+pascal(b'Files1')+struct.pack('<I',0),mode)
 for mode in(0,1):add('synthetic_negative_outer_size_mode'+str(mode),header+pascal(b'Files1')+struct.pack('<I',0xffffffff),mode)
 for mode in(0,1):add('synthetic_large_unconsumed_outer_size_mode'+str(mode),header+segment(declared=0x7fffffff),mode)
 for mode in(0,1):add('synthetic_negative_count_mode'+str(mode),header+segment(count=0xffffffff),mode)
 for mode in(0,1):add('synthetic_observed_or_unobserved_empty_mode'+str(mode),header+segment(),mode)
 rows=[(b'z\\Path',0xffffffff),(b'a/../Mixed',0x80000000),(b'z\\Path',0)]
 for mode in(0,1):add('synthetic_order_duplicates_slashes_dates_mode'+str(mode),header+segment(rows),mode)
 paths=[(b'Prefix\0suffix',1),(b'\xffRaw',0x7fffffff),(b'',0),(b'A'*259,3),(b'B'*260,4),(b'C'*4096,5)]
 add('synthetic_path_prefix_rawbytes_259_260_and4096',header+segment(paths))
 padded_path=bytearray(header+segment([(b'P',0xffffffff)]));padded_path[39]=0xa5;add('synthetic_path_arbitrary_nonzero_padding',bytes(padded_path))
 add('synthetic_signature_NUL_and_arbitrary_padding',header+segment([(b'P',0)],tag=b'Files1\0',padding=b'\xff\xa5\x7f'))
 for length in(19,20):
  for mode in(0,1):add('synthetic_signature_length'+str(length)+'_mode'+str(mode),header+segment(tag=b'Files1\0'+b'X'*(length-7)),mode)
 for count in(16,17):
  for mode in(0,1):add('synthetic_count'+str(count)+'_mode'+str(mode),header+segment([(b'',i)for i in range(count)]),mode)
 two=[(b'first',1),(b'second',2)];data=segment(two);first_extent=len(pascal(two[0][0]))+4
 add('synthetic_source_partial_one_node_then_reject',header+segment(two,declared=4+first_extent))
 add('synthetic_source_remaining_nonzero_after_one_node',header+segment([two[0]],declared=5+first_extent))
 add('synthetic_source_negative_remaining_before_first_allocation',header+segment([two[0]],declared=1))
 bad=bytearray(header+segment(two));struct.pack_into('<H',bad,36+first_extent,65535);add('synthetic_late_path_extent_refused_before_source',bytes(bad))
 add('synthetic_late_date_truncated_before_source',(header+segment(two))[:-1])
 add('synthetic_input_max_unentered_tail',raw[:64]+bytes(65536-64))
 add('synthetic_input_overmax_unentered_tail',raw[:64]+bytes(65537-64),0)
 # Authentic independent facts, not values derived from native output.
 if raw[38:58]!=b'Defs/UI/bodyparts.bp'or struct.unpack_from('<I',raw,60)[0]!=1767225600:raise ValueError('Authentic dependency changed')
 if cases[0]['dependency_end']!=64 or cases[0]['count_observed']or cases[1]['entries']!=[(b'Defs/UI/bodyparts.bp',1767225600)]:raise ValueError('Independent authentic projection changed')
 path=work/'file-list-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x31524c46,len(cases)))
  for i,c in enumerate(cases):
   data=c['data'];keys=('status','stage','failure','build','ignore','mode','header_end','dependency_end','count_observed','count','nodes','reads','seeks','warnings','header_accepted','filelist_called','source_result')
   f.write(struct.pack('<19I',i,*[c[k]for k in keys],len(data)));f.write(bytes.fromhex(sha(data)));f.write(data)
   if c['status']==status['COH_OK']:
    for value,date in c['entries']:f.write(struct.pack('<I',len(value)));f.write(value);f.write(struct.pack('<I',date))
   manifest.append({k:v for k,v in c.items()if k not in('data','entries')}|{'entries':[{'path_hex':v.hex(),'date_bits':date,'seen':0}for v,date in c['entries']],'case':i,'bytes':len(data),'sha256':sha(data),'authentic_retained_CLIENT_input':i in(0,1),'synthetic_control':i not in(0,1)})
 if path.stat().st_size>262144:raise ValueError('Fixture bound')
 proof={'archive_path':ARCHIVE,'archive_bytes':len(packed),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'member':'data/bin/BodyParts.bin','member_bytes':len(raw),'member_sha256':BODY_SHA,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'authentic_input':1,'authentic_profiles':2,'authentic_header_end':20,'authentic_dependency_begin':20,'authentic_dependency_end':64,'authentic_collect_count':1,'authentic_collect_path':'Defs/UI/bodyparts.bp','authentic_collect_date_bits':1767225600,'NULL_count_unobserved':True,'unused_suffix_bound_by_whole_input_hash':True,'fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'cases':manifest,'independent_expectations':'Entered little-endian scalar/Pascal extent projection and source NULL skip versus fresh COLLECT semantics. NULL does not inspect tag/count/paths. COLLECT independently preserves order/duplicates/slashes/raw dates/seen0/C-string prefix, oversized path becomes empty. No old main/full-body decoder/freshness/normalization. Raw comparison CRC is not ParseTableCRC provenance.','current_server_consumption_verified':False}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,hexvalue):return 'static const unsigned char '+name+'[32]={'+','.join(str(v)for v in bytes.fromhex(hexvalue))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 provider=module(HERE/'file_list_read_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'test_file_list_read.c',HERE/'file_list_read_provider.py',HERE/'file-list-read-source-pins.json',root/ARCHIVE,root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths}
 temporary=tempfile.TemporaryDirectory(prefix='coh-file-list-read-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  tool=compiler(work);python_path=Path(sys.executable).resolve();host_environment={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_pointer_bytes':struct.calcsize('P'),'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False};wire,inputs=fixtures(root,work);generated,origin=provider.build(root,work);generated=Path(generated);source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('FileListRead source pin changed')
   source_paths.add(path)
  test=HERE/'test_file_list_read.c';input_include=root/'native-android/engine/costume-import'
  # The identity header is build-derived below, deliberately outside the source
  # identity closure to avoid a circular executable/receipt self-hash.
  identity_stub=work/'file-list-qualification-identity.h';identity_stub.write_text('/* dependency discovery only */\n')
  for source in(test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header=work/'file-list-read-provider.h';header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())}
  source_identity={'schema':'coh-file-list-read-fixture-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['file-list-qualification-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-file-list-read-fixture-profile-v1','leaf':'unchanged whole original FileListRead + dependency scalar/Pascal/header/data/skip functions','header_dependency':'SerializeReadOpen original functions only; prior header checker/test main not replayed','caller':'ParserReadBinaryFile + actual ParserLoadFiles NULL tuple source audit only','modes':{'0':'actual-loader NULL skip; count/path/tag unobserved','1':'explicit fresh collect inspection; not actual loader branch'},'fixed_source_header_type':'Parse6','fixed_source_list_signature':'Files1 only inspected in COLLECT','binary_backend':'explicit fixed-buffer open/close/no-growth and owned calloc/earray adapters','input_max':65536,'positive_count_policy_max':16,'source_path_width':260,'complete_entered_fields_preflight':True,'source_Cstring_prefix_oversized_empty_path_padding_order_duplicates_slashes_datebits_seen0_preserved':True,'body_or_FileListInsert_calls':0,'child_fixture_max':262144,'child_input_ledger_max':131072,'child_build_receipt_max':65536,'child_stdout_max':4096,'fixture_only':True,'current_Map_runtime_admitted':False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes)
  input_ledger_bytes=canonical(inputs);assert len(input_ledger_bytes)<=131072;(work/'input-ledger.json').write_bytes(input_ledger_bytes);input_ledger_id=sha(input_ledger_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or generated.read_bytes()!=generated_raw or header.read_bytes()!=header_raw:raise ValueError('Source changed during FileListRead qualification')
   if Path(shutil.which('cc')).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed during FileListRead qualification')
   if sha(python_path.read_bytes())!=host_environment['python_executable_sha256']:raise ValueError('Python executable changed during FileListRead qualification')
  checks={};bindings={};builds={};stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  common=['-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-unused-parameter','-pedantic','-fno-strict-aliasing']
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-file-list-read-fixture-compile-profile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile))
   identity='/* Derived fixture self-measurement only; no runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',BODY_SHA),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_ledger_id),('fixture_compile_profile_id',compile_id)])
   (directory/'file-list-qualification-identity.h').write_text(identity);exe=directory/'file-list';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(test),'-lcrypto','-o',str(exe)];built=run(cmd);(directory/'compile.stdout').write_text(built.stdout);(directory/'compile.stderr').write_text(built.stderr)
   build={'schema':'coh-file-list-read-fixture-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes)
   ledger=b'COHFLR1\0'+b''.join(bytes.fromhex(x)for x in(source_id,build_id,profile_id,nonce,BODY_SHA,build['executable_sha256'],input_ledger_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger)
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
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};compact_inputs={k:v for k,v in inputs.items()if k!='cases'};compact_inputs.update(case_count=len(inputs['cases']),full_fixture_reference={'path':'fixture-reference.json',**files['fixture-reference.json']},full_input_ledger={'path':'input-ledger.json',**files['input-ledger.json']});proof={'schema':'coh-original-file-list-read-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host_environment,'host_python_binary_stable_before_after':True,'host_compiler_identity':tool,'host_compiler_stable_before_after':True,'original_file_list_provider':origin,'retained_authentic_CLIENT_input':compact_inputs,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'evidence_files':files,'scope':'Bounded unchanged original FileListRead, actual-loader NULL skip versus explicit fresh COLLECT inspection. Authentic retained CLIENT header end20/dependency end64; NULL only skips opaque extent and does not validate tag/count/paths. COLLECT returns one path/date/seen0; no freshness or runtime admission. Only original SerializeReadOpen prefix/dependencies composed; prior checker/test mains never replayed. Whole2584-byte input hash binds unused body suffix, which remains unparsed. Whole ParserReadBinaryFile and ParserLoadFiles NULL call tuple pinned/audited, not executed. Child self-measured source/input/ELF/build/profile/random fixture-run labels are controlled fixture associations, not runtime attestation or current Map consumption.','original_FileListRead_executed':True,'original_header_dependency_executed':True,'NULL_dependency_count_or_paths_validated':False,'collect_is_explicit_inspection_profile':True,'original_ParserReadBinaryFile_executed':False,'original_ParserReadBinaryTable_executed':False,'original_full_Parse6_reader_executed':False,'native_fullbody_decoder_executed':False,'ParseTableCRC_executed':False,'original_FileListInsert_executed':False,'filesystem_normalization_or_freshness_executed':False,'old_checker_mains_executed':False,'old_native_suites_executed':False,'external_crypto_libc_sanitizer_or_stack_closure':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'authentic_dependency_end':inputs['authentic_dependency_end']}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Focused original FileListLength/FileListDestroy qualification; no old checker mains."""
import argparse,hashlib,importlib.util,json,os,platform,shlex,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def run(args,record=None,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if record:
  Path(str(record)+'.stdout').write_text(p.stdout);Path(str(record)+'.stderr').write_text(p.stderr);Path(str(record)+'.command.json').write_bytes(canonical({'argv':list(map(str,args)),'returncode':p.returncode}))
 if p.returncode:raise RuntimeError('FILE_LIST_LIFECYCLE_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('file_list_lifecycle_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(work):
 command=shutil.which('cc')
 if not command:raise ValueError('Compiler unavailable')
 path=Path(command).resolve();raw=path.read_bytes();version=run([path,'--version'],record=work/'cc-version')
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 return{'command':'cc','resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def fixtures(work):
 # Independent linear fixture oracle. First normalized lowercase key retains
 # spelling/date; Python sorting supplies the release order, not source Search.
 cases=[]
 def op(kind,path=b'',date=1,length=None):return{'kind':kind,'path':path,'date':date,'length':len(path)if length is None else length}
 I=lambda p,d=1:op(1,p,d);F=lambda p:op(2,p);S=lambda p:op(3,p)
 def add(label,ops=(),directory=b'C:/data',fault=0,count=None,dl=None,mode=0,patch=None):
  count=len(ops)if count is None else count;dl=len(directory)if dl is None else dl
  raw=bytearray(struct.pack('<4I',count,dl,fault,mode)+directory.ljust(260,b'\0'))
  for v in ops:raw+=struct.pack('<3I',v['kind'],v['length'],v['date'])+v['path'].ljust(520,b'\0')
  raw+=bytes(532*(32-len(ops)))
  if len(raw)!=17300:raise ValueError('Fixture request bound')
  if patch:raw[patch[0]]=patch[1]
  status=0;stage=9;failed=0;res=reserved=unique=reported=0;inserts=0;mapping={};rows=[]
  def refuse(code,where):
   nonlocal status,stage
   status=code;stage=where
  def valid(value,n,cap):return n<cap and n<=len(value)and(n==len(value)or value[n]==0)and all(0<x<128 for x in value[:n])
  if count>32:refuse(4,3)
  elif not valid(directory,dl,260):refuse(1,4)
  else:
   for i,v in enumerate(ops):
    failed=i;path=v['path'];n=v['length'];kind=v['kind']
    if kind not in(1,2,3):refuse(2,3);break
    if not valid(path,n,520):refuse(1,4);break
    path=path[:n]
    if kind==1 and path.lower().startswith(directory[:dl].lower()):
     path=path[dl:]
     if path[:1]in(b'/',b'\\'):path=path[1:]
    if len(path)>=260:refuse(4,4);break
    if kind==1:
     if not v['date']:refuse(2,5);break
     inserts+=1
     if inserts>16:refuse(4,5);break
     path=path.replace(b'\\',b'/');mapping.setdefault(path.lower(),(path,v['date']))
   if not status and fault>inserts+1:refuse(2,3)
   if not status:
    reported=mode
    if mode>2:refuse(2,7)
    elif mode==1 and count or mode==2 and len(mapping)==16:refuse(4,7)
    elif fault:res=fault;refuse(4,8)
    else:
     res=inserts+1;reserved=inserts;unique=len(mapping);failed=0;rows=[mapping[key]for key in sorted(mapping)]
     if mode==2:rows.append((b'',0))
  if patch:status=1;stage=4;failed=0;res=reserved=unique=reported=0;rows=[]
  expected=struct.pack('<I',len(rows))+b''.join(path.ljust(260,b'\0')+struct.pack('<I',date)for path,date in rows)+bytes(264*(16-len(rows)))
  if len(expected)!=4228:raise ValueError('Fixture result bound')
  cases.append({'label':label,'raw':bytes(raw),'expected':expected,'status':status,'stage':stage,'failed_operation':failed,'reservation_calls':res,'reserved_nodes':reserved,'unique_nodes':unique,'reported_mode':reported,'rows':[{'path_hex':path.hex(),'date_bits':date}for path,date in rows],'inserts':inserts,'fixture_mode':mode})
 add('owned_empty_array')
 add('NULL_handle_length_and_repeated_destroy',mode=1)
 add('single_negative_date',[I(b'Only',0xffffffff)])
 add('multiple_sorted_release',[I(b'Zulu',0x80000000),I(b'alpha',0x7fffffff),I(b'Beta',0xffffffff)])
 add('duplicate_suppression_retains_first',[I(b'C:/data/a\\B',4),I(b'A/b',99),I(b'A/B',0x80000000)])
 add('empty_NULL_slot',mode=2)
 add('nested_path_and_NULL_slot',[I(b'X\\nested\\file',7),I(b'a',0x80000000)],mode=2)
 add('NULL_slot_duplicate_suppressed',[I(b'SAME',3),I(b'same',4)],mode=2)
 for names in[(b'a',b'b',b'c'),(b'c',b'b',b'a'),(b'b',b'a',b'c'),(b'c',b'a',b'b'),(b'b',b'c',b'a'),(b'a',b'c',b'b')]:add('release_order_'+b''.join(names).decode(),[I(name,i+1)for i,name in enumerate(names)])
 add('max16_owned',[I(bytes([c]),0x80000000+c)for c in range(80,64,-1)])
 add('max15_and_NULL_slot',[I(bytes([c]),c)for c in range(79,64,-1)],mode=2)
 add('16duplicates_one_original_free',[I(b'A'if i%2 else b'a',i+1)for i in range(16)])
 add('source_prefix_and_queries',[I(b'c:/DATA\\Beta',5),I(b'alpha',7),F(b'BETA'),S(b'Alpha'),F(b'missing')])
 add('source_prefix_no_component_boundary',[I(b'C:/database',7),I(b'base',99)])
 add('empty_path',[I(b'C:/data',0xffffffff),I(b'',9)])
 add('single_slash_only',[I(b'\\',2)])
 add('dots_repeated_slash_literal',[I(b'a//../B',3),I(b'A\\b',4)])
 add('path259',[I(b'x'*259,5)])
 add('stripped_raw519',[I(b'd'*259+b'/'+b'z'*259,7)],directory=b'd'*259)
 for mode in range(3,8):add(('borrowed_node','borrowed_header','compressed_flag','invalid_count','invalid_capacity')[mode-3],[I(b'x')],mode=mode)
 add('unknown_mode_UINTMAX',mode=0xffffffff)
 add('NULL_handle_operations_refusal',[I(b'x')],mode=1)
 add('NULL_slot_capacity_refusal',[I(bytes([c]),c)for c in range(80,64,-1)],mode=2)
 for n in(1,2,8,17):add('partial_reservation_cleanup_'+str(n),[I(str(i).encode(),i+1)for i in range(16)],fault=n)
 for n in(1,2,3,4):add('duplicate_reservation_cleanup_'+str(n),[I(b'x',i+1)for i in range(3)],fault=n)
 add('NULL_handle_reservation_refusal',mode=1,fault=1)
 add('path260_refusal',[I(b'p'*260)])
 add('Find_path260_refusal',[F(b'p'*260)])
 add('source_zero_date_refusal',[I(b'x',0)])
 add('duplicate_zero_date_refusal',[I(b'x',1),I(b'X',0)])
 add('17_INSERT_refusal',[I(b'x',i+1)for i in range(17)])
 add('invalid_kind',[op(4,b'x')])
 add('invalid_count',count=33)
 add('invalid_directory_length',dl=260)
 add('nonASCII_directory',directory=b'C:/d\xff')
 add('nonASCII_path',[I(b'x\xff')])
 add('embedded_NUL',[I(b'a\0b')])
 add('path_length_UINTMAX',[op(1,b'x',length=0xffffffff)])
 add('invalid_reservation_fault',[I(b'x')],fault=3)
 add('missing_terminator',[I(b'x')],patch=(276+12+1,ord('x')))
 path=work/'file-list-lifecycle-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x314c4c46,len(cases)))
  for i,c in enumerate(cases):
   f.write(struct.pack('<8I',i,c['status'],c['stage'],c['failed_operation'],c['reservation_calls'],c['reserved_nodes'],c['unique_nodes'],c['reported_mode']));f.write(bytes.fromhex(sha(c['raw'])));f.write(c['raw'])
   if not c['status']:f.write(c['expected'])
   manifest.append({k:v for k,v in c.items()if k not in('raw','expected')}|{'case':i,'input_bytes':len(c['raw']),'input_sha256':sha(c['raw']),'expected_sha256':sha(c['expected'])if not c['status']else None,'synthetic_control':True})
 if path.stat().st_size>4*1024*1024:raise ValueError('Fixture bound')
 proof={'schema':'coh-file-list-lifecycle-input-v1','fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'first_input_sha256':sha(cases[0]['raw']),'request_bytes':17300,'result_bytes':4228,'case_count':len(cases),'cases':manifest,'independent_expectations':'Python first lowercase normalized key retains original spelling/date; sorted unique keys specify original free order; optional final NULL slot contributes length but no node free. Empty allocated and NULL-handle lists distinct. All synthetic, no FS/freshness.'}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,value):return'static const unsigned char '+name+'[32]={'+','.join(str(x)for x in bytes.fromhex(value))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 temporary=tempfile.TemporaryDirectory(prefix='coh-file-list-lifecycle-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  provider=module(HERE/'file_list_lifecycle_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'file_list_lifecycle_provider.py',HERE/'file-list-lifecycle-source-pins.json',HERE/'test_file_list_lifecycle.c',HERE/'file_list_ops_provider.py',HERE/'file-list-ops-source-pins.json',root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths};tool=compiler(work);python_path=Path(sys.executable).resolve();host={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False}
  if sys.byteorder!='little':raise ValueError('Typed fixture profile is little-endian')
  wire,inputs=fixtures(work);generated,origin=provider.build(root,work);generated=Path(generated);header=work/'file-list-lifecycle-provider.h';test=HERE/'test_file_list_lifecycle.c';input_include=root/'native-android/engine/costume-import';source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Source pin changed')
   source_paths.add(path)
  (work/'file-list-lifecycle-identity.h').write_text('/* dependency discovery only */\n')
  for source in(test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())};source_identity={'schema':'coh-file-list-lifecycle-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['file-list-lifecycle-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema': 'coh-file-list-lifecycle-profile-v1', 'original_functions': ['FileListCreate', 'FileListSearch', 'FileListInsert', 'FileListFind', 'FileListLength', 'FileListDestroy', 'eaClearExDbg', 'eaDestroyExDbg', 'eaDestroyDbg'], 'exact_original_EArray_layout_and_macros': True, 'PRIVATE_EARRAY_HEAP': 0, 'EARRAY_CRAZY_DEBUGGING': False, 'fixture_modes': {'0': 'owned allocated header', '1': 'NULL handle with zero operations', '2': 'append one NULL slot', '3..7': 'borrowed/compressed/bad count/capacity pre-source refusals'}, 'original_NULL_destructor_frees_nodes_in_source_order': True, 'actual_host_free_called_from_checked_adapters': True, 'source_allocator_and_engine_heap_closure': False, 'reservation_faults_before_all_originals_cleanup_partial_host_allocations': True, 'output_pointer_free_atomic_after_cleanup': True, 'operation_max': 32, 'INSERT_call_max': 16, 'node_and_capacity_max': 16, 'raw_path_max': 519, 'directory_and_poststrip_max': 259, 'nonzero_signed32_fixture_dates_only': True, 'typed_request_bytes': 17300, 'typed_result_bytes': 4228, 'budget_max': 1048576, 'own_stack_reserve': 16384, 'all_paths_preflight_before_source': True, 'old_checker_mains_or_broad_suites_executed': False, 'filesystem_access': False, 'current_Map_runtime_admitted': False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes);input_bytes=canonical(inputs)
  if len(input_bytes)>131072:raise ValueError('Input ledger bound')
  (work/'input-ledger.json').write_bytes(input_bytes);input_id=sha(input_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or generated.read_bytes()!=generated_raw or header.read_bytes()!=header_raw:raise ValueError('Source changed during qualification')
   if Path(shutil.which('cc')).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed')
   if sha(python_path.read_bytes())!=host['python_executable_sha256']:raise ValueError('Python executable changed')
  common=['-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-pedantic','-fno-strict-aliasing'];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C');checks={};bindings={};builds={};stack=[]
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-file-list-lifecycle-compile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile));identity='/* Controlled fixture labels; not runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',inputs['first_input_sha256']),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_id),('fixture_compile_profile_id',compile_id)]);(directory/'file-list-lifecycle-identity.h').write_text(identity);exe=directory/'file-list-lifecycle';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(test),'-lcrypto','-o',str(exe)];run(cmd,record=directory/'compile')
   build={'schema':'coh-file-list-lifecycle-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes);ledger=b'COHFLL1\0'+b''.join(bytes.fromhex(v)for v in(source_id,build_id,profile_id,nonce,inputs['first_input_sha256'],build['executable_sha256'],input_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger);ran=run([exe,wire,directory/'run-ledger.bin',directory/'build.json',work/'input-ledger.json'],record=directory/'native',env=env)
   if ran.stderr or len(ran.stdout.encode())>4096:raise ValueError('Native output bound/refusal')
   result=json.loads(ran.stdout);checks[mode]=result['checks'];bindings[mode]=result['fixture_binding'];expected={'source_id':source_id,'build_id':build_id,'profile_id':profile_id,'run_id':nonce,'input_sha256':inputs['first_input_sha256'],'fixture_sha256':inputs['fixture_sha256'],'executable_sha256':build['executable_sha256'],'input_ledger_sha256':input_id,'compile_profile_sha256':compile_id,'run_ledger_sha256':sha(ledger)}
   if bindings[mode]!=expected:raise ValueError('Child measured association differs')
   builds[mode]=build;verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native check counts differ')
  for path in work.rglob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');stack.append({'translation_unit':path.name,'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded native stack')
  own_frame=next(row['bytes']for row in stack if row['function']=='filelifecycle_apply')
  provider_frame_sum=sum(row['bytes']for row in stack if 'provider' in row['translation_unit'])
  if own_frame>16384 or provider_frame_sum>16384:raise ValueError('Own provider frames exceed charged stack reserve')
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};proof={'schema':'coh-original-file-list-lifecycle-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host,'host_compiler_identity':tool,'compiler_and_python_stable_before_after':True,'original_provider':origin,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'inputs':{k:v for k,v in inputs.items()if k!='cases'},'full_fixture_reference':files['fixture-reference.json'],'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'conservative_sum_of_all_measured_provider_frames':provider_frame_sum,'evidence_files':files,'scope':'Original FileListLength/FileListDestroy with exact original EArray layout/macros and original eaClearExDbg/eaDestroyExDbg/eaDestroyDbg. Supported host free adapters own every node and header; source frees nodes in ascending list order, nulls slots/count, releases header and nulls caller handle. NULL handle and NULL slots tested. Partial reservation cleanup and malformed borrowed/compressed profiles refuse before all originals. Constructor/ASCII/slash adapters remain explicit. Engine allocator, heap, platform ABI, filesystem scanning/freshness and runtime admission unqualified.','ASan_LeakSanitizer_enabled':False,'LeakSanitizer_exclusion_reason':'Established host ptrace limitation; detect_leaks=0. No leak closure claim.','external_libc_crypto_sanitizer_stack_or_device_RSS_qualified':False,'original_Win32_or_Android_ABI_qualified':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'dictionary_generation_admitted':False,'complete_initial_character':False,'selected_owner_admitted':False,'actor_publication':False,'application_ACK':False,'world_authority':False,'gates_1_through_24_preserved':True,'gates_25_through_27_open':True,'ALLENTS_41_43_and_dictionary_index_stops_unchanged':True}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

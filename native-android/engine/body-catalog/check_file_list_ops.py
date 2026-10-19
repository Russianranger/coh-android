#!/usr/bin/env python3
"""Focused original FileList operations qualification; no old checker mains."""
import argparse,hashlib,importlib.util,json,os,platform,shlex,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def run(args,record=None,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if record:
  Path(str(record)+'.stdout').write_text(p.stdout);Path(str(record)+'.stderr').write_text(p.stderr);Path(str(record)+'.command.json').write_bytes(canonical({'argv':list(map(str,args)),'returncode':p.returncode}))
 if p.returncode:raise RuntimeError('FILE_LIST_OPS_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('file_list_ops_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(work):
 command=shutil.which('cc')
 if not command:raise ValueError('Compiler unavailable')
 path=Path(command).resolve();raw=path.read_bytes();version=run([path,'--version'],record=work/'cc-version')
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 return{'command':'cc','resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def fixtures(work):
 # Independent sorted-list model uses insertion order/bisect-style linear
 # lower-bound, not a translation or invocation of original binary search.
 cases=[]
 def op(kind,path=b'',date=1,length=None):return{'kind':kind,'path':path,'date':date,'length':len(path)if length is None else length}
 I=lambda p,d=1:op(1,p,d);F=lambda p:op(2,p);S=lambda p:op(3,p)
 def add(label,ops=(),directory=b'C:/data',fault=0,count=None,dir_length=None,patch=None):
  count=len(ops)if count is None else count;dl=len(directory)if dir_length is None else dir_length
  if len(directory)>260 or len(ops)>32:raise ValueError('fixture construction bound')
  raw=bytearray(struct.pack('<III',count,dl,fault)+directory.ljust(260,b'\0'))
  for v in ops:raw+=struct.pack('<III',v['kind'],v['length'],v['date'])+v['path'].ljust(520,b'\0')
  raw+=bytes(532*(32-len(ops)))
  if len(raw)!=17296:raise ValueError('typed fixture width')
  if patch:
   at,value=patch;raw[at]=value
  status=0;stage=8;failed=0;reservations=0;reserved=0;rows=[];answers=[];inserts=0
  def refuse(code,where):
   nonlocal status,stage
   status=code;stage=where
  def valid(value,length,cap):return length<cap and len(value)<=cap and length<=len(value) and (length==len(value)or value[length]==0) and all(0<x<128 for x in value[:length])
  if count>32:refuse(4,3)
  elif not valid(directory,dl,260):refuse(1,4)
  else:
   for i,v in enumerate(ops):
    failed=i;p=v['path'];n=v['length'];kind=v['kind']
    if kind not in(1,2,3):refuse(2,3);break
    if not valid(p,n,520):refuse(1,4);break
    p=p[:n]
    if kind==1 and p.lower().startswith(directory[:dl].lower()):
     p=p[dl:]
     if p[:1]in(b'/',b'\\'):p=p[1:]
    if len(p)>=260:refuse(4,4);break
    if kind==1:
     if not v['date']:refuse(2,5);break
     inserts+=1
     if inserts>16:refuse(4,5);break
   if not status and fault>inserts+1:refuse(2,3)
   if not status:
    if fault:reservations=fault;refuse(4,7)
    else:
     reservations=inserts+1;reserved=inserts;failed=0
     for v in ops:
      p=v['path'][:v['length']];kind=v['kind'];inserted=0
      if kind==1:
       if p.lower().startswith(directory[:dl].lower()):
        p=p[dl:]
        if p[:1]in(b'/',b'\\'):p=p[1:]
       p=p.replace(b'\\',b'/')
      elif kind==2:p=p.replace(b'\\',b'/')
      key=p.lower();index=sum(row[0].lower()<key for row in rows);found=int(index<len(rows)and rows[index][0].lower()==key)
      if kind==1 and not found:rows.insert(index,(p,v['date']));inserted=1
      date=rows[index][1]if found or inserted else 0
      answers.append((found,index if kind!=2 or found else 0xffffffff,len(rows),inserted,date))
  if patch:
   # Only used for terminator corruption after explicit n=length validation.
   status=1;stage=4;failed=0;reservations=reserved=0;rows=[];answers=[]
  expected=struct.pack('<I',len(rows))
  for p,date in rows:expected+=p.ljust(260,b'\0')+struct.pack('<II',date,0)
  expected+=bytes(268*(16-len(rows)))
  for answer in answers:expected+=struct.pack('<5I',*answer)
  expected+=bytes(20*(32-len(answers)))
  if len(expected)!=4932:raise ValueError('result fixture width')
  cases.append({'label':label,'raw':bytes(raw),'expected':expected,'status':status,'stage':stage,'failed_operation':failed,'reservations':reservations,'reserved_nodes':reserved,'rows':[{'path_hex':p.hex(),'date_bits':d}for p,d in rows],'operations':ops,'directory_hex':directory.hex()})
 add('mixedcase_sorted_insert_duplicate_find_search',[I(b'Zulu',11),I(b'c:/DATA\\bETA',22),I(b'alpha',33),I(b'BETA',99),F(b'BeTa'),S(b'BETa'),S(b'between'),F(b'missing'),F(b'C:/data/beta')])
 add('empty_list_no_operations')
 add('empty_find_and_search',[F(b''),S(b''),F(b'unknown'),S(b'unknown')])
 add('empty_paths_and_duplicate',[I(b'C:/data',7),I(b'',99),F(b''),S(b''),I(b'C:/data/',88)])
 for order in[(b'a',b'b',b'c'),(b'c',b'b',b'a'),(b'b',b'a',b'c'),(b'c',b'a',b'b'),(b'b',b'c',b'a'),(b'a',b'c',b'b')]:add('insertion_positions_'+b''.join(order).decode(),[I(p,i+1)for i,p in enumerate(order)]+[S(p)for p in(b'0',b'a',b'aa',b'b',b'bb',b'c',b'z')])
 add('max_nodes_descending_and_all_find',[I(bytes([c]),c)for c in range(80,64,-1)]+[F(bytes([c+32]))for c in range(65,81)])
 for p in[b'0',b'A',b'a/a',b'H',b'h/h',b'P',b'Z']:
  add('sixteen_node_search_'+p.hex(),[I(bytes([c]),c)for c in range(65,81)]+[S(p),F(p)])
 for directory,path in[(b'data',b'database/x'),(b'C:/data',b'C:\\data\\x'),(b'data',b'data//x'),(b'data',b'data\\\\x'),(b'data/',b'DATA/one'),(b'',b'/one'),(b'',b'\\one'),(b'',b'//one'),(b'data',b'daTAx'),(b'data',b'/data/x'),(b'data',b'data/../x')]:add('literal_prefix_'+directory.hex()+'_'+path.hex(),[I(path,0xffffffff),F(path),S(path)],directory)
 add('dots_repeated_separators_case_preserved',[I(b'A\\..\\B//C',0x80000000),I(b'a/../b//c',7),F(b'a\\..\\b//c'),S(b'a\\..\\b//c'),S(b'a/../b//c')])
 for n in(0,1,258,259):add('path_boundary_accept_'+str(n),[I(b'X'*n,0x7fffffff),F(b'x'*n),S(b'x'*n)])
 add('raw519_poststrip259_accept',[I(b'D'*259+b'/'+b'X'*259),F(b'X'*259)],b'D'*259)
 add('raw260_poststrip258_accept',[I(b'D/'+b'X'*258),F(b'X'*258)],b'D')
 add('raw_prefix_long_source_path_empty',[I(b'D'*259),F(b'')],b'D'*259)
 add('duplicate_nonzero_dates_preserve_first',[I(b'p',0xffffffff),I(b'P',1),F(b'p')])
 for n in(260,261,519):
  for kind in(1,2,3):add('path_limit_kind'+str(kind)+'_'+str(n),[op(kind,b'X'*n)])
 add('path_raw_cap_refusal',[op(1,b'X'*520)])
 add('poststrip260_refusal',[I(b'D/'+b'X'*260)],b'D')
 add('zero_date_new_preflight',[I(b'p',0)])
 add('zero_date_duplicate_preflight',[I(b'p'),I(b'P',0)])
 add('late_unsafe_path_refuses_before_create',[I(b'safe'),F(b'X'*260)])
 add('date_signed_bit_patterns',[I(b'a',0x80000000),I(b'b',0xffffffff),I(b'c',0x7fffffff)])
 add('kind_zero_refusal',[op(0,b'p')]);add('kind_four_refusal',[op(4,b'p')]);add('count33_refusal',count=33)
 add('seventeenth_insert_conservative_limit',[I(str(i).encode())for i in range(17)])
 add('seventeenth_duplicate_conservative_limit',[I(b'p')for i in range(17)])
 add('path_NUL_refusal',[I(b'p\0x')]);add('path_nonASCII_refusal',[I(b'p\xff')]);add('directory_NUL_refusal',directory=b'd\0x');add('directory_nonASCII_refusal',directory=b'\xff')
 add('directory260_refusal',directory=b'D'*260);add('path_length_UINTMAX_refusal',[op(1,b'p',length=0xffffffff)]);add('directory_length_UINTMAX_refusal',dir_length=0xffffffff)
 add('path_missing_terminator_refusal',[I(b'p')],patch=(272+12+1,ord('x')))
 add('invalid_reservation_fault_profile',[I(b'p')],fault=3)
 for fault in range(1,18):add('owned_reservation_failure_'+str(fault),[I(str(i).encode(),i+1)for i in range(16)],fault=fault)
 path=work/'file-list-ops-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x31504f46,len(cases)))
  for i,c in enumerate(cases):
   f.write(struct.pack('<6I',i,c['status'],c['stage'],c['failed_operation'],c['reservations'],c['reserved_nodes']));f.write(bytes.fromhex(sha(c['raw'])));f.write(c['raw'])
   if not c['status']:f.write(c['expected'])
   manifest.append({k:v for k,v in c.items()if k not in('raw','expected','operations')}|{'case':i,'input_bytes':len(c['raw']),'input_sha256':sha(c['raw']),'expected_sha256':sha(c['expected'])if not c['status']else None,'synthetic_control':True,'operation_kinds':[o['kind']for o in c['operations']]})
 if path.stat().st_size>4*1024*1024:raise ValueError('Fixture bound')
 proof={'schema':'coh-file-list-ops-input-v1','fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'first_input_sha256':sha(cases[0]['raw']),'request_bytes':17296,'result_bytes':4932,'case_count':len(cases),'cases':manifest,'independent_expectations':'ASCII lowercase keys, independent linear lower-bound in sorted unique rows; literal raw prefix removal before slash replacement; Find slash-only versus Search literal path; duplicate original spelling/date; no filesystem timestamps. Full fixed request including unused bytes hashed. All fixtures synthetic, no current dependency freshness or source selection established.'}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,value):return'static const unsigned char '+name+'[32]={'+','.join(str(x)for x in bytes.fromhex(value))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 temporary=tempfile.TemporaryDirectory(prefix='coh-file-list-ops-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  provider=module(HERE/'file_list_ops_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'file_list_ops_provider.py',HERE/'file-list-ops-source-pins.json',HERE/'test_file_list_ops.c',root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths};tool=compiler(work);python_path=Path(sys.executable).resolve();host={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False}
  if sys.byteorder!='little':raise ValueError('Typed fixture profile is little-endian')
  wire,inputs=fixtures(work);generated,origin=provider.build(root,work);generated=Path(generated);header=work/'file-list-ops-provider.h';test=HERE/'test_file_list_ops.c';input_include=root/'native-android/engine/costume-import';source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Source pin changed')
   source_paths.add(path)
  (work/'file-list-ops-identity.h').write_text('/* dependency discovery only */\n')
  for source in(test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())};source_identity={'schema':'coh-file-list-ops-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['file-list-ops-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-file-list-ops-profile-v1','original_functions':['FileListCreate','FileListSearch','FileListInsert','FileListFind'],'fixed_owner_shells':['calloc','eaCreate','eaSize','eaInsert','fileDataDir','ASCII stricmp/strnicmp','forwardSlashes (implementation absent from snapshot)'],'filesystem_timestamp_trap':True,'source_date_zero_excluded_even_duplicates':True,'operation_max':32,'INSERT_call_max':16,'node_max':16,'raw_path_max':519,'directory_max':259,'post_strip_INSERT_path_max':259,'FIND_SEARCH_path_max':259,'typed_request_bytes':17296,'typed_result_bytes':4932,'budget_max':1048576,'own_stack_reserve':16384,'all_paths_preflight_before_source':True,'source_calloc_never_injected_NULL':True,'owned_reservation_fault_refusal_before_source':True,'source_OOM_recovery_claimed':False,'literal_prefix_without_component_boundary':True,'Find_does_not_strip_prefix':True,'Search_does_not_normalize_slashes':True,'old_checker_mains_or_broad_suites_executed':False,'current_Map_runtime_admitted':False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes);input_bytes=canonical(inputs)
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
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-file-list-ops-compile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile));identity='/* Controlled fixture labels; not runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',inputs['first_input_sha256']),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_id),('fixture_compile_profile_id',compile_id)]);(directory/'file-list-ops-identity.h').write_text(identity);exe=directory/'file-list-ops';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(test),'-lcrypto','-o',str(exe)];run(cmd,record=directory/'compile')
   build={'schema':'coh-file-list-ops-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes);ledger=b'COHFLO1\0'+b''.join(bytes.fromhex(v)for v in(source_id,build_id,profile_id,nonce,inputs['first_input_sha256'],build['executable_sha256'],input_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger);ran=run([exe,wire,directory/'run-ledger.bin',directory/'build.json',work/'input-ledger.json'],record=directory/'native',env=env)
   if ran.stderr or len(ran.stdout.encode())>4096:raise ValueError('Native output bound/refusal')
   result=json.loads(ran.stdout);checks[mode]=result['checks'];bindings[mode]=result['fixture_binding'];expected={'source_id':source_id,'build_id':build_id,'profile_id':profile_id,'run_id':nonce,'input_sha256':inputs['first_input_sha256'],'fixture_sha256':inputs['fixture_sha256'],'executable_sha256':build['executable_sha256'],'input_ledger_sha256':input_id,'compile_profile_sha256':compile_id,'run_ledger_sha256':sha(ledger)}
   if bindings[mode]!=expected:raise ValueError('Child measured association differs')
   builds[mode]=build;verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native check counts differ')
  for path in work.rglob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');stack.append({'translation_unit':path.name,'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded native stack')
  own_frame=next(row['bytes']for row in stack if row['function']=='fileops_apply')
  provider_frame_sum=sum(row['bytes']for row in stack if 'provider' in row['translation_unit'])
  if own_frame>16384 or provider_frame_sum>16384:raise ValueError('Own provider frames exceed charged stack reserve')
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};proof={'schema':'coh-original-file-list-ops-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host,'host_compiler_identity':tool,'compiler_and_python_stable_before_after':True,'original_provider':origin,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'inputs':{k:v for k,v in inputs.items()if k!='cases'},'full_fixture_reference':files['fixture-reference.json'],'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'conservative_sum_of_all_measured_provider_frames':provider_frame_sum,'evidence_files':files,'scope':'Independent whole original FileListCreate/Search/Insert/Find in explicit bounded owned shells. All fixtures synthetic. Original case-insensitive sorting, duplicate suppression, insertion position, literal raw prefix and Find/Search asymmetry preserved. Zero dates and unsafe paths refuse before any source call. Owned reservation fault refusals do not establish source unchecked calloc OOM recovery. No source filesystem/earray/allocator closure, real FS scanning/freshness, old checker mains, broad suites or APK.','ASan_LeakSanitizer_enabled':False,'external_libc_crypto_sanitizer_stack_or_device_RSS_qualified':False,'original_Win32_or_Android_ABI_qualified':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'dictionary_generation_admitted':False,'complete_initial_character':False,'selected_owner_admitted':False,'actor_publication':False,'application_ACK':False,'world_authority':False,'gates_1_through_24_preserved':True,'gates_25_through_27_open':True,'ALLENTS_41_43_and_dictionary_index_stops_unchanged':True}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Focused original FileListIsBinUpToDate qualification; no old checker mains."""
import argparse,hashlib,importlib.util,json,os,platform,shlex,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def run(args,record=None,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if record:
  Path(str(record)+'.stdout').write_text(p.stdout);Path(str(record)+'.stderr').write_text(p.stderr);Path(str(record)+'.command.json').write_bytes(canonical({'argv':list(map(str,args)),'returncode':p.returncode}))
 if p.returncode:raise RuntimeError('FILE_LIST_COMPARE_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('file_list_compare_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(work):
 command=shutil.which('cc')
 if not command:raise ValueError('Compiler unavailable')
 path=Path(command).resolve();raw=path.read_bytes();version=run([path,'--version'],record=work/'cc-version')
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 return{'command':'cc','resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def fixtures(work):
 # Separate dictionary oracle: retain first spelling/date under lowercase key,
 # sort keys, compare sets/dates, then calculate the first original bin-order
 # diagnostic. No original binary-search code or prior checker executes.
 cases=[]
 def E(path,date=1,length=None):return {'path':path,'date':date,'length':len(path)if length is None else length}
 def add(label,left=(),right=(),directories=(b'C:/data',b'C:/data'),fault=0,counts=None,dlens=None,patch=None):
  counts=tuple(map(len,(left,right)))if counts is None else counts;dlens=tuple(map(len,directories))if dlens is None else dlens
  raw=bytearray(struct.pack('<I',fault));maps=[];status=0;stage=8;failed_list=failed_entry=0;reservations=reserved=0;total=0
  def valid(value,length,cap):return length<cap and len(value)<=cap and length<=len(value)and(length==len(value)or value[length]==0)and all(0<x<128 for x in value[:length])
  for side,entries in enumerate((left,right)):
   directory=directories[side];dl=dlens[side]
   raw+=struct.pack('<II',counts[side],dl)+directory.ljust(260,b'\0')
   for v in entries:raw+=struct.pack('<II',v['length'],v['date'])+v['path'].ljust(520,b'\0')
   raw+=bytes(528*(16-len(entries)))
   mapping={};maps.append(mapping)
   if status:continue
   failed_list=side;failed_entry=0
   if counts[side]>16:status=4;stage=3;continue
   if not valid(directory,dl,260):status=1;stage=4;continue
   for i,v in enumerate(entries):
    failed_entry=i;path=v['path'];n=v['length']
    if not valid(path,n,520):status=1;stage=4;break
    path=path[:n]
    if path.lower().startswith(directory[:dl].lower()):
     path=path[dl:]
     if path[:1]in(b'/',b'\\'):path=path[1:]
    if len(path)>=260:status=4;stage=4;break
    if not v['date']:status=2;stage=5;break
    total+=1;path=path.replace(b'\\',b'/');mapping.setdefault(path.lower(),(path,v['date']))
  if len(raw)!=17436:raise ValueError('typed request width')
  if patch:at,value=patch;raw[at]=value;status=1;stage=4;failed_list=failed_entry=0
  if not status:
   if fault>total+2:status=2;stage=3
   elif fault:reservations=fault;status=4;stage=7
   else:reservations=total+2;reserved=total;failed_list=failed_entry=0
  rows=[[m[k]for k in sorted(m)]for m in maps]
  equal=1;diagnostic=0;di=0xffffffff;lookups=0
  if len(maps[0])!=len(maps[1]):equal=0
  else:
   for i,key in enumerate(sorted(maps[0])):
    lookups+=1
    if key not in maps[1]:equal=0;diagnostic=1;di=i;break
    if maps[0][key][1]!=maps[1][key][1]:equal=0;diagnostic=2;di=i;break
  expected=struct.pack('<5I',equal,len(rows[0]),len(rows[1]),diagnostic,di)
  for values in rows:
   for path,date in values:expected+=path.ljust(260,b'\0')+struct.pack('<I',date)
   expected+=bytes(264*(16-len(values)))
  if len(expected)!=8468:raise ValueError('typed result width')
  cases.append({'label':label,'raw':bytes(raw),'expected':expected,'status':status,'stage':stage,'failed_list':failed_list,'failed_entry':failed_entry,'reservations':reservations,'reserved_nodes':reserved,'expected_find_calls':lookups if not status else 0,'equal':equal if not status else None,'diagnostic':diagnostic if not status else None,'diagnostic_index':di if not status else None,'rows':[[{'path_hex':path.hex(),'date_bits':d}for path,d in values]for values in rows],'counts':counts,'directories_hex':[d.hex()for d in directories]})
 add('empty_both')
 add('singleton_equal',[E(b'One',0xffffffff)],[E(b'ONE',0xffffffff)])
 add('left_empty',[ ],[E(b'a')]);add('right_empty',[E(b'a')],[])
 add('unequal_lengths',[E(b'a'),E(b'b')],[E(b'a')])
 add('missing_single',[E(b'a')],[E(b'b')])
 add('date_single',[E(b'a',1)],[E(b'A',2)])
 for order in[(b'z',b'a',b'm'),(b'a',b'm',b'z'),(b'm',b'z',b'a')]:
  add('order_'+b''.join(order).decode(),[E(v,ord(v))for v in order],[E(v.upper(),ord(v))for v in reversed(order)])
 for index in range(3):
  names=(b'a',b'm',b'z');left=[E(v,i+1)for i,v in enumerate(names)]
  add('missing_at_'+str(index),left,[E(v if i!=index else b'y'+v,i+1)for i,v in enumerate(names)])
  add('date_at_'+str(index),left,[E(v,i+1 if i!=index else 99)for i,v in enumerate(names)])
 add('first_diagnostic_date_precedes_missing',[E(b'a'),E(b'b')],[E(b'a',2),E(b'c')])
 add('first_diagnostic_missing_precedes_date',[E(b'a'),E(b'z')],[E(b'b'),E(b'z',2)])
 add('duplicates_first_date_kept_equal',[E(b'alpha',0x80000000),E(b'ALPHA',7),E(b'z',0xffffffff)],[E(b'Z',0xffffffff),E(b'ALPHA',0x80000000),E(b'alpha',8)])
 add('duplicates_first_date_unequal',[E(b'p',1),E(b'P',2)],[E(b'P',2),E(b'p',1)])
 add('duplicate_suppressed_lengths',[E(b'a'),E(b'A'),E(b'b')],[E(b'B'),E(b'a')])
 add('nonzero_signed32_boundaries',[E(b'a',0x80000000),E(b'b',0xffffffff),E(b'c',0x7fffffff)],[E(b'C',0x7fffffff),E(b'B',0xffffffff),E(b'A',0x80000000)])
 add('signed32_inequality',[E(b'a',0xffffffff)],[E(b'a',0x7fffffff)])
 add('slash_equal',[E(b'a\\b')],[E(b'A/B')])
 add('repeat_slash_literal_difference',[E(b'a//b')],[E(b'a/b')])
 add('dot_literal_difference',[E(b'a/../b')],[E(b'b')])
 add('prefix_removed_before_slash',[E(b'C:/DATA\\one')],[E(b'one')])
 add('prefix_separator_mismatch_retained',[E(b'C:\\data\\one')],[E(b'one')])
 add('raw_prefix_collision',[E(b'database/x')],[E(b'base/x')],(b'data',b''))
 add('different_directories_same_relative',[E(b'C:/one/a')],[E(b'D:/two/A')],(b'C:/one',b'D:/two'))
 add('empty_name',[E(b'C:/data')],[E(b'')])
 add('empty_directory_one_separator_removed',[E(b'//one')],[E(b'/one')],(b'',b''))
 for n in(0,1,258,259):add('path_accept_'+str(n),[E(b'X'*n,0xffffffff)],[E(b'x'*n,0xffffffff)])
 add('raw519_poststrip259',[E(b'D'*259+b'/'+b'X'*259)],[E(b'x'*259)],(b'D'*259,b''))
 add('max_lists_reverse_order',[E(bytes([c]),0x80000000+c)for c in range(80,64,-1)],[E(bytes([c+32]),0x80000000+c)for c in range(65,81)])
 add('max_lists_last_date_mismatch',[E(bytes([c]),c)for c in range(65,81)],[E(bytes([c]),c if c<80 else 99)for c in range(65,81)])
 for side in range(2):
  def bad(label,entries=(),**kw):add(label+'_side'+str(side),entries if side==0 else [E(b'safe')],entries if side==1 else [E(b'safe')],**kw)
  bad('count17',counts=(17,1)if side==0 else(1,17))
  bad('zero_date',[E(b'p',0)])
  bad('duplicate_zero_date',[E(b'p'),E(b'P',0)])
  for n in(260,519,520):bad('unsafe_path'+str(n),[E(b'X'*n)])
  bad('NUL_path',[E(b'a\0b')]);bad('nonASCII_path',[E(b'p\xff')]);bad('UINTMAX_path',[E(b'p',length=0xffffffff)])
  dirs=[b'C:/data',b'C:/data'];dirs[side]=b'D'*260;bad('directory260',directories=tuple(dirs))
  dirs[side]=b'd\0x';bad('directoryNUL',directories=tuple(dirs))
  dirs[side]=b'\xff';bad('directory_nonASCII',directories=tuple(dirs))
  bad('directory_UINTMAX',dlens=(0xffffffff,7)if side==0 else(7,0xffffffff))
 add('unterminated_path',[E(b'p')],patch=(4+268+8+1,ord('x')))
 add('late_unsafe_right_atomic',[E(b'safe')],[E(b'safe'),E(b'X'*260)])
 add('invalid_reservation_selector',[E(b'a')],[E(b'a')],fault=5)
 maximal=[E(bytes([c]),c)for c in range(65,81)]
 for fault in range(1,35):add('reservation_before_source_'+str(fault),maximal,maximal,fault=fault)
 path=work/'file-list-compare-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x31434c46,len(cases)))
  for i,c in enumerate(cases):
   f.write(struct.pack('<8I',i,c['status'],c['stage'],c['failed_list'],c['failed_entry'],c['reservations'],c['reserved_nodes'],c['expected_find_calls']));f.write(bytes.fromhex(sha(c['raw'])));f.write(c['raw'])
   if not c['status']:f.write(c['expected'])
   manifest.append({k:v for k,v in c.items()if k not in('raw','expected')}|{'case':i,'input_bytes':len(c['raw']),'input_sha256':sha(c['raw']),'expected_sha256':sha(c['expected'])if not c['status']else None,'synthetic_control':True})
 if path.stat().st_size>4*1024*1024:raise ValueError('Fixture bound')
 proof={'schema':'coh-file-list-compare-input-v1','fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'first_input_sha256':sha(cases[0]['raw']),'request_bytes':17436,'result_bytes':8468,'case_count':len(cases),'cases':manifest,'independent_expectations':'Independent dictionary first lowercase keys retain spelling and raw32 dates. Sorted keys generate source bin ordering; key membership/date equality independently determine result and earliest diagnostic. No source binary search or old checker runs. Literal prefix then slash-only normalization. Synthetic lists only.'}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,value):return'static const unsigned char '+name+'[32]={'+','.join(str(x)for x in bytes.fromhex(value))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 temporary=tempfile.TemporaryDirectory(prefix='coh-file-list-compare-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  provider=module(HERE/'file_list_compare_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'file_list_compare_provider.py',HERE/'file-list-compare-source-pins.json',HERE/'test_file_list_compare.c',HERE/'file_list_ops_provider.py',HERE/'file-list-ops-source-pins.json',root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths};tool=compiler(work);python_path=Path(sys.executable).resolve();host={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False}
  if sys.byteorder!='little':raise ValueError('Typed fixture profile is little-endian')
  wire,inputs=fixtures(work);generated,origin=provider.build(root,work);generated=Path(generated);header=work/'file-list-compare-provider.h';test=HERE/'test_file_list_compare.c';input_include=root/'native-android/engine/costume-import';source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Source pin changed')
   source_paths.add(path)
  (work/'file-list-compare-identity.h').write_text('/* dependency discovery only */\n')
  for source in(test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())};source_identity={'schema':'coh-file-list-compare-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['file-list-compare-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-file-list-compare-profile-v1','original_functions':['FileListCreate','FileListSearch','FileListInsert','FileListFind','FileListIsBinUpToDate'],'fixed_owner_shells':['calloc','eaCreate','eaSize','eaInsert','fileDataDir','ASCII stricmp/strnicmp','forwardSlashes implementation absent','verbose_printf fixed sanitized recorder'],'filesystem_timestamp_trap':True,'source_date_zero_excluded_even_duplicates':True,'lists':2,'INSERT_call_max_per_list':16,'node_max_per_list':16,'raw_path_max':519,'directory_max':259,'post_strip_INSERT_path_max':259,'typed_request_bytes':17436,'typed_result_bytes':8468,'two_independent_owned_node_arenas':True,'full_node_pointer_snapshots_unchanged':True,'comparison_result_false_is_completed_transaction':True,'diagnostics_numeric_only':True,'selected_original_Find_results_checked':True,'budget_max':1048576,'own_stack_reserve':16384,'all_paths_preflight_before_source':True,'source_calloc_never_injected_NULL':True,'owned_reservation_fault_refusal_before_source':True,'source_OOM_recovery_claimed':False,'literal_prefix_without_component_boundary':True,'Find_does_not_strip_prefix':True,'old_checker_mains_or_broad_suites_executed':False,'current_Map_runtime_admitted':False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes);input_bytes=canonical(inputs)
  if len(input_bytes)>196608:raise ValueError('Input ledger bound')
  (work/'input-ledger.json').write_bytes(input_bytes);input_id=sha(input_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or generated.read_bytes()!=generated_raw or header.read_bytes()!=header_raw:raise ValueError('Source changed during qualification')
   if Path(shutil.which('cc')).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed')
   if sha(python_path.read_bytes())!=host['python_executable_sha256']:raise ValueError('Python executable changed')
  common=['-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-pedantic','-fno-strict-aliasing'];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C');checks={};bindings={};builds={};stack=[]
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-file-list-compare-compile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile));identity='/* Controlled fixture labels; not runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',inputs['first_input_sha256']),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_id),('fixture_compile_profile_id',compile_id)]);(directory/'file-list-compare-identity.h').write_text(identity);exe=directory/'file-list-compare';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(test),'-lcrypto','-o',str(exe)];run(cmd,record=directory/'compile')
   build={'schema':'coh-file-list-compare-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes);ledger=b'COHFLC1\0'+b''.join(bytes.fromhex(v)for v in(source_id,build_id,profile_id,nonce,inputs['first_input_sha256'],build['executable_sha256'],input_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger);ran=run([exe,wire,directory/'run-ledger.bin',directory/'build.json',work/'input-ledger.json'],record=directory/'native',env=env)
   if ran.stderr or len(ran.stdout.encode())>4096:raise ValueError('Native output bound/refusal')
   result=json.loads(ran.stdout);checks[mode]=result['checks'];bindings[mode]=result['fixture_binding'];expected={'source_id':source_id,'build_id':build_id,'profile_id':profile_id,'run_id':nonce,'input_sha256':inputs['first_input_sha256'],'fixture_sha256':inputs['fixture_sha256'],'executable_sha256':build['executable_sha256'],'input_ledger_sha256':input_id,'compile_profile_sha256':compile_id,'run_ledger_sha256':sha(ledger)}
   if bindings[mode]!=expected:raise ValueError('Child measured association differs')
   builds[mode]=build;verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native check counts differ')
  for path in work.rglob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');stack.append({'translation_unit':path.name,'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded native stack')
  own_frame=next(row['bytes']for row in stack if row['function']=='filecompare_apply')
  provider_frame_sum=sum(row['bytes']for row in stack if 'provider' in row['translation_unit'])
  if own_frame>16384 or provider_frame_sum>16384:raise ValueError('Own provider frames exceed charged stack reserve')
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};proof={'schema':'coh-original-file-list-compare-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host,'host_compiler_identity':tool,'compiler_and_python_stable_before_after':True,'original_provider':origin,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'inputs':{k:v for k,v in inputs.items()if k!='cases'},'full_fixture_reference':files['fixture-reference.json'],'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'conservative_sum_of_all_measured_provider_frames':provider_frame_sum,'evidence_files':files,'scope':'Whole original FileListIsBinUpToDate over two independently owned lists built by unchanged Create/Search/Insert/Find. Independent Python expectations cover equal/unequal size, missing names, raw signed32 dates and original first sorted-bin diagnostic. Exact original diagnostic formats and owned path pointers captured numerically only. All fixtures synthetic. Existing ASCII/slash/earray/allocator shells explicit. Zero dates, malformed paths and reservation faults refuse before all original entry. Source OOM, original lifecycle, actual disk freshness/scanning/current Map/runtime catalog/default/dictionary/world entry remain unqualified.','ASan_LeakSanitizer_enabled':False,'LeakSanitizer_exclusion_reason':'Established host ptrace limitation; detect_leaks=0. No leak closure claim.','external_libc_crypto_sanitizer_stack_or_device_RSS_qualified':False,'original_Win32_or_Android_ABI_qualified':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'dictionary_generation_admitted':False,'complete_initial_character':False,'selected_owner_admitted':False,'actor_publication':False,'application_ACK':False,'world_authority':False,'gates_1_through_24_preserved':True,'gates_25_through_27_open':True,'ALLENTS_41_43_and_dictionary_index_stops_unchanged':True}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

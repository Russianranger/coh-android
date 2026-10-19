#!/usr/bin/env python3
"""Original bounded body-read composition, measured fixture provenance."""
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
 if p.returncode:raise RuntimeError('BODY_READ_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('body_read_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
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
 def signed(value):return value if value<0x80000000 else value-0x100000000
 def cstr(value):return value.split(b'\0',1)[0]
 def pascal(value,padding=None):
  count=(4-(len(value)+2)%4)%4
  if padding is not None and len(padding)!=count:raise ValueError('Pascal padding extent')
  return struct.pack('<H',len(value))+value+(bytes(count)if padding is None else padding)
 def row_bytes(row):
  t=row['strings'];v=row['raw'];pads=row.get('padding',[None]*5)
  return pascal(t[0],pads[0])+pascal(t[1],pads[1])+struct.pack('<2I',*v[:2])+b''.join(pascal(t[i],pads[i])for i in range(2,5))+struct.pack('<5I',*v[2:])
 def body(rows,count=None,declared=None,row_sizes=None):
  chunks=[struct.pack('<I',len(row_bytes(row))if row_sizes is None else row_sizes[i])+row_bytes(row)for i,row in enumerate(rows)]
  payload=struct.pack('<I',len(rows)if count is None else count)+b''.join(chunks)
  return raw[:64]+struct.pack('<I',len(payload)if declared is None else declared)+payload
 def public_part(row):
  values=[cstr(value)for value in row['strings']];v=row['raw']
  return {'strings':values,'raw':v[:],'final':[v[2],v[1],v[3]&255,v[4],v[5],v[6],sum((not value)<<i for i,value in enumerate(values))]}
 def reference_part(part):return {'strings_hex':[v.hex()for v in part['strings']],'raw':part['raw'],'final':part['final']}
 cases=[]
 def add(label,data,build=0xcf27aba3,ignore=1):
  # Independent entered-field projector: scalar extents, real schema order,
  # last BoneCount assignment and U8 narrowing. Native original source still
  # decides acceptance; no prior decoder/provider/test main is executed.
  c={'label':label,'data':data,'build':build,'ignore':ignore,'status':status['COH_OK'],'stage':17,'failure':0,'header_end':0,'dependency_end':0,'body_end':0,'raw_array_count':0,'body_declared_size':0,'nodes':0,'reads':0,'seeks':0,'tables':0,'capacity':0,'strings':0,'ints':0,'u8':0,'warnings':0,'header_accepted':0,'filelist_called':0,'source_result':0,'parts':[],'parsed_rows':[]}
  def refuse(code,stage,failure=0):c.update(status=status[code],stage=stage,failure=failure)
  def missing(stage):refuse('COH_INVALID',stage,len(data))
  if len(data)>65536:refuse('COH_LIMIT',1)
  elif ignore>1:refuse('COH_UNSUPPORTED',3)
  elif len(data)<14:missing(4)
  else:
   length=struct.unpack_from('<H',data,12)[0];header_end=14+length+(4-(length+2)%4)%4
   if length>=4096:refuse('COH_LIMIT',5,12)
   elif len(data)<header_end:missing(6)
   elif data[:8]!=b'CrypticS'or cstr(data[14:14+length])!=b'Parse6'or(not ignore and struct.unpack_from('<I',data,8)[0]!=build):
    refuse('COH_UNSUPPORTED',15);c.update(header_end=header_end,reads=4,seeks=1)
   else:
    at=header_end
    if len(data)-at<2:missing(7)
    else:
     length=struct.unpack_from('<H',data,at)[0];sizeat=at+2+length+(4-(length+2)%4)%4
     if sizeat>len(data)or len(data)-sizeat<4:missing(7)
     else:
      amount=signed(struct.unpack_from('<I',data,sizeat)[0]);at=sizeat+4
      if amount<0:refuse('COH_UNSUPPORTED',8,sizeat)
      elif amount>len(data)-at:missing(8)
      else:
       at+=amount;body_begin=at
       if len(data)-at<4:missing(9)
       else:
        declared=struct.unpack_from('<I',data,at)[0];at+=4
        if len(data)-at<4:missing(10)
        else:
         array_word=struct.unpack_from('<I',data,at)[0];n=signed(array_word);count_at=at;at+=4
         if n>30:refuse('COH_LIMIT',10,count_at)
         else:
          rows=[];row_failed=False;bad=False;datasum=4
          for _ in range(max(n,0)):
           begin=at
           if len(data)-at<4:missing(11);bad=True;break
           row_declared=struct.unpack_from('<I',data,at)[0];at+=4;payload_begin=at;values=[];words=[];positions=[];padding=[]
           for field in range(12):
            if field in(0,1,4,5,6):
             positions.append(at)
             if len(data)-at<2:missing(12);bad=True;break
             length=struct.unpack_from('<H',data,at)[0]
             if length>259:refuse('COH_LIMIT',12,at);bad=True;break
             extent=2+length+(4-(length+2)%4)%4
             if extent>len(data)-at:missing(12);bad=True;break
             values.append(data[at+2:at+2+length]);padding.append(data[at+2+length:at+extent]);at+=extent
            else:
             if len(data)-at<4:missing(13);bad=True;break
             words.append(struct.unpack_from('<I',data,at)[0]);at+=4
           if bad:break
           rows.append({'strings':values,'raw':words,'padding':padding,'begin':begin,'end':at,'string_at':positions})
           if at-payload_begin!=signed(row_declared):row_failed=True;break
           datasum+=at-begin
          if not bad:
           success=not row_failed and datasum==signed(declared)and len(data)-body_begin==4+signed(declared)
           warnings=3 if row_failed else 2 if datasum!=signed(declared)else int(not success)
           c.update(header_end=header_end,dependency_end=body_begin,body_end=at,raw_array_count=array_word,body_declared_size=declared,nodes=len(rows),reads=8+18*len(rows),seeks=4+5*len(rows),tables=1+len(rows),capacity=int(n>0),strings=5*len(rows),ints=6*len(rows),u8=len(rows),warnings=warnings,header_accepted=1,filelist_called=1,source_result=int(success),parsed_rows=rows)
           if success:c['parts']=[public_part(row)for row in rows]
           else:refuse('COH_UNSUPPORTED',16)
  cases.append(c)
 add('authentic_CLIENT_complete_source_body',raw)
 authentic=cases[0]
 if authentic['status']or authentic['body_end']!=2584 or authentic['raw_array_count']!=28 or authentic['body_declared_size']!=2516:raise ValueError('Authentic source body framing')
 rows=authentic['parsed_rows'];auth_rows=[{'strings':r['strings'][:],'raw':r['raw'][:],'padding':r['padding'][:]}for r in rows]
 if body(auth_rows)!=raw:raise ValueError('Independent authentic body reproduction changed')
 import copy
 changed=copy.deepcopy(auth_rows);changed[0]['raw']=[1,0x80000000,3,0xdeadbeef,0xffffffff,0x80000000,0x11223344];add('synthetic_duplicate_overwrite_U8_narrowing_cached_high_bits',body(changed))
 changed=copy.deepcopy(auth_rows);changed[0]['strings']=[b'',b'\0hidden',b'Geo\0suffix',b'\xffRaw',b''];changed[0].pop('padding');add('synthetic_empty_NULL_NULprefix_nonASCII_source_strings',body(changed))
 changed=copy.deepcopy(auth_rows);changed[0]['padding'][0]=b'\xa5';add('synthetic_arbitrary_body_string_padding',body(changed))
 changed=copy.deepcopy(auth_rows);changed[0]['strings'][0]=b'A'*259;changed[0].pop('padding');add('synthetic_native_string259_boundary',body(changed))
 changed=copy.deepcopy(auth_rows);changed[0]['strings'][0]=b'A'*260;changed[0].pop('padding');add('synthetic_native_string260_limit',body(changed))
 changed=copy.deepcopy(auth_rows);changed[-1]['strings'][-1]=b'X'*260;changed[-1].pop('padding');add('synthetic_late_string_policy_limit',body(changed))
 add('synthetic_empty_array_zero',body([]))
 add('synthetic_source_negative_count_minus1_observed_empty',body([],count=0xffffffff))
 add('synthetic_source_negative_count_INTMIN_observed_empty',body([],count=0x80000000))
 minimal={'strings':[b'X',b'',b'',b'',b''],'raw':[0,0,0,0,0,0,0]}
 max_rows=[copy.deepcopy(minimal)for _ in range(30)]
 for i,row in enumerate(max_rows):row['raw'][-1]=i
 add('synthetic_native_count30_boundary',body(max_rows))
 add('synthetic_native_count31_limit_before_capacity',body([],count=31))
 add('synthetic_outer_datasum_mismatch_after_all_rows',body(auth_rows,declared=2520))
 add('synthetic_outer_negative_datasum_after_all_rows',body(auth_rows,declared=0xffffffff))
 sizes=[len(row_bytes(row))for row in auth_rows];changed_sizes=sizes[:];changed_sizes[0]+=4;add('synthetic_first_row_datasum_failure_after_one_row',body(auth_rows,row_sizes=changed_sizes))
 changed_sizes=sizes[:];changed_sizes[-1]+=4;add('synthetic_last_row_datasum_failure_after28_rows',body(auth_rows,row_sizes=changed_sizes))
 changed_sizes=sizes[:];changed_sizes[0]=0xffffffff;add('synthetic_negative_row_datasum_after_one_row',body(auth_rows,row_sizes=changed_sizes))
 changed=bytearray(raw[:rows[0]['end']]+b'\xff');struct.pack_into('<I',changed,rows[0]['begin'],sizes[0]+4);add('synthetic_failed_first_row_leaves_later_malformed_bytes_unentered',bytes(changed))
 add('synthetic_exact_file_tail_extra_byte',raw+b'\xa5')
 add('synthetic_last_scalar_truncated_before_source',raw[:-1])
 for size in(64,65,67):add('synthetic_body_length_truncated_'+str(size),raw[:size])
 for size in(68,69,71):add('synthetic_array_count_truncated_'+str(size),raw[:size])
 for size in(72,73,75):add('synthetic_first_row_length_truncated_'+str(size),raw[:size])
 for size in(76,77,80,83):add('synthetic_first_string_extent_truncated_'+str(size),raw[:size])
 last=rows[-1]
 for label,size in(('row_length',last['begin']+3),('string_length',last['string_at'][0]+1),('string_payload',last['string_at'][1]+5),('scalar',last['end']-1)):
  add('synthetic_late_'+label+'_truncated_before_source',raw[:size])
 changed=bytearray(raw);struct.pack_into('<H',changed,last['string_at'][-1],65535);add('synthetic_late_string_length65535_policy_first_failure',bytes(changed))
 add('synthetic_composition_strict_CRC_header_rejection',raw,build=0,ignore=0)
 changed=bytearray(raw);changed[22:28]=b'Wrong!';struct.pack_into('<I',changed,32,0xffffffff);add('synthetic_actual_NULL_dependency_tag_count_remain_unobserved',bytes(changed))
 add('synthetic_composition_dependency_extent_truncated',raw[:63])
 add('synthetic_unsupported_ignore_profile',raw,ignore=2)
 add('synthetic_input_max_source_exact_file_accounting_rejection',raw+bytes(65536-len(raw)))
 add('synthetic_input_overmax_before_source',raw+bytes(65537-len(raw)))
 path=work/'body-read-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<II',0x31524442,len(cases)))
  keys=('status','stage','failure','build','ignore','header_end','dependency_end','body_end','raw_array_count','body_declared_size','nodes','reads','seeks','tables','capacity','strings','ints','u8','warnings','header_accepted','filelist_called','source_result')
  for i,c in enumerate(cases):
   data=c['data'];f.write(struct.pack('<24I',i,*[c[k]for k in keys],len(data)));f.write(bytes.fromhex(sha(data)));f.write(data)
   if c['status']==status['COH_OK']:
    for row in c['parts']:
     for text in row['strings']:f.write(struct.pack('<I',len(text)));f.write(text)
     f.write(struct.pack('<14I',*row['raw'],*row['final']))
   expected=[reference_part(row)for row in c['parts']]
   manifest.append({k:v for k,v in c.items()if k not in('data','parts','parsed_rows')}|{'case':i,'bytes':len(data),'sha256':sha(data),'expected_final_row_count':len(expected),'expected_rows_sha256':sha(canonical(expected)),'authentic_retained_CLIENT_input':i==0,'synthetic_control':i!=0})
 if path.stat().st_size>524288:raise ValueError('Fixture bound')
 full_reference={'authentic_rows':[reference_part(row)for row in authentic['parts']],'cases':manifest}
 (work/'body-field-reference.json').write_bytes(canonical(full_reference))
 proof={'archive_path':ARCHIVE,'archive_bytes':len(packed),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'member':'data/bin/BodyParts.bin','member_bytes':len(raw),'member_sha256':BODY_SHA,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'authentic_header_end':20,'authentic_dependency_end':64,'authentic_body_end':2584,'authentic_body_declared_size':2516,'authentic_raw_array_count':28,'authentic_rows':28,'NULL_dependency_count_and_paths_unobserved':True,'fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'cases':manifest,'independent_expectations':'Original schema order projected independently from exact retained bytes: five raw Pascal strings, all seven raw32 numeric words incl duplicate BoneCount and raw DontClear, final C-string/NULL masks, last BoneCount overwrite and low8 BOOLFLAG. Per-case final fields encoded in measured fixture; full authentic fields/reference hashes retained separately. No old decoder/provider/checker main, ParseBoneNames, freshness or normalization executes. Negative array count source-success is observed empty with raw word retained, never catalog admission.','current_server_consumption_verified':False}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,hexvalue):return 'static const unsigned char '+name+'[32]={'+','.join(str(v)for v in bytes.fromhex(hexvalue))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 provider=module(HERE/'body_read_provider.py');initial_paths=[Path(__file__).resolve(),HERE/'test_body_read.c',HERE/'body_read_provider.py',HERE/'body-read-source-pins.json',root/ARCHIVE,root/'native-android/engine/coh_contracts.h'];initial={path.resolve():path.read_bytes()for path in initial_paths}
 temporary=tempfile.TemporaryDirectory(prefix='coh-body-read-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  tool=compiler(work);python_path=Path(sys.executable).resolve();host_environment={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_pointer_bytes':struct.calcsize('P'),'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'original_Win32_or_Android_ABI_qualified':False};wire,inputs=fixtures(root,work);generated,origin=provider.build(root,work);generated=Path(generated);source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Body-read source pin changed')
   source_paths.add(path)
  test=HERE/'test_body_read.c';input_include=root/'native-android/engine/costume-import'
  # The identity header is build-derived below, deliberately outside the source
  # identity closure to avoid a circular executable/receipt self-hash.
  identity_stub=work/'body-read-qualification-identity.h';identity_stub.write_text('/* dependency discovery only */\n')
  for source in(test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-I'+str(input_include),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1];source_paths.update(Path(n).resolve()for n in shlex.split(deps)if Path(n).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};generated_raw=generated.read_bytes();header=work/'body-read-provider.h';header_raw=header.read_bytes();source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())}
  source_identity={'schema':'coh-body-read-fixture-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(generated_raw),'generated_header_sha256':sha(header_raw),'excluded_circular_derived_files':['body-read-qualification-identity.h','per-mode build receipts','native executables','run ledgers']};source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-body-read-fixture-profile-v1','composition':'whole original ParserReadBinaryFile + ParserReadBinaryTable + earray/nonarray/struct/string/int/u8 readbin chain','source_schemas':'original ParseBodyPartBegin/ParseBodyPart and full BodyPart/List/ParseTable declarations/macros','prefix_dependency':'original SerializeReadOpen + actual NULL FileListRead; accepted checker/test mains never replayed','caller':'opened binfile branch; actual ParseTableCRC and ParserLoadFiles not executed','binary_backend':'explicit fixed owned read-only buffer/close/no-growth + bounded TokenStore/storage/dispatch adapters','input_max':65536,'positive_count_policy_max':30,'declared_string_policy_max':259,'negative_count_source_behavior':'source succeeds as observed empty only with matching body/file accounting; raw count word retained','duplicate_BoneCount_last_assignment_and_BOOLFLAG_low8_preserved':True,'cached_bones_and_index_recalculated':False,'source_empty_Cstring_to_NULL_mask_preserved':True,'complete_entered_field_preflight':True,'source_row_failure_stops_before_later_rows':True,'NULL_dependencies_validated':False,'source_schema_CRC_verified':False,'stack_reserve':98304,'child_fixture_max':524288,'child_input_ledger_max':131072,'child_build_receipt_max':65536,'child_stdout_max':4096,'fixture_only':True,'current_Map_runtime_admitted':False,'runtime_body_catalog_admitted':False,'runtime_default_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'server_identity_bound':False,'selected_owner_bound':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes)
  input_ledger_bytes=canonical(inputs);assert len(input_ledger_bytes)<=131072;(work/'input-ledger.json').write_bytes(input_ledger_bytes);input_ledger_id=sha(input_ledger_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or generated.read_bytes()!=generated_raw or header.read_bytes()!=header_raw:raise ValueError('Source changed during body-read qualification')
   if Path(shutil.which('cc')).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed during body-read qualification')
   if sha(python_path.read_bytes())!=host_environment['python_executable_sha256']:raise ValueError('Python executable changed during body-read qualification')
  checks={};bindings={};builds={};stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  common=['-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-unused-parameter','-Wno-unused-value','-Wno-unused-but-set-variable','-pedantic','-fno-strict-aliasing']
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-body-read-fixture-compile-profile-v1','mode':mode,'compiler':tool,'flags':common+flags,'generated_provider_sha256':sha(generated_raw),'test_source_sha256':sha(test.read_bytes())};compile_id=sha(canonical(compile_profile))
   identity='/* Derived fixture self-measurement only; no runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',BODY_SHA),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',input_ledger_id),('fixture_compile_profile_id',compile_id)])
   (directory/'body-read-qualification-identity.h').write_text(identity);exe=directory/'body-read';cmd=['cc',*common,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(input_include),str(generated),str(test),'-lcrypto','-o',str(exe)];built=run(cmd);(directory/'compile.stdout').write_text(built.stdout);(directory/'compile.stderr').write_text(built.stderr)
   build={'schema':'coh-body-read-fixture-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'command':cmd,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build);(directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes)
   ledger=b'COHBDR1\0'+b''.join(bytes.fromhex(x)for x in(source_id,build_id,profile_id,nonce,BODY_SHA,build['executable_sha256'],input_ledger_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger)
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
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};compact_inputs={k:v for k,v in inputs.items()if k!='cases'};compact_inputs.update(case_count=len(inputs['cases']),full_fixture_reference={'path':'fixture-reference.json',**files['fixture-reference.json']},full_input_ledger={'path':'input-ledger.json',**files['input-ledger.json']},full_body_field_reference={'path':'body-field-reference.json',**files['body-field-reference.json']});proof={'schema':'coh-original-body-read-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':host_environment,'host_python_binary_stable_before_after':True,'host_compiler_identity':tool,'host_compiler_stable_before_after':True,'original_body_read_provider':origin,'retained_authentic_CLIENT_input':compact_inputs,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'child_measured_fixture_bindings':bindings,'builds':builds,'checks':checks,'native_stack_frames':stack,'evidence_files':files,'scope':'Bounded unchanged original ParserReadBinaryFile/Table composition with whole original array/struct/nonarray/string/int/u8 readbin functions, exact BodyPart schema/declarations/macros and explicit fixed owned TokenStore/dispatch/buffer adapters. Authentic retained CLIENT header end20/dependency end64/body end2584: all28 original rows/raw words/final source fields compared independently. NULL dependency route remains opaque. Cached bones/index preserved, duplicate BoneCount last wins, BOOLFLAG low8 and empty C-string NULL semantics preserved; ParseBoneNames not executed. Exact body/table/file accounting and partial state rollback tested. Full runtime Parse6 loader/CRC/current Map transaction unqualified. Child self-measured source/input/ELF/build/profile/random fixture labels are controlled fixture associations, not runtime attestation or current Map consumption.','original_ParserReadBinaryFile_executed':True,'original_ParserReadBinaryTable_executed':True,'original_FileListRead_NULL_executed':True,'NULL_dependency_count_or_paths_validated':False,'native_prior_body_decoder_executed':False,'original_ParseBoneNames_executed':False,'actual_ParseTableCRC_computed':False,'full_runtime_Parse6_loader_executed':False,'current_Map_runtime_executed':False,'filesystem_normalization_or_freshness_executed':False,'old_checker_mains_executed':False,'old_native_suites_executed':False,'external_crypto_libc_sanitizer_or_stack_closure':False,'runtime_body_catalog_admitted':False,'runtime_default_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'server_identity_bound':False,'selected_owner_bound':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'authentic_body_end':inputs['authentic_body_end']}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

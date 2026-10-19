#!/usr/bin/env python3
"""Original source schema CRC, independent Adler stream and measured fixture provenance."""
import argparse,hashlib,importlib.util,json,os,platform,re,shlex,shutil,struct,subprocess,sys,tempfile,zipfile,zlib,copy
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE='native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip'
ARCHIVE_SHA='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241';ARCHIVE_BLOB='606fd1e17751fbdf6d7c903dee4eaea40c2014f3'
BODY_SHA='b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError('SCHEMA_CRC_QUALIFICATION_REFUSED\n'+p.stdout[:1024]+p.stderr[:3072])
 return p
def module(path):
 s=importlib.util.spec_from_file_location('schema_crc_source_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(work,command):
 found=shutil.which(command)
 if not found:raise ValueError('Compiler unavailable: '+command)
 path=Path(found).resolve();raw=path.read_bytes();version=run([path,'--version'])
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 tag='cxx'if command=='c++'else'cc';(work/(tag+'-version.stdout')).write_text(version.stdout)
 return {'command':command,'resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def original_reference(root):
 parser=(root/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h').read_text()
 body=(root/'upstream/ouroboros/Common/gameData/BodyPart.c').read_text()
 enum=re.search(r'typedef enum\s*\{(.*?)\} StructTokenType;',parser,re.S)
 if not enum:raise ValueError('Original token enum absent')
 clean=re.sub(r'//[^\n]*|/\*.*?\*/','',enum[1],flags=re.S);symbols=[item.strip()for item in clean.split(',')if item.strip()]
 if any(not re.fullmatch(r'TOK_[A-Z0-9_]+|NUM_TOK_TYPE_TOKENS',item)for item in symbols):raise ValueError('Original token enum grammar changed')
 values={name:i for i,name in enumerate(symbols)};flags={}
 for name in('TOK_INDIRECT','TOK_EARRAY','TOK_REDUNDANTNAME','TOK_STRUCTPARAM'):
  match=re.search(r'^#define\s+'+name+r'\s+\(1 << ([0-9]+)\)',parser,re.M)
  if not match:raise ValueError('Original token flag grammar changed')
  flags[name]=1<<int(match[1])
 def table(name):
  match=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=\s*\{(.*?)\n\};',body,re.S)
  if not match:raise ValueError('Original BodyPart schema absent')
  text=re.sub(r'//[^\n]*|/\*.*?\*/','',match[1],flags=re.S);rows=[]
  for item in re.finditer(r'\{\s*"([^"\n]*)"\s*,\s*([^{}]+)\}',text):
   label,macro=item.groups();macro=macro.strip()
   if macro=='0, 0':continue
   field={'name':label.encode(),'offset':0,'format':0,'default':None,'param':0,'subtable':False}
   if macro=='TOK_END':field.update(type=values['TOK_END'],family='ignore')
   else:
    m=re.fullmatch(r'TOK_(STRING|CURRENTFILE|INT|BOOLFLAG|STRUCT)\(([^()]*)\)',macro)
    if not m:raise ValueError('Original schema macro grammar changed: '+macro)
    kind=m[1];args=[part.strip()for part in m[2].split(',')]
    primitive={'STRING':'TOK_STRING_X','CURRENTFILE':'TOK_CURRENTFILE_X','INT':'TOK_INT_X','BOOLFLAG':'TOK_BOOLFLAG_X','STRUCT':'TOK_STRUCT_X'}[kind]
    field['type']=values[primitive]
    if kind in('STRING','CURRENTFILE'):field.update(type=field['type']|flags['TOK_INDIRECT'],family='string')
    elif kind in('INT','BOOLFLAG'):
     if not re.fullmatch(r'-?[0-9]+',args[-1]):raise ValueError('Original numeric default grammar')
     field.update(family='number',param=int(args[-1])&0xffffffffffffffff)
    else:
     if args!=['BodyPartList','bodyParts','ParseBodyPart']:raise ValueError('Original nested schema changed')
     field.update(type=field['type']|flags['TOK_INDIRECT']|flags['TOK_EARRAY'],family='struct',subtable=True)
   field['base_type']=field['type'];rows.append(field)
  return rows
 tables=[table('ParseBodyPartBegin'),table('ParseBodyPart')]
 if len(tables[0])!=1 or len(tables[1])!=13:raise ValueError('Original schema extent changed')
 return tables,flags

def reference(tables,flags,mutations):
 tables=copy.deepcopy(tables)
 for table,row,field,value,text in mutations:
  target=tables[table][row]
  if field==1:target['name']=text
  elif field==2:target['type']=target['base_type']|value
  elif field==3:
   target['param']=value
   if target['family']=='string':target['default']=None
  elif field==4:target['offset']=value
  elif field==5:target['format']=value
  elif field==6:target['default']=text
  else:raise ValueError('Reference mutation field')
 updates=[];events=[];visited=0;interprets=0
 def emit(kind,table,row,raw):updates.append(raw);events.append({'kind':kind,'table':table,'row':row,'length':len(raw),'hex':raw.hex()})
 def visit(index):
  nonlocal visited,interprets
  for number,field in enumerate(tables[index]):
   if field['type']&flags['TOK_REDUNDANTNAME']:continue
   visited+=1;interprets+=1
   emit('name',index,number,field['name'].split(b'\0',1)[0]);emit('type_U32LE',index,number,struct.pack('<I',field['type']))
   if field['family']=='number':emit('param_int32LE',index,number,struct.pack('<I',field['param']&0xffffffff))
   elif field['family']=='string'and field['default']is not None:emit('default_Cstring',index,number,field['default'].split(b'\0',1)[0])
   if field['subtable']:
    visit(1);interprets+=1 # original SubtableField dispatch, not StaticDefineList
 visit(0);stream=b''.join(updates);standard=zlib.adler32(stream,1)&0xffffffff
 return {'crc':int.from_bytes(standard.to_bytes(4,'big'),'little'),'standard_adler32':standard,'stream':stream,'lengths':[len(raw)for raw in updates],'visited':visited,'interprets':interprets,'events':events}

def fixtures(root,work):
 status={name:int(value)for name,value in re.findall(r'(COH_[A-Z_]+)\s*=\s*([0-9]+)',(root/'native-android/engine/coh_contracts.h').read_text())}
 if not all(name in status for name in('COH_OK','COH_INVALID','COH_LIMIT','COH_UNSUPPORTED')):raise ValueError('Native status ABI absent')
 archive=root/ARCHIVE;packed=archive.read_bytes()
 if len(packed)!=2253704 or sha(packed)!=ARCHIVE_SHA or run(['git','-C',root,'rev-parse','HEAD:'+ARCHIVE]).stdout.strip()!=ARCHIVE_BLOB:raise ValueError('Exact retained CLIENT archive changed')
 with zipfile.ZipFile(archive)as z:
  members=z.infolist();inventory={'data/bin/BodyParts.bin':2584,'data/bin/costume.bin':17691352,'data/bin/supergroupColors.bin':2664}
  if len(members)!=3 or {i.filename:i.file_size for i in members}!=inventory or any(i.flag_bits&1 or i.is_dir()for i in members):raise ValueError('Exact subset inventory changed')
  retained=z.read('data/bin/BodyParts.bin')
 if len(retained)!=2584 or sha(retained)!=BODY_SHA:raise ValueError('Retained CLIENT bytes changed')
 retained_crc=struct.unpack_from('<I',retained,8)[0];(work/'retained-CLIENT-BodyParts.bin').write_bytes(retained)
 tables,flags=original_reference(root);cases=[]
 def wire(ops):return b'SCR1'+struct.pack('<I',len(ops))+b''.join(struct.pack('<IIIQI',t,r,f,v,len(text))+text for t,r,f,v,text in ops)
 def add(label,ops):
  data=wire(ops);expect=reference(tables,flags,ops);cases.append({'label':label,'wire':data,'ops':ops,'status':status['COH_OK'],'stage':8,'failure':0,'mutations':len(ops),'expect':expect})
 add('exact_original_source_BodyPart_schema',[])
 add('ignored_root_storeoffset_UINT64',[(0,0,4,0xffffffffffffffff,b'')])
 add('ignored_child_storeoffset_UINT64',[(1,2,4,0x123456789abcdef0,b'')])
 add('ignored_root_SizeOfSubstruct_param',[(0,0,3,0xffffffffffffffff,b'')])
 add('ignored_format_UINT32',[(1,2,5,0xffffffff,b'')])
 add('numeric_default7_changes_stream',[(1,2,3,7,b'')])
 add('numeric_default_highword_truncated_to_int32',[(1,2,3,0x1234567800000007,b'')])
 add('numeric_default_negative_bits',[(1,2,3,0xffffffffffffffff,b'')])
 add('schema_name_changes_stream',[(1,0,1,0,b'Other')])
 add('schema_name_embedded_NUL_preserves_prefix',[(1,0,1,0,b'Name\0hidden')])
 add('schema_name_empty_Cprefix',[(1,0,1,0,b'\0hidden')])
 add('string_default_changes_stream',[(1,0,6,0,b'Fallback')])
 add('empty_nonNULL_default_adds_zero_length_update',[(1,0,6,0,b'')])
 add('default_Cstring_prefix',[(1,0,6,0,b'Fallback\0hidden')])
 add('default_pointer_reset_to_NULL',[(1,0,6,0,b'Fallback'),(1,0,3,0,b'')])
 add('type_STRUCTPARAM_is_crc_sensitive',[(1,2,2,flags['TOK_STRUCTPARAM'],b'')])
 add('redundant_child_field_skips_all_updates',[(1,2,2,flags['TOK_REDUNDANTNAME'],b'')])
 add('redundant_child_name_and_param_ignored',[(1,2,2,flags['TOK_REDUNDANTNAME'],b''),(1,2,1,0,b'Ignored'),(1,2,3,1234,b'')])
 add('redundant_root_skips_subtree_empty_seed',[(0,0,2,flags['TOK_REDUNDANTNAME'],b'')])
 add('redundant_root_name_param_offset_ignored',[(0,0,2,flags['TOK_REDUNDANTNAME'],b''),(0,0,1,0,b'Ignored'),(0,0,3,0xffffffffffffffff,b''),(0,0,4,99,b'')])
 add('End_param_NoFieldUsage_ignored',[(1,12,3,0xffffffffffffffff,b'')])
 add('CURRENTFILE_default_uses_string_interpretfield',[(1,1,6,0,b'Defaults.bin')])
 add('name63_native_boundary',[(1,0,1,0,b'X'*63)])
 add('four_default_strings63_trace_boundary',[(1,row,6,0,b'X'*63)for row in(0,1,4,5)])
 add('sequential_names_restore_original',[(1,0,1,0,b'A'),(1,0,1,0,b'Name')])
 add('ignored_metadata_four_operations',[(0,0,3,99,b''),(0,0,4,999,b''),(1,12,3,999,b''),(1,2,5,99,b'')])
 add('combined_allowed_type_flags',[(1,2,2,flags['TOK_STRUCTPARAM']|flags['TOK_REDUNDANTNAME'],b'')])
 # Wrapper-profile refusals added explicitly below after canonical parse rules;
 # these controls never enter original checksum functions.
 def refuse(label,data,code,stage,failure,mutations=0):cases.append({'label':label,'wire':data,'ops':None,'status':status[code],'stage':stage,'failure':failure,'mutations':mutations,'expect':None})
 # Exact wrapper-contract refusals; no original checksum callback is entered.
 add('schema_name_nonASCII_unsigned_bytes',[(1,0,1,0,b'\xffName')])
 refuse('wire_bad_magic',b'BAD!'+struct.pack('<I',0),'COH_INVALID',4,0)
 for size in(0,3,7):refuse('wire_header_truncated_'+str(size),wire([])[:size],'COH_INVALID',4,size)
 refuse('wire_count5_native_limit',b'SCR1'+struct.pack('<I',5),'COH_LIMIT',4,4)
 refuse('wire_trailing_byte',wire([])+b'X','COH_INVALID',4,8)
 full=wire([(1,0,1,0,b'Name')])
 for size in(8,11,19,27,31,33):refuse('wire_record_truncated_'+str(size),full[:size],'COH_INVALID',4,size)
 refuse('wire_text64_limit',wire([(1,0,1,0,b'X'*64)]),'COH_LIMIT',4,28)
 refuse('mutation_unknown_table',wire([(2,0,1,0,b'X')]),'COH_UNSUPPORTED',5,8)
 refuse('mutation_root_sentinel_forbidden',wire([(0,1,1,0,b'X')]),'COH_UNSUPPORTED',5,12)
 refuse('mutation_child_sentinel_forbidden',wire([(1,13,1,0,b'X')]),'COH_UNSUPPORTED',5,12)
 for field in(0,7):refuse('mutation_unknown_field_'+str(field),wire([(1,0,field,0,b'')]),'COH_UNSUPPORTED',5,16)
 refuse('mutation_name_nonzero_value',wire([(1,0,1,1,b'X')]),'COH_INVALID',5,20)
 refuse('mutation_typeflags_outside_profile',wire([(1,0,2,0x400,b'')]),'COH_UNSUPPORTED',5,20)
 refuse('mutation_string_raw_pointer_forbidden',wire([(1,0,3,1,b'')]),'COH_UNSUPPORTED',5,20)
 refuse('mutation_default_string_on_number_forbidden',wire([(1,2,6,0,b'X')]),'COH_UNSUPPORTED',5,16)
 refuse('mutation_format_UINT64_limit',wire([(1,0,5,0x100000000,b'')]),'COH_LIMIT',5,20)
 refuse('mutation_scalar_nonempty_text',wire([(1,0,4,0,b'X')]),'COH_INVALID',5,28)
 early=(1,0,1,0,b'Other');refuse('late_invalid_mutation_stays_atomic',wire([early,(2,0,1,0,b'X')]),'COH_UNSUPPORTED',5,8+24+len(early[-1]))
 refuse('input357_native_limit',wire([])+bytes(357-8),'COH_LIMIT',1,0)
 add('fresh_source_baseline_after_all_mutations_and_refusals',[])
 baseline=cases[0]['wire'];baseline_expect=cases[0]['expect'];(work/'schema-baseline-wire.bin').write_bytes(baseline)
 path=work/'schema-crc-fixtures.bin';manifest=[];full_cases=[]
 with path.open('xb')as f:
  f.write(struct.pack('<III',0x31464353,len(cases),retained_crc))
  for i,c in enumerate(cases):
   data=c['wire'];expect=c['expect'];f.write(struct.pack('<7I',i,c['status'],c['stage'],c['failure'],c['mutations'],len(data),int(expect is not None)));f.write(bytes.fromhex(sha(data)));f.write(data)
   if expect:
    f.write(struct.pack('<5I',expect['crc'],len(expect['stream']),len(expect['lengths']),expect['visited'],expect['interprets']));f.write(struct.pack('<'+str(len(expect['lengths']))+'I',*expect['lengths']));f.write(expect['stream'])
   meta={'case':i,'label':c['label'],'bytes':len(data),'sha256':sha(data),'expected_status':c['status'],'expected_stage':c['stage'],'first_failure_byte':c['failure'],'mutations':c['mutations'],'exact_original_schema':i in(0,len(cases)-1),'synthetic_mutation_or_refusal':i not in(0,len(cases)-1)}
   if expect:meta.update(crc=expect['crc'],standard_adler32=expect['standard_adler32'],stream_bytes=len(expect['stream']),stream_sha256=sha(expect['stream']),update_calls=len(expect['lengths']),update_lengths=expect['lengths'],visited_fields=expect['visited'],interpret_calls=expect['interprets'])
   manifest.append(meta);full_cases.append(meta|{'wire_hex':data.hex(),'source_stream_hex':expect['stream'].hex()if expect else None,'events':expect['events']if expect else None})
 if path.stat().st_size>131072:raise ValueError('Fixture file bound')
 (work/'schema-stream-reference.json').write_bytes(canonical({'source_enum_and_flags':flags,'baseline_stream_hex':baseline_expect['stream'].hex(),'baseline_events':baseline_expect['events'],'cases':full_cases}))
 proof={'primary_input':'canonical SCR1 count0 mutation wire; source schemas emitted from exact pins, not packet data','primary_input_bytes':len(baseline),'primary_input_sha256':sha(baseline),'archive_path':ARCHIVE,'archive_bytes':len(packed),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'retained_CLIENT_member':'data/bin/BodyParts.bin','retained_CLIENT_bytes':len(retained),'retained_CLIENT_sha256':BODY_SHA,'retained_CLIENT_crc_word':retained_crc,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'retained_CLIENT_word_compared_separately_not_supplied_to_source':True,'independent_baseline_crc':baseline_expect['crc'],'independent_baseline_standard_adler32':baseline_expect['standard_adler32'],'independent_baseline_stream_bytes':len(baseline_expect['stream']),'independent_baseline_update_calls':len(baseline_expect['lengths']),'independent_baseline_visited_fields':baseline_expect['visited'],'independent_baseline_interpret_calls':baseline_expect['interprets'],'retained_CLIENT_word_matches_independent_baseline':retained_crc==baseline_expect['crc'],'fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'cases':manifest,'independent_expectations':'Original BodyPart schema/macro enum source parsed independently; UpdateCRCFromParseInfo semantics projected into actual ordered updates including zero-length calls. Standard zlib.adler32 seed1 plus source CryptoPP big-endian digest->little-U32 convention; stream bytes and all update lengths compared to actual original source. No retained CRC argument is supplied to source computation.','current_Map_schema_or_input_provenance_verified':False}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def array(name,hexvalue):return 'static const unsigned char '+name+'[32]={'+','.join(str(v)for v in bytes.fromhex(hexvalue))+'};\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 manifest_path=HERE/'qualification/schema-crc-20261019/cryptopp-adler-source.json';manifest=json.loads(manifest_path.read_text())
 initial_paths=[Path(__file__).resolve(),HERE/'test_schema_crc.c',HERE/'schema_crc_provider.py',HERE/'schema-crc-source-pins.json',HERE/'cryptopp_adler_source.py',manifest_path,root/manifest['archive']['path'],root/manifest['repository_dependency']['path'],root/ARCHIVE,root/'native-android/engine/coh_contracts.h',root/'upstream/ouroboros/Common/gameData/BodyPart.c',root/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h']
 initial={path.resolve():path.read_bytes()for path in initial_paths};provider=module(HERE/'schema_crc_provider.py')
 temporary=tempfile.TemporaryDirectory(prefix='coh-schema-crc-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  tools={name:compiler(work,name)for name in('cc','c++')};cc=tools['cc']['resolved_path'];cxx=tools['c++']['resolved_path'];python_path=Path(sys.executable).resolve();zlib_path=Path(zlib.__file__).resolve()if hasattr(zlib,'__file__')else python_path
  environment={'system':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'python_pointer_bytes':struct.calcsize('P'),'python_version':sys.version,'python_executable':str(python_path),'python_executable_sha256':sha(python_path.read_bytes()),'reference_zlib_version':zlib.ZLIB_VERSION,'reference_zlib_runtime_version':zlib.ZLIB_RUNTIME_VERSION,'reference_zlib_builtin_to_measured_python':not hasattr(zlib,'__file__'),'reference_zlib_module_or_python_binary':str(zlib_path),'reference_zlib_module_sha256':sha(zlib_path.read_bytes()),'original_engine_Win32_or_Android_ABI_qualified':False}
  wire,inputs=fixtures(root,work);generated,origin=provider.build(root,work);generated=Path(generated);adler_cpp=Path(origin['adler_cpp_path']);dependency=origin['crypto_dependency'];source_paths=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Schema CRC source pin changed')
   source_paths.add(path)
  test=HERE/'test_schema_crc.c';engine_include=root/'native-android/engine/costume-import';crypto_include=Path(dependency['include_dir']);cpp_sources=[adler_cpp,*map(Path,dependency['source_paths'])]
  identity_stub=work/'schema-crc-qualification-identity.h';identity_stub.write_text('/* dependency discovery only; derived files excluded from source identity. */\n')
  def dependencies(args):
   output=run(args).stdout.replace('\\\n',' ').split(':',1)[1];return[Path(name).resolve()for name in shlex.split(output)]
  for source in(generated,test):
   source_paths.update(path for path in dependencies([cc,'-std=c99','-I'+str(work),'-I'+str(engine_include),'-MM',source])if path.is_relative_to(root))
  dep_flags=dependency['proof']['compile_flags'];link_flags=dependency['proof']['link_flags']
  for source in cpp_sources:
   source_paths.update(path for path in dependencies([cxx,*dep_flags,'-I'+str(crypto_include),'-MM',source])if path.is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  frozen={path:path.read_bytes()for path in source_paths};header=work/'schema-crc-provider.h';owned={generated:generated.read_bytes(),header:header.read_bytes(),adler_cpp:adler_cpp.read_bytes()};dep_snapshots={Path(path).resolve():digest for path,digest in dependency['snapshot_sha256'].items()}
  source_hashes={str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())};crypto_snapshots={str(path.relative_to(work)):digest for path,digest in sorted(dep_snapshots.items())}
  source_identity={'schema':'coh-schema-crc-fixture-source-v1','source_sha256':source_hashes,'generated_provider_sha256':sha(owned[generated]),'generated_header_sha256':sha(owned[header]),'generated_adler_cpp_sha256':sha(owned[adler_cpp]),'dependency_snapshot_sha256':crypto_snapshots,'excluded_circular_derived_files':['schema-crc-qualification-identity.h','per-mode compile/build receipts','object files/native executables','run ledgers']}
  source_bytes=canonical(source_identity);(work/'source-identity.json').write_bytes(source_bytes);source_id=sha(source_bytes)
  profile={'schema':'coh-schema-crc-fixture-profile-v1','scope':'exact original BodyPart root/child source schemas, acyclic owned copy, definesNULL','original_functions':'ParseTableCRC/UpdateCRCFromParseInfo + four interpretfield handlers + original cryptAdler32Init/Update/Final wrappers','backend':'actual repository-pinned CryptoPP b5242667 Adler32/class-base closure; no alternate backend','wire_max':356,'mutation_max':4,'mutation_text_max':63,'trace_max':512,'update_max':64,'int32_intptr64_size64_little_endian_host_only':True,'source_offsets_format_substruct_size_ignored':True,'source_redundant_fields_skipped':True,'source_int_param_low32_and_Cstring_prefix_preserved':True,'original_define_profiles_executed':False,'reference':'independent source schema projection + standard zlib.adler32(seed1) + bigendian digest bytes interpretedlittleU32','retained_CLIENT_crc_is_separate_comparison_never_source_argument':True,'child_fixture_max':131072,'child_input_ledger_max':65536,'child_build_receipt_max':65536,'child_stdout_max':4096,'fixture_only':True,'body_reader_or_cache_selection_executed':False,'current_Map_runtime_admitted':False,'runtime_body_catalog_admitted':False,'runtime_default_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'server_identity_bound':False,'selected_owner_bound':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  profile_bytes=canonical(profile);(work/'fixture-profile.json').write_bytes(profile_bytes);profile_id=sha(profile_bytes);ledger_bytes=canonical(inputs)
  if len(ledger_bytes)>65536:raise ValueError('Input ledger bound')
  (work/'input-ledger.json').write_bytes(ledger_bytes);ledger_id=sha(ledger_bytes)
  def verify():
   if any(path.read_bytes()!=raw for path,raw in frozen.items())or any(path.read_bytes()!=raw for path,raw in owned.items()):raise ValueError('Source changed during schema CRC qualification')
   if any(sha(path.read_bytes())!=digest for path,digest in dep_snapshots.items()):raise ValueError('CryptoPP dependency source changed during qualification')
   for command,tool in tools.items():
    if Path(shutil.which(command)).resolve()!=Path(tool['resolved_path'])or sha(Path(tool['resolved_path']).read_bytes())!=tool['executable_sha256']:raise ValueError('Compiler changed during schema CRC qualification')
   if sha(python_path.read_bytes())!=environment['python_executable_sha256']or sha(zlib_path.read_bytes())!=environment['reference_zlib_module_sha256']:raise ValueError('Python/reference zlib binary changed')
  def command(args,stem,env=None):
   result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,env=env)
   Path(str(stem)+'.stdout').write_text(result.stdout);Path(str(stem)+'.stderr').write_text(result.stderr)
   if result.returncode:raise RuntimeError('SCHEMA_CRC_QUALIFICATION_REFUSED '+str(stem)+'\n'+result.stdout[:1024]+result.stderr[:3072])
   return result
  def actual_dependencies(path,identity):
   for dep in[Path(name).resolve()for name in shlex.split(path.read_text().replace('\\\n',' ').split(':',1)[1])]:
    if dep==identity:continue
    if dep in frozen or dep in owned or dep in dep_snapshots:continue
    raise ValueError('Unfrozen non-system compile dependency: '+str(dep))
  checks={};bindings={};build_summaries={};stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  c_flags=['-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-unused-parameter','-Wno-unused-value','-Wno-pointer-sign','-pedantic','-fno-strict-aliasing'];cpp_flags=[*dep_flags,'-Wall','-Wextra']
  for mode,flags in modes:
   directory=work/mode;directory.mkdir();nonce=os.urandom(32).hex();compile_profile={'schema':'coh-schema-crc-fixture-compile-profile-v1','mode':mode,'compilers':tools,'c_flags':c_flags+flags,'cpp_flags':cpp_flags+flags,'link_flags':link_flags+flags,'generated_provider_sha256':sha(owned[generated]),'adler_cpp_sha256':sha(owned[adler_cpp]),'test_source_sha256':sha(test.read_bytes()),'dependency_snapshot_manifest_sha256':sha(canonical(crypto_snapshots))};compile_id=sha(canonical(compile_profile))
   identity='/* Controlled fixture self-measurement only; no runtime attestation. */\n'+''.join(array(name,value)for name,value in [('fixture_source_id',source_id),('fixture_profile_id',profile_id),('fixture_run_id',nonce),('fixture_input_sha256',inputs['primary_input_sha256']),('fixture_wire_sha256',inputs['fixture_sha256']),('fixture_input_ledger_id',ledger_id),('fixture_compile_profile_id',compile_id)])
   identity_header=directory/'schema-crc-qualification-identity.h';identity_header.write_text(identity);objects=[];commands=[]
   for name,source in [('provider',generated),('test',test)]:
    obj=directory/(name+'.o');dep_file=directory/(name+'.d');args=[cc,*c_flags,*flags,'-I'+str(directory),'-I'+str(work),'-I'+str(engine_include),'-MMD','-MF',str(dep_file),'-c',str(source),'-o',str(obj)];command(args,directory/('compile-'+name));commands.append(args);objects.append(obj);actual_dependencies(dep_file,identity_header)
   for number,source in enumerate(cpp_sources):
    label='cpp-wrapper'if not number else'crypto-'+str(number)+'-'+source.stem;obj=directory/(label+'.o');dep_file=directory/(label+'.d');args=[cxx,*cpp_flags,*flags,'-I'+str(crypto_include),'-MMD','-MF',str(dep_file),'-c',str(source),'-o',str(obj)];command(args,directory/('compile-'+label));commands.append(args);objects.append(obj);actual_dependencies(dep_file,identity_header)
   exe=directory/'schema-crc';link=[cxx,*flags,*map(str,objects),*link_flags,'-lcrypto','-o',str(exe)];command(link,directory/'link');commands.append(link);commands_bytes=canonical(commands);(directory/'commands.json').write_bytes(commands_bytes)
   build={'schema':'coh-schema-crc-fixture-build-v1','compile_profile':compile_profile,'compile_profile_sha256':compile_id,'commands_sha256':sha(commands_bytes),'commands':commands,'source_identity_sha256':source_id,'profile_sha256':profile_id,'fixture_run_nonce':nonce,'generated_identity_header_sha256':sha(identity.encode()),'executable_bytes':exe.stat().st_size,'executable_sha256':sha(exe.read_bytes())};build_bytes=canonical(build)
   if len(build_bytes)>65536:raise ValueError('Build receipt bound')
   (directory/'build.json').write_bytes(build_bytes);build_id=sha(build_bytes);ledger=b'COHSCR1\0'+b''.join(bytes.fromhex(x)for x in(source_id,build_id,profile_id,nonce,inputs['primary_input_sha256'],build['executable_sha256'],ledger_id,compile_id));(directory/'run-ledger.bin').write_bytes(ledger)
   ran=command([exe,wire,directory/'run-ledger.bin',directory/'build.json',work/'input-ledger.json'],directory/'native',env)
   if ran.stderr or len(ran.stdout.encode())>4096:raise ValueError('Native output bound/refusal')
   result=json.loads(ran.stdout);checks[mode]=result['checks'];bindings[mode]=result['fixture_binding'];expected={'source_id':source_id,'build_id':build_id,'profile_id':profile_id,'run_id':nonce,'input_sha256':inputs['primary_input_sha256'],'fixture_sha256':inputs['fixture_sha256'],'executable_sha256':build['executable_sha256'],'input_ledger_sha256':ledger_id,'compile_profile_sha256':compile_id,'run_ledger_sha256':sha(ledger)}
   if bindings[mode]!=expected:raise ValueError('Child-measured fixture association differs')
   build_summaries[mode]={k:v for k,v in build.items()if k not in('commands','compile_profile')};build_summaries[mode].update(build_receipt_path=mode+'/build.json',build_receipt_sha256=build_id,compile_profile=compile_profile);verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native check counts differ')
  core_names=('Adler32::Update','Adler32::TruncatedFinal','Adler32::Reset','Adler32::Restart','Adler32::Adler32','Adler32::~Adler32','cryptAdler32Init','cryptAdler32Update','cryptAdler32Final','schema_adler_')
  stack_reports=[]
  for path in sorted((work/'release').glob('*.su')):
   rows=[]
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');match=re.match(r'.*:[0-9]+:[0-9]+:(.*)',location);function=match[1]if match else location
    if path.name in('provider.su','test.su')or any(name in function for name in core_names):rows.append({'function':function,'bytes':int(size),'bound':bound,'report':str(path.relative_to(work))})
   stack.extend(rows);stack_reports.append({'path':str(path.relative_to(work)),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded selected native stack')
  verify();files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()};compact_inputs={k:v for k,v in inputs.items()if k!='cases'};compact_inputs.update(case_count=len(inputs['cases']),full_fixture_reference={'path':'fixture-reference.json',**files['fixture-reference.json']},full_input_ledger={'path':'input-ledger.json',**files['input-ledger.json']},full_schema_stream_reference={'path':'schema-stream-reference.json',**files['schema-stream-reference.json']})
  compact_origin={k:v for k,v in origin.items()if k not in('crypto_dependency','adler_cpp_path','evidence_paths')};compact_origin['crypto_dependency']={'revision':dependency['proof']['revision'],'tree':dependency['proof']['tree'],'Git_commit_tree_selected_blob_membership_verified':True,'source_files_count':47,'source_snapshot_count':len(dep_snapshots),'source_snapshot_manifest_sha256':sha(canonical(crypto_snapshots)),'source_stable_before_after':True,'full_provenance':{'path':'cryptopp-provenance.json',**files['cryptopp-provenance.json']},'original_backend_not_alternate_Adler':True,'system_cpp_runtime_allocator_or_platform_closure':False}
  proof={'schema':'coh-original-schema-crc-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':source_hashes,'source_stable_before_after':True,'host_environment':environment,'host_python_and_reference_zlib_module_stable_before_after':True,'host_compiler_identities':tools,'host_compilers_stable_before_after':True,'original_schema_crc_provider':compact_origin,'schema_and_retained_CLIENT_comparison':compact_inputs,'fixture_source_identity':source_identity,'fixture_source_identity_sha256':source_id,'fixture_profile':profile,'fixture_profile_sha256':profile_id,'child_measured_fixture_bindings':bindings,'checks':checks,'builds':build_summaries,'native_stack_frames':stack,'full_dependency_stack_reports':stack_reports,'stack_scope':'Selected new C/test/wrapper and actual Adler core frames only; every compiled dependency .su retained. Unused generic CryptoPP methods and external runtime/allocator/aggregate stack closure not claimed.','evidence_files':files,'scope':'Original ParseTableCRC/UpdateCRCFromParseInfo on fresh owned exact BodyPart source schemas, actual interpretfield handlers and original cryptAdler32 wrappers with exact repository-pinned CryptoPP Adler32 dependency. Independent source-derived update stream/zero-length call boundaries matched byte-for-byte, then standard zlib.Adler reference with original digest-byte convention. Retained CLIENT CRC compared separately, never source input or forced expected result. Source/input/ELF/build/profile/random labels are measured fixture associations, not current Map attestation.','actual_original_ParseTableCRC_executed':True,'actual_original_CryptoPP_Adler32_executed':True,'external_define_or_recursive_schema_profiles_executed':False,'body_reader_or_cache_selection_executed':False,'old_checker_mains_executed':False,'old_native_suites_executed':False,'external_Cpp_OpenSSL_libc_allocator_sanitizer_or_total_stack_closure':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'runtime_default_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'server_identity_bound':False,'selected_owner_bound':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'case_count':len(inputs['cases'])}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()

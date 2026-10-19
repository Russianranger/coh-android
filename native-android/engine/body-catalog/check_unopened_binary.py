#!/usr/bin/env python3
"""Whole original unopened ParserReadBinaryFile owned transaction qualification."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('unopened_schema_crc_helpers', HERE / 'check_schema_crc.py')
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
sha, canonical, run, module, compiler, array = (_schema.sha, _schema.canonical, _schema.run,
                                               _schema.module, _schema.compiler, _schema.array)



ARCHIVE=_schema.ARCHIVE;ARCHIVE_SHA=_schema.ARCHIVE_SHA;ARCHIVE_BLOB=_schema.ARCHIVE_BLOB;BODY_SHA=_schema.BODY_SHA
def fixtures(root,work):
 tables,flags=_schema.original_reference(root);independent=_schema.reference(tables,flags,[])
 stream_reference={'crc':independent['crc'],'standard_adler32':independent['standard_adler32'],'stream_hex':independent['stream'].hex(),'update_lengths':independent['lengths'],'visited_fields':independent['visited'],'interpret_calls':independent['interprets']}
 (work/'schema-stream-reference.json').write_bytes(canonical(stream_reference))
 if independent['crc']!=0xcf27aba3 or len(independent['stream'])!=171 or len(independent['lengths'])!=35 or independent['visited']!=14 or independent['interprets']!=15:raise ValueError('Independent exact-source CRC profile changed')
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
 def add(label,data,build=0,ignore=1):
  # Independent entered-field projector: scalar extents, real schema order,
  # last BoneCount assignment and U8 narrowing. Native original source still
  # decides acceptance; no prior decoder/provider/test main is executed.
  c={'label':label,'data':data,'build':build,'ignore':ignore,'status':status['COH_OK'],'stage':18,'failure':0,'header_end':0,'dependency_end':0,'body_end':0,'raw_array_count':0,'body_declared_size':0,'nodes':0,'reads':0,'seeks':0,'tables':0,'capacity':0,'strings':0,'ints':0,'u8':0,'warnings':0,'header_accepted':0,'filelist_called':0,'source_result':0,'parts':[],'parsed_rows':[]}
  def refuse(code,stage,failure=0):c.update(status=status[code],stage=stage,failure=failure)
  def missing(stage):refuse('COH_INVALID',stage,len(data))
  if len(data)>65536:refuse('COH_LIMIT',1)
  elif ignore!=1 or build>3:refuse('COH_UNSUPPORTED',3)
  elif len(data)<14:missing(4)
  else:
   length=struct.unpack_from('<H',data,12)[0];header_end=14+length+(4-(length+2)%4)%4
   if length>=4096:refuse('COH_LIMIT',5,12)
   elif len(data)<header_end:missing(6)
   elif data[:8]!=b'CrypticS'or cstr(data[14:14+length])!=b'Parse6':
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
  if c['stage'] in(15,16,18) and build>=2:
   c.update(status=status['COH_LIMIT'],stage=17,failure=0,header_end=0,dependency_end=0,body_end=0,raw_array_count=0,body_declared_size=0,nodes=0,reads=0,seeks=0,tables=0,capacity=0,strings=0,ints=0,u8=0,warnings=0,header_accepted=0,filelist_called=0,source_result=0,parts=[],parsed_rows=[])
  elif c['stage'] in(15,16,18) and build==1:
   c.update(status=status['COH_UNSUPPORTED'],stage=15,failure=0,header_end=0,dependency_end=0,body_end=0,raw_array_count=0,body_declared_size=0,nodes=0,reads=0,seeks=0,tables=0,capacity=0,strings=0,ints=0,u8=0,warnings=0,header_accepted=0,filelist_called=0,source_result=0,parts=[],parsed_rows=[])
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
 changed=bytearray(raw);changed[0]^=1;add('synthetic_original_header_rejection',bytes(changed))
 changed=bytearray(raw);changed[22:28]=b'Wrong!';struct.pack_into('<I',changed,32,0xffffffff);add('synthetic_actual_NULL_dependency_tag_count_remain_unobserved',bytes(changed))
 add('synthetic_composition_dependency_extent_truncated',raw[:63])
 add('synthetic_unsupported_ignore_profile',raw,ignore=2)
 add('synthetic_input_max_source_exact_file_accounting_rejection',raw+bytes(65536-len(raw)))
 add('synthetic_input_overmax_before_source',raw+bytes(65537-len(raw)))
 for bit in range(32):
  changed=bytearray(raw);struct.pack_into('<I',changed,8,0xcf27aba3^(1<<bit));add('production_CRC_bit_'+str(bit)+'_full_body_accepted',bytes(changed))
 for value in(0,0xffffffff):
  changed=bytearray(raw);struct.pack_into('<I',changed,8,value);add('production_CRC_word_'+str(value)+'_full_body_accepted',bytes(changed))
 add('unsupported_fault_selector',raw,build=4)
 add('unsupported_requested_development_mode',raw,ignore=0)
 add('production_header_Cstring_NUL_suffix_with_complete_body',raw[:12]+pascal(b'Parse6\0suffix')+raw[20:])
 add('production_header_type4095_with_complete_body',raw[:12]+pascal(b'Parse6\0'+b'X'*4088)+raw[20:])
 add('owned_open_refusal_after_original_CRC',raw,build=1)
 add('owned_row_arena_reservation_failure_before_source',raw,build=2)
 add('actual_crypto_object_reservation_failure_before_source',raw,build=3)
 path=work/'unopened-binary-fixtures.bin';manifest=[]
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
 if path.stat().st_size>1048576:raise ValueError('Fixture bound')
 full_reference={'authentic_rows':[reference_part(row)for row in authentic['parts']],'cases':manifest}
 (work/'body-field-reference.json').write_bytes(canonical(full_reference))
 proof={'archive_path':ARCHIVE,'archive_bytes':len(packed),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'member':'data/bin/BodyParts.bin','member_bytes':len(raw),'member_sha256':BODY_SHA,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'authentic_header_end':20,'authentic_dependency_end':64,'authentic_body_end':2584,'authentic_body_declared_size':2516,'authentic_raw_array_count':28,'authentic_rows':28,'NULL_dependency_count_and_paths_unobserved':True,'primary_input_sha256':BODY_SHA,'fixture_bytes':path.stat().st_size,'fixture_sha256':sha(path.read_bytes()),'cases':manifest,'independent_expectations':'Original schema order projected independently from exact retained bytes: five raw Pascal strings, all seven raw32 numeric words incl duplicate BoneCount and raw DontClear, final C-string/NULL masks, last BoneCount overwrite and low8 BOOLFLAG. Per-case final fields encoded in measured fixture; full authentic fields/reference hashes retained separately. No old decoder/provider/checker main, ParseBoneNames, freshness or normalization executes. Negative array count source-success is observed empty with raw word retained, never catalog admission.','current_server_consumption_verified':False}
 (work/'fixture-reference.json').write_bytes(canonical(proof));return path,proof
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-directory', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(); root = args.source_root.resolve()
    if not __debug__:
        raise ValueError('Python assertions required')
    if args.output.exists() or (args.evidence_directory and args.evidence_directory.exists()):
        raise ValueError('Fresh output/evidence required')
    manifest_path = HERE / 'qualification/schema-crc-20261019/cryptopp-adler-source.json'
    manifest = json.loads(manifest_path.read_text())
    initial_paths = [Path(__file__).resolve(), HERE / 'check_schema_crc.py', HERE / 'test_unopened_binary.c',
                     HERE / 'unopened_binary_provider.py', HERE / 'unopened-binary-source-pins.json',
                     HERE / 'schema_crc_provider.py', HERE / 'schema-crc-source-pins.json',
                     HERE / 'body_read_provider.py', HERE / 'body-read-source-pins.json',
                     HERE / 'cryptopp_adler_source.py', manifest_path, root / manifest['archive']['path'],
                     root / manifest['repository_dependency']['path'], root / _schema.ARCHIVE,
                     root / 'native-android/engine/coh_contracts.h',
                     root / 'upstream/ouroboros/Common/gameData/BodyPart.c',
                     root / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h']
    initial = {path.resolve(): path.read_bytes() for path in initial_paths}
    provider = module(HERE / 'unopened_binary_provider.py')
    temporary = tempfile.TemporaryDirectory(prefix='coh-unopened-binary-') if not args.evidence_directory else None
    work = Path(temporary.name) if temporary else args.evidence_directory.resolve()
    if not temporary:
        work.mkdir(parents=True)
    try:
        tools = {name: compiler(work, name) for name in ('cc', 'c++')}
        cc, cxx = tools['cc']['resolved_path'], tools['c++']['resolved_path']
        python_path = Path(sys.executable).resolve()
        zlib_path = Path(zlib.__file__).resolve() if hasattr(zlib, '__file__') else python_path
        environment = {'system': platform.system(), 'machine': platform.machine(), 'byteorder': sys.byteorder,
                       'python_pointer_bytes': struct.calcsize('P'), 'python_version': sys.version,
                       'python_executable': str(python_path), 'python_executable_sha256': sha(python_path.read_bytes()),
                       'reference_zlib_version': zlib.ZLIB_VERSION, 'reference_zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION,
                       'reference_zlib_builtin_to_measured_python': not hasattr(zlib, '__file__'),
                       'reference_zlib_module_or_python_binary': str(zlib_path),
                       'reference_zlib_module_sha256': sha(zlib_path.read_bytes()),
                       'original_engine_Win32_or_Android_ABI_qualified': False}
        wire, inputs = fixtures(root, work)
        generated, origin = provider.build(root, work)
        generated = Path(generated); adler_cpp = Path(origin['adler_cpp_path'])
        dependency = origin['crypto_dependency']; source_paths = set(initial)
        for name, digest in origin['source_sha256'].items():
            path = (root / name).resolve()
            if sha(path.read_bytes()) != digest:
                raise ValueError('Unopened source pin changed')
            source_paths.add(path)
        test = HERE / 'test_unopened_binary.c'
        engine_include = root / 'native-android/engine/costume-import'
        crypto_include = Path(dependency['include_dir'])
        cpp_sources = [adler_cpp, *map(Path, dependency['source_paths'])]
        (work / 'unopened-binary-qualification-identity.h').write_text('/* dependency discovery only */\n')

        def dependencies(command):
            output = run(command).stdout.replace('\\\n', ' ').split(':', 1)[1]
            return [Path(name).resolve() for name in shlex.split(output)]

        for source in (generated, test):
            source_paths.update(path for path in dependencies([cc, '-std=c99', '-I' + str(work),
                                '-I' + str(engine_include), '-MM', source]) if path.is_relative_to(root))
        dep_flags, link_flags = dependency['proof']['compile_flags'], dependency['proof']['link_flags']
        for source in cpp_sources:
            source_paths.update(path for path in dependencies([cxx, *dep_flags, '-I' + str(crypto_include),
                                '-MM', source]) if path.is_relative_to(root))
        if any(path.read_bytes() != raw for path, raw in initial.items()):
            raise ValueError('Source changed during provider generation')
        frozen = {path: path.read_bytes() for path in source_paths}
        # Include every generated native header/source, not only the final
        # composite, so dependency discovery cannot silently leave a gap.
        owned = {path.resolve(): path.read_bytes() for path in work.iterdir()
                 if path.is_file() and path.suffix in ('.c', '.cpp', '.h')
                 and path.name != 'unopened-binary-qualification-identity.h'}
        dep_snapshots = {Path(path).resolve(): digest for path, digest in dependency['snapshot_sha256'].items()}
        source_hashes = {str(path.relative_to(root)): sha(raw) for path, raw in sorted(frozen.items())}
        crypto_snapshots = {str(path.relative_to(work)): digest for path, digest in sorted(dep_snapshots.items())}
        generated_hashes = {str(path.relative_to(work)): sha(raw) for path, raw in sorted(owned.items())}
        source_identity = {'schema': 'coh-unopened-binary-fixture-source-v1', 'source_sha256': source_hashes,
                           'generated_native_source_sha256': generated_hashes,
                           'dependency_snapshot_sha256': crypto_snapshots,
                           'excluded_circular_derived_files': ['unopened-binary-qualification-identity.h',
                             'per-mode compile/build receipts', 'object files/native executables', 'run ledgers']}
        source_bytes = canonical(source_identity); (work / 'source-identity.json').write_bytes(source_bytes)
        source_id = sha(source_bytes)
        profile = {'schema': 'coh-unopened-binary-fixture-profile-v1',
                   'scope': 'whole original unopened ParserReadBinaryFile production branch with exact BodyPart schemas and read dependencies, definesNULL',
                   'original_functions': 'ParserReadBinaryFile(NULL) + ParseTableCRC/UpdateCRCFromParseInfo/interpretfield/CryptoPP + SerializeReadOpen/FileListRead(NULL)/ParserReadBinaryTable/readbin/SerializeClose',
                   'source_crc_never_caller_supplied': True, 'production_mode': 1,
                   'production_ignoreCRC1_preserved': True,
                   'complete_entered_header_dependency_body_preflight':True,'all_authentic_prefix_truncations_tested':2584,
                   'failure_profiles': 'fixed row arena and actual crypto object reservation refusal before source; owned open refusal after actual CRC; original malloc/new failures not simulated',
                   'input_max': 65536, 'positive_count_policy_max':30,'declared_string_policy_max':259, 'declared_type_max': 4095, 'complete_header_preflight': True,
                   'source_embedded_NUL_and_arbitrary_padding_semantics_preserved': True,
                   'fixed_owned_buffer_no_filesystem': True, 'trace_max': 512, 'update_max': 64,
                   'child_fixture_max': 1048576, 'child_input_ledger_max': 131072,
                   'child_build_receipt_max': 65536, 'child_stdout_max': 4096,
                   'int32_intptr64_size64_little_endian_host_only': True, 'fixture_only': True,
                   'development_mode_executed': False, 'filesystem_freshness_executed': False,
                   'date_comparison_executed': False, 'current_Map_selection_provenance_verified': False,
                   'runtime_body_catalog_admitted': False, 'runtime_default_admitted': False,
                   'dictionary_imported': False, 'source_generation_admitted': False,
                   'complete_initial_character': False, 'server_identity_bound': False,
                   'selected_owner_bound': False, 'actor_publication': False, 'ack_permitted': False,
                   'world_authority': False}
        profile_bytes = canonical(profile); (work / 'fixture-profile.json').write_bytes(profile_bytes)
        profile_id = sha(profile_bytes); ledger_bytes = canonical(inputs)
        if len(ledger_bytes) > 131072:
            raise ValueError('Input ledger bound')
        (work / 'input-ledger.json').write_bytes(ledger_bytes); ledger_id = sha(ledger_bytes)

        def verify():
            if any(path.read_bytes() != raw for path, raw in frozen.items()) or any(path.read_bytes() != raw for path, raw in owned.items()):
                raise ValueError('Source changed during unopened qualification')
            if any(sha(path.read_bytes()) != digest for path, digest in dep_snapshots.items()):
                raise ValueError('CryptoPP dependency changed during qualification')
            for command, tool in tools.items():
                if (Path(shutil.which(command)).resolve() != Path(tool['resolved_path']) or
                        sha(Path(tool['resolved_path']).read_bytes()) != tool['executable_sha256']):
                    raise ValueError('Compiler changed during unopened qualification')
            if (sha(python_path.read_bytes()) != environment['python_executable_sha256'] or
                    sha(zlib_path.read_bytes()) != environment['reference_zlib_module_sha256']):
                raise ValueError('Python/reference zlib binary changed')

        def command(command_args, stem, env=None):
            result = subprocess.run(list(map(str, command_args)), capture_output=True, text=True, timeout=240, env=env)
            Path(str(stem) + '.stdout').write_text(result.stdout)
            Path(str(stem) + '.stderr').write_text(result.stderr)
            if result.returncode:
                raise RuntimeError('PERSIST_NEWER_QUALIFICATION_REFUSED ' + str(stem) + '\n' +
                                   result.stdout[:1024] + result.stderr[:3072])
            return result

        def actual_dependencies(path, identity):
            for dep in [Path(name).resolve() for name in shlex.split(path.read_text().replace('\\\n', ' ').split(':', 1)[1])]:
                if dep == identity or dep in frozen or dep in owned or dep in dep_snapshots:
                    continue
                raise ValueError('Unfrozen non-system compile dependency: ' + str(dep))

        checks, bindings, builds = {}, {}, {}
        modes = [('release', ['-O2', '-fstack-usage'])]
        if args.sanitize:
            modes += [('asan', ['-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer', '-no-pie']),
                      ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1', LC_ALL='C')
        c_flags = ['-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-missing-field-initializers',
                   '-Wno-unused-parameter', '-Wno-unused-value', '-Wno-unused-but-set-variable', '-Wno-pointer-sign', '-pedantic', '-fno-strict-aliasing']
        cpp_flags = [*dep_flags, '-Wall', '-Wextra']
        for mode, flags in modes:
            directory = work / mode; directory.mkdir(); nonce = os.urandom(32).hex()
            compile_profile = {'schema': 'coh-unopened-binary-fixture-compile-profile-v1', 'mode': mode,
                               'compilers': tools, 'c_flags': c_flags + flags, 'cpp_flags': cpp_flags + flags,
                               'link_flags': link_flags + flags, 'generated_native_source_sha256': generated_hashes,
                               'test_source_sha256': sha(test.read_bytes()),
                               'dependency_snapshot_manifest_sha256': sha(canonical(crypto_snapshots))}
            compile_id = sha(canonical(compile_profile))
            identity = '/* Controlled fixture association only; no runtime attestation. */\n' + ''.join(
                array(name, value) for name, value in [('fixture_source_id', source_id),
                ('fixture_profile_id', profile_id), ('fixture_run_id', nonce),
                ('fixture_input_sha256', inputs['primary_input_sha256']),
                ('fixture_wire_sha256', inputs['fixture_sha256']), ('fixture_input_ledger_id', ledger_id),
                ('fixture_compile_profile_id', compile_id)])
            identity_header = directory / 'unopened-binary-qualification-identity.h'
            identity_header.write_text(identity); objects, commands = [], []
            for name, source in [('provider', generated), ('test', test)]:
                obj, dep_file = directory / (name + '.o'), directory / (name + '.d')
                cmd = [cc, *c_flags, *flags, '-I' + str(directory), '-I' + str(work),
                       '-I' + str(engine_include), '-MMD', '-MF', str(dep_file), '-c', str(source), '-o', str(obj)]
                command(cmd, directory / ('compile-' + name)); commands.append(cmd); objects.append(obj)
                actual_dependencies(dep_file, identity_header)
            for number, source in enumerate(cpp_sources):
                label = 'cpp-wrapper' if not number else 'crypto-' + str(number) + '-' + source.stem
                obj, dep_file = directory / (label + '.o'), directory / (label + '.d')
                cmd = [cxx, *cpp_flags, *flags, '-I' + str(crypto_include), '-MMD', '-MF', str(dep_file),
                       '-c', str(source), '-o', str(obj)]
                command(cmd, directory / ('compile-' + label)); commands.append(cmd); objects.append(obj)
                actual_dependencies(dep_file, identity_header)
            exe = directory / 'unopened-binary'
            cmd = [cxx, *flags, *map(str, objects), *link_flags, '-lcrypto', '-o', str(exe)]
            command(cmd, directory / 'link'); commands.append(cmd)
            commands_bytes = canonical(commands); (directory / 'commands.json').write_bytes(commands_bytes)
            build = {'schema': 'coh-unopened-binary-fixture-build-v1', 'compile_profile': compile_profile,
                     'compile_profile_sha256': compile_id, 'commands_sha256': sha(commands_bytes),
                     'commands': commands, 'source_identity_sha256': source_id, 'profile_sha256': profile_id,
                     'fixture_run_nonce': nonce, 'generated_identity_header_sha256': sha(identity.encode()),
                     'executable_bytes': exe.stat().st_size, 'executable_sha256': sha(exe.read_bytes())}
            build_bytes = canonical(build)
            if len(build_bytes) > 65536:
                raise ValueError('Build receipt bound')
            (directory / 'build.json').write_bytes(build_bytes); build_id = sha(build_bytes)
            ledger = b'COHUB1\0\0' + b''.join(bytes.fromhex(value) for value in
                      (source_id, build_id, profile_id, nonce, inputs['primary_input_sha256'],
                       build['executable_sha256'], ledger_id, compile_id))
            (directory / 'run-ledger.bin').write_bytes(ledger)
            ran = command([exe, wire, directory / 'run-ledger.bin', directory / 'build.json',
                           work / 'input-ledger.json'], directory / 'native', env)
            if ran.stderr or len(ran.stdout.encode()) > 4096:
                raise ValueError('Native output bound/refusal')
            result = json.loads(ran.stdout); checks[mode], bindings[mode] = result['checks'], result['fixture_binding']
            expected = {'source_id': source_id, 'build_id': build_id, 'profile_id': profile_id, 'run_id': nonce,
                        'input_sha256': inputs['primary_input_sha256'], 'fixture_sha256': inputs['fixture_sha256'],
                        'executable_sha256': build['executable_sha256'], 'input_ledger_sha256': ledger_id,
                        'compile_profile_sha256': compile_id, 'run_ledger_sha256': sha(ledger)}
            if bindings[mode] != expected:
                raise ValueError('Child-measured fixture association differs')
            builds[mode] = {k: v for k, v in build.items() if k not in ('commands', 'compile_profile')}
            builds[mode].update(build_receipt_path=mode + '/build.json', build_receipt_sha256=build_id,
                                compile_profile=compile_profile)
            verify()
        if any(value != checks['release'] for value in checks.values()):
            raise ValueError('Native check counts differ')
        core_names = ('Adler32::Update', 'Adler32::TruncatedFinal', 'Adler32::Reset', 'Adler32::Restart',
                      'Adler32::Adler32', 'Adler32::~Adler32', 'cryptAdler32Init', 'cryptAdler32Update',
                      'cryptAdler32Final', 'schema_adler_')
        stack, stack_reports = [], []
        for path in sorted((work / 'release').glob('*.su')):
            for line in path.read_text().splitlines():
                location, size, bound = line.split('\t')
                match = re.match(r'.*:[0-9]+:[0-9]+:(.*)', location)
                function = match[1] if match else location
                if path.name in ('provider.su', 'test.su') or any(name in function for name in core_names):
                    stack.append({'function': function, 'bytes': int(size), 'bound': bound,
                                  'report': str(path.relative_to(work))})
            stack_reports.append({'path': str(path.relative_to(work)), 'bytes': path.stat().st_size,
                                  'sha256': sha(path.read_bytes())})
        if not stack or any(row['bound'] not in ('static', 'dynamic,bounded') for row in stack):
            raise ValueError('Unbounded selected native stack')
        verify()
        resources = {'profile_input_max': 65536, 'profile_type_max': 4095,
                     'fixture_file_bytes': wire.stat().st_size, 'fixture_file_max': 1048576,
                     'input_ledger_bytes': len(ledger_bytes), 'input_ledger_max': 131072,
                     'native_stdout_max': 4096, 'per_build_receipt_max': 65536,
                     'provider_owned_static_bytes': checks['release']['provider_owner_bytes'],
                     'actual_Adler_object_bytes': checks['release']['crypto_object_bytes'],
                     'wrapper_stack_charge_reserve': 98304, 'wrapper_total_budget_max': 1048576,
                     'digest_scratch_reserve_fixture': 65536, 'retained_reserve_fixture': 65536,
                     'selected_release_max_frame': max(row['bytes'] for row in stack),
                     'selected_release_frame_count': len(stack),
                     'stack_scope': 'new C provider/test and actual wrapper/Adler core only; every dependency .su retained',
                     'whole_process_or_aggregate_stack_bound_claimed': False}
        (work / 'resource-bounds.json').write_bytes(canonical(resources))
        files = {str(path.relative_to(work)): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
                 for path in sorted(work.rglob('*')) if path.is_file()}
        compact_inputs = {k: v for k, v in inputs.items() if k != 'cases'}
        compact_inputs.update(case_count=len(inputs['cases']), full_fixture_reference={'path': 'fixture-reference.json', **files['fixture-reference.json']},
                              full_input_ledger={'path': 'input-ledger.json', **files['input-ledger.json']},
                              full_schema_stream_reference={'path': 'schema-stream-reference.json', **files['schema-stream-reference.json']})
        compact_origin = {k: v for k, v in origin.items() if k not in ('crypto_dependency', 'adler_cpp_path', 'evidence_paths')}
        compact_origin['crypto_dependency'] = {'revision': dependency['proof']['revision'], 'tree': dependency['proof']['tree'],
             'Git_commit_tree_selected_blob_membership_verified': True, 'retained_source_file_count': dependency['proof']['source_files_count'],
             'compiled_dependency_translation_units': len(dependency['source_paths']),
             'source_snapshot_count': len(dep_snapshots), 'source_snapshot_manifest_sha256': sha(canonical(crypto_snapshots)),
             'source_stable_before_after': True, 'full_provenance': {'path': 'cryptopp-provenance.json', **files['cryptopp-provenance.json']},
             'original_backend_not_alternate_Adler': True, 'system_cpp_runtime_allocator_or_platform_closure': False}
        proof = {'schema': 'coh-original-unopened-binary-qualification-v1', 'passed': True,
                 'source_revision': run(['git', '-C', root, 'rev-parse', 'HEAD']).stdout.strip(),
                 'source_sha256': source_hashes, 'source_stable_before_after': True, 'host_environment': environment,
                 'host_python_and_reference_zlib_module_stable_before_after': True, 'host_compiler_identities': tools,
                 'host_compilers_stable_before_after': True, 'original_unopened_binary_provider': compact_origin,
                 'source_schema_and_body_fixtures': compact_inputs, 'fixture_source_identity': source_identity,
                 'fixture_source_identity_sha256': source_id, 'fixture_profile': profile,
                 'fixture_profile_sha256': profile_id, 'child_measured_fixture_bindings': bindings,
                 'checks': checks, 'builds': builds, 'resource_bounds': resources, 'native_stack_frames': stack,
                 'full_dependency_stack_reports': stack_reports, 'evidence_files': files,
                 'scope': 'Whole unchanged original ParserReadBinaryFile(NULL) computes actual source schema CRC with CryptoPP, opens with immutable production ignoreCRC1, skips FileListRead(NULL), interprets exact BodyPart schemas via original table/readbin functions, accounts the whole input and closes in original SerializeClose. Every authentic field compared independently; production CRC mismatch acceptance preserved. Every authentic-prefix truncation refuses before source entry. Fixed allocation reservation and open refusals are separately qualified; unsafe original NULL/new failures are not simulated. Source/input/ELF/build/profile/random labels are measured fixture associations, never current Map attestation.',
                 'actual_original_ParserReadBinaryFile_unopened_executed': True,
                 'actual_original_ParseTableCRC_executed': True, 'actual_original_SerializeReadOpen_executed': True,
                 'actual_original_CryptoPP_Adler32_executed': True, 'production_ignoreCRC1_preserved': True,
                 'development_mode_executed': False, 'date_or_filesystem_freshness_executed': False,
                 'original_FileListRead_NULL_executed': True, 'full_original_body_reader_executed': True,
                 'old_checker_mains_executed': False, 'old_native_suites_executed': False,
                 'external_Cpp_OpenSSL_libc_allocator_sanitizer_or_total_stack_closure': False,
                 'current_Map_runtime_executed': False, 'current_Map_selection_provenance_verified': False,
                 'runtime_body_catalog_admitted': False, 'runtime_default_admitted': False,
                 'dictionary_imported': False, 'source_generation_admitted': False,
                 'complete_initial_character': False, 'server_identity_bound': False, 'selected_owner_bound': False,
                 'actor_publication': False, 'ack_permitted': False, 'world_authority': False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2) + '\n')
        print(json.dumps({'passed': True, 'checks': checks, 'case_count': len(inputs['cases'])}))
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == '__main__':
    main()

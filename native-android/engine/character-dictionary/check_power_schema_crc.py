#!/usr/bin/env python3
"""Historical original full power schema CRC, never runtime/cache admission."""
from pathlib import Path
import types,tempfile,subprocess,zipfile,ctypes as C,argparse,json,gzip,hashlib,py_compile,os,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];LOCKED={}
def read(p):
 p=p.resolve()
 if str(p).startswith(str(ROOT/'upstream/ouroboros')+'/'):return subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+str(p.relative_to(ROOT))])
 return p.read_bytes()
def sha(p):return hashlib.sha256(read(p)).hexdigest()
def module(n,p):
 p=p.resolve();body=p.read_bytes()
 if LOCKED.get(p)!=hashlib.sha256(body).hexdigest():raise ValueError('helper not admitted '+str(p))
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(body,str(p),'exec'),m.__dict__);return m
def run(args):return subprocess.check_output(list(map(str,args))).decode().strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--supplier-root',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertion controls required')
 supplier=a.supplier_root.resolve();priorproof=HERE/'qualification/class-defines-20261017/host-proof.json.gz';priorbinding=HERE/'qualification/class-defines-20261017/source-binding.json';data={p.resolve():sha(p)for p in (priorproof,priorbinding)};binding=json.loads(priorbinding.read_text());assert sha(priorproof)==binding['host_proof_sha256'];prior=json.loads(gzip.decompress(priorproof.read_bytes()));supplier_revision=run(['git','-C',supplier,'rev-parse','HEAD']);supplier_hashes={}
 for name,h in prior['supplier_source_sha256'].items():
  p=supplier/name;assert sha(p)==h,(name,'unadmitted supplier role');assert hashlib.sha256(subprocess.check_output(['git','-C',supplier,'show',supplier_revision+':'+name])).hexdigest()==h;supplier_hashes[name]=h
 manifest=HERE/'../entities/qualification/costume-export-20261017/client-cache-manifest.json';helpers=[HERE/p for p in ['power_schema_crc_oracle.py','power_schema_crc_independent.py','class_defines_oracle.py','power_record_oracle.py','classes_oracle.py','origins_oracle.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py','../stash32/oracle.py','../stash32/source-pins.json']]+[supplier/n for n in supplier_hashes];LOCKED.update({p.resolve():sha(p)for p in helpers});m=module('power_schema_original',helpers[0]);m.module=module;independent=module('power_schema_independent',helpers[1]);mods=[module('schema_paths'+str(i),helpers[i])for i in (2,3,4,5,6,9,10)];sourcepaths=set(m.EXTRA+sum([getattr(v,'EXTRA',getattr(v,'PATHS',[]))for v in mods],[])+['Common/seq/seqstate.c','Common/seq/seqstate.h']);sources=[ROOT/'upstream/ouroboros'/p for p in sourcepaths];paths=set(helpers[:12]+sources+[priorproof,priorbinding,manifest,HERE/'attrib_names.bin',HERE/'origins.bin',HERE/'check_power_schema_crc.py',HERE/'POWER_SCHEMA_CRC.md']);hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)};assert all(sha(p)==h for p,h in data.items());source_revision=run(['git','-C',ROOT,'rev-parse','HEAD'])
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact ZIP required')
 pins=json.loads(manifest.read_text())['files'];inputs={}
 with zipfile.ZipFile(a.cache_zip)as z:
  for n in ('seqstatebits.bin','attrib_names.bin','origins.bin'):
   b=z.read('data/bin/'+n);assert hashlib.sha256(b).hexdigest()==pins['data/bin/'+n]['sha256'];inputs[n]=b
  assert z.getinfo('data/bin/powers.bin').file_size==62047164
  with z.open('data/bin/powers.bin')as f:header=f.read(12)
 assert header==b'CrypticS'+bytes.fromhex('ffb853b5');assert inputs['attrib_names.bin']==(HERE/'attrib_names.bin').read_bytes()and inputs['origins.bin']==(HERE/'origins.bin').read_bytes();seq=module('power_schema_supplier',supplier/'native-android/engine/world-render-adapter/check_surface_states.py');seq.load=module;rows=seq.states(inputs['seqstatebits.bin']);small=mods[4];loader=small.extract(read(ROOT/'upstream/ouroboros/Common/entity/powers_load.c').decode().replace('\r\n','\n'),'load_PowerDictionary');block=re.search(r'ParserLoadFiles\(pchFilename,"\.powers","powers.bin",flags\|s_ExtraLoadFlags,\s*ParsePowerDictionary,\(void\*\)ppow,NULL,NULL,load_PreprocPowerDictionary\);',loader).group();cases=[];checks=0
 with tempfile.TemporaryDirectory()as tmp:
  work=Path(tmp);p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);st=p.stat();p.write_text('value=2\n');os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns));LOCKED[p.resolve()]=sha(p);assert module('schema_stale',p).value==2;p.write_text('value=3\n')
  try:module('schema_changed',p)
  except ValueError:pass
  else:raise ValueError('changed helper executed')
  LOCKED.pop(p.resolve());source=work/'source'
  for name in sourcepaths:
   out=source/'upstream/ouroboros'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(read(ROOT/'upstream/ouroboros'/name))
  build=work/'build';build.mkdir();lib,proof=m.build(source,build,supplier,rows);lib.original_state_initialize();names=inputs['attrib_names.bin'];origins=inputs['origins.bin'];all_metadata=None
  for profile in range(8):
   stats=(C.c_uint*8)();classcrc=lib.original_class_defines(names,len(names),32+int.from_bytes(names[28:32],'little'),origins,len(origins),60,stats,profile)&0xffffffff;model=independent.schema(lib,proof);snapshot=C.create_string_buffer(262144);n=lib.original_define_slots(snapshot,len(snapshot));snapshot_bytes=C.string_at(snapshot,n);dynamic=independent.dynamic_bytes(snapshot_bytes);original=lib.original_power_schema_crc(0);observed=independent.checksum(model,dynamic);assert observed['crc']==original;checks+=1;double=independent.checksum(model,dynamic,True);assert double['crc']==lib.original_power_schema_crc(1);checks+=1;mutations=[]
   offsets=(C.c_uint*5)();assert lib.original_power_aspect_offsets(offsets)==5 and list(offsets)==[0,4,8,12,16];checks+=6
   if not profile:
    assert classcrc==0x7ff68aaf and original==0xb553b8ff and double['crc']==0xee12d099;assert snapshot_bytes==bytes.fromhex(prior['baseline_slots_hex']);assert hashlib.sha256(snapshot_bytes).hexdigest()==binding['baseline_slots_sha256'];all_metadata=model;checks+=5
   for mutation in range(5):
    expected=independent.checksum(model,dynamic,mutation=mutation);actual=lib.original_power_schema_mutated(mutation)&0xffffffff;assert expected['crc']==actual;assert (actual==original)==(mutation==0);checks+=2;mutations.append({'mutation':mutation,'crc':hex(actual),'independent':expected})
   cases.append({'profile':profile,'class_crc':hex(classcrc),'power_crc':hex(original),'independent':observed,'extra_root_defines':double,'dynamic_slots_sha256':hashlib.sha256(snapshot_bytes).hexdigest(),'mutations':mutations,'source_context_statistics':list(stats[:5])});lib.original_define_finish()
 assert hashes=={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 for name,h in supplier_hashes.items():assert sha(supplier/name)==h
 assert cases[0]['power_crc']==cases[5]['power_crc']==cases[7]['power_crc']and all(cases[i]['power_crc']!=cases[0]['power_crc']for i in (1,2,3,4,6));checks+=8
 # Metadata projection carries bytes explicitly, never executable project code.
 def plain(o):
  if isinstance(o,bytes):return {'hex':o.hex()}
  if isinstance(o,list):return[plain(x)for x in o]
  if isinstance(o,dict):return{k:plain(v)for k,v in o.items()}
  return o
 result={'schema':'coh-original-complete-power-schema-crc-v1','passed':True,'source_revision':source_revision,'source_sha256':hashes,'observed_supplier_revision':supplier_revision,'admitted_supplier_source_commit':binding['admitted_supplier_source_commit'],'supplier_source_sha256':supplier_hashes,'supplier_role_bytes_equal_prior_admitted_roles':True,'original':proof,'loader_function_sha256_lf':hashlib.sha256(loader.encode()).hexdigest(),'loader_powers_call_lf':block,'loader_powers_call_sha256_lf':hashlib.sha256(block.encode()).hexdigest(),'loader_function_executed':False,'original_root_defines_null':True,'original_static_enum_count':20,'actual_per_field_dynamic_wrapper_visits':34,'historical_original_power_schema_crc':'0xb553b8ff','observed_input_header_hex':header.hex(),'input_sha256':{k:hashlib.sha256(v).hexdigest()for k,v in inputs.items()},'cases':cases,'independent_checks':checks,'compiled_schema_metadata':plain(all_metadata),'independent_model_shared_macro_compiler_inputs':True,'independent_c_source_parser':False,'helper_loader_controls':{'stale_pyc_ignored':True,'changed_source_refused_before_execution':True},'original_oracle_sanitized':False,'win32_abi_executed':False,'runtime_cache_branch_admitted':False,'complete_dictionary_constructor_executed':False,'runtime_generation':False,'actor_authority':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'cases':len(cases),'checks':checks,'historical_crc':'0xb553b8ff','tested_files':len(hashes),'supplier_files':len(supplier_hashes)}))
if __name__=='__main__':main()

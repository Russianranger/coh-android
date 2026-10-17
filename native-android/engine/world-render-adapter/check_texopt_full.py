#!/usr/bin/env python3
"""Qualify complete historical TexOpt wire fields against unchanged original token readers."""
import argparse,hashlib,json,os,struct,tempfile
from pathlib import Path
from check_texopt_cache import load,sha,HERE,ROOT

def transcript(cache,tables,decode):
 out=bytearray(struct.pack('<I',len(cache.texopts)));leaves=0
 def scalar(kind,v):
  nonlocal leaves;leaves+=1
  if kind=='string':out.extend(struct.pack('<I',len(v)));out.extend(v)
  elif kind=='float':out.extend(struct.pack('<f',v))
  else:out.extend(struct.pack('<I',v))
 def values(vs):
  for x in vs:
   if x.kind=='struct':values(x.value)
   elif isinstance(x.value,tuple):
    for v in x.value:scalar(x.kind,v)
   else:scalar(x.kind,x.value)
 for x in cache.texopts:
  out.extend(struct.pack('<II',x.ordinal,x.offset-4));values(decode(cache,x.ordinal,tables).values);out.extend(struct.pack('<I',x.size+4))
 return bytes(out),leaves

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh receipt required')
 pins=json.loads((HERE/'texopt-cache-source-pins.json').read_text());deps=[HERE/x for x in ['CLIENT_TEXOPT_FULL.md','texopt_full_cache.py','texopt_full_oracle.py','check_texopt_full.py','texopt_cache_contract.py','texopt-cache-source-pins.json','check_texopt_cache.py','check_texname.py']]+[ROOT/x for x in pins['source_sha256']];before={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in deps}
 if any(before[x]!=v for x,v in pins['source_sha256'].items()):raise ValueError('pinned original source differs')
 cachemod=load('texopt_cache_contract',HERE/'texopt_cache_contract.py');full=load('texopt_full_cache',HERE/'texopt_full_cache.py');oracle=load('texopt_full_oracle',HERE/'texopt_full_oracle.py');old=load('texopt_full_original',HERE/'check_texname.py')
 path='upstream/ouroboros/Common/seq/tricks.c';source=(ROOT/path).read_text();tables=full.schema(source,pins['source_sha256'][path]);cache=cachemod.admit(a.actual_cache.read_bytes(),pins['cache']);expected,leaves=transcript(cache,tables,full.decode_record);controls=0
 def refused(fn):
  nonlocal controls
  try:fn();raise AssertionError('malformed accepted')
  except ValueError:controls+=1
 refused(lambda:full.schema(source+'\n',pins['source_sha256'][path]));refused(lambda:full.decode_record(cache,-1,tables));refused(lambda:full.decode_record(cache,len(cache.texopts),tables))
 from dataclasses import replace
 # Exact outer source admission and each nested parser-table length remain independent.
 sample=full.decode_record(cache,2913,tables)
 structs=[x for x in sample.values if x.kind=='struct']
 for x in structs:
  for n in [0,0xffffffff]:
   body=cache.body[:x.offset]+struct.pack('<I',n)+cache.body[x.offset+4:];mutated=replace(cache,body=body)
   refused(lambda:full.decode_record(mutated,2913,tables))
 modes={};code=oracle.create(ROOT,old.extract)
 with tempfile.TemporaryDirectory(prefix='coh-texopt-full-') as directory:
  t=Path(directory);(t/'oracle.c').write_text(code)
  for name,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   old.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-error=unused-but-set-variable',*flags,t/'oracle.c','-o',t/name]);old.run([t/name,a.actual_cache,t/(name+'.bin')],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));got=(t/(name+'.bin')).read_bytes()
   if got!=expected:raise ValueError('whole actual original-reader observation differs')
   controls+=1;modes[name]={'passed':True,'texopts':len(cache.texopts),'scalar_string_observations':leaves,'transcript_bytes':len(got),'transcript_sha256':sha(got)}
 if before!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in deps} or sha(a.actual_cache.read_bytes())!=cache.sha256:raise ValueError('source/input changed')
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':before,'cache':pins['cache'],'controls':controls,'modes':modes,'schema_tables':[(name,len(fs)) for name,fs in tables],'original_table_declarations_executed':True,'original_readbin_functions':['ParserReadBinaryTable','struct_readbin','nonarray_readbin','fixedarray_readbin','string_readbin','float_readbin','int_readbin','u8_readbin','ReadPascalString'],'table_macros_use_wire_observer_types':True,'original_storage_runtime_executed':False,'tokenstore_observers_used':True,'runtime_structure_offsets_qualified':False,'compiled_schema_crc_recomputed':False,'postprocess_executed':False,'active_client_generation':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'controls':controls,'texopts':len(cache.texopts),'leaf_observations_per_mode':leaves,'modes':list(modes)}))
if __name__=='__main__':main()

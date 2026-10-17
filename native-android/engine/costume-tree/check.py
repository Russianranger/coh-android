#!/usr/bin/env python3
"""Offline full-tree qualification; no server, Android, or dictionary publication."""
import argparse,ctypes as C,hashlib,json,os,random,subprocess,tempfile,zipfile
from pathlib import Path
import tree_oracle,independent,crc_provider
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE=HERE/'../entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip'
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,**kw)
 if r.returncode:raise RuntimeError(str(args)+'\n'+r.stdout+r.stderr)
 return r
MAIN=r'''
int main(int argc,char**argv){assert(argc==3);FILE*f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long size=ftell(f);assert(size>0&&size<=32*1024*1024);rewind(f);unsigned char*input=malloc(size),*output=malloc(32*1024*1024);assert(input&&output);assert(fread(input,1,size,f)==(size_t)size);assert(!fclose(f));unsigned stats[13]={0};unsigned char digest[32],wirehash[32];int scenario=atoi(argv[2]);assert(original_tree_roundtrip(input,size,48116,output,32*1024*1024,stats,digest,scenario));SHA256(output,stats[4],wirehash);printf("{\"stats\":[");for(unsigned i=0;i<13;i++)printf("%s%u",i?",":"",stats[i]);printf("],\"projection_sha256\":\"");for(unsigned i=0;i<32;i++)printf("%02x",digest[i]);printf("\",\"wire_sha256\":\"");for(unsigned i=0;i<32;i++)printf("%02x",wirehash[i]);printf("\"}\n");free(input);free(output);return 0;}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();assert tree_oracle.sha(ARCHIVE.read_bytes())=='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241'
 with zipfile.ZipFile(ARCHIVE)as z:raw=z.read('data/bin/costume.bin')
 assert len(raw)==17691352 and tree_oracle.sha(raw)=='10ef7562156be60bd1ef3c437c3b46d10b36b6b265129c10f39d25c4a4df5a77'
 with tempfile.TemporaryDirectory(prefix='coh-costume-tree-')as tmp:
  work=Path(tmp);lib,source=tree_oracle.build(ROOT,work);lib.original_tree_crc.restype=C.c_uint
  crcs=[lib.original_tree_crc(i)for i in range(3)];assert crcs==[0xa3374618,0xcf27aba3,0xf0095ef2]
  schemas=[]
  for i in range(lib.original_schema_count()):
   cols=[];v=(C.c_uint*3)();col=0
   while lib.original_schema_field(i,col,v):cols.append(list(v));col+=1
   schemas.append(cols)
  lib.original_tree_roundtrip.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_void_p,C.c_uint]
  cases=[];native_input=work/'costume.bin';native_input.write_bytes(raw)
  for scenario in(0,1):
   data=(C.c_ubyte*len(raw)).from_buffer_copy(raw);out=(C.c_ubyte*(32*1024*1024))();stats=(C.c_uint*13)();digest=(C.c_ubyte*32)()
   assert lib.original_tree_roundtrip(data,len(raw),48116,out,len(out),stats,digest,scenario)==1
   emitted=bytes(out[:stats[4]]);projection=independent.decode(emitted,48116,schemas)
   assert bytes(digest).hex()==projection['projection_sha256'] and list(stats)[5:]==projection['counts']
   if not scenario:assert emitted==raw
   else:assert emitted!=raw and projection['projection_sha256']!=cases[0]['projection_sha256']
   # Feed every source-produced field back through the whole original consumer.
   again=(C.c_ubyte*len(emitted)).from_buffer_copy(emitted);reout=(C.c_ubyte*(32*1024*1024))();restats=(C.c_uint*13)();redigest=(C.c_ubyte*32)()
   assert lib.original_tree_roundtrip(again,len(emitted),48116,reout,len(reout),restats,redigest,0)==1
   assert bytes(reout[:restats[4]])==emitted and bytes(redigest)==bytes(digest)
   cases.append({'scenario':scenario,'wire_sha256':tree_oracle.sha(emitted),'stats':list(stats),'projection_sha256':projection['projection_sha256'],'whole_original_reader_writer_readback':True,'independent_all_fields_match':True})
  del data,out,again,reout
  # Early/middle/late cuts and declared-size/count/string bounds; only independent
  # decoder is a malformed-input admission API. Source oracle sees verified data.
  controls=[]
  for cut in sorted(set([0,1,48115,48116,48117,len(raw)-1]+[48116+i*(len(raw)-48116)//64 for i in range(64)])):
   try:independent.decode(memoryview(raw)[:cut],48116,schemas)
   except independent.Refused:controls.append('cut:'+str(cut))
   else:raise AssertionError(('cut accepted',cut))
  for offset,value in[(48116,b'\xff'*4),(48120,b'\xff'*4),(48124,b'\xff'*4),(48128,b'\xff\xff')]:
   bad=bytearray(raw);bad[offset:offset+len(value)]=value
   try:independent.decode(bad,48116,schemas)
   except independent.Refused:controls.append('malformed:'+str(offset))
   else:raise AssertionError(('malformed accepted',offset))
  code=(work/'original-tree.c').read_text();(work/'standalone.c').write_text(code+MAIN);executions={}
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;run(['cc','-std=gnu99',*flags,'-w','-I'+str(HERE/'../costume-inputs'),work/'standalone.c','-lz','-lcrypto','-o',binary]);env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';results=[]
   for scenario in(0,1):
    result=json.loads(run([binary,native_input,scenario],env=env).stdout);assert result=={k:cases[scenario][k]for k in('stats','projection_sha256','wire_sha256')};results.append(result)
   executions[mode]={'passed':True,'binary_sha256':tree_oracle.sha(binary.read_bytes()),'cases':results}
  paths=list(HERE.glob('*.py'))+list(HERE.glob('*.h'))+[HERE/'CONTRACT.md',HERE/'source-pins.json',HERE/'../costume-inputs/oracle.py',HERE/'../costume-inputs/source-pins.json',HERE/'../costume-inputs/coh_costume_inputs.h',ARCHIVE]
  proof={'schema':1,'passed':True,'source_head':run(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip(),'source_oracle':source,'source_sha256':{str(p.relative_to(HERE)):tree_oracle.sha(p.read_bytes())for p in paths},'actual_schemas':schemas,'crc_numeric_hex':list(map(hex,crcs)),'crc_matches_all3_verified_donor_headers':True,'cases':cases,'independent_negative_controls':controls,'original_host_executions':executions,'memory':{'tracked_tree_peak_bytes':cases[0]['stats'][1],'source_allocations':cases[0]['stats'][2],'tracked_tree_heap_cap':128*1024*1024,'fixed_pointer_and_size_arrays_max_bytes':16000000,'input_cap':32*1024*1024,'output_cap':32*1024*1024,'named_C_owned_budget':256*1024*1024,'offline_preparer_only':True,'external_libraries_and_driver_runtime_RSS_included':False,'android_world_coexistence_qualified':False},'scope':{'source_schema_crc_equal':True,'runtime_cache_hit_observed':False,'shared_generation_observed':False,'original_CryptoPP_executed':False,'whole_original_engine_or_Win32_ABI':False,'preprocessor_or_final_callbacks_applied':False,'original_stash_builder_executed':False,'authentic_runtime_dictionary':False,'actor_or_ACK_authority':False,'android_built':False,'real_server_executed':False,'external_zlib_openssl_sanitizer_closure':False,'leak_sanitizer_executed':False}}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(cases),'negative_controls':len(controls),'output':str(a.output)}))
if __name__=='__main__':main()

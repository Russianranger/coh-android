#!/usr/bin/env python3
import argparse,ctypes as C,functools,gzip,hashlib,json,struct,subprocess,tempfile,zipfile
from pathlib import Path
import oracle,independent
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
class Bytes(C.Structure):_fields_=[('data',C.c_void_p),('size',C.c_size_t)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--slots-output',required=True,type=Path);a=p.parse_args();archive=HERE/'../entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip';assert sha(archive.read_bytes())=='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241'
 with zipfile.ZipFile(archive)as z:raw=z.read('data/bin/costume.bin');colors=z.read('data/bin/supergroupColors.bin')
 assert sha(raw)=='10ef7562156be60bd1ef3c437c3b46d10b36b6b265129c10f39d25c4a4df5a77'and sha(colors)=='e5676ebbccc380f9d69322ef6750332b0b7e7a46d915bdfb591322862d22cb75'
 with tempfile.TemporaryDirectory(prefix='coh-primary-builder-')as tmp:
  w=Path(tmp);lib,source=oracle.build(ROOT,w);lib.original_primary_builder.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint];lib.original_builder_schema_name.restype=C.c_char_p
  data=(C.c_ubyte*len(raw)).from_buffer_copy(raw);palette=(C.c_ubyte*len(colors)).from_buffer_copy(colors);out=(C.c_ubyte*(16*1024*1024))();tr=(C.c_ubyte*(32*1024*1024))();stats=(C.c_uint*14)();cases=[]
  for scenario in range(4):
   size=lib.original_primary_builder(data,len(raw),palette,len(colors),out,len(out),tr,len(tr),stats,scenario);assert size==stats[0];slots=bytes(out[:size]);trace=bytes(tr[:stats[1]])
   assert sha(slots)=='2e69212432d1b16a38f307aca16ac892cca56cf59128d5d8d25e71386da4af81'and sha(trace)=='21f83d2ddca9ffe3950631c9aa25c72dd4a38c1b512162d3c9e9048db8bc7237'
   cases.append({'scenario':scenario,'final_callback_executed':bool(scenario),'account_published_policy':['callback not executed','all true','all false','alternating'][scenario],'source_stats':list(stats),'slots_sha256':sha(slots),'trace_sha256':sha(trace)})
  schemas=[];names=[]
  for i in range(lib.original_schema_count()):
   cols=[];n=[];v=(C.c_uint*3)();col=0
   while lib.original_schema_field(i,col,v):cols.append(list(v));n.append(lib.original_builder_schema_name(i,col).decode());col+=1
   schemas.append(cols);names.append(n)
  h=hashlib.sha256();traversal=independent.trace(raw,colors,schemas,names,h.update);assert h.hexdigest()==sha(trace)
  native=w/'native-hash.so';subprocess.run(['cc','-std=c99','-O2','-shared','-fPIC',HERE/'../stash32/coh_stash32.c','-o',native],check=True);n=C.CDLL(str(native));n.coh_stash32_string_hash.argtypes=[Bytes,C.c_uint,C.c_void_p];n.coh_stash32_int_hash.argtypes=[C.c_uint,C.c_uint];n.coh_stash32_int_hash.restype=C.c_uint
  @functools.lru_cache(maxsize=32768)
  def string_hash(b):
   buf=C.create_string_buffer(b);o=C.c_uint();assert n.coh_stash32_string_hash(Bytes(C.cast(buf,C.c_void_p),len(b)),0xfaceface,C.byref(o))==0;return o.value
  def int_hash(v):return n.coh_stash32_int_hash(v,0xfaceface)
  expected,counts=independent.replay(trace,string_hash,int_hash);assert expected==slots
  # Every primary slot/header/hole is compared, not only compact valid strings.
  # Trace refusal/mutated-order controls execute the independent consumer.
  controls=0
  for bad in(trace[:1],trace[:-1],struct.pack('<I',3)+trace[4:]):
   try:independent.replay(bad,string_hash,int_hash)
   except independent.Refused:controls+=1
   else:raise AssertionError('malformed trace admitted')
  # Original full source constructor/resize ordering must affect this actual set.
  # Reverse event order and verify byte equality is refused (all keys retained).
  at=0;records=[];max_string=0
  while at<len(trace):
   kind,length=struct.unpack_from('<II',trace,at);end=at+8+(0 if kind==2 else length);records.append(trace[at:end]);at=end
   if kind!=2:max_string=max(max_string,length)
  changed,_=independent.replay(b''.join(reversed(records)),string_hash,int_hash);assert changed!=slots;controls+=1;del records,changed
  a.slots_output.parent.mkdir(parents=True,exist_ok=True);a.slots_output.write_bytes(gzip.compress(slots,mtime=0))
  inputs=list(HERE.glob('*.py'))+list(HERE.glob('*.h'))+[HERE/'source-pins.json',HERE/'CONTRACT.md',archive]
  # Bind all provider generators/adapters and their frozen input pins.
  for folder in('costume-tree','stash32','costume-inputs'):
   inputs+=list((HERE/'..'/folder).glob('*.py'))+list((HERE/'..'/folder).glob('*.h'))+list((HERE/'..'/folder).glob('*.c'))+[(HERE/'..'/folder)/'source-pins.json']
  receipt={'schema':1,'passed':True,'source_oracle':source,'source_sha256':{str(p.relative_to(HERE)):sha(p.read_bytes())for p in inputs},'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'cases':cases,'independent_source_order':traversal,'independent_slot_replay':counts,'slot_bytes':len(slots),'slots_sha256':sha(slots),'compressed_slots_bytes':a.slots_output.stat().st_size,'compressed_slots_sha256':sha(a.slots_output.read_bytes()),'trace_bytes':len(trace),'trace_sha256':sha(trace),'largest_primary_string_bytes':max_string,'negative_controls':controls,'native_byte_safe_hash_binary_sha256':sha(native.read_bytes()),'memory':{'source_tree_heap_peak_bytes':stats[11],'source_owned_aggregate_cap':256*1024*1024,'expanded_tree_offline_only':True,'driver_Python_RSS_or_external_dependency_stack_included':False},'scope':{'whole_original_primary_builder_and_stash_loops':True,'independent_complete_trace_and_fullholes_equal':True,'original_source_ub4_bound_uint32':True,'original_unsafe_hash_oracle_sanitized':False,'new_native_full_dictionary_owner':False,'ancillary_reward_tagged_geometry_semantics_qualified':False,'account_policy_qualified':False,'runtime_cache_or_shared_generation_observed':False,'Win32_ABI_executed':False,'authentic_runtime_dictionary_admitted':False,'actor_or_ACK_authority':False,'android_built':False,'server_executed':False}}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'counts':counts,'output':str(a.output)}))
if __name__=='__main__':main()

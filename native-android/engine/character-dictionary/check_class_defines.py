#!/usr/bin/env python3
"""Reconstruct exact original dynamic defines and historical class schema CRC."""
import argparse,ctypes as C,gzip,hashlib,json,os,struct,subprocess,tempfile,types,zipfile,py_compile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];LOCKED={}
def read(p):
 p=p.resolve()
 if str(p).startswith(str(ROOT/'upstream/ouroboros')+'/'):return subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+str(p.relative_to(ROOT))])
 return p.read_bytes()
def sha(p):return hashlib.sha256(read(p)).hexdigest()
def module(n,p):
 p=p.resolve();body=p.read_bytes()
 if LOCKED.get(p)!=hashlib.sha256(body).hexdigest():raise ValueError('helper source not admitted '+str(p))
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(body,str(p),'exec'),m.__dict__);return m
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-8000:]+p.stderr[-8000:])
 return p.stdout
def controls(work):
 p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);stat=p.stat();p.write_text('value=2\n');os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns));LOCKED[p.resolve()]=sha(p);assert module('define_stale',p).value==2;p.write_text('value=3\n')
 try:module('define_changed',p)
 except ValueError:pass
 else:raise ValueError('changed source executed')
 LOCKED.pop(p.resolve());return {'stale_pyc_ignored':True,'changed_source_refused_before_execution':True}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--supplier-root',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():ap.error('fresh output required')
 if not __debug__:raise ValueError('qualification assertions must remain enabled')
 sr=a.supplier_root.resolve();eh=sr/'native-android/engine/world-render-adapter';supplier_revision=run(['git','-C',sr,'rev-parse','HEAD']).strip()
 epaths=[eh/p for p in('CLIENT_SURFACE_STATES.md','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','check_surface_states.py','tests/test_surface_states.c','texopt_cache_contract.py','check_texname.py')]+[sr/'upstream/ouroboros/Common/seq'/n for n in('seqstate.c','seqstate.h','TriggeredMove.h')]+[sr/'native-android/engine/coh_contracts.h']
 supplier_hashes={str(p.relative_to(sr)):sha(p)for p in epaths}
 for n in('seqstate.c','seqstate.h','TriggeredMove.h'):
  path='upstream/ouroboros/Common/seq/'+n
  if supplier_hashes[path]!=sha(ROOT/path):raise ValueError('supplier original source mismatch '+path)
 for p,h in supplier_hashes.items():
  if hashlib.sha256(subprocess.check_output(['git','-C',sr,'show',supplier_revision+':'+p])).hexdigest()!=h:raise ValueError('supplier uncommitted source '+p)
 helpers=[HERE/p for p in('class_defines_oracle.py','class_defines_independent.py','classes_oracle.py','origins_oracle.py','check_origins.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py','../stash32/oracle.py','../stash32/source-pins.json','../costume-builder/independent.py')]+epaths
 LOCKED.update({p.resolve():sha(p)for p in helpers});oracle=module('define_original',helpers[0]);oracle.module=module;independent=module('define_model',helpers[1]);classes=module('define_class_paths',helpers[2]);origin=module('define_origin_paths',helpers[3]);origin_decode=module('define_origin_decoder',helpers[4]);small=module('define_small_paths',helpers[5]);crc=module('define_crc_paths',helpers[8]);stash=module('define_stash_paths',helpers[9]);table=module('define_slot_model',helpers[11]);supplier=module('define_seq_supplier',eh/'check_surface_states.py');supplier.load=module
 original=set(small.PATHS+origin.EXTRA+classes.EXTRA+oracle.EXTRA+crc.PATHS+stash.PATHS+['Common/seq/seqstate.c','Common/seq/seqstate.h']);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in original];paths=set(helpers[:-len(epaths)]+sourcepaths+[HERE/'check_class_defines.py',HERE/'CLASS_DEFINES.md',HERE/'attrib_names.bin',ROOT/'native-android/engine/entities/qualification/costume-export-20261017/client-cache-manifest.json',HERE/'origins.bin',HERE/'../stash32/coh_stash32.c',HERE/'../stash32/coh_stash32.h',HERE/'../coh_contracts.h']);hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('donor identity')
 with zipfile.ZipFile(a.cache_zip)as z:
  inputs={}
  for name,size in [('attrib_names.bin',10592),('seqstatebits.bin',15380)]:
   info=z.getinfo('data/bin/'+name)
   if info.file_size!=size:raise ValueError('cache bound')
   with z.open(info)as f:inputs[name]=f.read(size+1);assert len(inputs[name])==size and not f.read(1)
  class_headers={}
  for name,size in [('classes.bin',1219292),('villain_classes.bin',4228088)]:
   info=z.getinfo('data/bin/'+name)
   if info.file_size!=size:raise ValueError('class member bound')
   with z.open(info)as f:header=f.read(12)
   if len(header)!=12 or header[:8]!=b'CrypticS':raise ValueError('class envelope')
   class_headers[name]=int.from_bytes(header[8:12],'little')
  if set(class_headers.values())!={0x7ff68aaf}:raise ValueError('historical class headers changed')
 # Exact known state SHA and exact whole donor+member identity bind new name bytes.
 if hashlib.sha256(inputs['seqstatebits.bin']).hexdigest()!='9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac':raise ValueError('state identity')
 names=inputs['attrib_names.bin'];assert names==(HERE/'attrib_names.bin').read_bytes();origins=(HERE/'origins.bin').read_bytes();name_crc,name_rows=independent.attrib_names(names);origin_rows=origin_decode.decode(origins)['rows'];seqrows=supplier.states(inputs['seqstatebits.bin']);texts={p:read(ROOT/'upstream/ouroboros'/p).decode().replace('\r\n','\n')for p in original};cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-class-defines-')as tmp:
  work=Path(tmp);loader=controls(work);originalroot=work/'source'
  for p in sourcepaths:
   dst=originalroot/p.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(read(p))
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow,sr,seqrows);lib.original_state_initialize();lib.original_state_count.restype=C.c_uint
  class StateBit(C.Structure):_fields_=[('name',C.c_char_p),('bitNum',C.c_uint32),('flags',C.c_uint32)]
  lib.original_state.argtypes=[C.c_uint];lib.original_state.restype=C.POINTER(StateBit)
  assert lib.original_state_count()==875;roundtrip=C.create_string_buffer(65536);assert lib.original_names_roundtrip(names,len(names),32+int.from_bytes(names[28:32],'little'),roundtrip)==len(names)and roundtrip.raw[:len(names)]==names;assert(lib.original_names_crc()&0xffffffff)==name_crc
  hashlibpath=work/'native_hash.so';run(['cc','-std=c99','-O2','-shared','-fPIC',HERE/'../stash32/coh_stash32.c','-o',hashlibpath]);native=C.CDLL(str(hashlibpath))
  class Bytes(C.Structure):_fields_=[('data',C.c_void_p),('size',C.c_size_t)]
  native.coh_stash32_string_hash.argtypes=[Bytes,C.c_uint32,C.c_void_p]
  def hashfn(key):
   buf=C.create_string_buffer(key);out=C.c_uint32();assert native.coh_stash32_string_hash(Bytes(C.cast(buf,C.c_void_p),len(key)),0xfaceface,C.byref(out))==0;return out.value
  accepted_slots=None;accepted_trace=None;accepted_snapshot=None;checks=0
  for profile in range(8):
   stats=(C.c_uint*8)();observed=lib.original_class_defines(names,len(names),32+int.from_bytes(names[28:32],'little'),origins,len(origins),60,stats,profile)&0xffffffff;buffer=C.create_string_buffer(262144);n=lib.original_define_trace(buffer,len(buffer));trace=buffer.raw[:n];pairs,states=independent.traces(texts,seqrows,origin_rows,name_rows,profile);
   for i,name in enumerate(states):
    state=lib.original_state(i).contents;assert state.name==name.encode()and state.bitNum==i
   assert independent.parse_trace(trace)==pairs;assert trace==independent.trace_wire(pairs);n=lib.original_define_slots(buffer,len(buffer));snapshot=buffer.raw[:n];slots=independent.parse_slots(snapshot);model=table.Table(128,0,hashfn);values={};duplicates=[]
   for k,v in pairs:
    key=k.encode();model.insert(key);fold=k.lower()
    if fold not in values:values[fold]=v
    else:duplicates.append({'key':k,'retained':values[fold],'refused':v})
   expected=[None if k is None else(k.decode(),values[k.decode().lower()])for k in model.slots];assert expected==slots;assert stats[0]==len(slots)and stats[1]==model.count and stats[3]==len(pairs)and stats[4]==model.resizes
   adler=independent.slot_crc(slots);crc_bytes=struct.pack('>I',adler);assert(lib.original_define_crc_only()&0xffffffff)==int.from_bytes(crc_bytes,'little')
   if profile==0:accepted_slots=slots;accepted_trace=trace;accepted_snapshot=snapshot;assert observed==0x7ff68aaf
   elif profile==5:assert observed==0x7ff68aaf and slots==accepted_slots
   else:assert observed!=0x7ff68aaf
   checks+=len(pairs)+len(slots)+len(states)+5;cases.append({'profile':profile,'class_schema_crc':hex(observed),'max_size':stats[0],'valid':stats[1],'attempts':stats[3],'resizes':stats[4],'trace_sha256':hashlib.sha256(trace).hexdigest(),'slots_sha256':hashlib.sha256(snapshot).hexdigest(),'define_only_adler32':hex(adler),'duplicates':duplicates,'every_trace_pair_and_full_slot_equal':True});lib.original_define_finish()
  lib.original_state_destroy();native_hash_sha=sha(hashlibpath)
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}or supplier_hashes!={str(p.relative_to(sr)):sha(p)for p in epaths}:raise ValueError('source changed')
 result={'schema':'coh-original-class-dynamic-defines-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'supplier_revision':supplier_revision,'supplier_source_sha256':supplier_hashes,'original':proof,'helper_loader_controls':loader,'input_sha256':{k:hashlib.sha256(v).hexdigest()for k,v in inputs.items()},'attrib_names_original_crc':hex(name_crc),'class_cache_headers':class_headers,'attrib_names_exact_original_roundtrip':True,'independent_checks':checks,'baseline_trace_hex':accepted_trace.hex(),'baseline_slots_hex':accepted_snapshot.hex(),'cases':cases,'native_independent_hash_binary_sha256':native_hash_sha,'original_class_crc_exact':True,'observed_class_cache_header_crc':'0x7ff68aaf','source_width_binding_ub4':32,'source_width_binding_auto_size_t':32,'original_abi_win32_executed':False,'original_hash_sanitized':False,'stringtable_storage_adapter':True,'original_repack_finalize_executed':False,'runtime_cache_generation':False,'actor_authority':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'independent_checks':checks,'profiles':len(cases),'baseline_crc':cases[0]['class_schema_crc'],'slots':cases[0]['max_size'],'valid':cases[0]['valid']}))
if __name__=='__main__':main()

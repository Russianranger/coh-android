#!/usr/bin/env python3
"""Trusted original-leaf execution and independent wire projections, no live permit."""
import argparse,ctypes as C,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def frozen(root):
 paths=set(HERE.glob('leaf_*'))|{HERE/'check_leaves.py',HERE/'leaf-source-pins.json'}
 for manifest,key in [(root/'native-android/engine/entities/source-pins.json','sha256_lf'),(HERE/'leaf-source-pins.json','additional_full_sources_sha256_lf')]:
  paths|={root/'upstream/ouroboros'/name for name in json.loads(manifest.read_text())[key]}
 for directory in [root/'native-android/engine/entities',root/'native-android/tools/protocol_fixture']:
  paths|={p for p in directory.iterdir() if p.suffix in {'.h','.inc','.py','.json'}}
 paths|=set((root/'native-android/include').rglob('*.h'))
 return {str(p.relative_to(root)):digest(p)for p in sorted(paths)if p.is_file()}
def bits(data,begin,end):return [(data[i//8]>>(i%8))&1 for i in range(begin,end)]
def packbytes(seq):
 out=bytearray((len(seq)+7)//8)
 for i,b in enumerate(seq):out[i//8]|=b<<(i%8)
 return bytes(out)
class Writer:
 def __init__(self,aligned):self.a=aligned;self.b=[]
 def scalar(self,n,v):
  v&=(1<<n)-1;n=(n+7)&~7 if self.a else n
  self.b += [(v>>i)&1 for i in range(n)]
 def packed(self,n,v):
  if self.a:self.scalar(32,v);return
  while n<32 and v >= (1<<n)-1:
   mask=(1<<n)-1;self.scalar(n,mask);v-=mask;n=min(n*2,32)
  self.scalar(n,v)
 def optional(self,n,v,packed=False):
  self.scalar(1,bool(v))
  if v:(self.packed if packed else self.scalar)(n,v)
 def auto(self,v):
  widths=[2,10,24,32];index=next(i for i,n in enumerate(widths)if v.bit_length()<=n)
  self.scalar(2,index);self.scalar(widths[index],v)
 def string(self,s):
  for c in s.encode()+b'\0':self.b += [(c>>i)&1 for i in range(8)]
def run(root,work):
 before=frozen(root);spec=importlib.util.spec_from_file_location('record_leaves',HERE/'leaf_oracle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 lib,source=m.build(root,work);cases=[];checks=0
 lib.original_stats.argtypes=[C.c_int,C.c_int,C.c_void_p,C.c_void_p,C.c_void_p]
 lib.original_receive_stats.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_int,C.c_void_p,C.c_void_p]
 for kind in range(1,5):
  for scenario in range(4):
   for aligned,prefix in [(0,i)for i in range(8)]+[(1,0)]:
    out=(C.c_ubyte*65536)();end=C.c_uint();begin=C.c_uint();size=C.c_uint();lib.original_record_leaf(kind,scenario,aligned,prefix,out,C.byref(size),C.byref(begin),C.byref(end))
    wire=bytes(out[:(size.value+7)//8]);body=bits(wire,begin.value,end.value)
    assert begin.value==prefix and end.value==size.value and bits(wire,0,prefix)==[i&1 for i in range(prefix)];checks+=3
    w=Writer(aligned)
    if kind==1:
     if scenario==1:w.scalar(1,0);assert body==w.b;checks+=1
     else:
      w.scalar(1,1);w.scalar(1,scenario!=2);assert body[:len(w.b)]==w.b;checks+=1
      if scenario==2:assert body==w.b;checks+=1
      else:
       raw=packbytes(body[len(w.b):]);array=(C.c_ubyte*len(raw)).from_buffer_copy(raw);values=(C.c_float*16)();integers=(C.c_int*6)();lib.original_receive_stats(array,len(body)-len(w.b),aligned,0,values,integers)
       if scenario==0:
        expected=(C.c_ubyte*32768)();count=C.c_uint();scalars=(C.c_float*5)();lib.original_stats(0,aligned,expected,C.byref(count),scalars)
        assert body[len(w.b):]==bits(bytes(expected),0,count.value);checks+=1
        assert list(integers)==[12,14,0,0,0,0];checks+=1
       else:assert list(values)==[0.0]*16 and list(integers)==[0]*6;checks+=1
       assert len(body)>len(w.b)+1;checks+=1
    elif kind==2:w.scalar(1,0);assert body==w.b;checks+=1
    elif kind==3:
     w.scalar(1,scenario!=1)
     if scenario!=1:
      w.optional(8,[33,0,0,2147483647][scenario],True);w.optional(4,[4,0,0,65535][scenario],True);w.optional(11,1248 if scenario==2 else 0)
     assert body==w.b;checks+=1
    else:
     w.scalar(10,[0,1023,0,772][scenario]);w.auto(5 if scenario==1 else 1);w.auto(1 if scenario==1 else 0);w.auto([0,2,0,1][scenario])
     if scenario in(1,3):w.string('source-status')
     if scenario==1:w.string('')
     assert body==w.b;checks+=1
    cases.append({'kind':kind,'scenario':scenario,'aligned':aligned,'prefix':prefix,'begin':begin.value,'end':end.value,'wire_hex':wire.hex()})
 assert frozen(root)==before
 original={**source['base_source_pins'],**source['additional_full_sources_sha256_lf']}
 for p,expected in original.items():assert hashlib.sha256((root/'upstream/ouroboros'/p).read_text().encode()).hexdigest()==expected
 return {'passed':True,'checks':checks,'case_count':len(cases),'source_sha256':before,'source_proof':source,'cases':cases,'scope':{'original_trusted_host_producers':True,'original_schema_consumer_for_self_stats':True,'original_sequence_status_ragdoll_consumers':False,'sanitizers':False,'whole_engine':False,'win32':False,'live_server':False,'dictionary_authority':False,'actor':False,'ACK':False}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-leaf-proof-')as d:result=run(a.root.resolve(),Path(d))
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':result['checks'],'cases':result['case_count']}))

#!/usr/bin/env python3
"""Generic original outer CONTROL qualification; marker children, not child grammar."""
import argparse,ctypes as C,hashlib,importlib.util,json,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args()
 if args.output.exists():raise ValueError('fresh output required')
 deps={HERE/n for n in ['generic_order.py','check_generic_order.py','order_oracle.py','outer_adapters.h','outer_wrapper.h']}
 deps|={ROOT/'native-android/engine/dbclient'/n for n in ['check.py','source-pins.json']};deps|={ROOT/'native-android/tools/protocol_fixture/prepare.py'};deps|=set((ROOT/'native-android/include').rglob('*.h'))
 pins=json.loads((ROOT/'native-android/engine/dbclient/source-pins.json').read_text())
 if 'sha256_lf' in pins:pins=pins['sha256_lf']
 deps|={ROOT/'upstream/ouroboros'/n for n in pins};deps|={ROOT/'upstream/ouroboros/MapServer/src/entity/entsend.c'}
 before={str(p.relative_to(ROOT)):sha(p)for p in sorted(deps)}
 m=module('generic_order_provider',HERE/'generic_order.py');checks=0;cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-generic-order-')as temp:
  lib,proof=m.build(ROOT,Path(temp));lib.record_outer.argtypes=[C.c_uint]*3+[C.c_void_p]*6;lib.record_generic_indices.argtypes=[C.c_uint,C.c_uint]
  for aligned in [0,1]:
   lib.record_clear_children();keep=[]
   for ident in range(1,24):
    n=8 if aligned else 1+ident%7;value=ident&((1<<n)-1);data=(C.c_ubyte*4).from_buffer_copy(value.to_bytes(4,'little'));keep.append(data);lib.record_set_child(ident,data,n,255)
   for profile in range(5):
    for scenario in range(16):
     for prefix in (range(8)if not aligned else[0]):
      out=(C.c_ubyte*65536)();bits=C.c_uint();begin=C.c_uint();events=(C.c_uint*72)();count=C.c_uint();lib.record_generic_outer(profile,scenario,aligned,prefix,out,C.byref(bits),C.byref(begin),events,C.byref(count));rows=[list(events[i*3:i*3+3])for i in range(count.value)]
      ids=list(range(1,8))
      if profile in[0,1,2,4] and not scenario&8:ids+=[8]
      ids += [9,10,11]
      if profile in[0,1,2,4]:ids += [12,13]
      if profile==0:
       if scenario&2:ids += [14]
       ids += [15]
       if scenario&1:ids += [16,17]
      ids += list(range(18,24));assert [x[0]for x in rows]==ids;checks+=1
      assert begin.value>prefix and bits.value>begin.value;checks+=2
      for ident,start,end in rows:
       n=8 if aligned else 1+ident%7;value=ident&((1<<n)-1);assert end-start==n;assert sum(((out[i//8]>>(i%8))&1)<<(i-start)for i in range(start,end))==value;checks+=2
      wire=bytes(out[:(bits.value+7)//8])
      if profile==0:
       old=(C.c_ubyte*65536)();oldbits=C.c_uint();oldbegin=C.c_uint();bounds=(C.c_uint*28)();oldevents=(C.c_uint*72)();oldcount=C.c_uint();lib.record_outer(scenario,aligned,prefix,old,C.byref(oldbits),C.byref(oldbegin),bounds,oldevents,C.byref(oldcount));assert(oldbits.value,oldbegin.value,bytes(old[:(oldbits.value+7)//8]),list(oldevents[:oldcount.value*3]))==(bits.value,begin.value,wire,list(events[:count.value*3]));checks+=1
      cases.append({'profile':profile,'scenario':scenario,'aligned':aligned,'prefix':prefix,'begin':begin.value,'bits':bits.value,'sha256':hashlib.sha256(wire).hexdigest(),'events':rows})
 # Original signed-negative delta is preserved by the unchanged U32 bit writer.
  index_deltas=[]
  for index,previous in [(1,0),(17,16),(99,4),(4,99),(1,10239)]:
   lib.record_generic_indices(index,previous)
   for aligned in [0,1]:
    lib.record_clear_children();out=(C.c_ubyte*65536)();bits=C.c_uint();begin=C.c_uint();events=(C.c_uint*72)();count=C.c_uint();lib.record_generic_outer(3,0,aligned,0,out,C.byref(bits),C.byref(begin),events,C.byref(count));expected=(index-previous-1)&0xffffffff
    if aligned:assert begin.value==32 and int.from_bytes(bytes(out[:4]),'little')==expected
    else:
     pos=0;width=1;value=0
     while True:
      word=sum(((out[(pos+i)//8]>>((pos+i)%8))&1)<<i for i in range(width));pos+=width
      if word!=(1<<width)-1 or width==32:value=(value+word)&0xffffffff;break
      value=(value+word)&0xffffffff;width=min(width*2,32)
     assert pos==begin.value and value==expected
    checks+=2;index_deltas.append({'index':index,'previous':previous,'aligned':aligned,'original_u32_delta':expected,'record_begin':begin.value})
 assert before=={str(p.relative_to(ROOT)):sha(p)for p in deps}
 result={'passed':True,'controls':checks,'profiles':720,'index_deltas':index_deltas,'source_sha256':before,'source_proof':proof,'cases':cases,'original_child_producers':False,'marker_children':True,'whole_engine':False,'generic_child_object_graph':False,'live_server':False,'actor':False,'ACK':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'controls':checks,'profiles':len(cases)}))
if __name__=='__main__':main()

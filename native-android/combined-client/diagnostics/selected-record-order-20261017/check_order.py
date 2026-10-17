#!/usr/bin/env python3
"""Small source order/inline-control fixture qualification; no child semantics."""
import argparse,ctypes as C,hashlib,json,tempfile,subprocess,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('Fresh output required')
 dependencies=list(HERE.glob('*.py'))+list(HERE.glob('*.h'))+[root/'native-android/engine/dbclient/check.py',root/'native-android/engine/dbclient/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py']
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in dependencies}
 # Freeze every executed helper before importing its implementation.
 spec=importlib.util.spec_from_file_location('frozen_selected_order',HERE/'order_oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 cases=[];checks=0
 with tempfile.TemporaryDirectory(prefix='coh-selected-order-')as directory:
  lib,source=oracle.build(root,Path(directory));lib.record_clear_children();buffers=[]
  # Explicit relocation-safe marker spans, NOT source child grammar fixtures.
  for child in range(1,24):
   data=(C.c_ubyte*2)(child,child^0xa5);buffers.append(data);lib.record_set_child(child,data,16,255)
  for scenario in range(16):
   for aligned,prefix in[(0,k)for k in range(8)]+[(1,0)]:
    out=(C.c_ubyte*65536)();bits=C.c_uint();begin=C.c_uint();bounds=(C.c_uint*28)();events=(C.c_uint*72)();count=C.c_uint()
    lib.record_outer(scenario,aligned,prefix,out,C.byref(bits),C.byref(begin),bounds,events,C.byref(count))
    expected=[n for n in range(1,24)if not(n==8 and scenario&8)and not(n==14 and not scenario&2)and not(n in(16,17)and not scenario&1)]
    actual=[events[k*3]for k in range(count.value)];assert actual==expected;checks+=1
    assert bounds[0]==bounds[26]==begin.value and bounds[25]==bounds[27]==bits.value;checks+=1
    for stage in range(13):
     assert bounds[stage*2]<=bounds[stage*2+1]
     if stage:assert bounds[stage*2]==bounds[stage*2-1]
     checks+=1
    wire=bytes(out[:(bits.value+7)//8]);assert len(wire)<=65536
    for k,child in enumerate(actual):
     start,end=events[3*k+1],events[3*k+2];assert end-start==16
     value=sum(((wire[(start+i)//8]>>((start+i)&7))&1)<<i for i in range(16));assert value==child+((child^0xa5)<<8);checks+=2
    cases.append({'scenario':scenario,'aligned':aligned,'prefix':prefix,'bits':bits.value,'record_begin':begin.value,'stage_boundaries':list(bounds),'events':[list(events[k*3:k*3+3])for k in range(count.value)],'wire_hex':wire.hex(),'wire_sha256':oracle.sha(wire)})
 assert hashes=={str(p):oracle.sha(p.read_bytes())for p in dependencies}
 for name,pin in source['base_original_bit_writer_pins'].items():
  assert oracle.sha((root/'upstream/ouroboros'/name).read_text().replace('\r\n','\n').encode())==pin
 assert oracle.sha((root/'upstream/ouroboros'/oracle.SOURCE).read_text().replace('\r\n','\n').encode())==oracle.SOURCE_SHA
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({'passed':True,'source':source,'helper_sha256':hashes,'checks':checks,'cases':cases,'case_count':len(cases),'marker_child_grammar_qualified':False,'whole_original_control_function_executed':True,'original_child_serializers_executed':False,'original_consumer_executed':False,'sanitizers':False,'server_executed':False,'android_executed':False,'actor_or_ACK':False},indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()

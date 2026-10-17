#!/usr/bin/env python3
"""Small trusted original-producer corpus plus independent bit decoder."""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
sourcepins=json.loads((HERE/'source-pins.json').read_text());paths=[HERE/'oracle.py',HERE/'wrapper.h',HERE/'source-pins.json',Path(__file__),ROOT/'native-android/tools/protocol_fixture/prepare.py']+[ROOT/'upstream/ouroboros'/x for x in sourcepins['whole_sources_sha256_lf']]
sha=lambda b:hashlib.sha256(b).hexdigest();before={str(x.relative_to(ROOT)):sha(x.read_bytes())for x in paths}
s=importlib.util.spec_from_file_location('tail_admitted',HERE/'oracle.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
# Independent explicit bit reader; no native/client helper calls.
def observe(data,bits,begin,aligned):
 at=begin;marks=meta=0
 def read(n):
  nonlocal at
  if aligned:at=(at+7)//8*8
  if at+n>bits:raise ValueError('short')
  v=sum(((data[(at+i)//8]>>((at+i)%8))&1)<<i for i in range(n));at+=n;return v
 for _ in range(258):
  if aligned:cmd=read(32)
  else:
   cmd=0;n=1
   while True:
    v=read(n);cmd+=v
    if v!=(1<<n)-1 or n==32:break
    n=min(32,n*2)
  if cmd==0:
   if at!=bits:raise ValueError('late')
   return at,marks,meta
  if cmd==15:marks+=1
  elif cmd==197:meta+=1;at=(at+7)//8*8
  else:raise ValueError('unsupported')
 raise ValueError('limit')
cases=[];checks=0
with tempfile.TemporaryDirectory(prefix='coh-tail-source-') as d:
 lib,pins=m.build(ROOT,Path(d));lib.restricted_tail_observe.argtypes=[C.c_void_p]+[C.c_uint]*3+[C.c_void_p]*3
 for aligned in [0,1]:
  for prefix in ([0] if aligned else range(8)):
   for profile in range(3):
    for marks in [0,1,3,16,128,255,256]:
     # max258 commands includes outermeta +innermeta +zero; profile2 caps255.
     if profile==2 and marks==256:continue
     out=C.create_string_buffer(8192);bits=C.c_uint();begin=C.c_uint();end=C.c_uint();lib.original_tail(profile,aligned,prefix,marks,out,C.byref(bits),C.byref(begin),C.byref(end));wire=out.raw[:(bits.value+7)//8]
     expected=(bits.value,marks,0 if profile==0 else profile)
     assert observe(wire,bits.value,begin.value,aligned)==expected;checks+=1
     seen=[C.c_uint()for _ in range(3)];assert lib.restricted_tail_observe(wire,bits.value,begin.value,aligned,*[C.byref(x)for x in seen])==1;assert tuple(x.value for x in seen)==expected;checks+=2
     for cut in range(begin.value,bits.value):
      try:observe(wire,cut,begin.value,aligned)
      except ValueError:pass
      else:raise AssertionError('truncation admitted')
      checks+=1
     cases.append(dict(profile=profile,aligned=aligned,prefix=prefix,markers=marks,wire_hex=wire.hex(),bits=bits.value,begin=begin.value,end=end.value,meta=expected[2]))
assert before=={str(x.relative_to(ROOT)):sha(x.read_bytes())for x in paths}
r={'schema':'coh-original-nested-command-framing-v1','passed':True,'checks':checks,'cases':cases,'source_sha256':before,'original':pins,'whole_dispatcher_executed':False,'original_early_ack_executed':False,'original_producer_sanitized':False,'transport_live_actor_world_ack_permit':False,'scope':'unchanged append block/final statement and whole bit+alignment functions; restricted 15/197/zero observer, fixtures only'}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'cases':len(cases),'checks':checks}))

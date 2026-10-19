#!/usr/bin/env python3
"""Focused first-create probe; original component writers, no live packet claim."""
import argparse, ctypes as C, hashlib, importlib.util, json, os, shlex, struct, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(raw): return hashlib.sha256(raw).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode: raise RuntimeError(repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path); value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def fixtures(lib,work):
 rows=[]; metadata=[]
 def fields(mode,widths,values):
  output=(C.c_uint8*32768)();length=C.c_uint32()
  lib.original_fields((C.c_int*len(widths))(*widths),(C.c_uint32*len(values))(*values),len(values),mode,output,C.byref(length))
  return [(output[i//8]>>(i%8))&1 for i in range(length.value)]
 def build(mode,start,scenario,variant):
  bits=[0]*start;bits+=fields(mode,[-1],[3]);post=len(bits)
  odd=0 if variant==2 else 1
  widths=[-1,1,-1,32,-1,-1,-1,32,32,32,-1,32,32,1]
  values=[7,odd,99 if variant==4 else 11,0x3f800000,12,0xffffffff,13,0x3f800000,0x40000000,0x40400000,0,123,456,0 if variant==3 else 1]
  if variant==3:widths += [1,1];values += [1,0]
  bits+=fields(mode,widths,values);header_end=len(bits)
  index=0 if variant in(6,8,13,14) else 5 if variant==7 else 10240 if variant==9 else 17
  bits+=fields(mode,[-1],[index])
  if variant==5:bits+=fields(mode,[1],[0])
  elif variant in(6,7,13,14):bits+=fields(mode,[1,1],[1,1])
  else:
   output=(C.c_uint8*32768)();length=C.c_uint32();lib.original_create(scenario,mode,output,C.byref(length))
   bits += [(output[i//8]>>(i%8))&1 for i in range(length.value)]
  create_end=len(bits)
  if variant!=1:bits+=fields(mode,[32,32],[0xdeadbeef,0x11223344])
  raw=bytearray((len(bits)+7)//8)
  for i,bit in enumerate(bits):raw[i//8]|=bit<<(i%8)
  # The original writer masks high bits. These two deliberate malformed-byte
  # controls mutate its valid sentinel output; no original producer claim.
  if variant in(13,14):raw[header_end//8+4+(variant==14)]=2
  selected=4243 if variant in(10,11) else 4242
  status=1 if variant in(1,2,7,8,13,14) else 4 if variant==9 else 7 if variant in(10,11) else 2
  stage=2 if variant in(2,3,4) else 3 if variant in(8,9) else 4 if variant in(5,10,11,13,14) else 6 if variant in(6,7) else 5
  validated=int(variant in(0,1,12));header=int(variant not in(2,3,4))
  expected_self=int(scenario in(0,1) and validated)
  row=(len(raw),len(bits),post,header_end,create_end,mode,variant,scenario,index,selected,status,stage,validated,header,expected_self)
  rows.append((row,raw));metadata.append({'mode':mode,'start_bit':start,'scenario':scenario,'variant':variant,'sha256':sha(raw)})
 for mode in(0,1):
  for start in(range(8) if not mode else(0,8)):
   for scenario in range(7):build(mode,start,scenario,0)
  for variant in range(1,15 if mode else 13):build(mode,0,6 if variant==11 else 0,variant)
 path=work/'fixtures.bin'
 with path.open('xb')as stream:
  stream.write(struct.pack('<I',len(rows)))
  for row,raw in rows:stream.write(struct.pack('<15I',*row));stream.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'packed_start_offsets':list(range(8)),'byte_aligned_start_offsets':[0,8],'original_create_scenarios':7,'synthetic_control_variants':14,'case_manifest_sha256':sha(json.dumps(metadata,sort_keys=True).encode())}

def main():
 if not __debug__:raise ValueError('Python assertions required')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args();root=args.source_root.resolve()
 if args.output.exists():raise ValueError('fresh evidence output required')
 engine=root/'native-android/engine';entities=engine/'entities'
 helper=module('first_create_original_components',entities/'check.py')
 sources=[HERE/'coh_initial_create_probe.c',engine/'replication/coh_replication.c',entities/'coh_entities.c']
 inputs=set(sources+[HERE/'coh_initial_create_probe.h',HERE/'test_initial_create_probe.c',Path(__file__),entities/'check.py',entities/'source-pins.json',entities/'oracle_shim.h',entities/'stats_oracle_shim.h',entities/'rare_fixture.c.inc',root/'native-android/tools/protocol_fixture/prepare.py'])
 inputs.update(root/'upstream/ouroboros'/name for name in helper.FILES)
 for source in sources+[HERE/'test_initial_create_probe.c']:
  dependencies=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1]
  inputs.update(Path(name).resolve()for name in shlex.split(dependencies))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]
 if args.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-first-create-')as temporary:
  work=Path(temporary);lib,pins,names,_,_=helper.oracle(root,work);verify();wire,proof=fixtures(lib,work)
  for mode,flags in modes:
   executable=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_create_probe.c','-lm','-o',executable]);checks[mode]=json.loads(run([executable,wire],env=env));binaries[mode]=sha(executable.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('qualification modes differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_create_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('unbounded probe stack')
  original={'executed_entrypoints':['original_create','original_fields'],'entSendCreate_sha256_lf':sha(helper.extract(helper.source_text(root,'MapServer/src/entity/entsend.c'),'entSendCreate').encode()),'source_pin_manifest_sha256':sha((entities/'source-pins.json').read_bytes()),'all_original_source_pins_verified':True,'generated_original_oracle_sha256':sha((work/'source-oracle.c').read_bytes()),'oracle_sanitized':False}
 verify();args.output.parent.mkdir(parents=True,exist_ok=True)
 result={'schema':'coh-first-create-probe-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if 'upstream/ouroboros'not in str(path)},'original_components':original,'fixtures':proof,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'fixture_join':'Synthetic header/index framing plus complete unchanged original entSendCreate output; no complete sendEntity or entSendUpdate execution.','raw_packet_body_retained_in_evidence':False,'whole_original_allents_producer_executed':False,'actual_server_transaction':False,'physical_device_executed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['count']}))
if __name__=='__main__':main()

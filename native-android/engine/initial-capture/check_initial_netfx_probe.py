#!/usr/bin/env python3
"""Focused original NetFX producer/consumer and bounded diagnostic envelope."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise RuntimeError(repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def bitlist(raw,begin,end):return[(raw[i//8]>>(i%8))&1 for i in range(begin,end)]
def packed_bytes(bits):
 raw=bytearray((len(bits)+7)//8)
 for i,value in enumerate(bits):raw[i//8]|=value<<(i%8)
 return raw
def retained_ai(root):
 directory=HERE/'qualification/initial-aianim-20261019';host=json.loads((directory/'host.json').read_text());header=(directory/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('retained AI header changed')
 for name,expected in host['source_sha256'].items():
  if sha((root/name).read_bytes())!=expected:raise ValueError('retained AI input changed: '+name)
 raw=bytes(map(int,re.search(r'coh_aianim_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')))
 if sha(raw)!=proof['payload_sha256']:raise ValueError('retained AI payload changed')
 constants={name:int(value)for name,value in re.findall(r'#define COH_AIANIM_JNI_FIXTURE_(\w+) (\d+)u',header)}
 for name,key in [('AI_END','ai_end_bit'),('TRIGGERED_END','triggered_end_bit'),('SEQUENCE_END','sequence_end_bit'),('POSE_END','pose_end_bit'),('CREATE_END','create_end_bit'),('POST_COMMAND','post_command_bit')]:
  if constants[name]!=proof[key]:raise ValueError('retained AI boundaries changed: '+name)
 return raw,constants,{'host_sha256':sha((directory/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'verified_source_inputs':len(host['source_sha256']),'accepted_prefix_end':constants['AI_END'],'old_AI_or_earlier_ranges_reexecuted':False}
def fixtures(lib,work,retained,fixture_output):
 rows=[];manifest=[];source_cases={};consumer_checks=0
 lib.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_int,C.c_void_p,C.c_void_p]
 lib.original_netfx.argtypes=[C.c_int,C.c_int,C.c_void_p,C.c_void_p]
 lib.original_receive_netfx.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_void_p,C.c_void_p]
 def fields(mode,seq):
  raw=(C.c_ubyte*32768)();bits=C.c_uint();lib.original_fields((C.c_int*len(seq))(*(item[0]for item in seq)),(C.c_uint*len(seq))(*(item[1]for item in seq)),len(seq),mode,raw,C.byref(bits));return bitlist(raw,0,bits.value)
 def original(mode,scenario):
  nonlocal consumer_checks
  if(mode,scenario)not in source_cases:
   raw=(C.c_ubyte*32768)();bits=C.c_uint();lib.original_netfx(scenario,mode,raw,C.byref(bits));values=(C.c_uint*(1+32*17))();positions=(C.c_float*(32*8))();lib.original_receive_netfx(raw,bits.value,mode,values,positions)
   expected=[3,2,0][scenario]
   if values[0]!=expected:raise ValueError('whole original producer/consumer count differs')
   source_cases[(mode,scenario)]=(bitlist(raw,0,bits.value),expected,{'mode':mode,'scenario':scenario,'bits':bits.value,'payload_sha256':sha(bytes(raw[:(bits.value+7)//8])),'count':expected,'original_consumer_projection_sha256':sha(bytes(values)+bytes(positions))});consumer_checks+=1
  return source_cases[(mode,scenario)]
 def minimal(variant=0,index=0):
  # Explicit original-writer controls, not a complete original effect producer.
  command=4 if variant==14 else 0 if variant==5 else 1;ident=0 if variant==6 else 0xffffffff if variant==16 else 500+index
  seq=[(2,command),(32,ident),(1,2 if variant==13 else 0),(1,0)]
  seq +=[(1,1),(-12,0xffffffff)]if variant==16 else[(1,0)]
  seq +=[(1,0)] # no tint
  seq +=[(1,1),(-4,0x80000000)]if variant==12 else[(1,0)]
  seq +=[(1,0)] # no trigger
  seq +=[(1,1),(32,0x7fc00000)]if variant==7 else[(1,0)]
  seq +=[(1,0),(1,0),(1,0)] # radius, power, debris absent
  if variant in(8,11):seq +=[(1,1),(2,3 if variant==8 else 1)]
  else:seq +=[(1,0)]
  if variant==11:seq +=[(32,0x7f800000),(32,0),(32,0)]
  else:
   seq +=[(1,1),(-8,10239)]if variant==16 else[(1,0)]
   seq +=[(-2,256 if variant==9 else 255 if variant==16 else 0)]
  seq +=[(1,0)] # entity target
  seq +=[(1,1),(-12,10240 if variant==10 else 10239)]if variant in(10,16)else[(1,0)]
  return seq
 def append(mode,start,scenario=0,pchar=1,phase=1,variant=0,prefix=None):
  bits=[i&1 for i in range(start)];expected_pchar=pchar;expected_phase=phase
  bits+=fields(mode,[(1,2 if variant==2 else pchar),(1,2 if variant==3 else phase)]);flags_end=len(bits)
  body=bool(pchar and phase);count=0;child=0;status=2;stage=4;valid=1
  if body:
   if variant in(0,1):body_bits,count,_=original(mode,scenario)
   elif variant==4:body_bits=fields(mode,[(-1,33)]);child=status=4;valid=0;stage=3
   elif variant==15:count=32;body_bits=fields(mode,[(-1,32)]+sum((minimal(index=i)for i in range(32)),[]))
   else:
    count=1;body_bits=fields(mode,[(-1,1)]+minimal(variant))
    if variant!=16:child=status=4 if variant in(8,9,10,12)else 1;valid=0;stage=3
   bits+=body_bits
  end=len(bits)
  if variant!=1:bits+=fields(mode,[(1,1),(32,0xdeadbeef)])
  else:status=1
  # Original writers mask narrow values. Malformed rounded-byte controls are
  # explicit post-generation mutations, never original-producer assertions.
  if variant in(2,3):
   at=start+(8 if variant==3 else 0);bits[at:at+8]=fields(mode,[(8,2)])
  elif variant==13:
   at=flags_end+32+8+32;bits[at:at+8]=fields(mode,[(8,2)])
  elif variant==14:
   at=flags_end+32;bits[at:at+8]=fields(mode,[(8,4)])
  if variant==2:status=1;stage=2;valid=0;expected_pchar=0;expected_phase=0;body=False;flags_end=0;count=0;child=0
  elif variant==3:status=1;stage=2;valid=0;expected_phase=0;body=False;flags_end=0;count=0;child=0
  if not valid:count=0
  if prefix is not None:
   old_start=start;delta=len(prefix)-start;bits=prefix+bits[start:];start+=delta;flags_end+=delta;end+=delta
  raw=packed_bytes(bits);row=(len(raw),len(bits),mode,variant,scenario,start,flags_end,end,status,stage,expected_pchar,expected_phase,int(body),count,valid,child,0)
  rows.append((row,raw));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'pchar':pchar,'in_phase':phase,'sha256':sha(raw)})
  return row,raw
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(3):append(mode,start,scenario)
   for pchar,phase in((0,0),(0,1),(1,0)):append(mode,start,pchar=pchar,phase=phase)
  for variant in(1,4,5,6,7,8,9,10,11,12,15,16):append(mode,0,variant=variant)
  for pchar,phase in((0,0),(0,1),(1,0)):append(mode,0,pchar=pchar,phase=phase,variant=1)
  if mode:
   for variant in(2,3,13,14):append(mode,0,variant=variant)
 raw,constants,_=retained;prefix=bitlist(raw,0,constants['AI_END']);row,jni=append(0,constants['AI_END']%8,prefix=prefix)
 jni_proof={'payload_bits':row[1],'payload_sha256':sha(jni),'post_command_bit':constants['POST_COMMAND'],'create_end_bit':constants['CREATE_END'],'pose_end_bit':constants['POSE_END'],'sequence_end_bit':constants['SEQUENCE_END'],'triggered_end_bit':constants['TRIGGERED_END'],'ai_end_bit':constants['AI_END'],'netfx_end_bit':row[7],'effect_count':3,'device_packet':False}
 if fixture_output:
  header='/* SOURCE-GENERATED FIXTURE: retained AI prefix, synthetic two-flag framing, whole original full-send NetFX leaf, and opaque costume witness. Never physical packet data. */\nstatic const unsigned char coh_netfx_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_NETFX_JNI_FIXTURE_'+name+' '+str(value)+'u\n'for name,value in[('BITS',row[1]),('POST_COMMAND',constants['POST_COMMAND']),('CREATE_END',constants['CREATE_END']),('POSE_END',constants['POSE_END']),('SEQUENCE_END',constants['SEQUENCE_END']),('TRIGGERED_END',constants['TRIGGERED_END']),('AI_END',constants['AI_END']),('NETFX_END',row[7])]);fixture_output.parent.mkdir(parents=True,exist_ok=True);fixture_output.write_text(header);jni_proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as stream:
  stream.write(struct.pack('<I',len(rows)))
  for row,raw in rows:stream.write(struct.pack('<17I',*row));stream.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'original_producer_consumer_comparisons':consumer_checks,'source_leaf_cases':[value[2]for value in source_cases.values()],'outer_flag_combinations':[[0,0],[0,1],[1,0],[1,1]],'packed_start_offsets':list(range(8)),'byte_aligned_start_offsets':[0,8],'synthetic_native_count_controls':[32,33],'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())},jni_proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture-output',type=Path);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args();root=args.source_root.resolve()
 if args.output.exists():raise ValueError('fresh evidence output required')
 engine=root/'native-android/engine';entities=engine/'entities';base=module('initial_netfx_original_components',entities/'check.py');retained=retained_ai(root)
 sources=[HERE/'coh_initial_netfx_probe.c',engine/'replication/coh_replication.c',entities/'coh_entities.c'];inputs=set(sources+[HERE/'coh_initial_netfx_probe.h',HERE/'test_initial_netfx_probe.c',Path(__file__),entities/'check.py',entities/'source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-aianim-20261019/host.json',HERE/'qualification/initial-aianim-20261019/jni-fixture.h'])
 inputs.update(path for path in entities.iterdir()if path.suffix in('.h','.inc'));inputs.update(root/'upstream/ouroboros'/name for name in base.FILES)
 for source in sources+[HERE/'test_initial_netfx_probe.c']:
  dependencies=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(name).resolve()for name in shlex.split(dependencies))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]
 if args.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-initial-netfx-')as temporary:
  work=Path(temporary);lib,pins,names,_,_=base.oracle(root,work);verify();wire,proof,jni=fixtures(lib,work,retained,args.fixture_output)
  for mode,flags in modes:
   executable=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_netfx_probe.c','-lm','-o',executable]);checks[mode]=json.loads(run([executable,wire],env=env));binaries[mode]=sha(executable.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('qualification modes differ')
  stack=[];child_stack=[]
  child_names={'coh_ent_netfx','check_reader','netfx','stage','require','read_n','pack','scalar','flag','opt_bits','opt_pack','optional_float32','float32','fail','clear_failure'}
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');name=location.rsplit(':',1)[-1];record={'function':name,'bytes':int(size),'bound':bound}
    if 'coh_initial_netfx_probe.c:'in location:stack.append(record)
    elif('coh_entities.c:'in location and name in child_names)or('coh_replication.c:'in location and name in{'valid','coh_rep_read','coh_rep_pack'}):child_stack.append(record)
  if not stack or not child_stack or any(row['bound']not in('static','dynamic,bounded')for row in stack+child_stack):raise ValueError('unbounded native stack')
  stack_upper=sum(row['bytes']for row in stack+child_stack)
  if stack_upper>16384:raise ValueError('native envelope/child frame bound exceeded')
  original={'executed_entrypoints':['original_netfx','original_receive_netfx','original_fields'],'whole_producer_sha256_lf':sha(base.extract(base.source_text(root,'MapServer/src/entity/entsend.c'),'entSendNetFx').encode()),'whole_consumer_sha256_lf':sha(base.extract(base.source_text(root,'Game/src/entity/entrecv.c'),'entReceiveNetFx').encode()),'source_pin_manifest_sha256':sha((entities/'source-pins.json').read_bytes()),'all_original_source_pins_verified':True,'generated_original_oracle_sha256':sha((work/'source-oracle.c').read_bytes()),'original_dynamic_effect_array':True,'native_effect_count_limit':32,'source_MAX_NETFX_30_is_commented_out':True,'oracle_sanitized':False}
 verify();args.output.parent.mkdir(parents=True,exist_ok=True)
 result={'schema':'coh-initial-netfx-probe-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if 'upstream/ouroboros'not in str(path)},'original_component':original,'retained_ai_prefix':retained[2],'fixtures':proof,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'child_native_stack_frames':child_stack,'conservative_sum_native_envelope_and_child_frames':stack_upper,'external_libc_stack_measured':False,'source_stable_before_after':True,'fixture_join':'Synthetic two-flag envelope and immutable scalar-bit relocation of complete original NetFX leaves; JNI fixture reuses hashed qualified AI prefix plus an opaque costume witness. Original enclosing sendEntity/entSendUpdate not executed.','physical_packet_body_retained_in_evidence':False,'costume_produced_or_parsed':False,'old_AI_or_earlier_ranges_reexecuted':False,'whole_original_allents_producer_executed':False,'actual_server_transaction':False,'physical_device_executed':False,'cross_prefix_in_phase_verified':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['count'],'jni':jni,'native_stack_frame_sum':stack_upper}))
if __name__=='__main__':main()

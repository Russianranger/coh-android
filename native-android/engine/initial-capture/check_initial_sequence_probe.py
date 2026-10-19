#!/usr/bin/env python3
"""Focused original sequence-leaf qualification; no triggered-move parsing."""
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
class Writer:
 def __init__(self,aligned,start=0):self.aligned=aligned;self.bits=[i&1 for i in range(start)]
 def scalar(self,width,value):
  width=(width+7)&~7 if self.aligned else width;self.bits +=[(value>>i)&1 for i in range(width)]
 def pack(self,width,value):
  if self.aligned:self.scalar(32,value);return
  while width<32 and value>=(1<<width)-1:self.scalar(width,(1<<width)-1);value-=(1<<width)-1;width=min(32,width*2)
  self.scalar(width,value)
 def optional(self,width,value,packed=False,present=None):
  present=bool(value)if present is None else present;self.scalar(1,present)
  if present:(self.pack if packed else self.scalar)(width,value)

LEGAL_WRAPPER=r'''
/* Value255 is representable by the original Entity's U8 timer. The fixture
 * shell itself remains explicitly synthetic and does not qualify Win32 ABI. */
void sequence_legal255(unsigned aligned,unsigned prefix,U8*out,unsigned*bits,unsigned*begin,unsigned*end){
 U32 memory[16384]={0};Packet p={0};LeafSeqCharacter ch={0};LeafSequence seq={0};LeafSeqEntity e={&ch,&seq,33,255};
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);
 for(unsigned k=0;k<prefix;k++)bsWriteBits(&p.stream,1,k&1);
 p.stream.byteAlignedMode=aligned;*begin=bsGetCursorBitPosition(&p.stream);leaf_seq_count=0;
 entSendSeqMoveUpdate(&p,&e,1);assert(!p.stream.errorFlags);*end=*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
}
'''

def retained_pose(root):
 directory=HERE/'qualification/initial-pose-20261019';host=json.loads((directory/'host.json').read_text());header=(directory/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('retained pose fixture header changed')
 for name,expected in host['source_sha256'].items():
  if sha((root/name).read_bytes())!=expected:raise ValueError('retained pose input changed: '+name)
 raw=bytes(map(int,re.search(r'coh_pose_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')))
 if sha(raw)!=proof['payload_sha256']:raise ValueError('retained pose payload changed')
 constants={name:int(value)for name,value in re.findall(r'#define COH_POSE_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if constants['POSE_END']!=proof['pose_end_bit']or constants['CREATE_END']!=proof['create_end_bit']or constants['POST_COMMAND']!=proof['post_command_bit']:raise ValueError('retained pose boundaries changed')
 return raw,constants,{'host_sha256':sha((directory/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'verified_source_inputs':len(host['source_sha256']),'accepted_prefix_end':constants['POSE_END'],'old_pose_range_reexecuted':False}

def fixtures(lib,work,pose,fixture_output):
 rows=[];manifest=[];source_checks=0
 def source(mode,start,scenario):
  raw=(C.c_uint8*65536)();bits=C.c_uint();begin=C.c_uint();end=C.c_uint();seed=0 if mode else start
  if scenario==4:lib.sequence_legal255(mode,seed,raw,C.byref(bits),C.byref(begin),C.byref(end))
  else:lib.original_record_leaf(3,scenario,mode,seed,raw,C.byref(bits),C.byref(begin),C.byref(end))
  values=bitlist(raw,begin.value,end.value)
  return [i&1 for i in range(start)]+values
 def projection(mode,start,scenario,variant):
  writer=Writer(mode,start);updated=scenario!=1;writer.scalar(1,updated)
  index=(33,0,0,0x7fffffff,33)[scenario];ticks=(4,0,0,65535,255)[scenario];movement=1248 if scenario==2 else 0
  if variant==2:index=0x80000000
  if variant==3:ticks=65536
  if variant==4:movement=2047
  if variant==9:index=ticks=movement=0
  if variant==10:index=0x7fffffff;ticks=65535;movement=2047
  index_present=int(bool(index)or variant==9);ticks_present=int(bool(ticks)or variant==9);movement_present=int(bool(movement)or variant==9)
  if updated:
   writer.optional(8,index,True,index_present);index_end=len(writer.bits);writer.optional(4,ticks,True,ticks_present);ticks_end=len(writer.bits);writer.optional(11,movement,False,movement_present)
  else:index_end=ticks_end=0;index_present=ticks_present=movement_present=0
  return writer.bits,index_end,ticks_end,index_present,ticks_present,movement_present
 def append_row(mode,start,scenario,variant,full_prefix=None):
  nonlocal source_checks
  projected,index_end,ticks_end,ip,tp,mp=projection(mode,start,scenario,variant)
  if not variant or variant==1:
   original=source(mode,start,scenario)
   if original!=projected:raise ValueError('original sequence differs from independent wire projection')
   source_checks+=1;bits=original
  else:bits=projected
  sequence_end=len(bits)
  if variant!=1:
   witness=Writer(mode);witness.scalar(1,1);witness.scalar(32,0xdeadbeef);bits+=witness.bits
  raw=packed_bytes(bits)
  # Original writer masks unused high bits; these are explicitly malformed
  # rounded-byte controls, never original-server-produced bodies.
  if variant==4:raw[ticks_end//8+1]=0;raw[ticks_end//8+2]=8
  elif variant==5:raw[start//8]=2
  elif variant==6:raw[start//8+1]=2
  elif variant==7:raw[index_end//8]=2
  elif variant==8:raw[ticks_end//8]=2
  stage=3 if variant in(2,6)else 4 if variant in(3,7)else 5 if variant in(4,8)else 2 if variant==5 or scenario==1 else 6
  status=4 if variant in(2,3)else 1 if variant in(1,4,5,6,7,8)else 2
  update=int(stage>2);flags=[update,ip if stage>=3 else 0,tp if stage>=4 else 0,mp if stage>=5 else 0]
  if variant==6:flags[1]=0
  if variant==7:flags[2]=0
  if variant==8:flags[3]=0
  if full_prefix is not None:
   prefix,old_start=full_prefix;delta=len(prefix)-old_start;raw=packed_bytes(prefix+bitlist(raw,old_start,len(bits)));start+=delta;index_end+=delta;ticks_end+=delta;sequence_end+=delta;bits=[0]*(len(prefix)+len(bits)-old_start)
  row=(len(raw),len(bits),mode,variant,scenario,start,index_end,ticks_end,sequence_end,status,stage,*flags,int(stage==6));rows.append((row,raw));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'sha256':sha(raw)})
  return row,raw
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(5):append_row(mode,start,scenario,0)
  for variant in(1,2,3,9,10):append_row(mode,0,0,variant)
  if mode:
   for variant in(4,5,6,7,8):append_row(mode,0,0,variant)
 raw,constants,_=pose;prefix=bitlist(raw,0,constants['POSE_END']);row,jni=append_row(0,constants['POSE_END']%8,0,0,(prefix,constants['POSE_END']%8))
 jni_proof={'payload_bits':row[1],'payload_sha256':sha(jni),'post_command_bit':constants['POST_COMMAND'],'create_end_bit':constants['CREATE_END'],'pose_end_bit':constants['POSE_END'],'sequence_end_bit':row[8],'device_packet':False}
 if fixture_output:
  header='/* SOURCE-GENERATED FIXTURE: retained qualified create/pose prefix plus exact original sequence leaf and synthetic trigger witness. Never device packet data. */\nstatic const unsigned char coh_sequence_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_SEQUENCE_JNI_FIXTURE_'+name+' '+str(value)+'u\n'for name,value in [('BITS',row[1]),('POST_COMMAND',constants['POST_COMMAND']),('CREATE_END',constants['CREATE_END']),('POSE_END',constants['POSE_END']),('SEQUENCE_END',row[8])]);fixture_output.parent.mkdir(parents=True,exist_ok=True);fixture_output.write_text(header);jni_proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as stream:
  stream.write(struct.pack('<I',len(rows)))
  for row,raw in rows:stream.write(struct.pack('<16I',*row));stream.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'original_sequence_projection_checks':source_checks,'packed_start_offsets':list(range(8)),'byte_aligned_start_offsets':[0,8],'source_leaf_scenarios':[0,1,2,3],'added_source_value_legal_ticks255_scenario':4,'synthetic_control_variants':10,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())},jni_proof

def main():
 if not __debug__:raise ValueError('Python assertions required')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture-output',type=Path);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args();root=args.source_root.resolve()
 if args.output.exists():raise ValueError('fresh evidence output required')
 engine=root/'native-android/engine';entities=engine/'entities';provider=root/'native-android/combined-client/diagnostics/selected-record-order-20261017';leaf=module('initial_sequence_original_leaf',provider/'leaf_oracle.py');base=module('initial_sequence_base',entities/'check.py');pose=retained_pose(root)
 retained=json.loads((provider/'host-leaf-proof.json').read_text());sources=[HERE/'coh_initial_sequence_probe.c',engine/'replication/coh_replication.c']
 inputs=set(sources+[HERE/'coh_initial_sequence_probe.h',HERE/'test_initial_sequence_probe.c',Path(__file__),entities/'check.py',entities/'source-pins.json',entities/'oracle_shim.h',entities/'stats_oracle_shim.h',entities/'rare_fixture.c.inc',root/'native-android/tools/protocol_fixture/prepare.py',provider/'leaf_oracle.py',provider/'leaf_wrapper.h',provider/'leaf_adapters.h',provider/'leaf-source-pins.json',provider/'host-leaf-proof.json',HERE/'qualification/initial-pose-20261019/host.json',HERE/'qualification/initial-pose-20261019/jni-fixture.h'])
 for name in('leaf_oracle.py','leaf_wrapper.h','leaf_adapters.h','leaf-source-pins.json'):
  path=provider/name
  if sha(path.read_bytes())!=retained['source_sha256'][str(path.relative_to(root))]:raise ValueError('retained original leaf provider changed: '+name)
 original_names=set(base.FILES)|set(json.loads((provider/'leaf-source-pins.json').read_text())['additional_full_sources_sha256_lf']);inputs.update(root/'upstream/ouroboros'/name for name in original_names)
 for source in sources+[HERE/'test_initial_sequence_probe.c']:
  dependencies=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(name).resolve()for name in shlex.split(dependencies))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]
 if args.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-initial-sequence-')as temporary:
  work=Path(temporary);_,source_proof=leaf.build(root,work);verify();original=source_proof['whole_functions_sha256_lf']['MapServer/src/entity/entsend.c:entSendSeqMoveUpdate']
  if original!=retained['source_proof']['whole_functions_sha256_lf']['MapServer/src/entity/entsend.c:entSendSeqMoveUpdate']:raise ValueError('original sequence function differs from retained qualification')
  source=work/'sequence-original.c';source.write_text((work/'leaf-source.c').read_text()+LEGAL_WRAPPER);oracle=work/'sequence-original.so';run(['cc','-std=gnu99','-O0','-fwrapv','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(entities),source,'-lz','-lm','-o',oracle]);lib=C.CDLL(str(oracle));lib.original_record_leaf.argtypes=[C.c_uint]*4+[C.c_void_p]*4;lib.sequence_legal255.argtypes=[C.c_uint]*2+[C.c_void_p]*4;wire,proof,jni=fixtures(lib,work,pose,args.fixture_output)
  for mode,flags in modes:
   executable=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_sequence_probe.c','-lm','-o',executable]);checks[mode]=json.loads(run([executable,wire],env=env));binaries[mode]=sha(executable.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('qualification modes differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_sequence_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('unbounded probe stack')
  original_proof={'executed_component_producer':'entSendSeqMoveUpdate','executed_provider_kinds':[3],'whole_function_sha256_lf':original,'constant_definitions_sha256':source_proof['exact_constant_definitions_sha256'],'source_pin_manifest_sha256':sha((provider/'leaf-source-pins.json').read_bytes()),'retained_leaf_host_proof_sha256':sha((provider/'host-leaf-proof.json').read_bytes()),'all_original_source_pins_verified':True,'generated_original_oracle_sha256':sha(source.read_bytes()),'legal255_wrapper_sha256':sha(LEGAL_WRAPPER.encode()),'scenario3_scope':'Consumer U16-range shell extreme65535; original Entity timer is U8, so this is not representable actual server entity state.','scenario4_scope':'Complete unchanged original producer with timer255, representable by the original U8 field; explicit fixture shell, not Win32 ABI or real session.','stance_branch_executed':False,'oracle_sanitized':False,'original_consumer_executed':False}
 verify();args.output.parent.mkdir(parents=True,exist_ok=True)
 result={'schema':'coh-initial-sequence-probe-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if 'upstream/ouroboros'not in str(path)},'original_component':original_proof,'retained_pose_prefix':pose[2],'fixtures':proof,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'fixture_join':'Exact original sequence leaves plus explicit synthetic outer offsets and opaque triggered-move witness. JNI fixture reuses hashed qualified pose prefix, with matching bit alignment.','physical_packet_body_retained_in_evidence':False,'triggered_moves_produced_or_parsed':False,'old_pose_range_reexecuted':False,'whole_original_allents_producer_executed':False,'actual_server_transaction':False,'physical_device_executed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['count'],'jni':jni}))
if __name__=='__main__':main()

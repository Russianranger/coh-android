#!/usr/bin/env python3
"""Focused complete original triggered-move producer and bounded native probe."""
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

WRAPPER=r'''
/* Explicit fixture entities, never a live server or full original record.
 * The complete unchanged entSendSeqTriggeredMoves above executes below. */
void triggered_original(unsigned aligned,unsigned prefix,unsigned scenario,U8*out,unsigned*bits,unsigned*begin,unsigned*end){
 assert(aligned<=1&&prefix<8&&(!aligned||!prefix)&&scenario<=10);
 U32 memory[16384]={0};Packet p={0};Entity e={0};
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);
 for(unsigned k=0;k<prefix;k++)bsWriteBits(&p.stream,1,k&1);
 p.stream.byteAlignedMode=aligned;*begin=bsGetCursorBitPosition(&p.stream);
 e.lastTimeEntSent=10;e.triggered_move_count=scenario==0?0:scenario==2?16:scenario==10?2:1;e.set_triggered_moves=scenario==3;
 for(int i=0;i<e.triggered_move_count;i++){
  TriggeredMove*tm=&e.triggered_moves[i];tm->idx=42+i;tm->ticksToDelay=6+i;tm->triggerFxNetId=1000;tm->timeCreated=10;
  if(scenario==2){tm->triggerFxNetId=i%2?1000+i:0;tm->timeCreated=20;}
  if(scenario==4){tm->triggerFxNetId=0;tm->timeCreated=5;}
  if(scenario==5){tm->triggerFxNetId=0;tm->timeCreated=16.75f;}
  if(scenario==6){tm->triggerFxNetId=0;tm->timeCreated=80;}
  if(scenario==7){tm->triggerFxNetId=1000;tm->timeCreated=80;}
  if(scenario==8){tm->idx=INT32_MAX;tm->ticksToDelay=2147483520;tm->triggerFxNetId=0;}
  if(scenario==9){tm->idx=0;tm->ticksToDelay=0;tm->triggerFxNetId=0;}
  if(scenario==10){tm->triggerFxNetId=i?65536:0;tm->timeCreated=i?80:10;}
 }
 entSendSeqTriggeredMoves(&p,&e);assert(!p.stream.errorFlags);*end=*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
}
'''

def retained_sequence(root):
 directory=HERE/'qualification/initial-sequence-20261019';host=json.loads((directory/'host.json').read_text());header=(directory/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('retained sequence fixture header changed')
 for name,expected in host['source_sha256'].items():
  if sha((root/name).read_bytes())!=expected:raise ValueError('retained sequence input changed: '+name)
 raw=bytes(map(int,re.search(r'coh_sequence_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')))
 if sha(raw)!=proof['payload_sha256']:raise ValueError('retained sequence payload changed')
 constants={name:int(value)for name,value in re.findall(r'#define COH_SEQUENCE_JNI_FIXTURE_(\w+) (\d+)u',header)}
 for name,key in [('SEQUENCE_END','sequence_end_bit'),('POSE_END','pose_end_bit'),('CREATE_END','create_end_bit'),('POST_COMMAND','post_command_bit')]:
  if constants[name]!=proof[key]:raise ValueError('retained sequence boundaries changed')
 return raw,constants,{'host_sha256':sha((directory/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'verified_source_inputs':len(host['source_sha256']),'accepted_prefix_end':constants['SEQUENCE_END'],'old_sequence_or_pose_ranges_reexecuted':False}

def fixtures(lib,work,retained,fixture_output):
 rows=[];manifest=[];source_checks=0
 def expected(scenario):
  if scenario in(0,3):return[]
  entries=[]
  for i in range(16 if scenario==2 else 2 if scenario==10 else 1):
   index=42+i;ticks=6+i;fx=1000
   if scenario==2:fx=1000+i if i%2 else 0;ticks+=0 if fx else 10
   elif scenario==4:fx=0
   elif scenario==5:fx=0;ticks=12
   elif scenario==6:fx=0;ticks=21
   elif scenario==8:index=0x7fffffff;ticks=2147483520;fx=0
   elif scenario==9:index=ticks=fx=0
   elif scenario==10:fx=65536 if i else 0
   entries.append((index,ticks,fx))
  return entries
 def original(mode,start,scenario):
  raw=(C.c_uint8*65536)();bits=C.c_uint();begin=C.c_uint();end=C.c_uint();lib.triggered_original(mode,0 if mode else start,scenario,raw,C.byref(bits),C.byref(begin),C.byref(end));return[i&1 for i in range(start)]+bitlist(raw,begin.value,end.value)
 def append_row(mode,start,scenario,variant,full_prefix=None):
  nonlocal source_checks
  entries=expected(scenario);count=len(entries)
  if variant in(2,10):count=17 if variant==2 else 0xffffffff;entries=[]
  elif variant==3:entries=[(0x80000000,6,0)];count=1
  elif variant==4:entries=[(42,0x80000000,0)];count=1
  elif variant in(6,7,8):entries=[(42,6,1000 if variant in(6,8)else 0),(0x80000000 if variant==6 else 43,0x80000000 if variant==7 else 7,1000)];count=2
  elif variant==9:entries=[(0x7fffffff,0x7fffffff,0xffffffff)];count=1
  elif variant==13:entries=[];count=0
  writer=Writer(mode,start);writer.pack(1,count);count_end=len(writer.bits);fx_positions=[]
  for index,ticks,fx in entries:
   writer.pack(10,index);writer.pack(6,ticks);fx_positions.append(len(writer.bits));writer.scalar(1,bool(fx))
   if fx:writer.pack(16,fx)
  if not variant or variant in(1,13):
   produced=original(mode,start,0 if variant==13 else scenario)
   if produced!=writer.bits:raise ValueError('original triggered producer differs from independent wire projection')
   source_checks+=1;writer.bits=produced
  triggered_end=len(writer.bits)
  if variant not in(1,13):writer.scalar(1,1);writer.scalar(32,0xdeadbeef)
  raw=packed_bytes(writer.bits)
  if variant==5:raw[fx_positions[0]//8]=2
  elif variant==8:raw[fx_positions[1]//8]=2
  stage=2 if variant in(2,10)else 3 if variant in(3,6)else 4 if variant in(4,7)else 5 if variant in(5,8)else 6
  status=4 if variant in(2,3,4,6,7,10)else 1 if variant in(1,5,8,13)else 2
  complete_entries=count if stage==6 else 1 if variant in(6,7,8)else 0;current=count if stage==6 else 1 if variant in(6,7,8)else 0
  fx_count=sum(bool(entry[2])for entry in entries[:complete_entries])
  bits=len(writer.bits)
  if full_prefix is not None:
   prefix,old_start=full_prefix;delta=len(prefix)-old_start;raw=packed_bytes(prefix+bitlist(raw,old_start,bits));bits=len(prefix)+bits-old_start;start+=delta;count_end+=delta;triggered_end+=delta
  row=(len(raw),bits,mode,variant,scenario,start,count_end,triggered_end,status,stage,count,int(stage!=2),complete_entries,current,fx_count,int(stage==6));rows.append((row,raw));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'sha256':sha(raw)})
  return row,raw
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(11):append_row(mode,start,scenario,0)
  for variant in(1,2,3,4,6,7,9,10,13):append_row(mode,0,1,variant)
  if mode:
   for variant in(5,8):append_row(mode,0,1,variant)
 raw,constants,_=retained;prefix=bitlist(raw,0,constants['SEQUENCE_END']);row,jni=append_row(0,constants['SEQUENCE_END']%8,10,0,(prefix,constants['SEQUENCE_END']%8))
 jni_proof={'payload_bits':row[1],'payload_sha256':sha(jni),'post_command_bit':constants['POST_COMMAND'],'create_end_bit':constants['CREATE_END'],'pose_end_bit':constants['POSE_END'],'sequence_end_bit':constants['SEQUENCE_END'],'triggered_end_bit':row[7],'trigger_count':2,'fx_entries':1,'device_packet':False}
 if fixture_output:
  header='/* SOURCE-GENERATED FIXTURE: retained qualified initial prefix plus complete original triggered-move producer and synthetic AI witness. Never device packet data. */\nstatic const unsigned char coh_triggered_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_TRIGGERED_JNI_FIXTURE_'+name+' '+str(value)+'u\n'for name,value in [('BITS',row[1]),('POST_COMMAND',constants['POST_COMMAND']),('CREATE_END',constants['CREATE_END']),('POSE_END',constants['POSE_END']),('SEQUENCE_END',constants['SEQUENCE_END']),('TRIGGERED_END',row[7])]);fixture_output.parent.mkdir(parents=True,exist_ok=True);fixture_output.write_text(header);jni_proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as stream:
  stream.write(struct.pack('<I',len(rows)))
  for row,raw in rows:stream.write(struct.pack('<16I',*row));stream.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'original_triggered_projection_checks':source_checks,'packed_start_offsets':list(range(8)),'byte_aligned_start_offsets':[0,8],'source_scenarios':11,'source_counts':[0,1,2,16],'synthetic_count_overflow_controls':[17,0xffffffff],'source_high_safe_tick':2147483520,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())},jni_proof

def main():
 if not __debug__:raise ValueError('Python assertions required')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture-output',type=Path);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args();root=args.source_root.resolve()
 if args.output.exists():raise ValueError('fresh evidence output required')
 engine=root/'native-android/engine';entities=engine/'entities';base=module('initial_triggered_original_components',entities/'check.py');retained=retained_sequence(root)
 original_entity=(root/'upstream/ouroboros/Common/entity/entity.h').read_text();native_entity=(entities/'coh_entities.h').read_text();trigger_header=root/'upstream/ouroboros/Common/seq/TriggeredMove.h';trigger_text=trigger_header.read_text()
 if not re.search(r'#define\s+MAX_TRIGGEREDMOVES\s+20\b',original_entity)or not re.search(r'#define\s+COH_ENT_TRIGGER_MAX\s+16u\b',native_entity):raise ValueError('source/native trigger count limits changed')
 if any(not re.search(r'\bint\s+'+name+r'\s*;',trigger_text)for name in('ticksToDelay','triggerFxNetId','idx'))or not re.search(r'\bF32\s+timeCreated\s*;',trigger_text):raise ValueError('original triggered-move field domains changed')
 sources=[HERE/'coh_initial_triggered_probe.c',engine/'replication/coh_replication.c'];inputs=set(sources+[HERE/'coh_initial_triggered_probe.h',HERE/'test_initial_triggered_probe.c',Path(__file__),entities/'check.py',entities/'source-pins.json',entities/'oracle_shim.h',entities/'stats_oracle_shim.h',entities/'rare_fixture.c.inc',entities/'coh_entities.h',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-sequence-20261019/host.json',HERE/'qualification/initial-sequence-20261019/jni-fixture.h'])
 inputs.update(root/'upstream/ouroboros'/name for name in base.FILES);inputs.add(trigger_header)
 for source in sources+[HERE/'test_initial_triggered_probe.c']:
  dependencies=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(name).resolve()for name in shlex.split(dependencies))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]
 if args.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-initial-triggered-')as temporary:
  work=Path(temporary);base.oracle(root,work);verify();source=work/'triggered-original.c';source.write_text((work/'source-oracle.c').read_text()+WRAPPER);oracle=work/'triggered-original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(entities),source,'-lm','-o',oracle]);lib=C.CDLL(str(oracle));lib.triggered_original.argtypes=[C.c_uint]*3+[C.c_void_p]*4;wire,proof,jni=fixtures(lib,work,retained,args.fixture_output)
  for mode,flags in modes:
   executable=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_triggered_probe.c','-lm','-o',executable]);checks[mode]=json.loads(run([executable,wire],env=env));binaries[mode]=sha(executable.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('qualification modes differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_triggered_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('unbounded probe stack')
  original={'executed_component_producer':'entSendSeqTriggeredMoves','whole_function_sha256_lf':sha(base.extract(base.source_text(root,'MapServer/src/entity/entsend.c'),'entSendSeqTriggeredMoves').encode()),'source_pin_manifest_sha256':sha((entities/'source-pins.json').read_bytes()),'triggered_move_header_sha256':sha(trigger_header.read_bytes()),'triggered_move_field_domains_verified':True,'all_original_source_pins_verified':True,'generated_original_oracle_sha256':sha(source.read_bytes()),'wrapper_sha256':sha(WRAPPER.encode()),'source_count_max':20,'native_diagnostic_count_max':16,'fixture_shell_capacity':16,'packet_delay_source_cases':['negative difference clamps0','fractional6.75 then integer truncation','large difference clamps15','nonzero FX bypasses delay'],'high_tick_scope':'2147483520 is exactly representable in F32 below INT32 overflow; raw INT32_MAX endpoint tested synthetically.','original_consumer_executed':False,'oracle_sanitized':False}
 verify();args.output.parent.mkdir(parents=True,exist_ok=True)
 result={'schema':'coh-initial-triggered-probe-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if 'upstream/ouroboros'not in str(path)},'original_component':original,'retained_sequence_prefix':retained[2],'fixtures':proof,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'fixture_join':'Exact complete original triggered-move leaf with explicit fixture entity/offsets and opaque AI witness. JNI fixture reuses hashed qualified sequence prefix with matching bit alignment.','physical_packet_body_retained_in_evidence':False,'ai_animation_produced_or_parsed':False,'old_sequence_or_pose_ranges_reexecuted':False,'whole_original_allents_producer_executed':False,'actual_server_transaction':False,'physical_device_executed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['count'],'jni':jni}))
if __name__=='__main__':main()

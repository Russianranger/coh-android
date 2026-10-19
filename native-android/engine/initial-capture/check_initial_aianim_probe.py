#!/usr/bin/env python3
"""Focused original AI-animation leaf and bounded nonretaining native probe."""
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

WRAPPER=r'''
/* Exact complete original entSendAiAnimList above; synthetic fixture entity.
 * No native consumer, dictionary lookup or complete original record runs. */
void aianim_original(unsigned aligned,unsigned prefix,unsigned scenario,U8*out,unsigned*bits,unsigned*begin,unsigned*end){
 assert(aligned<=1&&prefix<8&&(!aligned||!prefix)&&scenario<8);
 U32 memory[16384]={0};Packet p={0};Entity e={0};char long_name[1001],high_bytes[]={-128,-1,'A',0};
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);
 for(unsigned k=0;k<prefix;k++)bsWriteBits(&p.stream,1,k&1);
 p.stream.byteAlignedMode=aligned;*begin=bsGetCursorBitPosition(&p.stream);
 e.aiAnimList=scenario==0?NULL:scenario==1?"":"FixtureAnim";e.aiAnimListUpdated=scenario==6;
 if(scenario==3||scenario==4){unsigned length=scenario==3?999:1000;memset(long_name,'A',length);long_name[length]=0;e.aiAnimList=long_name;}
 if(scenario==7)e.aiAnimList=high_bytes;
 entSendAiAnimList(&p,&e,scenario==5||scenario==6?0:1);assert(!p.stream.errorFlags);
 *end=*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
}
'''

def retained_triggered(root):
 directory=HERE/'qualification/initial-triggered-20261019';host=json.loads((directory/'host.json').read_text());header=(directory/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('retained triggered fixture header changed')
 for name,expected in host['source_sha256'].items():
  if sha((root/name).read_bytes())!=expected:raise ValueError('retained triggered input changed: '+name)
 raw=bytes(map(int,re.search(r'coh_triggered_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')))
 if sha(raw)!=proof['payload_sha256']:raise ValueError('retained triggered payload changed')
 constants={name:int(value)for name,value in re.findall(r'#define COH_TRIGGERED_JNI_FIXTURE_(\w+) (\d+)u',header)}
 for name,key in [('TRIGGERED_END','triggered_end_bit'),('SEQUENCE_END','sequence_end_bit'),('POSE_END','pose_end_bit'),('CREATE_END','create_end_bit'),('POST_COMMAND','post_command_bit')]:
  if constants[name]!=proof[key]:raise ValueError('retained triggered boundaries changed')
 return raw,constants,{'host_sha256':sha((directory/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'verified_source_inputs':len(host['source_sha256']),'accepted_prefix_end':constants['TRIGGERED_END'],'old_triggered_sequence_or_pose_ranges_reexecuted':False}

def fixtures(lib,work,retained,fixture_output):
 rows=[];manifest=[];source_checks=0
 def expected(mode,start,scenario,variant):
  writer=Writer(mode,start);update=scenario!=5;present=scenario not in(0,1);text=b'A'*999 if scenario==3 else b'A'*1000 if scenario==4 else bytes((128,255,65))if scenario==7 else b'FixtureAnim'
  if variant==5:present=1;text=b''
  writer.scalar(1,update)
  if update:
   writer.scalar(1,present)
   if present:
    for value in text+b'\0':writer.scalar(8,value)
  return writer.bits,int(update),int(update and present),len(text)if update and present else 0
 def original(mode,start,scenario):
  raw=(C.c_uint8*65536)();bits=C.c_uint();begin=C.c_uint();end=C.c_uint();lib.aianim_original(mode,0 if mode else start,scenario,raw,C.byref(bits),C.byref(begin),C.byref(end));return[i&1 for i in range(start)]+bitlist(raw,begin.value,end.value)
 def append_row(mode,start,scenario,variant,full_prefix=None):
  nonlocal source_checks
  bits,update,present,length=expected(mode,start,scenario,variant)
  if variant!=5:
   produced=original(mode,start,scenario)
   if produced!=bits:raise ValueError('original AI animation differs from independent wire projection')
   source_checks+=1;bits=produced
  if variant==4:bits=bits[:-8]
  ai_end=len(bits)
  if variant not in(1,4):witness=Writer(mode);witness.scalar(1,1);witness.scalar(32,0xdeadbeef);bits+=witness.bits
  raw=packed_bytes(bits)
  if variant==2:raw[start//8]=2;update=present=length=0
  elif variant==3:raw[start//8+1]=2;present=length=0
  stage=2 if variant==2 or scenario==5 else 3 if variant==3 else 4 if scenario==4 or variant==4 else 5
  status=4 if scenario==4 else 1 if variant in(1,2,3,4)else 2
  if scenario==4:length=1000
  if full_prefix is not None:
   prefix,old_start=full_prefix;delta=len(prefix)-old_start;raw=packed_bytes(prefix+bitlist(raw,old_start,len(bits)));start+=delta;ai_end+=delta;bits=[0]*(len(prefix)+len(bits)-old_start)
  row=(len(raw),len(bits),mode,variant,scenario,start,ai_end,status,stage,update,present,length,int(stage==5));rows.append((row,raw));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'sha256':sha(raw)})
  return row,raw
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(8):append_row(mode,start,scenario,0)
  for variant in(1,4,5):append_row(mode,0,2,variant)
  if mode:
   for variant in(2,3):append_row(mode,0,2,variant)
 raw,constants,_=retained;prefix=bitlist(raw,0,constants['TRIGGERED_END']);row,jni=append_row(0,constants['TRIGGERED_END']%8,2,0,(prefix,constants['TRIGGERED_END']%8))
 jni_proof={'payload_bits':row[1],'payload_sha256':sha(jni),'post_command_bit':constants['POST_COMMAND'],'create_end_bit':constants['CREATE_END'],'pose_end_bit':constants['POSE_END'],'sequence_end_bit':constants['SEQUENCE_END'],'triggered_end_bit':constants['TRIGGERED_END'],'ai_end_bit':row[6],'device_packet':False}
 if fixture_output:
  names=[('BITS',row[1])]+[(name,constants[name])for name in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END')]+[('AI_END',row[6])];header='/* SOURCE-GENERATED FIXTURE: retained qualified initial prefix plus complete original AI-animation producer and opaque NetFX witness. Never device packet data. */\nstatic const unsigned char coh_aianim_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_AIANIM_JNI_FIXTURE_'+name+' '+str(value)+'u\n'for name,value in names);fixture_output.parent.mkdir(parents=True,exist_ok=True);fixture_output.write_text(header);jni_proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as stream:
  stream.write(struct.pack('<I',len(rows)))
  for row,raw in rows:stream.write(struct.pack('<13I',*row));stream.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'original_ai_projection_checks':source_checks,'packed_start_offsets':list(range(8)),'byte_aligned_start_offsets':[0,8],'source_scenarios':8,'string_length_cases':[0,3,11,999,1000],'native_max_including_nul':1000,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())},jni_proof

def main():
 if not __debug__:raise ValueError('Python assertions required')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture-output',type=Path);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args();root=args.source_root.resolve()
 if args.output.exists():raise ValueError('fresh evidence output required')
 engine=root/'native-android/engine';entities=engine/'entities';base=module('initial_aianim_original_components',entities/'check.py');retained=retained_triggered(root)
 sources=[HERE/'coh_initial_aianim_probe.c',engine/'replication/coh_replication.c'];inputs=set(sources+[HERE/'coh_initial_aianim_probe.h',HERE/'test_initial_aianim_probe.c',Path(__file__),entities/'check.py',entities/'source-pins.json',entities/'oracle_shim.h',entities/'stats_oracle_shim.h',entities/'rare_fixture.c.inc',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-triggered-20261019/host.json',HERE/'qualification/initial-triggered-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/name for name in base.FILES)
 for source in sources+[HERE/'test_initial_aianim_probe.c']:
  dependencies=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(name).resolve()for name in shlex.split(dependencies))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]
 if args.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-initial-aianim-')as temporary:
  work=Path(temporary);base.oracle(root,work);verify();source=work/'aianim-original.c';source.write_text((work/'source-oracle.c').read_text()+WRAPPER);oracle=work/'aianim-original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(entities),source,'-lm','-o',oracle]);lib=C.CDLL(str(oracle));lib.aianim_original.argtypes=[C.c_uint]*3+[C.c_void_p]*4;wire,proof,jni=fixtures(lib,work,retained,args.fixture_output)
  for mode,flags in modes:
   executable=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_aianim_probe.c','-lm','-o',executable]);checks[mode]=json.loads(run([executable,wire],env=env));binaries[mode]=sha(executable.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('qualification modes differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_aianim_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('unbounded probe stack')
  original={'executed_component_producer':'entSendAiAnimList','whole_function_sha256_lf':sha(base.extract(base.source_text(root,'MapServer/src/entity/entsend.c'),'entSendAiAnimList').encode()),'source_pin_manifest_sha256':sha((entities/'source-pins.json').read_bytes()),'all_original_source_pins_verified':True,'generated_original_oracle_sha256':sha(source.read_bytes()),'wrapper_sha256':sha(WRAPPER.encode()),'native_string_max_including_nul':1000,'original_string_pointer_has_this_bound':False,'initial_outer_update_required':True,'producer_predicates_exercised':['appearance1','appearance0 updated1','appearance0 updated0'],'original_consumer_executed':False,'oracle_sanitized':False}
 verify();args.output.parent.mkdir(parents=True,exist_ok=True)
 result={'schema':'coh-initial-aianim-probe-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if 'upstream/ouroboros'not in str(path)},'original_component':original,'retained_triggered_prefix':retained[2],'fixtures':proof,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'fixture_join':'Exact complete original AI-animation leaf with explicit fixture entity/offsets and opaque next-field witness. JNI reuses hashed qualified triggered prefix with matching bit alignment.','physical_packet_body_retained_in_evidence':False,'netfx_produced_or_parsed':False,'old_triggered_sequence_or_pose_ranges_reexecuted':False,'whole_original_allents_producer_executed':False,'actual_server_transaction':False,'physical_device_executed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['count'],'jni':jni}))
if __name__=='__main__':main()

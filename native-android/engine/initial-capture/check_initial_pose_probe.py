#!/usr/bin/env python3
"""Focused initial mode/absolute pose proof using unchanged original leaves."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise RuntimeError(repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

WRAPPER=r'''
/* Explicit synthetic outer flags/objects. The three complete original leaf
 * functions above remain unchanged; this is not sendEntity or a live packet. */
void pose_original(unsigned aligned,unsigned prefix,unsigned scenario,unsigned variant,
 U8*out,U32*bits,U32*boundaries){
 U32 storage[8192]={0};Packet p={0};Entity e={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 if(prefix)pktSendBits(&p,(int)prefix,0);
 boundaries[0]=bsGetCursorBitPosition(&p.stream);
 original_record_entity(&e,91);
 switch(scenario){
 case 1:e.state.mode=0;for(int j=0;j<3;j++){e.net_ipos[j]=0;e.net_iqrot[j]=0;}break;
 case 2:e.state.mode=7;for(int j=0;j<3;j++){e.net_ipos[j]=0xffffff;e.net_iqrot[j]=511;}break;
 case 3:e.state.mode=8;for(int j=0;j<3;j++){e.net_ipos[j]=0x800000;e.net_iqrot[j]=256;}break;
 case 4:e.state.mode=0x7fffffff;e.net_ipos[0]=1;e.net_ipos[1]=0xffffff;e.net_ipos[2]=0x800000;e.net_iqrot[0]=1;e.net_iqrot[1]=510;e.net_iqrot[2]=255;break;
 case 5:e.state.mode=63;e.net_ipos[0]=0x7fffff;e.net_ipos[1]=2;e.net_ipos[2]=0xfffffe;e.net_iqrot[0]=255;e.net_iqrot[1]=257;e.net_iqrot[2]=3;break;
 default:break;
 }
 pktSendBits(&p,1,variant==2?0:1);
 if(variant!=2){pktSendBits(&p,1,variant==3?0:1);pktSendBits(&p,1,variant==4?0:1);}
 boundaries[1]=bsGetCursorBitPosition(&p.stream);
 entSendModes(&p,&e,variant==5?0:1);
 boundaries[2]=bsGetCursorBitPosition(&p.stream);
 entSendPosUpdate(&p,&e,variant==6?0:variant==7?1:variant==8?6:7,1,0);
 boundaries[3]=bsGetCursorBitPosition(&p.stream);
 entSendQrotUpdate(&p,&e,variant==9?0:variant==10?1:variant==11?3:7);
 boundaries[4]=bsGetCursorBitPosition(&p.stream);
 /* Only an opaque remaining-body witness. Sequence itself is not produced. */
 if(variant!=1){pktSendBits(&p,1,1);pktSendBits(&p,32,0xdeadbeef);}
 *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
/* Source-generated component fixture for the separate JNI double test. The
 * header/index/rare flags are explicit synthetic framing, never device data. */
void pose_initial_fixture(U8*out,U32*bits,U32*boundaries){
 U32 storage[8192]={0};Packet p={0};Entity e={0};Character ch={3,1,1,NULL};Player pl={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,0,0);
 pktSendBitsPack(&p,1,3);boundaries[0]=bsGetCursorBitPosition(&p.stream);
 pktSendBitsPack(&p,1,7);pktSendBits(&p,1,1);pktSendBitsPack(&p,1,0);
 pktSendBits(&p,32,123);pktSendBits(&p,32,456);pktSendBits(&p,1,1);
 pktSendBitsPack(&p,1,17);pktSendBits(&p,1,1);
 original_record_entity(&e,91);e.type=2;e.db_id=909090;e.pchar=&ch;e.pl=&pl;e.name="FixturePlayer";
 entSendCreate(&p,&e,&e,1);boundaries[1]=bsGetCursorBitPosition(&p.stream);
 pktSendBits(&p,1,1);pktSendBits(&p,1,1);pktSendBits(&p,1,1);
 entSendModes(&p,&e,1);entSendPosUpdate(&p,&e,7,1,0);entSendQrotUpdate(&p,&e,7);
 boundaries[2]=bsGetCursorBitPosition(&p.stream);
 pktSendBits(&p,1,1);pktSendBits(&p,32,0xdeadbeef);
 *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
'''

def fixtures(lib,work):
 rows=[];manifest=[]
 def build(mode,start,scenario,variant):
  output=(C.c_uint8*32768)();bits=C.c_uint32();ends=(C.c_uint32*5)();lib.pose_original(mode,start,scenario,variant,output,C.byref(bits),ends);raw=bytearray(output[:(bits.value+7)//8])
  # Original rounded scalar writers mask unused high bits; malformed inputs
  # below are explicit byte mutations of valid original-component output.
  if variant in(12,13,14):raw[ends[0]//8+variant-12]=2
  elif variant==15:raw[ends[1]//8]=2
  elif variant==16:raw[ends[1]//8+1]=2
  elif variant==17:raw[ends[2]//8]=8
  elif variant==18:raw[ends[3]//8]=2
  elif variant==19:raw[ends[3]//8+1]=8
  elif variant==20:raw[ends[3]//8+2]=0;raw[ends[3]//8+3]=2
  status=1 if variant==1 or variant>=12 else 2
  stage=2 if variant in(2,3,4,12,13,14) else 3 if variant in(5,15,16) else 4 if variant in(6,7,8,17) else 5 if variant in(9,10,11,18,19,20) else 6
  validated=[int(stage>i)for i in(2,3,4,5)]
  packet_id=(1,77,0xffffffff)[scenario%3]
  row=(len(raw),bits.value,mode,variant,scenario,packet_id,status,stage,*ends,*validated,int(stage==6))
  rows.append((row,raw));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'sha256':sha(raw)})
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(6):build(mode,start,scenario,0)
  for variant in range(1,21 if mode else 12):build(mode,0,0,variant)
 path=work/'fixtures.bin'
 with path.open('xb')as stream:
  stream.write(struct.pack('<I',len(rows)))
  for row,raw in rows:stream.write(struct.pack('<18I',*row));stream.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'original_leaf_scenarios':6,'packed_start_offsets':list(range(8)),'byte_aligned_start_offsets':[0,8],'synthetic_control_variants':20,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())}

def main():
 if not __debug__:raise ValueError('Python assertions required')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture-output',type=Path);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args();root=args.source_root.resolve()
 if args.output.exists():raise ValueError('fresh evidence output required')
 engine=root/'native-android/engine';entities=engine/'entities';helper=module('initial_pose_original_components',entities/'check.py')
 sources=[HERE/'coh_initial_pose_probe.c',engine/'replication/coh_replication.c',entities/'coh_entities.c']
 inputs=set(sources+[HERE/'coh_initial_pose_probe.h',HERE/'test_initial_pose_probe.c',Path(__file__),entities/'check.py',entities/'source-pins.json',entities/'oracle_shim.h',entities/'stats_oracle_shim.h',entities/'rare_fixture.c.inc',root/'native-android/tools/protocol_fixture/prepare.py'])
 inputs.update(root/'upstream/ouroboros'/name for name in helper.FILES)
 for source in sources+[HERE/'test_initial_pose_probe.c']:
  dependencies=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(name).resolve()for name in shlex.split(dependencies))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]
 if args.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={};jni_fixture=None;env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-initial-pose-')as temporary:
  work=Path(temporary);helper.oracle(root,work);verify();code=(work/'source-oracle.c').read_text()+WRAPPER;source=work/'pose-original.c';source.write_text(code);oracle=work/'pose-original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(entities),source,'-lm','-o',oracle]);lib=C.CDLL(str(oracle));lib.pose_original.argtypes=[C.c_uint]*4+[C.c_void_p]*3;wire,proof=fixtures(lib,work)
  if args.fixture_output:
   raw=(C.c_uint8*32768)();bits=C.c_uint32();ends=(C.c_uint32*3)();lib.pose_initial_fixture.argtypes=[C.c_void_p]*3;lib.pose_initial_fixture(raw,C.byref(bits),ends);payload=bytes(raw[:(bits.value+7)//8]);header='/* SOURCE-GENERATED FIXTURE; synthetic framing plus unchanged original create/mode/position/quaternion producers. Never device packet data. */\nstatic const unsigned char coh_pose_jni_fixture[]={'+','.join(map(str,payload))+'};\n#define COH_POSE_JNI_FIXTURE_BITS '+str(bits.value)+'u\n#define COH_POSE_JNI_FIXTURE_POST_COMMAND '+str(ends[0])+'u\n#define COH_POSE_JNI_FIXTURE_CREATE_END '+str(ends[1])+'u\n#define COH_POSE_JNI_FIXTURE_POSE_END '+str(ends[2])+'u\n';args.fixture_output.parent.mkdir(parents=True,exist_ok=True);args.fixture_output.write_text(header);jni_fixture={'header_sha256':sha(header.encode()),'payload_sha256':sha(payload),'payload_bits':bits.value,'post_command_bit':ends[0],'create_end_bit':ends[1],'pose_end_bit':ends[2],'synthetic_selected_dbid':909090,'unchanged_original_create_producer':True,'device_packet':False}
  for mode,flags in modes:
   executable=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_pose_probe.c','-lm','-o',executable]);checks[mode]=json.loads(run([executable,wire],env=env));binaries[mode]=sha(executable.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('qualification modes differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_pose_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('unbounded probe stack')
  original={'executed_component_producers':['entSendModes','entSendPosUpdate','entSendQrotUpdate'],'component_sha256_lf':{name:sha(helper.extract(helper.source_text(root,'MapServer/src/entity/entsend.c'),name).encode())for name in('entSendModes','entSendPosUpdate','entSendQrotUpdate')},'source_pin_manifest_sha256':sha((entities/'source-pins.json').read_bytes()),'all_original_source_pins_verified':True,'generated_original_oracle_sha256':sha(source.read_bytes()),'wrapper_sha256':sha(WRAPPER.encode()),'oracle_sanitized':False}
 verify();args.output.parent.mkdir(parents=True,exist_ok=True)
 result={'schema':'coh-initial-pose-probe-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if 'upstream/ouroboros'not in str(path)},'original_components':original,'fixtures':proof,'source_generated_jni_fixture':jni_fixture,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'fixture_join':'Explicit synthetic outer flags, fixture objects and opaque remaining-body witness around complete unchanged original mode/position/quaternion producers; no sendEntity or entSendUpdate execution.','physical_packet_body_retained_in_evidence':False,'sequence_body_produced_or_parsed':False,'whole_original_allents_producer_executed':False,'actual_server_transaction':False,'physical_device_executed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['count']}))
if __name__=='__main__':main()

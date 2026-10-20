#!/usr/bin/env python3
"""Whole original sender -> whole original bounded receiver qualification."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(args,work,stem,env=None):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,env=env,timeout=240)
 for k,v in [('command.json',json.dumps(list(map(str,args)))),('stdout',r.stdout),('stderr',r.stderr)]: (work/(stem+'.'+k)).write_text(v)
 if r.returncode:raise RuntimeError(stem+' '+str(r.returncode)+'\n'+r.stderr[-4000:]+r.stdout[-1000:])
 return r.stdout
def fixtures(root,work,extract):
 prep=module('costume_packet_prepare',HERE/'../../tools/protocol_fixture/prepare.py')
 paths=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c']
 pins=json.loads((HERE/'source-pins.json').read_text())['sha256_lf'];texts={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in paths}
 for n,v in texts.items():assert sha(v.encode())==pins[n],n
 bit,util,math,costume=[texts[n]for n in paths];names=[]
 def take(text,name):names.append((name,sha(extract(text,name).encode())));return extract(text,name)
 code=prep.PREAMBLE+''.join(take(bit,n)for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'])
 code+='''\nstatic void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet*p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendString(Packet*p,const char*s){bsWriteString(&p->stream,s?s:"");}
static void pktSendF32(Packet*p,F32 f);
'''
 # Reuse existing member/stash fixture declarations. No new source ABI claim.
 code+=(HERE/'costume_oracle_shim.h').read_text().replace('typedef float F32;','typedef float F32;')
 # F32 must be declared after the existing shim declarations above.
 code=code.replace('static void pktSendF32(Packet*p,F32 f);','static void pktSendF32(Packet*p,float f);')
 code+='static void pktSendF32(Packet*p,F32 f){U32 u;memcpy(&u,&f,4);pktSendBits(p,32,u);}\n'
 code+=take(math,'log2i')+take(util,'pktSendF')+take(util,'defaultBitsPack')+take(util,'defaultBitsPackGeneric')
 code+='''\n#define stashFindIndexByKey(t,s,p) ((void)(t),(void)(s),(void)(p),0)
#define stashIntFindIndexByKey(t,v,p) ((void)(t),(void)(v),(void)(p),0)
'''
 code+=take(util,'pktSendIndexedString')+take(util,'pktSendIndexedGeneric')
 code+='static unsigned fixture_default;\n#define GetBodyPartCount() ((int)fixture_default)\n'
 code+=''.join(take(costume,n)for n in ['sendCachedIndexedString','sendCachedIndexedColor','costume_send'])
 code+='''
void fixture(unsigned mode,unsigned start,unsigned count,unsigned def,unsigned extra,unsigned names,U8*out,U32*length){
 U32 memory[32768]={0};Packet p={0};Costume c={0};CostumePart parts[30]={{0}};
 assert(count<=28&&def<=28&&(!mode||!start));fixture_default=def;
 for(unsigned i=0;i<30;i++)c.parts[i]=&parts[i];c.appearance.bodytype=1;c.appearance.iNumParts=(int)count;
 c.appearance.entTypeFile=names?"FixtureEntity":NULL;c.appearance.costumeFilePrefix=names?"Male":NULL;
 for(unsigned i=0;i<30;i++)c.appearance.fScales[i]=.125f;
 for(unsigned i=0;i<count;i++){parts[i].pchGeom="FixtureGeometry";parts[i].pchTex1="InlineTexture";parts[i].pchTex2="InlineTexture";parts[i].pchFxName=i%2?"GlowFX":NULL;parts[i].regionName="Upper";parts[i].bodySetName="BodySet";for(unsigned j=0;j<4;j++)parts[i].color[j].integer=0x12340000+j;}
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<start;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;costume_send(&p,&c,(int)extra);assert(!p.stream.errorFlags);*length=p.stream.bitLength;memcpy(out,memory,(*length+7)/8);
}
'''
 src=work/'original-sender.c';src.write_text(code);lib=work/'original-sender.so'
 run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),src,'-lm','-o',lib],work,'sender-compile')
 dll=C.CDLL(str(lib));dll.fixture.argtypes=[C.c_uint]*6+[C.c_void_p,C.c_void_p]
 scenarios=[]
 for mode in (0,1):
  for start in ((0,3,7)if not mode else(0,)):
   for count in (0,1,4,28):
    for extra in (0,1):
     for names_on in (0,1):
      b=(C.c_uint8*16384)();bits=C.c_uint32();dll.fixture(mode,start,count,28,extra,names_on,b,C.byref(bits));scenarios.append((mode,start,28,count,bits.value,bytes(b[:(bits.value+7)//8])))
 out=bytearray(struct.pack('<I',len(scenarios)))
 for mode,start,bodycount,count,bits,b in scenarios:out+=struct.pack('<IIIII',mode,start,bodycount,count,bits)+b
 path=work/'fixtures.bin';path.write_bytes(out)
 return path,{'scenarios':len(scenarios),'source_sha256_lf':{n:pins[n]for n in paths},'whole_functions':dict(names),'generated_sha256':sha(code.encode()),'fixtures_sha256':sha(out),'table_fixture_forces_literal_misses':True,'sender_source_sanitized':False,'sender_alias_profile':'Original BitStream helper executed O0, inherited unchanged fixture scalar wrappers; source alias idioms not sanitizer-qualified.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
 gen=module('original_receiver_generator',HERE/'prepare_original_costume_receive.py');generated,sourceproof=gen.generate(a.source_root)
 assert(HERE/'original_costume_receive.inc').read_text()==generated;assert json.loads((HERE/'original-costume-receive-source.json').read_text())==sourceproof
 inputs=[HERE/n for n in ['coh_original_costume_receive.c','coh_original_costume_receive.h','original_costume_receive.inc','original-costume-receive-source.json','prepare_original_costume_receive.py','test_original_costume_receive.c','costume_oracle_shim.h','source-pins.json','check_original_costume_receive.py']]+[HERE/'../replication/coh_replication.c',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',HERE/'../../tools/protocol_fixture/prepare.py']
 before={str(v.resolve().relative_to(ROOT)):sha(v.read_bytes())for v in inputs};fixture,producer=fixtures(a.source_root,work,gen.extract)
 proof={'schema':'coh-original-costume-receiver-v1','source_head':run(['git','-C',ROOT,'rev-parse','HEAD'],work,'head').strip(),'source':sourceproof,'original_sender':producer,'inputs_sha256':before,'native':{}}
 for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  target=work/mode;target.mkdir();binary=target/'receiver';run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,HERE/'coh_original_costume_receive.c',HERE/'../replication/coh_replication.c',HERE/'test_original_costume_receive.c','-lm','-o',binary],target,'compile')
  env=os.environ.copy();env.update(ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');result=json.loads(run([binary,fixture],target,'native',env));result['binary_sha256']=sha(binary.read_bytes());proof['native'][mode]=result
 frames=[]
 for path in(work/'release').glob('*.su'):
  for line in path.read_text().splitlines():
   name,size,kind=line.split('\t')
   if 'test_original_'not in name:assert kind in('static','dynamic,bounded');frames.append({'name':name,'bytes':int(size),'kind':kind})
 # Conservative sum includes even unrelated linked replication entrypoints.
 wrapperframes=[x for x in frames if'coh_original_costume_receive.c:'in x['name']or'original_costume_receive.inc:'in x['name']or x['name'].rsplit(':',1)[-1]in('valid','coh_rep_read','coh_rep_pack')]
 total=sum(x['bytes']for x in wrapperframes);assert total<=4096
 proof['memory']={'workspace_bytes':65536,'native_frame_sum':total,'call_stack_reserve':4096,'frames':wrapperframes,'heap_allocations':0,'RSS_PSS':None,'caller_initial_aggregate_ceiling':8388608,'workspace_must_be_charged_by_caller':True,'leak_sanitizer_executed':False}
 assert before=={str(v.resolve().relative_to(ROOT)):sha(v.read_bytes())for v in inputs}
 proof.update(passed=True,whole_original_receiver_executed=True,source_fields_rewritten=False,raw_index_pack_skipped=False,actual_server_packet_replayed=False,android_executed=False,world_or_ACK_accepted=False)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'native':proof['native'],'stack':total,'output':str(a.output)}))
if __name__=='__main__':main()

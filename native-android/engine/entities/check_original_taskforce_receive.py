#!/usr/bin/env python3
"""Original taskforce senders -> unchanged receivers with CLIENT costume slots.
Legacy parameter receiver alone excludes shift sanitizer for source1<<31; all new
native adapters remain instrumented. No live packet, actor or ACK is admitted.
"""
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,os,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=False)
 gen=mod('tf_source',HERE/'prepare_original_taskforce_receive.py');legacy=mod('tf_body_oracle',HERE/'check_original_costume_receive.py');body=mod('tf_body_extract',HERE/'prepare_original_costume_receive.py');slots=mod('tf_slots',HERE/'check_client_costume_slots.py');generated,provenance=gen.generate(a.source_root);assert generated==(HERE/'original_taskforce_receive.inc').read_text()
 legacy.fixtures(a.source_root,w,body.extract);archive=HERE/'qualification/costume-builder-20261017/offline-primary-slots.bin.gz';raw=gzip.decompress(archive.read_bytes());assert hashlib.sha256(raw).hexdigest()==slots.RAW_SHA;_,tables=slots.projection(raw);slots.indexed_sender(w,legacy,tables);rawfile=w/'slots.bin';rawfile.write_bytes(raw)
 code=(w/'indexed-original-sender.c').read_text().replace('static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}','');util=(a.source_root/'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packetutil.c').read_text();sender=(a.source_root/'upstream/ouroboros/MapServer/src/entity/entsend.c').read_text();costume=(a.source_root/'upstream/ouroboros/Common/entity/costume.c').read_text();pins=json.loads((HERE/'source-pins.json').read_text())['sha256_lf'];assert hashlib.sha256(sender.encode()).hexdigest()==pins['MapServer/src/entity/entsend.c']
 code+='static int auto_bins[]={2,10,24,32};\n'+body.extract(util,'pktSendBitsAuto')+body.extract(costume,'NPCcostume_send')
 code+='''
#define INLINEDBG
#define MAX_TASKFORCE_PARAMETERS 32
#define TFPARAM_TIME_LIMIT 2
#define TFPARAM_START_TIME 24
typedef struct{int architect_flags,architect_id,architect_contact_override,architect_useCachedCostume;char architect_contact_name[33];Costume*architect_contact_costume;CustomNPCCostume*architect_contact_npc_costume;U32 parametersSet,parameters[32];}TaskForce;
typedef struct{int taskforce_id,onArchitect,invincible,untargetable;TaskForce*taskforce;}Entity;
typedef struct{char*pchName,*pchAuthor,*pchDescription;int rating,european;}PlayerCreatedStoryArc;
static PlayerCreatedStoryArc *arc;
static PlayerCreatedStoryArc *playerCreatedStoryArc_GetPlayerCreatedStoryArc(int id){(void)id;return arc;}
static int TaskForceIsOnArchitect(Entity*e){return e->onArchitect;}
static int timerSecondsSince2000(void){return 10;}
static U32 body_end;
static void tf_body_send(Packet*p,Costume*c,int names){costume_send(p,c,names);body_end=p->stream.bitLength;}
#define costume_send tf_body_send
'''
 code+=body.extract(sender,'entSendTaskforceParameters')+body.extract(sender,'entSendTaskforceArchitectInfo')
 code+='''
void taskforce_fixture(unsigned mode,unsigned start,unsigned scenario,U8*out,U32*length,U32*bodyend){
 U32 memory[32768]={0};Packet p={0};Entity e={0};TaskForce tf={0};Costume c={0};CostumePart parts[30]={{0}};CustomNPCCostume custom={0};CustomNPCCostumePart customparts[63]={{0}},*ptrs[63];
 char name[257]="FixtureArc",author[128]="FixtureAuthor",description[4096]="FixtureDescription";PlayerCreatedStoryArc story={name,author,description,-1,3};
 fixture_default=28;c.appearance.bodytype=1;c.appearance.iNumParts=28;for(unsigned i=0;i<30;i++){c.parts[i]=parts+i;parts[i].pchGeom=ordinary_value(2+i*4);parts[i].pchTex1=ordinary_value(3+i*4);parts[i].pchTex2=ordinary_value(4+i*4);parts[i].pchFxName=i%2?ordinary_value(5+i*4):NULL;for(unsigned j=0;j<4;j++)parts[i].color[j].integer=palette_value(j);}
 custom.parts=ptrs;custom_count=63;for(unsigned i=0;i<63;i++){ptrs[i]=customparts+i;customparts[i].regionName="Upper";customparts[i].color[0].integer=i;customparts[i].color[1].integer=i+1;}
 e.taskforce=&tf;e.onArchitect=scenario>=2;e.invincible=3;e.untargetable=17;tf.architect_flags=0x42;tf.architect_id=12345;tf.architect_contact_override=1024;strcpy(tf.architect_contact_name,"FixtureContact");tf.parametersSet=scenario==7?UINT32_MAX:(1u<<1)|(1u<<23)|(1u<<31);for(unsigned i=0;i<32;i++)tf.parameters[i]=i*1023;
 if(scenario==2||scenario==5||scenario==6||scenario==10)tf.architect_contact_costume=&c;if(scenario==3||scenario==5)tf.architect_contact_npc_costume=&custom;tf.architect_useCachedCostume=scenario==6;arc=scenario==4||scenario==7||scenario==9?&story:NULL;
 if(scenario==4){memset(name,'n',255);name[255]=0;memset(author,'a',127);author[127]=0;memset(description,'d',4095);description[4095]=0;}
 if(scenario==8){memset(tf.architect_contact_name,'c',32);tf.architect_contact_name[32]=0;}if(scenario==9){memset(name,'n',256);name[256]=0;}
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<start;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;body_end=0;
 pktSendBits(&p,1,scenario!=0);if(scenario!=0)entSendTaskforceArchitectInfo(&e,&p);pktSendBitsPack(&p,1,scenario%2);pktSendBits(&p,1,scenario!=0);if(scenario!=0)entSendTaskforceParameters(&tf,&p);assert(!p.stream.errorFlags);*length=p.stream.bitLength;*bodyend=body_end;memcpy(out,memory,(*length+7)/8);
}
'''
 src=w/'sender.c';src.write_text(code);lib=w/'sender.so';legacy.run(['cc','-std=c99','-O0','-w','-shared','-fPIC','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),src,'-lm','-o',lib],w,'sender-compile');dll=C.CDLL(str(lib));dll.load_projection(C.create_string_buffer(raw));dll.taskforce_fixture.argtypes=[C.c_uint]*3+[C.c_void_p]*3
 records=[]
 for mode in(0,1):
  for start in((0,3,7)if not mode else(0,)):
   for scenario in range(11):
    buf=(C.c_uint8*131072)();end=C.c_uint();bodyend=C.c_uint();dll.taskforce_fixture(mode,start,scenario,buf,C.byref(end),C.byref(bodyend));records.append((mode,start,scenario,end.value,bodyend.value,bytes(buf[:(end.value+7)//8])))
 fixture=w/'fixtures.bin';data=bytearray(struct.pack('<I',len(records)))
 for row in records:data+=struct.pack('<5I',*row[:-1])+row[-1]
 fixture.write_bytes(data);result={'passed':True,'source':provenance,'sender_sha256':hashlib.sha256(code.encode()).hexdigest(),'sender_original_functions':['entSendTaskforceParameters','entSendTaskforceArchitectInfo','costume_send','NPCcostume_send'],'sender_sanitized':False,'fixtures_sha256':hashlib.sha256(data).hexdigest(),'modes':{}}
 flags=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage'];sources=[HERE/'coh_original_taskforce_receive.c',HERE/'coh_original_costume_receive.c',HERE/'../replication/coh_replication.c',HERE/'test_original_taskforce_receive.c']
 for mode,opts in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=w/mode;legacy.run([*flags,*opts,*sources,'-lcrypto','-lm','-o',binary],w,mode+'-compile');result['modes'][mode]=json.loads(legacy.run([binary,rawfile,fixture],w,mode+'-run',{**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}))
 frames=[]
 for file in w.glob('release-*.su'):
  for line in file.read_text().splitlines():
   name,size,kind=line.split('\t')
   if 'test_original_'not in name and('original_taskforce'in name or'original_costume'in name or name.rsplit(':',1)[-1]in('valid','coh_rep_read','coh_rep_pack')):frames.append((name,int(size),kind))
 total=sum(f[1]for f in frames);assert total<=16384;result['memory']={'native_frame_sum':total,'stack_reserve':16384,'body_workspace':65536,'raw_and_index':775621,'heap_allocations':0,'initial_aggregate_limit':8388608,'device_RSS_PSS':None,'frames':frames};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':result['modes'],'native_frame_sum':total}))
if __name__=='__main__':main()

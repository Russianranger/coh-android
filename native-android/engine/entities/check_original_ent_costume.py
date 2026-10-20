#!/usr/bin/env python3
"""Whole original appearance sender/receiver; no live packet completeness claim."""
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,os,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=False)
 legacy=module('outer_legacy',HERE/'check_original_costume_receive.py');gen=module('outer_source',HERE/'prepare_original_ent_costume.py');body=module('outer_body_source',HERE/'prepare_original_costume_receive.py');slots=module('outer_slots',HERE/'check_client_costume_slots.py')
 generated,proof=gen.generate(a.source_root);assert generated==(HERE/'original_ent_costume_receive.inc').read_text()
 legacy.fixtures(a.source_root,w,body.extract);raw=gzip.decompress((HERE/'qualification/costume-builder-20261017/offline-primary-slots.bin.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==slots.RAW_SHA
 rawfile=w/'slots.bin';rawfile.write_bytes(raw);_,tables=slots.projection(raw);slots.indexed_sender(w,legacy,tables)
 code=(w/'indexed-original-sender.c').read_text();prefix=module('outer_prefix',HERE/'../initial-capture/check_initial_costume_probe.py');shim=prefix.SHIM
 shim=shim.replace('typedef struct {unsigned fixture;} Costume;','').replace('static void*costume_HashTable;','')
 shim=shim[0:shim.index('static unsigned observed_boundary')]+shim[shim.index('static Costume*costume_current'):]
 shim=shim.replace('static int fixture_ea_size(void*p){if(p==groups[0])return group_counts[0];assert(p==groups[1]);return group_counts[1];}','static int fixture_ea_size(void*p){if(p==groups[0])return group_counts[0];if(p==groups[1])return group_counts[1];return custom_count;}')
 shim='#undef eaSize\n'+shim
 comm=(a.source_root/'upstream/ouroboros/Common/comm_game.h').read_text();at=comm.index('typedef enum',comm.index('// Used by entsend and entrecv.'));code+=comm[at:comm.index('} AppearanceType;',at)+len('} AppearanceType;')]+'\n'+(a.source_root/'upstream/ouroboros/Common/entity/entity_enum.h').read_text()+shim
 util=(a.source_root/'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packetutil.c').read_text();costume=(a.source_root/'upstream/ouroboros/Common/entity/costume.c').read_text();sender=(a.source_root/'upstream/ouroboros/MapServer/src/entity/entsend.c').read_text()
 pins=json.loads((HERE/'source-pins.json').read_text())['sha256_lf'];assert hashlib.sha256(sender.encode()).hexdigest()==pins['MapServer/src/entity/entsend.c']
 code+=''.join(body.extract(util,n)for n in ('pktSendIfSetBitsPack','pktSendIfSetString'))+body.extract(costume,'ent_SendCostumeRewards')+body.extract(costume,'NPCcostume_send')+body.extract(sender,'entSendCostume')
 wrapper=(w/'indexed-original-sender.c').read_text();wrapper=wrapper[wrapper.index('void fixture('):wrapper.index('void list_fixture(')]
 wrapper=wrapper.replace('void fixture(unsigned mode,unsigned start,unsigned count,unsigned def,unsigned extra,unsigned names,U8*out,U32*length)','void outer_fixture(unsigned mode,unsigned start,unsigned count,unsigned def,unsigned extra,unsigned names,unsigned bodies,unsigned sg,unsigned fx,unsigned npc,unsigned custom,unsigned xlucency,U8*out,U32*length,U32*appearance)')
 wrapper=wrapper.replace('costume_send(&p,&c,(int)extra);','''Entity e={0};Player pl={0};CustomNPCCostume customcostume={0};CustomNPCCostumePart customparts[63]={{0}},*ptrs[63];e.type=ENTTYPE_PLAYER;e.pl=&pl;e.send_all_costume=1;e.supergroup_id=sg;e.npcIndex=123;e.costumeIndex=2;e.costumeWorldGroup=npc?"WorldGroup":NULL;e.customNPC_costume=custom?&customcostume:NULL;customcostume.parts=ptrs;custom_count=custom;assert(custom<=63);for(unsigned i=0;i<custom;i++){ptrs[i]=&customparts[i];customparts[i].regionName="Upper";}for(unsigned i=0;i<10;i++)pl.costume[i]=&c;pl.num_costumes_stored=bodies;pl.supergroup_mode=1;pl.hide_supergroup_emblem=1;pl.npc_costume=npc;if(fx)strcpy(pl.costumeFxSpecial,"GlowFX");pl.rewardTokens=groups[0];pl.ArchitectRewardTokens=groups[1];entSendCostume(&p,&e,&e,1);*appearance=p.stream.bitLength;pktSendBits(&p,1,xlucency!=0);if(xlucency)pktSendBits(&p,8,xlucency);''')
 code+=wrapper;src=w/'outer-sender.c';src.write_text(code);dllfile=w/'outer-sender.so';legacy.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),src,'-lm','-o',dllfile],w,'outer-sender-compile');dll=C.CDLL(str(dllfile));dll.load_projection(C.create_string_buffer(raw));dll.outer_fixture.argtypes=[C.c_uint]*12+[C.c_void_p]*3
 records=[]
 for mode in(0,1):
  for start in((0,3,7)if not mode else(0,)):
   for bodies in(1,2,10):
    for sg,fx,npc,custom,xlucency in((0,0,0,0,0),(1,0,0,0,0),(0,1,0,0,128),(1,1,1,0,255),(0,0,1,2,1),(1,1,1,63,0)):
     b=(C.c_uint8*131072)();end=C.c_uint();appearance=C.c_uint();dll.outer_fixture(mode,start,28,28,1,1,bodies,sg,fx,npc,custom,xlucency,b,C.byref(end),C.byref(appearance));records.append((mode,start,bodies,sg,fx,npc,custom,appearance.value,end.value,bytes(b[:(end.value+7)//8])))
 fixture=w/'outer.bin';data=bytearray(struct.pack('<I',len(records)))
 for row in records:data+=struct.pack('<9I',*row[:-1])+row[-1]
 fixture.write_bytes(data);result={'passed':True,'source':proof,'sender_sha256':hashlib.sha256(code.encode()).hexdigest(),'fixture_sha256':hashlib.sha256(data).hexdigest(),'modes':{}}
 flags=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage'];sources=[HERE/'coh_original_ent_costume.c',HERE/'coh_original_costume_receive.c',HERE/'../replication/coh_replication.c',HERE/'test_original_ent_costume.c']
 for mode,opts in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=w/mode;legacy.run([*flags,*opts,*sources,'-lcrypto','-lm','-o',binary],w,mode+'-compile');result['modes'][mode]=json.loads(legacy.run([binary,rawfile,fixture],w,mode+'-run',{**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}))
 frames=[]
 for path in w.glob('release-*.su'):
  for line in path.read_text().splitlines():
   name,size,kind=line.split('\t')
   if 'test_original_'not in name:frames.append((name,int(size),kind))
 frames=[f for f in frames if 'ent_costume'in f[0]or'original_costume'in f[0]or f[0].rsplit(':',1)[-1]in('valid','coh_rep_read','coh_rep_pack')];total=sum(f[1]for f in frames);assert total<=8192
 result['memory']={'frame_sum':total,'stack_reserve':8192,'frames':frames,'body_workspace':65536,'snapshot':48352,'raw_and_index':775621,'aggregate_limit':8388608,'RSS_PSS':None};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':result['modes'],'stack_frame_sum':total}))
if __name__=='__main__':main()

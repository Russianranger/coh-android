#!/usr/bin/env python3
"""Compose existing source-qualified rare suffix parsers, with optional real replay."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(b):return hashlib.sha256(b).hexdigest()
def bitlist(raw,a,b):return[(raw[i//8]>>(i%8))&1 for i in range(a,b)]
def rawbits(bits):
 b=bytearray((len(bits)+7)//8)
 for i,v in enumerate(bits):b[i//8]|=v<<(i%8)
 return bytes(b)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--replay',type=Path);ap.add_argument('--begin',type=int);a=ap.parse_args();assert bool(a.replay)==(a.begin is not None);w=a.work.resolve();w.mkdir(parents=True,exist_ok=False)
 legacy=module('rare_native_run',HERE/'check_original_costume_receive.py');entity=module('rare_entity_source',HERE/'check.py');tail=module('rare_tail_source',HERE/'check_very_rare_tail.py');buffs=module('rare_buffs_source',HERE/'check_teammate_buffs.py')
 for p in('entity','tail','buffs'):(w/p).mkdir()
 elib,epins,enames,etitles,eprefix=entity.oracle(ROOT,w/'entity');tlib,tproof=tail.oracle(w/'tail');blib,bproof=buffs.oracle(w/'buffs')
 source=entity.source_text(ROOT,'Game/src/entity/entrecv.c');whole=entity.extract(source,'entReceive');begin=whole.index('            // These are just part of the main stream');end=whole.index('    // If there are any outstanding floaters',begin);block=whole[begin:end];order=['entReceiveSendOnOddSend','entReceiveAllyID','entReceivePvP','entReceiveNameUpdate','entReceivePetInfo','entReceiveAFK','entReceiveOtherSupergroupInfo','entReceiveLevelingpactInfo','entReceiveLogoutUpdate','entReceiveBuffs'];assert[block.index(n+'(')for n in order]==sorted(block.index(n+'(')for n in order)
 rows=[]
 for mode in(0,1):
  for start in((0,3,7)if not mode else(0,)):
   for scenario in range(28):
    pr=(C.c_uint8*32768)();pb=C.c_uint32();ps=C.c_uint32();pex=(C.c_uint8*elib.original_rare_size())();elib.original_rare(scenario%8,mode,start,pr,C.byref(pb),C.byref(ps),pex)
    tr=(C.c_uint8*262144)();tb=C.c_uint32();ts=C.c_uint32();tn=(C.c_uint8*tlib.tail_observation_size())();to=(C.c_uint8*tlib.tail_observation_size())()
    if scenario==25:tlib.tail_receiver_only(mode,0,tr,C.byref(tb),C.byref(ts),tn,to)
    else:tlib.tail_original(scenario,mode,0,tr,C.byref(tb),C.byref(ts),tn,to)
    br=(C.c_uint8*1048576)();bb=C.c_uint32();bs=C.c_uint32();bn=(C.c_uint32*32768)();bo=(C.c_uint32*32768)();nc=C.c_uint32();oc=C.c_uint32();blib.buffs_original(scenario,mode,0,br,C.byref(bb),C.byref(bs),bn,C.byref(nc),bo,C.byref(oc))
    joined=bitlist(pr,0,pb.value)+bitlist(tr,ts.value,tb.value)+(bitlist(br,bs.value,bb.value)if scenario!=24 else[]);prefixend=pb.value;tailend=prefixend+tb.value-ts.value;status=4 if scenario in(21,22,23,15,17,18)else 1 if scenario==24 else 0;stage=2 if scenario in(21,22,23,24)else 3 if scenario in(15,17,18)else 4
    rows.append((mode,ps.value,scenario,status,stage,prefixend,tailend,len(joined),bytes(pex),rawbits(joined)))
 data=bytearray(struct.pack('<II',len(rows),elib.original_rare_size()))
 for row in rows:data+=struct.pack('<8I',*row[:8])+row[8]+row[9]
 fixture=w/'fixtures.bin';fixture.write_bytes(data)
 result={'passed':True,'source_order':{'source_sha256_lf':sha(source.encode()),'original_entReceive_block_sha256_lf':sha(block.encode()),'order':order,'enclosing_entReceive_executed':False,'selected_self_fresh_very_rare_profile':True},'original_prefix':eprefix,'original_tail':tproof,'original_buffs':bproof,'fixtures_sha256':sha(data),'source_fixtures':len(rows),'modes':{}}
 flags=['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage'];sources=[HERE/n for n in('coh_original_rare_receive.c','coh_entities.c','coh_very_rare_tail.c','coh_teammate_buffs.c','coh_costume.c','coh_taskforce.c','../replication/coh_replication.c','test_original_rare_receive.c')]
 inputs={p.resolve():sha(p.read_bytes())for p in sources};inputs.update({p.resolve():sha(p.read_bytes())for p in[HERE/'coh_original_rare_receive.h',HERE/'check_original_rare_receive.py',HERE/'coh_entities.h',HERE/'coh_very_rare_tail.h',HERE/'coh_teammate_buffs.h']})
 for mode,opts in [('release',[]),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=w/mode;legacy.run([*flags,*opts,*sources,'-lm','-o',binary],w,mode+'-compile');args=[binary,fixture]+([a.replay,str(a.begin)]if a.replay else[]);result['modes'][mode]=json.loads(legacy.run(args,w,mode+'-run',{**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}))
 assert len({json.dumps(v,sort_keys=True)for v in result['modes'].values()})==1
 frames=[];generic={'valid','coh_rep_read','coh_rep_pack','coh_ent_rare_prefix','check_reader','stage','read_n','pack','flag','scalar','opt_pack','opt_bits','auto_bits','string','require','fail','clear_failure'}
 for p in w.glob('release-*.su'):
  for line in p.read_text().splitlines():
   name,size,kind=line.split('\t');fn=name.rsplit(':',1)[-1]
   if 'test_original_'not in name and('coh_original_rare_receive.c:'in name or'coh_very_rare_tail.c:'in name or'coh_teammate_buffs.c:'in name or('coh_entities.c:'in name and fn in generic)or('../replication/'in name and fn in generic)):frames.append({'function':name,'bytes':int(size),'kind':kind})
 total=sum(f['bytes']for f in frames);assert total<=16384;result['memory']={'workspace_bytes':result['modes']['release']['workspace_bytes'],'report_bytes':result['modes']['release']['report_bytes'],'stack_reserve':16384,'closed_native_frame_sum':total,'frames':frames,'heap_allocations':0,'initial_aggregate_limit':8388608,'child_tail_limit':4194304,'child_buff_limit':4194304,'RSS_PSS':None};result['inputs_sha256']={str(p.relative_to(ROOT)):h for p,h in inputs.items()};assert inputs=={p:sha(p.read_bytes())for p in inputs}
 if a.replay:
  actual=a.replay.read_bytes();assert actual[:8]==b'COHIRP01' and int.from_bytes(actual[8:12],'little')==88 and int.from_bytes(actual[12:16],'little')==len(actual)-88 and sha(actual[88:])==actual[56:88].hex()
  result['actual_replay']={'file_sha256':sha(a.replay.read_bytes()),'source_start_cursor':a.begin,'receipt':'Caller-supplied saved physical INITIAL payload; no raw input committed.'}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':result['modes'],'stack':total}))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Actual replay plus fixed-budget source-ordered character/global continuation."""
import argparse,hashlib,importlib.util,json,os,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--replay',type=Path);a=p.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=False)
 source=module('initial_client_shared_source',HERE/'client_shared_count_source.py').collect(ROOT)
 assert source['canonical_inputs_sha256']=='649b85493dcd6bdc0ebd7669eed9ce61536d8788755075265b17a0905a83bd11' and source['source_profile_token']==1233492836
 assert source['reachable_shared_references']==26 and source['allocated_shared']==27 and source['unreachable_shared']==['N_Tutorial_Powers.Atlas_Normal_VisionPhase']
 startup_pins={'upstream/ouroboros/Game/src/main.c': '0291ebfc9c375bf952a3cd5db23f475942bea8561487ab26b085f7aa462c9c8c', 'upstream/ouroboros/Game/src/game.c': '7a970aa0db124fb68ec37e8b4eb6f5907c4883f9f17a5475ec5b58e5dfa9adde', 'upstream/ouroboros/Common/entity/load_def.c': 'b0d9683471b93194cf40dfe673ca8b2948ef4ebcd05a8ec240062a6e4c3220e5', 'upstream/ouroboros/Common/entity/powers.c': '6d5c9ad363b29f35f866516d253a05edb8ced653576e4c4b31b83322bbe69330', 'upstream/ouroboros/Common/entity/powers_load.c': 'c5b7bbf32621922a36ba097d566840bdd9d4afc692d8e3baacd0e207dc1e12b8'}
 startup={p:subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+p])for p in source['startup_sources']};assert {p:hashlib.sha256(b).hexdigest()for p,b in startup.items()}==startup_pins
 assert re.search(rb'g_SharedPowersets\s*=\s*(?:NULL|0)',startup['upstream/ouroboros/Common/entity/powers.c']) and b'g_numSharedPowersets = eaSize(&g_SharedPowersets)' in startup['upstream/ouroboros/Common/entity/powers_load.c']
 if a.replay:
  raw=a.replay.read_bytes();assert len(raw)==37795 and hashlib.sha256(raw).hexdigest()=='148a4a687d709d2f9ae298bf457e1b067e82b90e70928bd47712ba733fd533ba' and hashlib.sha256(raw[88:]).digest()==raw[56:88]
 names={
 'entities':['coh_original_initial_tail.c','coh_character_outer.c','coh_character_tail.c','coh_character_creation.c','coh_character_initial.c','coh_character_prefix.c','coh_character_ui.c','coh_entities.c'],
 'character-data':['coh_character_data.c'],'replication':['coh_replication.c'],'entity-control':['coh_entity_control.c'],
 'entity-globals':['coh_power_info.c','coh_entity_globals.c','coh_badges.c'],
 'entity-inventory':['coh_inventory.c','coh_invention.c','coh_inventory_phase.c'],
 'entity-team':['coh_team.c'],'entity-superstats':['coh_superstats.c'],'entity-social':['coh_social.c'],
 'entity-attributes':['coh_attrib_monitor.c'],'entity-dynamic':['coh_dynamic.c'],'entity-view':['coh_view.c']}
 sources=[HERE.parent/d/n for d,ns in names.items()for n in ns]+[HERE/'test_original_initial_tail.c'];inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[HERE/'coh_original_initial_tail.h',HERE/'check_original_initial_tail.py',HERE/'client_shared_count_source.py']}
 result={'passed':True,'client_source':source,'startup_source_sha256':startup_pins,'source_sha256':inputs,'modes':{}}
 flags=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage']
 for mode,opts in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=w/mode;cmd=[*flags,*opts,*map(str,sources),'-Wl,--wrap=mmap','-Wl,--wrap=munmap','-lm','-lz','-o',str(binary)];c=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(w/(mode+'-compile.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,(mode,c.stderr[-2000:])
  r=subprocess.run([str(binary)]+([str(a.replay)]if a.replay else[]),capture_output=True,text=True,timeout=180,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'});(w/(mode+'-run.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(mode,r.stderr[-2000:]);result['modes'][mode]=json.loads(r.stdout)
 assert len({json.dumps(v,sort_keys=True)for v in result['modes'].values()})==1
 frames=[];stats={'coh_ent_next_index','coh_ent_create','create','coh_ent_deletes','coh_ent_character_stats','character_stats','stats_leaf','pack','read_n','flag','scalar','require','signed_bits','check_reader','fail','clear_failure'}
 for p in w.glob('release-*.su'):
  for line in p.read_text().splitlines():
   loc,n,kind=line.split('\t');fn=loc.rsplit(':',1)[-1].split('.')[0]
   if 'test_original_'in loc or ('coh_entities.c:'in loc and fn not in stats):continue
   frames.append({'function':loc,'bytes':int(n),'kind':kind})
 total=sum(x['bytes']for x in frames);assert total<=65536,total
 result['memory']={'native_distinct_frame_sum':total,'stack_reserve':65536,'mapped_peak':result['modes']['release']['peak_mapped_bytes'],'retained_test_owner':1000000,'RSS_PSS':None,'external_zlib_rebuilt_with_sanitizers':False,'external_zlib_stack_measured':False,'frames':frames}
 assert inputs=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in inputs};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':result['modes'],'native_frame_sum':total}))
if __name__=='__main__':main()

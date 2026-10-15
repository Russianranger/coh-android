#!/usr/bin/env python3
"""Qualify transactional source-selected multi-actor presentation without GL."""
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
SEQ=HERE.parent
CONT=SEQ/'continuation'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(cmd,env=None):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env)
 if p.returncode:raise ValueError('command failed: '+' '.join(map(str,cmd))+'\n'+p.stdout+p.stderr)
 return p.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--android-clang',type=Path)
 a=p.parse_args();a.output=a.output.resolve();build=a.output.parent/'showcase-build';build.mkdir(parents=True,exist_ok=True)
 cc=os.environ.get('CC') or shutil.which('cc');oracle=module('showcase_original_pose',CONT/'oracle.py')
 provenance=oracle.write(a.source_root,build/'original-playback.c')
 if provenance!=json.loads((CONT/'source-pins.json').read_text()):raise ValueError('original transition source pins differ')
 families=module('showcase_families',CONT/'families.py')
 family=families.qualify(a.source_root,a.corpus,build/'families',cc,a.corpus)
 graph=(build/'families/expanded_graph.h').read_text()
 graph='''/* Generated from the unchanged source subset in
 * continuation/fixtures/expanded_graph.json; missing graph edges stay explicit.
 * Reproduce using showcase/check.py. Neutral clip rigs stay external. */
#ifndef COH_SEQ_SHOWCASE_AUTHORED_GRAPH_H
#define COH_SEQ_SHOWCASE_AUTHORED_GRAPH_H
'''+graph.replace('source_graph','coh_showcase_graph').replace('source_moves','coh_showcase_moves').replace('male_clips','coh_showcase_male_clips').replace('huge_clips','coh_showcase_huge_clips').replace('fem_clips','coh_showcase_fem_clips')+'\n#endif\n'
 graph=re.sub(r'\bS_', 'COH_SHOWCASE_STATE_',graph);graph=re.sub(r'\bM_', 'COH_SHOWCASE_MOVE_',graph)
 if (HERE/'authored_graph.h').read_text()!=graph:raise ValueError('shipping authored source graph differs from independent source regeneration')
 paths=[build/'families'/f'{body}-{clip}.bin' for body in ('male','fem','huge') for clip in ('1_2punch','jump_n_smash','fallout','comb_postjump' if body=='male' else 'combat_postjump')]
 sources=[SEQ/'coh_seq_actor.c',SEQ/'coh_seq_playback.c',SEQ/'coh_sequencer.c',NATIVE/'animation/coh_animation.c']
 results={};commands=[]
 for label,flags in [('host',['-O2']),('asan-ubsan',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])]:
  obj=build/(label+'-actor.o');cmd=[cc,'-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off','-fstack-usage',*flags,'-c',sources[0],'-o',obj];run(cmd);commands.append(list(map(str,cmd)))
  symbols=[x.split()[-1] for x in run(['nm','-u',obj]).splitlines() if x.split()]
  if set(symbols)&{'malloc','calloc','realloc','free','pthread_mutex_lock','fopen','read','write','glFinish','glReadPixels'}:raise ValueError('allocation/blocking import in presentation hot path')
  exe=build/(label+'-actor-test');cmd=[cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-ffp-contract=off',*flags,'-I',SEQ,'-I',build/'families',HERE/'tests/actor_test.c',obj,*sources[1:],build/'original-playback.c',build/'families/original-graph.c','-lm','-o',exe];run(cmd);commands.append(list(map(str,cmd)))
  env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
  begin=time.monotonic();result=json.loads(run([exe,*paths],env));result['host_test_elapsed_seconds']=time.monotonic()-begin
  result['allocation_blocking_symbol_audit']='passed';result['compiler_stack_usage']=obj.with_suffix('.su').read_text().strip().splitlines();results[label]=result
 android={'status':'not run'}
 if a.android_clang:
  objects=[]
  for source in sources[:1]:
   obj=build/(source.stem+'-arm64.o');cmd=[a.android_clang,'-std=c11','-O2','-Wall','-Wextra','-Werror','-c',source,'-o',obj];run(cmd);commands.append(list(map(str,cmd)));objects.append({'module':source.name,'bytes':obj.stat().st_size,'sha256':hashlib.sha256(obj.read_bytes()).hexdigest()})
  android={'status':'ARM64 API26 object built; no Android execution','objects':objects}
 acquisition=json.loads((a.corpus/'acquisition.json').read_text())
 result={'schema':'coh-native-three-body-showcase-v1','gate':33,'starting_commit':'3c5da1d8cd501d778e270d395109d40666fbe37a','source_commit':'0b75ade0c801735e10c5798f641948a45cc50488','data_commit':'d51533ec8e6a9cf726b9214968077a05fdcf19f3','host':results,'source_transition_provenance':provenance,'authentic_family_regeneration':family,'acquisition':acquisition,'android':android,'emulator':'not run for new adapter','physical_thor':'not run','module_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [sources[0],sources[0].with_suffix('.h'),HERE/'tests/actor_test.c',HERE/'authored_graph.h',HERE/'base-pins.json',HERE/'acquire.py']},'limitations':['No renderer, GPU or physical evidence for the new three-body adapter.','No complete source player graph, body morphing, root registration, combat mechanics or authored PlayFx routing.','Typed presentation cue routes are explicit local bindings; original timing/FX dependency closure remains pending.','ASan/UBSan active; LeakSanitizer disabled because executor /proc inspection is unavailable.'],'commands':commands}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':str(a.output),'host':results,'android':android}))
if __name__=='__main__':main()

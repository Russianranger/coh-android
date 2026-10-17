#!/usr/bin/env python3
"""Bounded selected SELF/CREATE raw record; explicit component fixture scope."""
import argparse,hashlib,importlib.util,json,os,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
SOURCES=[HERE/'coh_selected_record.c',HERE/'../entities/coh_entities.c',HERE/'../entities/coh_costume.c',HERE/'../entities/coh_taskforce.c',HERE/'../entities/coh_very_rare_tail.c',HERE/'../entities/coh_teammate_buffs.c',HERE/'../replication/coh_replication.c']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 paths=set(SOURCES+[HERE/'test_selected_record.c',HERE/'check.py',HERE/'fixtures.py',HERE/'oracle_front.h']);paths.update((HERE/'../entities').glob('*.h'));paths.update((HERE/'../entities').glob('*.py'));paths.update((HERE/'../entities').glob('*.inc'));paths.update((HERE/'../entities').glob('*source-pins.json'));paths.update([HERE/'coh_selected_record.h',HERE/'coh_record_kernel.h',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py'])
 hashes={str(p.resolve().relative_to(ROOT)):sha(p) for p in sorted(paths)}
 revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip();spec=importlib.util.spec_from_file_location('selected_fixtures',HERE/'fixtures.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
 with tempfile.TemporaryDirectory(prefix='coh-selected-record-')as name:
  work=Path(name);front,base,buff,tail,original=fixture.build(work);records=[];proof=[]
  for aligned in(0,1):
   for prefix in(range(8)if not aligned else(0,8)):
    raw,bits,begin=fixture.simple_record(front,aligned,prefix);records.append((raw,bits,begin,aligned,0,[0]*10))
    for scenario in range(4):
     raw,bits,begin,p=fixture.full_record(front,base,buff,tail,aligned,prefix,scenario);proof.append(p);b=p['boundaries'];ends=[b[k]for k in('costume_end','power_end','titles_end','ragdoll_end','common_end','taskforce_end','rare_end','tail_end','buff_end')]+[0];records.append((raw,bits,begin,aligned,1,ends))
  wire=work/'fixtures.bin'
  with wire.open('wb')as f:
   f.write(struct.pack('<I',len(records)))
   for raw,bits,begin,aligned,full,ends in records:f.write(struct.pack('<15I',len(raw),bits,begin,aligned,full,*ends));f.write(raw)
  common=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE)]
  modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  checks={};binaries={};stack=[];env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for mode,flags in modes:
   binary=work/mode;run([*common,*flags,*SOURCES,HERE/'test_selected_record.c','-lm','-o',binary]);checks[mode]=json.loads(run([binary,wire],env=env));binaries[mode]=sha(binary)
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t')
    if any(str(source)+':' in location for source in SOURCES):stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(r['bound']not in('static','dynamic,bounded')for r in stack)or sum(r['bytes']for r in stack)>65536:raise ValueError('native stack reserve not supported')
  result={'schema':'coh-selected-record-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'original_components':original,'fixtures':{'sha256':sha(wire),'count':len(records),'component_cases':proof,'whole_original_outer_executed':False},'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'source_worktree_clean':not run(['git','-C',ROOT,'status','--porcelain']).strip(),'full_initial_transaction':False,'whole_entity_list':False,'authentic_dictionary_authority':False,'actor_publication':False,'ack_permitted':False,'real_server_accepted':False,'android_built':False,'thor_accepted':False,'leak_sanitizer':False}
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('input changed')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()

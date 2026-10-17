#!/usr/bin/env python3
"""Atomic groups1..4 composition of independently source-produced fixture bodies."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sys,tempfile
import check_character_initial as initial
import check_teammate_buffs as common
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 provider=a.oracle_root/'native-android/combined-client/diagnostics/character-outer-20261017';sys.path.insert(0,str(provider));import group4_oracle as group4;import qualify_outer as q
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in [provider/n for n in ['group4_oracle.py','qualify_outer.py','independent.py','source-pins.json']]}
 texts={p:q.source(p) for p in q.PATHS}
 if {p:sha(s.encode()) for p,s in texts.items()}!=json.loads((provider/'source-pins.json').read_text()):raise ValueError('source pins changed')
 sources=[HERE/n for n in ['coh_character_creation.c','coh_character_initial.c','coh_character_prefix.c','coh_character_ui.c','coh_entities.c']]+[HERE/'../character-data/coh_character_data.c',HERE/'../replication/coh_replication.c',HERE/'test_character_creation.c']
 inputs=sources+[HERE/n for n in ['coh_character_creation.h','coh_character_initial.h','coh_character_prefix.h','coh_character_ui.h','coh_entities.h','coh_costume.h','coh_taskforce.h','check_character_creation.py','check_character_initial.py','check_teammate_buffs.py','stats_oracle_shim.h','character-initial-source-pins.json']]+[HERE/'../character-data'/n for n in ['coh_character_data.h','check.py','oracle_shim.h','oracle_fixture.c.inc','source-pins.json']]+[HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
 inputs.append(HERE/'run_character_android.py')
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 with tempfile.TemporaryDirectory(prefix='coh-character-creation-') as tmp:
  work=Path(tmp);lib,proof_initial=initial.oracle(work);fixtures_initial=initial.fixtures(lib,work);proof_ui=group4.qualify(texts);lines=[];rows=[]
  if proof_ui['counts']!=[8,9,10,4,720,128,5,128,6,17]:raise ValueError('shape changed')
  for i,f in enumerate(proof_ui['cases']):
   name='ui_'+str(i);raw=bytes.fromhex(f['wire_hex']);lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(str(f[n]) for n in ['begin_bit','end_bit','aligned','scenario'])+',{'+','.join(map(str,f['observed']))+'}}')
  ui_data='\n'.join(lines)+'\nstatic const UiFixture ui_fixtures[]={'+',\n'.join(rows)+'};\n';(work/'ui_fixtures.h').write_text(ui_data)
  checks={};binaries={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
  stats_calls={'coh_ent_character_stats','character_stats','stats_leaf','pack','read_n','flag','require','signed_bits','check_reader','fail','clear_failure'}
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t');function=location.rsplit(':',1)[-1];admitted=any(n+':' in location for n in ['coh_character_creation.c','coh_character_initial.c','coh_character_prefix.c','coh_character_data.c','coh_character_ui.c']) or ('coh_entities.c:' in location and function in stats_calls) or ('coh_replication.c:' in location and function.split('.')[0] in {'valid','coh_rep_read','coh_rep_pack','coh_rep_string'})
    if admitted:stack.append({'function':function,'bytes':int(size),'bound':bound})
  if not stack or any(row['bound'] not in {'static','dynamic,bounded'} for row in stack) or sum(row['bytes'] for row in stack)>16384:raise ValueError('stack reserve not justified')
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_character_creation.h"\nint main(){return coh_character_creation_read(nullptr,nullptr,0,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True)
   for n in ['initial_fixtures.h','ui_fixtures.h']:shutil.copy2(work/n,a.android_output/n)
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_character_creation_test';common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',binary]);r={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'source_sha256':hashes,'fixtures_sha256':{'initial_fixtures.h':fixtures_initial['sha256'],'ui_fixtures.h':sha(ui_data.encode())}};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source/provider changed')
  del proof_ui['cases'];result={'schema':'coh-character-creation-prefix-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'source_stable_before_after':True,'original_initial':proof_initial,'original_ui':proof_ui,'fixture_initial':fixtures_initial,'ui_fixtures_sha256':sha(ui_data.encode()),'fixture_composition':'Synthetic exact bit concatenation of separately source-produced group1..3 and group4 bodies at matching source bit alignment. Not whole sendCharacterToClient execution or authentic capture.','checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'cpp_link_passed':True,'android':android,'whole_character_complete':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()

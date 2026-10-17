#!/usr/bin/env python3
"""Original supergroup producer raw staging qualification."""
from pathlib import Path
import importlib.util,argparse,hashlib,json,os,re,shutil,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'../entities'));import check_teammate_buffs as common
import fixture_builder
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 provider=a.oracle_root/'native-android/combined-client/diagnostics/allents-tail-20261017';sys.path.insert(0,str(provider));import superstats_oracle as oracle;import team_oracle as team
 ppaths=[provider/n for n in ['superstats_oracle.py','superstats-source-pins.json','team_oracle.py','team-source-pins.json','member_oracle.py','inventory_oracle.py']]+[provider.parent/'character-outer-20261017'/n for n in ['qualify_outer.py','independent.py']]
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in ppaths}
 sources=[HERE/'coh_social.c',HERE/'../entity-team/coh_team.c',HERE/'../entity-superstats/coh_superstats.c',HERE/'../replication/coh_replication.c',HERE/'test_social.c']
 inputs=sources+[HERE/'../entity-team/coh_team.h',HERE/'../entity-team/fixture_builder.py',HERE/'../entity-superstats/coh_superstats.h',HERE/'../entity-superstats/fixture_builder.py']+[HERE/n for n in ['coh_social.h','fixture_builder.py','check.py','CONTRACT.md','phase-order-source-pins.json']]+[HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',HERE/'../entities/check_teammate_buffs.py',ROOT/'native-android/tools/protocol_fixture/prepare.py',ROOT/'native-android/include/coh_native_core.h']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip();src=oracle.texts()
 proof=oracle.qualify();team_proof=team.qualify()
 order={n:common.source(n) for n in json.loads((HERE/'phase-order-source-pins.json').read_text())};order_hash={n:sha(t.encode()) for n,t in order.items()}
 if order_hash!=json.loads((HERE/'phase-order-source-pins.json').read_text()):raise ValueError('source order pin mismatch')
 send=order['MapServer/src/entity/entsend.c'];receive=order['Game/src/entity/entrecv.c']
 for text,names in [(send,['team_sendList( pak, player_ent, full_update );','sgroup_sendList( pak, player_ent, full_update);','league_sendList( pak, player_ent, full_update );']),(receive,['receiveTeamList(pak, playerPtr());','receiveSuperStats(pak, playerPtr());','receiveLeagueList(pak, playerPtr());'])]:
  positions=[text.index(n) for n in names]
  if positions!=sorted(positions):raise ValueError('social ordering changed')
 def load_builder(name,path):
  spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 tb=load_builder('team_builder',HERE/'../entity-team/fixture_builder.py');sb=load_builder('sg_builder',HERE/'../entity-superstats/fixture_builder.py')
 if proof['constants']!={'ranks':7,'permission_bytes':4,'allies':10,'permission_enum_count':22}:raise ValueError('source schema changed')
 with tempfile.TemporaryDirectory(prefix='coh-superstats-') as tmp:
  work=Path(tmp);team_header=re.sub(r'\bFixture\b','TeamFixture',tb.build(team_proof)).replace('fixtures','team_fixtures').replace('expected_','team_expected_').replace('wire_','team_wire_');sg_header=re.sub(r'\bFixture\b','SgFixture',sb.build(proof)).replace('fixtures','sg_fixtures').replace('expected_','sg_expected_').replace('wire_','sg_wire_');social_header=fixture_builder.build(team_proof,proof)
  fixture_hashes={}
  for name,contents in [('team_fixtures.h',team_header),('sg_fixtures.h',sg_header),('social_fixtures.h',social_header)]:
   (work/name).write_text(contents);fixture_hashes[name]=sha(contents.encode())
  checks={};binaries={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t');fn=location.rsplit(':',1)[-1];admitted=any(n+':' in location for n in ['coh_social.c','coh_team.c','coh_superstats.c']) or ('coh_replication.c:' in location and fn.split('.')[0] in {'valid','coh_rep_read','coh_rep_pack','coh_rep_string'})
    if admitted:stack.append({'function':fn,'bytes':int(size),'bound':bound})
  if not stack or any(row['bound'] not in {'static','dynamic,bounded'} for row in stack) or sum(row['bytes'] for row in stack)>8192:raise ValueError('stack reserve not justified')
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_social.h"\nint main(){return coh_social_phase_read(nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True)
   for name in fixture_hashes:shutil.copy2(work/name,a.android_output/name)
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);exe=dest/'coh_social_test';common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',exe]);r={'built':True,'executed':False,'binary':exe.name,'binary_sha256':sha(exe.read_bytes()),'fixtures_sha256':fixture_hashes,'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source/provider changed')
  del proof['cases'];del team_proof['cases'];result={'schema':'coh-social-phase-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'original_superstats_producer':proof,'original_team_league':team_proof,'phase_order_original_source_sha256_lf':order_hash,'qualification_scope':'composed exact source fragments; no whole outer original producer/consumer execution','fixtures_sha256':fixture_hashes,'source_stable_before_after':True,'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'cpp_link_passed':True,'android':android,'original_consumer_executed':False,'prior_or_local_state_applied':False,'whole_initial_update_complete':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()

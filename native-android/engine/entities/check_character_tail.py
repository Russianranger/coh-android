#!/usr/bin/env python3
"""Native groups5..6 raw staging against independently supplied original whole oracles."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sys,tempfile,shutil
import check_teammate_buffs as common
import character_tail_fixture as fixture_factory
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 if a.output.exists():ap.error('new output required')
 provider=a.oracle_root/'native-android/combined-client/diagnostics/character-outer-20261017';sys.path.insert(0,str(provider));import group56_oracle as original;import qualify_outer as q
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in [provider/n for n in ['group56_oracle.py','group56_independent.py','group56-source-pins.json','qualify_outer.py','independent.py','source-pins.json','host-proof.json']]}
 texts={p:q.source(p) for p in q.PATHS+original.EXTRA};source_pins={p:sha(s.encode()) for p,s in texts.items()}
 if source_pins!=json.loads((provider/'group56-source-pins.json').read_text()):raise ValueError('original source pins changed')
 sources=[HERE/'coh_character_tail.c',HERE/'../replication/coh_replication.c',HERE/'test_character_tail.c'];inputs=sources+[HERE/'coh_character_tail.h',HERE/'character-tail-admission-pins.json',HERE/'coh_character_options_schema.h',HERE/'character_tail_fixture.py',HERE/'character_tail_test_writer.h',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',HERE/'check_character_tail.py',HERE/'check_teammate_buffs.py',ROOT/'native-android/tools/protocol_fixture/prepare.py',ROOT/'native-android/include/coh_native_core.h'];hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 admission=json.loads((HERE/'character-tail-admission-pins.json').read_text());admission_text={n:common.source(n) for n in admission}
 if admission!={n:sha(t.encode()) for n,t in admission_text.items()}:raise ValueError('local fixed source bound changed')
 import re
 for path,name,value in [('Common/entity/friendCommon.h','MAX_FRIENDS',25),('Common/chatdefs.h','MAX_CHANNELNAME',21),('Common/entity/chatSettings.h','MAX_CHAT_WINDOWS',5),('Common/entity/chatSettings.h','MAX_CHAT_TABS',20),('Common/entity/chatSettings.h','MAX_CHAT_CHANNELS',15),('Common/entity/chatSettings.h','MAX_TAB_NAME_LEN',18),('MapServer/src/entity/keybinds.h','BIND_MAX',256),('Common/entity/attrib_description.h','MAX_COMBAT_STATS',10)]:
  if not re.search(r'^#define\s+'+name+r'\s+'+str(value)+r'\b',admission_text[path],re.M):raise ValueError('fixed source count changed '+name)
 proof=original.qualify(texts)
 widths=json.loads((provider/'host-proof.json').read_text())['constants']['option_widths_in_enum_order']
 import re
 native_widths=list(map(int,re.search(r'\[114\]=\{([^}]+)',(HERE/'coh_character_options_schema.h').read_text()).group(1).split(',')))
 if widths!=native_widths:raise ValueError('native option schema disagrees with pinned original')
 with tempfile.TemporaryDirectory(prefix='coh-character-tail-') as tmp:
  work=Path(tmp);data=fixture_factory.generate(proof);(work/'tail_fixtures.h').write_text(data)
  if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);a.fixtures_output.write_text(data)
  checks={};binaries={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
  for p in work.glob('*.su'):
   stack += [line for line in p.read_text().splitlines() if 'coh_character_tail.c:' in line or 'coh_replication.c:' in line and line.split('\t')[0].rsplit(':',1)[-1].split('.')[0] in {'valid','coh_rep_read','coh_rep_pack'}]
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  frames=[line.split('\t') for line in stack]
  if any(bound not in {'static','dynamic,bounded'} for location,size,bound in frames) or sum(int(size) for location,size,bound in frames)>8192:raise ValueError('stack reserve not justified')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_character_tail.h"\nint main(){return coh_character_tail_read(nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'tail_fixtures.h',a.android_output/'tail_fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_character_tail_test';common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',binary]);r={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':sha(data.encode()),'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r

  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or admission!={n:sha(common.source(n).encode()) for n in admission} or source_pins!={n:sha(q.source(n).encode()) for n in source_pins} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source/provider changed')
  del proof['cases'];result={'schema':'coh-character-tail-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'original_admission_source_sha256_lf':admission,'original_source_sha256_lf':source_pins,'original':proof,'fixtures_sha256':sha(data.encode()),'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'source_stable_before_after':True,'whole_initial_update_complete':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'cpp_link_passed':True,'android':android,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':proof['producer_consumer_cases']}))
if __name__=='__main__':main()

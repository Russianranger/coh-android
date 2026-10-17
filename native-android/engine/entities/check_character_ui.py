#!/usr/bin/env python3
"""Native group4 raw staging against independently supplied original whole oracles."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sys,tempfile,shutil
import check_teammate_buffs as common
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 if a.output.exists():ap.error('new output required')
 provider=a.oracle_root/'native-android/combined-client/diagnostics/character-outer-20261017';sys.path.insert(0,str(provider));import group4_oracle as original;import qualify_outer as q
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in [provider/n for n in ['group4_oracle.py','qualify_outer.py','independent.py','source-pins.json']]}
 texts={p:q.source(p) for p in q.PATHS};source_pins={p:sha(s.encode()) for p,s in texts.items()}
 if source_pins!=json.loads((provider/'source-pins.json').read_text()):raise ValueError('original source pins changed')
 sources=[HERE/'coh_character_ui.c',HERE/'../replication/coh_replication.c',HERE/'test_character_ui.c'];inputs=sources+[HERE/'coh_character_ui.h',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',HERE/'check_character_ui.py',HERE/'check_teammate_buffs.py',ROOT/'native-android/tools/protocol_fixture/prepare.py',ROOT/'native-android/include/coh_native_core.h'];hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 proof=original.qualify(texts)
 if proof['counts']!=[8,9,10,4,720,128,5,128,6,17]:raise ValueError('source shape changed')
 with tempfile.TemporaryDirectory(prefix='coh-character-ui-') as tmp:
  work=Path(tmp);lines=[];rows=[]
  for i,f in enumerate(proof['cases']):
   name='ui_'+str(i);raw=bytes.fromhex(f['wire_hex']);lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(str(f[n]) for n in ['begin_bit','end_bit','aligned','scenario'])+',{'+','.join(map(str,f['observed']))+'}}')
  data='\n'.join(lines)+'\nstatic const UiFixture ui_fixtures[]={'+',\n'.join(rows)+'};\n';(work/'ui_fixtures.h').write_text(data)
  if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);a.fixtures_output.write_text(data)
  checks={};binaries={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
  for p in work.glob('*.su'):
   stack += [line for line in p.read_text().splitlines() if 'coh_character_ui.c:' in line or 'coh_replication.c:' in line and line.split('\t')[0].rsplit(':',1)[-1].split('.')[0] in {'valid','coh_rep_read','coh_rep_pack'}]
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  frames=[line.split('\t') for line in stack]
  if any(bound not in {'static','dynamic,bounded'} for location,size,bound in frames) or sum(int(size) for location,size,bound in frames)>4096:raise ValueError('stack reserve not justified')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_character_ui.h"\nint main(){return coh_character_ui_read(nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'ui_fixtures.h',a.android_output/'ui_fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_character_ui_test';common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',binary]);r={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':sha(data.encode()),'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r

  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source/provider changed')
  del proof['cases'];result={'schema':'coh-character-ui-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'original_source_sha256_lf':source_pins,'original':proof,'fixtures_sha256':sha(data.encode()),'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'source_stable_before_after':True,'whole_character_complete':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'cpp_link_passed':True,'android':android,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':len(rows)}))
if __name__=='__main__':main()

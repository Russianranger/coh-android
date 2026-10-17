#!/usr/bin/env python3
"""Whole original team/league producer-consumer raw staging qualification."""
from pathlib import Path
import ctypes as C,argparse,hashlib,json,os,re,shutil,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'../entities'));import check_teammate_buffs as common
import fixture_builder
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 provider=a.oracle_root/'native-android/combined-client/diagnostics/allents-tail-20261017';sys.path.insert(0,str(provider));import dynamic_wire_oracle as oracle
 ppaths=[provider/n for n in ['dynamic_wire_oracle.py','dynamic-wire-source-pins.json','inventory_oracle.py']]+[provider.parent/'character-outer-20261017'/n for n in ['qualify_outer.py','independent.py']]
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in ppaths}
 sources=[HERE/'coh_dynamic.c',HERE/'../replication/coh_replication.c',HERE/'test_dynamic.c']
 inputs=sources+[HERE/n for n in ['coh_dynamic.h','fixture_builder.py','check.py','CONTRACT.md']]+[HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',HERE/'../entities/check_teammate_buffs.py',ROOT/'native-android/tools/protocol_fixture/prepare.py',ROOT/'native-android/include/coh_native_core.h']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip();src=oracle.texts()
 proof=oracle.qualify()
 zpath=Path(common.run(['cc','-print-file-name=libz.so']).strip()).resolve()
 if not zpath.is_file():raise ValueError('cannot bind linked host zlib')
 zlib_hash=sha(zpath.read_bytes());zlib=C.CDLL(str(zpath));zlib.zlibVersion.restype=C.c_char_p;zlib.zlibCompileFlags.restype=C.c_ulong
 zlib_identity={'library_path':str(zpath),'library_sha256':zlib_hash,'version':zlib.zlibVersion().decode('ascii'),'compile_flags':zlib.zlibCompileFlags(),'library_rebuilt_with_sanitizers':False,'external_library_stack_measured':False,'native_emitted_frames_only':True}
 with tempfile.TemporaryDirectory(prefix='coh-team-') as tmp:
  work=Path(tmp);fixtures=fixture_builder.build(proof);(work/'fixtures.h').write_text(fixtures);fixture_hashes={'fixtures.h':sha(fixtures.encode())};checks={};binaries={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-lz','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
   linked=common.run(['ldd',exe]);match=re.search(r'libz\.so\.1 => (\S+)',linked)
   if not match or Path(match.group(1)).resolve()!=zpath:raise ValueError('executed binary zlib identity mismatch')
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t');fn=location.rsplit(':',1)[-1];admitted='coh_dynamic.c:' in location or ('coh_replication.c:' in location and fn.split('.')[0] in {'valid','coh_rep_read','coh_rep_pack','coh_rep_string'})
    if admitted:stack.append({'function':fn,'bytes':int(size),'bound':bound})
  if not stack or any(row['bound'] not in {'static','dynamic,bounded'} for row in stack) or sum(row['bytes'] for row in stack)>4096:raise ValueError('stack reserve not justified')
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_dynamic.h"\nint main(){return coh_dynamic_diagnostic_read(nullptr,0,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-lz','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'fixtures.h',a.android_output/'fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);exe=dest/'coh_dynamic_test';common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-lz','-o',exe]);r={'built':True,'executed':False,'binary':exe.name,'binary_sha256':sha(exe.read_bytes()),'fixtures_sha256':fixture_hashes,'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r
  if sha(zpath.read_bytes())!=zlib_hash:raise ValueError('host zlib changed')
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source/provider changed')
  del proof['cases'];result={'schema':'coh-dynamic-diagnostic-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'original_dynamic_producer':proof,'fixtures_sha256':fixture_hashes,'source_stable_before_after':True,'zlib_allocation_policy':'fixed256KiBworkspacearena; no system allocations','zlib_linkage':'host system zlib; Android platform zlib when built','host_zlib':zlib_identity,'dependency_stack_and_sanitizer_closure':False,'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'cpp_link_passed':True,'android':android,'world_ownership_authenticated':False,'original_gameplay_consumer_executed':False,'prior_or_local_state_applied':False,'whole_initial_update_complete':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()

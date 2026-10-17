#!/usr/bin/env python3
"""Initial full-create records/list: source fixtures and bounded native owner."""
import argparse,gzip,hashlib,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def original_paths(obj):
 if isinstance(obj,dict):
  for k,v in obj.items():
   if isinstance(k,str)and k.startswith(('MapServer/','Game/','Common/','libs/')):
    p=ROOT/'upstream/ouroboros'/k
    if p.is_file():yield p
   yield from original_paths(v)
 elif isinstance(obj,list):
  for v in obj:yield from original_paths(v)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 selected=HERE/'../selected-record';previous=json.loads((selected/'qualification/20261017/host-outer-proof.json').read_text());paths={ROOT/p for p in previous['source_sha256']};paths.update(p for p in HERE.iterdir()if p.suffix in('.c','.h','.py'));paths.add(selected/'coh_record_kernel.h');order=ROOT/'native-android/combined-client/diagnostics/selected-record-order-20261017';paths.update(order/p for p in('generic_order.py','leaf_oracle.py','leaf_adapters.h','leaf_wrapper.h','leaf-source-pins.json'))
 for p in(HERE/'../entities').glob('*source-pins.json'):paths.update(original_paths(json.loads(p.read_text())))
 paths.update(original_paths(json.loads((order/'leaf-source-pins.json').read_text())));hashes={str(p.resolve().relative_to(ROOT)):digest(p)for p in sorted(paths)}
 old=load('initial_selected_compiler',selected/'check.py');fixture=load('initial_sources',HERE/'fixtures.py');revision=old.run(['git','-C',ROOT,'rev-parse','HEAD']).strip();sources=old.SOURCES+[HERE/'coh_initial_record.c',HERE/'coh_initial_list.c'];checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-initial-record-')as tmp:
  work=Path(tmp);wire,proof=fixture.generate(work)
  if a.fixtures_output:
   if a.fixtures_output.exists():raise ValueError('new fixture output required')
   a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(wire,a.fixtures_output)
  modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for mode,flags in modes:
   binary=work/mode;old.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial.c','-lm','-o',binary]);checks[mode]=json.loads(old.run([binary,wire],env=env));binaries[mode]=digest(binary)
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t')
    if any(str(source)+':'in location for source in sources):stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack)or sum(x['bytes']for x in stack)>98304:raise ValueError('native stack reserve insufficient')
  cpp=work/'header.cpp';cpp.write_text('#include "coh_initial_list.h"\nint main(){return coh_initial_list_read(nullptr,nullptr,nullptr,nullptr,0,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/(str(i)+'.o');old.run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  old.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp']);old.run([work/'cpp'])
  result={'schema':'coh-initial-record-list-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'fixtures':proof,'checks':checks,'binary_sha256':binaries,'native_stack_frames':stack,'cpp_link_passed':True,'original_oracle_sanitized':False,'full_initial_transaction':False,'control_delete_character_globals_composed':False,'authentic_dictionary_generation':False,'actor_publication':False,'ack_permitted':False,'real_server_accepted':False,'android_built':False,'thor_accepted':False,'leak_sanitizer':False}
 if hashes!={str(p.resolve().relative_to(ROOT)):digest(p)for p in sorted(paths)}:raise ValueError('source input changed')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.suffix=='.gz':
  with a.output.open('xb')as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as out:out.write((json.dumps(result,indent=2)+'\n').encode())
 else:
  with a.output.open('x')as out:json.dump(result,out,indent=2);out.write('\n')
 print(json.dumps({'passed':True,'checks':checks,'relocations':proof['child_relocation_equalities']}))
if __name__=='__main__':main()

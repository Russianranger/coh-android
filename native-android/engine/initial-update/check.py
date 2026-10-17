#!/usr/bin/env python3
"""Whole initial syntax diagnostic, authentic ownership deliberately gated."""
import sys
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'../initial-suffix'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--suffix-evidence',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 host=json.loads((a.suffix_evidence/'host.json').read_text());package=json.loads((a.suffix_evidence/'package.json').read_text());fixture_header=a.suffix_evidence/'fixtures.h'
 if sha(fixture_header)!=host['fixtures_sha256']or sha(fixture_header)!=package['fixture_sha256']or sha(fixture_header)!='da69e9a2c715526a9f1c263c9da57b08b659690550ca786741f5446dca8b68cb':raise ValueError('retained suffix identity')
 if any(not(ROOT/k).is_file()or sha(ROOT/k)!=v for k,v in host['source_sha256'].items()):raise ValueError('retained suffix source mismatch')
 initial=json.loads(gzip.decompress((HERE/'../initial-record/qualification/20261017/host-proof.json.gz').read_bytes()))
 if any(not(ROOT/k).is_file()or sha(ROOT/k)!=v for k,v in initial['source_sha256'].items()):raise ValueError('retained list source mismatch')
 pinpath=HERE/'source-pins.json';pins=json.loads(pinpath.read_text())
 if any(sha(ROOT/'upstream/ouroboros'/k)!=v for k,v in pins.items()):raise ValueError('source pins mismatch')
 provider_paths=set(HERE.glob('*.py'))|{HERE/'../selected-record/check.py',HERE/'../initial-suffix/check.py',HERE/'../initial-suffix/fixture_builder.py',HERE/'../entities/check_teammate_buffs.py',HERE/'../entity-control/check.py'}
 provider_hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in provider_paths}
 selected=load('whole_selected_compile',HERE/'../selected-record/check.py');suffix=load('whole_suffix_compile',HERE/'../initial-suffix/check.py');fixture=load('whole_initial_fixtures',HERE/'fixtures.py')
 sources=list(dict.fromkeys(p.resolve()for p in selected.SOURCES+[HERE/'../initial-record/coh_initial_record.c',HERE/'../initial-record/coh_initial_list.c',HERE/'../entity-control/coh_entity_control.c',HERE/'coh_initial_update.c']+[HERE.parent/d/n for d,ns in suffix.SOURCES.items()for n in ns]))
 paths={ROOT/p for p in host['source_sha256']}|{ROOT/p for p in initial['source_sha256']}|set(sources)|set(HERE.glob('*.[ch]'))|set(HERE.glob('*.py'))
 paths.update(p for p in HERE.glob('*.md'));paths.add(pinpath);paths.update(ROOT/'upstream/ouroboros'/k for k in pins);paths.update(p for p in (HERE/'../entity-control').iterdir()if p.suffix in('.c','.h','.py','.inc','.json'));paths.update(provider_paths);hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)};checks={};binaries={};stack=[]
 zpath=Path(run(['cc','-print-file-name=libz.so']).strip()).resolve();zlib=C.CDLL(str(zpath));zlib.zlibVersion.restype=C.c_char_p;zlib.zlibCompileFlags.restype=C.c_ulong
 zidentity={'path':str(zpath),'sha256':sha(zpath),'version':zlib.zlibVersion().decode(),'compile_flags':zlib.zlibCompileFlags(),'rebuilt_with_sanitizers':False,'external_stack_measured':False}
 with tempfile.TemporaryDirectory(prefix='coh-whole-initial-')as tmp:
  work=Path(tmp);wire,proof=fixture.build(work,fixture_header)
  if a.fixtures_output:
   with a.fixtures_output.open('xb')as f:f.write(wire.read_bytes())
  modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for mode,flags in modes:
   binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_update.c','-lm','-lz','-o',binary]);checks[mode]=json.loads(run([binary,wire],env=env));binaries[mode]=sha(binary)
   linked=run(['ldd',binary]);
   if str(zpath)not in linked and str(zpath.parent/'libz.so.1')not in linked:
    import re
    m=re.search(r'libz\.so\.1 => (\S+)',linked)
    if not m or Path(m.group(1)).resolve()!=zpath:raise ValueError('linked zlib changed')
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t')
    if any(str(source)+':'in location for source in sources):stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack)or sum(x['bytes']for x in stack)>131072:raise ValueError('native stack reserve insufficient')
  cpp=work/'header.cpp';cpp.write_text('#include "coh_initial_update.h"\nint main(){return coh_initial_update_diagnostic(nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/(str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-lz','-o',work/'cpp']);run([work/'cpp'])
 if provider_hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in provider_paths}:raise ValueError('provider changed')
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source changed')
 result={'schema':'coh-whole-initial-diagnostic-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'provider_sha256':provider_hashes,'original_source_sha256':pins,'retained_suffix_evidence_sha256':{n:sha(a.suffix_evidence/n)for n in('fixtures.h','host.json','package.json')},'fixtures':proof,'checks':checks,'binary_sha256':binaries,'native_stack_frames':stack,'host_zlib':zidentity,'cpp_link_passed':True,'whole_original_producer_consumer':False,'runtime_dictionary_authority':False,'whole_update_accepted':False,'actor_publication':False,'ack_permitted':False,'android_built':False,'android_executed':False,'real_server_accepted':False,'thor_accepted':False,'leak_sanitizer':False,'dependency_stack_and_sanitizer_closure':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as out:out.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'source_count':len(hashes)}))
if __name__=='__main__':main()

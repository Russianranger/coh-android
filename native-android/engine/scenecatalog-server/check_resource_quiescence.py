#!/usr/bin/env python3
"""Verify pinned original mutation paths and sanitized private no-wait guard."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FUNCTIONS={'Common/seq/anim.c':['initBackgroundLoader','backgroundLoadingThread','heyThreadLoadAGeo','geoRequestBackgroundLoad','geoRequestForegroundLoad','geoCheckThreadLoader','forceGeoLoaderToComplete','geoLoad','geoLoadData','heyThreadLODAModel'],'libs/UtilitiesLib/src/utils/FolderCache.c':['FolderCacheUpdate','FolderCacheEnableCallbacks','FolderCacheSetManualCallbackMode','FolderCacheDoCallbacks'],'Common/seq/tricks.c':['trickLoad','reloadTrickProcessor','reloadTrick','checkTrickReload'],'Common/group/group.c':['groupModelFind'],'MapServer/src/group/groupnetdb.c':['groupLoadMap']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def extract(source,name):
 match=re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)[ \t]*(?://[^\n]*)?\s*\{',source,re.M)
 if not match:raise ValueError('Missing original function '+name)
 begin=source.index('{',match.start());depth=1;at=begin+1
 while depth:depth+=(source[at]=='{')-(source[at]=='}');at+=1
 return source[match.start():at]+'\n'
def source_pins(root):
 spec=importlib.util.spec_from_file_location('qsource',root/'native-android/engine/replication/groups_oracle.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
 files=list(FUNCTIONS)+['MapServer/src/svr/svr_init.c','MapServer/src/svr/svr_tick.c','Common/group/groupfilelib.c'];src={p:o.read_source(root,p) for p in files}
 return {'schema':1,'reference_commit':'bf653dd4ef5372c921b049a76f902a4a921e8c4d','sha256_lf':{p:digest(s) for p,s in src.items()},'functions':{p:{f:digest(extract(src[p],f)) for f in names} for p,names in FUNCTIONS.items()}}
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120,**kw)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
 actual=source_pins(a.source_root.resolve());assert actual==json.loads((HERE/'resource-quiescence-source-pins.json').read_text())
 files=[HERE/n for n in ('source_resource_quiescence.inc','test_resource_quiescence.c','check_resource_quiescence.py','resource-quiescence-source-pins.json')];hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
 modes=[('release',['-O2'])]
 if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={}
 with tempfile.TemporaryDirectory(prefix='coh-source-quiescence-') as temp:
  for mode,flags in modes:
   binary=Path(temp)/mode;run([os.environ.get('CC','cc'),'-std=c99','-Wall','-Wextra','-Werror',*flags,'-I'+str(HERE),HERE/'test_resource_quiescence.c','-o',binary])
   checks[mode]=json.loads(run([binary],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}));binaries[mode]=sha(binary)
 assert all(c==checks['release'] for c in checks.values());assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in files}
 receipt={'schema':'coh-resource-quiescence-source-control-v1','passed':True,'original_source':actual,'guard_source_sha256':hashes,'checks':checks,'binary_sha256':binaries,'actual_windows_compiled':False,'actual_runtime_executed':False,'fixture_only':True,'loader_wait_performed':False,'source_gameplay_mutation':False,'source_guard_policy':'try originalgeo+LOD locks; requireinitialized,notloaderworker,zerooutstanding+readyqueue; startupownercaller sourceprecondition; retainthroughobservation; sameownerrelease','scope':'originalsourcepathandguardcontract; actualcaptureguardreceiptpending','leak_sanitizer':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks['release']['checks'],'output':str(a.output)}))
if __name__=='__main__':main()

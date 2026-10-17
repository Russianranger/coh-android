#!/usr/bin/env python3
"""Qualify only private source staging and WinAPI-shim triple sink; no capture."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120,**kw)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
 files=[HERE/n for n in ('source_resources.inc','source_resource_quiescence.inc','source_resources_sink.inc','test_resources_sink.c','test_stage_resources.py','stage_resources.py','record_resource_compile.py','check_resources_stage.py','source_sink.inc','source_snapshot.inc','stage_snapshot.py','stage_export.py')]
 hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
 tests=run([os.environ.get('PYTHON','python'),'-m','unittest','test_stage_resources','-v'],cwd=HERE)
 modes=[('release',['-O2'])]
 if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 checks={};binaries={}
 with tempfile.TemporaryDirectory(prefix='coh-resource-stage-') as tmp:
  for name,flags in modes:
   binary=Path(tmp)/name
   run([os.environ.get('CC','cc'),'-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-function',*flags,'-I'+str(HERE),HERE/'test_resources_sink.c','-o',binary])
   checks[name]=json.loads(run([binary],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}).stdout);binaries[name]=sha(binary)
 assert all(r==checks['release'] for r in checks.values())
 assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in files}
 result={'schema':'coh-resource-stage-source-qualification-v1','passed':True,'source_sha256':hashes,'stage_tests':7,'stage_test_output':tests.stderr,'sink_checks':checks,'binary_sha256':binaries,'actual_windows_compiled':False,'actual_runtime_executed':False,'winapi_fixture_only':True,'capture_started':False,'catalog_replaced':False,'shipping_changed':False,'source_observer_mutation':False,'client_materials_complete':False,'client_lods_complete':False,'sink_faults':'each create/write/flush/close/rename position; producer failures; delete leftovers; private path collisions; original outputs preserved','leak_sanitizer':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'output':str(a.output),'stage_tests':7,'sink_checks':checks['release']['checks']}))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Qualify new isolated source profile with host stubs; never launch a server."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import stage
SCHEMA='coh-fresh-callback-source-qualification-v1'
MODES={'release':['-O2'],'address':['-O1','-fsanitize=address','-fno-omit-frame-pointer'],
 'undefined':['-O1','-fsanitize=undefined','-fno-sanitize-recover=all']}
FLAGS=['-std=c11','-g','-Wall','-Wextra','-Werror','-pedantic','-pthread']
def digest(raw):return hashlib.sha256(raw).hexdigest()
def run(args):
 root=stage.base.safe_path(args.source_root);output=stage.base.safe_path(args.output)
 stage.base.require(not output.exists(),'FRESH_QUAL_OUTPUT_EXISTS');output.mkdir(mode=0o700)
 # All executed helper/source fixtures are independently pinable; the receipt
 # itself is excluded to avoid a self-reference. No actual PE/native authority.
 sources={p.relative_to(root).as_posix():digest(p.read_bytes()) for p in HERE.iterdir() if p.is_file() and p.name not in ('source-qualification.json',)}
 for n in (stage.FOLDER,*stage.old.PATCHED):sources['upstream/ouroboros/'+n]=digest((root/'upstream/ouroboros'/n).read_bytes())
 for n in ('source_resource_quiescence.inc','stage_groups_capture.py','stage_export.py','stage_groups_boundary.py','stage_resources.py','source_groups_boundary.inc','source_groups_capture_sink.inc'):
  p=HERE.parent/n;sources[p.relative_to(root).as_posix()]=digest(p.read_bytes())
 for p in (*stage.old.boundary.OVERLAYS,Path(stage.old.resources.snapshot.__file__)):
  sources[p.relative_to(root).as_posix()]=digest(p.read_bytes())
 mode_results={}
 compiler=subprocess.run([args.cc,'--version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
 for mode,extra in MODES.items():
  work=output/mode;work.mkdir(mode=0o700)
  for n,raw in stage.overlays(root).items():p=work/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  source=work/'test_profile.c';source.write_bytes((HERE/'test_profile.c').read_bytes());binary=work/'test-profile'
  includes=sum((['-I',str(work/n)] for n in ('libs/UtilitiesLib/src/utils','Common/seq','MapServer/src/group')),[])
  flags=FLAGS+extra;command=[args.cc,*flags,*includes,str(source),'-o',str(binary)]
  built=subprocess.run(command,capture_output=True,text=True,timeout=120);stage.base.require(built.returncode==0,'FRESH_COMPILE_'+mode)
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,env=env)
  (work/'stdout.json').write_bytes(result.stdout.encode());(work/'stderr.txt').write_bytes(result.stderr.encode())
  stage.base.require(result.returncode==0 and not result.stderr,'FRESH_RUN_'+mode)
  value=json.loads(result.stdout);stage.base.require(value['passed'] is True and value['checks']>=1200 and value['scenarios']==36 and value['original_foldercache_executed'] is False and value['real_server'] is False,'FRESH_CONTROLS_'+mode)
  sync=subprocess.run([str(binary),'--sync-fail'],capture_output=True,text=True,timeout=30,env=env)
  (work/'sync-stdout.json').write_bytes(sync.stdout.encode());(work/'sync-stderr.txt').write_bytes(sync.stderr.encode())
  stage.base.require(sync.returncode==0 and not sync.stderr and json.loads(sync.stdout)=={'passed':True,'sync_initialization_refusal':True,'ordinary_fallback_preserved':True},'FRESH_SYNC_'+mode)
  mode_results[mode]={'flags':flags,'controls':value,'sync_initialization_refusal':True,'binary':{'bytes':binary.stat().st_size,'sha256':digest(binary.read_bytes())}}
 suite=unittest.TestSuite()
 for name in ('test_stage','test_admit_compile','test_probe'):
  suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
 result=unittest.TextTestRunner(verbosity=2).run(suite);stage.base.require(result.wasSuccessful(),'FRESH_PYTHON_CONTROLS')
 stage.base.require(sources=={n:digest((root/n).read_bytes()) for n in sources},'FRESH_QUAL_SOURCE_CHANGED')
 receipt={'schema':SCHEMA,'passed':True,'source_sha256':sources,'compiler':compiler,'modes':mode_results,
 'python_test_methods':result.testsRun,'real_host_threads':True,
 'leak_sanitizer_qualified':False,'leak_sanitizer_unavailable_reason':'HOST_PROC_TASK_ACCESS','exact_old_loader_guard_executed_in_host_harness':True,
 'foldercache_bodies_source_shaped_stubs':True,'emitter_win32_io_and_group_hooks_stubs':True,
 'original_foldercache_executed':False,'actual_windows_pe_compiled':False,'runtime_executed':False,
 'source_generation_admitted':False,'world_authority':False}
 raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode()
 with (output/'source-qualification.json').open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 return receipt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cc',default='cc');a=p.parse_args();r=run(a)
 print(json.dumps({'passed':True,'schema':SCHEMA,'python_test_methods':r['python_test_methods'],'runtime_executed':False}))
if __name__=='__main__':main()

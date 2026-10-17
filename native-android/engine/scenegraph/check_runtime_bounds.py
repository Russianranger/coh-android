#!/usr/bin/env python3
"""Bounded bottom-up scheduling tests with explicit immutable graph API fixtures."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args();checks={}
sources=[HERE/'coh_runtime_bounds.c',HERE/'coh_group_bounds.c',HERE/'tests/test_runtime_bounds.c']
with tempfile.TemporaryDirectory(prefix='coh-runtime-bounds-') as temp:
 for mode,flags in [('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
  binary=Path(temp)/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,'-I'+str(HERE),*sources,'-lm','-o',binary]);checks[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
result={'passed':True,'checks':checks,'fixture_graph_api_only':True,'actual_graph_execution':False,'leak_sanitizer':False,'world_authority':False,'source_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*sources,HERE/'coh_runtime_bounds.h',HERE/'runtime_graph.h',HERE/'coh_group_bounds.h',Path(__file__)]}}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

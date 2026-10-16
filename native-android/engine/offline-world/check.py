#!/usr/bin/env python3
"""Qualify additive bounded offline streaming; never rebuild accepted app."""
import argparse, hashlib, importlib.util, json, os, pathlib, subprocess, tempfile
HERE=pathlib.Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
def run(args, env=None):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,env=env,timeout=120)
 if r.returncode:raise RuntimeError(' '.join(map(str,args))+'\n'+r.stdout+r.stderr)
 return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--ndk',type=pathlib.Path);a=p.parse_args()
 spec=importlib.util.spec_from_file_location('zone_preparation',HERE/'tools/prepare_zones.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
 negatives=0
 for path in ('../secret','/abs','a//b','a/../b','a/./b','x:y','a\\b',''):
  try:prep.safe(path)
  except ValueError:negatives+=1
  else:raise AssertionError('unsafe path admitted')
 for text in ('Def x\nGroup y\nEnd\n', 'End\n', 'Def x\nPos NaN 0 0\nEnd\n','Def x\nTintColor 256 0 0 0 0 0\nEnd\n'):
  try:prep.GROUPS.parse_groups(text)
  except ValueError:negatives+=1
  else:raise AssertionError('malformed source admitted')
 # Exercise actual graph traversal rejection; no source/kernel copies.
 class EmptySource:
  directories={}
 source=EmptySource();identity=prep.MATH.local([0,0,0],[0,0,0])
 defs,refs,_=prep.GROUPS.parse_groups('Def a\nGroup a\nEnd\nEnd\nRef a\nEnd\n')
 closure=prep.Closure(source,{})
 try:closure.visit(refs[0],'synthetic.txt',defs,identity)
 except ValueError:negatives+=1
 else:raise AssertionError('source cycle admitted')
 defs,refs,_=prep.GROUPS.parse_groups('Def a\nGroup b\nEnd\nEnd\nRootMod b\nEnd\nRef a\nEnd\n')
 closure=prep.Closure(source,{},max_visits=1)
 try:closure.visit(refs[0],'synthetic.txt',defs,identity)
 except prep.TraversalLimit:negatives+=1
 else:raise AssertionError('source visit budget ignored')
 graph=prep.Closure(source,{}).audit_graph(refs,'synthetic.txt',defs)
 assert graph['top_level_refs']==1 and graph['symbolic_rootmod_occurrences']==1 and graph['unique_reachable_definitions']==2
 sources=[HERE/'test_offline_world.c',HERE/'coh_offline_world.c',NATIVE/'engine/assets/coh_asset_loader.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c']
 common=['-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror','-pedantic','-I',NATIVE/'include']
 with tempfile.TemporaryDirectory(prefix='coh-offline-check-') as temp:
  t=pathlib.Path(temp);exe=t/'test';run(['cc',*common,*sources,'-lz','-lm','-o',exe]);host=json.loads(run([exe]))
  san=t/'san';run(['cc',*common,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',*sources,'-lz','-lm','-o',san]);san_result=json.loads(run([san],{**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}))
  arm={'compiled':False,'executed':False}
  if a.ndk:
   obj=t/'world.o';clang=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
   run([clang,*common,'-fPIC','-c',HERE/'coh_offline_world.c','-o',obj]);b=obj.read_bytes();arm.update(compiled=True,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),api=26)
 report=dict(schema='coh-offline-world-qualification-v1',implemented=True,host_source_qualified=True,host=host,
  source_parser_negative_cases=negatives,reused_source_reference_self_check=prep.MATH.self_check(),
  sanitizers={'asan':True,'ubsan':True,'leak_sanitizer':False,'result':san_result},android_arm64=arm,
  android_emulator_qualified=False,physical_thor_qualified=False,full_zone_qualified=False,
  source_files={str(x.relative_to(NATIVE)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*HERE.glob('*.c'),*HERE.glob('*.h'),HERE/'check.py',HERE/'tools/prepare_zones.py',HERE/'tools/source_math.py']})
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'host':host,'arm64':arm,'python_negatives':negatives}))
if __name__=='__main__':main()

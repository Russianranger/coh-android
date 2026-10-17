#!/usr/bin/env python3
"""Project-source closure controls, including valid poisoned timestamp PYC."""
import argparse,hashlib,importlib.util,json,os,py_compile,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
guard_path=HERE/'coh_checked_sources.py';helpers=[HERE/'inspect_root_partitions.py',ROOT/'native-android/tools/material_fixture/original_delta_check.py',HERE/'coh_source_cpu_oracle.py']
# No ordinary project import occurs in this bootstrap.
frozen={f.resolve():f.read_bytes() for f in [Path(__file__),guard_path,*helpers]}
for f,raw in frozen.items():assert f.read_bytes()==raw
ns={'__name__':'checked_source_bootstrap','__file__':str(guard_path)};exec(compile(frozen[guard_path.resolve()],str(guard_path),'exec',dont_inherit=True),ns);Checked=ns['CheckedSources'];cases=[];poisoned=[]
def refuses(name,fn):
 try:fn()
 except (RuntimeError,ValueError):cases.append(name)
 else:raise AssertionError('source closure refusal missing: '+name)
with tempfile.TemporaryDirectory(prefix='coh-source-cache-controls-') as td:
 temp=Path(td)
 for i,helper in enumerate(helpers):
  path=temp/('helper%d.py'%i);raw=helper.read_bytes();poison=b'CACHE_POISON=True\n';assert len(raw)>len(poison);path.write_bytes(poison+b'#'*(len(raw)-len(poison)));os.utime(path,(1700000000,1700000000));pyc=Path(py_compile.compile(str(path),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP));path.write_bytes(raw);os.utime(path,(1700000000,1700000000))
  # Control confirms the old loader REALLY selects poison with source present.
  spec=importlib.util.spec_from_file_location('old_loader_probe%d'%i,path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);assert old.CACHE_POISON is True
  unrelated=temp/('header%d.h'%i);unrelated.write_bytes(b'int frozen;\n');sources={path:raw,unrelated:unrelated.read_bytes()};checked=Checked(sources);loaded=checked.load('admitted%d'%i,path);assert not hasattr(loaded,'CACHE_POISON') and loaded.__cached__ is None;cases.append('valid_poisoned_pyc_bypassed_'+helper.name);poisoned.append({'helper':str(helper),'source_sha256':hashlib.sha256(raw).hexdigest(),'poison_pyc_sha256':hashlib.sha256(pyc.read_bytes()).hexdigest(),'old_loader_executed_poison':True,'checked_loader_executed_source':True})
  refuses('direct_pyc_refused_'+helper.name,lambda:checked.load('bad',pyc))
  path.write_bytes(raw+b'\n');refuses('changed_helper_before_load_'+helper.name,lambda:checked.load('bad',path));path.write_bytes(raw)
  unrelated.write_bytes(b'int changed;\n');refuses('changed_nonpython_dep_'+helper.name,lambda:checked.load('bad',path));unrelated.write_bytes(sources[unrelated])
  # caller dictionaries and sys.modules cannot replace the copied byte snapshot.
  sources[path]=b'CACHE_POISON=True\n';sys.modules['admitted_again']=old;assert not hasattr(checked.load('admitted_again',path),'CACHE_POISON');del sys.modules['admitted_again'];cases.append('copied_snapshot_and_modulecache_'+helper.name)
 unknown=temp/'unknown.py';unknown.write_text('x=1\n');refuses('unfrozen_project_module',lambda:checked.load('bad',unknown))
 mutator=temp/'mutator.py';mutator.write_text("from pathlib import Path\nPath(__file__).write_text('changed after execution')\n");checked=Checked({mutator:mutator.read_bytes()});refuses('changed_during_execution',lambda:checked.load('mutator',mutator))
for f,raw in frozen.items():assert f.read_bytes()==raw
result={'passed':True,'controls':len(cases),'cases':cases,'poisoned_pyc_controls':poisoned,'source_sha256':{str(f):hashlib.sha256(raw).hexdigest() for f,raw in frozen.items()},'scope':'Project helpers compiled directly from frozen bytes; trusted stdlib/interpreter outside project closure; no native/asset/material authority','native_sweep_reexecuted':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'controls':len(cases),'poisoned_pyc_helpers':len(poisoned)}))

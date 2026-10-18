#!/usr/bin/env python3
"""Evaluate only frozen scene JSON/Git predicates, without hosted/runtime code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

def sha(b):
    return hashlib.sha256(b).hexdigest()

def require(ok, code):
    if not ok:
        raise ValueError(code)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--workflow',type=Path,required=True)
    ap.add_argument('--sha256',required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.root.resolve(strict=True)
    require(not a.output.exists(),'FRESH_OUTPUT')
    workflow_raw=a.workflow.read_bytes();require(sha(workflow_raw)==a.sha256,'FROZEN_WORKFLOW')
    doc=yaml.safe_load(workflow_raw);jobs=doc['jobs'];require(len(jobs)==1,'ONE_JOB')
    steps=next(iter(jobs.values()))['steps'];require(len(steps)==17,'SEVENTEEN_STEPS')
    body=steps[1]['run'].split('\n',1)[1].rsplit('PYINVENTORYINITIALSOURCE',1)[0]
    tree=ast.parse(body);constants={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            name=n.targets[0].id
            if name in {'HELPER','TEST','BINDING','MOCK','HELPER_REVIEW','MAP_METADATA','pins'}:
                constants[name]=ast.literal_eval(n.value)
    pins=constants['pins'];require(isinstance(pins,dict) and 0<len(pins)<512,'BOUNDED_LITERAL_PINS')
    revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    rows=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','-z','HEAD','--',*sorted(pins)])
    blobs={}
    for row in rows.split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,digest=meta.split()
        require(kind==b'blob' and mode in (b'100644',b'100755'),'GIT_MODE')
        blobs[name.decode()]=digest.decode()
    require(set(blobs)==set(pins),'EXACT_TRACKED_PINS')
    for name,digest in pins.items():
        p=root/name;rel=Path(name)
        require(not rel.is_absolute() and rel.as_posix()==name and all(x not in ('','.','..') for x in rel.parts) and '\\' not in name and ':' not in name,'CANONICAL_NAME')
        require(p.resolve()==p and p.is_file() and not p.is_symlink() and 0<p.stat().st_size<8*1024**2,'CANONICAL_FILE')
        b=p.read_bytes()
        require(sha(b)==digest and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blobs[name],'CURRENT_RAW_AND_GIT:'+name)
    start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='binding' for t in n.targets))
    end=next(i for i,n in enumerate(tree.body[start:],start) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='receipt' for t in n.targets))
    fragment=ast.Module(body=tree.body[start:end],type_ignores=[])
    allowed_names={'need','all','len','type','isinstance','list','set'}
    allowed_attributes={('json','loads'),('subprocess','check_output')}
    for n in ast.walk(fragment):
        if isinstance(n,ast.Call):
            f=n.func
            if isinstance(f,ast.Name):require(f.id in allowed_names,'PURE_DATA_NAME')
            elif isinstance(f,ast.Attribute):
                require(f.attr in {'get','read_bytes','decode','strip'} or isinstance(f.value,ast.Name) and (f.value.id,f.attr) in allowed_attributes,'PURE_DATA_ATTRIBUTE')
            else:raise ValueError('PURE_DATA_CALL')
        require(not isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.ClassDef,ast.With,ast.Try)),'PURE_DATA_STATEMENT')
    codes=[]
    def need(ok,code):
        require(ok,code);codes.append(code)
    env={**constants,'root':root,'head':revision,'json':json,'need':need,'subprocess':subprocess}
    # The only subprocess in this fragment is the fixed read-only HEAD check.
    for n in ast.walk(fragment):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess':
            require(n.func.attr=='check_output' and ast.literal_eval(n.args[0])==['git','rev-parse','HEAD'],'ONLY_READ_ONLY_GIT')
    previous=Path.cwd()
    import os
    try:
        os.chdir(root);exec(compile(fragment,'frozen-json-git-data-guards','exec'),env)
    finally:os.chdir(previous)
    require(subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==revision,'HEAD_UNCHANGED')
    result={'schema':'coh-inventory-initial-owner-scene-frozen-data-guards-v1','passed':True,'source_revision':revision,
      'workflow_sha256':sha(workflow_raw),'workflow_bytes':len(workflow_raw),'nonself_raw_Git_pins_verified':len(pins),
      'pure_data_guard_calls':len(codes),'guard_codes':codes,'hosted_environment_guards_executed':False,
      'dynamic_workflow_self_check_deferred_to_actual_CI':True,'project_helpers_imported':False,
      'qualifiers_or_mocks_reexecuted':False,'loader_or_native_or_runtime_executed':False,
      'read_only_Git_subprocesses_executed':True,'root_repository_mutated':False}
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result))

if __name__=='__main__':main()

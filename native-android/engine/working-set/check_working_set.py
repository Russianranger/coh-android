#!/usr/bin/env python3
"""Compile frozen tracked reservation source; do not execute cached helpers."""
import argparse, hashlib, json, os, pathlib, subprocess, tempfile

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=pathlib.Path,required=True)
    ap.add_argument('--output',type=pathlib.Path,required=True)
    a=ap.parse_args();root=a.source_root.resolve();here=pathlib.Path(__file__).resolve().parent
    if a.output.exists():raise ValueError('fresh output required')
    revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip()
    paths=[here/n for n in ('coh_working_set.c','coh_working_set.h','test_working_set.c','check_working_set.py','README.md')]+[root/'native-android/engine/coh_contracts.h']
    frozen={p:p.read_bytes()for p in paths}
    for p,b in frozen.items():
        if subprocess.check_output(['git','-C',str(root),'show',revision+':'+str(p.relative_to(root))])!=b:raise ValueError('uncommitted qualification input '+str(p))
    modes={};frames={}
    def run(cmd):
        r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=90,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout
    with tempfile.TemporaryDirectory(prefix='coh-parent-budget-')as tmp:
        d=pathlib.Path(tmp)/'working-set';d.mkdir()
        for p,b in frozen.items():((d if p.parent==here else d.parent)/p.name).write_bytes(b)
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            obj=d/(mode+'.o');binary=d/mode
            run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,'-fstack-usage','-c',d/'coh_working_set.c','-o',obj])
            run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,d/'test_working_set.c',obj,'-Wl,--wrap=calloc','-Wl,--wrap=free','-o',binary])
            modes[mode]=json.loads(run([binary]))
            rows=[int(line.split('\t')[1])for line in obj.with_suffix('.su').read_text().splitlines()]
            frames[mode]={'maximum_frame':max(rows),'sum_frames':sum(rows)}
            if sum(rows)>16384:raise ValueError('native frame sum exceeds parent reserve')
        # Compile a real C++ caller against the separately compiled C object.
        cpp=d/'caller.cc';cpp.write_text('#include "coh_working_set.h"\nint main(){CohWorkingSet*s=nullptr;return coh_ws_create(COH_WS_MAX,&s)!=COH_OK||coh_ws_destroy(&s)!=COH_OK;}\n')
        run(['c++','-std=c++11','-Wall','-Wextra','-Werror',cpp,d/'release.o','-o',d/'cpp']);run([d/'cpp'])
    if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed')
    if subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip()!=revision:raise ValueError('HEAD changed')
    if not(modes['release']==modes['asan']==modes['ubsan']):raise ValueError('mode results differ')
    proof={'passed':True,'source_revision':revision,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(b).hexdigest()for p,b in frozen.items()},'modes':modes,'stack':frames,'cpp_c_linkage':True,'leak_sanitizer':False,'reservation_only':True,'module_adapters':False,'actual_malloc_census':False,'android_build':False,'android_execution':False,'global_pipeline':False,'world_authority':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'stack':frames}))
if __name__=='__main__':main()

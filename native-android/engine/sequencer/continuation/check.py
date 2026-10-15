#!/usr/bin/env python3
"""Opt-in playback qualification; never modifies accepted animation kernels."""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ENGINE=HERE.parents[1]
NATIVE=ENGINE.parent
sys.path.insert(0,str(HERE))
import oracle
def run(command,env=None):
    r=subprocess.run(list(map(str,command)),capture_output=True,text=True,env=env)
    if r.returncode:raise RuntimeError('command failed: '+' '.join(map(str,command))+'\n'+r.stdout+r.stderr)
    return r.stdout
def source_root(p):
    for root in [p,p/'upstream/ouroboros',p/'ouroboros']:
        if (root/'Common/seq/seqanimate.c').exists():return root
    raise ValueError('original source root unavailable')
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--source-root',type=Path);p.add_argument('--corpus',type=Path)
    p.add_argument('--android-clang',type=Path);p.add_argument('--sanitize',action='store_true');p.add_argument('--no-sanitize',action='store_true')
    p.add_argument('--extra-corpus',type=Path,help='Additional authentic body-specific raw clips')
    p.add_argument('--landing-corpus',type=Path,help='Additional original male landing clip')
    a=p.parse_args();report_path=a.output.resolve()
    if report_path.suffix!='.json':report_path=report_path/'report.json'
    build=report_path.parent/'playback-build';build.mkdir(parents=True,exist_ok=True)
    corpora=[a.corpus] if a.corpus else [Path('/workspace/scratch/552733ac6bdc/coh-next/native-android/tools/directional_fixture/corpus'),Path('/workspace/scratch/cd30b2fc1c9e/recovered-coh-next/native-android/tools/directional_fixture/corpus')]
    corpus=next((v for v in corpora if v and (v/'ready.anim').exists()),None)
    if not corpus:raise ValueError('authentic raw clip corpus unavailable; provide --corpus')
    fixture=build/'prepared';prepare=NATIVE/'tools/directional_fixture/prepare.py'
    run([sys.executable,prepare,'--corpus',corpus,'--output',fixture]);bundle=fixture/'locomotion.bin'
    cc=os.environ.get('CC') or shutil.which('cc');commands=[];results={};provenance=None
    root=source_root(a.source_root.resolve()) if a.source_root else None
    if root:
        provenance=oracle.write(root,build/'original-playback.c')
        pins=HERE/'source-pins.json'
        if pins.exists() and json.loads(pins.read_text())!=provenance:raise ValueError('original per-bone source pins changed; inspect before admission')
    sources=[ENGINE/'sequencer/coh_seq_playback.c',ENGINE/'sequencer/coh_sequencer.c',NATIVE/'character/coh_character.c',NATIVE/'locomotion/coh_locomotion.c']
    for label,flags in [('host',['-O2'])]+([] if a.no_sanitize else [('asan-ubsan',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])]):
        obj=build/(label+'-playback.o');command=[cc,'-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off','-fstack-usage',*flags,'-c',sources[0],'-o',obj]
        run(command);commands.append(list(map(str,command)))
        imports=run(['nm','-u',obj]);forbidden=['malloc','calloc','realloc','free','pthread_mutex_lock','fopen','read','write']
        actual=[line.split()[-1] for line in imports.splitlines() if line.split()]
        if any(x in actual for x in forbidden):raise ValueError('unexpected allocation/blocking module import')
        exe=build/(label+'-playback-test');command=[cc,'-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off',*flags,'-I',ENGINE/'sequencer','-I',NATIVE/'locomotion',HERE/'tests/playback_test.c',obj,*sources[1:],'-lm','-o',exe]
        if root:command+=['-DCOH_PLAYBACK_ORACLE',build/'original-playback.c','-Wno-unused-variable','-Wno-unused-function']
        run(command);commands.append(list(map(str,command)))
        env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
        start=time.monotonic();result=json.loads(run([exe,bundle],env));result['elapsed_seconds']=time.monotonic()-start
        result['heap_blocking_symbol_audit']='passed';results[label]=result
        result['compiler_stack_usage']=obj.with_suffix('.su').read_text().strip().splitlines()
    android={'status':'not compiled; provide --android-clang'}
    clang=a.android_clang
    if not clang:
        ndk=Path('/workspace/scratch/cd30b2fc1c9e/toolchains/android-ndk-r28c/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang')
        if ndk.exists():clang=ndk
    if clang:
        obj=build/'coh_seq_playback-arm64.o';command=[clang,'-std=c11','-O2','-Wall','-Wextra','-Werror','-c',sources[0],'-o',obj]
        run(command);commands.append(list(map(str,command)));android={'status':'ARM64 API26 object compiled; execution not qualified','bytes':obj.stat().st_size,'sha256':hashlib.sha256(obj.read_bytes()).hexdigest()}
    # Preserve existing priority/interruption/selection reference qualification.
    existing=build/'existing-sequencer.json';command=[sys.executable,ENGINE/'sequencer/tools/check.py','--output',existing,'--sanitize']
    if root:command+=['--source-root',root]
    run(command);regression=json.loads(existing.read_text())
    new_families={'status':'not run; provide --extra-corpus and --source-root'}
    extra=a.extra_corpus or Path('/workspace/scratch/bd17f7dd7d03/support-corpus/extra')
    if root and extra.exists():
        import families
        landing=a.landing_corpus or Path('/workspace/scratch/bd17f7dd7d03/support-corpus/extra-landing')
        new_families=families.qualify(root,extra,build/'families',cc,landing if landing.exists() else None)
        if not a.no_sanitize:
            exe=build/'asan-family-test';command=[cc,'-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie','-I',ENGINE/'sequencer',HERE/'tests/families_sanitizer.c',*sources[:2],NATIVE/'animation/coh_animation.c','-lm','-o',exe]
            run(command);commands.append(list(map(str,command)))
            new_families['asan_ubsan']=json.loads(run([exe,*[x['rig_file'] for x in new_families['raw_assets']]],env))
    receipt={'schema':'coh-sequencer-continuation-v1','gate':33,'status':'implemented; host-qualified bounded raw-pose playback extension; full gate pending',
        'host':results,'additional_authentic_families':new_families,'original_source_oracle':bool(root),'provenance':provenance,'android':android,'emulator':'not run','physical_thor':'not run',
        'fixture':json.loads((fixture/'directional-fixture.json').read_text())['assets'],
        'existing_selection_regression':{'host':regression['host'],'original_source_kernel_oracle':regression['original_source_kernel_oracle'],'source_families':regression['source_families']},
        'module_sha256':{str(v.relative_to(ENGINE/'sequencer')):hashlib.sha256(v.read_bytes()).hexdigest() for v in [sources[0],ENGINE/'sequencer/coh_seq_playback.h',HERE/'tests/playback_test.c']},
        'limits':['Additional raw combat/jump-power/reaction/landing poses require --extra-corpus; existing graph has unresolved edges and side effects.','Neutral rigs; body morphing/root-motion/registration/FX not implemented.','Event markers are a local deterministic adapter contract, not original FX timing or network packets.','No Android execution or new Thor acceptance claimed.','LeakSanitizer disabled due to known executor /proc limitation; ASan and UBSan active, module heap imports absent.'],
        'commands':commands}
    report_path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'report':str(report_path),'host':results,'android':android}))
if __name__=='__main__':main()

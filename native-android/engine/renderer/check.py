#!/usr/bin/env python3
"""Gate24 host/source/sanitizer qualification; optional actual Mesa GLES check.
 --output is a JSON file. --source-root is the original repository checkout.
 --corpus points at accepted world.bin/world-fixture.json (no fixture embedded).
 --ndk enables ARM64 build and supplies GLES headers for the Mesa driver test.
"""
import argparse,ctypes as C,hashlib,importlib.util,json,os,random,subprocess,sys,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'tests'))
from bindings import *
from oracle import fragment,vertex

def run(cmd,**kw):
    p=subprocess.run([str(x) for x in cmd],text=True,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(str(cmd)+'\n'+p.stdout+'\n'+p.stderr)
    return p
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source_audit(root):
    pins=json.loads((HERE/'source-pins.json').read_text());records=[]
    for pin in pins:
        p=root/pin['path'];assert p.is_file(),str(p)
        assert sha(p)==pin['sha256'],str(p)+' source drift';records.append(pin)
    return {'passed':True,'original_source_files':records,'original_cg_executed':False}

def scalar_check(lib):
    rng=random.Random(0x242424);fragment_max=vertex_max=0
    for family in range(3):
        for case in range(1000):
            m=lib.coh_renderer_default_material(family)
            for field in ('const0','const1','fog_color','glow_params'):
                setattr(m,field,V4(*(rng.random() for _ in range(4))))
            m.fog_params=V4(0,0,rng.uniform(0,100),rng.uniform(0,.2));m.alpha_ref=rng.random()
            b,d,l=[V4(*(rng.random() for _ in range(4))) for _ in range(3)];fog=F(rng.uniform(0,100)).value;mask=F(rng.random()).value;out=V4();discard=C.c_int()
            assert lib.coh_renderer_fragment(C.byref(m),b,d,mask,l,fog,out,C.byref(discard))==0
            expected,skip=fragment(m,b,d,mask,l,fog);err=max(abs(out[i]-expected[i]) for i in range(4));fragment_max=max(fragment_max,err)
            assert err<3e-5 and bool(discard.value)==skip,(family,case,out[:],expected,err)
    for lighting in range(3):
        for case in range(1000):
            d=Draw();d.material=lib.coh_renderer_default_material(0);d.material.lighting=lighting;d.model_view=identity();d.projection=identity()
            # Nonuniform transform deliberately uses source upper-left 3x3,
            # never a conventional inverse transpose substitution.
            d.model_view[0]=rng.uniform(.2,3);d.model_view[5]=rng.uniform(.2,3);d.model_view[10]=rng.uniform(.2,3)
            d.model_view[12]=rng.uniform(-8,8);d.model_view[13]=rng.uniform(-8,8);d.model_view[14]=rng.uniform(-8,8)
            d.projection[0]=.3;d.projection[5]=.4;d.projection[10]=-.8;d.projection[11]=-.1
            for field in ('diffuse','ambient'):setattr(d.material,field,V4(*(rng.random() for _ in range(4))))
            d.material.specular=V3(.8,1.2,2);d.material.shininess=rng.uniform(1,16)
            v=Vertex(V3(*(rng.uniform(-3,3) for _ in range(3))),V3(*(rng.uniform(-1,1) for _ in range(3))), (F*2)(0,0),(F*2)(1,1),V4(*(rng.random() for _ in range(4))))
            cl=V4();n=V3();li=V4();fo=F()
            assert lib.coh_renderer_vertex(C.byref(d),C.byref(v),cl,n,li,C.byref(fo))==0
            ex=vertex(d,v);actual=[*cl,*n,*li,fo.value];expected=[*ex[0],*ex[1],*ex[2],ex[3]];err=max(abs(a-b) for a,b in zip(actual,expected));vertex_max=max(vertex_max,err);assert err<5e-5,(lighting,case,err)
    return {'passed':True,'fragment_cases':3000,'vertex_cases':3000,'max_fragment_error':fragment_max,'max_vertex_error':vertex_max,'fragment_tolerance':3e-5,'vertex_tolerance':5e-5,'reference':'independent binary64 source equations; no original Cg execution'}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-root',type=Path);ap.add_argument('--corpus',type=Path);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);a=ap.parse_args()
    run([sys.executable,HERE/'embed_shaders.py','--check'])
    result={'working_tree_sources':{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and (p.suffix in ('.c','.h','.py','.vert') or p.name.endswith('.frag.in'))},'base_commit':run(['git','-C',ROOT,'rev-parse','HEAD']).stdout.strip(),'gate':24,'status':'implemented','android_emulator_qualified':False,'physical_thor_qualified':False,'source_audit':source_audit(a.source_root) if a.source_root else {'passed':False,'reason':'--source-root not supplied'},'limits':['low-profile rigid source families only','skinned adapter remains accepted separate module','no HQ/bump/cube/shadow/multi/water/postprocessing','no gameplay FPS claim']}
    with tempfile.TemporaryDirectory(prefix='coh-renderer-') as td:
        temp=Path(td);cc=os.environ.get('CC','cc');flags=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off']
        run([cc,*flags,'-O2',HERE/'coh_renderer.c',HERE/'tests/selftest.c','-lm','-o',temp/'selftest']);result['host_unit']=json.loads(run([temp/'selftest']).stdout)
        run([cc,*flags,'-O2','-shared','-fPIC',HERE/'coh_renderer.c','-lm','-o',temp/'libcoh_renderer.so']);result['source_oracle']=scalar_check(load(temp/'libcoh_renderer.so'))
        if a.sanitize:
            run([cc,*flags,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',HERE/'coh_renderer.c',HERE/'tests/selftest.c','-lm','-o',temp/'sanitizer']);env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1');result['sanitizers']=dict(json.loads(run([temp/'sanitizer'],env=env).stdout),instrumentation='ASan+UBSan',leak_sanitizer={'passed':False,'reason':'LSan unavailable in this traced execution environment (/proc task inspection denied); no leak-sanitizer result claimed'})
        else:result['sanitizers']={'passed':False,'reason':'--sanitize not supplied'}
        ndk=a.ndk or Path(os.environ.get('ANDROID_NDK_HOME',str(ROOT.parent/'toolchains/android-ndk-r28c')))
        if ndk.is_dir():
            tool=ndk/'toolchains/llvm/prebuilt/linux-x86_64';compiler=tool/'bin/aarch64-linux-android26-clang'
            run([compiler,*flags,'-O2','-shared','-fPIC',HERE/'coh_renderer.c',HERE/'coh_renderer_gles.c','-lGLESv3','-lm','-o',temp/'libcoh_renderer_arm64.so'])
            result['android_arm64_build']={'passed':True,'api':26,'ndk':ndk.name,'elf':run(['file',temp/'libcoh_renderer_arm64.so']).stdout.strip(),'sha256':sha(temp/'libcoh_renderer_arm64.so'),'execution':False}
            # Isolate NDK GL headers; never mix Android libc headers into host build.
            inc=temp/'include';inc.mkdir()
            for directory in ('GLES3','KHR'):(inc/directory).symlink_to(tool/'sysroot/usr/include'/directory,target_is_directory=True)
            run([cc,*flags,'-O2','-shared','-fPIC','-I'+str(inc),HERE/'coh_renderer.c',HERE/'coh_renderer_gles.c','-l:libGL.so.1','-lm','-o',temp/'libcoh_renderer_gles.so'])
            from gpu_check import gpu_check
            result['host_gles']=gpu_check(temp/'libcoh_renderer_gles.so',a.corpus)
        else:result['android_arm64_build']=result['host_gles']={'passed':False,'reason':'NDK and GLES headers unavailable; pass --ndk'}
    result['status']='host_qualified' if result['host_unit']['passed'] and result['source_oracle']['passed'] and result['source_audit']['passed'] else 'implemented'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

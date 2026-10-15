#!/usr/bin/env python3
"""Perf observer and exact-skin wrapper qualification. Host CPU timings only."""
import argparse
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
CORE = NATIVE / 'material-probe/app/src/main/cpp/coh_mesh.c'
APK_SHA = '75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'
DEFAULT_APK = Path('/workspace/scratch/cd30b2fc1c9e/recovered-world-qualified/CoH-Native-Session-Client-0.3.0-arm64.apk')
DEFAULT_NDK = Path('/workspace/scratch/cd30b2fc1c9e/toolchains/android-ndk-r28c')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(args, **kwargs):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True, **kwargs)
    require(result.returncode == 0, 'Command failed: ' + ' '.join(map(str,args)) + '\n' + result.stdout[-3000:] + result.stderr[-6000:])
    return result.stdout

def fixtures(apk, out):
    require(digest(apk) == APK_SHA, 'Accepted APK SHA256 differs')
    with zipfile.ZipFile(apk) as z:
        raw = z.read('assets/character.bin')
    import struct
    require(raw[:8] == b'COHCHAR8', 'Accepted character pack identity differs')
    meshes = []
    for i in range(11):
        start, size = struct.unpack_from('<II', raw, 128 + i * 128)
        require(start + size <= len(raw), 'Character mesh span outside accepted pack')
        part = out / ('accepted-part-%02d.mesh' % i)
        part.write_bytes(raw[start:start+size])
        require(part.read_bytes()[:8] == b'COHMESH1', 'Canonical mesh magic differs')
        meshes.append(part)
    return meshes, {'apk_sha256': APK_SHA, 'character_bin_sha256': hashlib.sha256(raw).hexdigest(),
                    'source': 'unchanged authentic Wretch/Huge eleven-part meshes from physically accepted bounded APK; controlled palettes are mocks',
                    'meshes': [{'part': i, 'sha256': digest(p), 'bytes':p.stat().st_size} for i,p in enumerate(meshes)]}

class Mesh(C.Structure):
    _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),
              *((x,C.c_uint32) for x in ('vertex_count','index_count','bone_count','vertices_offset','indices_offset','bone_ids_offset'))]
class Vertex(C.Structure):
    _fields_=[('position',C.c_float*3),('normal',C.c_float*3),('uv',C.c_float*2),('weights',C.c_float*2),('bones',C.c_uint32*2)]
class Skinned(C.Structure):
    _fields_=[('position',C.c_float*3),('normal',C.c_float*3)]

def scalar_reference(library, meshes):
    """Independent scalar Cg formula interpretation, not original shader execution."""
    lib = C.CDLL(str(library))
    lib.coh_mesh_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Mesh)]
    lib.coh_mesh_vertex.argtypes=[C.POINTER(Mesh),C.c_uint32,C.POINTER(Vertex)]
    lib.coh_mesh_skin_vertex.argtypes=[C.POINTER(Vertex),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Skinned)]
    comparisons = 0
    max_error = 0
    for path in meshes:
        raw=path.read_bytes();mem=(C.c_uint8*len(raw)).from_buffer_copy(raw);mesh=Mesh()
        require(lib.coh_mesh_parse(mem,len(raw),C.byref(mesh)) == 0, 'Authentic mesh rejected')
        for pose in range(4):
            values=[]
            for b in range(mesh.bone_count):
                angle=b*.13+pose*.04;c=math.cos(angle);s=math.sin(angle)
                values += [c,-s,0,b*.07+pose*.02,s,c,0,-b*.03,0,0,1,b*.09]
            rows=(C.c_float*len(values))(*values)
            for i in range(mesh.vertex_count):
                v=Vertex();actual=Skinned()
                require(lib.coh_mesh_vertex(C.byref(mesh),i,C.byref(v))==0,'Mesh vertex rejected')
                require(lib.coh_mesh_skin_vertex(C.byref(v),rows,mesh.bone_count,C.byref(actual))==0,'Kernel skin rejected')
                targets=[]
                for is_normal in (False,True):
                    a=v.normal if is_normal else v.position
                    endpoints=[]
                    for bone in v.bones:
                        endpoints.append([sum(float(rows[bone*12+r*4+k])*float(a[k]) for k in range(3)) + (0 if is_normal else float(rows[bone*12+r*4+3])) for r in range(3)])
                    blended=[a+(b-a)*float(v.weights[1]) for a,b in zip(*endpoints)]
                    if is_normal:
                        length=math.sqrt(sum(x*x for x in blended));blended=[x/length for x in blended]
                    targets += blended
                for a,b in zip([*actual.position,*actual.normal],targets):
                    error=abs(a-b);max_error=max(max_error,error);comparisons+=1
                    require(error <= 2e-5+2e-5*abs(b), 'Scalar Cg formula comparison differs')
    return {'status':'passed', 'comparisons':comparisons, 'max_absolute_error':max_error,
            'tolerance':'2e-5 absolute + 2e-5 relative',
            'scope':'independent Python scalar interpretation of pinned Cg blend_bone_positions/blend_bone_normals, authentic meshes, four controlled palettes; no GPU/original application execution'}

def trace_reference(report):
    p=report['perf'];durations=[(i%80+1)*1000000 for i in range(1000)]
    require(p['frame']['samples']==1000 and p['frame']['sum_ns']==sum(durations),'Independent frame trace differs')
    require(p['over_budget']==sum(x>33333333 for x in durations),'Frame budget classification differs')
    require(p['stages']['skinning']['sum_ns']==sum(x//4 for x in durations),'Independent stage trace differs')
    require(p['counters']['draw_calls']==sum(i%11+1 for i in range(1000)),'Draw accounting differs')
    require(p['counters']['upload_bytes']==96000,'Copy accounting differs')
    require(p['counters']['allocations']==0,'Pause admitted a counter sample')
    require(p['dropped_frames']==2 and p['epoch']==5,'Lifecycle boundary accounting differs')
    require(p['gpu']['samples']==1 and p['gpu']['sum_ns']==123456 and p['gpu_stale']==2,'Invalid/stale/disjoint/pre-pause GPU sample admitted')
    for label,values in [('frame',durations),('skinning',[x//4 for x in durations])]:
        histogram=p['frame'] if label=='frame' else p['stages'][label]
        for q in (50,95,99):
            actual=sorted(values)[math.ceil(len(values)*q/100)-1]
            upper=histogram['p%d_upper_ns'%q]
            require(actual<=upper<actual+500000, 'Percentile bound differs')

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--source-root',required=True,type=Path,help='Full checkout including upstream read-only original source')
    a.add_argument('--output',required=True,type=Path)
    a.add_argument('--apk',type=Path,default=DEFAULT_APK)
    a.add_argument('--ndk',type=Path,default=DEFAULT_NDK)
    a.add_argument('--compiler',default='cc')
    args=a.parse_args()
    pins=json.loads((HERE/'source-pins.json').read_text())
    # Upstream pins resolve against full source checkout, native pins against
    # this worktree. This permits additive concurrent changes in the coordinator.
    for relative,expected in pins.items():
        p=(args.source_root if relative.startswith('upstream/') else NATIVE.parent)/relative
        require(p.is_file() and digest(p)==expected,'Read-only source pin differs: '+str(p))
    sources=[HERE/'coh_perf.c',HERE/'coh_skin_cache.c',CORE]
    common=['-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',HERE]
    wraps=['-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free']
    with tempfile.TemporaryDirectory(prefix='coh-perf-check-') as td:
        build=Path(td);meshes,authentic=fixtures(args.apk,build)
        executable=build/'perf-test'
        run([args.compiler,*common,'-O2',HERE/'tests/test_perf.c',*sources,*wraps,'-lm','-o',executable])
        host=[json.loads(run([executable,mesh])) for mesh in meshes]
        for item in host: trace_reference(item);require(item['hot_path_allocations']==0,'Hot path allocated')
        shared=build/'perf-reference.so'
        run([args.compiler,*common,'-O2','-shared','-fPIC',*sources,'-lm','-o',shared])
        oracle=scalar_reference(shared,meshes)
        sanitized=build/'perf-sanitizer'
        run([args.compiler,*common,'-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all',HERE/'tests/test_perf.c',*sources,*wraps,'-lm','-o',sanitized])
        env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
        sanitizer=[]
        for mesh in meshes:
            result=json.loads(run([sanitized,mesh],env=env));sanitizer.append({'part':len(sanitizer),'checks':result['checks'],'status':result['status']})
        tool=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
        require(tool.is_file(),'NDK clang missing: '+str(tool))
        arm=build/'libcoh_perf_arm64.so'
        run([tool,*common,'-O2','-fPIC','-shared',*sources,'-Wl,--no-undefined','-lm','-o',arm])
        elf=run([tool.parent/'llvm-readelf','-h',arm]);require('AArch64' in elf,'Wrong Android ELF architecture')
        report={'schema':1,'status':'host-qualified-and-arm64-built','full_gate_44_45_accepted':False,
                'host':{'machine':platform.machine(),'compiler':run([args.compiler,'--version']).splitlines()[0],
                        'runs':host,'timing_scope':'instrumented host CPU process time, no inference about Thor/full game; cache hit workload repeats the same controlled pose',
                        'total_checks':sum(x['checks'] for x in host)},
                'source_pins':pins,'authentic_assets':authentic,'scalar_source_reference':oracle,
                'independent_trace_reference':'1000 scripted frame intervals, stage durations, percentiles, copied counters and lifecycle boundaries matched Python arithmetic',
                'sanitizers':{'status':'passed','address':True,'undefined':True,'leak_detection':False,
                              'leak_detection_limitation':'Initial LeakSanitizer attempt failed: cannot open /proc/task; LeakSanitizer cannot work under ptrace in execution environment. No code diagnostic was emitted; explicit module malloc/calloc/free balance verified instead.',
                              'module_allocator_balance':'every directly linked module/test allocation released; zero malloc/calloc/realloc calls across warm sample workload',
                              'runs':sanitizer},
                'android_arm64':{'status':'built','api':26,'compiler':run([tool,'--version']).splitlines()[0],
                                 'elf_machine':'AArch64','so_sha256':digest(arm),'so_bytes':arm.stat().st_size,
                                 'scope':'all module sources plus unchanged scalar mesh kernel; no JNI/GL integration/execution'},
                'emulator_qualified':False,'physical_thor_accepted':False,
                'standalone_cmake':{'status':'not-run','reason':'cmake executable unavailable in worker environment; direct host and real NDK compile/link succeeded'},
                'module_hashes':{p.name:digest(p) for p in [*sources[:-1],HERE/'coh_perf.h',HERE/'coh_skin_cache.h',HERE/'tests/test_perf.c',HERE/'check.py']},
                'limitations':['Observer must be connected by coordinator; no accepted hot-path changes.',
                               'No actual GPU query adapter or GPU measurements; asynchronous result admission tested with scripted data only.',
                               'Exact skin cache accelerates identical poses; continuously changing poses miss and incur comparison/copy overhead.',
                               'Cache storage includes duplicate source/palette/output; use small caps and evaluate real workload before enabling.',
                               'No ARM64 execution, emulator or physical acceptance is claimed by this standalone driver.',
                               'cmake executable unavailable; supplied standalone target is not configured here.']}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'status':report['status'],'host_checks':report['host']['total_checks'],
                          'scalar_comparisons':oracle['comparisons'],'sanitizer_runs':len(sanitizer),
                          'android_machine':'AArch64','output':str(args.output)}))

if __name__=='__main__':main()

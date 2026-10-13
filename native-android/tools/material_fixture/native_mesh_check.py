#!/usr/bin/env python3
"""Qualify bounded mesh parser and native source-GPU deformation against real fixtures.

The native deformation routine is a derivative of the source GPU contract. Pose
comparison consumes separately prepared scalar Python golden data; it is not an
independent implementation of the whole original Win32 game.
"""
from __future__ import annotations
import argparse, ctypes as C, hashlib, json, math, os
from pathlib import Path
import shlex, struct, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
CPP=ROOT/'material-probe/app/src/main/cpp'
class Mesh(C.Structure):
    _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),
              *((x,C.c_uint32) for x in ('vertex_count','index_count','bone_count','vertices_offset','indices_offset','bone_ids_offset'))]
class Vertex(C.Structure):
    _fields_=[('position',C.c_float*3),('normal',C.c_float*3),('uv',C.c_float*2),('weights',C.c_float*2),('bones',C.c_uint32*2)]
class Skinned(C.Structure):
    _fields_=[('position',C.c_float*3),('normal',C.c_float*3)]
def h(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(lib):
    lib.coh_mesh_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Mesh)]
    lib.coh_mesh_vertex.argtypes=[C.POINTER(Mesh),C.c_uint32,C.POINTER(Vertex)]
    lib.coh_mesh_index.argtypes=[C.POINTER(Mesh),C.c_uint32,C.POINTER(C.c_uint32)]
    lib.coh_mesh_global_bone.argtypes=[C.POINTER(Mesh),C.c_uint32,C.POINTER(C.c_uint32)]
    lib.coh_mesh_skin_vertex.argtypes=[C.POINTER(Vertex),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Skinned)]
    for name in ('parse','vertex','index','global_bone','skin_vertex'): getattr(lib,'coh_mesh_'+name).restype=C.c_int
    return lib
def parse(lib,blob):
    mem=(C.c_uint8*len(blob)).from_buffer_copy(blob);out=Mesh()
    result=lib.coh_mesh_parse(mem,len(blob),C.byref(out))
    return result,mem,out

def synthetic():
    vertices=b''.join(struct.pack('<10f2I',1,2,3,0,1,0,0,0,.75,.25,0,1) for _ in range(3))
    indices=struct.pack('<3I',0,1,2);boneids=struct.pack('<2I',0,1)
    io=64+len(vertices);bo=io+len(indices);total=bo+len(boneids)
    return b'COHMESH1'+struct.pack('<14I',1,64,3,3,2,48,64,io,bo,total,0,0,0,0)+vertices+indices+boneids

def primitive_tests(lib):
    valid=synthetic();result,mem,mesh=parse(lib,valid);assert result==0
    checks=1
    mutations={
        'magic':(0,b'X'),'version':(8,struct.pack('<I',2)),
        'header_size':(12,struct.pack('<I',63)),'zero_vertices':(16,bytes(4)),
        'vertex_limit':(16,struct.pack('<I',65537)),'indices_not_triangles':(20,struct.pack('<I',2)),
        'bone_limit':(24,struct.pack('<I',16)),'wrong_vertex_stride':(28,struct.pack('<I',44)),
        'vertex_offset_wrap':(32,struct.pack('<I',0xffffffff)),
        'index_overlap':(36,struct.pack('<I',64)),'bone_overlap':(40,struct.pack('<I',64)),
        'total_size':(44,struct.pack('<I',len(valid)-1)),'flags':(48,struct.pack('<I',1)),
        'reserved':(60,struct.pack('<I',1)), 'nan_position':(64,struct.pack('<f',float('nan'))),
        'infinite_normal':(76,struct.pack('<f',float('inf'))),'zero_normal':(76,bytes(12)),
        'nan_uv':(88,struct.pack('<f',float('nan'))),
        'negative_weight':(96,struct.pack('<f',-.25)),'weight_sum':(100,struct.pack('<f',.5)),
        'invalid_local_bone':(104,struct.pack('<I',2)),
        'invalid_triangle_vertex':(mesh.indices_offset,struct.pack('<I',3)),
        'invalid_global_bone':(mesh.bone_ids_offset,struct.pack('<I',99)),
        'duplicate_global_bone':(mesh.bone_ids_offset+4,struct.pack('<I',0))}
    tested=[]
    for name,(offset,value) in mutations.items():
        bad=bytearray(valid);bad[offset:offset+len(value)]=value
        data=(C.c_uint8*len(bad)).from_buffer_copy(bad);untouched=Mesh();C.memset(C.byref(untouched),0x5a,C.sizeof(untouched));before=bytes(untouched)
        assert lib.coh_mesh_parse(data,len(bad),C.byref(untouched))!=0,name
        assert bytes(untouched)==before,name+' output touched'
        tested.append(name);checks+=1
    for size in (0,1,7,63,64,len(valid)-1):
        assert parse(lib,valid[:size])[0]!=0;tested.append('truncated_'+str(size));checks+=1
    assert parse(lib,valid+b'\x00')[0]!=0;tested.append('trailing_byte');checks+=1
    v=Vertex();assert lib.coh_mesh_vertex(C.byref(mesh),0,C.byref(v))==0
    # Hand-computed nontrivial rotation/translation control; includes blended-normal normalization.
    rows=(C.c_float*24)(1,0,0,0,0,1,0,0,0,0,1,0, 0,-1,0,2,1,0,0,0,0,0,1,0)
    output=Skinned();assert lib.coh_mesh_skin_vertex(C.byref(v),rows,2,C.byref(output))==0
    for actual,expected in zip(output.position,(.75,1.75,3)):assert abs(actual-expected)<1e-6
    for actual,expected in zip(output.normal,(-1/math.sqrt(10),3/math.sqrt(10),0)):assert abs(actual-expected)<1e-6
    checks+=1
    for name,palette,count in [('nan_palette',(C.c_float*24)(*[float('nan')]+[0]*23),2),('zero_palette',(C.c_float*24)(*([0]*24)),2),('palette_count',rows,1)]:
        untouched=Skinned();C.memset(C.byref(untouched),0x5a,C.sizeof(untouched));before=bytes(untouched)
        assert lib.coh_mesh_skin_vertex(C.byref(v),palette,count,C.byref(untouched))!=0,name
        assert bytes(untouched)==before
        tested.append(name);checks+=1
    return {'checks':checks,'invalid_cases':tested,'control':'hand-computed two-bone rotated/translated position and normalized normal'}

def real_check(lib,path,poses):
    blob=path.read_bytes();result,mem,m=parse(lib,blob)
    if result:raise ValueError('Real canonical mesh rejected')
    vertices=[];used=set();blended=0
    for i in range(m.vertex_count):
        v=Vertex();assert lib.coh_mesh_vertex(C.byref(m),i,C.byref(v))==0;vertices.append(v)
        for b,w in zip(v.bones,v.weights):
            if w>0:used.add(b)
        if 0<v.weights[1]<1 and v.bones[0]!=v.bones[1]:blended+=1
    if len(used)<2 or not blended:raise ValueError('Real mesh does not exercise genuine two-bone blending')
    global_ids=[]
    for i in range(m.bone_count):
        b=C.c_uint32();assert lib.coh_mesh_global_bone(C.byref(m),i,C.byref(b))==0;global_ids.append(b.value)
    reports=[]
    for label,palette_file,golden_file in poses:
        p=Path(palette_file);g=Path(golden_file);palette=p.read_bytes();golden=g.read_bytes()
        if len(palette)!=m.bone_count*48 or len(golden)!=m.vertex_count*24:raise ValueError('Pose/golden byte size mismatch')
        rows=(C.c_float*(m.bone_count*12))(*struct.unpack('<'+'f'*(m.bone_count*12),palette))
        expected=struct.unpack('<'+'f'*(m.vertex_count*6),golden);max_error=0.;comparisons=0
        for i,v in enumerate(vertices):
            output=Skinned();assert lib.coh_mesh_skin_vertex(C.byref(v),rows,m.bone_count,C.byref(output))==0
            for j,actual in enumerate((*output.position,*output.normal)):
                target=expected[i*6+j]
                if not math.isfinite(target):raise ValueError('Golden contains nonfinite values')
                error=abs(actual-target);max_error=max(max_error,error);comparisons+=1
                if error>2e-5+2e-5*abs(target):raise ValueError(f'Native/Python pose mismatch {label} vertex{i} component{j}: {actual} vs {target}')
        reports.append({'label':label,'palette_sha256':h(p),'python_golden_sha256':h(g),'scalar_comparisons':comparisons,'max_absolute_error':max_error,'tolerance':'2e-5 absolute + 2e-5 relative'})
    if len(reports)<2:raise ValueError('At least bind and nontrivial controlled pose goldens are required')
    return {'mesh_sha256':h(path),'bytes':len(blob),'vertex_count':m.vertex_count,'triangle_count':m.index_count//3,'bone_count':m.bone_count,'global_bone_ids':global_ids,'used_local_bones':sorted(used),'genuine_two_bone_vertices':blended,'poses':reports}

def sanitizer_check(path,compiler,temp):
    # A separate process permits ASan runtime initialization before any Python code.
    program=temp/'mesh_sanitizer.c';exe=temp/'mesh_sanitizer'
    program.write_text(r'''#include "coh_mesh.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void check(const unsigned char *p,size_t n,int must_fail) {
    CohMeshView m;memset(&m,0x5a,sizeof m);CohMeshView before=m;
    int result=coh_mesh_parse(p,n,&m);
    if(must_fail && !result) abort();
    if(result) { if(memcmp(&m,&before,sizeof m)) abort(); return; }
    float palette[COH_MESH_MAX_BONES*12]={0};
    for(unsigned i=0;i<m.bone_count;i++) {palette[i*12]=1;palette[i*12+5]=1;palette[i*12+10]=1;}
    for(unsigned i=0;i<m.vertex_count;i++) {CohMeshVertex v;CohSkinnedVertex out;if(coh_mesh_vertex(&m,i,&v)||coh_mesh_skin_vertex(&v,palette,m.bone_count,&out))abort();}
    for(unsigned i=0;i<m.index_count;i++) {unsigned value;if(coh_mesh_index(&m,i,&value))abort();}
    for(unsigned i=0;i<m.bone_count;i++) {unsigned value;if(coh_mesh_global_bone(&m,i,&value))abort();}
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;FILE *f=fopen(argv[1],"rb");if(!f)return 2;
    if(fseek(f,0,SEEK_END))return 2;long length=ftell(f);if(length<64||length>8*1024*1024)return 2;
    rewind(f);size_t n=(size_t)length;unsigned char *raw=malloc(n);if(!raw||fread(raw,1,n,f)!=n)return 2;fclose(f);
    check(raw,n,0);size_t checks=1;
    for(size_t i=0;i<n;i++) {unsigned char *allocation=malloc(i+1);if(!allocation)abort();unsigned char *p=allocation+1;if(i)memcpy(p,raw,i);check(p,i,1);free(allocation);checks++;}
    unsigned char *allocation=malloc(n+1);if(!allocation)abort();unsigned char *p=allocation+1;memcpy(p,raw,n);
    for(size_t i=0;i<n;i++) {unsigned char old=p[i];p[i]=old^1;check(p,n,0);p[i]=old^255;check(p,n,0);p[i]=old;checks+=2;}
    free(allocation);free(raw);printf("{\"status\":\"passed\",\"checks\":%zu,\"real_input_bytes\":%zu,\"sanitizers\":[\"address\",\"undefined\"],\"scope\":\"exact-allocation truncations and two byte mutations at every real-mesh offset; unaligned inputs, getters and identity skinning\"}\n",checks,n);return 0;
}
''')
    cmd=[*shlex.split(compiler),'-std=c11','-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(CPP),'-o',str(exe),str(program),str(CPP/'coh_mesh.c'),'-lm']
    subprocess.run(cmd,check=True)
    env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    run=subprocess.run([str(exe),str(path.resolve())],capture_output=True,text=True,env=env)
    if run.returncode:raise ValueError(f'Sanitizer harness failed (exit {run.returncode}): '+run.stderr[:12000])
    if run.stderr:raise ValueError('Sanitizer harness emitted unexpected diagnostics: '+run.stderr)
    report=json.loads(run.stdout);report['leak_detection']=False
    return report

def combined_poses(path,fixture,temp):
    raw=path.read_bytes()
    if len(raw)<64 or raw[:8]!=b'COHPOSE1':raise ValueError('Combined pose header magic/size invalid')
    fields=struct.unpack_from('<14I',raw,8)
    version,header,pose_count,vertices,bones,palette_stride,pose_stride,data_offset,total,flags,*reserved=fields
    mesh=fixture.read_bytes()
    if len(mesh)<64:raise ValueError('Canonical mesh header truncated')
    mesh_vertices,_,mesh_bones=struct.unpack_from('<3I',mesh,16)
    expected_stride=bones*48+vertices*24
    if (version,header,pose_count,palette_stride,data_offset,flags)!=(1,64,2,48,64,0) or any(reserved) or vertices!=mesh_vertices or bones!=mesh_bones or not (1<=bones<=15) or not (1<=vertices<=65536) or pose_stride!=expected_stride or total!=len(raw) or total!=64+pose_count*expected_stride:
        raise ValueError('Combined pose header does not match canonical mesh/contract')
    result=[]
    for i,label in enumerate(('bind','controlled')):
        start=64+i*pose_stride;palette=raw[start:start+bones*48];golden=raw[start+bones*48:start+pose_stride]
        p=temp/(label+'.palette.bin');g=temp/(label+'.golden.bin');p.write_bytes(palette);g.write_bytes(golden)
        result.append((label,str(p),str(g)))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',required=True,type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pose',action='append',nargs=3,metavar=('LABEL','PALETTE','PYTHON_GOLDEN'))
    group.add_argument('--poses',type=Path,help='Bounded combined COHPOSE1 palette/Python-golden fixture')
    parser.add_argument('--compiler',default=os.environ.get('CC','cc'))
    parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-mesh-check-') as temp:
        library=Path(temp)/'coh_mesh.so'
        command=[*shlex.split(a.compiler),'-std=c11','-O2','-fPIC','-shared','-Wall','-Wextra','-Werror','-o',str(library),str(CPP/'coh_mesh.c'),'-lm']
        subprocess.run(command,check=True)
        lib=load(C.CDLL(str(library)))
        poses=combined_poses(a.poses,a.fixture,Path(temp)) if a.poses else a.pose
        report={'format':1,'status':'passed','scope':'host-native standalone mesh parser and source-GPU-contract CPU deformation','android_device_execution':False,'production_geo_decoder':False,'native_source_sha256':h(CPP/'coh_mesh.c'),'native_header_sha256':h(CPP/'coh_mesh.h'),'primitive_tests':primitive_tests(lib),'real_asset':real_check(lib,a.fixture,poses),'sanitizer_tests':sanitizer_check(a.fixture,a.compiler,Path(temp))}
    if a.poses:report['combined_pose_sha256']=h(a.poses)
    rendered=json.dumps(report,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered)
    print(rendered,end='')
if __name__=='__main__':main()

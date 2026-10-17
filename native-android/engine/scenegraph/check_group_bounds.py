#!/usr/bin/env python3
"""Compare bounded numerical kernel with unchanged original group bounds functions."""
import argparse, ctypes as C, hashlib, json, os, random, re, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def run(args,**kwargs):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,**kwargs)
    if p.returncode: raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def extract(s,name):
    m=re.search(r'^[^\n;{}]+\b'+name+r'\s*\([^;{}]*\)\s*\{',s,re.M)
    if not m:raise ValueError(name)
    p=s.index('{',m.start())+1;d=1
    while d:d+=(s[p]=='{')-(s[p]=='}');p+=1
    return s[m.start():p]+'\n'
class Bounds(C.Structure):_fields_=[('min',C.c_float*3),('max',C.c_float*3),('mid',C.c_float*3),('radius',C.c_float)]
class Child(C.Structure):_fields_=[('bounds',C.POINTER(Bounds)),('matrix',(C.c_float*3)*4)]
class Input(C.Structure):_fields_=[('model_present',C.c_uint32),('has_volume',C.c_uint32),('pre_alloc',C.c_uint32),('model_min',C.c_float*3),('model_max',C.c_float*3),('box_scale',C.c_float*3),('children',C.POINTER(Child)),('child_count',C.c_size_t),('cancelled',C.c_void_p),('context',C.c_void_p)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    paths=['upstream/ouroboros/Common/group/group.c','upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h']
    texts=[(ROOT/x).read_text().replace('\r\n','\n') for x in paths]
    pins={x:hashlib.sha256(t.encode()).hexdigest() for x,t in zip(paths,texts)}
    if pins!=json.loads((HERE/'bounds-source-pins.json').read_text()):raise ValueError('source pins changed')
    funcs=[extract(texts[1],'mulVecMat4')]+[extract(texts[0],n) for n in ['groupGetBoundsTransformed','groupGetBoundsMinMax','groupSetBounds']]
    with tempfile.TemporaryDirectory(prefix='coh-bounds-') as temp:
        d=Path(temp);code=(HERE/'tests/bounds_oracle_shim.h').read_text()+'\n'+''.join(funcs)+'''
void original(const CohGroupBoundsInput *in,CohGroupBounds*out) {
 GroupDef g={0},defs[8];GroupEnt entries[8];Model model;size_t n;
 g.count=(int)in->child_count;g.entries=entries;g.has_volume=in->has_volume;g.pre_alloc=in->pre_alloc;
 memcpy(g.box_scale,in->box_scale,sizeof(Vec3));
 memcpy(model.min,in->model_min,sizeof(Vec3));memcpy(model.max,in->model_max,sizeof(Vec3));g.model=in->model_present?&model:0;
 for(n=0;n<in->child_count;n++){const CohGroupBounds*b=in->children[n].bounds;
 entries[n].def=b?&defs[n]:0;memcpy(entries[n].mat,in->children[n].matrix,sizeof(Mat4));
 if(b){memset(&defs[n],0,sizeof(GroupDef));memcpy(defs[n].min,b->min,sizeof(Vec3));memcpy(defs[n].max,b->max,sizeof(Vec3));memcpy(defs[n].mid,b->mid,sizeof(Vec3));defs[n].radius=b->radius;}}
 groupSetBounds(&g);memcpy(out->min,g.min,sizeof(Vec3));memcpy(out->max,g.max,sizeof(Vec3));memcpy(out->mid,g.mid,sizeof(Vec3));out->radius=g.radius;
}
'''
        (d/'oracle.c').write_text(code)
        run(['cc','-std=c99','-O0','-ffp-contract=off','-shared','-fPIC','-w','-I'+str(HERE),d/'oracle.c','-lm','-o',d/'oracle.so'])
        lib=C.CDLL(str(d/'oracle.so'));lib.original.argtypes=[C.POINTER(Input),C.POINTER(Bounds)]
        rng=random.Random(401225);fixtures=[]
        for case in range(1024):
            b=Bounds();children=(Child*8)();owned=[];inp=Input();inp.model_present=case%2;inp.has_volume=int(case%7==0);inp.child_count=case%9;inp.children=children
            for j in range(3):inp.model_min[j]=rng.randint(-50,0);inp.model_max[j]=rng.randint(0,100);inp.box_scale[j]=rng.randint(0,100)
            for n in range(inp.child_count):
                b=Bounds();owned.append(b)
                for j in range(3):b.min[j]=rng.randint(-50,0);b.max[j]=rng.randint(0,100);b.mid[j]=(b.min[j]+b.max[j])*.5
                b.radius=rng.randint(0,100)
                if (case+n)%11:children[n].bounds=C.pointer(b)
                for j in range(4):
                    for k in range(3):children[n].matrix[j][k]=rng.randint(-12,12)*.25 if j<3 else rng.randint(-500,500)
            out=Bounds();lib.original(C.byref(inp),C.byref(out))
            def vec(v):return '{'+','.join(float(f).hex()+'f' for f in v)+'}'
            def bounds(v):return '{'+','.join([vec(v.min),vec(v.max),vec(v.mid),float(v.radius).hex()+'f'])+'}'
            cs=','.join('{'+str(int(bool(children[n].bounds)))+','+bounds(owned[n])+','+'{'+','.join(vec(v) for v in children[n].matrix)+'}'+'}' for n in range(inp.child_count)) or '{0,{{0,0,0},{0,0,0},{0,0,0},0},{{0,0,0},{0,0,0},{0,0,0},{0,0,0}}}'
            fixtures.append('{'+','.join([str(inp.model_present),str(inp.has_volume),vec(inp.model_min),vec(inp.model_max),vec(inp.box_scale),str(inp.child_count),'{'+cs+'}',bounds(out)])+'}')
        (d/'fixtures.h').write_text('static const BoundsFixture fixtures[]={'+',\n'.join(fixtures)+'};\n')
        sources=[HERE/'coh_group_bounds.c',HERE/'tests/test_group_bounds.c'];results={}
        modes=[('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else [])
        for mode,flags in modes:
            binary=d/mode
            run(['cc','-std=c99','-Wall','-Wextra','-Werror','-ffp-contract=off',*flags,'-I'+str(HERE),'-I'+str(d),*sources,'-lm','-o',binary])
            results[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
        receipt={'passed':True,'checks':results,'fixtures':len(fixtures),'original_source_sha256_lf':pins,'original_functions_sha256':[hashlib.sha256(f.encode()).hexdigest() for f in funcs],'oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),'source_oracle_sanitized':False,'leak_sanitizer':False,'native_source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*sources,HERE/'coh_group_bounds.h',Path(__file__),HERE/'tests/bounds_oracle_shim.h']},'world_resource_renderer_authority':False,'android_execution':False}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()

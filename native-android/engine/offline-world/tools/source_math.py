"""Compare expanded hierarchy against pinned original and accepted native kernels."""
import ctypes as C, importlib.util, pathlib, subprocess, tempfile
HERE=pathlib.Path(__file__).resolve().parent;NATIVE=HERE.parents[2]
class SourceMath:
    def __init__(self, repo, revision):
        spec=importlib.util.spec_from_file_location('offline_original_math',NATIVE/'tools/world_fixture/original_world_check.py');source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
        self.tmp=tempfile.TemporaryDirectory(prefix='coh-offline-source-math-');t=pathlib.Path(self.tmp.name)
        for name,path in source.PATHS.items():
            raw=subprocess.check_output(['git','-C',str(repo),'show',revision+':upstream/ouroboros/'+path]);(t/name).write_bytes(raw)
        code,self.pins=source.source_code(t)
        code+='''
extern void offline_native_local(const float *,const float *,float *);
extern void offline_native_multiply(const float *,const float *,float *);
unsigned offline_compare(const float parent[12],const float pos[3],const float pyr[3],unsigned root,float out[12]) {
 float a[12],b[12],native[12];unsigned differences=0;
 original_local(pos,pyr,a);offline_native_local(pos,pyr,b);
 if(root){memcpy(out,a,48);memcpy(native,b,48);}
 else {mulMat4Inline((const float(*)[3])parent,(const float(*)[3])a,(float(*)[3])out);offline_native_multiply(parent,b,native);}
 for(unsigned i=0;i<12;i++)differences+=memcmp(out+i,native+i,4)!=0;
 return differences;
}
'''
        (t/'original.c').write_text(code)
        native='#include "'+str(NATIVE/'engine/world/coh_world_stream.c')+'"\nvoid offline_native_local(const float *p,const float *d,float *m){local(p,d,m);}\nvoid offline_native_multiply(const float *a,const float *b,float *o){multiply(a,b,o);}\n'
        (t/'native.c').write_text(native)
        sources=[t/'original.c',t/'native.c',NATIVE/'engine/assets/coh_asset_loader.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c']
        subprocess.run(['cc','-std=c11','-O2','-fPIC','-shared','-ffp-contract=off','-I',str(NATIVE/'include'),*map(str,sources),'-lz','-lm','-o',str(t/'math.so')],check=True,capture_output=True)
        self.lib=C.CDLL(str(t/'math.so'));ptr=C.POINTER(C.c_float);self.lib.offline_compare.argtypes=[ptr,ptr,ptr,C.c_uint,ptr];self.lib.offline_compare.restype=C.c_uint
        self.nodes=0;self.differences=0
    def compose(self,parent,pos,pyr,root=False):
        out=(C.c_float*12)();p=(C.c_float*12)(*parent);xyz=(C.c_float*3)(*pos);degrees=(C.c_float*3)(*pyr)
        self.differences+=self.lib.offline_compare(p,xyz,degrees,int(root),out);self.nodes+=1;return list(out)
    def report(self):
        return dict(passed=self.differences==0,compared_nodes=self.nodes,binary32_components=self.nodes*12,byte_differences=self.differences,source_function_pins=self.pins,
                    scope='Actual expanded geometry hierarchy inputs, unchanged original degrees/YPR/mulMat4Inline vs accepted engine/world kernels; original output retained including signed zero.')

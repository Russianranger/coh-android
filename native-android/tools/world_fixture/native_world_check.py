#!/usr/bin/env python3
"""Qualify bounded native world parsing/math against independent references."""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,math,os,shlex,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
types=module('bounded_world_types',HERE/'_types.py');mesh_api=module('bounded_world_mesh',HERE.parent/'material_fixture/native_mesh_check.py')
class Part(C.Structure):
 _fields_=[('mesh',mesh_api.Mesh),('node',C.c_uint32),('base_texture',C.c_uint32),('dual_texture',C.c_uint32),('flags',C.c_uint32),('mode',C.c_uint32),('const0',C.c_float*4),('const1',C.c_float*4),('diffuse_scale',C.c_float),('ambient_scale',C.c_float),('alpha_ref',C.c_float)]
class Texture(C.Structure):
 _fields_=[('width',C.c_uint32),('height',C.c_uint32),('rgba',C.POINTER(C.c_uint8)),('bytes',C.c_size_t)]
class Scene(C.Structure):
 _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('part_count',C.c_uint32),('texture_count',C.c_uint32),('vertices',C.c_uint32),('indices',C.c_uint32),('inputs',types.Inputs),('parts',Part*16),('textures',Texture*32)]
def require(v,s):
 if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def floats(b,o,n):
 require(0<=o<=len(b) and n<=(len(b)-o)//4,'Reference span invalid');v=struct.unpack_from('<'+'f'*n,b,o);require(all(math.isfinite(x) for x in v),'Reference nonfinite');return list(v)
def stat():return {'components':0,'maximum_absolute_error':0.,'mismatches':0}
def compare(actual,expected,name,stats):
 require(len(actual)==len(expected),name+' count differs')
 for x,y in zip(actual,expected):
  require(math.isfinite(x) and math.isfinite(y),name+' nonfinite');e=abs(x-y);stats['components']+=1;stats['maximum_absolute_error']=max(stats['maximum_absolute_error'],e);require(e<=1e-4,f'{name}: {x} vs {y}; tolerance 1e-4')
def reference(raw):
 require(raw[:8]==b'COHWRF09','Reference magic differs');fields=list(struct.unpack_from('<12I',raw,8));require(fields==[1,64,6,6,512,2,64,352,640,26784,161344,160] and len(raw)==161344 and not any(raw[56:64]),'Reference envelope differs');return fields
def reject(func,cls,raw,mutations,cuts):
 names=[]
 for name,off,data in mutations:
  bad=bytearray(raw);bad[off:off+len(data)]=data;mem=(C.c_uint8*len(bad)).from_buffer_copy(bad);out=cls();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes(out);require(func(mem,len(bad),C.byref(out))!=0,name+' admitted');require(bytes(out)==before,name+' changed output');names.append(name)
 mem=(C.c_uint8*len(raw)).from_buffer_copy(raw)
 for n in sorted(set(cuts)):
  out=cls();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes(out);require(func(mem,n,C.byref(out))!=0,'Truncation admitted');require(bytes(out)==before,'Truncation changed output')
 return {'named_rejections':names,'truncated_lengths_rejected':len(set(cuts)),'failed_outputs_untouched':True}
def malformed(lib,raw,scene):
 mathoff=u32(raw,48);inputs=raw[mathoff:mathoff+520];u=lambda x:struct.pack('<I',x);f=lambda x:struct.pack('<f',x)
 changes=[('input_magic',0,b'X')]+[(f'input_header_{i}',i,u(0xffffffff)) for i in range(8,44,4)]+[('input_reserved',63,b'X')]
 for i in range(6):
  node=64+i*28;changes.append((f'node{i}_parent',node,u(99)))
  for j in range(6):changes.append((f'node{i}_nonfinite{j}',node+4+j*4,f(float('nan'))))
  changes.extend([(f'node{i}_position_limit',node+4,f(32769)),(f'node{i}_degree_limit',node+16,f(361))])
  cam=232+i*48
  for j in range(10):changes.append((f'camera{i}_nonfinite{j}',cam+j*4,f(float('inf'))))
  for name,j,val in [('pos',0,32769.),('degree',3,361.),('fovlo',6,9.),('fovhi',6,121.),('aspectlo',7,.1),('aspecthi',7,9.),('near',8,0.),('far',9,.1),('farhi',9,100001.)]:changes.append((f'camera{i}_{name}_limit',cam+j*4,f(val)))
  changes.extend([(f'camera{i}_flipx',cam+40,u(2)),(f'camera{i}_flipy',cam+44,u(2))])
 out={'inputs':reject(lib.coh_world_parse_inputs,types.Inputs,inputs,changes,range(520))}
 changes=[('world_magic',0,b'X')]+[(f'world_header_{i}',i,u(0xffffffff)) for i in range(8,64,4)]+[('world_reserved',127,b'X')]
 for i in range(scene.part_count):
  part=128+i*96
  for j in (0,4,8,12,16,20,68):changes.append((f'part{i}_field{j}',part+j,u(0xffffffff)))
  for j in range(24,68,4):changes.append((f'part{i}_nonfinite{j}',part+j,f(float('nan'))))
  changes.extend([(f'part{i}_color_limit',part+24,f(1.01)),(f'part{i}_diffuse_limit',part+56,f(2.01)),(f'part{i}_ambient_limit',part+60,f(-.01)),(f'part{i}_alpha_limit',part+64,f(1.01)),(f'part{i}_reserved',part+95,b'X')])
 for i in range(scene.texture_count):
  texture=u32(raw,40)+i*32
  for j in (0,4,8,12):changes.append((f'texture{i}_field{j}',texture+j,u(0xffffffff)))
  changes.append((f'texture{i}_reserved',texture+31,b'X'))
 # Semantic scalar/weight bounds in embedded canonical geometry are explicit.
 for i in range(scene.part_count):
  part=128+i*96;mo=u32(raw,part);vertexoff=u32(raw,mo+32);changes.extend([(f'part{i}_position_nonfinite',mo+vertexoff,f(float('nan'))),(f'part{i}_rigid_weight',mo+vertexoff+32,f(.5))])
 cuts=list(range(128))+[len(raw)-1,mathoff-1,mathoff,mathoff+519]
 for i in range(scene.part_count):off=u32(raw,128+i*96);size=u32(raw,132+i*96);cuts.extend([off-1,off,off+63,off+size-1])
 for i in range(scene.texture_count):table=u32(raw,40)+i*32;off=u32(raw,table);size=u32(raw,table+4);cuts.extend([off-1,off,off+size-1])
 out['scene']=reject(lib.coh_world_scene_parse,Scene,raw,changes,cuts);return out
def sanitizer(a,temp,raw):
 code=r'''#include "coh_world.h"
#include "coh_world_scene.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned u32(const unsigned char*p){return p[0]|p[1]<<8|p[2]<<16|(unsigned)p[3]<<24;}
int main(int argc,char**argv){if(argc!=2)return 1;FILE*f=fopen(argv[1],"rb");if(!f)return 2;fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);if(size<128)return 2;size_t n=(size_t)size;unsigned char*b=malloc(n);if(!b||fread(b,1,n,f)!=n)return 2;fclose(f);unsigned off=u32(b+48);CohWorldInputs inputs;CohWorldScene scene;if(coh_world_scene_parse(b,n,&scene))return 3;unsigned checks=0;
for(size_t t=0;t<520;t++){memset(&inputs,0x5a,sizeof inputs);CohWorldInputs before=inputs;if(!coh_world_parse_inputs(b+off,t,&inputs)||memcmp(&inputs,&before,sizeof inputs))return 4;checks++;}
for(size_t t=0;t<n;t+=4093){memset(&scene,0x5a,sizeof scene);CohWorldScene before=scene;if(!coh_world_scene_parse(b,t,&scene)||memcmp(&scene,&before,sizeof scene))return 5;checks++;}
unsigned seed=0x1390u;for(unsigned i=0;i<3000;i++){seed=seed*1664525u+1013904223u;size_t at=off+seed%520;unsigned char old=b[at];b[at]^=(unsigned char)(1u<<(seed%8));(void)coh_world_parse_inputs(b+off,520,&inputs);b[at]=old;checks++;}
for(unsigned i=0;i<3000;i++){seed=seed*1664525u+1013904223u;size_t at=seed%n;unsigned char old=b[at];b[at]^=(unsigned char)(1u<<(seed%8));(void)coh_world_scene_parse(b,n,&scene);b[at]=old;checks++;}free(b);printf("%u",checks);return 0;}
'''
 cpp=ROOT/'world-probe/app/src/main/cpp';mesh=ROOT/'material-probe/app/src/main/cpp';source=temp/'sanitize.c';source.write_text(code);binary=temp/'sanitize'
 subprocess.run([*shlex.split(a.compiler),'-std=c11','-O1','-g','-ffp-contract=off','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(ROOT/'world'),'-I',str(cpp),'-I',str(mesh),str(source),str(ROOT/'world/coh_world.c'),str(cpp/'coh_world_scene.c'),str(mesh/'coh_mesh.c'),'-lm','-o',str(binary)],check=True)
 path=temp/'world-snapshot.bin';path.write_bytes(raw);result=subprocess.run([str(binary),str(path)],capture_output=True,text=True,timeout=300,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:abort_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'});require(result.returncode==0,result.stderr);return {'passed':True,'checks':int(result.stdout),'address_and_undefined_sanitizers':True,'leak_sanitizer':False,'seed':'0x1390','random_mutations':6000,'immutable_input_snapshot':True,'timeout_seconds':300}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--world',required=True,type=Path);p.add_argument('--reference',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args();raw=a.world.read_bytes();ref=a.reference.read_bytes();reference(ref);cpp=ROOT/'world-probe/app/src/main/cpp';mesh=ROOT/'material-probe/app/src/main/cpp'
 with tempfile.TemporaryDirectory(prefix='coh-world-check-') as directory:
  temp=Path(directory);so=temp/'native.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC','-I',str(ROOT/'world'),'-I',str(mesh),str(ROOT/'world/coh_world.c'),str(cpp/'coh_world_scene.c'),str(mesh/'coh_mesh.c'),'-lm','-o',str(so)],check=True);lib=mesh_api.load(types.configure(C.CDLL(str(so))));lib.coh_world_scene_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Scene)];lib.coh_world_scene_parse.restype=C.c_int;mem=(C.c_uint8*len(raw)).from_buffer_copy(raw);scene=Scene();require(lib.coh_world_scene_parse(mem,len(raw),C.byref(scene))==0,'Native source scene rejected');require((scene.part_count,scene.vertices,scene.indices)==(2,512,564),'Exact source geometry counts differ');stats={k:stat() for k in ('local','world','view','projection','modelview','geometry')};local=(C.c_float*72)();world=(C.c_float*72)();require(lib.coh_world_group_matrices(C.byref(scene.inputs),local,world)==0,'Native source group failed');compare(local,floats(ref,64,72),'Independent source locals',stats['local']);compare(world,floats(ref,352,72),'Independent source group',stats['world']);vertices=[]
  for i in range(scene.part_count):
   part=scene.parts[i];require(part.node==5,'Source-selected root node differs')
   for j in range(part.mesh.vertex_count):v=mesh_api.Vertex();require(lib.coh_mesh_vertex(C.byref(part.mesh),j,C.byref(v))==0,'Canonical static vertex rejected');vertices.append(v)
  wm=(C.c_float*12)(*world[60:72])
  for case in range(6):
   base=640+case*26784;view=(C.c_float*12)();projection=(C.c_float*16)();require(lib.coh_world_camera(C.byref(scene.inputs),case,0,view,projection)==0,'Native camera failed');compare(view,floats(ref,base,12),'Independent source view',stats['view']);compare(projection,floats(ref,base+48,16),'Independent source projection',stats['projection']);eyes=(C.c_float*72)();require(lib.coh_world_group_eye_matrices(C.byref(scene.inputs),view,eyes)==0,'Native source eye hierarchy failed');modelview=(C.c_float*12)(*eyes[-12:]);compare(modelview,floats(ref,base+112,12),'Independent source final modelview',stats['modelview']);actual=[]
   for v in vertices:out=(C.c_float*13)();require(lib.coh_world_vertex(wm,modelview,projection,v.position,v.normal,out)==0,'Actual native world vertex failed');actual.extend(out)
   compare(actual,floats(ref,base+160,6656),'Independent source world/eye/clip/normal',stats['geometry'])
  rejections=malformed(lib,raw,scene);san=sanitizer(a,temp,raw);report={'passed':True,'fixture_sha256':{'world.bin':sha(raw),'world-reference.bin':sha(ref)},'source_group_nodes':6,'camera_cases':6,'source_root_instances':1,'source_geometry_vertices':256,'canonical_vertices':scene.vertices,'triangles':scene.indices//3,'draws':scene.part_count,'textures':scene.texture_count,'stages':stats,'float_tolerance':1e-4,'rejections':rejections,'sanitizer':san};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'stages':stats,'sanitizer':san}))
if __name__=='__main__':main()

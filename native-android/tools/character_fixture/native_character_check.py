#!/usr/bin/env python3
"""Qualify complete native character math against independent source goldens."""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,math,os,shlex,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
actor=module('native_actor_types',HERE/'_types.py');mesh_api=module('native_actor_mesh',HERE.parent/'material_fixture/native_mesh_check.py')
Rig,Pose,Morph=actor.Rig,actor.Pose,actor.Morph
class Part(C.Structure):
 _fields_=[('mesh',mesh_api.Mesh),('socket',C.c_uint32),('base_texture',C.c_uint32),('dual_texture',C.c_uint32),('const0',C.c_float*4),('const1',C.c_float*4),('diffuse_scale',C.c_float),('ambient_scale',C.c_float),('alpha_ref',C.c_float),('flags',C.c_uint32)]
class Texture(C.Structure):
 _fields_=[('width',C.c_uint32),('height',C.c_uint32),('rgba',C.POINTER(C.c_uint8)),('bytes',C.c_size_t)]
class Scene(C.Structure):
 _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('part_count',C.c_uint32),('texture_count',C.c_uint32),('vertices',C.c_uint32),('indices',C.c_uint32),('blended_vertices',C.c_uint32),('parts',Part*11),('textures',Texture*32)]
def require(v,s):
 if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def f32(v):return C.c_float(v).value
def floats(b,o,n):
 require(0<=o<=len(b) and n<=(len(b)-o)//4,'Reference span invalid');out=struct.unpack_from('<'+'f'*n,b,o);require(all(math.isfinite(x) for x in out),'Nonfinite reference');return list(out)
def stat():return {'components':0,'maximum_absolute_error':0.,'mismatches':0}
def compare(actual,expected,label,stats):
 require(len(actual)==len(expected),label+' count differs')
 for x,y in zip(actual,expected):
  require(math.isfinite(x) and math.isfinite(y),label+' nonfinite');error=abs(x-y);stats['components']+=1;stats['maximum_absolute_error']=max(stats['maximum_absolute_error'],error)
  require(error<=1e-4,f'{label}: {x} vs {y}; tolerance1e-4')
def reference(raw):
 require(len(raw)==438216 and raw[:8]==b'COHCHR01','Reference identity differs');fields=struct.unpack_from('<22I',raw,8);expected=[1,128,6,60,11,2626,128,368,608,1328,2048,2096,2448,72628,438216,4,1684,4564,7444,9604,45,32];require(list(fields)==expected and not any(raw[108:128]),'Reference envelope differs')
 require(floats(raw,96,3)==[30.,1.,25.],'Reference source clock differs');ids=list(struct.unpack_from('<60I',raw,128));parents=list(struct.unpack_from('<60i',raw,368));require(ids==sorted(set(ids)) and max(ids)<99 and all(p==-1 or p in ids for p in parents),'Reference hierarchy differs')
 draws=[struct.unpack_from('<8I',raw,2096+i*32) for i in range(11)]
 require(sum(d[1] for d in draws)==45 and sum(d[2] for d in draws)==2626 and all(d[7]==0 for d in draws),'Reference draw counts differ')
 return ids,parents,draws
def mutation_check(lib,raw,func,cls,mutations,truncations):
 names=[]
 for name,offset,data in mutations:
  bad=bytearray(raw);bad[offset:offset+len(data)]=data;mem=(C.c_uint8*len(bad)).from_buffer_copy(bad);out=cls();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes(out)
  require(func(mem,len(bad),C.byref(out))!=0,name+' admitted');require(bytes(out)==before,name+' changed output');names.append(name)
 mem=(C.c_uint8*len(raw)).from_buffer_copy(raw)
 for n in sorted(set(truncations)):
  out=cls();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes(out);require(func(mem,n,C.byref(out))!=0,'Truncation admitted');require(bytes(out)==before,'Truncation changed output')
 return {'named_rejections':names,'truncated_lengths_rejected':len(set(truncations)),'failed_outputs_untouched':True}
def malformed(lib,morph_raw,scene_raw,scene):
 pack=lambda v:struct.pack('<I',v);fp=lambda v:struct.pack('<f',v)
 mutations=[('morph_magic',0,b'X')]
 for o in (8,12,16,20,24,28,32,36,252):mutations.append((f'morph_header_{o}',o,pack(0xffffffff)))
 for o in range(40,252,4):mutations.append((f'morph_nonfinite_{o}',o,fp(float('nan'))))
 for o,v in ((40,0.),(44,-1.),(48,33.),(72,-1.),(76,-1.),(92,-1.),(92,5.),(256+4,0.),(256+16,-1.),(256+8,17.)):mutations.append((f'morph_limit_{o}_{v}',o,fp(v)))
 for id in (0,1,4,73,98):mutations.append((f'morph_order_{id}',256+id*28,pack(99)))
 mutations.append(('morph_original_head_union_inconsistent',168,fp(1.)))
 out={'morph':mutation_check(lib,morph_raw,lib.coh_character_parse_morph,Morph,mutations,range(len(morph_raw)))}
 mutations=[('scene_magic',0,b'X')]
 for o in range(8,60,4):mutations.append((f'scene_header_{o}',o,pack(0xffffffff)))
 mutations.append(('scene_reserved',124,pack(1)))
 for i in range(11):
  base=128+i*128
  for offset in (0,4,8,12,16,20,24,28,76):mutations.append((f'scene_part{i}_field{offset}',base+offset,pack(0xffffffff)))
  for offset in (32,48,64,68,72):mutations.append((f'scene_part{i}_nonfinite{offset}',base+offset,fp(float('nan'))))
 for i in range(scene.texture_count):
  base=1536+i*32
  for offset in (0,4,8,12,16):mutations.append((f'scene_texture{i}_field{offset}',base+offset,pack(0xffffffff)))
 cuts=list(range(128))+[len(scene_raw)-1]
 for i in range(11):
  base=128+i*128;offset,size=u32(scene_raw,base),u32(scene_raw,base+4);cuts+=[offset-1,offset,offset+63,offset+size-1]
 for i in range(scene.texture_count):
  base=1536+i*32;offset,size=u32(scene_raw,base+8),u32(scene_raw,base+12);cuts+=[offset-1,offset,offset+size-1]
 out['scene']=mutation_check(lib,scene_raw,lib.coh_scene_parse,Scene,mutations,cuts)
 return out
def sanitizer(a,temp,scene_raw,morph_raw):
 code=r'''#include "coh_character.h"
#include "coh_scene.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char *read_all(const char*path,size_t*n){FILE*f=fopen(path,"rb");if(!f)return 0;fseek(f,0,SEEK_END);long l=ftell(f);rewind(f);if(l<0){fclose(f);return 0;}unsigned char*p=malloc((size_t)l);if(!p){fclose(f);return 0;}*n=fread(p,1,(size_t)l,f);fclose(f);return p;}
int main(int argc,char**argv){if(argc!=3)return 1;size_t mn,sn;unsigned char*m=read_all(argv[1],&mn),*s=read_all(argv[2],&sn);if(!m||!s)return 2;CohCharacterMorph mo;CohScene scene;if(coh_character_parse_morph(m,mn,&mo)||coh_scene_parse(s,sn,&scene))return 3;unsigned checks=0;
for(size_t n=0;n<mn;n++){memset(&mo,0x5a,sizeof mo);CohCharacterMorph before=mo;if(!coh_character_parse_morph(m,n,&mo)||memcmp(&mo,&before,sizeof mo))return 4;checks++;}
for(size_t n=0;n<sn;n+=4093){memset(&scene,0x5a,sizeof scene);CohScene before=scene;if(!coh_scene_parse(s,n,&scene)||memcmp(&scene,&before,sizeof scene))return 5;checks++;}
unsigned seed=0x13a8u;for(unsigned i=0;i<3000;i++){seed=seed*1664525u+1013904223u;size_t off=seed%mn;unsigned char old=m[off];m[off]^=(unsigned char)(1u<<(seed%8));(void)coh_character_parse_morph(m,mn,&mo);m[off]=old;checks++;}
for(unsigned i=0;i<3000;i++){seed=seed*1664525u+1013904223u;size_t off=seed%sn;unsigned char old=s[off];s[off]^=(unsigned char)(1u<<(seed%8));(void)coh_scene_parse(s,sn,&scene);s[off]=old;checks++;}
free(m);free(s);printf("%u",checks);return 0;}
'''
 cpp=ROOT/'character-probe/app/src/main/cpp';mesh=ROOT/'material-probe/app/src/main/cpp';p=temp/'sanitize.c';p.write_text(code);binary=temp/'sanitize'
 subprocess.run([*shlex.split(a.compiler),'-std=c11','-O1','-g','-ffp-contract=off','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(ROOT/'character'),'-I',str(cpp),'-I',str(mesh),str(p),str(ROOT/'character/coh_character.c'),str(cpp/'coh_scene.c'),str(mesh/'coh_mesh.c'),'-lm','-o',str(binary)],check=True)
 morph_path=temp/'morph.bin';scene_path=temp/'character.bin';morph_path.write_bytes(morph_raw);scene_path.write_bytes(scene_raw)
 result=subprocess.run([str(binary),str(morph_path),str(scene_path)],capture_output=True,text=True,timeout=300,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:abort_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'});require(result.returncode==0,result.stderr);return {'passed':True,'checks':int(result.stdout),'address_and_undefined_sanitizers':True,'leak_sanitizer':False,'seed':'0x13a8','timeout_seconds':300,'immutable_input_snapshots':True}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--character',required=True,type=Path);p.add_argument('--rig',required=True,type=Path);p.add_argument('--morph',required=True,type=Path);p.add_argument('--reference',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args();scene_raw=a.character.read_bytes();rig_raw=a.rig.read_bytes();morph_raw=a.morph.read_bytes();ref=a.reference.read_bytes();ids,parents,draws=reference(ref)
 cpp=ROOT/'character-probe/app/src/main/cpp';mesh_dir=ROOT/'material-probe/app/src/main/cpp'
 with tempfile.TemporaryDirectory(prefix='coh-character-check-') as directory:
  temp=Path(directory);so=temp/'native.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-fPIC','-shared','-I',str(mesh_dir),str(ROOT/'character/coh_character.c'),str(cpp/'coh_scene.c'),str(mesh_dir/'coh_mesh.c'),'-lm','-o',str(so)],check=True);lib=mesh_api.load(actor.configure(C.CDLL(str(so))));lib.coh_scene_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Scene)];lib.coh_scene_parse.restype=C.c_int
  scene_mem=(C.c_uint8*len(scene_raw)).from_buffer_copy(scene_raw);rig_mem=(C.c_uint8*len(rig_raw)).from_buffer_copy(rig_raw);morph_mem=(C.c_uint8*len(morph_raw)).from_buffer_copy(morph_raw);scene=Scene();rig=Rig();morph=Morph();require(lib.coh_scene_parse(scene_mem,len(scene_raw),C.byref(scene))==0,'Complete scene rejected');require(lib.coh_animation_parse(rig_mem,len(rig_raw),C.byref(rig))==0,'Real rig rejected');require(lib.coh_character_parse_morph(morph_mem,len(morph_raw),C.byref(morph))==0,'Real morphology rejected');require(sorted(rig.order[:rig.node_count])==ids and [rig.parent[id] for id in ids]==parents,'Reference/runtime hierarchy differs')
  stats={name:stat() for name in ('bind_translation','bone_scales','actor_root','local','world','scaled_world','palettes','geometry')}
  compare([x for id in ids for x in rig.bind_translation[id]],floats(ref,608,180),'Original bind translations',stats['bind_translation']);compare([x for id in ids for x in morph.bone_scales[id]],floats(ref,1328,180),'Original morphology scales',stats['bone_scales']);compare(list(morph.actor_root_rows),floats(ref,2048,12),'Original actor root',stats['actor_root'])
  palettes=[];mesh_vertices=[]
  for i,part in enumerate(scene.parts):
   draw=draws[i];require(part.socket==draw[0] and part.mesh.bone_count==draw[1] and part.mesh.vertex_count==draw[2],'Scene/reference draw identity differs');bones=[];vertices=[]
   for j in range(part.mesh.bone_count):
    value=C.c_uint32();require(lib.coh_mesh_global_bone(C.byref(part.mesh),j,C.byref(value))==0,'Bone identity read failed');bones.append(value.value)
   for j in range(part.mesh.vertex_count):
    vertex=mesh_api.Vertex();require(lib.coh_mesh_vertex(C.byref(part.mesh),j,C.byref(vertex))==0,'Mesh vertex read failed');vertices.append(vertex)
   palettes.append(bones);mesh_vertices.append(vertices)
  for case in range(6):
   base=2448+case*72628;frame=floats(ref,base,1)[0];pose=Pose();require(lib.coh_character_sample(C.byref(rig),C.byref(morph),frame,C.byref(pose))==0,'Actual native actor sample failed');compare([x for id in ids for x in (*pose.rotation[id],*pose.position[id])],floats(ref,base+4,420),'Original actor locals',stats['local']);compare([x for id in ids for x in pose.world_rows[id]],floats(ref,base+1684,720),'Independent world hierarchy',stats['world']);scaled=[]
   for id in ids:
    for row in range(3):
     scaled.extend([f32(pose.world_rows[id][row*4+c]*morph.bone_scales[id][c]) for c in range(3)]+[pose.world_rows[id][row*4+3]])
   compare(scaled,floats(ref,base+4564,720),'Independent nonpropagating render scales',stats['scaled_world'])
   for i,part in enumerate(scene.parts):
    indices=(C.c_uint32*len(palettes[i]))(*palettes[i]);rows=(C.c_float*(len(palettes[i])*12))();require(lib.coh_character_palette(C.byref(rig),C.byref(morph),C.byref(pose),part.socket,indices,len(palettes[i]),rows)==0,'Actual part palette failed');compare(list(rows),floats(ref,base+draws[i][5],len(rows)),'Independent actual socket palette',stats['palettes']);skinned=[]
    for vertex in mesh_vertices[i]:
     out=mesh_api.Skinned();require(lib.coh_mesh_skin_vertex(C.byref(vertex),rows,len(palettes[i]),C.byref(out))==0,'Actual complete vertex deformation failed');skinned.extend((*out.position,*out.normal))
    compare(skinned,floats(ref,base+draws[i][6],len(skinned)),'Independent complete character geometry',stats['geometry'])
  rejection=malformed(lib,morph_raw,scene_raw,scene);san=sanitizer(a,temp,scene_raw,morph_raw)
  report={'passed':True,'fixture_sha256':{'character.bin':sha(scene_raw),'rig.bin':sha(rig_raw),'morph.bin':sha(morph_raw),'character-reference.bin':sha(ref)},'draws':scene.part_count,'textures':scene.texture_count,'vertices':scene.vertices,'indices':scene.indices,'genuine_blended_vertices':scene.blended_vertices,'hierarchy_bones':rig.node_count,'samples':6,'stages':stats,'float_tolerance':1e-4,'rejections':rejection,'sanitizer':san};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'vertices':scene.vertices,'stages':stats,'sanitizer':san}))
if __name__=='__main__':main()

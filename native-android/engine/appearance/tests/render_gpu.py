"""Bounded host software-GPU proof of new bridge part packets.

This is transform feedback for three genuine source body-part geometries and
matching neutral rigs. It does not render complete actors or original materials.
Readback is confined to this test; production bridge has no GL calls.
"""
import ctypes as C,hashlib,importlib.util,sys
from pathlib import Path
NATIVE=Path(__file__).resolve().parents[3]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
appearance=module('appearance_gpu_abi',NATIVE/'engine/appearance/tests/bindings.py')
animation=module('appearance_gpu_animation',NATIVE/'tools/character_fixture/_types.py')
sys.path.insert(0,str(NATIVE/'engine/renderer/tests'))
import gpu_check as gpu
import bindings as renderer
U=C.c_uint32;Q=C.c_uint64
class Actor(C.Structure):_fields_=[('actor_id',Q),('rig_id',Q),('body_type',U),('appearance_generation',U),('rig_generation',U),('pose_generation',U),('rig',C.c_void_p),('morph',C.c_void_p),('pose',C.c_void_p)]
class Resource(C.Structure):_fields_=[('actor_id',Q),('rig_id',Q),('geometry_id',Q),('appearance_generation',U),('rig_generation',U),('body_type',U),('first_index',U),('index_count',U),('path',C.c_char_p),('model',C.c_char_p),('mesh',C.c_void_p)]
class Material(C.Structure):_fields_=[('material',renderer.Material),('surface_generation',U),('texture',C.c_char_p*2)]
def prove(lib,api,corpus,families):
 assert families,'--gpu requires --families-root'
 animation.configure(lib);lib.coh_renderer_default_material.argtypes=[C.c_int];lib.coh_renderer_default_material.restype=renderer.Material
 lib.coh_asset_geo_model.argtypes=[C.POINTER(api.asset.Geo),U,C.POINTER(api.asset.Model)]
 lib.coh_appearance_render_part.argtypes=[C.POINTER(appearance.Draw),C.POINTER(Resource),C.POINTER(Actor),C.POINTER(Material),U,C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(renderer.Vertex),C.c_size_t,C.POINTER(U),C.c_size_t,C.POINTER(renderer.Draw),C.c_void_p]
 packets=[];identities=[]
 for body,(file_name,family) in enumerate([('v_male_pants.geo','male'),('fem_pants.geo','fem'),('huge_pants.geo','huge')]):
  body_type=[0,1,4][body];raw=(corpus/file_name).read_bytes();source=C.create_string_buffer(raw);needed=C.c_size_t();assert lib.coh_asset_geo_workspace(api.asset.Bytes(C.addressof(source),len(raw)),C.byref(needed))==0
  header=C.create_string_buffer(needed.value);geo=api.asset.Geo();assert lib.coh_asset_geo_open(api.asset.Bytes(C.addressof(source),len(raw)),header,len(header),4096,C.byref(geo))==0
  req=api.Requirements();assert lib.coh_appearance_mesh_requirements(C.byref(geo),0,0,C.byref(req))==0;scratch=C.create_string_buffer(req.workspace_bytes);canonical=C.create_string_buffer(req.canonical_bytes);mesh=api.Mesh();assert lib.coh_appearance_mesh_build(C.byref(geo),0,0,scratch,len(scratch),canonical,len(canonical),C.byref(mesh),None)==0
  model=api.asset.Model();assert lib.coh_asset_geo_model(C.byref(geo),0,C.byref(model))==0
  rig_raw=(families/(family+'-jump_n_smash.bin')).read_bytes();rig_bytes=(C.c_uint8*len(rig_raw)).from_buffer_copy(rig_raw);rig=animation.Rig();assert lib.coh_animation_parse(rig_bytes,len(rig_raw),C.byref(rig))==0
  for step in range(3):
   frame=rig.first_frame+(rig.last_frame-rig.first_frame)*step/2;pose=animation.Pose();assert lib.coh_animation_sample(C.byref(rig),frame,C.byref(pose))==0
   d=appearance.Draw();d.generation=1;d.socket=0;d.geometry_path=('player_library/'+file_name).encode();d.model_name=model.name;d.texture[0].value=b'none';d.texture[1].value=b'none'
   for color in d.color:
    for i in range(4):color[i]=255
   a=Actor(body+1,body+1,body_type,1,1,step+1,C.addressof(rig),None,C.addressof(pose))
   resource=Resource(body+1,body+1,body+1,1,1,body_type,0,mesh.indices,d.geometry_path,model.name,C.addressof(mesh))
   binding=Material(lib.coh_renderer_default_material(1),1,(C.c_char_p*2)(b'none',b'none'))
   vertices=(renderer.Vertex*mesh.vertices)();indices=(U*mesh.indices)();draw=renderer.Draw();identity=renderer.identity()
   assert lib.coh_appearance_render_part(C.byref(d),C.byref(resource),C.byref(a),C.byref(binding),1,identity,identity,vertices,len(vertices),indices,len(indices),C.byref(draw),None)==0
   packets.append({'vertices':vertices,'indices':indices})
  identities.append({'body_type':body_type,'source_file':file_name,'source_geo_sha256':hashlib.sha256(raw).hexdigest(),'source_model':model.name.decode(),'source_rig':family+'-jump_n_smash.bin','source_rig_sha256':hashlib.sha256(rig_raw).hexdigest(),'mesh_vertices':mesh.vertices,'poses':3,'morph':'neutral source rig, no custom body morphology','material':'untextured diagnostic inputs; original costume/material not qualified'})
 e=gpu.EGL()
 try:
  cycles=[]
  for cycle in range(2):
   if cycle:e.recreate_context()
   # Surfaceless GLES still requires a complete draw framebuffer for TF draws.
   # These 1x1 attachments are test-owned and recreated with each context.
   target=e.texture(1,1);fbo=U();e.g.glGenFramebuffers(1,C.byref(fbo));e.g.glBindFramebuffer(0x8d40,fbo);e.g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0);assert e.g.glCheckFramebufferStatus(0x8d40)==0x8cd5;e.g.glBindTexture(0xde1,0)
   try:cycles.append(gpu.tf_check(e,lib,packets))
   finally:e.g.glDeleteFramebuffers(1,C.byref(fbo));e.g.glDeleteTextures(1,C.byref(target))
  return {'run':True,'passed':True,'platform':'Linux host Mesa software GLES, not Android/Adreno','identity':e.identity,'surface_contexts':2,'cycles':cycles,'source_parts':identities,'complete_actor':False,'original_materials':False,'gpu_skinning':False,'scope':'new CPU-skinned part packets consumed by unchanged renderer vertex shader, three source body families at three poses and three lighting modes; transform feedback only','test_only_readback':True,'production_readback':False}
 except AssertionError as error:
  raise AssertionError(f"Host part transform failed; driver={e.identity}, GL error={e.g.glGetError():#x}: {error}") from error
 finally:e.close()

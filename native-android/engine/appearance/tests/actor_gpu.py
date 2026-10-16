"""Complete source-menu Male costume through the unchanged GLES renderer.

Genuine six-piece/eight-draw actor with a source-selected legacy head. This is
an explicit valid neutral custom costume, not a claim of original Clear output,
character creator entitlement validation, or full Gate31 acceptance.
"""
import ctypes as C
import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
api=module('actor_converter_api',HERE.parent/'check_render.py')
bridge=module('actor_render_gpu_api',HERE/'render_gpu.py')
source=module('actor_source_data',HERE/'source_data.py')
a,r=bridge.appearance,bridge.renderer
U,Z=C.c_uint32,C.c_size_t
class Request(C.Structure):
 _fields_=[('draws',C.POINTER(a.Draw)),('resources',C.POINTER(bridge.Resource)),('materials',C.POINTER(bridge.Material)),('source_material_counts',C.POINTER(U)),('count',U),('complete',U),('actor',bridge.Actor),('surface',U),('cancel',a.Cancel)]
class Diagnostics(C.Structure):
 _fields_=[('rendered_parts',U),('cleared_parts',U),('vertices',U),('indices',U),('vertex_bytes',Z),('index_bytes',Z)]
class Workspace(C.Structure):_fields_=[('draws',r.Draw*120)]
def sha(raw):return hashlib.sha256(raw).hexdigest()

def prepare(library,assets,source_root,rig_path,output):
 lib=r.load(library,gles=hasattr(C.CDLL(str(library)),'coh_renderer_gles_create'));api.configure(lib);a.configure(lib);bridge.animation.configure(lib)
 lib.coh_asset_geo_model.argtypes=[C.POINTER(api.asset.Geo),U,C.POINTER(api.asset.Model)]
 lib.coh_appearance_geo_model.argtypes=[C.POINTER(api.asset.Geo),C.POINTER(a.Draw),U,C.POINTER(U),C.POINTER(api.asset.Model)]
 lib.coh_asset_texture.argtypes=[api.asset.Bytes,C.POINTER(api.asset.Texture)]
 lib.coh_asset_texture_rgba.argtypes=[C.POINTER(api.asset.Texture),U,C.c_void_p,Z]
 lib.coh_appearance_actor_requirements.argtypes=[C.POINTER(Request),C.POINTER(Diagnostics)]
 lib.coh_appearance_actor_render.argtypes=[C.POINTER(Request),C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(Workspace),C.POINTER(r.Vertex),Z,C.POINTER(U),Z,C.POINTER(r.Draw),Z,C.POINTER(Z),C.POINTER(Diagnostics)]
 pins=json.loads((HERE.parent/'actor-pins.json').read_text())
 for name,digest in pins['source_files'].items():assert sha((source_root/name).read_bytes())==digest,name
 # Read actual creator Info blocks. Optional patterns explicitly select the
 # source-authored "none" mask; this is the engine white binding, not a missing
 # texture replacement. Legacy head is explicitly selected, never substituted.
 root='upstream/i24/data/menu/costume/localized/'
 choices=[('Pants','male/all/lower/menu_tight.ctm'),('Chest','male/all/upper/menu_tight.ctm'),('Head','male/all/head/inc_heads_legacy.ctm'),('Gloves','common/male_gloves.ctm'),('Boots','common/male_boots.ctm'),('Hair','male/all/head/inc_hair.ctm')]
 defs=source.load(source_root)['definitions'];lookup={x['name']:i for i,x in enumerate(defs)}
 definitions=(a.Def*len(defs))(*(a.Def(a.b(x['name']),a.b(x['geometry_name']),a.b(x['texture_name']),a.b(x['base_name']),(U*2)(*(x['sockets']+[0])[:2]),len(x['sockets']),0) for x in defs))
 records=[];provenance=[]
 for name,path in choices:
  text=(source_root/(root+path)).read_text(errors='replace');match=re.search(r'(?ms)^\s*Info\s*\n(.*?)^\s*End\s*$',text);assert match,path
  f=source.fields(match[1]);tex=[f['tex1'][0],f['tex2'][0]]
  if tex[1].lower()=='mask':
   mask={'Pants':'male/all/lower/inc_tight_patterns.ctm','Chest':'male/all/upper/inc_chest_patterns.ctm','Head':'male/all/head/inc_heads_standard_patterns.ctm','Gloves':'common/patterns_gloves_01.ctm','Boots':'common/patterns_boots_01.ctm'}[name]
   masktext=(source_root/(root+mask)).read_text();assert re.search(r'(?ims)^\s*Mask\s*\n(?:(?!^\s*End).)*?^\s*Name\s+"none"',masktext),mask
   if name=='Head':
    context=(source_root/(root+'male/all/head/menu_standard.ctm')).read_text();assert 'Include menu/costume/localized/'+path in context and 'Include menu/costume/localized/'+mask in context
   else:assert 'Include menu/costume/localized/'+mask in text
   tex[1]='none'
  colors=([[50,35,22,255],[85,59,32,255]] if name=='Hair' else [[40,100,210,255],[230,175,40,255]])+[[0,0,0,255],[0,0,0,255]]
  records.append(a.Part(lookup[name],a.b(f['geo'][0]),(C.c_char_p*2)(*map(a.b,tex)),((C.c_uint8*4)*4)(*((C.c_uint8*4)(*v) for v in colors))))
  provenance.append({'part':name,'source':root+path,'source_sha256':pins['source_files'][root+path],'authored_geometry':f['geo'][0],'authored_texture1':f['tex1'][0],'selected_texture2':tex[1],'mask_source':root+mask if f['tex2'][0].lower()=='mask' else None,'legacy_selection':name=='Head'})
 parts=(a.Part*len(records))(*records);body=a.Body();assert lib.coh_appearance_body(0,None,None,C.byref(body))==0
 textures={Path(n).stem.lower():n for n in pins['files'] if n.endswith('.texture')}
 probe=a.Probe(lambda ctx,kind,key:int(kind==2 and Path(key.decode()).stem.lower() in textures))
 req=a.Request(body,definitions,len(definitions),parts,len(parts),5,(C.c_uint8*4)(196,154,126,255),None,0,probe,None,a.Cancel())
 aw=a.Workspace();draws=(a.Draw*120)();count=Z();status=lib.coh_appearance_assemble(C.byref(req),C.byref(aw),draws,120,C.byref(count),C.byref(a.Diagnostics()));assert status==0 and count.value==8,(status,count.value,[x.geometry_key for x in draws[:count.value]])
 rig_raw=rig_path.read_bytes();assert sha(rig_raw)==pins['neutral_rig_sha256'];rb=C.create_string_buffer(rig_raw);rig=bridge.animation.Rig();assert lib.coh_animation_parse(C.cast(rb,C.POINTER(C.c_uint8)),len(rig_raw),C.byref(rig))==0
 pose=bridge.animation.Pose();assert lib.coh_animation_sample(C.byref(rig),rig.first_frame,C.byref(pose))==0
 resources=(bridge.Resource*count.value)();materials=(bridge.Material*count.value)();material_counts=(U*count.value)();retained=[rb,rig,pose,draws];meta=[];rgba={}
 output.mkdir(parents=True,exist_ok=True)
 for i,d in enumerate(draws[:count.value]):
  name=d.geometry_path.decode().lower();pin=pins['files'][name];raw=(assets/name).read_bytes();assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256']
  b=C.create_string_buffer(raw);size=Z();assert lib.coh_asset_geo_workspace(api.asset.Bytes(C.addressof(b),len(raw)),C.byref(size))==0;h=C.create_string_buffer(size.value);geo=api.asset.Geo();assert lib.coh_asset_geo_open(api.asset.Bytes(C.addressof(b),len(raw)),h,len(h),4096,C.byref(geo))==0
  index=U();model=api.asset.Model();assert lib.coh_appearance_geo_model(C.byref(geo),C.byref(d),4096,C.byref(index),C.byref(model))==0
  requirements=api.Requirements();assert lib.coh_appearance_mesh_requirements(C.byref(geo),index,d.socket,C.byref(requirements))==0
  assert requirements.materials==1,'This complete costume proof admits original single-material parts only'
  scratch=C.create_string_buffer(requirements.workspace_bytes);canonical=C.create_string_buffer(requirements.canonical_bytes);mesh=api.Mesh();assert lib.coh_appearance_mesh_build(C.byref(geo),index,d.socket,scratch,len(scratch),canonical,len(canonical),C.byref(mesh),None)==0
  resources[i]=bridge.Resource(1,1,100+i,5,1,0,0,mesh.indices,d.geometry_path,d.model_name,C.addressof(mesh));material_counts[i]=requirements.materials
  names=[bytes(x).split(b'\0')[0].decode() for x in d.texture];materials[i]=bridge.Material(lib.coh_renderer_default_material(1),1,(C.c_char_p*2)(*map(str.encode,names)))
  for texture in names:
   key=texture.lower()
   if key in rgba:continue
   if key=='none':rgba[key]=(1,1,b'\xff'*4,{'engine_default':'original unbound/none white binding'});continue
   path=textures[key];pin=pins['files'][path];rawtex=(assets/path).read_bytes();assert len(rawtex)==pin['bytes'] and sha(rawtex)==pin['sha256'];tb=C.create_string_buffer(rawtex);view=api.asset.Texture();assert lib.coh_asset_texture(api.asset.Bytes(C.addressof(tb),len(rawtex)),C.byref(view))==0
   pixels=C.create_string_buffer(view.width*view.height*4);assert lib.coh_asset_texture_rgba(C.byref(view),0,pixels,len(pixels))==0
   rgba[key]=(view.width,view.height,pixels.raw,{'path':path,'sha256':pin['sha256'],'rgba_sha256':sha(pixels.raw),'width':view.width,'height':view.height})
  retained.extend([b,h,geo,canonical,mesh]);meta.append({'geometry':name,'source_sha256':pins['files'][name]['sha256'],'model':d.model_name.decode(),'socket':d.socket,'vertices':mesh.vertices,'indices':mesh.indices,'materials':requirements.materials,'textures':names,'canonical_sha256':sha(canonical.raw),'colors':[list(x) for x in d.color]})
  (output/f'part-{i}.mesh').write_bytes(canonical.raw)
 actor=bridge.Actor(1,1,0,5,1,1,C.addressof(rig),None,C.addressof(pose));request=Request(draws,resources,materials,material_counts,count.value,1,actor,1,a.Cancel());diag=Diagnostics();assert lib.coh_appearance_actor_requirements(C.byref(request),C.byref(diag))==0
 vertices=(r.Vertex*diag.vertices)();indices=(U*diag.indices)();work=Workspace();packets=(r.Draw*120)();n=Z();identity=r.identity()
 def render():return lib.coh_appearance_actor_render(C.byref(request),identity,identity,C.byref(work),vertices,len(vertices),indices,len(indices),packets,len(packets),C.byref(n),C.byref(diag))
 assert render()==0 and n.value==8
 negative=0
 def rejected(change,restore,expected):
  nonlocal negative
  before=bytes(packets);oldn=n.value;old=bytes(diag);change();status=render();assert status==expected,(negative,status,expected);assert bytes(packets)==before and n.value==oldn and bytes(diag)==old;restore();negative+=1
 rejected(lambda:setattr(request,'complete',0),lambda:setattr(request,'complete',1),1)
 rejected(lambda:setattr(resources[7],'mesh',None),lambda:setattr(resources[7],'mesh',C.addressof(retained[-1])),3)
 rejected(lambda:setattr(resources[7],'rig_id',2),lambda:setattr(resources[7],'rig_id',1),7)
 rejected(lambda:setattr(materials[7],'surface_generation',2),lambda:setattr(materials[7],'surface_generation',1),7)
 rejected(lambda:setattr(draws[7],'socket',draws[0].socket),lambda:setattr(draws[7],'socket',meta[7]['socket']),1)
 rejected(lambda:material_counts.__setitem__(7,2),lambda:material_counts.__setitem__(7,1),2)
 rejected(lambda:setattr(resources[7],'index_count',resources[7].index_count-3),lambda:setattr(resources[7],'index_count',meta[7]['indices']),2)
 oldtex=materials[7].texture[0];rejected(lambda:materials[7].texture.__setitem__(0,b'missing-authentic-texture'),lambda:materials[7].texture.__setitem__(0,oldtex),3)
 callback=a.CancelFn(lambda ctx:1);request.cancel=a.Cancel(callback,None);before=bytes(packets);assert render()==5 and bytes(packets)==before;request.cancel=a.Cancel();negative+=1
 assert render()==0
 result={'parts':meta,'source_menu_selection':provenance,'body_type':0,'complete_body_geometry':True,'complete_authored_texture_selection':True,'morphology':'explicit source-qualified neutral Male rig; no custom body scales','rig_sha256':sha(rig_raw),'negative_transaction_tests':negative,'vertices':diag.vertices,'indices':diag.indices,'frame_vertex_bytes':diag.vertex_bytes,'frame_index_bytes':diag.index_bytes,'workspace_bytes':C.sizeof(work),'heap_allocations_in_adapter':0,'textures':{k:v[3] for k,v in rgba.items()},'full_gate31_accepted':False}
 # Bounded portable preview package; no metadata aliases or runtime file lookup.
 # Draw records contain only fixed uint32/ASCII/byte fields (asserted in C).
 texture_keys=list(rgba);cursor=64+count.value*1328+len(rgba)*16
 header=bytearray(64);struct.pack_into('<8s8I',header,0,b'COHAPV01',1,0,count.value,len(rgba),64,64+count.value*1328,cursor,len(rig_raw));payload=[rig_raw];cursor+=len(rig_raw);part_records=[];tex_records=[]
 for i,d in enumerate(draws[:count.value]):
  mesh=(output/f'part-{i}.mesh').read_bytes();names=[bytes(t).split(b'\0')[0].decode().lower() for t in d.texture];part_records.append(struct.pack('<4I',cursor,len(mesh),*(texture_keys.index(t) for t in names))+bytes(d));payload.append(mesh);cursor+=len(mesh)
 for key in texture_keys:
  w,h,pixels,_=rgba[key];tex_records.append(struct.pack('<4I',w,h,cursor,len(pixels)));payload.append(pixels);cursor+=len(pixels)
 struct.pack_into('<I',header,12,cursor);package=bytes(header)+b''.join(part_records)+b''.join(tex_records)+b''.join(payload);assert len(package)==cursor
 (output/'appearance-male.bin').write_bytes(package);result['package']={'file':'appearance-male.bin','bytes':len(package),'sha256':sha(package)}
 (output/'actor.json').write_text(json.dumps(result,indent=2)+'\n')
 return lib,request,diag,packets,n,vertices,indices,work,retained,rgba,result,render

def prove(library,assets,source_root,rig_path,output):
 state=prepare(library,assets,source_root,rig_path,output);lib,request,diag,packets,n,vertices,indices,work,retained,rgba,result,render=state
 e=bridge.gpu.EGL();g=e.g;cycles=[];identity=r.identity()
 try:
  for cycle in range(2):
   if cycle:e.recreate_context()
   request.surface=cycle+1
   texture_handles={key:e.texture(v[0],v[1],v[2]) for key,v in rgba.items()}
   for i in range(request.count):
    binding=request.materials[i];binding.surface_generation=cycle+1
    for j in range(2):binding.material.textures[j]=r.Texture(texture_handles[binding.texture[j].decode().lower()].value,1,1,0,0)
    binding.material.cull_back=0;binding.material.depth_test=binding.material.depth_write=1;binding.material.fog_params=r.V4(0,0,100,1)
   target=e.texture(512,640);fbo=U();g.glGenFramebuffers(1,C.byref(fbo));g.glBindFramebuffer(0x8d40,fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0)
   # Real depth attachment prevents rear limbs/hair drawing over the body.
   e.gf('glGenRenderbuffers',None,[C.c_int,C.POINTER(U)]);e.gf('glBindRenderbuffer',None,[U,U]);e.gf('glRenderbufferStorage',None,[U,U,C.c_int,C.c_int]);e.gf('glFramebufferRenderbuffer',None,[U,U,U,U]);e.gf('glDeleteRenderbuffers',None,[C.c_int,C.POINTER(U)])
   depth=U();g.glGenRenderbuffers(1,C.byref(depth));g.glBindRenderbuffer(0x8d41,depth);g.glRenderbufferStorage(0x8d41,0x81a6,512,640);g.glFramebufferRenderbuffer(0x8d40,0x8d00,0x8d41,depth);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5
   driver=C.c_void_p();backend=r.Backend();renderer=C.c_void_p();assert lib.coh_renderer_gles_create(65536,196608,C.byref(driver),C.byref(backend))==0;cfg=r.Config(32,65536,196608,3);assert lib.coh_renderer_create(C.byref(cfg),C.byref(backend),C.byref(renderer))==0
   if cycle:lib.coh_renderer_surface_lost(renderer,cycle+1,1)
   else:lib.coh_renderer_surface_lost(renderer,1,1)
   pose_results=[]
   try:
    for step in range(3):
     rig=retained[1];pose=retained[2];at=rig.first_frame+(rig.last_frame-rig.first_frame)*step/2;assert lib.coh_animation_sample(C.byref(rig),at,C.byref(pose))==0;request.actor.pose_generation=step+1;assert render()==0
     # Fixed full-character camera from first pose bounds, reused all steps.
     if cycle==0 and step==0:
      xyz=[[v.position[k] for v in vertices] for k in range(3)];mins=list(map(min,xyz));maxs=list(map(max,xyz));center=[(x+y)/2 for x,y in zip(mins,maxs)];scale=1.65/max(maxs[1]-mins[1],(maxs[0]-mins[0])*1.25)
     g.glViewport(0,0,512,640);g.glDepthMask(1);g.glClearColor(.035,.045,.065,1);g.glClear(0x4000|0x100);assert lib.coh_renderer_begin(renderer,cycle+1)==0
     for i in range(n.value):
      d=packets[i];d.model_view=identity;d.model_view[12]=-center[0];d.model_view[13]=-center[1];d.model_view[14]=-center[2];d.projection=identity;d.projection[0]=scale*1.25;d.projection[5]=scale;d.projection[10]=-.08
      assert lib.coh_renderer_submit(renderer,C.byref(d))==0
     assert lib.coh_renderer_flush(renderer,r.Cancel())==0,lib.coh_renderer_gles_shader_log(driver)
     pixels=C.create_string_buffer(512*640*4);g.glReadPixels(0,0,512,640,0x1908,0x1401,pixels);assert g.glGetError()==0
     from PIL import Image
     im=Image.frombytes('RGBA',(512,640),pixels.raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM);image=output/f'male-context{cycle+1}-pose{step+1}.png';im.save(image)
     raw=pixels.raw;background=raw[:4];visible=sum(raw[i:i+4]!=background for i in range(0,len(raw),4));assert visible>3000,visible
     pose_results.append({'source_frame':at,'visible_pixels':visible,'rgba_sha256':sha(pixels.raw),'image':image.name})
    stats=lib.coh_renderer_stats(renderer);cycles.append({'surface_generation':cycle+1,'draws':stats.drawn,'submitted':stats.submitted,'gl_errors':0,'poses':pose_results})
   finally:
    lib.coh_renderer_destroy(renderer);lib.coh_renderer_gles_destroy(driver,1);g.glDeleteFramebuffers(1,C.byref(fbo));g.glDeleteTextures(1,C.byref(target));g.glDeleteRenderbuffers(1,C.byref(depth))
    for tex in texture_handles.values():g.glDeleteTextures(1,C.byref(tex))
  result.update(host_textured_gpu_qualified=True,gpu={'identity':e.identity,'contexts':cycles,'texture_bytes':sum(len(v[2]) for v in rgba.values()),'readback':'test-only'},android_executed=False,physical_thor=False)
  (output/'actor.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:e.close()

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--rig',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();result=prove(args.library,args.assets,args.source_root,args.rig,args.output);print(json.dumps({k:result[k] for k in ['host_textured_gpu_qualified','vertices','indices','negative_transaction_tests','gpu']}))

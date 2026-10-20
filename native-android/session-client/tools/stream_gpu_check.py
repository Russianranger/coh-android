#!/usr/bin/env python3
"""Qualify new session map/asset/renderer adapters on an actual host GLES context.

Reuses admitted raw assets and camera kernels. Does not rerun old module suites.
Requires Mesa libEGL.so.1/libGL.so.1, a host C compiler and NDK GLES headers.
--prepared contains map.bin/map-fixture.json; --accepted-assets contains the
accepted world.bin/world-fixture.json and its material-reference binary.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,math,os,struct,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
sys.path.insert(0,str(NATIVE/'engine/renderer/tests'))
from bindings import F,U,Z,Q,V3,V4,M4,Draw
from gpu_check import EGL
class WorldStats(C.Structure):
 _fields_=[(n,Q) for n in ('catalog_instances','selected_instances','resident_bytes','budget_bytes','peak_resident_bytes','selection_updates','cache_hits','cache_misses','evictions','draws','geo_loads','texture_loads','errors','draw_packets','tf_components','tf_mismatches','visible_pixels','owned_cpu_bytes','gpu_bytes')]+[('generation',U),('material_mode_mask',U),('view_radius',F),('tf_max_error',F)]
class BridgeStats(C.Structure):
 _fields_=[('allocated_bytes',Z),('peak_allocated_bytes',Z)]+[(n,U) for n in ('meshes','textures','pins','surface_generation')]+[(n,Q) for n in ('mesh_hits','mesh_loads','texture_hits','texture_loads','uploads','evictions','rejections')]
class AssetStats(C.Structure):
 _fields_=[(n,Z) for n in ('allocated_bytes','peak_allocated_bytes','resident_bytes','peak_resident_bytes')]+[(n,U) for n in ('indexed_entries','mounted_sources','resident_entries','pinned_blobs')]+[(n,Q) for n in ('cache_hits','cache_misses','evictions','reads','read_bytes','rejections')]
class Instance(C.Structure):_fields_=[('node',U),('endpoint',U),('world',F*12),('tint',F*6)]
class CameraNode(C.Structure):_fields_=[('parent',U),('position',V3),('pyr_degrees',V3)]
class Camera(C.Structure):_fields_=[('position',V3),('pyr_degrees',V3),('fovy',F),('aspect',F),('znear',F),('zfar',F),('flip_x',U),('flip_y',U)]
class CameraInputs(C.Structure):_fields_=[('nodes',CameraNode*6),('cameras',Camera*6)]
def run(command,**kw):
 p=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise RuntimeError(' '.join(map(str,command))+'\n'+p.stdout+p.stderr)
 return p.stdout
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def values(obj):return {n:getattr(obj,n) for n,_ in obj._fields_}
def f32(v):return F(v).value
def source_product(a,b):
 result=[]
 for col in range(4):
  for row in range(3):
   value=f32(f32(f32(a[row]*b[col*3])+f32(a[3+row]*b[col*3+1]))+f32(a[6+row]*b[col*3+2]))
   if col==3:value=f32(value+a[9+row])
   result.append(value)
 return result
def admitted_assets(path,temp):
 """Preserve binary bytes and record the accepted filename alias explicitly."""
 meta=json.loads((path/'world-fixture.json').read_text());assets=meta['assets']
 if 'material-reference.bin' in assets:return path,None
 pin=assets['world-material-reference.bin'];ref=next((path/name for name in ('world-material-reference.bin','material-reference.bin') if (path/name).is_file() and sha(path/name)==pin['sha256']),None)
 assert ref is not None,'accepted material-reference pin missing'
 target=temp/'accepted-alias';target.mkdir();(target/'world.bin').symlink_to((path/'world.bin').resolve());(target/'material-reference.bin').symlink_to(ref.resolve())
 meta['assets']['material-reference.bin']=dict(pin);(target/'world-fixture.json').write_text(json.dumps(meta))
 return target,{'source_metadata_sha256':sha(path/'world-fixture.json'),'binary_alias':{ref.name:'material-reference.bin'},'binary_sha256':pin['sha256'],'binary_bytes_unchanged':True}
def wrapper(library,prepared,accepted):
 fixture=json.loads((prepared/'map-fixture.json').read_text());raw=(prepared/'map.bin').read_bytes();pin=fixture['bundle'];assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
 # Verify each original raw asset inside the app envelope against its source pin.
 entry_count,rows=struct.unpack_from('<II',raw,28);source_rows=[]
 for i,item in enumerate(fixture['assets']):
  row=struct.unpack_from('<6I',raw,rows+i*24);data=raw[row[2]:row[2]+row[3]];assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'];source_rows.append({'path':item['path'],'bytes':len(data),'sha256':item['sha256']})
 assert entry_count==len(source_rows)==8
 e=EGL();g=e.g;lib=C.CDLL(str(library));world=C.c_void_p();stats=WorldStats();error=C.create_string_buffer(1024);data=C.create_string_buffer(raw)
 for n,r,types in [('glGenRenderbuffers',None,[C.c_int,C.POINTER(U)]),('glDeleteRenderbuffers',None,[C.c_int,C.POINTER(U)]),('glBindRenderbuffer',None,[U,U]),('glRenderbufferStorage',None,[U,U,C.c_int,C.c_int]),('glFramebufferRenderbuffer',None,[U,U,U,U])]:e.gf(n,r,types)
 frame=[]
 def render_target():
  target=e.texture(256,256);fbo=U();depth=U();g.glGenFramebuffers(1,C.byref(fbo));g.glBindFramebuffer(0x8d40,fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0);g.glGenRenderbuffers(1,C.byref(depth));g.glBindRenderbuffer(0x8d41,depth);g.glRenderbufferStorage(0x8d41,0x81a6,256,256);g.glFramebufferRenderbuffer(0x8d40,0x8d00,0x8d41,depth);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5
  frame[:]=[target,fbo,depth]
 render_target()
 lib.coh_session_world_create.argtypes=[C.c_void_p,Z,C.POINTER(C.c_void_p),C.c_void_p,Z]
 lib.coh_session_world_destroy.argtypes=[C.POINTER(C.c_void_p)]
 for name in ('coh_session_world_surface','coh_session_world_draw'):getattr(lib,name).argtypes=[C.c_void_p,C.POINTER(F),C.POINTER(F),C.POINTER(F),F,C.POINTER(WorldStats),C.c_void_p,Z]
 lib.coh_session_world_surface_lost.argtypes=[C.c_void_p,C.c_int,C.POINTER(WorldStats)]
 lib.coh_stream_test_packet.argtypes=[C.c_void_p,U,C.POINTER(Draw)];lib.coh_stream_test_packet_count.argtypes=[C.c_void_p];lib.coh_stream_test_packet_count.restype=U
 lib.coh_stream_test_instance.argtypes=[C.c_void_p,U,C.POINTER(Instance)]
 lib.coh_stream_test_bridge_stats.argtypes=[C.c_void_p];lib.coh_stream_test_bridge_stats.restype=BridgeStats
 lib.coh_stream_test_asset_stats.argtypes=[C.c_void_p];lib.coh_stream_test_asset_stats.restype=AssetStats
 lib.coh_world_parse_inputs.argtypes=[C.c_void_p,Z,C.POINTER(CameraInputs)];lib.coh_world_camera.argtypes=[C.POINTER(CameraInputs),U,F,C.POINTER(F),C.POINTER(F)]
 accepted_raw=(accepted/'world.bin').read_bytes();inputs=CameraInputs();offset=struct.unpack_from('<I',accepted_raw,48)[0];source_inputs=C.create_string_buffer(accepted_raw[offset:offset+520]);assert lib.coh_world_parse_inputs(source_inputs,520,C.byref(inputs))==0
 spawn=V3(*fixture['spawn']);view=(F*12)();projection=M4();camera=inputs.cameras[0]
 def source_camera(center,yaw=0,pitch=.16):
  pitch=f32(pitch);yaw=f32(yaw);cp=f32(math.cos(pitch));distance=22.
  camera.position=V3(f32(center[0]+f32(f32(distance*f32(math.sin(yaw)))*cp)),f32(f32(center[1]+3.8)+f32(distance*f32(math.sin(pitch)))),f32(center[2]+f32(f32(distance*f32(math.cos(yaw)))*cp)))
  camera.pyr_degrees=V3(f32(f32(pitch*180)/f32(math.pi)),f32(f32(yaw*180)/f32(math.pi)),0)
  assert lib.coh_world_camera(C.byref(inputs),0,1,view,projection)==0
 def invoke(name,radius,center=spawn):
  assert getattr(lib,name)(world,view,projection,center,radius,C.byref(stats),error,len(error)),error.value.decode()
  assert stats.tf_mismatches==0 and stats.errors==0 and stats.resident_bytes<=stats.budget_bytes==512*1024
  return values(stats)
 def packets(radius,center=spawn):
  actual=[];comparisons=0;count=lib.coh_stream_test_packet_count(world);cursor=0
  expected=fixture['radius_queries'][str(int(radius))] if list(center)==list(spawn) else [x['node'] for x in fixture['instances'] if sum((x['world_center'][j]-center[j])**2 for j in range(3))<=(radius+x['radius'])**2]
  for i,node_id in enumerate(expected):
   instance=Instance();assert lib.coh_stream_test_instance(world,i,C.byref(instance)) and instance.node==node_id
   source=next(x for x in fixture['instances'] if x['node']==node_id);assert bytes(instance.world)==struct.pack('<12f',*source['world'])
   matrix=source_product(view,instance.world);gl=[]
   for col in range(4):gl.extend(matrix[col*3:col*3+3]+[1. if col==3 else 0.])
   endpoint=fixture['endpoints'][source['endpoint']]
   for material in endpoint['source_model_materials']:
    d=Draw();assert lib.coh_stream_test_packet(world,cursor,C.byref(d));cursor+=1
    assert bytes(d.model_view)==struct.pack('<16f',*gl),'source view × hierarchy differs'
    assert bytes(d.projection)==bytes(projection)
    declared=next(m for m in fixture['materials'] if m['name'].casefold()==material['name'].casefold())
    assert d.material.family==declared['family'] and list(d.material.const0)[:3]==list(instance.tint)[:3] and list(d.material.const1)[:3]==list(instance.tint)[3:]
    assert list(d.material.fog_params)==[0.,0.,1000000.,1.]
    for unit in range(2):assert d.material.textures[unit].handle and d.material.textures[unit].wrap_s==declared['wrap'][unit] and d.material.textures[unit].wrap_t==declared['wrap'][unit]
    comparisons+=32
   actual.append(node_id)
  assert cursor==count and count==stats.selected_instances*2 and stats.material_mode_mask==3
  return {'nodes':actual,'packets':count,'exact_source_matrix_projection_components':comparisons}
 # Actual framebuffer draw/readback validates textures are not obscured by fog.
 def pixels(radius,center=spawn):
  g.glBindFramebuffer(0x8d40,frame[1]);g.glViewport(0,0,256,256);g.glDepthMask(1);g.glClearColor(17/255,19/255,23/255,1);g.glClear(0x4100)
  invoke('coh_session_world_draw',radius,center);rgba=(C.c_uint8*(256*256*4))();g.glReadPixels(0,0,256,256,0x1908,0x1401,rgba);assert g.glGetError()==0
  visible=[tuple(rgba[i:i+3]) for i in range(0,len(rgba),4) if any(abs(rgba[i+k]-c)>2 for k,c in enumerate((17,19,23)))]
  textured=sum(max(p)>28 and max(p)-min(p)>3 for p in visible);assert visible and textured>100,(len(visible),textured)
  return {'visible_pixels':len(visible),'nonblack_chromatic_pixels':textured}
 result={'passed':False,'host_software_gpu_only':True,'android_execution':False,'physical_thor':False,'identity':e.identity,'bundle_sha256':pin['sha256'],'original_raw_assets':source_rows,'selection':{},'surface':[]}
 try:
  assert lib.coh_session_world_create(data,len(raw),C.byref(world),error,len(error)),error.value.decode()
  source_camera(spawn);near=invoke('coh_session_world_surface',24);assert near['catalog_instances']==11 and near['selected_instances']==6 and near['geo_loads']==3 and near['texture_loads']==6 and near['tf_components'] and near['visible_pixels']>0
  result['surface'].append(near);result['selection']['near']=packets(24);result['near_render']=pixels(24)
  original=lib.coh_stream_test_bridge_stats(world);asset=lib.coh_stream_test_asset_stats(world);stable_bytes=original.allocated_bytes
  invoke('coh_session_world_draw',96);assert stats.selected_instances==11;result['selection']['far']=packets(96);result['far_render']=pixels(96)
  # Repeated Near/Far toggles exercise unchanged decoded bridge/cache ownership.
  for i in range(120):invoke('coh_session_world_draw',24 if i%2 else 96)
  bridge=lib.coh_stream_test_bridge_stats(world);assert bridge.mesh_loads==original.mesh_loads==3 and bridge.texture_loads==original.texture_loads==6 and bridge.allocated_bytes==stable_bytes
  assert lib.coh_stream_test_asset_stats(world).allocated_bytes==asset.allocated_bytes
  result['bounded_cache']={'toggle_draws':120,'budget_bytes':stats.budget_bytes,'peak_resident_bytes':stats.peak_resident_bytes,'unchanged_bridge_allocated_bytes':stable_bytes,'geo_decode_count':bridge.mesh_loads,'texture_decode_count':bridge.texture_loads,'raw_evictions':stats.evictions,'all_admitted_raw_assets_fit_budget':True}
  # Changed real source camera and center compose without any matrix transpose.
  moved=V3(spawn[0]+5,spawn[1],spawn[2]-5);source_camera(moved,.4,.2);invoke('coh_session_world_draw',96,moved);result['selection']['moved_camera']=packets(96,moved)
  # Context resources are dropped/reuploaded; decoded CPU assets remain cached.
  lib.coh_session_world_surface_lost(world,1,C.byref(stats));assert stats.gpu_bytes==0
  source_camera(spawn);live=invoke('coh_session_world_surface',24);result['surface'].append(live);b=lib.coh_stream_test_bridge_stats(world);assert b.mesh_loads==3 and b.texture_loads==6 and b.uploads==12 and b.allocated_bytes==stable_bytes
  lib.coh_session_world_surface_lost(world,0,C.byref(stats));e.recreate_context();render_target()
  source_camera(spawn);recreated=invoke('coh_session_world_surface',96);result['surface'].append(recreated);b=lib.coh_stream_test_bridge_stats(world);assert b.mesh_loads==3 and b.texture_loads==6 and b.uploads==18 and b.allocated_bytes==stable_bytes
  result['context_recreate']={'passed':True,'generations':stats.generation,'gpu_uploads':b.uploads,'geo_decodes_unchanged':b.mesh_loads,'texture_decodes_unchanged':b.texture_loads,'cpu_bytes_unchanged':stable_bytes}
  result['recreated_render']=pixels(96);result['passed']=True
 finally:
  if world:lib.coh_session_world_surface_lost(world,1,C.byref(stats));lib.coh_session_world_destroy(C.byref(world));assert not world.value
  if frame:g.glDeleteFramebuffers(1,C.byref(frame[1]));g.glDeleteTextures(1,C.byref(frame[0]));g.glDeleteRenderbuffers(1,C.byref(frame[2]))
  e.close()
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--accepted-assets',type=Path,required=True);p.add_argument('--ndk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 source=[NATIVE/'session-client/app/src/main/cpp/session_world_imports.c',NATIVE/'engine/assets/coh_asset_zip.c',NATIVE/'engine/world/coh_world_live.c',NATIVE/'session-client/tools/stream_gpu_fixture.c',NATIVE/'session-client/app/src/main/cpp/session_stream_qualify.c',NATIVE/'engine/world/coh_world_stream.c',NATIVE/'engine/bridge/coh_asset_render.c',NATIVE/'engine/assets/coh_asset_loader.c',NATIVE/'engine/assets/coh_asset_geo.c',NATIVE/'engine/renderer/coh_debug_entity.c',NATIVE/'engine/renderer/coh_renderer.c',NATIVE/'engine/renderer/coh_renderer_gles.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c',NATIVE/'world/coh_world.c']
 flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-strict-aliasing','-O2','-shared','-fPIC']
 includes=['-I',NATIVE/'include','-I',NATIVE/'engine/assets','-I',NATIVE/'engine/world','-I',NATIVE/'engine/bridge','-I',NATIVE/'engine/renderer']
 with tempfile.TemporaryDirectory(prefix='coh-stream-gpu-') as directory:
  t=Path(directory);inc=t/'include';inc.mkdir();tool=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64'
  for name in ('GLES3','KHR'):(inc/name).symlink_to((tool/'sysroot/usr/include'/name).resolve(),target_is_directory=True)
  camera_obj=t/'camera-host.o';run(['cc',*[f for f in flags if f not in ('-pedantic','-shared')],'-c',source[-1],'-o',camera_obj])
  library=t/'stream.so';command=['cc',*flags,*includes,'-I',inc,*source[:-1],camera_obj,'-l:libGL.so.1','-lz','-lm','-o',library];run(command)
  accepted,alias=admitted_assets(a.accepted_assets,t)
  result={'schema':'coh-session-stream-gpu-v1','passed':True,'source_sha256':{str(x.relative_to(NATIVE)):sha(x) for x in [*source,NATIVE/'session-client/app/src/main/cpp/session_stream_world.c',NATIVE/'session-client/app/src/main/cpp/session_stream_world.h',NATIVE/'session-client/app/src/main/cpp/session_stream_qualify.h',Path(__file__),HERE/'stream_qualify_check.py']},'accepted_binary_alias':alias,'profiles':[]}
  # Separate processes are required because Mesa reads the override on startup.
  for version in ('3.2','3.0'):
   env={**os.environ,'MESA_GLES_VERSION_OVERRIDE':version};q=t/f'qualify-{version}.json';run([sys.executable,HERE/'stream_qualify_check.py','--library',library,'--accepted-assets',accepted,'--output',q],env=env)
   result['profiles'].append({'gles_version':version,'diagnostics':json.loads(q.read_text())})
  result['world']=wrapper(library,a.prepared,a.accepted_assets)
  android_sources=[NATIVE/'session-client/app/src/main/cpp/session_stream_world.c',*source[1:-1]];arm=t/'stream-arm64.so';camera_arm=t/'camera-arm64.o';run([tool/'bin/aarch64-linux-android26-clang',*[f for f in flags if f not in ('-pedantic','-shared')],'-c',source[-1],'-o',camera_arm]);run([tool/'bin/aarch64-linux-android26-clang',*flags,*includes,*android_sources,camera_arm,'-lGLESv3','-lz','-lm','-Wl,--no-undefined','-o',arm]);result['android_arm64_link']={'passed':True,'execution':False,'bytes':arm.stat().st_size,'sha256':sha(arm),'elf':run(['file',arm]).strip()}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'world':{k:result['world'][k] for k in ['selection','bounded_cache','context_recreate','near_render','far_render']},'android_arm64_link':result['android_arm64_link']},indent=2))
if __name__=='__main__':main()

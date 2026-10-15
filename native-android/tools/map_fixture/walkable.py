#!/usr/bin/env python3
"""Build the existing native WALK container for every admitted source instance.

Reuse accepted GEO, DDS, CTri adapters unchanged; render and collision positions
come from one source-matrix vertex list. No synthesized floor or obstacle.
"""
from pathlib import Path
import ctypes as C, hashlib, importlib.util, json, math, struct, subprocess, tempfile
NATIVE=Path(__file__).resolve().parents[2]
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def build(receipt,assets,source_root,output):
 g=module('mapwalk_geo',NATIVE/'tools/world_fixture/geo_prepare.py');w=module('mapwalk_floor',NATIVE/'tools/walkable_fixture/prepare.py');r=module('mapwalk_reference',NATIVE/'tools/world_fixture/world_reference.py');original=module('mapwalk_original',NATIVE/'tools/world_fixture/original_world_check.py');pins=[]
 with tempfile.TemporaryDirectory(prefix='coh-map-walk-') as temp:
  t=Path(temp);sd=t/'source';sd.mkdir()
  for name,relative in original.PATHS.items():(sd/name).write_bytes((source_root/'upstream/ouroboros'/relative).read_bytes())
  code,pins=original.source_code(sd);code+='\nvoid map_compose(const float a[12],const float b[12],float out[12]){mulMat4Inline((const float(*)[3])a,(const float(*)[3])b,(float(*)[3])out);}\n';(t/'original.c').write_text(code)
  subprocess.run(['cc','-std=c11','-O0','-fPIC','-shared','-ffp-contract=off',str(t/'original.c'),'-lm','-o',str(t/'original.so')],check=True)
  subprocess.run(['cc','-std=c11','-O2','-fPIC','-shared','-ffp-contract=off',str(NATIVE/'walk/source_ctri.c'),str(NATIVE/'walk/source_tritri.c'),'-lm','-o',str(t/'ctri.so')],check=True)
  subprocess.run(['cc','-std=c11','-O2','-fPIC','-shared','-I',str(NATIVE/'include'),str(NATIVE/'src/coh_assets.c'),str(NATIVE/'src/coh_dds.c'),'-o',str(t/'dds.so')],check=True)
  oracle=C.CDLL(str(t/'original.so'));ctri=C.CDLL(str(t/'ctri.so'));dds=C.CDLL(str(t/'dds.so'));fp=C.POINTER(C.c_float);oracle.original_local.argtypes=[fp,fp,fp];oracle.map_compose.argtypes=[fp,fp,fp];ctri.createCTri.argtypes=[C.POINTER(w.CTri),fp,fp,fp];ctri.createCTri.restype=C.c_int;dds.coh_dds_rgba.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
  worlds=[]
  for node in receipt['nodes']:
   local=(C.c_float*12)();pos=(C.c_float*3)(*node['pos']);pyr=(C.c_float*3)(*node['pyr']);oracle.original_local(pos,pyr,local)
   if node['parent']==0xffffffff:worlds.append(list(local))
   else:
    dst=(C.c_float*12)();parent=(C.c_float*12)(*worlds[node['parent']]);oracle.map_compose(parent,local,dst);worlds.append(list(dst))
  raw_by_name={a['source_file']:a['raw'] for a in assets};_,miscdata,miscmodels,_=g.records(raw_by_name['misc.geo']);floordata,floormodels=w.legacy_records(raw_by_name['trainstation.geo'])
  raw_textures=['mono_station_infloor_sml.texture','mono_station_infloor.texture','bench.texture','grey.texture','sign.texture','white.texture'];textures=[]
  for name in raw_textures:
   rgba,width,height,metadata=g.accepted.decode_texture(raw_by_name[name],dds.coh_dds_rgba);textures.append({'name':name,'rgba':rgba,'width':width,'height':height,'source_sha256':g.sha(raw_by_name[name])})
  texindex={assets[a]['path']:raw_textures.index(assets[a]['source_file']) for a in range(len(assets)) if assets[a]['source_file'] in raw_textures};material_by_name={x['name']:x for x in receipt['materials']};meshes=[];parts=[];triangles=[];gridproof=[]
  for instance in receipt['instances']:
   e=receipt['endpoints'][instance['endpoint']];floor=e['geometry']==1;models=floormodels if floor else miscmodels;data=floordata if floor else miscdata;stream=w.stream if floor else g.stream;m=next(x for x in models if x['name']==e['model']);g.require(m['scale']==[1.,1.,1.] and not m['bone_info_offset'],'nonrigid source model unsupported');g.require(not stream(data,m,4) and not stream(data,m,5),'source skin/secondaryuv unsupported')
   decoded={j:g.accepted.decode_delta(stream(data,m,j),m['triangle_count'] if j==0 else m['vertex_count'],2 if j==3 else 3,j!=0) for j in range(4)};g.require(all(0<=x<m['vertex_count'] for x in decoded[0]),'source index bound')
   matrix=r.row_matrix(worlds[instance['node']]);vertices=[]
   for i in range(m['vertex_count']):vertices.append(r.transform(matrix,decoded[1][i*3:i*3+3])+r.transform(matrix,decoded[2][i*3:i*3+3],False)+[decoded[3][i*2],g.f32(1-decoded[3][i*2+1])]+[1.,0.,0,0])
   tint=None;node=instance['node']
   while node!=0xffffffff:
    if receipt['nodes'][node]['tint'] is not None:tint=receipt['nodes'][node]['tint'];break
    node=receipt['nodes'][node]['parent']
   tint=tint or [255,255,255,0,0,0];colors=[g.f32(x*g.f32(1./255)) for x in tint]
   for material in m['materials']:
    spec=material_by_name[material['name'].casefold()];indices=decoded[0][material['first_triangle']*3:(material['first_triangle']+material['triangle_count'])*3];meshes.append(w.mesh(vertices,indices));parts.append({'node':instance['node'],'model':m['name'],'base_texture':texindex[spec['textures'][0]],'dual_texture':texindex[spec['textures'][1]],'flags':0,'mode':spec['family'],'color1':[*colors[:3],1.],'color2':[*colors[3:],1.],'diffuse_scale':1.,'ambient_scale':1.,'alpha_ref':spec['alpha_ref'],'uv_scale0':spec['uv_scale'][0],'uv_scale1':spec['uv_scale'][1]});triangles.extend([[vertices[j][:3] for j in indices[k:k+3]] for k in range(0,len(indices),3)])
   grid_index=6 if floor else 7;grid=stream(data,m,grid_index);decoded_grid=w.decode_grid(grid,m['triangle_count']);gridproof.append({'node':instance['node'],'model':m['name'],'source_grid_sha256':g.sha(grid),'grid':decoded_grid})
  records=[]
  for points in triangles:
   tri=w.CTri();vs=[(C.c_float*3)(*v) for v in points];valid=ctri.createCTri(C.byref(tri),*vs);flags=2048 if valid and tri.scale else 0;records.append(struct.pack('<9fI',*(x for v in points for x in v),flags))
  po=128;to=po+len(parts)*96;co=to+len(textures)*32;dataoff=co+len(records)*40;cursor=dataoff;pr=[]
  for raw,part in zip(meshes,parts):
   rec=bytearray(96);struct.pack_into('<6I',rec,0,cursor,len(raw),0,part['base_texture'],part['dual_texture'],part['flags']);struct.pack_into('<4f',rec,24,*part['color1']);struct.pack_into('<4f',rec,40,*part['color2']);struct.pack_into('<3fI4f',rec,56,part['diffuse_scale'],part['ambient_scale'],part['alpha_ref'],part['mode'],*part['uv_scale0'],*part['uv_scale1']);pr.append(bytes(rec));cursor+=len(raw)
  tr=[]
  for texture in textures:tr.append(struct.pack('<4I',cursor,len(texture['rgba']),texture['width'],texture['height'])+bytes(16));cursor+=len(texture['rgba'])
  floorinstance=next(x for x in receipt['instances'] if receipt['endpoints'][x['endpoint']]['geometry']==1);fm=r.row_matrix(worlds[floorinstance['node']]);spawn=r.transform(fm,[-36,0,-41.5]);yaw=g.f32(math.atan2(fm[0][0],fm[2][0]));points=[v for tri in triangles for v in tri];lo=[min(p[k] for p in points) for k in range(3)];hi=[max(p[k] for p in points) for k in range(3)];head=bytearray(128);head[:8]=b'COHWALK1';struct.pack_into('<15I',head,8,1,128,len(parts),len(textures),len(records),sum(g.u32(b,16) for b in meshes),sum(g.u32(b,20) for b in meshes),po,96,to,32,co,40,dataoff,cursor);struct.pack_into('<10f',head,68,*lo,*hi,*spawn,yaw)
  raw=bytes(head)+b''.join(pr)+b''.join(tr)+b''.join(records)+b''.join(meshes)+b''.join(x['rgba'] for x in textures);g.require(len(raw)==cursor and cursor<=16<<20 and len(parts)<=32 and len(records)<=8192,'native WALK fixed capacities exceeded');(output/'walkable.bin').write_bytes(raw)
  proof={'schema':'coh-gate23-expanded-walk-v1','passed':True,'assets':{'walkable.bin':{'bytes':len(raw),'sha256':g.sha(raw)}},'source_instances':len(receipt['instances']),'scene':{'part_count':len(parts),'texture_count':len(textures),'triangle_count':len(records),'bounds_min':lo,'bounds_max':hi,'spawn':spawn,'spawn_yaw':yaw},'parts':parts,'grids':gridproof,'source_world_matrices':worlds,'source_math_pins':pins,'render_collision_source_positions_shared':True,'source_CTtri_normal_triangles':sum(struct.unpack_from('<I',x,36)[0]==2048 for x in records),'source_collision_flags':{'mbench':0,'infloor':0,'texopt_collision_flags':0,'normal_bit':2048},'accepted_walkable_replaced':False,'full_atlas_loaded':False,'android_execution_qualified':False,'physical_qualified':False}
  (output/'walkable-fixture.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
